import sys
import os
from dateutil.parser import parse

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from agent_verifier.verifier.data_type import (
    ValueType,
    Arg,
    ValueInstance,
    PredicateInstance,
    CmpOp,
    Formula,
    Anything,
    PredicateUpdateOp,
    PredicateUpdate,
    PredicateDef,
    EnumValues,
    get_unknown,
)
from agent_verifier.verifier.llm_output_parser import Anything as Anything2

bool_arg = Arg("bool_param", ValueType.Boolean)
num_arg = Arg("num_param", ValueType.Number)
text_arg = Arg("text_param", ValueType.Text)

# Create predicate definitions for tests
test_pred_def = PredicateDef(
    name="test_pred",
    arguments={"bool_param": bool_arg, "num_param": num_arg},
    description="Test predicate with boolean and number parameters",
)

different_pred_def = PredicateDef(
    name="different_pred",
    arguments={"bool_param": bool_arg, "num_param": num_arg},
    description="Different test predicate",
)

mixed_pred_def = PredicateDef(
    name="mixed_pred",
    arguments={"bool_param": bool_arg, "text_param": text_arg},
    description="Mixed predicate with boolean and text parameters",
)

complex_pred_def = PredicateDef(
    name="complex_pred",
    arguments={"bool_param": bool_arg, "num_param": num_arg, "text_param": text_arg},
    description="Complex predicate with multiple parameters",
)

# Create test predicates
p1 = PredicateInstance(
    predicate_def=test_pred_def,
    arguments={
        "bool_param": ValueInstance(bool_arg, True),
        "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
    },
)  # True, x > 5

p2 = PredicateInstance(
    predicate_def=test_pred_def,
    arguments={
        "bool_param": ValueInstance(bool_arg, True),
        "num_param": ValueInstance(num_arg, 3, CmpOp.GreaterThan),
    },
)  # True, x > 3

# Basic contains test
formula = Formula([p2])


# Test ValueType.__str__ method
def test_value_type_str():
    # Verify string representation of each value type
    assert str(ValueType.Boolean) == "Boolean"
    assert str(ValueType.Text) == "Text"
    assert str(ValueType.Time) == "Time"
    assert str(ValueType.Date) == "Date"
    assert str(ValueType.Number) == "Number"
    assert str(ValueType.Enum) == "Enum"


# Test CmpOp.__str__ method
def test_cmp_op_str():
    # Verify string representation of each comparison operator
    assert str(CmpOp.Equal) == "=="
    assert str(CmpOp.NotEqual) == "!="
    assert str(CmpOp.GreaterThan) == ">"
    assert str(CmpOp.GreaterThanOrEqual) == ">="
    assert str(CmpOp.LessThan) == "<"
    assert str(CmpOp.LessThanOrEqual) == "<="


# Test PredicateUpdateOp.__str__ method
def test_predicate_update_op_str():
    # Verify string representation of each update operation
    assert str(PredicateUpdateOp.Add) == "Add"
    assert str(PredicateUpdateOp.Update) == "Update"
    assert str(PredicateUpdateOp.Delete) == "Delete"

    # Test invalid operation case
    # This test would cause an error, so we'll keep it commented
    # invalid_op = PredicateUpdateOp.Add
    # invalid_op.name = "Invalid"  # This would trigger ValueError in __str__


# Test equality methods in enum classes
def test_value_type_eq():
    # Same type equality
    assert ValueType.Boolean == ValueType.Boolean
    assert ValueType.Text == ValueType.Text
    assert ValueType.Number == ValueType.Number

    # Different type equality
    assert ValueType.Boolean != ValueType.Text
    assert not (ValueType.Number == ValueType.Date)

    # Test with non-ValueType object
    assert ValueType.Boolean.__eq__("Boolean") is NotImplemented


def test_cmp_op_eq():
    # Same operator equality
    assert CmpOp.Equal == CmpOp.Equal
    assert CmpOp.GreaterThan == CmpOp.GreaterThan

    # Different operator equality
    assert CmpOp.Equal != CmpOp.NotEqual
    assert not (CmpOp.LessThan == CmpOp.GreaterThan)

    # Test with non-CmpOp object
    assert CmpOp.Equal.__eq__("==") is NotImplemented


def test_predicate_update_op_eq():
    # Same operation equality
    assert PredicateUpdateOp.Add == PredicateUpdateOp.Add
    assert PredicateUpdateOp.Update == PredicateUpdateOp.Update

    # Different operation equality
    assert PredicateUpdateOp.Add != PredicateUpdateOp.Delete
    assert not (PredicateUpdateOp.Update == PredicateUpdateOp.Add)

    # Test with non-PredicateUpdateOp object
    assert PredicateUpdateOp.Add.__eq__("Add") is NotImplemented


# Test PredicateUpdate.__str__ method
def test_predicate_update_str():
    # Create test arguments
    arg = Arg("test_param", ValueType.Text)

    # Create predicate definition
    pred_def = PredicateDef(
        name="test_pred",
        arguments={"test_param": arg},
        description="Test predicate for update string test",
    )

    # Setup test predicates
    pred1 = PredicateInstance(
        predicate_def=pred_def,
        arguments={"test_param": ValueInstance(arg, "value1")},
    )

    pred2 = PredicateInstance(
        predicate_def=pred_def,
        arguments={"test_param": ValueInstance(arg, "value2")},
    )

    # Test Add operation string representation
    add_update = PredicateUpdate(predicate=pred1, operation=PredicateUpdateOp.Add)
    assert str(add_update) == f"Add {str(pred1)}"

    # Test Update operation string representation
    update_update = PredicateUpdate(predicate=pred2, operation=PredicateUpdateOp.Update)
    assert str(update_update) == f"Update to {str(pred2)}"

    # Test Delete operation string representation
    remove_update = PredicateUpdate(predicate=pred1, operation=PredicateUpdateOp.Delete)
    assert str(remove_update) == f"Delete {str(pred1)}"


# Test ValueInstance implies method
def test_value_instance_implies_boolean():
    # Create test arguments
    arg = Arg("test_bool", ValueType.Boolean)

    # Test cases for boolean values
    v1 = ValueInstance(arg, True)
    v2 = ValueInstance(arg, True)
    v3 = ValueInstance(arg, False)

    assert v1.implies(v2) == True  # True → True
    assert v1.implies(v3) == False  # True → False
    assert v3.implies(v1) == False  # False → True


def test_value_instance_implies_text():
    # Create test arguments
    arg = Arg("test_text", ValueType.Text)

    # Test cases for text values
    v1 = ValueInstance(arg_ty=arg, value=Anything())
    v2 = ValueInstance(arg_ty=arg, value="hello")
    v3 = ValueInstance(arg_ty=arg, value=Anything())

    assert v1.implies(v2) == False  # * -> hello
    assert v2.implies(v1) == True  # hello -> *
    assert v1.implies(v3) == True  # * -> *


def test_value_instance_implies_number():
    # Create test arguments
    arg = Arg("test_number", ValueType.Number)

    # Test cases for number values with comparison operators
    v1 = ValueInstance(arg, 5, CmpOp.GreaterThan)
    v2 = ValueInstance(arg, 3, CmpOp.GreaterThan)
    v3 = ValueInstance(arg, 7, CmpOp.GreaterThan)

    assert v1.implies(v2) == True  # x > 5 → x > 3
    assert v1.implies(v3) == False  # x > 5 → x > 7


# Test PredicateInstance implies method
def test_predicate_instance_implies():
    # Create test arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)

    # Create test predicate instances
    p1 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )

    p2 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 3, CmpOp.GreaterThan),
        },
    )

    p3 = PredicateInstance(
        predicate_def=different_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )

    assert p1.implies(p2) == True  # Same predicate, valid implication
    assert p2.implies(p1) == False  # Same predicate, invalid implication
    assert p1.implies(p3) == False  # Different predicate name
    assert p3.implies(p1) == False  # Different predicate name


def test_value_instance_implies_invalid_types():
    # Test with different value types
    bool_arg = Arg("bool_param", ValueType.Boolean)
    text_arg = Arg("text_param", ValueType.Text)

    v1 = ValueInstance(bool_arg, True)
    v2 = ValueInstance(text_arg, "hello")

    # Different types should not imply each other
    assert v1.implies(v2) == False
    assert v2.implies(v1) == False


def test_value_instance_implies_number_edge_cases():
    arg = Arg("test_number", ValueType.Number)

    # Test various comparison operators
    eq_5 = ValueInstance(arg, 5, CmpOp.Equal)
    gt_5 = ValueInstance(arg, 5, CmpOp.GreaterThan)
    gte_5 = ValueInstance(arg, 5, CmpOp.GreaterThanOrEqual)
    lt_5 = ValueInstance(arg, 5, CmpOp.LessThan)
    lte_5 = ValueInstance(arg, 5, CmpOp.LessThanOrEqual)

    # Test implications between different operators
    assert gte_5.implies(gt_5) == False  # x ≥ 5 ↛ x > 5
    assert gt_5.implies(gte_5) == True  # x > 5 → x ≥ 5
    assert eq_5.implies(gte_5) == True  # x = 5 → x ≥ 5
    assert eq_5.implies(lte_5) == True  # x = 5 → x ≤ 5
    assert lt_5.implies(lte_5) == True  # x < 5 → x ≤ 5


def test_basic_contains():
    assert not (p1 in formula)  # x > 3 → x > 5 is not found


# Test edge cases
def test_empty_formula():
    empty_formula = Formula([])
    assert not (p1 in empty_formula)  # Empty formula contains nothing


def test_different_predicate_name():
    p3 = PredicateInstance(
        predicate_def=different_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )
    assert p3 not in formula  # Different predicate name


def test_multiple_predicates():
    p5 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 7, CmpOp.GreaterThan),
        },
    )  # True, x > 7

    multi_formula = Formula([p2, p5])
    assert p1 in multi_formula  # Should find p1 → p2
    assert p5 in multi_formula  # Should find p5 directly
    assert p2 in multi_formula  # Should find p2 directly

    # Test with a predicate that doesn't imply any in the formula
    p6 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 10, CmpOp.GreaterThan),
        },
    )  # True, x > 10
    assert p6 not in multi_formula  # p6 doesn't imply any predicate in the formula


def test_mixed_type_predicates():
    mixed_pred = PredicateInstance(
        predicate_def=mixed_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "text_param": ValueInstance(text_arg, "hello"),
        },
    )

    mixed_formula = Formula([mixed_pred])

    mixed_pred2 = PredicateInstance(
        predicate_def=mixed_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "text_param": ValueInstance(text_arg, "world"),
        },
    )

    assert mixed_pred2 not in mixed_formula  # Different text values


def test_value_instance_implies_anything():
    # Test with Anything value
    bool_arg = Arg("bool_param", ValueType.Boolean)
    text_arg = Arg("text_param", ValueType.Text)
    num_arg = Arg("num_param", ValueType.Number)

    # Create instances with Anything value
    v1 = ValueInstance(bool_arg)  # Default value is Anything
    v2 = ValueInstance(bool_arg, True)
    v3 = ValueInstance(text_arg)
    v4 = ValueInstance(text_arg, "hello")
    v5 = ValueInstance(num_arg)
    v6 = ValueInstance(num_arg, 5, CmpOp.GreaterThan)

    # Test implications with Anything
    assert v2.implies(v1) == True  # Concrete value implies Anything
    assert v1.implies(v2) == False  # Anything doesn't imply concrete value
    assert v4.implies(v3) == True
    assert v3.implies(v4) == False
    assert v6.implies(v5) == True
    assert v5.implies(v6) == False


def test_value_instance_implies_date():
    # Test date comparisons
    date_arg = Arg("date_param", ValueType.Date)

    # Test cases for date values
    v1 = ValueInstance(date_arg, parse("2024-03-15"), CmpOp.GreaterThan)
    v2 = ValueInstance(date_arg, parse("2024-03-10"), CmpOp.GreaterThan)
    v3 = ValueInstance(date_arg, parse("2024-03-20"), CmpOp.GreaterThan)
    v4 = ValueInstance(date_arg, parse("2024-03-15"), CmpOp.Equal)

    assert v1.implies(v2) == True  # x > 2024-03-15 → x > 2024-03-10
    assert v1.implies(v3) == False  # x > 2024-03-15 ↛ x > 2024-03-20
    assert v4.implies(v1) == False  # x = 2024-03-15 ↛ x > 2024-03-15


def test_value_instance_implies_time():
    # Test time comparisons
    time_arg = Arg("time_param", ValueType.Time)

    # Test cases for time values
    v1 = ValueInstance(time_arg, parse("14:30:00"), CmpOp.GreaterThan)
    v2 = ValueInstance(time_arg, parse("13:00:00"), CmpOp.GreaterThan)
    v3 = ValueInstance(time_arg, parse("15:00:00"), CmpOp.GreaterThan)
    v4 = ValueInstance(time_arg, parse("14:30:00"), CmpOp.Equal)

    assert v1.implies(v2) == True  # x > 14:30:00 → x > 13:00:00
    assert v1.implies(v3) == False  # x > 14:30:00 ↛ x > 15:00:00
    assert v4.implies(v1) == False  # x = 14:30:00 ↛ x > 14:30:00


def test_predicate_instance_implies_multiple_arguments():
    # Setup test arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)
    text_arg = Arg("text_param", ValueType.Text)
    date_arg = Arg("date_param", ValueType.Date)

    # Create complex predicates with multiple arguments
    p1 = PredicateInstance(
        predicate_def=complex_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
            "text_param": ValueInstance(text_arg, "hello"),
            "date_param": ValueInstance(date_arg, "2024-03-15", CmpOp.GreaterThan),
        },
    )  # complex_pred(bool_param=True, num_param=(5, >), text_param=hello, date_param=(2024-03-15, >))

    # Same predicate with weaker conditions
    p2 = PredicateInstance(
        predicate_def=complex_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 3, CmpOp.GreaterThan),
            "text_param": ValueInstance(text_arg, Anything()),
            "date_param": ValueInstance(date_arg, "2024-03-10", CmpOp.GreaterThan),
        },
    )  # complex_pred(bool_param=True, num_param=(3, >), text_param=*, date_param=(2024-03-10, >))

    # Same predicate with stronger conditions
    p3 = PredicateInstance(
        predicate_def=complex_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 7, CmpOp.GreaterThan),
            "text_param": ValueInstance(text_arg, "hello"),
            "date_param": ValueInstance(date_arg, "2024-03-20", CmpOp.GreaterThan),
        },
    )  # complex_pred(bool_param=True, num_param=(7, >), text_param=bye, date_param=(2024-03-20, >))

    # Test implications
    assert p1.implies(p2) == True  # Stronger conditions imply weaker ones
    assert p2.implies(p1) == False  # Weaker conditions don't imply stronger ones
    assert p1.implies(p3) == False  # p1 doesn't imply stronger conditions
    assert p3.implies(p1) == True  # p3 is stronger than p1
    assert p1.implies(p1) == True  # same predicate

    # Test with anything arguments
    p4 = PredicateInstance(
        predicate_def=complex_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, Anything()),
            "num_param": ValueInstance(num_arg, Anything()),
            "text_param": ValueInstance(text_arg, Anything()),
            "date_param": ValueInstance(date_arg, Anything()),
        },
    )

    assert (
        p1.implies(p4) == True
    )  # complex_pred(True, x > 5, hello, x > 2024-03-15) -> complex_pred(*, *, *, *)
    assert p4.implies(p1) == False


def test_predicate_instance_is_every_arg_anything():
    # Setup test arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)
    text_arg = Arg("text_param", ValueType.Text)

    # Test case 1: All arguments are Anything
    p1 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, Anything()),
            "num_param": ValueInstance(num_arg, Anything()),
            "text_param": ValueInstance(text_arg, Anything()),
        },
    )
    assert p1.is_every_arg_anything() == True

    # Test case 2: X -> top is always true
    p2 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )
    assert p2.implies(p1) == True


def test_formula_instance_is_every_arg_anything():
    # Setup test arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)
    text_arg = Arg("text_param", ValueType.Text)

    # Create formula with all arguments as Anything
    formula1 = Formula(
        [
            PredicateInstance(
                predicate_def=test_pred_def,
                arguments={
                    "bool_param": ValueInstance(bool_arg, Anything()),
                    "num_param": ValueInstance(num_arg, Anything()),
                    "text_param": ValueInstance(text_arg, Anything()),
                },
            )
        ]
    )

    # Create formula with some arguments as Anything
    formula2 = Formula(
        [
            PredicateInstance(
                predicate_def=test_pred_def,
                arguments={
                    "bool_param": ValueInstance(bool_arg, True),
                },
            )
        ]
    )

    # Test formula with all arguments as Anything
    assert formula2.implies(formula1) == True


def test_bottom_formula():
    # Setup test arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)

    # Create bottom formula
    bottom_formula = Formula([])

    f = Formula(
        [
            PredicateInstance(
                predicate_def=test_pred_def,
                arguments={
                    "bool_param": ValueInstance(bool_arg, True),
                },
            )
        ]
    )

    assert bottom_formula.implies(f) == False  # False -/-> f is False
    assert f.implies(bottom_formula) == True  # f -> False is True


def test_overlapping_predicates():
    # Setup test arguments
    text_arg = Arg("text_param", ValueType.Text)

    # Create overlapping predicates
    p1 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, "hello"),
        },
    )
    p2 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, "world"),
        },
    )

    # Create Formula
    f = Formula([p1, p2])

    # Formula for test
    f_test_1 = Formula([p1])
    f_test_2 = Formula([p2])

    assert f.implies(f_test_1) == True
    assert f.implies(f_test_2) == True


# Test Add operation
def test_add_operation():
    formula = Formula([])
    pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )
    pred_update = PredicateUpdate(predicate=pred, operation=PredicateUpdateOp.Add)
    formula.formula_update(pred_update)
    assert len(formula.formula) == 1
    assert formula.formula[0] == pred


# Test Update operation with strict condition
def test_update_strict_condition():
    base_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )
    formula = Formula([base_pred])

    update_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "num_param": ValueInstance(num_arg, 7, CmpOp.GreaterThan),
        },
    )
    pred_update = PredicateUpdate(
        predicate=update_pred,
        operation=PredicateUpdateOp.Update,
    )
    formula.formula_update(pred_update)
    assert len(formula.formula) == 1
    assert formula.formula[0] == update_pred


# Test Update operation with base condition
def test_update_base_condition():
    base_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )
    formula = Formula([base_pred])

    update_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "num_param": ValueInstance(num_arg, 3, CmpOp.LessThan),
        },
    )
    pred_update = PredicateUpdate(
        predicate=update_pred,
        operation=PredicateUpdateOp.Update,
    )
    formula.formula_update(pred_update)
    assert len(formula.formula) == 1
    assert formula.formula[0] == update_pred


# Test Delete operation
def test_remove_operation():
    pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )
    formula = Formula([pred])

    remove_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )
    pred_update = PredicateUpdate(
        predicate=remove_pred,
        operation=PredicateUpdateOp.Delete,
    )
    formula.formula_update(pred_update)
    assert len(formula.formula) == 0


# Test multiple predicates
def test_multiple_predicates_2():
    pred1 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )
    pred2 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )
    formula = Formula([pred1, pred2])

    update_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, False),
        },
    )
    pred_update = PredicateUpdate(
        predicate=update_pred,
        operation=PredicateUpdateOp.Update,
    )
    formula.formula_update(pred_update)
    assert len(formula.formula) == 2
    assert formula.formula[1] == pred2
    assert formula.formula[0].arguments["bool_param"].value == False


# Test Formula.__dict__ method
def test_formula_dict():
    # Create test arguments and predicates
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)

    pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 5, CmpOp.GreaterThan),
        },
    )

    # Create a formula with the predicate
    formula = Formula([pred])

    # Get the dictionary representation
    formula_dict = formula.__dict__()

    # Verify the structure of the dictionary
    assert "formula" in formula_dict
    assert isinstance(formula_dict["formula"], list)
    assert len(formula_dict["formula"]) == 1


# Test Formula.__iter__ method
def test_formula_iter():
    # Create test arguments and predicates
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)

    pred1 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )

    pred2 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "num_param": ValueInstance(num_arg, 5),
        },
    )

    # Create a formula with multiple predicates
    formula = Formula([pred1, pred2])

    # Use iteration to collect predicates
    iterated_preds = []
    for pred in formula:
        iterated_preds.append(pred)

    # Verify all predicates were iterated over
    assert len(iterated_preds) == 2
    assert pred1 in iterated_preds
    assert pred2 in iterated_preds


# Test Formula.formula_update edge cases
def test_formula_update_edge_cases():
    # Create test arguments and predicates
    text_arg = Arg("text_param", ValueType.Text)

    pred1 = PredicateInstance(
        predicate_def=complex_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, "value1"),
        },
    )

    formula = Formula([])

    empty_pred = PredicateInstance(predicate_def=complex_pred_def, arguments={})
    update_with_empty_pred = PredicateUpdate(
        predicate=empty_pred, operation=PredicateUpdateOp.Update
    )
    formula.formula_update(update_with_empty_pred)

    assert len(formula) == 1
    assert pred1 not in formula, f"{pred1} is in {str(formula)}"


def empty_value_predicate():
    pred1 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={},
    )
    pred2 = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
        },
    )
    formula1 = Formula([pred1])
    empty_formula = Formula([])
    assert formula1.implies(empty_formula) == True
    assert empty_formula.implies(formula1) == False

    formula2 = Formula([pred2])
    assert formula.implies(formula2) == False
    assert formula2.implies(formula) == False

    formula3 = Formula([pred1, pred2])
    assert formula3.implies(formula2) == True
    assert formula3.implies(formula1) == True
    assert formula2.implies(formula3) == False
    assert formula1.implies(formula3) == False


def anything_comparison():
    any1 = Anything()
    any2 = Anything2()
    any3 = ValueInstance(bool_arg).value
    not_any = "not_anything"
    assert any1 == any2
    assert any1 == any3
    assert any2 == any3
    assert any1 != not_any
    assert any2 != not_any
    assert any3 != not_any


# Test PredicateInstance with predicate_def
def test_predicate_instance_with_predicate_def():
    # Create arguments
    key_arg = Arg("id", ValueType.Text)
    name_arg = Arg("name", ValueType.Text)
    age_arg = Arg("age", ValueType.Number)

    # Create predicate definition
    person_def = PredicateDef(
        name="Person",
        arguments={"id": key_arg, "name": name_arg, "age": age_arg},
        description="A person with ID, name and age",
        arg_keys=["id"],
    )

    # Create a predicate instance with predicate_def
    person = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "John"),
            "age": ValueInstance(age_arg, 30),
        },
    )

    # Test has_key method
    assert person.has_key() == True

    # Test get_key_value method
    key_args = person.get_key_args()
    assert len(key_args) == 1
    assert key_args[0].arg_ty.name == "id"
    assert key_args[0].value == "person-123"


# Test PredicateInstance with matching keys
def test_predicate_instance_matches_key():
    # Create arguments
    key_arg = Arg("id", ValueType.Text)
    name_arg = Arg("name", ValueType.Text)

    # Create predicate definition
    person_def = PredicateDef(
        name="Person",
        arguments={"id": key_arg, "name": name_arg},
        description="A person with ID and name",
        arg_keys=["id"],
    )

    # Create two predicate instances with the same key
    person1 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "John"),
        },
    )

    person2 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "Johnny"),
        },
    )

    # Create a predicate instance with a different key
    person3 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-456"),
            "name": ValueInstance(name_arg, "Jane"),
        },
    )

    # Test matches_key method
    assert person1.matches_key(person2) == True
    assert person2.matches_key(person1) == True
    assert person1.matches_key(person3) == False
    assert person3.matches_key(person1) == False


# Test Formula.find_closest with key
def test_formula_find_closest_with_key():
    # Create arguments
    key_arg = Arg("id", ValueType.Text)
    name_arg = Arg("name", ValueType.Text)

    # Create predicate definition
    person_def = PredicateDef(
        name="Person",
        arguments={"id": key_arg, "name": name_arg},
        description="A person with ID and name",
        arg_keys=["id"],
    )

    # Create predicates with different keys
    person1 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "John"),
        },
    )

    person2 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-456"),
            "name": ValueInstance(name_arg, "Jane"),
        },
    )

    # Create a formula with these predicates
    formula = Formula([person1, person2])

    # Create a search predicate with matching key to person1
    search_pred = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "Changed Name"),
        },
    )

    # Test find_closest finds the matching key
    found_pred = formula.find_closest(search_pred)
    assert found_pred is not None
    assert found_pred == person1

    # Create a search predicate with non-matching key
    search_pred_no_match = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-789"),
            "name": ValueInstance(name_arg, "Unknown"),
        },
    )

    # Test find_closest returns None for non-matching key
    found_pred = formula.find_closest(search_pred_no_match)
    assert found_pred is None


# Test Formula.formula_update with key
def test_formula_update_with_key():
    # Create arguments
    key_arg = Arg("id", ValueType.Text)
    name_arg = Arg("name", ValueType.Text)

    # Create predicate definition
    person_def = PredicateDef(
        name="Person",
        arguments={"id": key_arg, "name": name_arg},
        description="A person with ID and name",
        arg_keys=["id"],
    )

    # Create initial predicate
    person1 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "John"),
        },
    )

    # Create a formula with this predicate
    formula = Formula([person1])

    # Create an updated predicate with the same key
    person1_updated = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-123"),
            "name": ValueInstance(name_arg, "John Doe"),
        },
    )

    # Create an update operation
    update_op = PredicateUpdate(
        predicate=person1_updated, operation=PredicateUpdateOp.Update
    )

    # Apply the update
    formula.formula_update(update_op)

    # Test that the formula has been updated correctly
    assert len(formula) == 1
    assert formula.formula[0] == person1_updated
    assert formula.formula[0].arguments["name"].value == "John Doe"

    # Create a new predicate with a different key
    person2 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(key_arg, "person-456"),
            "name": ValueInstance(name_arg, "Jane"),
        },
    )

    # Create an add operation
    add_op = PredicateUpdate(predicate=person2, operation=PredicateUpdateOp.Add)

    # Apply the add
    formula.formula_update(add_op)

    # Test that the formula now has both predicates
    assert len(formula) == 2
    assert person1_updated in formula.formula
    assert person2 in formula.formula

    # Create a remove operation for the first predicate
    remove_op = PredicateUpdate(
        predicate=PredicateInstance(
            predicate_def=person_def,
            arguments={
                "id": ValueInstance(key_arg, "person-123"),
            },
        ),
        operation=PredicateUpdateOp.Delete,
    )

    # Apply the remove
    formula.formula_update(remove_op)

    # Test that the first predicate has been removed
    assert len(formula) == 1
    assert formula.formula[0] == person2


# Test Formula.formula_update with unknown values
def test_formula_update_with_unknown_values():
    # Create test arguments
    text_arg = Arg("text_param", ValueType.Text)
    num_arg = Arg("num_param", ValueType.Number)
    bool_arg = Arg("bool_param", ValueType.Boolean)

    # Create predicate definition
    test_pred_def = PredicateDef(
        name="TestPredicate",
        arguments={
            "text_param": text_arg,
            "num_param": num_arg,
            "bool_param": bool_arg,
        },
        description="Test predicate with multiple parameters",
    )

    # Create initial predicate with all values specified
    initial_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, "initial text"),
            "num_param": ValueInstance(num_arg, 100),
            "bool_param": ValueInstance(bool_arg, True),
        },
    )

    # Create a formula with this predicate
    formula = Formula([initial_pred])

    # Create an update predicate with some unknown values
    update_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, "updated text"),
            "num_param": ValueInstance(num_arg, get_unknown()),  # Unknown value
            "bool_param": ValueInstance(bool_arg, False),
        },
    )

    # Create an update operation
    update_op = PredicateUpdate(
        predicate=update_pred, operation=PredicateUpdateOp.Update
    )

    # Apply the update
    formula.formula_update(update_op)

    # Test that the formula has been updated correctly
    assert len(formula) == 1
    updated_pred = formula.formula[0]

    # Check that text_param and bool_param were updated
    assert updated_pred.arguments["text_param"].value == "updated text"
    assert updated_pred.arguments["bool_param"].value == False

    # Check that num_param was NOT updated (remained the same) because it was unknown in the update
    assert updated_pred.arguments["num_param"].value == 100

    # Test with a predicate that has all unknown values
    all_unknown_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, get_unknown()),
            "num_param": ValueInstance(num_arg, get_unknown()),
            "bool_param": ValueInstance(bool_arg, get_unknown()),
        },
    )

    # Create an update operation
    all_unknown_update_op = PredicateUpdate(
        predicate=all_unknown_pred, operation=PredicateUpdateOp.Update
    )

    # Apply the update
    formula.formula_update(all_unknown_update_op)

    # Test that the formula was not changed (all values remained the same)
    assert len(formula) == 1
    unchanged_pred = formula.formula[0]

    assert unchanged_pred.arguments["text_param"].value == "updated text"
    assert unchanged_pred.arguments["num_param"].value == 100
    assert unchanged_pred.arguments["bool_param"].value == False

    # Test with a mix of known and unknown values in a new predicate
    mixed_pred = PredicateInstance(
        predicate_def=test_pred_def,
        arguments={
            "text_param": ValueInstance(text_arg, get_unknown()),
            "num_param": ValueInstance(num_arg, 200),
            "bool_param": ValueInstance(bool_arg, get_unknown()),
        },
    )

    # Create an update operation
    mixed_update_op = PredicateUpdate(
        predicate=mixed_pred, operation=PredicateUpdateOp.Update
    )

    # Apply the update
    formula.formula_update(mixed_update_op)

    # Test that only the non-unknown values were updated
    assert len(formula) == 1
    partially_updated_pred = formula.formula[0]

    assert (
        partially_updated_pred.arguments["text_param"].value == "updated text"
    )  # Unchanged
    assert partially_updated_pred.arguments["num_param"].value == 200  # Updated
    assert partially_updated_pred.arguments["bool_param"].value == False  # Unchanged


# Test Formula.formula_update with multiple key arguments
def test_formula_update_with_multiple_key_args():
    # Create arguments
    id_arg = Arg("id", ValueType.Text)
    type_arg = Arg("type", ValueType.Text)
    name_arg = Arg("name", ValueType.Text)
    value_arg = Arg("value", ValueType.Number)

    # Create predicate definition with multiple key arguments
    item_def = PredicateDef(
        name="Item",
        arguments={
            "id": id_arg,
            "type": type_arg,
            "name": name_arg,
            "value": value_arg,
        },
        description="An item with ID, type, name and value",
        arg_keys=["id", "type"],  # Multiple keys
    )

    # Create initial predicate
    item1 = PredicateInstance(
        predicate_def=item_def,
        arguments={
            "id": ValueInstance(id_arg, "item-123"),
            "type": ValueInstance(type_arg, "equipment"),
            "name": ValueInstance(name_arg, "Sword"),
            "value": ValueInstance(value_arg, 100),
        },
    )

    # Create a formula with this predicate
    formula = Formula([item1])

    # Create an updated predicate with the same keys
    item1_updated = PredicateInstance(
        predicate_def=item_def,
        arguments={
            "id": ValueInstance(id_arg, "item-123"),
            "type": ValueInstance(type_arg, "equipment"),
            "name": ValueInstance(name_arg, "Magic Sword"),
            "value": ValueInstance(value_arg, 200),
        },
    )

    # Create an update operation
    update_op = PredicateUpdate(
        predicate=item1_updated, operation=PredicateUpdateOp.Update
    )

    # Apply the update
    formula.formula_update(update_op)

    # Test that the formula has been updated correctly
    assert len(formula) == 1
    assert formula.formula[0] == item1_updated
    assert formula.formula[0].arguments["name"].value == "Magic Sword"
    assert formula.formula[0].arguments["value"].value == 200

    # Create a new predicate with different keys
    item2 = PredicateInstance(
        predicate_def=item_def,
        arguments={
            "id": ValueInstance(id_arg, "item-123"),  # Same id
            "type": ValueInstance(type_arg, "consumable"),  # Different type
            "name": ValueInstance(name_arg, "Potion"),
            "value": ValueInstance(value_arg, 50),
        },
    )

    # Create an add operation
    add_op = PredicateUpdate(predicate=item2, operation=PredicateUpdateOp.Add)

    # Apply the add
    formula.formula_update(add_op)

    # Test that the formula now has both predicates (since they have different keys)
    assert len(formula) == 2
    assert item1_updated in formula.formula
    assert item2 in formula.formula

    # Create a partial key match predicate (only one key matches)
    partial_match = PredicateInstance(
        predicate_def=item_def,
        arguments={
            "id": ValueInstance(id_arg, "item-123"),  # Same id
            "type": ValueInstance(type_arg, "equipment"),  # Same type as item1_updated
            "name": ValueInstance(name_arg, "Enhanced Sword"),
            "value": ValueInstance(value_arg, 300),
        },
    )

    # Create an update operation
    partial_update_op = PredicateUpdate(
        predicate=partial_match, operation=PredicateUpdateOp.Update
    )

    # Apply the update
    formula.formula_update(partial_update_op)

    # Test that only the matching predicate was updated
    assert len(formula) == 2

    # Find the updated item
    updated_item = None
    for pred in formula.formula:
        if (
            pred.arguments["id"].value == "item-123"
            and pred.arguments["type"].value == "equipment"
        ):
            updated_item = pred
            break

    assert updated_item is not None
    assert updated_item.arguments["name"].value == "Enhanced Sword"
    assert updated_item.arguments["value"].value == 300

    # Create a remove operation with both keys specified
    remove_op = PredicateUpdate(
        predicate=PredicateInstance(
            predicate_def=item_def,
            arguments={
                "id": ValueInstance(id_arg, "item-123"),
                "type": ValueInstance(type_arg, "equipment"),
            },
        ),
        operation=PredicateUpdateOp.Delete,
    )

    # Apply the remove
    formula.formula_update(remove_op)

    # Test that only the matching predicate has been removed
    assert len(formula) == 1
    assert formula.formula[0].arguments["id"].value == "item-123"
    assert formula.formula[0].arguments["type"].value == "consumable"


# Test PredicateDef.__eq__ method
def test_predicate_def_eq():
    # Create basic arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)
    text_arg = Arg("text_param", ValueType.Text)

    # Create enum argument
    enum_values = EnumValues(["RED", "GREEN", "BLUE"])
    color_arg = Arg("color", ValueType.Enum, enum_values)

    # Create predicate definitions
    pred_def1 = PredicateDef(
        name="TestPredicate",
        arguments={"bool_param": bool_arg, "num_param": num_arg},
        description="Test predicate description",
        arg_keys=["bool_param"],
    )

    # Same definition with different description (should still be equal)
    pred_def2 = PredicateDef(
        name="TestPredicate",
        arguments={"bool_param": bool_arg, "num_param": num_arg},
        description="Different description",
        arg_keys=["bool_param"],
    )

    # Different name
    pred_def3 = PredicateDef(
        name="DifferentName",
        arguments={"bool_param": bool_arg, "num_param": num_arg},
        description="Test predicate description",
        arg_keys=["bool_param"],
    )

    # Different arguments
    pred_def4 = PredicateDef(
        name="TestPredicate",
        arguments={"bool_param": bool_arg, "text_param": text_arg},
        description="Test predicate description",
        arg_keys=["bool_param"],
    )

    # Different arg_keys
    pred_def5 = PredicateDef(
        name="TestPredicate",
        arguments={"bool_param": bool_arg, "num_param": num_arg},
        description="Test predicate description",
        arg_keys=["num_param"],
    )

    # Additional argument
    pred_def6 = PredicateDef(
        name="TestPredicate",
        arguments={
            "bool_param": bool_arg,
            "num_param": num_arg,
            "text_param": text_arg,
        },
        description="Test predicate description",
        arg_keys=["bool_param"],
    )

    # With enum argument
    pred_def7 = PredicateDef(
        name="ColorPredicate",
        arguments={"color": color_arg},
        description="Color predicate",
        arg_keys=["color"],
    )

    # Same as pred_def7 but with different enum values
    different_enum_values = EnumValues(["RED", "GREEN", "YELLOW"])
    different_color_arg = Arg("color", ValueType.Enum, different_enum_values)
    pred_def8 = PredicateDef(
        name="ColorPredicate",
        arguments={"color": different_color_arg},
        description="Color predicate",
        arg_keys=["color"],
    )

    # Test equality
    assert pred_def1 == pred_def1  # Same object
    assert pred_def1 == pred_def2  # Different description, should still be equal
    assert pred_def1 != pred_def3  # Different name
    assert pred_def1 != pred_def4  # Different arguments
    assert pred_def1 != pred_def5  # Different arg_keys
    assert pred_def1 != pred_def6  # Additional argument
    assert pred_def7 != pred_def8  # Different enum values


# Test PredicateInstance.__eq__ method
def test_predicate_instance_eq():
    # Create basic arguments
    bool_arg = Arg("bool_param", ValueType.Boolean)
    num_arg = Arg("num_param", ValueType.Number)
    text_arg = Arg("text_param", ValueType.Text)

    # Create predicate definitions
    pred_def1 = PredicateDef(
        name="TestPredicate",
        arguments={"bool_param": bool_arg, "num_param": num_arg},
        description="Test predicate description",
        arg_keys=["bool_param"],
    )

    pred_def2 = PredicateDef(
        name="DifferentPredicate",
        arguments={"bool_param": bool_arg, "num_param": num_arg},
        description="Different predicate",
        arg_keys=["bool_param"],
    )

    # Create predicate instances
    pred_instance1 = PredicateInstance(
        predicate_def=pred_def1,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 42),
        },
    )

    # Same as pred_instance1
    pred_instance2 = PredicateInstance(
        predicate_def=pred_def1,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 42),
        },
    )

    # Different argument value
    pred_instance3 = PredicateInstance(
        predicate_def=pred_def1,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 100),
        },
    )

    # Different argument type name
    pred_instance4 = PredicateInstance(
        predicate_def=pred_def1,
        arguments={
            "bool_param": ValueInstance(Arg("different_name", ValueType.Boolean), True),
            "num_param": ValueInstance(num_arg, 42),
        },
    )

    # Different comparison operator
    pred_instance5 = PredicateInstance(
        predicate_def=pred_def1,
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 42, CmpOp.GreaterThan),
        },
    )

    # Different predicate definition but same name and arguments
    pred_instance6 = PredicateInstance(
        predicate_def=pred_def2,  # Different predicate definition
        arguments={
            "bool_param": ValueInstance(bool_arg, True),
            "num_param": ValueInstance(num_arg, 42),
        },
    )

    # Test equality
    assert pred_instance1 == pred_instance1  # Same object
    assert pred_instance1 == pred_instance2  # Same values
    assert pred_instance1 != pred_instance3  # Different argument value
    assert pred_instance1 != pred_instance4  # Different argument type name
    assert pred_instance1 != pred_instance5  # Different comparison operator
    assert (
        pred_instance1 != pred_instance6
    )  # Different predicate definition but same name and arguments

    # Test with non-PredicateInstance object
    assert pred_instance1 != "not a predicate instance"


# Test PredicateInstance.matches_key method with more complex cases
def test_predicate_instance_matches_key_complex():
    # Create arguments
    id_arg = Arg("id", ValueType.Text)
    name_arg = Arg("name", ValueType.Text)
    age_arg = Arg("age", ValueType.Number)

    # Create predicate definition with single key
    person_def = PredicateDef(
        name="Person",
        arguments={"id": id_arg, "name": name_arg, "age": age_arg},
        description="A person with ID, name and age",
        arg_keys=["id"],
    )

    # Create predicate definition with multiple keys
    employee_def = PredicateDef(
        name="Employee",
        arguments={"id": id_arg, "name": name_arg, "age": age_arg},
        description="An employee with ID, name and age",
        arg_keys=["id", "name"],
    )

    # Create predicate definition with no keys
    generic_def = PredicateDef(
        name="Generic",
        arguments={"name": name_arg, "age": age_arg},
        description="A generic entity with name and age",
        arg_keys=[],
    )

    # Create instances with single key
    person1 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(id_arg, "person-123"),
            "name": ValueInstance(name_arg, "John"),
            "age": ValueInstance(age_arg, 30),
        },
    )

    person2 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(id_arg, "person-123"),
            "name": ValueInstance(name_arg, "John Updated"),
            "age": ValueInstance(age_arg, 31),
        },
    )

    person3 = PredicateInstance(
        predicate_def=person_def,
        arguments={
            "id": ValueInstance(id_arg, "person-456"),
            "name": ValueInstance(name_arg, "John"),
            "age": ValueInstance(age_arg, 30),
        },
    )

    # Create instances with multiple keys
    employee1 = PredicateInstance(
        predicate_def=employee_def,
        arguments={
            "id": ValueInstance(id_arg, "emp-123"),
            "name": ValueInstance(name_arg, "Alice"),
            "age": ValueInstance(age_arg, 28),
        },
    )

    employee2 = PredicateInstance(
        predicate_def=employee_def,
        arguments={
            "id": ValueInstance(id_arg, "emp-123"),
            "name": ValueInstance(name_arg, "Alice"),
            "age": ValueInstance(age_arg, 29),
        },
    )

    employee3 = PredicateInstance(
        predicate_def=employee_def,
        arguments={
            "id": ValueInstance(id_arg, "emp-123"),
            "name": ValueInstance(name_arg, "Bob"),
            "age": ValueInstance(age_arg, 28),
        },
    )

    # Create instances with no keys
    generic1 = PredicateInstance(
        predicate_def=generic_def,
        arguments={
            "name": ValueInstance(name_arg, "Generic1"),
            "age": ValueInstance(age_arg, 25),
        },
    )

    generic2 = PredicateInstance(
        predicate_def=generic_def,
        arguments={
            "name": ValueInstance(name_arg, "Generic2"),
            "age": ValueInstance(age_arg, 26),
        },
    )

    # Test single key matching
    assert person1.matches_key(person2) == True
    assert person2.matches_key(person1) == True
    assert person1.matches_key(person3) == False
    assert person3.matches_key(person1) == False

    # Test multiple key matching
    assert employee1.matches_key(employee2) == True
    assert employee2.matches_key(employee1) == True
    assert employee1.matches_key(employee3) == False
    assert employee3.matches_key(employee1) == False

    # Test no key matching
    assert generic1.matches_key(generic2) == False

    # Test matching between different predicate definitions
    assert person1.matches_key(employee1) == False

    # Test with different predicate definition but same key structure
    different_person_def = PredicateDef(
        name="DifferentPerson",
        arguments={"id": id_arg, "name": name_arg, "age": age_arg},
        description="A different person entity",
        arg_keys=["id"],
    )

    different_person = PredicateInstance(
        predicate_def=different_person_def,
        arguments={
            "id": ValueInstance(id_arg, "person-123"),
            "name": ValueInstance(name_arg, "John"),
            "age": ValueInstance(age_arg, 30),
        },
    )

    assert person1.matches_key(different_person) == False
