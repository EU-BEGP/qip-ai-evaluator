import time
from pathlib import Path
import yaml
from typing import List, Dict, Optional
from langchain.schema import Document
import json
from model_wrapper import get_llm_wrapper

from retrievers.vector_store_manager import VectorStoreManager
from .criteria_manager import CriteriaManager
from retrievers.cross_encoder import CrossEncoderRAG

from evaluator.models import Module, Evaluation

class ContentEvaluator:
    """Evaluates documents against academic criteria using LLMs with structured JSON output."""

    def __init__(self, cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        """Initialize evaluator: load config, vector manager, criteria manager, LLM, and CrossEncoderRAG."""
        self.cfg = self._load_config()
        self.vector_manager = VectorStoreManager()
        self.criteria_manager = CriteriaManager(Path(__file__).parents[1] / "config" / "config.yaml")
        self.results: Dict[str, Dict[str, Dict]] = {}
        self.document_chunks: List[Document] = []
        self.rag = CrossEncoderRAG(model_name=cross_encoder_model, use_memory_only=True)
        
        # Model wrapper setup
        self.document_snapshot = ""
        self.llm = get_llm_wrapper(self.cfg)

    def _load_config(self) -> Dict:
        """Load YAML configuration for LLM and processing."""
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def set_documents_for_rag(self, documents: List[Document]):
        """Set documents for CrossEncoderRAG and initialize anchored session memory for this document."""
        self.document_chunks = documents
        self.rag.set_documents(documents)

        # Build anchored memory snapshot once per document (global view)
        snapshot = self._build_document_digest_llm()
        self.document_snapshot = snapshot

    def _build_document_digest_llm(self) -> str:
        """
        Create a compact, LLM-generated digest using a smart-chunking strategy 
        (first 5 + top 20) to prevent crashes and improve accuracy.
        """
        
        # 1. Define the number of chunks
        total_chunks_to_use = 25
        first_n_chunks = 5
        top_k_chunks = 20 # (total - first_n)
        
        # 2. Check if the document is already small
        if len(self.document_chunks) <= total_chunks_to_use:
            # Document is small, just use all of it.
            print(f"[INFO] Snapshot: Document is small ({len(self.document_chunks)} chunks). Using all.")
            selected_chunks = self.document_chunks
        
        else:
            # 3. Document is large. Implement the new strategy.
            print(f"[INFO] Snapshot: Document is large ({len(self.document_chunks)} chunks). Using {total_chunks_to_use} smart chunks (first {first_n_chunks} + top {top_k_chunks}).")
            
            # 3a. Always get the first 5 chunks
            first_five_chunks = self.document_chunks[:first_n_chunks]
            
            # 3b. Get the pool of remaining chunks
            remaining_chunks = self.document_chunks[first_n_chunks:]
            
            # 3c. Define a query to find the "best" chunks for a snapshot
            # We are looking for metadata, so we query for that.
            search_query = (
                "Document Title, Abstract, Keywords, "
                "Intended Learning Outcomes, Outline, Table of Contents, Main Headings"
            )
            
            # 3d. Use RAG to find the top 20 best remaining chunks
            ranked_remaining = self.rag.rank_chunks(
                search_query, 
                documents=remaining_chunks, 
                top_k=top_k_chunks
            )
            top_twenty_chunks = [doc for doc, _, _ in ranked_remaining]
            
            # 3e. Combine them. We sort the top_twenty by their original index
            # to keep the document in a logical order for the LLM.
            top_twenty_chunks.sort(key=lambda doc: doc.metadata.get("chunk_index", 0))
            
            selected_chunks = first_five_chunks + top_twenty_chunks
            
        # 4. Create the final text from *only* the selected chunks
        full_text = "\n\n".join(d.page_content for d in selected_chunks)

        # The prompt uses the smaller, smarter full_text
        prompt = (
            "You are an **academic text parser** — not a summarizer, writer, or analyst.\n"
            "Your ONLY task is to EXTRACT text segments from the DOCUMENT CONTENT below and place them into a JSON object that follows the DocumentSnapshot schema.\n\n"
            "### HARD RULES:\n"
            "1. Return **ONLY JSON** — no reasoning, no explanation, no <think> blocks.\n"
            "2. **Copy text EXACTLY as it appears** in the document. Do not infer, interpret, or guess missing parts.\n"
            "3. If something does not appear in the document, leave it empty (\"\" or []).\n"
            "4. The 'Outline' field must list all main titles and subtitles IN THE DOCUMENT, word-for-word, in order.\n"
            "5. The 'ImportantInformation' field may summarize briefly, but must be derived only from explicit content — not background knowledge.\n"
            "6. Never add, reformulate, or assume information. Do not include anything that isn’t literally in the document.\n"
            "7. Output must be syntactically valid JSON only.\n\n"
            "### DOCUMENT CONTENT:\n" + full_text + "\n\n"
            "### REQUIRED OUTPUT FORMAT:\n"
            "{\n"
            '  "Title": "...",\n'
            '  "Keywords": ["..."],\n'
            '  "Abstract": "...",\n'
            '  "IntendedLearningOutcomesKnowledge": "...",\n'
            '  "IntendedLearningOutcomesSkills": "...",\n'
            '  "IntendedLearningOutcomesResponsibility": "...",\n'
            '  "Outline": ["Title 1", "Subtitle 1.1", "Subtitle 1.2", "..."],\n'
            '  "ImportantInformation": ["Point 1", "Point 2", "...", "Point 20"]\n'
            "}\n\n"
            "DO NOT ADD ANY TEXT THAT IS NOT DIRECTLY FOUND IN THE DOCUMENT CONTENT ABOVE."
        )
        
        return self.llm.run_prompt(prompt, mode="snapshot", remember=True)

    def _retrieve_top_document_chunks(self, query: str, k_doc: int) -> List[Document]:
        """Retrieve top-K document chunks using CrossEncoderRAG ranking without modifying them."""
        ranked = self.rag.rank_chunks(query, top_k=k_doc)
        return [doc for doc, _, _ in ranked]

    def _retrieve_knowledge_base_chunks(self, query: str, top_chunks: List[Document], k_kb: int) -> List[Document]:
        """
        Retrieve knowledge base chunks using vector store, then rerank them with CrossEncoderRAG.
        Ensures no duplicates with document chunks.
        """
        # Step 1: Retrieve raw KB candidates (vector similarity only)
        kb_candidates = self.vector_manager.retrieve(query, k=k_kb * 4)
        if not kb_candidates:
            return []

        # Step 2: Filter out chunks already in the document set
        seen_texts = set(doc.page_content for doc in top_chunks)
        unique_kb_candidates = [doc for doc in kb_candidates if doc.page_content not in seen_texts]

        if not unique_kb_candidates:
            return []

        # Step 3: Rerank retrieved chunks using the cross-encoder
        reranked = self.rag.rank_chunks(query, documents=unique_kb_candidates, top_k=k_kb)

        # Step 4: Return the top reranked chunks only (discard scores)
        return [doc for doc, _, _ in reranked]

    def _build_prompt(self, criterion: Dict, doc_chunks: List[Document], kb_chunks: List[Document], course_key: str = None, scan_name: str = None, criterion_name: str = None) -> str:
        """Build evaluation prompt with DOCUMENT, KNOWLEDGE BASE, and previous evaluation sections."""
        doc_text = "\n\n".join(d.page_content for d in doc_chunks)
        kb_text = "\n\n".join(d.page_content for d in kb_chunks)

        previous_eval_section = ""
        if Evaluation and course_key and scan_name and criterion_name:
            history = Evaluation.get_criterion_history(course_key, scan_name, criterion_name, limit=1)
            if history:
                prev = history[0]
                previous_eval_section = (
                    f"### PREVIOUS EVALUATION TO '{criterion_name}' IN THE MODULE (most recent):\n"
                    f"Date: {prev['evaluation_date']}\n"
                    f"Description: {prev['description']}\n"
                    f"Score: {prev['score']}\n"
                    f"Shortcomings: {prev['shortcomings']}\n"
                    f"Recommendations: {prev['recommendations']}\n\n"
                )

        prompt = (
            "You are an EXPERT AND CONFIDENT academic evaluator.\n"
            "DO NOT TAKE POINTS UNLESS THERE IS A CLEAR REASON AND DO NOT TAKE STRONG DEDUCTIONS.\n"
            "Evaluate the DOCUMENT against the criterion STRICTLY and ONLY using the RUBRIC.\n"
            "Rely on the KNOWLEDGE BASE for additional context if needed.\n"
            "### Instructions:\n"
            "1. Carefully read the CRITERION and the DOCUMENT provided. Search the DOCUMENT for the relevant section for the CRITERION.\n"
            "2. You may consult the KNOWLEDGE BASE for additional context, but primary evaluation should focus on DOCUMENT.\n"
            "3. Start from 5.0 and subtract partial points for shortcomings.\n"
            "4. For EACH Shortcoming:\n"
            "   - Provide exactly ONE Recommendation.\n"
            "   - Provide exactly ONE numeric Deduction.\n"
            "   - **CRITICAL RULE:** The `Shortcomings`, `Recommendations`, and `Deductions` lists MUST always have the same number of items.\n"
            "6. Finish with a concise Description summarizing the analysis.\n"
            "7. Conduct a thorough and precise analysis.\n"
            "8. ONLY return the following JSON format:\n\n"
            "{\n"
            '  "Name": "<Criterion Name>",\n'
            '  "Shortcomings": ["<shortcoming1>", "<shortcoming2>", ...],\n'
            '  "Recommendations": ["<recommendation1>", "<recommendation2>", ...],\n'
            '  "Deductions": [-x.y, -x.y, ...],\n'
            '  "Description": "<summary of the analysis>"\n'
            "}\n"
            "9. **If there are NO shortcomings:**\n"
            "   - You MUST return:\n"
            '     "Shortcomings": ["NO SHORTCOMINGS"]\n'
            '     "Recommendations": ["NO RECOMMENDATIONS"]\n'
            '     "Deductions": [0.0]\n'
            '     "Description": "<summary of the analysis>"\n'
            f"### Criterion: {json.dumps(criterion, indent=2)}\n\n"
            f"### DOCUMENT:\n{doc_text}\n\n"
            f"### KNOWLEDGE BASE:\n{kb_text}\n\n"
            f"### DOCUMENT SNAPSHOT:\n{self.document_snapshot}\n\n"
            f"{previous_eval_section}"
        )
        print("-------------------- Prompt to LLM --------------------")
        print(prompt)
        return prompt

    def _evaluate_criterion(self, criterion: Dict, doc_chunks: List[Document], kb_chunks: List[Document], course_key: str = None, scan_name: str = None, criterion_name: str = None):
        """Run evaluation for a single criterion against DOCUMENT and KNOWLEDGE BASE separately, with previous evaluation if available."""
        prompt = self._build_prompt(criterion, doc_chunks, kb_chunks, course_key, scan_name, criterion_name)
        start_time = time.time()
        
        # Evaluate using LLM with structured output
        eval_obj = self.llm.run_prompt(prompt, mode="criterion", remember=False)
        elapsed = time.time() - start_time
        return {"evaluation": eval_obj, "elapsed": elapsed}

    def evaluate(self, document_chunks: List[Document], k_doc: int = 10, k_kb: int = 5, course_key: str = None, scan_name: Optional[str] = None):
        """
        Evaluate documents against criteria.
        
        If 'scan_name' is provided, only that scan is evaluated.
        If 'scan_name' is None, all scans are evaluated.
        """
        self.document_chunks = document_chunks
        benchmark_results = []
        
        # Determine which scans to run
        scans_to_process = []
        if scan_name:
            # Find the specific scan
            scans_to_process = [s for s in self.criteria_manager.scans if s.get("scan") == scan_name]
            if not scans_to_process:
                print(f"[ERROR] Scan '{scan_name}' not found in criteria configuration.")
                return {} # Return empty results
        else:
            # Run all scans (default behavior)
            scans_to_process = self.criteria_manager.scans

        for scan in scans_to_process:
            current_scan_name = scan.get("scan")
            criteria = scan.get("criteria", [])
            print(f"[INFO] Starting evaluation for scan: {current_scan_name}")

            for c in criteria:
                crit = {
                    "key": f"{current_scan_name}:{c['name']}",
                    "name": c["name"],
                    "text": self.criteria_manager.get_criterion_text(current_scan_name, c["name"]),
                    "description": self.criteria_manager.get_criterion_description(current_scan_name, c["name"])
                }

                search_query = f"{crit['name']}: {crit['description']}"

                # Retrieve top document chunks (CrossEncoderRAG) without touching original chunks
                doc_chunks = self._retrieve_top_document_chunks(search_query, k_doc)

                # Retrieve KB chunks (vector store only)
                kb_chunks = self._retrieve_knowledge_base_chunks(search_query, doc_chunks, k_kb)

                # Evaluate criterion, passing course_key, scan_name, criterion_name
                res = self._evaluate_criterion(crit, doc_chunks, kb_chunks, course_key, current_scan_name, crit["name"])
                if res:
                    eval_obj = res["evaluation"]
                    shortcomings_with_deductions = [
                        f"{s} {d:.1f}" for s, d in zip(eval_obj.Shortcomings, eval_obj.Deductions)
                    ]

                    self.results.setdefault(current_scan_name, {})[crit["name"]] = {
                        "description": eval_obj.Description,
                        "llm_response": eval_obj.model_dump_json(indent=2),
                        "retrieved_chunks": [d.page_content for d in doc_chunks + kb_chunks],
                        "score": max(0.0, 5.0 + sum(eval_obj.Deductions)),
                        "shortcomings": shortcomings_with_deductions,
                        "recommendations": eval_obj.Recommendations,
                        "max_score": 5.0,
                        "elapsed": res["elapsed"]
                    }
                    benchmark_results.append((crit["name"], res["elapsed"], sum(eval_obj.Deductions)))

        if Evaluation and course_key:
            results_json = self.generate_json_output(scans_processed=scans_to_process)
            
            try:
                # 1. Get or create the module (mimics 'save_module')
                module_obj, _ = Module.objects.get_or_create(course_key=course_key)
                
                # 2. Delete old evaluations (mimics 'save_evaluation' logic)
                old_evaluation_ids = Evaluation.objects.filter(
                    module=module_obj
                ).order_by('-evaluation_date').values_list('id', flat=True)[2:]
                
                if old_evaluation_ids:
                    Evaluation.objects.filter(id__in=list(old_evaluation_ids)).delete()

                # 3. Create new evaluation
                new_evaluation = Evaluation(module=module_obj)
                new_evaluation.set_results_dict(results_json)
                new_evaluation.save()
                
                print(f"[INFO] Successfully saved new evaluation {new_evaluation.id} for module {course_key}")
            except Exception as e:
                print(f"[ERROR] Failed to save evaluation to Django DB: {e}")

        return self.results

    def generate_json_output(self) -> Dict:
        """Generate consolidated JSON output with evaluations for all scans and criteria."""
        main_title = self.document_chunks[0].page_content.split("\n")[0] if self.document_chunks else "Document Evaluation"
        content_list = []

        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            scan_desc = scan.get("description", "")
            scan_dict = {"scan": scan_name, "description": scan_desc, "criteria": []}

            for criterion in scan.get("criteria", []):
                crit_name = criterion.get("name")
                crit_results = self.results.get(scan_name, {}).get(crit_name, {})
                crit_dict = {
                    "name": crit_name,
                    "description": crit_results.get("description", ""),
                    "score": crit_results.get("score", 0.0),
                    "shortcomings": crit_results.get("shortcomings", []),
                    "recommendations": crit_results.get("recommendations", []),
                    "max_score": 5.0
                }
                scan_dict["criteria"].append(crit_dict)
            content_list.append(scan_dict)

        return {"title": main_title, "content": content_list}
