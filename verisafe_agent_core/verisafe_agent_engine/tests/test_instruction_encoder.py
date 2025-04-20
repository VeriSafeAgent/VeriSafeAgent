import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Adjust sys.path to import modules from the verifier directory and its parent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_verifier.verifier.data_type import (
    ValueType,
    Arg,
    PredicateDef,
    PredicateDefDict,
    EnumValues,
    Instruction,
    CHC,
    Formula,
    PredicateInstance,
    ValueInstance,
)
from agent_verifier.verifier.instruction_encoder import Config, InstructionEncoder


class TestInstructionEncoder(unittest.TestCase):

    def setUp(self):
        # Create predicate definitions covering all data types for reuse in tests
        self.pred_defs = {
            "BoolPred": PredicateDef(
                name="BoolPred",
                arguments={"flag": Arg(name="flag", type=ValueType.Boolean)},
                description="A boolean predicate",
            ),
            "TextPred": PredicateDef(
                name="TextPred",
                arguments={"text": Arg(name="text", type=ValueType.Text)},
                description="A text predicate",
            ),
            "NumberPred": PredicateDef(
                name="NumberPred",
                arguments={"number": Arg(name="number", type=ValueType.Number)},
                description="A number predicate",
            ),
            "DatePred": PredicateDef(
                name="DatePred",
                arguments={"date": Arg(name="date", type=ValueType.Date)},
                description="A date predicate",
            ),
            "TimePred": PredicateDef(
                name="TimePred",
                arguments={"time": Arg(name="time", type=ValueType.Time)},
                description="A time predicate",
            ),
            "EnumPred": PredicateDef(
                name="EnumPred",
                arguments={
                    "choice": Arg(
                        name="choice",
                        type=ValueType.Enum,
                        enum_values=EnumValues(["A", "B", "C"]),
                    )
                },
                description="An enum predicate",
            ),
        }

        # Create a mock OpenAI client
        self.mock_client = MagicMock()

        # Setup a mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = (
            "<CHC>\n" "BoolPred(flag=true) → TextPred(text=hello)\n" "</CHC>"
        )
        self.mock_client.chat.completions.create.return_value = mock_response

        # Create an instruction for testing
        self.instruction = Instruction(
            predicates=PredicateDefDict(self.pred_defs),
            natural_language_instruction="Test instruction",
        )

        # Create the encoder instance
        self.encoder = InstructionEncoder(
            client=self.mock_client,
            instruction=self.instruction,
            config=Config(verbose=True),
        )

        # Setup some test CHCs
        bool_arg = Arg(name="flag", type=ValueType.Boolean)
        text_arg = Arg(name="text", type=ValueType.Text)

        bool_pred_def = self.pred_defs["BoolPred"]
        text_pred_def = self.pred_defs["TextPred"]

        bool_pred = PredicateInstance(
            predicate_def=bool_pred_def,
            arguments={"flag": ValueInstance(arg_ty=bool_arg, value=True)},
        )

        text_pred = PredicateInstance(
            predicate_def=text_pred_def,
            arguments={"text": ValueInstance(arg_ty=text_arg, value="hello")},
        )

        # Create test CHCs
        self.test_chcs = [
            CHC(formula=Formula([bool_pred]), action=text_pred),
            CHC(formula=Formula([text_pred]), action=bool_pred),
        ]

    def test_valid_parsing(self):
        # Test valid CHC parsing
        chc_content = """
        <CHC>
        BoolPred(flag=true) → TextPredAction()
        TextPred(text="world") → NumberPredAction()
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))
        result = self.encoder.encode()

        # Verify parsed CHCs
        self.assertEqual(len(result.chcs), 4)
        self.assertEqual(result.chcs[0].action.name, "TextPredAction")
        self.assertEqual(result.chcs[1].action.name, "NumberPredAction")

    def test_invalid_date_format(self):
        # Test invalid date format
        chc_content = """
        <CHC>
        DatePred(date=2023-13-32) → BoolPred(flag=true)
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)
        self.assertTrue(self.encoder.retry_count > 0)

    def test_invalid_time_format(self):
        # Test invalid time format
        chc_content = """
        <CHC>
        TimePred(time=25:61:99) → BoolPred(flag=true)
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)
        self.assertTrue(self.encoder.retry_count > 0)

    def test_invalid_enum_value(self):
        # Test invalid enum value
        chc_content = """
        <CHC>
        EnumPred(choice=D) → BoolPred(flag=true)
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)
        self.assertTrue(self.encoder.retry_count > 0)

    def test_invalid_comparison_operator(self):
        # Test invalid comparison operator
        chc_content = """
        <CHC>
        NumberPred(number=(42, =>)) → BoolPred(flag=true)
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)

    def test_invalid_chc_format(self):
        # Test invalid CHC format (missing arrow)
        chc_content = """
        <CHC>
        BoolPred(flag=true) TextPred(text=hello)
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)

    def test_invalid_chc_response(self):
        # Test missing CHC tags
        chc_content = """
        BoolPred(flag=true) → TextPred(text=hello)
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)

    def test_type_conversion_errors(self):
        # Test invalid enum value
        # Make sure number is not converted to text
        chc_content = """
        <CHC>
        BoolPred(flag=maybe) → TextPred(text=hello)
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should be handled through retries
        result = self.encoder.encode()

        # Verify no CHCs due to error
        self.assertEqual(len(result.chcs), 0)

    def test_no_condition(self):
        # Test no condition
        chc_content = """
        <CHC>
        → BoolPredAction()
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should parse successfully
        result = self.encoder.encode()

        # Verify CHC with empty formula
        self.assertEqual(len(result.chcs), 2)
        self.assertEqual(len(result.chcs[0].formula.formula), 0)
        self.assertEqual(result.chcs[0].action.name, "BoolPredAction")

    def test_no_value_arg(self):
        # Test when no value is provided for an argument
        chc_content = """
        <CHC>
        BoolPred() → TextPredAction()
        </CHC>
        """

        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = chc_content
        self.mock_client.chat.completions.create.return_value = mock_response

        # Parse using encoder
        self.encoder.set_predicates(PredicateDefDict(self.pred_defs))

        # This should parse successfully
        result = self.encoder.encode()

        # Verify CHC dropped condition
        self.assertEqual(len(result.chcs), 2)
        self.assertEqual(len(result.chcs[0].formula.formula), 0)

    # New tests for InstructionEncoder-specific methods

    def test_tagging(self):
        # Test static tagging method
        content = "Test content"
        tag = "TestTag"
        tagged = InstructionEncoder.tagging(content, tag)
        expected = "<TestTag>\nTest content\n</TestTag>"
        self.assertEqual(tagged, expected)

    def test_instruction_tagging(self):
        # Test instruction_tagging method
        instruction = "Do something"
        tagged = self.encoder.instruction_tagging(instruction)
        expected = "<Instruction>\nDo something\n</Instruction>"
        self.assertEqual(tagged, expected)

    def test_tag_predicates(self):
        # Test tag_predicates method
        predicates = PredicateDefDict(self.pred_defs)
        tagged = self.encoder.tag_predicates(predicates)

        # Check the result has the correct tag and contains all predicates
        self.assertTrue(tagged.startswith("<Predicates>"))
        self.assertTrue(tagged.endswith("</Predicates>"))
        for pred_name in self.pred_defs:
            self.assertIn(pred_name, tagged)

    def test_instruction_to_prompt(self):
        # Test instruction_to_prompt with no feedback
        prompt = self.encoder.instruction_to_prompt(self.instruction)

        # Check the prompt contains tagged instruction and predicates
        self.assertIn("<Instruction>", prompt)
        self.assertIn("</Instruction>", prompt)
        self.assertIn("<Predicates>", prompt)
        self.assertIn("</Predicates>", prompt)
        self.assertIn("Test instruction", prompt)

        # Test with feedback
        self.encoder.feedbacks[1].append("Feedback item 1")
        self.encoder.feedbacks[1].append("Feedback item 2")
        self.encoder.retry_count = 1

        prompt_with_feedback = self.encoder.instruction_to_prompt(self.instruction)

        # Check the prompt contains feedback items
        self.assertIn("Feedback item 1", prompt_with_feedback)
        self.assertIn("Feedback item 2", prompt_with_feedback)

    def test_get_relevant_predicate_definitions(self):
        # Setup instruction with CHCs
        self.instruction.chcs = self.test_chcs

        # Get relevant predicates
        relevant_preds = self.encoder.get_relevant_predicate_definitions()

        # Verify the result contains the used predicates
        self.assertIn("BoolPred", relevant_preds)
        self.assertIn("TextPred", relevant_preds)
        self.assertNotIn("NumberPred", relevant_preds)  # Not used in test_chcs

    def test_feedback_to_str(self):
        # Setup feedback
        self.encoder.feedbacks[1].append("Attempt 1 Feedback 1")
        self.encoder.feedbacks[1].append("Attempt 1 Feedback 2")
        self.encoder.feedbacks[2].append("Attempt 2 Feedback")

        # Convert to string
        feedback_str = self.encoder.feedback_to_str()

        # Verify the result contains all feedback items
        self.assertIn("Attempt 1 Feedback 1", feedback_str)
        self.assertIn("Attempt 1 Feedback 2", feedback_str)
        self.assertIn("Attempt 2 Feedback", feedback_str)
        self.assertIn("---Attempt 1---", feedback_str)
        self.assertIn("---Attempt 2---", feedback_str)
        self.assertIn("---End of Feedback---", feedback_str)

    def test_decode_with_instruction_tag(self):
        # Mock response with instruction tag
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = (
            "Some prefix text\n"
            "<Instruction>Decoded instruction content</Instruction>\n"
            "Some suffix text"
        )
        self.mock_client.chat.completions.create.return_value = mock_response

        # Setup instruction with CHCs
        self.instruction.chcs = self.test_chcs

        # Call decode
        result = self.encoder.decode()

        # Verify the extracted instruction
        self.assertEqual(result, "Decoded instruction content")

    def test_decode_without_instruction_tag(self):
        # Mock response without instruction tag
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Plain text response without tags"
        self.mock_client.chat.completions.create.return_value = mock_response

        # Setup instruction with CHCs
        self.instruction.chcs = self.test_chcs

        # Call decode
        result = self.encoder.decode()

        # Verify the full response is returned
        self.assertEqual(result, "Plain text response without tags")

    def test_check_equiv(self):
        # Mock response for equivalence checking
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "<r></r>"
        self.mock_client.chat.completions.create.return_value = mock_response

        # Call check_equiv
        self.assertRaises(ValueError, self.encoder.check_equiv, "Instruction 2")

    def test_check_encoded_chc_is_good(self):
        # Test check_encoded_chc_is_good
        with patch.object(self.encoder, "decode", return_value="Decoded instruction"):
            with patch.object(self.encoder, "check_equiv", return_value=True):
                result = self.encoder.check_encoded_chc_is_good()
                self.assertTrue(result)

            with patch.object(self.encoder, "check_equiv", return_value=False):
                result = self.encoder.check_encoded_chc_is_good()
                self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
