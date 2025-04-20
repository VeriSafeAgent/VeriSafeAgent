from collections import defaultdict
from copy import deepcopy
import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional, TypeVar

from termcolor import colored
import graphviz as gv

T = TypeVar("T")


class MinimizedDAG:
    def __init__(self):
        self._dag = defaultdict(list)
        self._reachable = defaultdict(set)

    def __str__(self):
        result = ""
        for source, targets in self._dag.items():
            if targets:
                result += f"{source} -> {targets}\n"
        return result

    @property
    def dag(self) -> dict[int, list[int]]:
        return self._dag

    @property
    def entries(self) -> list[int]:
        # Vertices with no incoming edges
        candidates = set(self._dag.keys())
        for targets in self._dag.values():
            for target in targets:
                candidates.discard(target)
        return list(candidates)

    @property
    def leaves(self) -> list[int]:
        # Vertices with no outgoing edges
        result = []
        for source, targets in self._dag.items():
            if not targets:
                result.append(source)
        return result

    def get_sources_by_target(self, v: int) -> list[int]:
        result = []
        for source, targets in self._dag.items():
            if v in targets:
                result.append(source)
        return result

    def get_targets_by_source(self, v: int) -> list[int]:
        return self._dag[v]

    def is_reachable(self, u, v) -> bool:
        if u in self._reachable and v in self._reachable[u]:
            return True
        return False

    def calc_fixedpoint_of_reachable(self):
        # Track if any changes were made in the current iteration
        changed = True

        while changed:
            changed = False
            # Process each source node
            for u in list(self._reachable.keys()):
                # Get the current set of nodes reachable from u
                reachable_from_u = set(self._reachable[u])

                # For each node v that u can reach directly
                for v in reachable_from_u:
                    # If v can reach some nodes that u doesn't know about yet
                    if not self._reachable[v].issubset(self._reachable[u]):
                        # Add these new nodes to u's reachability set
                        new_reachable = self._reachable[v] - self._reachable[u]
                        if new_reachable:
                            self._reachable[u].update(new_reachable)
                            changed = True

    def add_edge_with_reduction(self, u, v):
        self._transitive_reduction(u, v)

    def _transitive_reduction(self, u, v):
        if self.is_reachable(u, v):  # Already reachable, no need to reduce
            return
        original_u_edges = self._dag[u]
        for w in original_u_edges:
            if self.is_reachable(v, w):
                self.remove_edge(u, w)
        self._add_edge(u, v)
        self.calc_fixedpoint_of_reachable()

    def _register(self, v: int):
        if v not in self._dag:
            self._dag[v] = []
            self._reachable[v] = set()

    def _add_edge(self, u: int, v: int) -> None:
        self._register(u)
        self._register(v)
        self._dag[u].append(v)
        self._reachable[u].add(v)

    def remove_edge(self, u: int, v: int) -> None:
        self._dag[u].remove(v)

    def add_vertice(self, idx: int) -> None:
        if idx in self._dag:
            return
        self._dag[idx] = []
        self._reachable[idx] = set()

    def get_bfs_depth_from_entries(self) -> dict[int, int]:
        result = {}
        for entry in self.entries:
            result[entry] = 0
        queue = self.entries
        while queue:
            v = queue.pop(0)
            for target in self._dag[v]:
                if target not in result:
                    result[target] = result[v] + 1
                    queue.append(target)
        return result

    def draw_graphdot(self, name: str = "graph"):
        """
        Creates a visual representation of the DAG using graphviz and saves it as a PDF file.
        The graph will show the structure of the DAG with nodes and edges.
        """
        # Create a new directed graph
        dot = gv.Digraph(comment="Minimized DAG")
        dot.attr(rankdir="TB")  # Top to Bottom direction

        # Add all vertices
        for vertex in self._dag.keys():
            dot.node(str(vertex), str(vertex))

        # Add all edges
        for source, targets in self._dag.items():
            for target in targets:
                dot.edge(str(source), str(target))

        # Save the graph as PDF
        dot.render(name, format="pdf", cleanup=True)


def find_first(iterable: Iterable[T], cond_f: Callable[[T], bool]) -> Optional[T]:
    for elem in iterable:
        if cond_f(elem):
            return elem
    return None


def find_all(iterable: Iterable[T], cond_f: Callable[[T], bool]) -> list[T]:
    return [elem for elem in iterable if cond_f(elem)]


# Setup logging variables
log_dir = Path("logs")
log_file = None
enable_file_logging = False


def init_logging(to_file: bool = False, log_directory: str = "logs") -> None:
    """
    Initialize the logging system

    Args:
        to_file: Whether to log to a file
        log_directory: Directory to store log files
    """
    global log_dir, log_file, enable_file_logging

    enable_file_logging = to_file
    log_dir = Path(log_directory)

    if enable_file_logging:
        log_dir.mkdir(exist_ok=True)
        log_file = (
            log_dir / f"{datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log"
        )


def log(msg: str, color = "white") -> None:
    """
    Log a message both to console and file with color support
    Args:
        msg: Message to log
        color: Color of the message (termcolor supported colors)
    """
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_with_time = f"[{time}] {msg}"
    colored_log = colored(msg_with_time, color, attrs=["bold"])
    print(colored_log)

    if enable_file_logging and log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{msg_with_time}\n")


def prefix_adder(s: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in s.split("\n"))
