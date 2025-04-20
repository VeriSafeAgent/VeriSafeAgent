from datetime import datetime
from dateutil.parser import parse
import os
import sys
import unittest

# Adjust sys.path to import modules from the verifier directory and its parent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_verifier.verifier.collect import (
    parse_predicate_defs,
    parse_predicate_instance_dict,
)
from agent_verifier.verifier.data_type import (
    ValueType,
    Arg,
    PredicateDefDict,
    PredicateDef,
    CmpOp,
    get_unknown,
    Formula,
    PredicateInstance,
    ValueInstance,
)
from agent_verifier.verifier.llm_output_parser import (
    Parser,
    UndefinedPredicateHandleOption,
)


class TestParseFunctions(unittest.TestCase):

    def test_parse_predicates_valid(self):
        # Define valid raw predicates with non-enum and enum types
        raw_predicates = {
            "pred_bool_text": {
                "key_arg_name": "flag",
                "arguments": [
                    {"name": "flag", "type": "Boolean"},
                    {"name": "text", "type": "Text"},
                ],
                "description": "Testing boolean and text",
            },
            "pred_enum": {
                "key_arg_name": "",
                "arguments": [
                    {
                        "name": "choice",
                        "type": "Enum",
                        "enum_values": ["option1", "option2"],
                    }
                ],
                "description": "Testing enum",
            },
        }

        # Call parse_predicates
        result = parse_predicate_defs(raw_predicates)

        # Verify that both predicates are present with correct attributes
        self.assertIn("pred_bool_text", result)
        self.assertIn("pred_enum", result)

        pred_bool_text = result["pred_bool_text"]
        self.assertEqual(pred_bool_text.name, "pred_bool_text")
        self.assertEqual(pred_bool_text.description, "Testing boolean and text")
        self.assertEqual(len(pred_bool_text.arguments), 2)
        self.assertEqual(pred_bool_text.arguments["flag"].type, ValueType.Boolean)
        self.assertEqual(pred_bool_text.arguments["text"].type, ValueType.Text)

        pred_enum = result["pred_enum"]
        self.assertEqual(pred_enum.name, "pred_enum")
        self.assertEqual(pred_enum.description, "Testing enum")
        self.assertEqual(len(pred_enum.arguments), 1)
        self.assertEqual(pred_enum.arguments["choice"].type, ValueType.Enum)
        # Check that enum values are correctly set
        self.assertEqual(
            pred_enum.arguments["choice"].enum_values.values, ["option1", "option2"]
        )

    def test_parse_predicates_invalid_type(self):
        # Define a predicate with an invalid type to trigger ValueError
        raw_predicates_invalid = {
            "pred_invalid": {
                "arguments": [{"name": "value", "type": "InvalidType"}],
                "description": "Invalid type",
            }
        }

        with self.assertRaises(ValueError):
            parse_predicate_defs(raw_predicates_invalid)

    def test_parse_predicate_and_value_valid(self):
        # First, create valid predicate definitions
        raw_pred_defs = {
            "pred1": {
                "key_arg_name": "",
                "arguments": [{"name": "flag", "type": "Boolean"}],
                "description": "A boolean predicate",
            },
            "pred2": {
                "key_arg_name": "",
                "arguments": [{"name": "number", "type": "Number"}],
                "description": "A number predicate",
            },
        }
        pred_defs = parse_predicate_defs(raw_pred_defs)

        # Define raw predicate instances matching the definitions
        raw_instances = {
            "pred1": {
                "operation": "Add",
                "key_arg_name": "",
                "arguments": {"flag": {"value": True, "compare_op": "=="}},
            },
            "pred2": {
                "operation": "Update",
                "key_arg_name": "",
                "arguments": {"number": {"value": 42, "compare_op": "!="}},
            },
        }

        result = parse_predicate_instance_dict(raw_instances, pred_defs)

        # Verify that both predicate instances are correctly parsed
        self.assertIn("pred1", result)
        self.assertIn("pred2", result)

        pred1_instance = result["pred1"]
        self.assertEqual(pred1_instance.name, "pred1")
        self.assertEqual(len(pred1_instance.arguments), 1)
        self.assertEqual(pred1_instance.arguments["flag"].value, True)

        pred2_instance = result["pred2"]
        self.assertEqual(pred2_instance.name, "pred2")
        self.assertEqual(len(pred2_instance.arguments), 1)
        self.assertEqual(pred2_instance.arguments["number"].value, 42)

    def test_parse_predicate_and_value_missing_predicate(self):
        # Define predicate definitions with only 'pred1'
        raw_pred_defs = {
            "pred1": {
                "arguments": [{"name": "flag", "type": "Boolean"}],
                "description": "A boolean predicate",
            }
        }
        pred_defs = parse_predicate_defs(raw_pred_defs)

        # Define an instance for a non-existent predicate 'pred_missing'
        raw_instances = {
            "pred_missing": {
                "operation": "Add",
                "arguments": {"flag": {"value": True, "compare_op": "=="}},
            }
        }

        with self.assertRaises(ValueError):
            parse_predicate_instance_dict(raw_instances, pred_defs)

    def test_parse_predicate_and_value_missing_variable(self):
        # Define predicate definitions
        raw_pred_defs = {
            "pred1": {
                "arguments": [{"name": "flag", "type": "Boolean"}],
                "description": "A boolean predicate",
            }
        }
        pred_defs = parse_predicate_defs(raw_pred_defs)

        # Define an instance with a variable not defined in the predicate definition
        raw_instances = {
            "pred1": {
                "operation": "Add",
                "arguments": {"nonexistent": {"value": False, "compare_op": "=="}},
            }
        }

        result = parse_predicate_instance_dict(raw_instances, pred_defs)
        self.assertEqual(result["pred1"].arguments["flag"].value, get_unknown())

    def test_parse_predicate_and_value_invalid_operation(self):
        # Define predicate definitions
        raw_pred_defs = {
            "pred1": {
                "arguments": [{"name": "flag", "type": "Boolean"}],
                "description": "A boolean predicate",
            }
        }
        pred_defs = parse_predicate_defs(raw_pred_defs)

        # Define an instance with an invalid operation
        raw_instances = {
            "pred1": {
                "arguments": {"flag": {"value": True, "compare_op": "==="}},
            }
        }

        with self.assertRaises(ValueError):
            parse_predicate_instance_dict(raw_instances, pred_defs)


class TestParser(unittest.TestCase):
    def setUp(self):
        # Setup common predicate definitions
        self.predicates = PredicateDefDict(
            {
                "BoolPred": PredicateDef(
                    name="BoolPred",
                    arguments={"flag": Arg(name="flag", type=ValueType.Boolean)},
                    description="A boolean predicate",
                ),
                "NumPred": PredicateDef(
                    name="NumPred",
                    arguments={"number": Arg(name="number", type=ValueType.Number)},
                    description="A number predicate",
                ),
                "TextPred": PredicateDef(
                    name="TextPred",
                    arguments={"text": Arg(name="text", type=ValueType.Text)},
                    description="A text predicate",
                ),
            }
        )

        # Create parser instances with different configurations
        self.parser = Parser(self.predicates)
        self.error_parser = Parser(
            self.predicates,
            reject_undefined_predicate=UndefinedPredicateHandleOption.Error,
        )
        self.leave_parser = Parser(
            self.predicates,
            reject_undefined_predicate=UndefinedPredicateHandleOption.Leave,
        )

    def test_parse_cmp_op(self):
        # Test parsing of comparison operators
        self.assertEqual(Parser.parse_cmp_op("=="), CmpOp.Equal)
        self.assertEqual(Parser.parse_cmp_op("="), CmpOp.Equal)
        self.assertEqual(Parser.parse_cmp_op("!="), CmpOp.NotEqual)
        self.assertEqual(Parser.parse_cmp_op(">"), CmpOp.GreaterThan)
        self.assertEqual(Parser.parse_cmp_op("<"), CmpOp.LessThan)
        self.assertEqual(Parser.parse_cmp_op(">="), CmpOp.GreaterThanOrEqual)
        self.assertEqual(Parser.parse_cmp_op("<="), CmpOp.LessThanOrEqual)
        self.assertIsNone(Parser.parse_cmp_op(None))

        # Test invalid operator
        with self.assertRaises(ValueError):
            Parser.parse_cmp_op("invalid")

    def test_parse_raw_value(self):
        # Test parsing of boolean values
        bool_arg = Arg(name="flag", type=ValueType.Boolean)
        self.assertEqual(Parser.parse_raw_value("true", bool_arg), True)
        self.assertEqual(Parser.parse_raw_value("false", bool_arg), False)

        # Test parsing of number values
        num_arg = Arg(name="number", type=ValueType.Number)
        self.assertEqual(Parser.parse_raw_value("42", num_arg), 42)

        # Test parsing of text values
        text_arg = Arg(name="text", type=ValueType.Text)
        self.assertEqual(Parser.parse_raw_value("hello", text_arg), "hello")
        self.assertEqual(Parser.parse_raw_value('"hello"', text_arg), "hello")

        # Test parsing of date values
        date_arg = Arg(name="date", type=ValueType.Date)
        self.assertEqual(
            Parser.parse_raw_value("2023-01-15", date_arg), datetime(2023, 1, 15)
        )

        # Test parsing of time values
        time_arg = Arg(name="time", type=ValueType.Time)
        self.assertEqual(
            Parser.parse_raw_value("12:30:45", time_arg), parse("12:30:45")
        )

        # Test invalid values
        self.assertEqual(Parser.parse_raw_value("invalid", bool_arg), get_unknown())

        with self.assertRaises(ValueError):
            Parser.parse_raw_value("2023-15-01", date_arg)

        with self.assertRaises(ValueError):
            Parser.parse_raw_value("25:30:45", time_arg)

    def test_split_args(self):
        # Test splitting simple arguments
        args = "flag=true, number=42, text=hello"
        result = self.parser.split_args(args)
        self.assertEqual(result["flag"], "true")
        self.assertEqual(result["number"], "42")
        self.assertEqual(result["text"], "hello")

        # Test with nested parentheses
        args = "flag=true, complex=(42, >), text=hello"
        result = self.parser.split_args(args)
        self.assertEqual(result["flag"], "true")
        self.assertEqual(result["complex"], "(42, >)")
        self.assertEqual(result["text"], "hello")

        # Test with unnamed arguments
        args = "true, 42, hello"
        result = self.parser.split_args(args)
        self.assertEqual(result["arg_0"], "true")
        self.assertEqual(result["arg_1"], "42")
        self.assertEqual(result["arg_2"], "hello")

    def test_set_equivalent(self):
        # Test equivalent lists
        self.assertTrue(self.parser.set_equivalent(["a", "b", "c"], ["a", "b", "c"]))
        self.assertTrue(self.parser.set_equivalent(["a", "b", "c"], ["c", "b", "a"]))

        # Test non-equivalent lists
        self.assertFalse(self.parser.set_equivalent(["a", "b"], ["a", "b", "c"]))
        self.assertFalse(self.parser.set_equivalent(["a", "b", "c"], ["a", "b"]))
        self.assertFalse(self.parser.set_equivalent(["a", "b", "c"], ["a", "b", "d"]))

    def test_arg_type_guess(self):
        # Test type guessing for different values
        arg_dict = {"bool_val": "true", "num_val": "42", "text_val": "hello"}

        result = Parser.arg_type_guess(arg_dict)
        self.assertEqual(len(result), 3)

        for arg in result.values():
            if arg.name == "bool_val":
                self.assertEqual(arg.type, ValueType.Boolean)
            elif arg.name == "num_val":
                self.assertEqual(arg.type, ValueType.Number)
            elif arg.name == "text_val":
                self.assertEqual(arg.type, ValueType.Text)

    def test_parse_predicate_instance_dict(self):
        # Test parsing a valid predicate instance
        pred_instance = self.parser.parse_predicate_instance("BoolPred(flag=true)")
        if pred_instance is not None:
            self.assertEqual(pred_instance.name, "BoolPred")
            self.assertEqual(len(pred_instance.arguments), 1)
            self.assertEqual(pred_instance.arguments["flag"].value, True)

        # Test parsing with undefined predicate in different modes
        # Drop mode (default)
        pred_instance = self.parser.parse_predicate_instance("UndefinedPred(value=42)")
        self.assertIsNone(pred_instance)

        # Error mode
        with self.assertRaises(ValueError):
            self.error_parser.parse_predicate_instance("UndefinedPred(value=42)")

        # Leave mode
        pred_instance = self.leave_parser.parse_predicate_instance(
            "UndefinedPred(value=42)"
        )
        if pred_instance is not None:
            self.assertEqual(pred_instance.name, "UndefinedPred")
            self.assertEqual(len(pred_instance.arguments), 1)

        # Test True/empty condition
        self.assertIsNone(self.parser.parse_predicate_instance("True"))
        self.assertIsNone(self.parser.parse_predicate_instance(""))

        # Test invalid format
        with self.assertRaises(ValueError):
            self.parser.parse_predicate_instance("InvalidFormat")

    def test_parse(self):
        # Test parsing with no CHC section
        result = self.parser.parse("No CHC section here")
        self.assertEqual(len(result), 0)

        # Test parsing with empty input
        result = self.parser.parse("")
        self.assertEqual(len(result), 0)

        # Test parsing with None input
        result = self.parser.parse(None)
        self.assertEqual(len(result), 0)

        # Test parsing with valid CHC section
        valid_chc = """
        <CHC>
        BoolPred(flag=true) → NumPredAction()
        NumPred(number=42) → TextPredAction()
        </CHC>
        """
        self.setUp()
        result = self.parser.parse(valid_chc)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].action.name, "NumPredAction")
        self.assertEqual(result[1].action.name, "TextPredAction")

    def test_repeated_action_names_generation(self):
        """Test generation of repeated action names when num_repeat > 1."""
        # Create a parser with an empty predicate dictionary
        parser = Parser(PredicateDefDict({}))

        # Test generating repeated action names
        repeated_actions = parser.generate_repeated_action_names("TestAction", 3)

        # Verify correct number of actions generated
        self.assertEqual(len(repeated_actions), 3)

        # Verify action names are correctly formatted
        self.assertEqual(repeated_actions[0].name, "TestAction1")
        self.assertEqual(repeated_actions[1].name, "TestAction2")
        self.assertEqual(repeated_actions[2].name, "TestAction3")

        # Verify actions are added to predicate dictionary
        self.assertIn("TestAction1", parser.predicates)
        self.assertIn("TestAction2", parser.predicates)
        self.assertIn("TestAction3", parser.predicates)

        # Verify all generated actions are marked as actions
        for action in repeated_actions:
            self.assertTrue(action.is_action)
            self.assertEqual(action.arguments, {})

    def test_unrolled_chcs_generation(self):
        """Test generation of unrolled CHCs from repeated actions."""
        # Create predicates dictionary with a condition predicate
        predicates = PredicateDefDict(
            {
                "ConditionPred": PredicateDef(
                    name="ConditionPred",
                    arguments={"flag": Arg(name="flag", type=ValueType.Boolean)},
                    is_action=False,
                    description="A condition predicate",
                )
            }
        )
        parser = Parser(predicates)

        # Create condition instance
        condition_instance = PredicateInstance(
            predicate_def=predicates["ConditionPred"],
            arguments={
                "flag": ValueInstance(
                    arg_ty=Arg(name="flag", type=ValueType.Boolean), value=True
                )
            },
        )
        conditions = Formula([condition_instance])

        # Generate action names
        action_defs = parser.generate_repeated_action_names("RepeatAction", 3)

        # Generate unrolled CHCs
        unrolled_chcs = parser.generate_unrolled_chcs(conditions, action_defs)

        # Verify correct number of CHCs generated
        self.assertEqual(len(unrolled_chcs), 3)

        # Verify first CHC structure
        self.assertEqual(len(unrolled_chcs[0].formula.formula), 1)
        self.assertEqual(
            unrolled_chcs[0].formula.formula[0].predicate_def.name, "ConditionPred"
        )
        self.assertEqual(unrolled_chcs[0].action.predicate_def.name, "RepeatAction1")

        # Verify second CHC structure (should include first action as condition)
        self.assertEqual(len(unrolled_chcs[1].formula.formula), 2)
        self.assertEqual(
            unrolled_chcs[1].formula.formula[0].predicate_def.name, "ConditionPred"
        )
        self.assertEqual(
            unrolled_chcs[1].formula.formula[1].predicate_def.name, "RepeatAction1"
        )
        self.assertEqual(unrolled_chcs[1].action.predicate_def.name, "RepeatAction2")

        # Verify third CHC structure (should include second action as condition)
        self.assertEqual(len(unrolled_chcs[2].formula.formula), 2)
        self.assertEqual(
            unrolled_chcs[2].formula.formula[0].predicate_def.name, "ConditionPred"
        )
        self.assertEqual(
            unrolled_chcs[2].formula.formula[1].predicate_def.name, "RepeatAction2"
        )
        self.assertEqual(unrolled_chcs[2].action.predicate_def.name, "RepeatAction3")

    def test_parse_chc_with_repeat(self):
        """Test parsing a CHC with an action that has num_repeat > 1."""
        # Setup predicate with a repeated action
        predicates = PredicateDefDict(
            {
                "TestCondition": PredicateDef(
                    name="TestCondition",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    is_action=False,
                    description="Test condition",
                ),
                "TestActionRepeat3": PredicateDef(
                    name="TestActionRepeat3",
                    arguments={},
                    is_action=True,
                    description="A repeated action",
                    num_repeat=3,
                ),
            }
        )
        parser = Parser(predicates)

        # Parse a CHC with repeated action
        chc_str = "TestCondition(value=true) → TestActionRepeat3()"
        parsed_result = parser.parse_chc(chc_str)

        # For repeating actions, parse_chc should return a list
        self.assertIsNotNone(parsed_result)
        self.assertIsInstance(parsed_result, list)
        result = parsed_result  # Now TypedDict knows it's a list

        # Verify we have 3 CHCs as expected
        if isinstance(result, list):
            self.assertEqual(len(result), 3)
            # Verify action names in the unrolled CHCs
            self.assertEqual(result[0].action.predicate_def.name, "TestAction1")
            self.assertEqual(result[1].action.predicate_def.name, "TestAction2")
            self.assertEqual(result[2].action.predicate_def.name, "TestAction3")

        # Verify the predicates dictionary has the new action definitions
        self.assertIn("TestAction1", parser.predicates)
        self.assertIn("TestAction2", parser.predicates)
        self.assertIn("TestAction3", parser.predicates)

    def test_parse_chcs_with_repeat(self):
        """Test parsing multiple CHCs with a repeated action."""
        # Setup predicates with a repeated action
        predicates = PredicateDefDict(
            {
                "Condition1": PredicateDef(
                    name="Condition1",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    is_action=False,
                    description="Condition 1",
                ),
                "Condition2": PredicateDef(
                    name="Condition2",
                    arguments={"num": Arg(name="num", type=ValueType.Number)},
                    is_action=False,
                    description="Condition 2",
                ),
            }
        )
        parser = Parser(predicates)

        # Parse multiple CHCs with one containing a repeated action
        chcs_str = """
        Condition1(value=true) → Action()
        Action() ∧ Condition2(num=5) → MultiStepRepeat2()
        MultiStepRepeat2() ∧ Condition2(num=10) → Done()
        """
        result = parser.parse_chcs(chcs_str)

        print(parser.predicates)
        for chc in result:
            print(chc)

        # Verify correct number of CHCs (1 normal + 2 unrolled = 3)
        self.assertEqual(len(result), 4)

        # Verify first CHC is normal
        self.assertEqual(result[0].action.predicate_def.name, "Action")

        # Verify second and third CHCs are unrolled from the repeated action
        self.assertEqual(result[1].action.predicate_def.name, "MultiStep1")
        self.assertEqual(result[2].action.predicate_def.name, "MultiStep2")
        self.assertEqual(result[3].action.predicate_def.name, "Done")
        self.assertEqual(result[3].formula.formula[0].name, "MultiStep2")

    def test_space_in_string(self):
        # Setup predicates with a repeated action
        predicates = PredicateDefDict(
            {
                "Condition1": PredicateDef(
                    name="Condition1",
                    arguments={
                        "value": Arg(name="value", type=ValueType.Boolean),
                        "string": Arg(name="string", type=ValueType.Text),
                        "number": Arg(name="number", type=ValueType.Number),
                    },
                    is_action=False,
                    description="Condition 1",
                ),
            }
        )
        parser = Parser(predicates)

        chc = """
        Condition1(value=true, string=hello how are you?, number=5) → Action()
        """
        result = parser.parse_chcs(chc)
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0].formula.formula[0].arguments["string"].value, "hello how are you?"
        )


if __name__ == "__main__":
    unittest.main()
