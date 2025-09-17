import sys
import os
from pathlib import Path
import json

# Import project modules
from rag.vector_store_manager import VectorStoreManager
from evaluation.criteria_extractor import CriteriaExtractor
from rag.content_evaluator import ContentEvaluator


def build_knowledge_base():
    """Step 1: Build and load the persistent Knowledge Base vector store."""
    print("\n=== Step 1: Build Knowledge Base Vector Store ===")
    kb_files = input("Enter KB document file paths (comma separated): ").strip()
    kb_file_paths = [p.strip() for p in kb_files.split(",") if p.strip()]

    manager = VectorStoreManager()
    docs = manager.load_documents(kb_file_paths)
    print(f"Loaded {len(docs)} chunks for KB.")

    # Build persistent vector store
    manager.build_vector_store(docs)
    print("Knowledge base vector store built and persisted.")

    # Load the KB store into memory
    manager.load_vector_store()
    print("Knowledge base vector store loaded into memory.")
    return manager


def load_or_extract_criteria():
    """Step 2: Load criteria from JSON or extract from PDF/DOCX."""
    print("\n=== Step 2: Load or Extract Criteria ===")
    input_file = input("Enter criteria file path (.pdf, .docx or .json): ").strip()
    output_file = Path(__file__).parents[1] / "scans.json"

    if input_file.lower().endswith(".json"):
        # Simply copy/load the JSON
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Criteria JSON loaded and saved to {output_file}")
    elif input_file.lower().endswith((".pdf", ".docx")):
        # Use extractor
        extractor = CriteriaExtractor(input_file, str(output_file))
        extractor.process_file()
        print(f"Criteria extracted from {input_file} and saved to {output_file}")
    else:
        raise ValueError("Unsupported file type. Please provide a .pdf, .docx or .json file.")

    return output_file


def evaluate_document_content(vector_manager):
    """Step 3: Evaluate a document against all criteria using the ContentEvaluator."""
    print("\n=== Step 3: Evaluate Document Content ===")
    evaluator = ContentEvaluator()

    # Assign KB vector store to evaluator
    evaluator.vector_manager = vector_manager
    evaluator.vector_manager.vector_store  # ensure the store is loaded

    # Load document and create temporary vector store
    doc_path = input("Enter document file path to evaluate: ").strip()
    docs = evaluator.vector_manager.load_documents([doc_path])
    for i, doc in enumerate(docs):
        doc.metadata["chunk_index"] = i + 1

    evaluator.current_document_chunks = docs
    print(f"Loaded {len(docs)} chunks for evaluation.")

    # Build temporary vector store for this document
    temp_store = evaluator._create_temp_vector_store(docs)

    # Ask user for batch size
    n_criteria = int(input("Enter number of criteria to evaluate per batch (default 3): ") or 3)

    # Evaluate all scans and criteria sequentially
    print(f"\nEvaluating all scans and criteria in batches of {n_criteria}...")
    evaluator.evaluate_all(document_chunks=docs, k_doc=10, k_kb=5, n_criteria=n_criteria)

    # Generate JSON output
    print("\nGenerating JSON output...")
    final_json = evaluator.generate_json_output()
    output_file = Path(__file__).parents[1] / "evaluation_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2)
    print(f"Evaluation results saved to {output_file}")


def main():
    """Main workflow: build KB, load/extract criteria, evaluate document, and generate output."""
    print("=== Unit Evaluator EEDA: Main Workflow ===")
    print("This script will guide you through the full process.\n")

    # Step 1: Build KB
    vector_manager = build_knowledge_base()

    # Step 2: Load or Extract criteria
    load_or_extract_criteria()

    # Step 3: Evaluate document
    evaluate_document_content(vector_manager)

    print("\n=== All steps completed! ===")


if __name__ == "__main__":
    main()
