import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent_verifier.verifier.utils import MinimizedDAG


class TestMinimizedDAG(unittest.TestCase):
    """Test cases for the MinimizedDAG class."""

    def test_init(self):
        """Test initialization of MinimizedDAG."""
        dag = MinimizedDAG()
        assert dag.dag == {}

    def test_str_representation(self):
        """Test string representation of the DAG."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(2, 3)
        expected = "1 -> [2]\n2 -> [3]\n"
        assert str(dag) == expected

    def test_dag_property(self):
        """Test the dag property returns the internal DAG structure."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(1, 3)
        assert dag.dag == {1: [2, 3], 2: [], 3: []}

    def test_entries_property(self):
        """Test entries property returns vertices with no incoming edges."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(1, 3)
        dag._add_edge(3, 4)
        dag._add_edge(5, 6)

        entries = dag.entries
        assert sorted(entries) == [
            1,
            5,
        ]

    def test_leaves_property(self):
        """Test leaves property returns vertices with no outgoing edges."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(1, 3)
        dag._add_edge(3, 4)
        dag._add_edge(5, 6)

        leaves = dag.leaves
        assert sorted(leaves) == [
            2,
            4,
            6,
        ]

    def test_get_sources_by_target(self):
        """Test get_sources_by_target returns correct source vertices."""
        dag = MinimizedDAG()
        dag._add_edge(1, 3)
        dag._add_edge(2, 3)
        dag._add_edge(3, 4)

        sources = dag.get_sources_by_target(3)
        assert sorted(sources) == [
            1,
            2,
        ]

        sources = dag.get_sources_by_target(4)
        assert sources == [3]

        sources = dag.get_sources_by_target(5)  # Non-existent target
        assert sources == []

    def test_get_targets_by_source(self):
        """Test get_targets_by_source returns correct target vertices."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(1, 3)
        dag._add_edge(3, 4)

        targets = dag.get_targets_by_source(1)
        assert sorted(targets) == [
            2,
            3,
        ]

        targets = dag.get_targets_by_source(2)  # Source with no targets
        assert targets == []

        targets = dag.get_targets_by_source(5)  # Non-existent source
        assert targets == []

    def test_is_reachable(self):
        """Test is_reachable correctly identifies reachable vertices."""
        dag = MinimizedDAG()
        # Add edges without reachability tracking
        dag._add_edge(1, 2)
        dag._add_edge(2, 3)

        # Without proper reachability tracking, should return False
        assert not dag.is_reachable(1, 3), f"Expected False, but got True"

        # Using add_edge_with_reduction properly updates reachability
        dag = MinimizedDAG()
        dag.add_edge_with_reduction(1, 2)
        dag.add_edge_with_reduction(2, 3)

        assert dag.is_reachable(1, 2), f"Expected True, but got False"
        assert dag.is_reachable(2, 3), f"Expected True, but got False"
        assert dag.is_reachable(
            1, 3
        ), f"Expected True, but got False"  # Transitive reachability
        assert not dag.is_reachable(
            3, 1
        ), f"Expected False, but got True"  # Reverse direction

    def test_add_edge_with_reduction(self):
        """Test add_edge_with_reduction correctly adds edges with transitive reduction."""
        dag = MinimizedDAG()
        dag.add_edge_with_reduction(1, 2)
        dag.add_edge_with_reduction(2, 3)
        dag.add_edge_with_reduction(1, 3)  # This should be reduced since 1->2->3 exists

        # Direct edge from 1 to 3 should be removed due to reduction
        assert dag.dag[1] == [2], f"Expected [2], but got {dag.dag[1]}"
        assert dag.dag[2] == [3], f"Expected [3], but got {dag.dag[2]}"

        # Reachability should still be maintained
        assert dag.is_reachable(1, 3), f"Expected True, but got False"

    def test_transitive_reduction(self):
        """Test _transitive_reduction correctly implements transitive reduction."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(2, 3)

        # Manually update reachability to test reduction
        dag._reachable[1].add(2)
        dag._reachable[2].add(3)
        dag._reachable[1].add(3)

        dag._transitive_reduction(1, 4)
        dag._transitive_reduction(4, 3)

        # Direct edge from 1 to 3 should be removed if it existed
        assert 3 not in dag.dag[1]
        # New edges should be added
        assert 4 in dag.dag[1]
        assert 3 in dag.dag[4]

    def test_add_edge(self):
        """Test _add_edge correctly adds an edge to the DAG."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)

        assert dag.dag == {1: [2], 2: []}

        dag._add_edge(1, 3)
        assert sorted(dag.dag[1]) == [
            2,
            3,
        ], f"Expected [2, 3], but got {dag.dag[1]}"

    def test_remove_edge(self):
        """Test remove_edge correctly removes an edge from the DAG."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(1, 3)

        dag.remove_edge(1, 2)
        assert dag.dag[1] == [3], f"Expected [3], but got {dag.dag[1]}"

        dag.remove_edge(1, 3)
        assert dag.dag[1] == [], f"Expected [], but got {dag.dag[1]}"

    def test_add_vertice(self):
        """Test add_vertice correctly adds a vertex to the DAG."""
        dag = MinimizedDAG()
        dag.add_vertice(1)

        assert 1 in dag.dag, f"Expected 1 in dag.dag, but got {dag.dag}"
        assert dag.dag[1] == [], f"Expected [], but got {dag.dag[1]}"

        # Adding the same vertex again should have no effect
        dag.add_vertice(1)
        assert dag.dag[1] == [], f"Expected [], but got {dag.dag[1]}"

    def test_get_bfs_depth_from_entries(self):
        """Test get_bfs_depth_from_entries returns correct depths."""
        dag = MinimizedDAG()
        dag._add_edge(1, 2)
        dag._add_edge(1, 3)
        dag._add_edge(2, 4)
        dag._add_edge(3, 4)
        dag._add_edge(4, 5)

        depths = dag.get_bfs_depth_from_entries()

        assert depths == {
            1: 0,
            2: 1,
            3: 1,
            4: 2,
            5: 3,
        }

        # Test with multiple entry points
        dag = MinimizedDAG()
        dag._add_edge(1, 3)
        dag._add_edge(2, 3)
        dag._add_edge(3, 4)

        depths = dag.get_bfs_depth_from_entries()

        assert depths == {
            1: 0,
            2: 0,
            3: 1,
            4: 2,
        }

    def test_complex_graph(self):
        """Test a more complex graph scenario."""
        dag = MinimizedDAG()

        # Create a diamond pattern with transitive edges
        dag.add_edge_with_reduction(1, 2)
        dag.add_edge_with_reduction(1, 3)
        dag.add_edge_with_reduction(2, 4)
        dag.add_edge_with_reduction(3, 4)
        dag.add_edge_with_reduction(1, 4)  # Should be reduced

        # Check the structure after reduction
        assert sorted(dag.dag[1]) == [
            2,
            3,
        ], f"Expected {sorted(dag.dag[1])}, but got {dag.dag[1]}"
        assert dag.dag[2] == [4], f"Expected [4], but got {dag.dag[2]}"
        assert dag.dag[3] == [4], f"Expected [4], but got {dag.dag[3]}"

        # Check entries and leaves
        assert dag.entries == [1], f"Expected [1], but got {dag.entries}"
        assert dag.leaves == [4], f"Expected [4], but got {dag.leaves}"

        # Check reachability
        assert dag.is_reachable(1, 4), f"Expected True, but got False"
        assert dag.is_reachable(2, 4), f"Expected True, but got False"
        assert dag.is_reachable(3, 4), f"Expected True, but got False"

        # Check BFS depths
        depths = dag.get_bfs_depth_from_entries()
        assert depths == {
            1: 0,
            2: 1,
            3: 1,
            4: 2,
        }, f"Expected {depths}, but got {depths}"
