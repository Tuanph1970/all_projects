"""
Formula Database tool for Vietnamese Grade 12 Math Tutor.

Provides formula retrieval and lookup functionality for:
- Calculus formulas (derivatives, integrals, limits)
- Geometry formulas (areas, volumes, coordinates)
- Trigonometry formulas (identities, equations)
- Probability and statistics formulas
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.logger import get_logger

logger = get_logger("formula_db")


class FormulaCategory(Enum):
    """Categories of mathematical formulas."""
    CALCULUS = "calculus"
    GEOMETRY = "geometry"
    TRIGONOMETRY = "trigonometry"
    PROBABILITY = "probability"
    ALL = "all"


@dataclass
class Formula:
    """Represents a mathematical formula."""
    id: str
    name: str
    name_vi: str
    category: str
    subcategory: str
    formula: str
    latex: str
    description: str
    description_vi: str
    variables: Dict[str, str]
    examples: List[Dict[str, str]]
    related: List[str]
    keywords: List[str]
    keywords_vi: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "name_vi": self.name_vi,
            "category": self.category,
            "subcategory": self.subcategory,
            "formula": self.formula,
            "latex": self.latex,
            "description": self.description,
            "description_vi": self.description_vi,
            "variables": self.variables,
            "examples": self.examples,
            "related": self.related,
            "keywords": self.keywords,
            "keywords_vi": self.keywords_vi,
        }

    def format_for_display(self, language: str = "vi") -> str:
        """Format formula for display."""
        if language == "vi":
            name = self.name_vi
            desc = self.description_vi
        else:
            name = self.name
            desc = self.description

        output = f"**{name}**\n"
        output += f"Formula: {self.formula}\n"
        output += f"LaTeX: ${self.latex}$\n"
        output += f"Description: {desc}\n"

        if self.variables:
            output += "Variables:\n"
            for var, meaning in self.variables.items():
                output += f"  - {var}: {meaning}\n"

        if self.examples:
            output += "Examples:\n"
            for ex in self.examples[:2]:  # Show max 2 examples
                output += f"  - {ex.get('problem', '')}\n"
                output += f"    Solution: {ex.get('solution', '')}\n"

        return output


@dataclass
class SearchResult:
    """Result of a formula search."""
    formula: Formula
    relevance_score: float
    match_type: str  # "exact", "keyword", "partial"


class FormulaDatabase:
    """
    Database of mathematical formulas for Grade 12.

    Supports searching by:
    - Category/subcategory
    - Keywords (Vietnamese and English)
    - Formula ID
    - Natural language query
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the formula database.

        Args:
            data_dir: Directory containing formula JSON files
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "formulas"

        self.data_dir = Path(data_dir)
        self.formulas: Dict[str, Formula] = {}
        self.by_category: Dict[str, List[str]] = {}
        self.by_subcategory: Dict[str, List[str]] = {}
        self.keyword_index: Dict[str, List[str]] = {}

        self._load_formulas()
        logger.info(f"Formula database initialized with {len(self.formulas)} formulas")

    def _load_formulas(self) -> None:
        """Load all formula files from data directory."""
        if not self.data_dir.exists():
            logger.warning(f"Formula directory not found: {self.data_dir}")
            return

        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                category = data.get("category", json_file.stem)
                formulas_data = data.get("formulas", [])

                for formula_data in formulas_data:
                    formula = Formula(
                        id=formula_data.get("id", ""),
                        name=formula_data.get("name", ""),
                        name_vi=formula_data.get("name_vi", formula_data.get("name", "")),
                        category=category,
                        subcategory=formula_data.get("subcategory", ""),
                        formula=formula_data.get("formula", ""),
                        latex=formula_data.get("latex", formula_data.get("formula", "")),
                        description=formula_data.get("description", ""),
                        description_vi=formula_data.get("description_vi", formula_data.get("description", "")),
                        variables=formula_data.get("variables", {}),
                        examples=formula_data.get("examples", []),
                        related=formula_data.get("related", []),
                        keywords=formula_data.get("keywords", []),
                        keywords_vi=formula_data.get("keywords_vi", []),
                    )

                    self.formulas[formula.id] = formula
                    self._index_formula(formula)

                logger.info(f"Loaded {len(formulas_data)} formulas from {json_file.name}")

            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")

    def _index_formula(self, formula: Formula) -> None:
        """Index a formula for fast searching."""
        # Index by category
        if formula.category not in self.by_category:
            self.by_category[formula.category] = []
        self.by_category[formula.category].append(formula.id)

        # Index by subcategory
        subcat_key = f"{formula.category}:{formula.subcategory}"
        if subcat_key not in self.by_subcategory:
            self.by_subcategory[subcat_key] = []
        self.by_subcategory[subcat_key].append(formula.id)

        # Index by keywords
        all_keywords = formula.keywords + formula.keywords_vi
        all_keywords.extend([formula.name.lower(), formula.name_vi.lower()])

        for keyword in all_keywords:
            keyword = keyword.lower().strip()
            if keyword:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = []
                if formula.id not in self.keyword_index[keyword]:
                    self.keyword_index[keyword].append(formula.id)

    def get_formula(self, formula_id: str) -> Optional[Formula]:
        """
        Get a formula by ID.

        Args:
            formula_id: The formula ID

        Returns:
            Formula object or None
        """
        return self.formulas.get(formula_id)

    def get_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
    ) -> List[Formula]:
        """
        Get all formulas in a category.

        Args:
            category: Category name (calculus, geometry, trigonometry, probability)
            subcategory: Optional subcategory filter

        Returns:
            List of Formula objects
        """
        category = category.lower()

        if subcategory:
            subcat_key = f"{category}:{subcategory}"
            formula_ids = self.by_subcategory.get(subcat_key, [])
        else:
            formula_ids = self.by_category.get(category, [])

        return [self.formulas[fid] for fid in formula_ids if fid in self.formulas]

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5,
        language: str = "vi",
    ) -> List[SearchResult]:
        """
        Search for formulas by natural language query.

        Args:
            query: Search query (Vietnamese or English)
            category: Optional category filter
            max_results: Maximum number of results
            language: Preferred language for ranking

        Returns:
            List of SearchResult objects sorted by relevance
        """
        query = query.lower().strip()
        results: List[SearchResult] = []

        # Extract keywords from query
        query_words = set(re.findall(r'\w+', query))

        for formula_id, formula in self.formulas.items():
            # Skip if category filter doesn't match
            if category and formula.category.lower() != category.lower():
                continue

            score = 0.0
            match_type = "partial"

            # Check for exact ID match
            if query == formula_id.lower():
                score = 1.0
                match_type = "exact"
            # Check for exact name match
            elif query == formula.name.lower() or query == formula.name_vi.lower():
                score = 0.95
                match_type = "exact"
            else:
                # Keyword matching
                formula_keywords = set(
                    k.lower() for k in formula.keywords + formula.keywords_vi
                )
                formula_keywords.add(formula.name.lower())
                formula_keywords.add(formula.name_vi.lower())

                # Add words from formula description
                desc_words = set(re.findall(r'\w+', formula.description.lower()))
                desc_words_vi = set(re.findall(r'\w+', formula.description_vi.lower()))

                # Calculate overlap
                keyword_overlap = len(query_words & formula_keywords)
                desc_overlap = len(query_words & (desc_words | desc_words_vi))

                if keyword_overlap > 0:
                    score = 0.7 + (0.2 * keyword_overlap / len(query_words))
                    match_type = "keyword"
                elif desc_overlap > 0:
                    score = 0.3 + (0.3 * desc_overlap / len(query_words))
                    match_type = "partial"

                # Boost if query words appear in formula text
                if any(word in formula.formula.lower() for word in query_words):
                    score += 0.1

            if score > 0:
                results.append(SearchResult(
                    formula=formula,
                    relevance_score=score,
                    match_type=match_type,
                ))

        # Sort by relevance score
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:max_results]

    def search_by_keywords(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        max_results: int = 5,
    ) -> List[Formula]:
        """
        Search formulas by specific keywords.

        Args:
            keywords: List of keywords to search
            category: Optional category filter
            max_results: Maximum number of results

        Returns:
            List of matching formulas
        """
        matching_ids: Dict[str, int] = {}

        for keyword in keywords:
            keyword = keyword.lower().strip()

            # Direct keyword match
            if keyword in self.keyword_index:
                for fid in self.keyword_index[keyword]:
                    matching_ids[fid] = matching_ids.get(fid, 0) + 2

            # Partial keyword match
            for indexed_keyword, formula_ids in self.keyword_index.items():
                if keyword in indexed_keyword or indexed_keyword in keyword:
                    for fid in formula_ids:
                        matching_ids[fid] = matching_ids.get(fid, 0) + 1

        # Filter by category if specified
        if category:
            category = category.lower()
            matching_ids = {
                fid: score for fid, score in matching_ids.items()
                if self.formulas.get(fid, Formula("", "", "", "", "", "", "", "", "", {}, [], [], [], [])).category.lower() == category
            }

        # Sort by match count
        sorted_ids = sorted(matching_ids.items(), key=lambda x: x[1], reverse=True)

        return [
            self.formulas[fid]
            for fid, _ in sorted_ids[:max_results]
            if fid in self.formulas
        ]

    def get_related(self, formula_id: str) -> List[Formula]:
        """
        Get related formulas.

        Args:
            formula_id: ID of the formula to find relations for

        Returns:
            List of related formulas
        """
        formula = self.formulas.get(formula_id)
        if not formula:
            return []

        related = []
        for related_id in formula.related:
            if related_id in self.formulas:
                related.append(self.formulas[related_id])

        return related

    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.by_category.keys())

    def get_subcategories(self, category: str) -> List[str]:
        """Get all subcategories for a category."""
        category = category.lower()
        subcats = []
        for key in self.by_subcategory.keys():
            if key.startswith(f"{category}:"):
                subcat = key.split(":", 1)[1]
                if subcat not in subcats:
                    subcats.append(subcat)
        return subcats

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            "total_formulas": len(self.formulas),
            "categories": {},
            "keywords_indexed": len(self.keyword_index),
        }

        for category, formula_ids in self.by_category.items():
            stats["categories"][category] = {
                "count": len(formula_ids),
                "subcategories": [],
            }

            for subcat_key, subcat_ids in self.by_subcategory.items():
                if subcat_key.startswith(f"{category}:"):
                    subcat = subcat_key.split(":", 1)[1]
                    stats["categories"][category]["subcategories"].append({
                        "name": subcat,
                        "count": len(subcat_ids),
                    })

        return stats


# Tool interface for agent
def formula_db_tool(
    action: str,
    query: str = "",
    category: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    formula_id: Optional[str] = None,
    max_results: int = 5,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Formula database tool interface for the math agent.

    Args:
        action: Action to perform (search, get, list_category, get_related, stats)
        query: Search query for "search" action
        category: Category filter
        keywords: List of keywords for keyword search
        formula_id: Formula ID for "get" and "get_related" actions
        max_results: Maximum results to return
        language: Preferred language (vi/en)

    Returns:
        Dictionary with results
    """
    db = FormulaDatabase()

    try:
        if action == "search":
            results = db.search(query, category, max_results, language)
            return {
                "success": True,
                "action": "search",
                "query": query,
                "count": len(results),
                "results": [
                    {
                        "id": r.formula.id,
                        "name": r.formula.name_vi if language == "vi" else r.formula.name,
                        "formula": r.formula.formula,
                        "latex": r.formula.latex,
                        "category": r.formula.category,
                        "relevance": r.relevance_score,
                        "match_type": r.match_type,
                        "description": r.formula.description_vi if language == "vi" else r.formula.description,
                    }
                    for r in results
                ],
            }

        elif action == "get":
            if not formula_id:
                return {
                    "success": False,
                    "error": "formula_id is required for 'get' action",
                }

            formula = db.get_formula(formula_id)
            if formula:
                return {
                    "success": True,
                    "action": "get",
                    "formula": formula.to_dict(),
                    "formatted": formula.format_for_display(language),
                }
            else:
                return {
                    "success": False,
                    "error": f"Formula not found: {formula_id}",
                }

        elif action == "list_category":
            if not category:
                # Return all categories
                return {
                    "success": True,
                    "action": "list_category",
                    "categories": db.get_all_categories(),
                }

            formulas = db.get_by_category(category)
            return {
                "success": True,
                "action": "list_category",
                "category": category,
                "count": len(formulas),
                "formulas": [
                    {
                        "id": f.id,
                        "name": f.name_vi if language == "vi" else f.name,
                        "formula": f.formula,
                        "subcategory": f.subcategory,
                    }
                    for f in formulas
                ],
            }

        elif action == "search_keywords":
            if not keywords:
                return {
                    "success": False,
                    "error": "keywords list is required for 'search_keywords' action",
                }

            formulas = db.search_by_keywords(keywords, category, max_results)
            return {
                "success": True,
                "action": "search_keywords",
                "keywords": keywords,
                "count": len(formulas),
                "results": [
                    {
                        "id": f.id,
                        "name": f.name_vi if language == "vi" else f.name,
                        "formula": f.formula,
                        "latex": f.latex,
                        "category": f.category,
                    }
                    for f in formulas
                ],
            }

        elif action == "get_related":
            if not formula_id:
                return {
                    "success": False,
                    "error": "formula_id is required for 'get_related' action",
                }

            related = db.get_related(formula_id)
            return {
                "success": True,
                "action": "get_related",
                "formula_id": formula_id,
                "count": len(related),
                "related": [
                    {
                        "id": f.id,
                        "name": f.name_vi if language == "vi" else f.name,
                        "formula": f.formula,
                    }
                    for f in related
                ],
            }

        elif action == "stats":
            return {
                "success": True,
                "action": "stats",
                "statistics": db.get_statistics(),
            }

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. "
                        f"Available: search, get, list_category, search_keywords, get_related, stats",
            }

    except Exception as e:
        logger.error(f"Formula DB tool error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    # Test the formula database
    db = FormulaDatabase()

    print("=" * 60)
    print("Formula Database Tool Test")
    print("=" * 60)

    # Get statistics
    print("\n1. Database Statistics:")
    stats = db.get_statistics()
    print(f"   Total formulas: {stats['total_formulas']}")
    for cat, info in stats['categories'].items():
        print(f"   - {cat}: {info['count']} formulas")

    # Search for derivative formulas
    print("\n2. Search: 'đạo hàm' (derivative)")
    results = db.search("đạo hàm", max_results=3)
    for r in results:
        print(f"   - {r.formula.name_vi}: {r.formula.formula} (score: {r.relevance_score:.2f})")

    # Search by category
    print("\n3. Calculus Formulas:")
    calculus = db.get_by_category("calculus")
    for f in calculus[:3]:
        print(f"   - {f.name_vi}: {f.formula}")

    # Get specific formula
    print("\n4. Get Formula by ID:")
    formula = db.get_formula("calc_001")
    if formula:
        print(f"   Name: {formula.name_vi}")
        print(f"   Formula: {formula.formula}")
        print(f"   Description: {formula.description_vi}")

    # Test via tool interface
    print("\n5. Tool Interface Test:")
    tool_result = formula_db_tool("search", query="tích phân", max_results=2)
    print(f"   Search 'tích phân': Found {tool_result['count']} results")
    for r in tool_result.get('results', []):
        print(f"   - {r['name']}: {r['formula']}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
