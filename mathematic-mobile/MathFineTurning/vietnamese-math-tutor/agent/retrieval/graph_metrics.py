"""
Graph metrics and centrality calculations for Knowledge Graph.

Provides PageRank, degree centrality, betweenness centrality, and clustering.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import math

logger = logging.getLogger(__name__)


@dataclass
class NodeMetrics:
    """Metrics for a single graph node."""

    node_id: str
    degree_centrality: float = 0.0
    in_degree: int = 0
    out_degree: int = 0
    pagerank: float = 0.0
    betweenness: float = 0.0
    clustering_coefficient: float = 0.0
    hub_score: float = 0.0
    authority_score: float = 0.0


class GraphMetricsCalculator:
    """
    Calculate various graph metrics for the Knowledge Graph.

    Supports:
    - Degree centrality (in/out)
    - PageRank
    - Betweenness centrality
    - Clustering coefficient
    - HITS (hub/authority scores)
    """

    def __init__(
        self,
        nodes: Dict[str, Any],
        adjacency_list: Dict[str, Dict[str, List[Any]]],
    ):
        """
        Initialize the metrics calculator.

        Args:
            nodes: Dictionary of node_id -> node data
            adjacency_list: Adjacency list representation of the graph
        """
        self.nodes = nodes
        self.adjacency_list = adjacency_list
        self._metrics_cache: Dict[str, NodeMetrics] = {}
        self._pagerank_cache: Dict[str, float] = {}
        self._betweenness_cache: Dict[str, float] = {}

    def get_node_metrics(self, node_id: str) -> NodeMetrics:
        """
        Get all metrics for a node.

        Args:
            node_id: Node ID

        Returns:
            NodeMetrics object
        """
        if node_id in self._metrics_cache:
            return self._metrics_cache[node_id]

        metrics = NodeMetrics(
            node_id=node_id,
            degree_centrality=self.degree_centrality(node_id),
            in_degree=self.in_degree(node_id),
            out_degree=self.out_degree(node_id),
            pagerank=self.pagerank().get(node_id, 0.0),
            betweenness=self.betweenness_centrality().get(node_id, 0.0),
            clustering_coefficient=self.clustering_coefficient(node_id),
        )

        self._metrics_cache[node_id] = metrics
        return metrics

    def in_degree(self, node_id: str) -> int:
        """Calculate in-degree (number of incoming edges)."""
        count = 0
        for source_id, targets in self.adjacency_list.items():
            if node_id in targets:
                count += len(targets[node_id])
        return count

    def out_degree(self, node_id: str) -> int:
        """Calculate out-degree (number of outgoing edges)."""
        if node_id not in self.adjacency_list:
            return 0
        return sum(len(edges) for edges in self.adjacency_list[node_id].values())

    def degree_centrality(self, node_id: str) -> float:
        """
        Calculate degree centrality (normalized).

        Centrality = (in_degree + out_degree) / (2 * (n-1))
        """
        n = len(self.nodes)
        if n <= 1:
            return 0.0

        total_degree = self.in_degree(node_id) + self.out_degree(node_id)
        return total_degree / (2 * (n - 1))

    def pagerank(
        self,
        damping: float = 0.85,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> Dict[str, float]:
        """
        Calculate PageRank for all nodes.

        Args:
            damping: Damping factor (default 0.85)
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance

        Returns:
            Dictionary of node_id -> PageRank score
        """
        if self._pagerank_cache:
            return self._pagerank_cache

        n = len(self.nodes)
        if n == 0:
            return {}

        # Initialize PageRank uniformly
        pr = {node_id: 1.0 / n for node_id in self.nodes}

        # Build reverse adjacency for efficient computation
        incoming = defaultdict(list)
        for source_id, targets in self.adjacency_list.items():
            for target_id in targets:
                incoming[target_id].append(source_id)

        # Power iteration
        for iteration in range(max_iterations):
            new_pr = {}
            max_change = 0.0

            for node_id in self.nodes:
                # Sum of PR contributions from incoming nodes
                incoming_sum = 0.0
                for source_id in incoming[node_id]:
                    out_deg = self.out_degree(source_id)
                    if out_deg > 0:
                        incoming_sum += pr[source_id] / out_deg

                # PageRank formula
                new_pr[node_id] = (1 - damping) / n + damping * incoming_sum

                # Track convergence
                max_change = max(max_change, abs(new_pr[node_id] - pr[node_id]))

            pr = new_pr

            if max_change < tolerance:
                logger.debug(f"PageRank converged at iteration {iteration + 1}")
                break

        self._pagerank_cache = pr
        return pr

    def betweenness_centrality(self) -> Dict[str, float]:
        """
        Calculate betweenness centrality for all nodes.

        Betweenness measures how often a node lies on shortest paths.

        Returns:
            Dictionary of node_id -> betweenness score
        """
        if self._betweenness_cache:
            return self._betweenness_cache

        n = len(self.nodes)
        betweenness = {node_id: 0.0 for node_id in self.nodes}

        for source in self.nodes:
            # BFS from source
            distances, predecessors = self._bfs_shortest_paths(source)

            # Count paths through each node
            for target in self.nodes:
                if target == source:
                    continue

                # Backtrack through predecessors
                stack = [target]
                path_nodes = set()

                while stack:
                    current = stack.pop()
                    path_nodes.add(current)
                    for pred in predecessors.get(current, []):
                        if pred not in path_nodes:
                            stack.append(pred)

                # Increment betweenness for intermediate nodes
                for node in path_nodes:
                    if node != source and node != target:
                        betweenness[node] += 1.0

        # Normalize
        if n > 2:
            norm = 2.0 / ((n - 1) * (n - 2))
            betweenness = {k: v * norm for k, v in betweenness.items()}

        self._betweenness_cache = betweenness
        return betweenness

    def _bfs_shortest_paths(
        self, source: str
    ) -> Tuple[Dict[str, int], Dict[str, List[str]]]:
        """
        BFS to find shortest paths from source.

        Returns:
            Tuple of (distances, predecessors)
        """
        distances = {source: 0}
        predecessors = defaultdict(list)
        queue = [source]
        visited = {source}

        while queue:
            current = queue.pop(0)
            current_dist = distances[current]

            for neighbor in self.adjacency_list.get(current, {}).keys():
                if neighbor not in visited:
                    visited.add(neighbor)
                    distances[neighbor] = current_dist + 1
                    predecessors[neighbor].append(current)
                    queue.append(neighbor)
                elif distances[neighbor] == current_dist + 1:
                    # Equal length path
                    predecessors[neighbor].append(current)

        return distances, predecessors

    def clustering_coefficient(self, node_id: str) -> float:
        """
        Calculate local clustering coefficient for a node.

        Measures how interconnected a node's neighbors are.
        """
        neighbors = set(self.adjacency_list.get(node_id, {}).keys())

        # Add incoming neighbors
        for source_id, targets in self.adjacency_list.items():
            if node_id in targets:
                neighbors.add(source_id)

        neighbors.discard(node_id)
        k = len(neighbors)

        if k < 2:
            return 0.0

        # Count edges between neighbors
        neighbor_edges = 0
        neighbor_list = list(neighbors)

        for i, n1 in enumerate(neighbor_list):
            for n2 in neighbor_list[i + 1 :]:
                # Check both directions
                if n2 in self.adjacency_list.get(n1, {}):
                    neighbor_edges += 1
                if n1 in self.adjacency_list.get(n2, {}):
                    neighbor_edges += 1

        # Possible edges between k neighbors
        max_edges = k * (k - 1)

        return neighbor_edges / max_edges if max_edges > 0 else 0.0

    def hits(
        self, max_iterations: int = 100, tolerance: float = 1e-6
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Calculate HITS hub and authority scores.

        Returns:
            Tuple of (hub_scores, authority_scores)
        """
        n = len(self.nodes)
        if n == 0:
            return {}, {}

        # Initialize
        hubs = {node_id: 1.0 for node_id in self.nodes}
        authorities = {node_id: 1.0 for node_id in self.nodes}

        # Build reverse adjacency
        incoming = defaultdict(list)
        for source_id, targets in self.adjacency_list.items():
            for target_id in targets:
                incoming[target_id].append(source_id)

        for iteration in range(max_iterations):
            # Update authorities
            new_authorities = {}
            for node_id in self.nodes:
                new_authorities[node_id] = sum(
                    hubs[source] for source in incoming[node_id]
                )

            # Normalize authorities
            auth_norm = math.sqrt(sum(v ** 2 for v in new_authorities.values()))
            if auth_norm > 0:
                new_authorities = {k: v / auth_norm for k, v in new_authorities.items()}

            # Update hubs
            new_hubs = {}
            for node_id in self.nodes:
                new_hubs[node_id] = sum(
                    new_authorities.get(target, 0)
                    for target in self.adjacency_list.get(node_id, {}).keys()
                )

            # Normalize hubs
            hub_norm = math.sqrt(sum(v ** 2 for v in new_hubs.values()))
            if hub_norm > 0:
                new_hubs = {k: v / hub_norm for k, v in new_hubs.items()}

            # Check convergence
            max_change = max(
                max(abs(new_hubs.get(k, 0) - hubs.get(k, 0)) for k in self.nodes),
                max(
                    abs(new_authorities.get(k, 0) - authorities.get(k, 0))
                    for k in self.nodes
                ),
            )

            hubs = new_hubs
            authorities = new_authorities

            if max_change < tolerance:
                break

        return hubs, authorities

    def get_top_nodes(
        self, metric: str = "pagerank", top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get top nodes by a specific metric.

        Args:
            metric: "pagerank", "degree", "betweenness", "hub", "authority"
            top_k: Number of top nodes

        Returns:
            List of (node_id, score) tuples
        """
        if metric == "pagerank":
            scores = self.pagerank()
        elif metric == "degree":
            scores = {
                node_id: self.degree_centrality(node_id) for node_id in self.nodes
            }
        elif metric == "betweenness":
            scores = self.betweenness_centrality()
        elif metric == "hub":
            hubs, _ = self.hits()
            scores = hubs
        elif metric == "authority":
            _, authorities = self.hits()
            scores = authorities
        else:
            raise ValueError(f"Unknown metric: {metric}")

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]

    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Calculate overall graph statistics.

        Returns:
            Dictionary of graph-level statistics
        """
        n = len(self.nodes)
        total_edges = sum(
            sum(len(edges) for edges in targets.values())
            for targets in self.adjacency_list.values()
        )

        # Density
        max_edges = n * (n - 1)
        density = total_edges / max_edges if max_edges > 0 else 0

        # Degree statistics
        degrees = [
            self.in_degree(node_id) + self.out_degree(node_id)
            for node_id in self.nodes
        ]
        avg_degree = sum(degrees) / n if n > 0 else 0
        max_degree = max(degrees) if degrees else 0

        # Clustering
        clustering_coeffs = [
            self.clustering_coefficient(node_id) for node_id in self.nodes
        ]
        avg_clustering = sum(clustering_coeffs) / n if n > 0 else 0

        return {
            "num_nodes": n,
            "num_edges": total_edges,
            "density": density,
            "avg_degree": avg_degree,
            "max_degree": max_degree,
            "avg_clustering": avg_clustering,
        }

    def clear_cache(self):
        """Clear all cached metrics."""
        self._metrics_cache.clear()
        self._pagerank_cache.clear()
        self._betweenness_cache.clear()
