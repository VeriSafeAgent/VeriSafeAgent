import os
import re
import sys
from typing import Any

sys.path.append(os.path.join(os.path.dirname(__file__)))

from instruction_encoder import Parser
from data_type import (
    Arg,
    EnumValues,
    PredicateDef,
    PredicateInstance,
    PredicateDefDict,
    PredicateInstanceDict,
    PredicateUpdate,
    PredicateUpdateOp,
    ValueInstance,
    ValueType,
    get_unknown,
)
from utils import find_first

ANNOTATED_INFO = re.compile(r"^\d+_annotated\.json$")
ACTION_PATTERN = re.compile(r"^\d+_actions\.json$")
INSTRUCTION_PATTERN = re.compile(r"^instruction\.txt$")
ANNOTATED_PATTERN = re.compile(r"^\d+_annotated\.png$")
PREDICATES_PATTERN = re.compile(r"predicates\.json$")


def parse_predicate_definition(
    predicate_name: str, raw_predicate: dict[str, Any]
) -> PredicateDef:
    """
    Parse raw predicate definition from JSON format into PredicateDef.
    raw_predicate structure:
        {
            "key_arg_name": "key_arg_name" | ["key_arg_name1", "key_arg_name2", ...],
            "arguments": [
                {
                    "name": "arg_name1",
                    "type": "arg_type1",
                },
                {
                    "name": "arg_name2",
                    "type": "Enum",
                    "enum_values": ["value1", "value2", "value3"],
                }
                ...
            ],
            "description": "predicate_description1",
        }
    """

    def parse_predicate_type(predicate_type: str) -> ValueType:
        if predicate_type == "Boolean":
            return ValueType.Boolean
        elif predicate_type == "Text":
            return ValueType.Text
        elif predicate_type == "Number":
            return ValueType.Number
        elif predicate_type == "Date":
            return ValueType.Date
        elif predicate_type == "Time":
            return ValueType.Time
        elif predicate_type == "Enum":
            return ValueType.Enum
        raise ValueError(f"Invalid predicate type: {predicate_type}")

    arguments: dict[str, Arg] = {}
    arg_keys: list[str] = []
    if "key_arg_name" in raw_predicate:
        arg_keys = raw_predicate["key_arg_name"]
        if isinstance(arg_keys, str) and arg_keys:
            arg_keys = [arg_keys]
    for v in raw_predicate["arguments"]:
        if v["type"] == "Enum":
            arguments[v["name"]] = Arg(
                v["name"],
                parse_predicate_type(v["type"]),
                EnumValues([value.strip('"').strip() for value in v["enum_values"]]),
            )
        else:
            arguments[v["name"]] = Arg(v["name"], parse_predicate_type(v["type"]))
    predicate_description = raw_predicate["description"]
    return PredicateDef(
        name=predicate_name,
        arguments=arguments,
        description=predicate_description,
        arg_keys=arg_keys,
    )


def parse_predicate_defs(raw_predicates: dict) -> PredicateDefDict:
    """
    Parse raw predicate definitions from JSON format into PredicateDefDict.

    Args:
        raw_predicates: Dictionary containing raw predicate definitions
        raw_predicates structure:
            {
                "predicate_name_A": {
                    "key_arg_name": "key_arg_name",
                    "arguments": [
                        {
                            "name": "arg_name1",
                            "type": "arg_type1",
                        },
                        {
                            "name": "arg_name2",
                            "type": "Enum",
                            "enum_values": ["value1", "value2", "value3"],
                        }
                        ...
                    ],
                    "description": "predicate_description1",
                },
                "predicate_name_B": {
                    ...
                }
            }

    Returns:
        PredicateDefDict: Dictionary mapping predicate names to their definitions
    """

    predicate_defs = PredicateDefDict({})
    for predicate_name in raw_predicates:
        predicate_defs[predicate_name] = parse_predicate_definition(
            predicate_name, raw_predicates[predicate_name]
        )
    return predicate_defs


def parse_predicate_update_op(s: str) -> PredicateUpdateOp:
    match s:
        case "Add":
            return PredicateUpdateOp.Add
        case "Update":
            return PredicateUpdateOp.Update
        case "Delete":
            return PredicateUpdateOp.Delete
        case _:
            return PredicateUpdateOp.Update


def parse_predicate_instance(
    predicate_name: str, raw_predicate: dict, pred_defs: PredicateDefDict
) -> PredicateInstance:
    """
    Parse raw predicate instance from JSON format into PredicateInstance.
    raw_predicate structure:
    {
        "arguments": [
            {
                "name": "arg_name1",
                "value": "arg_value1",
                "compare_op": "==",
            },
            {
                "name": "arg_name2",
                "value": "arg_value2",
                "compare_op": "==",
            }
            ...
        ]
    }
    """
    variables = raw_predicate["arguments"]
    if predicate_name not in pred_defs:
        raise ValueError(f"Invalid predicate name: {predicate_name}({variables})")
    pred_def = pred_defs[predicate_name]
    arguments: dict[str, ValueInstance] = {}
    for variable_name in pred_def.arguments:
        arg_ty = pred_def.arguments[variable_name]
        if variable_name not in variables:
            value = get_unknown()
            cmp_op = None
        else:
            value = Parser.parse_raw_value(
                variables[variable_name]["value"],
                arg_ty,
            )
            cmp_op = Parser.parse_cmp_op(variables[variable_name]["compare_op"])
        arguments[variable_name] = ValueInstance(
            arg_ty=arg_ty,
            value=value,
            comparison_operator=cmp_op,
        )
    predicate_instance = PredicateInstance(
        predicate_def=pred_def,
        arguments=arguments,
    )
    return predicate_instance


def parse_predicate_instance_dict(
    raw_predicates: dict, pred_defs: PredicateDefDict
) -> PredicateInstanceDict:
    """
    raw_predicates structure:
    {
        "<predicate_name>": {
            "variables": {
                "<variable_name1>": {
                    "value": <value>,
                    "compare_op": "== / != / <= / >= / < / > / None"
                },
                "<variable_name2>": {
                    "value": <value>,
                    "compare_op": "== / != / <= / >= / < / > / None"
                }
            }
        },
        ...
    }
    """
    pred_dict = PredicateInstanceDict({})
    for predicate_name in raw_predicates:
        pred_dict[predicate_name] = parse_predicate_instance(
            predicate_name, raw_predicates[predicate_name], pred_defs
        )
    return pred_dict


def parse_predicate_update_list(
    raw_predicate_update_list: list[dict], pred_defs: PredicateDefDict
) -> list[PredicateUpdate]:
    """
    input_structure:
    [
        {
            "Predicate": <predicate_name>,
            "Reasoning": <description about why the predicate is updated>,
            "Update_Rule": Update | Delete,
            <argument_name1>: <argument_value1>,
            <argument_name2>: <argument_value2>,
            ...
        },
        ...
    ]
    """
    predicate_updates: list[PredicateUpdate] = []
    for raw_predicate_update in raw_predicate_update_list:
        predicate_name = raw_predicate_update["Predicate"]
        normalized_predicate_arguments = {
            "arguments": {
                value_name: {
                    "value": raw_predicate_update[value_name],
                    "compare_op": "==",  # TODO: Add other comparison operators
                }
                for value_name in raw_predicate_update
                if value_name not in ["Predicate", "Reasoning"]
            }
        }
        predicate_instance = parse_predicate_instance(
            predicate_name, normalized_predicate_arguments, pred_defs
        )
        raw_update_rule = (
            "Update"
            if "Update_Rule" not in raw_predicate_update
            else raw_predicate_update["Update_Rule"]
        )
        predicate_update = PredicateUpdate(
            predicate=predicate_instance,
            operation=parse_predicate_update_op(raw_update_rule),
        )
        predicate_updates.append(predicate_update)
    return predicate_updates
