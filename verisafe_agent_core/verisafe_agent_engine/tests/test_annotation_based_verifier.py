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
    EnumValues,
    PredicateDef,
)
from agent_verifier.verifier.annotation_based_verifier import (
    get_unsatisfies_for_each_chc,
    verify,
    get_candidates_chcs_to_satisfiable,
)
from agent_verifier.verifier.instruction_encoder import InstructionEncoder


# Test helper function to create predicates
def create_predicate(name: str, value: bool) -> PredicateInstance:
    arg = Arg("value", ValueType.Boolean)
    pred_def = PredicateDef(
        name=name, arguments={"value_param": arg}, description=f"{name} predicate"
    )
    return PredicateInstance(
        predicate_def=pred_def,
        arguments={"value_param": ValueInstance(arg, value)},
    )


# Helper function to create number predicates
def create_number_predicate(
    name: str, value: int, op: CmpOp = CmpOp.Equal
) -> PredicateInstance:
    arg = Arg("value", ValueType.Number)
    pred_def = PredicateDef(
        name=name,
        arguments={"value_param": arg},
        description=f"{name} number predicate",
    )
    return PredicateInstance(
        predicate_def=pred_def,
        arguments={"value_param": ValueInstance(arg, value, op)},
    )


# Helper function to create text predicates
def create_text_predicate(name: str, value: str) -> PredicateInstance:
    arg = Arg("value", ValueType.Text)
    pred_def = PredicateDef(
        name=name, arguments={"value_param": arg}, description=f"{name} text predicate"
    )
    return PredicateInstance(
        predicate_def=pred_def,
        arguments={"value_param": ValueInstance(arg, value)},
    )


# Helper function to create enum predicates
def create_enum_predicate(
    name: str, value: str, enum_values: list[str]
) -> PredicateInstance:
    arg = Arg("value", ValueType.Enum, EnumValues(enum_values))
    pred_def = PredicateDef(
        name=name, arguments={"value_param": arg}, description=f"{name} enum predicate"
    )
    return PredicateInstance(
        predicate_def=pred_def,
        arguments={"value_param": ValueInstance(arg, value)},
    )


class TestGetUnsatisfiedPredicates:
    def test_all_satisfied(self):
        # Test case where all CHCs are satisfied
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)

        formula = Formula([pred_a])

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B
            CHC(Formula([pred_b]), pred_c),  # B → C
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # All CHCs should be satisfied after processing
        assert all(len(unsat) == 0 for unsat in unsatisfied)

    def test_unsatisfied_predicates(self):
        # Test case where some CHCs are not satisfied
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)
        pred_d = create_predicate("D", True)

        formula = Formula([pred_a])

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B (satisfied)
            CHC(Formula([pred_c]), pred_d),  # C → D (not satisfied, C is missing)
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # First CHC should be satisfied
        assert len(unsatisfied[0]) == 0
        # Second CHC should be unsatisfied with pred_c missing
        assert len(unsatisfied[1]) > 0
        assert unsatisfied[1][0].name == "C"

    def test_dependency_chain(self):
        # Test case with a dependency chain: A → B → C → D
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)
        pred_d = create_predicate("D", True)

        formula = Formula([pred_a])

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B
            CHC(Formula([pred_b]), pred_c),  # B → C
            CHC(Formula([pred_c]), pred_d),  # C → D
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # All CHCs should be satisfied due to dependency chain
        assert all(len(unsat) == 0 for unsat in unsatisfied)

    def test_complex_dependencies(self):
        # Test with more complex dependencies
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)
        pred_d = create_predicate("D", True)
        pred_e = create_predicate("E", True)

        formula = Formula([pred_a, pred_b])

        chcs = [
            CHC(Formula([pred_a]), pred_c),  # A → C
            CHC(Formula([pred_b, pred_c]), pred_d),  # B ∧ C → D
            CHC(Formula([pred_d]), pred_e),  # D → E
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # All CHCs should be satisfied due to dependencies
        assert all(len(unsat) == 0 for unsat in unsatisfied)

    def test_with_formula_updates(self):
        # Test that formula is correctly updated during processing
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)

        # Start with just pred_a
        formula = Formula([pred_a])
        original_formula_len = len(formula.formula)

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B
            CHC(Formula([pred_b]), pred_c),  # B → C
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)

        # Formula should now contain pred_a, pred_b, and pred_c
        assert len(formula.formula) > original_formula_len
        assert pred_a in formula.formula
        assert any(p.name == "B" for p in formula.formula)
        assert any(p.name == "C" for p in formula.formula)

        # All CHCs should be satisfied
        assert all(len(unsat) == 0 for unsat in unsatisfied)

    def test_with_different_predicate_types(self):
        # Test with different types of predicates (number, text, enum)
        num_pred = create_number_predicate("NumCheck", 10, CmpOp.GreaterThan)
        text_pred = create_text_predicate("TextCheck", "hello")
        enum_pred = create_enum_predicate(
            "EnumCheck", "option1", ["option1", "option2", "option3"]
        )

        formula = Formula([num_pred])

        chcs = [
            CHC(Formula([num_pred]), text_pred),  # NumCheck → TextCheck
            CHC(Formula([text_pred]), enum_pred),  # TextCheck → EnumCheck
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # All CHCs should be satisfied due to dependency chain
        assert all(len(unsat) == 0 for unsat in unsatisfied)

        # Formula should now contain all three predicates
        assert len(formula.formula) == 3
        assert any(p.name == "NumCheck" for p in formula.formula)
        assert any(p.name == "TextCheck" for p in formula.formula)
        assert any(p.name == "EnumCheck" for p in formula.formula)

    def test_with_empty_formula(self):
        # Test with an empty initial formula
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)

        formula = Formula([])  # Empty formula

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B
        ]

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # CHC should be unsatisfied because pred_a is missing
        assert len(unsatisfied[0]) > 0
        assert unsatisfied[0][0].name == "A"

    def test_with_empty_chcs(self):
        # Test with empty CHCs list
        pred_a = create_predicate("A", True)

        formula = Formula([pred_a])

        chcs = []  # Empty CHCs

        unsatisfied = get_unsatisfies_for_each_chc(formula, chcs)
        # Should return an empty list
        assert len(unsatisfied) == 0


class TestVerify:
    def test_verify_all_satisfied(self):
        # Test case where all CHCs are satisfied
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)

        formula = Formula([pred_a])

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B
            CHC(Formula([pred_b]), pred_c),  # B → C
        ]

        assert verify(formula, chcs) == True

    def test_verify_some_unsatisfied(self):
        # Test case where some CHCs are not satisfied
        pred_a = create_predicate("A", True)
        pred_b = create_predicate("B", True)
        pred_c = create_predicate("C", True)
        pred_d = create_predicate("D", True)

        formula = Formula([pred_a])

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # A → B (satisfied)
            CHC(
                Formula([pred_b, pred_c]), pred_d
            ),  # B ∧ C → D (not satisfied, C is missing)
        ]

        assert verify(formula, chcs) == False

    def test_verify_with_number_comparison(self):
        # Test with number comparisons
        num_arg = Arg("value", ValueType.Number)
        num_pred_def = PredicateDef(
            name="NumCheck",
            arguments={"value_param": num_arg},
            description="Number check predicate",
        )

        pred_a = PredicateInstance(
            predicate_def=num_pred_def,
            arguments={"value_param": ValueInstance(num_arg, 10, CmpOp.GreaterThan)},
        )

        pred_b = PredicateInstance(
            predicate_def=num_pred_def,
            arguments={"value_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan)},
        )

        formula = Formula([pred_a])  # x > 10

        chcs = [
            CHC(Formula([pred_a]), pred_b),  # if x > 10 then x > 5
        ]

        assert verify(formula, chcs) == True

    def test_verify_empty_cases(self):
        # Test edge cases with empty formulas/CHCs
        pred_a = create_predicate("A", True)

        # Empty formula and empty CHCs
        assert verify(Formula([]), []) == True

        # Empty CHCs
        assert verify(Formula([pred_a]), []) == True

        # Formula with predicates but no CHCs
        formula = Formula([pred_a])
        assert verify(formula, []) == True

    def test_verify_with_different_predicate_types(self):
        # Test with different types of predicates
        num_pred = create_number_predicate("NumCheck", 10, CmpOp.GreaterThan)
        text_pred = create_text_predicate("TextCheck", "hello")
        enum_pred = create_enum_predicate(
            "EnumCheck", "option1", ["option1", "option2", "option3"]
        )

        formula = Formula([num_pred, text_pred])

        chcs = [
            CHC(
                Formula([num_pred, text_pred]), enum_pred
            ),  # NumCheck ∧ TextCheck → EnumCheck
        ]

        assert verify(formula, chcs) == True

    def test_verify_complex_scenario(self):
        # Test a more complex scenario with multiple dependencies and different predicate types
        bool_pred = create_predicate("BoolCheck", True)
        num_pred = create_number_predicate("NumCheck", 10, CmpOp.GreaterThan)
        text_pred = create_text_predicate("TextCheck", "hello")
        enum_pred = create_enum_predicate(
            "EnumCheck", "option1", ["option1", "option2", "option3"]
        )

        formula = Formula([bool_pred, num_pred])

        chcs = [
            CHC(Formula([bool_pred]), text_pred),  # BoolCheck → TextCheck
            CHC(
                Formula([num_pred, text_pred]), enum_pred
            ),  # NumCheck ∧ TextCheck → EnumCheck
        ]

        assert verify(formula, chcs) == True


def test_get_candidates_chcs_to_satisfiable():
    """
    Test the get_candidates_chcs_to_satisfiable function which returns CHCs
    that are not satisfied yet but can be satisfiable based on current facts.
    """
    # Create predicates for testing
    p1 = create_predicate("p1", True)
    p2 = create_predicate("p2", True)
    p3 = create_predicate("p3", True)
    p4 = create_predicate("p4", True)
    p5 = create_predicate("p5", True)
    p6 = create_predicate("p6", True)

    p1.predicate_def.is_action = True
    p3.predicate_def.is_action = True
    p5.predicate_def.is_action = True

    # Create CHCs with dependencies
    # CHC0: true → p1
    # CHC1: p1 ∧ p2 → p3
    # CHC2: p1 ∧ p4 → p5
    # CHC3: p3 → p6
    chc1 = CHC(Formula([]), p1)
    chc2 = CHC(Formula([p1, p2]), p3)
    chc3 = CHC(Formula([p1, p4]), p5)
    chc4 = CHC(Formula([p3]), p6)

    chcs = [chc1, chc2, chc3, chc4]

    # Test1: no facts
    facts = Formula([])
    candidates = get_candidates_chcs_to_satisfiable(facts, chcs)
    assert (
        len(candidates) == 1
    ), f"Expected 1 candidate, got {InstructionEncoder.listup_iterable(candidates)}"
    assert candidates[0].action == p1, f"Expected p1, got {candidates[0].action}"

    # Test2: p1 is true
    facts = Formula([p1])
    candidates = get_candidates_chcs_to_satisfiable(facts, chcs)
    assert (
        len(candidates) == 2
    ), f"Expected 2 candidates, got {InstructionEncoder.listup_iterable(candidates)}"
    actions = [c.action for c in candidates]
    assert p3 in actions and p5 in actions, f"Expected p3 and p5 in {actions}"

    # Test3: p1, p2, p3 are true
    facts = Formula([p1, p2, p3])
    candidates = get_candidates_chcs_to_satisfiable(facts, chcs)
    assert (
        len(candidates) == 1
    ), f"Expected 1 candidate, got {InstructionEncoder.listup_iterable(candidates)}"
    assert candidates[0].action == p6, f"Expected p6, got {candidates[0].action}"
