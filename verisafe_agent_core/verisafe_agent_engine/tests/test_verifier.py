import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_verifier.verifier.data_type import (
    Arg,
    ValueType,
    Formula,
    PredicateInstance,
    ValueInstance,
    CHC,
    CmpOp,
    PredicateDef,
)
from agent_verifier.verifier.annotation_based_verifier import verify


# Test helper function to create predicates
def create_predicate(name: str, value: bool) -> PredicateInstance:
    arg = Arg("value", ValueType.Boolean)
    pred_def = PredicateDef(
        name=name, arguments={"value": arg}, description=f"{name} predicate"
    )
    return PredicateInstance(
        predicate_def=pred_def,
        arguments={"value": ValueInstance(arg, value)},
    )


def test_verify_simple_chain():
    # Test case: A → B → C
    # Formula contains A, should verify B and C

    pred_a = create_predicate("A", True)
    pred_b = create_predicate("B", True)
    pred_c = create_predicate("C", True)

    formula = Formula([pred_a])

    chcs = [
        CHC(Formula([pred_a]), pred_b),  # A → B
        CHC(Formula([pred_b]), pred_c),  # B → C
    ]

    assert verify(formula, chcs) == True


def test_verify_already_satisfied():
    # Test case where action is already satisfied
    pred_a = create_predicate("A", True)
    pred_b = create_predicate("B", True)

    formula = Formula([pred_a])

    chcs = [
        CHC(Formula([pred_b]), pred_a),  # Action is already satisfied
    ]

    assert verify(formula, chcs) == True


def test_verify_with_numbers():
    # Test with number comparisons
    num_arg = Arg("value", ValueType.Number)
    num_pred_def = PredicateDef(
        arguments={"value": num_arg},
        description="Number check predicate",
    )

    pred_a = PredicateInstance(
        predicate_def=num_pred_def,
        arguments={"value": ValueInstance(num_arg, 10, CmpOp.GreaterThan)},
    )

    pred_b = PredicateInstance(
        predicate_def=num_pred_def,
        arguments={"value": ValueInstance(num_arg, 5, CmpOp.GreaterThan)},
    )

    formula = Formula([pred_a])  # x > 10

    chcs = [
        CHC(Formula([pred_a]), pred_b),  # if x > 10 then x > 5
    ]

    assert verify(formula, chcs) == True


def test_verify_complex_dependency():
    # Test with multiple dependencies
    pred_a = create_predicate("A", True)
    pred_b = create_predicate("B", True)
    pred_c = create_predicate("C", True)
    pred_d = create_predicate("D", True)

    formula = Formula([pred_a, pred_b])

    chcs = [
        CHC(Formula([pred_a, pred_b]), pred_c),  # A ∧ B → C
        CHC(Formula([pred_c]), pred_d),  # C → D
    ]

    assert verify(formula, chcs) == True


def test_verify_empty_cases():
    # Test edge cases with empty formulas/CHCs
    pred_a = create_predicate("A", True)

    # Empty formula
    assert verify(Formula([]), []) == True

    # Empty CHCs
    assert verify(Formula([pred_a]), []) == True

    # Formula with predicates but no CHCs
    formula = Formula([pred_a])
    assert verify(formula, []) == True


def test_verify_multiple_conditions():
    # Test CHCs with multiple conditions in antecedent
    pred_a = create_predicate("A", True)
    pred_b = create_predicate("B", True)
    pred_c = create_predicate("C", True)
    pred_d = create_predicate("D", True)

    formula = Formula([pred_a, pred_b, pred_c])

    chcs = [
        CHC(Formula([pred_a, pred_b, pred_c]), pred_d),  # A ∧ B ∧ C → D
    ]

    assert verify(formula, chcs) == True


def test_branch_and_join():
    # Test with branch and loop dependencies
    pred_a = create_predicate("A", True)
    pred_b = create_predicate("B", True)
    pred_c = create_predicate("C", True)
    pred_d = create_predicate("D", True)
    pred_e = create_predicate("E", True)

    formula = Formula([pred_a, pred_c])

    chcs = [
        CHC(Formula([pred_a]), pred_b),  # A → B
        CHC(Formula([pred_b]), pred_d),  # B → D
        CHC(Formula([pred_c]), pred_d),  # C → D
        CHC(Formula([pred_b, pred_c, pred_d]), pred_e),  # B /\ C /\ D → E
    ]

    assert verify(formula, chcs) == True
