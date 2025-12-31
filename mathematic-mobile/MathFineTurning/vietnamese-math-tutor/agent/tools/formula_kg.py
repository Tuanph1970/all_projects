"""
Knowledge Graph enhanced Formula Database for Vietnamese Grade 12 Math Tutor.

Extends the basic formula database with:
- Explicit relationship types between formulas
- Multi-hop traversal for related concepts
- Prerequisite and application chains
- Concept hierarchy navigation
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.logger import get_logger
from agent.tools.formula_db import FormulaDatabase, Formula, SearchResult

logger = get_logger("formula_kg")


class RelationType(Enum):
    """Types of relationships between mathematical concepts."""
    # Hierarchical relationships
    IS_SPECIAL_CASE_OF = "is_special_case_of"       # e.g., definite integral IS_SPECIAL_CASE_OF integral
    GENERALIZES = "generalizes"                      # inverse of IS_SPECIAL_CASE_OF
    IS_PART_OF = "is_part_of"                       # e.g., chain rule IS_PART_OF differentiation
    CONTAINS = "contains"                            # inverse of IS_PART_OF

    # Dependency relationships
    REQUIRES = "requires"                            # prerequisite knowledge
    ENABLES = "enables"                              # inverse - what this enables
    DERIVES_FROM = "derives_from"                    # mathematical derivation source
    LEADS_TO = "leads_to"                           # inverse of DERIVES_FROM

    # Application relationships
    APPLIES_TO = "applies_to"                        # formula applies to problem type
    USED_IN = "used_in"                             # e.g., derivative USED_IN optimization
    SOLVES = "solves"                               # formula solves problem type

    # Equivalence and similarity
    EQUIVALENT_TO = "equivalent_to"                  # mathematically equivalent
    SIMILAR_TO = "similar_to"                       # similar structure/pattern
    INVERSE_OF = "inverse_of"                       # e.g., derivative INVERSE_OF integral

    # Transformation relationships
    TRANSFORMS_TO = "transforms_to"                  # algebraic transformation
    SIMPLIFIES_TO = "simplifies_to"                 # simplification relationship


@dataclass
class KGRelationship:
    """A relationship between two formulas/concepts in the KG."""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0  # Strength of relationship (0-1)
    description: str = ""
    description_vi: str = ""
    bidirectional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type.value,
            "weight": self.weight,
            "description": self.description,
            "description_vi": self.description_vi,
            "bidirectional": self.bidirectional,
        }


@dataclass
class KGNode:
    """A node in the Knowledge Graph representing a formula or concept."""
    id: str
    formula: Optional[Formula]
    node_type: str  # "formula", "concept", "topic", "problem_type"
    outgoing_edges: List[KGRelationship] = field(default_factory=list)
    incoming_edges: List[KGRelationship] = field(default_factory=list)

    @property
    def all_related_ids(self) -> Set[str]:
        """Get all directly related node IDs."""
        related = set()
        for edge in self.outgoing_edges:
            related.add(edge.target_id)
        for edge in self.incoming_edges:
            related.add(edge.source_id)
        return related


@dataclass
class KGPath:
    """A path through the knowledge graph."""
    nodes: List[str]
    relationships: List[KGRelationship]
    total_weight: float

    def __str__(self) -> str:
        path_str = self.nodes[0]
        for i, rel in enumerate(self.relationships):
            path_str += f" --[{rel.relation_type.value}]--> {self.nodes[i+1]}"
        return path_str


class FormulaKnowledgeGraph:
    """
    Knowledge Graph for mathematical formulas.

    Provides:
    - Multi-hop relationship traversal
    - Prerequisite chain discovery
    - Application chain discovery
    - Concept similarity search
    - Learning path generation
    """

    # Inverse relationship mappings
    INVERSE_RELATIONS = {
        RelationType.IS_SPECIAL_CASE_OF: RelationType.GENERALIZES,
        RelationType.GENERALIZES: RelationType.IS_SPECIAL_CASE_OF,
        RelationType.IS_PART_OF: RelationType.CONTAINS,
        RelationType.CONTAINS: RelationType.IS_PART_OF,
        RelationType.REQUIRES: RelationType.ENABLES,
        RelationType.ENABLES: RelationType.REQUIRES,
        RelationType.DERIVES_FROM: RelationType.LEADS_TO,
        RelationType.LEADS_TO: RelationType.DERIVES_FROM,
        RelationType.INVERSE_OF: RelationType.INVERSE_OF,
        RelationType.EQUIVALENT_TO: RelationType.EQUIVALENT_TO,
        RelationType.SIMILAR_TO: RelationType.SIMILAR_TO,
    }

    def __init__(self, formula_db: Optional[FormulaDatabase] = None):
        """
        Initialize the Knowledge Graph.

        Args:
            formula_db: Existing formula database to build KG from
        """
        self.formula_db = formula_db or FormulaDatabase()
        self.nodes: Dict[str, KGNode] = {}
        self.relationships: List[KGRelationship] = []

        # Indices for fast lookup
        self.by_relation_type: Dict[RelationType, List[KGRelationship]] = defaultdict(list)
        self.adjacency_list: Dict[str, Dict[str, List[KGRelationship]]] = defaultdict(lambda: defaultdict(list))

        # Build KG from formula database
        self._build_knowledge_graph()
        logger.info(f"Knowledge Graph built with {len(self.nodes)} nodes and {len(self.relationships)} relationships")

    def _build_knowledge_graph(self) -> None:
        """Build the knowledge graph from the formula database."""
        # Create nodes for all formulas
        for formula_id, formula in self.formula_db.formulas.items():
            self.nodes[formula_id] = KGNode(
                id=formula_id,
                formula=formula,
                node_type="formula",
            )

        # Create concept nodes for categories and subcategories
        for category in self.formula_db.by_category.keys():
            concept_id = f"concept_{category}"
            self.nodes[concept_id] = KGNode(
                id=concept_id,
                formula=None,
                node_type="concept",
            )

        # Build relationships from formula metadata
        self._build_relationships_from_formulas()

        # Build relationships from KG definition file if exists
        self._load_kg_definitions()

        # Auto-generate implicit relationships
        self._generate_implicit_relationships()

    def _build_relationships_from_formulas(self) -> None:
        """Build relationships from formula 'related' fields."""
        for formula_id, formula in self.formula_db.formulas.items():
            # Related formulas become SIMILAR_TO relationships
            for related_id in formula.related:
                if related_id in self.formula_db.formulas:
                    self._add_relationship(KGRelationship(
                        source_id=formula_id,
                        target_id=related_id,
                        relation_type=RelationType.SIMILAR_TO,
                        weight=0.8,
                        bidirectional=True,
                    ))

            # Category membership
            concept_id = f"concept_{formula.category}"
            if concept_id in self.nodes:
                self._add_relationship(KGRelationship(
                    source_id=formula_id,
                    target_id=concept_id,
                    relation_type=RelationType.IS_PART_OF,
                    weight=1.0,
                ))

    def _load_kg_definitions(self) -> None:
        """Load explicit KG relationship definitions from file."""
        kg_file = self.formula_db.data_dir / "knowledge_graph.json"
        if not kg_file.exists():
            logger.info("No knowledge_graph.json found, using auto-generated relationships")
            return

        try:
            with open(kg_file, 'r', encoding='utf-8') as f:
                kg_data = json.load(f)

            for rel_data in kg_data.get("relationships", []):
                try:
                    rel_type = RelationType(rel_data["type"])
                    self._add_relationship(KGRelationship(
                        source_id=rel_data["source"],
                        target_id=rel_data["target"],
                        relation_type=rel_type,
                        weight=rel_data.get("weight", 1.0),
                        description=rel_data.get("description", ""),
                        description_vi=rel_data.get("description_vi", ""),
                        bidirectional=rel_data.get("bidirectional", False),
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid relationship definition: {e}")

            logger.info(f"Loaded {len(kg_data.get('relationships', []))} explicit relationships")

        except Exception as e:
            logger.error(f"Failed to load knowledge_graph.json: {e}")

    def _generate_implicit_relationships(self) -> None:
        """Auto-generate relationships based on formula patterns."""
        formulas = list(self.formula_db.formulas.values())

        for i, formula1 in enumerate(formulas):
            for formula2 in formulas[i+1:]:
                # Same subcategory = SIMILAR_TO
                if (formula1.category == formula2.category and
                    formula1.subcategory == formula2.subcategory):
                    self._add_relationship(KGRelationship(
                        source_id=formula1.id,
                        target_id=formula2.id,
                        relation_type=RelationType.SIMILAR_TO,
                        weight=0.6,
                        bidirectional=True,
                    ))

                # Derivative-Integral pairs = INVERSE_OF
                if ("derivative" in formula1.id.lower() and "integral" in formula2.id.lower() or
                    "integral" in formula1.id.lower() and "derivative" in formula2.id.lower()):
                    if formula1.category == formula2.category:
                        self._add_relationship(KGRelationship(
                            source_id=formula1.id,
                            target_id=formula2.id,
                            relation_type=RelationType.INVERSE_OF,
                            weight=0.9,
                            bidirectional=True,
                        ))

        # Prerequisites based on keywords
        prereq_map = {
            "integral": ["derivative", "limit"],
            "derivative": ["limit", "function"],
            "optimization": ["derivative", "critical_point"],
            "volume": ["integral", "area"],
            "probability": ["combination", "permutation"],
        }

        for formula in formulas:
            for keyword, prereqs in prereq_map.items():
                if keyword in formula.id.lower() or keyword in " ".join(formula.keywords).lower():
                    for prereq in prereqs:
                        # Find formulas matching prereq
                        for other_formula in formulas:
                            if prereq in other_formula.id.lower() and other_formula.id != formula.id:
                                self._add_relationship(KGRelationship(
                                    source_id=formula.id,
                                    target_id=other_formula.id,
                                    relation_type=RelationType.REQUIRES,
                                    weight=0.7,
                                ))

    def _add_relationship(self, rel: KGRelationship) -> None:
        """Add a relationship to the graph."""
        # Check if relationship already exists
        for existing in self.adjacency_list[rel.source_id][rel.target_id]:
            if existing.relation_type == rel.relation_type:
                return  # Duplicate, skip

        self.relationships.append(rel)
        self.by_relation_type[rel.relation_type].append(rel)
        self.adjacency_list[rel.source_id][rel.target_id].append(rel)

        # Update node edges
        if rel.source_id in self.nodes:
            self.nodes[rel.source_id].outgoing_edges.append(rel)
        if rel.target_id in self.nodes:
            self.nodes[rel.target_id].incoming_edges.append(rel)

        # Add inverse relationship if bidirectional
        if rel.bidirectional:
            inverse_type = self.INVERSE_RELATIONS.get(rel.relation_type, rel.relation_type)
            inverse_rel = KGRelationship(
                source_id=rel.target_id,
                target_id=rel.source_id,
                relation_type=inverse_type,
                weight=rel.weight,
                description=rel.description,
                description_vi=rel.description_vi,
                bidirectional=False,  # Don't recurse
            )
            self.relationships.append(inverse_rel)
            self.by_relation_type[inverse_type].append(inverse_rel)
            self.adjacency_list[rel.target_id][rel.source_id].append(inverse_rel)

    def get_related(
        self,
        formula_id: str,
        relation_types: Optional[List[RelationType]] = None,
        max_depth: int = 1,
    ) -> List[Tuple[str, KGRelationship]]:
        """
        Get related formulas via specific relationship types.

        Args:
            formula_id: Source formula ID
            relation_types: Filter by relationship types (None for all)
            max_depth: Maximum traversal depth

        Returns:
            List of (formula_id, relationship) tuples
        """
        if formula_id not in self.nodes:
            return []

        results = []
        visited = {formula_id}
        current_level = [(formula_id, None)]

        for depth in range(max_depth):
            next_level = []
            for node_id, _ in current_level:
                for target_id, rels in self.adjacency_list[node_id].items():
                    if target_id in visited:
                        continue
                    for rel in rels:
                        if relation_types is None or rel.relation_type in relation_types:
                            results.append((target_id, rel))
                            next_level.append((target_id, rel))
                            visited.add(target_id)

            current_level = next_level
            if not current_level:
                break

        return results

    def find_prerequisites(self, formula_id: str, max_depth: int = 3) -> List[KGPath]:
        """
        Find prerequisite knowledge paths for a formula.

        Args:
            formula_id: Target formula
            max_depth: Maximum chain length

        Returns:
            List of prerequisite paths
        """
        prereq_types = [RelationType.REQUIRES, RelationType.DERIVES_FROM]
        return self._find_paths_by_type(formula_id, prereq_types, max_depth, reverse=True)

    def find_applications(self, formula_id: str, max_depth: int = 3) -> List[KGPath]:
        """
        Find application paths for a formula.

        Args:
            formula_id: Source formula
            max_depth: Maximum chain length

        Returns:
            List of application paths
        """
        app_types = [RelationType.ENABLES, RelationType.LEADS_TO, RelationType.USED_IN, RelationType.APPLIES_TO]
        return self._find_paths_by_type(formula_id, app_types, max_depth, reverse=False)

    def _find_paths_by_type(
        self,
        start_id: str,
        relation_types: List[RelationType],
        max_depth: int,
        reverse: bool = False,
    ) -> List[KGPath]:
        """Find paths following specific relationship types."""
        paths = []
        visited = {start_id}

        def dfs(current_id: str, current_path: List[str], current_rels: List[KGRelationship], depth: int):
            if depth >= max_depth:
                return

            node = self.nodes.get(current_id)
            if not node:
                return

            edges = node.incoming_edges if reverse else node.outgoing_edges
            for edge in edges:
                next_id = edge.source_id if reverse else edge.target_id

                if edge.relation_type in relation_types and next_id not in visited:
                    new_path = current_path + [next_id]
                    new_rels = current_rels + [edge]
                    weight = sum(r.weight for r in new_rels) / len(new_rels)

                    paths.append(KGPath(
                        nodes=new_path,
                        relationships=new_rels,
                        total_weight=weight,
                    ))

                    visited.add(next_id)
                    dfs(next_id, new_path, new_rels, depth + 1)
                    visited.remove(next_id)

        dfs(start_id, [start_id], [], 0)

        # Sort by weight
        paths.sort(key=lambda p: p.total_weight, reverse=True)
        return paths

    def find_similar(self, formula_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find similar formulas using graph structure.

        Args:
            formula_id: Source formula
            top_k: Number of results

        Returns:
            List of (formula_id, similarity_score) tuples
        """
        if formula_id not in self.nodes:
            return []

        similarity_types = [
            RelationType.SIMILAR_TO,
            RelationType.EQUIVALENT_TO,
            RelationType.IS_SPECIAL_CASE_OF,
            RelationType.GENERALIZES,
        ]

        # Get direct similar formulas
        related = self.get_related(formula_id, similarity_types, max_depth=2)

        # Calculate similarity scores
        scores = {}
        for target_id, rel in related:
            if target_id.startswith("concept_"):
                continue  # Skip concept nodes
            base_score = rel.weight
            if rel.relation_type == RelationType.EQUIVALENT_TO:
                base_score *= 1.2
            elif rel.relation_type == RelationType.SIMILAR_TO:
                base_score *= 1.0
            else:
                base_score *= 0.8

            scores[target_id] = max(scores.get(target_id, 0), base_score)

        # Sort and return top_k
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]

    def get_learning_path(
        self,
        target_formula_id: str,
        known_formulas: Optional[Set[str]] = None,
    ) -> List[str]:
        """
        Generate a learning path to understand a formula.

        Args:
            target_formula_id: Formula to learn
            known_formulas: Already known formulas

        Returns:
            Ordered list of formula IDs to learn
        """
        if known_formulas is None:
            known_formulas = set()

        if target_formula_id in known_formulas:
            return []

        # Find all prerequisites
        prereqs = self.find_prerequisites(target_formula_id, max_depth=5)

        # Build dependency graph
        all_prereqs = set()
        for path in prereqs:
            all_prereqs.update(path.nodes[1:])  # Exclude target

        # Filter out known formulas and concept nodes
        to_learn = [
            f_id for f_id in all_prereqs
            if f_id not in known_formulas and not f_id.startswith("concept_")
        ]

        # Topological sort based on dependencies
        learning_path = self._topological_sort(to_learn, target_formula_id)

        return learning_path + [target_formula_id]

    def _topological_sort(self, formula_ids: List[str], target: str) -> List[str]:
        """Topological sort of formulas based on prerequisites."""
        # Simple sort by prerequisite count
        prereq_counts = {}
        for f_id in formula_ids:
            prereqs = self.get_related(f_id, [RelationType.REQUIRES], max_depth=1)
            prereq_counts[f_id] = len([p for p, _ in prereqs if p in formula_ids])

        sorted_ids = sorted(formula_ids, key=lambda x: prereq_counts.get(x, 0))
        return sorted_ids

    def query(
        self,
        query: str,
        include_related: bool = True,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph with natural language.

        Args:
            query: Natural language query
            include_related: Include related formulas
            max_hops: Maximum relationship hops

        Returns:
            Query results with formulas and relationships
        """
        # Search base formula database
        search_results = self.formula_db.search(query, max_results=3)

        results = {
            "direct_matches": [],
            "related_formulas": [],
            "prerequisites": [],
            "applications": [],
            "learning_path": [],
        }

        for sr in search_results:
            formula = sr.formula
            results["direct_matches"].append({
                "id": formula.id,
                "name": formula.name_vi,
                "formula": formula.formula,
                "score": sr.relevance_score,
            })

            if include_related:
                # Get related formulas
                similar = self.find_similar(formula.id, top_k=3)
                for sim_id, sim_score in similar:
                    if sim_id in self.formula_db.formulas:
                        sim_formula = self.formula_db.formulas[sim_id]
                        results["related_formulas"].append({
                            "id": sim_id,
                            "name": sim_formula.name_vi,
                            "formula": sim_formula.formula,
                            "similarity": sim_score,
                        })

                # Get prerequisites
                prereq_paths = self.find_prerequisites(formula.id, max_depth=max_hops)
                for path in prereq_paths[:3]:
                    results["prerequisites"].append({
                        "path": str(path),
                        "formulas": path.nodes,
                        "weight": path.total_weight,
                    })

                # Get applications
                app_paths = self.find_applications(formula.id, max_depth=max_hops)
                for path in app_paths[:3]:
                    results["applications"].append({
                        "path": str(path),
                        "formulas": path.nodes,
                        "weight": path.total_weight,
                    })

        # Generate learning path for first match
        if search_results:
            learning_path = self.get_learning_path(search_results[0].formula.id)
            results["learning_path"] = learning_path

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get KG statistics."""
        relation_counts = {rt.value: 0 for rt in RelationType}
        for rel in self.relationships:
            relation_counts[rel.relation_type.value] += 1

        return {
            "total_nodes": len(self.nodes),
            "formula_nodes": len([n for n in self.nodes.values() if n.node_type == "formula"]),
            "concept_nodes": len([n for n in self.nodes.values() if n.node_type == "concept"]),
            "total_relationships": len(self.relationships),
            "relationships_by_type": relation_counts,
            "avg_edges_per_node": len(self.relationships) / len(self.nodes) if self.nodes else 0,
        }


# Tool interface for agent
def formula_kg_tool(
    action: str,
    formula_id: str = "",
    query: str = "",
    max_depth: int = 2,
    relation_types: Optional[List[str]] = None,
    language: str = "vi",
) -> Dict[str, Any]:
    """
    Knowledge Graph enhanced formula tool for the math agent.

    Args:
        action: Action to perform (query, get_related, find_prerequisites,
                find_applications, find_similar, get_learning_path, stats)
        formula_id: Formula ID for single-formula operations
        query: Natural language query
        max_depth: Maximum traversal depth
        relation_types: Filter relationship types
        language: Output language

    Returns:
        Dictionary with results
    """
    kg = FormulaKnowledgeGraph()

    try:
        if action == "query":
            results = kg.query(query, include_related=True, max_hops=max_depth)
            return {
                "success": True,
                "action": "query",
                "query": query,
                "results": results,
            }

        elif action == "get_related":
            rel_types = None
            if relation_types:
                rel_types = [RelationType(rt) for rt in relation_types]
            related = kg.get_related(formula_id, rel_types, max_depth)
            return {
                "success": True,
                "action": "get_related",
                "formula_id": formula_id,
                "related": [
                    {"id": r_id, "relation": rel.relation_type.value, "weight": rel.weight}
                    for r_id, rel in related
                ],
            }

        elif action == "find_prerequisites":
            paths = kg.find_prerequisites(formula_id, max_depth)
            return {
                "success": True,
                "action": "find_prerequisites",
                "formula_id": formula_id,
                "prerequisites": [
                    {"path": str(p), "nodes": p.nodes, "weight": p.total_weight}
                    for p in paths
                ],
            }

        elif action == "find_applications":
            paths = kg.find_applications(formula_id, max_depth)
            return {
                "success": True,
                "action": "find_applications",
                "formula_id": formula_id,
                "applications": [
                    {"path": str(p), "nodes": p.nodes, "weight": p.total_weight}
                    for p in paths
                ],
            }

        elif action == "find_similar":
            similar = kg.find_similar(formula_id, top_k=5)
            return {
                "success": True,
                "action": "find_similar",
                "formula_id": formula_id,
                "similar": [
                    {"id": s_id, "similarity": score}
                    for s_id, score in similar
                ],
            }

        elif action == "get_learning_path":
            path = kg.get_learning_path(formula_id)
            formulas_info = []
            for f_id in path:
                if f_id in kg.formula_db.formulas:
                    f = kg.formula_db.formulas[f_id]
                    formulas_info.append({
                        "id": f_id,
                        "name": f.name_vi if language == "vi" else f.name,
                        "formula": f.formula,
                    })
            return {
                "success": True,
                "action": "get_learning_path",
                "target": formula_id,
                "learning_path": path,
                "formulas": formulas_info,
            }

        elif action == "stats":
            return {
                "success": True,
                "action": "stats",
                "statistics": kg.get_statistics(),
            }

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Available: query, get_related, "
                        f"find_prerequisites, find_applications, find_similar, get_learning_path, stats",
            }

    except Exception as e:
        logger.error(f"Formula KG tool error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("Formula Knowledge Graph Test")
    print("=" * 60)

    # Create KG
    kg = FormulaKnowledgeGraph()

    # Statistics
    print("\n1. Knowledge Graph Statistics:")
    stats = kg.get_statistics()
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Formula nodes: {stats['formula_nodes']}")
    print(f"   Concept nodes: {stats['concept_nodes']}")
    print(f"   Total relationships: {stats['total_relationships']}")
    print(f"   Avg edges per node: {stats['avg_edges_per_node']:.2f}")

    # Query
    print("\n2. Query: 'đạo hàm'")
    results = kg.query("đạo hàm")
    print(f"   Direct matches: {len(results['direct_matches'])}")
    for match in results['direct_matches'][:2]:
        print(f"     - {match['name']}: {match['formula']}")

    # Related formulas
    print("\n3. Find Similar to calc_001:")
    similar = kg.find_similar("calc_001", top_k=3)
    for sim_id, score in similar:
        print(f"   - {sim_id}: {score:.2f}")

    # Learning path
    print("\n4. Learning Path for calc_010 (integral):")
    path = kg.get_learning_path("calc_010")
    for f_id in path:
        if f_id in kg.formula_db.formulas:
            f = kg.formula_db.formulas[f_id]
            print(f"   {f_id}: {f.name_vi}")

    # Tool interface
    print("\n5. Tool Interface Test:")
    result = formula_kg_tool(action="stats")
    print(f"   Success: {result['success']}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
