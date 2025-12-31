#!/usr/bin/env python3
"""
Script to import textbook data into the Vietnamese Math Tutor system.

This script shows how to:
1. Add problems to the fine-tuning dataset
2. Enrich formula database with examples
3. Update Knowledge Graph with new relationships

Usage:
    python scripts/import_textbook_data.py --source textbook_data.json
    python scripts/import_textbook_data.py --validate-only
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: Path):
    """Save JSON file with pretty formatting."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved: {file_path}")


def validate_problem(problem: Dict[str, Any]) -> List[str]:
    """Validate a problem entry."""
    errors = []
    required_fields = ["id", "question", "solution", "answer", "topic"]

    for field in required_fields:
        if field not in problem:
            errors.append(f"Missing required field: {field}")

    if "topic" in problem:
        valid_topics = ["calculus", "trigonometry", "geometry", "probability"]
        if problem["topic"] not in valid_topics:
            errors.append(f"Invalid topic: {problem['topic']}. Must be one of {valid_topics}")

    if "difficulty" in problem:
        valid_difficulties = ["easy", "medium", "hard"]
        if problem["difficulty"] not in valid_difficulties:
            errors.append(f"Invalid difficulty: {problem['difficulty']}")

    return errors


def add_problems_to_finetuning(
    new_problems: List[Dict[str, Any]],
    dataset_path: Path,
    dry_run: bool = False
) -> int:
    """
    Add new problems to the fine-tuning dataset.

    Args:
        new_problems: List of problem dictionaries
        dataset_path: Path to grade12_math_dataset.json
        dry_run: If True, only validate without saving

    Returns:
        Number of problems added
    """
    print("\n" + "="*60)
    print("Adding problems to fine-tuning dataset")
    print("="*60)

    # Load existing dataset
    if dataset_path.exists():
        dataset = load_json(dataset_path)
    else:
        dataset = {
            "metadata": {
                "version": "2.1.0",
                "grade": 12,
                "total_problems": 0
            },
            "problems": []
        }

    existing_ids = {p["id"] for p in dataset["problems"]}
    added_count = 0

    for problem in new_problems:
        # Validate
        errors = validate_problem(problem)
        if errors:
            print(f"⚠ Skipping {problem.get('id', 'unknown')}: {errors}")
            continue

        # Check for duplicates
        if problem["id"] in existing_ids:
            print(f"⚠ Skipping {problem['id']}: Already exists")
            continue

        # Add problem
        dataset["problems"].append(problem)
        existing_ids.add(problem["id"])
        added_count += 1
        print(f"✓ Added: {problem['id']} ({problem['topic']})")

    # Update metadata
    dataset["metadata"]["total_problems"] = len(dataset["problems"])

    # Save
    if not dry_run and added_count > 0:
        save_json(dataset, dataset_path)

    print(f"\nTotal: {added_count} problems added")
    return added_count


def add_examples_to_formulas(
    enrichment_data: List[Dict[str, Any]],
    formulas_dir: Path,
    dry_run: bool = False
) -> int:
    """
    Add example problems to formula database entries.

    Args:
        enrichment_data: List of formula enrichment dictionaries
        formulas_dir: Path to data/formulas directory
        dry_run: If True, only validate without saving

    Returns:
        Number of examples added
    """
    print("\n" + "="*60)
    print("Adding examples to formula database")
    print("="*60)

    # Map formula IDs to their category files
    category_map = {
        "calc": "calculus.json",
        "trig": "trigonometry.json",
        "geom": "geometry.json",
        "prob": "probability.json"
    }

    total_added = 0

    for enrichment in enrichment_data:
        formula_id = enrichment["formula_id"]
        action = enrichment.get("action", "add_examples")

        if action != "add_examples":
            continue

        # Determine category file
        prefix = formula_id.split("_")[0]
        if prefix not in category_map:
            print(f"⚠ Unknown formula prefix: {prefix}")
            continue

        formula_file = formulas_dir / category_map[prefix]
        if not formula_file.exists():
            print(f"⚠ Formula file not found: {formula_file}")
            continue

        # Load formula file
        formula_data = load_json(formula_file)

        # Find and update formula
        formula_found = False
        for formula in formula_data.get("formulas", []):
            if formula.get("id") == formula_id:
                formula_found = True

                # Initialize examples if not exists
                if "examples" not in formula:
                    formula["examples"] = []

                # Add new examples
                existing_example_ids = {e.get("id") for e in formula["examples"]}

                for example in enrichment.get("examples", []):
                    if example.get("id") in existing_example_ids:
                        print(f"  ⚠ Example {example['id']} already exists")
                        continue

                    formula["examples"].append(example)
                    total_added += 1
                    print(f"  ✓ Added example to {formula_id}: {example['id']}")

                break

        if not formula_found:
            print(f"⚠ Formula not found: {formula_id}")
            continue

        # Save updated formula file
        if not dry_run:
            save_json(formula_data, formula_file)

    print(f"\nTotal: {total_added} examples added")
    return total_added


def update_knowledge_graph(
    kg_enrichment: Dict[str, Any],
    kg_path: Path,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Update Knowledge Graph with new relationships and problem types.

    Args:
        kg_enrichment: KG enrichment data
        kg_path: Path to knowledge_graph.json
        dry_run: If True, only validate without saving

    Returns:
        Dictionary with counts of added items
    """
    print("\n" + "="*60)
    print("Updating Knowledge Graph")
    print("="*60)

    # Load existing KG
    if kg_path.exists():
        kg_data = load_json(kg_path)
    else:
        kg_data = {
            "metadata": {"version": "1.1.0"},
            "relationships": [],
            "problem_type_mappings": {}
        }

    counts = {"relationships": 0, "problem_types": 0, "mappings": 0}

    # Add new relationships
    existing_rels = {
        (r["source"], r["target"], r["type"])
        for r in kg_data.get("relationships", [])
    }

    for rel in kg_enrichment.get("new_relationships", []):
        rel_key = (rel["source"], rel["target"], rel["type"])
        if rel_key in existing_rels:
            print(f"  ⚠ Relationship exists: {rel['source']} -> {rel['target']}")
            continue

        kg_data["relationships"].append(rel)
        counts["relationships"] += 1
        print(f"  ✓ Added: {rel['source']} --[{rel['type']}]--> {rel['target']}")

    # Add problem type mappings
    for prob_type, formulas in kg_enrichment.get("problem_type_mappings", {}).items():
        if prob_type not in kg_data.get("problem_type_mappings", {}):
            kg_data["problem_type_mappings"][prob_type] = formulas
            counts["mappings"] += 1
            print(f"  ✓ Added mapping: {prob_type} -> {formulas}")

    # Save
    if not dry_run and any(counts.values()):
        save_json(kg_data, kg_path)

    print(f"\nTotal: {counts['relationships']} relationships, {counts['mappings']} mappings added")
    return counts


def reindex_vector_store():
    """Re-index formulas in the vector store after updates."""
    print("\n" + "="*60)
    print("Re-indexing vector store")
    print("="*60)

    try:
        from agent.tools.formula_kg import FormulaKnowledgeGraph
        from agent.retrieval import HybridRetriever

        kg = FormulaKnowledgeGraph()
        retriever = HybridRetriever(knowledge_graph=kg)

        doc_count = retriever.index_formulas()
        print(f"✓ Indexed {doc_count} documents")

    except Exception as e:
        print(f"⚠ Re-indexing failed: {e}")
        print("  Run manually: python -c 'from agent.retrieval import create_semantic_search; s = create_semantic_search(); s.index_from_database()'")


def main():
    parser = argparse.ArgumentParser(
        description="Import textbook data into the Vietnamese Math Tutor system"
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Path to textbook data JSON file"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate data without importing"
    )
    parser.add_argument(
        "--skip-reindex",
        action="store_true",
        help="Skip vector store re-indexing"
    )
    parser.add_argument(
        "--use-samples",
        action="store_true",
        help="Use sample data files from data/samples/"
    )

    args = parser.parse_args()

    # Paths
    data_dir = project_root / "data"
    formulas_dir = data_dir / "formulas"
    samples_dir = data_dir / "samples"

    dataset_path = data_dir / "grade12_math_dataset.json"
    kg_path = formulas_dir / "knowledge_graph.json"

    print("="*60)
    print("Vietnamese Math Tutor - Textbook Data Importer")
    print("="*60)

    if args.use_samples:
        # Load sample data
        finetuning_data = load_json(samples_dir / "sample_finetuning_data.json")
        enrichment_data = load_json(samples_dir / "sample_formula_enrichment.json")
        kg_enrichment = load_json(samples_dir / "sample_kg_enrichment.json")

        # Import fine-tuning problems
        add_problems_to_finetuning(
            finetuning_data.get("problems", []),
            dataset_path,
            dry_run=args.validate_only
        )

        # Import formula examples
        add_examples_to_formulas(
            enrichment_data.get("formula_updates", []),
            formulas_dir,
            dry_run=args.validate_only
        )

        # Import KG relationships
        update_knowledge_graph(
            kg_enrichment,
            kg_path,
            dry_run=args.validate_only
        )

    elif args.source:
        # Load custom data file
        source_data = load_json(Path(args.source))

        if "problems" in source_data:
            add_problems_to_finetuning(
                source_data["problems"],
                dataset_path,
                dry_run=args.validate_only
            )

        if "formula_updates" in source_data:
            add_examples_to_formulas(
                source_data["formula_updates"],
                formulas_dir,
                dry_run=args.validate_only
            )

        if "new_relationships" in source_data or "problem_type_mappings" in source_data:
            update_knowledge_graph(
                source_data,
                kg_path,
                dry_run=args.validate_only
            )

    else:
        print("Please specify --source <file.json> or --use-samples")
        return

    # Re-index vector store
    if not args.validate_only and not args.skip_reindex:
        reindex_vector_store()

    print("\n" + "="*60)
    print("Import complete!")
    print("="*60)


if __name__ == "__main__":
    main()
