import os
import sys


sys.path.append(os.path.join(os.path.dirname(__file__)))
from data_type import (
    CHC,
    Formula,
    PredicateInstance,
    PredicateUpdate,
    PredicateUpdateOp,
)
from llm_output_parser import get_dependency_dag_from_chcs


from instruction_encoder import InstructionEncoder
from utils import log


def check_previously_satisfied(facts: Formula, chc: CHC) -> bool:
    """
    Check chc action is already satisfied given current facts.
    """
    return facts.implies(Formula([chc.action]))


def get_candidates_chcs_to_satisfiable(facts: Formula, chcs: list[CHC]) -> list[CHC]:
    """
    Get CHCs that are not checked yet and can be satisfiable by current facts.
    """
    satisfied_chc_indices = [
        idx for idx, chc in enumerate(chcs) if check_previously_satisfied(facts, chc)
    ]
    dependency_graph = get_dependency_dag_from_chcs(chcs)
    no_dependency_chcs = dependency_graph.entries

    if len(satisfied_chc_indices) == 0:
        candidate_indicies = [
            idx for idx in no_dependency_chcs if idx not in satisfied_chc_indices
        ]
        return [chcs[idx] for idx in candidate_indicies]

    depth_info = dependency_graph.get_bfs_depth_from_entries()
    max_depth_in_satisfied_chcs = max(
        [depth_info[idx] for idx in satisfied_chc_indices]
    )
    max_depth_chc_indicies = [
        idx for idx, depth in depth_info.items() if depth == max_depth_in_satisfied_chcs
    ]
    candidate_indicies = []
    for satisfied_chc_idx in max_depth_chc_indicies:
        next_chcs = dependency_graph.get_targets_by_source(satisfied_chc_idx)
        for next_chc_idx in next_chcs:
            if next_chc_idx not in satisfied_chc_indices:
                candidate_indicies.append(next_chc_idx)
    return [chcs[idx] for idx in candidate_indicies]


def get_unsatisfies_for_each_chc(
    facts: Formula, chcs: list[CHC]
) -> list[list[PredicateInstance]]:
    """
    Find predicates that are not satisfied in each CHC given current facts.

    Args:
        facts: Current known facts as Formula
        chcs: List of Constrained Horn Clauses to verify

    Returns:
        list[list[PredicateInstance]]: For each CHC, list of predicates that are not satisfied
    """
    unsatisfied = [[] for _ in chcs]

    satisfied = [check_previously_satisfied(facts, chc) for chc in chcs]

    satisfied_indicies = [idx for idx, s in enumerate(satisfied) if s]

    dependency_graph = get_dependency_dag_from_chcs(chcs)

    depth_into = dependency_graph.get_bfs_depth_from_entries()

    if satisfied_indicies:
        sat_depths = [depth_into[i] for i in satisfied_indicies]
        max_depth = max(sat_depths)
        worklist = [i for i in range(len(chcs)) if depth_into[i] == max_depth]
    else:
        worklist = dependency_graph.entries

    while worklist:
        chc_idx = worklist.pop()
        chc = chcs[chc_idx]

        if facts.implies(chc.formula):
            satisfied[chc_idx] = True
            if chc.action not in facts.formula:
                operator = PredicateUpdateOp.Add
            else:
                operator = PredicateUpdateOp.Update
            facts.formula_update(
                PredicateUpdate(predicate=chc.action, operation=operator)
            )
            next_chcs = dependency_graph.get_targets_by_source(chc_idx)
            worklist.extend(next_chcs)

    for idx, s in enumerate(satisfied):
        if s:
            continue
        unsats = facts.implies_verbose(chcs[idx].formula)
        unsatisfied[idx] = unsats

    return unsatisfied


def pretty_print_unsats(unsats: list[list[PredicateInstance]]) -> str:
    result = ""
    for i, unsat in enumerate(unsats):
        result += f"CHC {i}: "
        result += " ∧ ".join([str(pred) for pred in unsat])
        result += "\n"
    return result


def verify(facts: Formula, chcs: list[CHC]) -> bool:
    """
    Verify if all CHCs are satisfied given current facts.

    Args:
        facts: Current known facts as Formula
        chcs: List of Constrained Horn Clauses to verify

    Returns:
        bool: True if all CHCs are satisfied, False otherwise
    """
    if len(chcs) == 0:
        return True
    dependency_graph = get_dependency_dag_from_chcs(chcs)
    log(f"dependency_graph: {dependency_graph}", "white")
    leaf_chcs = dependency_graph.leaves
    log(f"leaf_chcs: {leaf_chcs}", "white")
    unsats = get_unsatisfies_for_each_chc(facts, chcs)
    for leaf_chc in leaf_chcs:
        print(f"leaf_chc: {leaf_chc}")
        print(f"unsats[leaf_chc]: {unsats[leaf_chc]}")
        if len(unsats[leaf_chc]) == 0:
            return True
    return False
