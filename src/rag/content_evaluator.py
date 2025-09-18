import re
import time
from pathlib import Path
import yaml
from typing import List, Dict
from langchain.schema import Document
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma

from .vector_store_manager import VectorStoreManager
from .criteria_manager import CriteriaManager


class ContentEvaluator:
    """Evaluates documents against academic criteria using LLMs, preserving original text formatting."""

    # Initialize configuration, vector store manager, criteria manager, and LLM
    def __init__(self):
        self.cfg = self._load_config()
        self.vector_manager = VectorStoreManager()
        self.criteria_manager = CriteriaManager(Path(__file__).parents[1] / "config" / "config.yaml")
        self.llm = self._init_llm()
        self.results: Dict[str, Dict[str, Dict]] = {}
        self.document_chunks: List[Document] = []  # store document chunks globally

    # Load YAML configuration
    def _load_config(self) -> Dict:
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # Initialize LLM with settings from config
    def _init_llm(self) -> Ollama:
        llm_cfg = self.cfg["llm_settings"]["processing_llm"]
        return Ollama(
            model=llm_cfg["model"],
            temperature=llm_cfg.get("temperature", 0.2),
            top_p=llm_cfg.get("top_p", 0.9)
        )

    # Create a temporary in-memory vector store from documents
    def _create_temp_vector_store(self, docs: List[Document]) -> Chroma:
        return self.vector_manager.build_vector_store(docs, persist=False)

    def _retrieve_top_document_chunks(self, query: str, temp_store: Chroma,
                                    document_chunks: List[Document], k_doc: int) -> List[Document]:
        doc_results = self.vector_manager.multi_query_retrieval(
            [query], vector_store=temp_store, k=100, search_type="similarity"
        )
        all_docs = [doc for docs in doc_results for doc in docs]

        seen_texts, scored_chunks = set(), []
        for doc in all_docs:
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                doc.metadata.setdefault("chunk_index", len(scored_chunks) + 1)
                scored_chunks.append(doc)

        # Fill if not enough chunks
        for doc in document_chunks:
            if len(scored_chunks) >= k_doc:
                break
            if doc.page_content not in seen_texts:
                scored_chunks.append(doc)
                seen_texts.add(doc.page_content)

        return sorted(scored_chunks[:k_doc], key=lambda d: d.metadata["chunk_index"])

    def _retrieve_knowledge_base_chunks(self, query: str, top_chunks: List[Document], k_kb: int) -> List[Document]:
        kb_results = self.vector_manager.multi_query_retrieval([query], vector_store=self.vector_manager.vector_store, k=k_kb*2)
        seen_texts = set(doc.page_content for doc in top_chunks)
        unique_kb_chunks = []

        for doc in sorted([d for docs in kb_results for d in docs], key=lambda d: d.metadata.get("chunk_index", 0)):
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                unique_kb_chunks.append(doc)
            if len(unique_kb_chunks) >= k_kb:
                break

        return unique_kb_chunks

    # Build evaluation prompt for a single criterion
    def _build_single_prompt(self, criterion: Dict, chunks: Dict[str, Dict]) -> str:
        doc_text = "\n\n".join(d.page_content for d in chunks["doc"])
        kb_text = "\n\n".join(d.page_content for d in chunks["kb"])
        return (
            "You are an EXPERT AND CONFIDENT academic evaluator.\n"
            "Evaluate the DOCUMENT against the criterion STRICTLY using the rubric.\n"
            "DO NOT include reasoning outside the structured format.\n\n"
            "### Instructions:\n"
            "1. Carefully read the criterion and the DOCUMENT provided.\n"
            "2. Analyze and search for sections in the DOCUMENT related to the criterion.\n"
            "3. Start from 5.0 and subtract partial points for shortcomings. "
            "Each shortcoming must end with a numeric deduction only, e.g., -x.y\n"
            "The sum of deductions for each criterion must not exceed 5.0.\n"
            "4. Create a RECOMMENDATION for each SHORTCOMING.\n"
            "5. DO NOT OVERTHINK, ANSWER PRECISE AND QUICKLY.\n"
            "6. ONLY return the following format:\n"
            "Name: <Criterion Name>\n"
            "Shortcomings: <shortcoming1> -x.y; ...\n"
            "Recommendations: <recommendation1>; ...\n\n"
            f"### Criterion: {criterion['text']}\n\n"
            f"### DOCUMENT:\n{doc_text}\n\n"
            f"### KNOWLEDGE BASE:\n{kb_text}\n"
        )

    # Build evaluation prompt for multiple criteria
    def _build_multi_prompt(self, criteria_batch: List[Dict], all_chunks: Dict[str, Dict]) -> str:
        sections = []
        for c in criteria_batch:
            doc_text = "\n\n".join(d.page_content for d in all_chunks[c["key"]]["doc"])
            kb_text = "\n\n".join(d.page_content for d in all_chunks[c["key"]]["kb"])
            sections.append(
                f"### Criterion: {c['text']}\n\n"
                f"### DOCUMENT:\n{doc_text}\n\n"
                f"### KNOWLEDGE BASE:\n{kb_text}\n"
            )
        return (
            "You are an EXPERT AND CONFIDENT academic evaluator.\n"
            "Evaluate EACH criterion STRICTLY and INDEPENDENTLY using the rubric.\n"
            "DO NOT include reasoning outside the structured format.\n\n"
            "### Instructions:\n"
            "1. Carefully read each criterion and the DOCUMENT provided.\n"
            "2. Analyze and search for relevant sections in the DOCUMENT.\n"
            "3. Start from 5.0 and subtract partial points for shortcomings. "
            "Each shortcoming must end with a numeric deduction only, e.g., -x.y\n"
            "The sum of deductions for each criterion must not exceed 5.0.\n"
            "4. Create a RECOMMENDATION for each SHORTCOMING.\n"
            "5. DO NOT OVERTHINK, ANSWER PRECISE AND QUICKLY.\n"
            "6. ONLY return the following format:\n"
            "Name: <Criterion Name>\n"
            "Shortcomings: <shortcoming1> -deduction; ...\n"
            "Recommendations: <recommendation1>; ...\n\n"
            + "\n\n".join(sections)
        )

    # Stream LLM response in real-time
    def _stream_llm_response(self, prompt: str) -> str:
        start_time = time.time()
        response_text, token_count = "", 0
        for chunk in self.llm.stream(prompt):
            content = chunk if isinstance(chunk, str) else chunk.get("text", str(chunk))
            print(content, end="", flush=True)
            response_text += content
            token_count += len(content.split())
        elapsed = time.time() - start_time
        print(f"\n--- LLM finished in {elapsed:.2f}s | Tokens: {token_count} ---\n")
        return response_text

    # Run evaluation for all scans and criteria
    def evaluate_all(self, document_chunks: List[Document], k_doc: int = 30,
                     k_kb: int = 5, n_criteria: int = 3):
        self.document_chunks = document_chunks  # keep a reference for title extraction
        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            criteria = scan.get("criteria", [])
            for i in range(0, len(criteria), n_criteria):
                batch = criteria[i:i + n_criteria]
                criteria_batch = [
                    {
                        "key": f"{scan_name}:{c['name']}",
                        "name": c["name"],
                        "text": self.criteria_manager.get_criterion_text(scan_name, c["name"]),
                        "description": self.criteria_manager.get_criterion_description(scan_name, c["name"])
                    }
                    for c in batch
                ]

                temp_store = self._create_temp_vector_store(document_chunks)
                retrievals = {}
                for c in criteria_batch:
                    crit_text = c["text"]
                    print(f"\n=== Evaluating Criterion: {c['name']} ===")
                    print(f"Criterion Text: {crit_text}\n")
                    doc_chunks = self._retrieve_top_document_chunks(
                        crit_text, temp_store, document_chunks, k_doc
                    )
                    kb_chunks = self._retrieve_knowledge_base_chunks(crit_text, doc_chunks, k_kb)
                    retrievals[c["key"]] = {"doc": doc_chunks, "kb": kb_chunks}

                if len(criteria_batch) > 1:
                    prompt = self._build_multi_prompt(criteria_batch, retrievals)
                else:
                    prompt = self._build_single_prompt(criteria_batch[0], retrievals[criteria_batch[0]["key"]])

                print("--- LLM Prompt ---")
                print(prompt)
                print("--- LLM Response ---")
                response = self._stream_llm_response(prompt)

                for c in criteria_batch:
                    crit_name = c["name"]
                    description = c["description"]

                    if len(criteria_batch) > 1:
                        crit_resp_match = re.search(
                            rf"Name:\s*{re.escape(crit_name)}([\s\S]*?)(?=Name:|$)", response
                        )
                    else:
                        crit_resp_match = re.search(
                            rf"Name:\s*{re.escape(crit_name)}([\s\S]*)", response
                        )
                    crit_resp = crit_resp_match.group(1).strip() if crit_resp_match else response

                    shortcomings_match = re.search(
                        r"Shortcomings:\s*(.+?)\n(?:Recommendations:|$)", crit_resp, re.DOTALL
                    )
                    shortcomings, total_deduction = [], 0.0
                    if shortcomings_match:
                        lines = shortcomings_match.group(1).split(";")
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            num_match = re.search(r"-(\d+(?:\.\d+)?)", line)
                            deduction = float(num_match.group(1)) if num_match else 0.0
                            total_deduction += deduction
                            shortcomings.append(re.sub(r"-\d+(?:\.\d+)?", f"-{deduction}", line))

                    recommendations_match = re.search(
                        r"Recommendations:\s*(.+?)\n(?:Score:|$)", crit_resp, re.DOTALL
                    )
                    recommendations = [
                        r.strip() for r in recommendations_match.group(1).split(";") if r.strip()
                    ] if recommendations_match else []

                    score = max(0.0, 5.0 - total_deduction)

                    self.results.setdefault(scan_name, {})[crit_name] = {
                        "description": description,
                        "llm_response": crit_resp,
                        "retrieved_chunks": [
                            d.page_content for d in retrievals[c["key"]]["doc"] +
                            retrievals[c["key"]]["kb"]
                        ],
                        "score": score,
                        "shortcomings": shortcomings,
                        "recommendations": recommendations,
                        "max_score": 5.0
                    }

        return self.results

    # Generate evaluation JSON output
    def generate_json_output(self) -> Dict:
        # Title is always extracted from the first document chunk's first line
        if self.document_chunks:
            main_title = self.document_chunks[0].page_content.split("\n")[0]
        else:
            main_title = "Document Evaluation"

        content_list = []
        for scan in self.criteria_manager.scans:
            scan_name = scan.get("scan")
            scan_desc = scan.get("description", "")
            scan_dict = {
                "scan": scan_name,
                "description": scan_desc,
                "criteria": []
            }

            for criterion in scan.get("criteria", []):
                crit_name = criterion.get("name")
                crit_results = self.results.get(scan_name, {}).get(crit_name, {})
                crit_dict = {
                    "name": crit_name,
                    "description": crit_results.get("description", ""),
                    "score": crit_results.get("score", 0.0),
                    "shortcomings": crit_results.get("shortcomings", []),
                    "recommendations": crit_results.get("recommendations", []),
                    "max_score": crit_results.get("max_score", 5.0)
                }
                scan_dict["criteria"].append(crit_dict)

            content_list.append(scan_dict)

        return {
            "title": main_title,
            "content": content_list
        }
