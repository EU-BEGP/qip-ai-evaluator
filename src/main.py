from pathlib import Path
import json
import yaml
import logging

from rag.vector_store_manager import VectorStoreManager
from evaluation.criteria_extractor import CriteriaExtractor
from rag.content_evaluator import ContentEvaluator
from evaluation.report_manager import ReportManager


# -------------------- CONFIG UTILITIES --------------------

def load_config():
    cfg_path = Path(__file__).parent / "config" / "config.yaml"
    if not cfg_path.exists():
        logging.warning("Config file not found, using defaults.")
        return {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_project_path(path_str, default):
    """Resolve a path relative to project root if not absolute."""
    project_root = Path(__file__).parent
    path = Path(path_str or default)
    return (project_root / path).resolve() if not path.is_absolute() else path.resolve()


# -------------------- MAIN PROCESS STEPS --------------------

def build_knowledge_base(kb_paths):
    """Step 1: Build and load the persistent Knowledge Base vector store."""
    print("\n=== Step 1: Build Knowledge Base Vector Store ===")
    logging.info("Building Knowledge Base Vector Store...")
    manager = VectorStoreManager()

    docs = manager.load_documents(kb_paths)
    logging.info(f"Loaded {len(docs)} document chunks.")

    manager.build_vector_store(docs)
    manager.load_vector_store()
    logging.info("Knowledge base vector store ready.")
    return manager


def load_or_extract_criteria(input_file):
    """Step 2: Load criteria from JSON or extract from PDF/DOCX."""
    print("\n=== Step 2: Load or Extract Criteria ===")
    logging.info("Loading or extracting evaluation criteria...")
    cfg = load_config()
    scans_path = resolve_project_path(
        cfg.get("evaluation", {}).get("scans_path"),
        "KB/scans.json"
    )
    scans_path.parent.mkdir(parents=True, exist_ok=True)

    if input_file.lower().endswith(".json"):
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(scans_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logging.info(f"Criteria JSON loaded and saved to {scans_path}")
    elif input_file.lower().endswith((".pdf", ".docx")):
        extractor = CriteriaExtractor(input_file, str(scans_path))
        extractor.process_file()
        logging.info(f"Criteria extracted from {input_file}")
    else:
        raise ValueError("Unsupported file type: must be .pdf, .docx or .json")

    return scans_path


def evaluate_document_content(vector_manager, doc_path):
    """Step 3: Evaluate a document against all criteria using the ContentEvaluator."""
    print("\n=== Step 3: Evaluate Document Content ===")
    logging.info("Evaluating document content...")
    evaluator = ContentEvaluator()
    evaluator.vector_manager = vector_manager

    docs = vector_manager.load_documents([doc_path])
    for i, doc in enumerate(docs):
        doc.metadata["chunk_index"] = i + 1

    evaluator.current_document_chunks = docs
    evaluator.set_documents_for_rag(docs)

    evaluator.evaluate_all(document_chunks=docs, k_doc=10, k_kb=5)
    result_json = evaluator.generate_json_output()

    cfg = load_config()
    output_path = resolve_project_path(
        cfg.get("evaluation", {}).get("evaluation_json_path"),
        "data/evaluation/evaluation_results.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2)
    logging.info(f"Evaluation results saved to {output_path}")
    return output_path


def generate_pdf_report():
    """Step 4: Generate PDF report from evaluation JSON using ReportManager."""
    print("\n=== Step 4: Generate PDF report ===")
    logging.info("Generating PDF report...")
    cfg = load_config()
    eval_json_path = resolve_project_path(
        cfg.get("evaluation", {}).get("evaluation_json_path"),
        "data/evaluation/evaluation_results.json"
    )
    eval_report_path = resolve_project_path(
        cfg.get("evaluation", {}).get("evaluation_report_path"),
        "data/evaluation/evaluation_report.pdf"
    )
    eval_report_path.parent.mkdir(parents=True, exist_ok=True)

    report_manager = ReportManager(str(eval_json_path))
    report_manager.generate_pdf_report(str(eval_report_path))
    logging.info(f"PDF report generated at {eval_report_path}")


# -------------------- MAIN EXECUTION --------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("=== Unit Evaluator EEDA: Main Workflow ===")

    # Step 1: Build KB
    kb_input = input("Enter KB document file paths (comma separated): ").strip()
    kb_paths = [p.strip() for p in kb_input.split(",") if p.strip()]
    vector_manager = build_knowledge_base(kb_paths)

    # Step 2: Load or Extract criteria
    criteria_file = input("Enter criteria file path (.pdf, .docx, or .json): ").strip()
    load_or_extract_criteria(criteria_file)

    # Step 3: Evaluate document
    doc_to_eval = input("Enter document file path to evaluate: ").strip()
    evaluate_document_content(vector_manager, doc_to_eval)

    # Step 4: Generate PDF report
    generate_pdf_report()
    print("\n=== All steps completed successfully! ===")


if __name__ == "__main__":
    main()
