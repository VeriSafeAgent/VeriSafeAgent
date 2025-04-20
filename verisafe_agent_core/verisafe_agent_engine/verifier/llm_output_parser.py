from datetime import datetime
from enum import Enum, auto
import os
import re
import sys
from dateutil.parser import parse


sys.path.append(os.path.dirname(__file__))

from data_type import (
    CHC,
    Anything,
    Nothing,
    Unknown,
    get_anything,
    Arg,
    CmpOp,
    Formula,
    PredicateDef,
    PredicateDefDict,
    PredicateInstance,
    ValueInstance,
    ValueType,
    get_unknown,
)

from utils import log, MinimizedDAG


class UndefinedPredicateHandleOption(Enum):
    Leave = auto()  # Leave undefined predicate as is
    Error = auto()  # Raise error when undefined predicate is found
    Drop = auto()  # Drop undefined predicate and remain the same

    def __str__(self) -> str:
        return self.name


class Parser:

    def __init__(
        self,
        predicates: PredicateDefDict,
        reject_undefined_predicate: UndefinedPredicateHandleOption = UndefinedPredicateHandleOption.Drop,
    ):
        self.predicates = predicates
        self.reject_undefined_predicate: UndefinedPredicateHandleOption = (
            reject_undefined_predicate
        )

    @staticmethod
    def parse_cmp_op(cmp_op: str | None) -> CmpOp | None:
        match cmp_op:
            case None:
                return cmp_op
            case "=" | "==":
                return CmpOp.Equal
            case "!=":
                return CmpOp.NotEqual
            case ">":
                return CmpOp.GreaterThan
            case "<":
                return CmpOp.LessThan
            case ">=":
                return CmpOp.GreaterThanOrEqual
            case "<=":
                return CmpOp.LessThanOrEqual
            case _:
                raise ValueError(f"Invalid comparison operator: {cmp_op}")

    @staticmethod
    def parse_raw_value(
        v: str | bool | int | float, ty: Arg
    ) -> str | int | float | bool | datetime | Anything | Unknown | Nothing:

        def format_check(s: str):
            try:
                return parse(s)
            except ValueError:
                raise ValueError(f"Invalid format: {s}")

        str_v = str(v)
        normalized_str_v = str_v.strip().strip('"')

        if normalized_str_v == "*":
            return get_anything()

        match ty.type:
            case ValueType.Boolean:
                if normalized_str_v.lower() == "true":
                    return True
                elif normalized_str_v.lower() == "false":
                    return False
                else:
                    log(f"Invalid boolean value: {normalized_str_v}", "red")
                    return get_unknown()
            case ValueType.Text:
                return normalized_str_v
            case ValueType.Number:
                if normalized_str_v.lower().endswith("k"):
                    return float(normalized_str_v[:-1]) * 1000
                elif normalized_str_v.lower().endswith("m"):
                    return float(normalized_str_v[:-1]) * 1000000
                elif normalized_str_v.lower().endswith("b"):
                    return float(normalized_str_v[:-1]) * 1000000000
                else:
                    return float(normalized_str_v)
            case ValueType.Date:
                try:
                    return format_check(normalized_str_v)
                except ValueError:
                    raise ValueError(f"Invalid date value: {normalized_str_v}")
            case ValueType.Time:
                try:
                    return format_check(normalized_str_v)
                except ValueError:
                    raise ValueError(f"Invalid time value: {normalized_str_v}")
            case ValueType.Enum:
                if normalized_str_v not in ty.enum_values.values:
                    raise ValueError(
                        f"Invalid enum value: {normalized_str_v}. Possible enum values: {ty.enum_values.values}"
                    )
                return normalized_str_v
            case _:
                raise ValueError(f"Invalid predicate type: {ty}")

    @staticmethod
    def safe_parse_raw_value(
        v: str | bool | float, ty: Arg
    ) -> str | float | bool | datetime | Anything | Unknown | Nothing:
        try:
            return Parser.parse_raw_value(v, ty)
        except ValueError:
            return get_anything()

    def parse_argument(
        self, argument_types: dict[str, Arg], argument_values: dict[str, str]
    ) -> dict[str, ValueInstance]:

        def parse_single_argument(arg_ty: Arg, str_arg: str) -> ValueInstance:
            COMPARATOR_PATTERN = r"(.+),\s?(<=|>=|!=|==|<|>)"
            match = re.match(COMPARATOR_PATTERN, str_arg.strip("() "))
            try:
                if match:
                    return ValueInstance(
                        arg_ty=arg_ty,
                        value=self.parse_raw_value(match.group(1), arg_ty),
                        comparison_operator=self.parse_cmp_op(match.group(2)),
                    )
                else:
                    return ValueInstance(
                        arg_ty=arg_ty, value=self.parse_raw_value(str_arg, arg_ty)
                    )
            except ValueError as e:
                log(f"[Warning] {e}", "red")
                raise ValueError(f"Invalid argument: {str_arg} for {arg_ty}")

        result = {}
        for arg_name, arg in argument_types.items():
            if arg_name not in argument_values:
                result[arg_name] = ValueInstance(arg_ty=arg, value=get_anything())
            else:
                arg_value = argument_values[arg_name]
                result[arg_name] = parse_single_argument(arg, arg_value)
        return result

    def split_args(self, args: str) -> dict[str, str]:
        splitted = []
        current_token = []
        depth = 0

        for char in args:
            if char == "(":
                depth += 1
                current_token.append(char)
            elif char == ")":
                depth -= 1
                current_token.append(char)
            elif char == "," and depth == 0:
                token_str = "".join(current_token).strip()
                if token_str:
                    splitted.append(token_str)
                current_token = []
            else:
                current_token.append(char)
        # Add the last token if any
        final_token_str = "".join(current_token).strip()
        if final_token_str:
            splitted.append(final_token_str)

        result_dict = {}
        for idx, s in enumerate(splitted):
            splitted_by_equal = s.split("=", maxsplit=1)
            if len(splitted_by_equal) == 1:
                arg = splitted_by_equal[0].strip()
                name = f"arg_{idx}"
            else:
                name = splitted_by_equal[0].strip()
                arg = splitted_by_equal[1].strip()
            result_dict[name] = arg
        return result_dict

    def set_equivalent(self, l1: list[str], l2: list[str]) -> bool:
        if len(l1) != len(l2):
            return False
        for e in l1:
            if e not in l2:
                return False
        return True

    @classmethod
    def arg_type_guess(cls, arg_dict: dict[str, str]) -> dict[str, Arg]:

        def guess_single_arg_type(arg_value: str) -> ValueType:
            if arg_value.lower() in ["true", "false"]:
                return ValueType.Boolean
            try:
                float(arg_value)
                return ValueType.Number
            except ValueError:
                return ValueType.Text

        return {
            key: Arg(name=key, type=guess_single_arg_type(value))
            for key, value in arg_dict.items()
        }

    def parse_predicate_instance(
        self, cond: str, is_action: bool = False
    ) -> PredicateInstance | None:
        PRED_PATTERN = r"([A-Za-z0-9_]+)\((.*)\)"
        TRUE_PATTERN = r"True"
        REPEAT_PATTERN = r"Repeat(\d+)"
        predicate_match = re.search(PRED_PATTERN, cond)
        if not predicate_match:
            if re.search(TRUE_PATTERN, cond) or len(cond) == 0:
                return None
            raise ValueError(f"Invalid predicate instance: {cond}")
        name, args = predicate_match.group(1), predicate_match.group(2)
        arg_dict = self.split_args(args)
        if is_action:
            if len(arg_dict) != 0:
                raise ValueError(
                    f"Action {name} has arguments: {arg_dict}. \n Action cannot have any argument!!!"
                )

            repeat_match = re.search(REPEAT_PATTERN, name)
            if repeat_match:
                num_repeat = int(repeat_match.group(1))
                name = name[: repeat_match.start()]
            else:
                num_repeat = 1
            if name not in self.predicates:
                self.predicates[name] = PredicateDef(
                    name=name,
                    is_action=True,
                    arguments=self.arg_type_guess(arg_dict),
                    description=f"Whether the action {name} is completed",
                    num_repeat=num_repeat,
                )
        if re.search(REPEAT_PATTERN, name):
            name = name.replace("Repeat", "")
        if name not in self.predicates:
            match self.reject_undefined_predicate:
                case UndefinedPredicateHandleOption.Leave:
                    log(
                        f"[Warning] Predicate {name} not found in predicates. Create a new predicate definition.",
                        "red",
                    )
                    self.predicates[name] = PredicateDef(
                        name=name,
                        arguments=self.arg_type_guess(arg_dict),
                        description="",
                    )
                case UndefinedPredicateHandleOption.Error:
                    raise ValueError(
                        f"Predicate {name} not found in predicate definitions: {list(self.predicates.keys())}"
                    )
                case UndefinedPredicateHandleOption.Drop:
                    log(
                        f"[Warning] Predicate {name} not found in predicates. Drop it.",
                        "red",
                    )
                    return None
        predicate_def = self.predicates[name]

        try:
            predicate_instance = PredicateInstance(
                arguments=self.parse_argument(predicate_def.arguments, arg_dict),
                predicate_def=predicate_def,
            )
        except ValueError as e:
            raise ValueError(
                str(e)
                + f"\n\nParse Argument Failed for {cond}. Predicate definition: {predicate_def}"
            )
        if (
            not predicate_def.is_action and predicate_instance.is_every_arg_anything()
        ):  # Ignore meaningless condition predicate instance
            return None
        return predicate_instance

    def generate_repeated_action_names(
        self, prefix: str, repeat_count: int
    ) -> list[PredicateDef]:
        new_actions = []
        for i in range(1, repeat_count + 1):
            name = f"{prefix}{i}"
            self.predicates[name] = PredicateDef(
                name=name,
                is_action=True,
                arguments={},
                description=f"Whether the action {name} is completed",
            )
            new_actions.append(self.predicates[name])
        return new_actions

    def generate_unrolled_chcs(
        self, conditions: Formula, new_actions: list[PredicateDef]
    ) -> list[CHC]:
        pure_conditions = [c for c in conditions if not c.predicate_def.is_action]
        first_chc = CHC(
            formula=conditions,
            action=PredicateInstance(predicate_def=new_actions[0]),
        )
        unrolled_chcs = [first_chc]
        prev_action_instance = first_chc.action
        for i in range(1, len(new_actions)):
            new_chc = CHC(
                formula=Formula(pure_conditions + [prev_action_instance]),
                action=PredicateInstance(predicate_def=new_actions[i]),
            )
            unrolled_chcs.append(new_chc)
            prev_action_instance = new_chc.action
        assert len(unrolled_chcs) == len(
            new_actions
        ), f"Unrolled CHCs length {len(unrolled_chcs)} is not equal to new actions length {len(new_actions)}"
        return unrolled_chcs

    def parse_chc(self, line: str) -> CHC | list[CHC] | None:
        """
        Parse a single Constrained Horn Clause (CHC) from a string representation.

        Args:
            line: String containing a single CHC in format "condition1 ∧ condition2 → action"
            predicates: Dictionary of predicate definitions

        Returns:
            CHC: Parsed Constrained Horn Clause object
        """
        splitted = line.split("→")
        if len(splitted) != 2:
            log(f"Invalid CHC: {line}", "red")
            return None
        conditions = splitted[0].split("∧")
        action = splitted[1].strip()
        try:
            parsed_predicates = [self.parse_predicate_instance(c) for c in conditions]
        except ValueError as e:
            raise ValueError(str(e) + f"\n\nParsing failed: {line}")
        filter_nones = [p for p in parsed_predicates if p is not None]
        parsed = Formula(filter_nones)
        parsed_action = self.parse_predicate_instance(action, is_action=True)
        if parsed_action is None:
            raise ValueError(f"Action is not parsed: {action}")
        if parsed_action.predicate_def.num_repeat > 1:
            new_actions = self.generate_repeated_action_names(
                parsed_action.predicate_def.name, parsed_action.predicate_def.num_repeat
            )
            unrolled_chcs = self.generate_unrolled_chcs(parsed, new_actions)
            return unrolled_chcs

        return CHC(formula=parsed, action=parsed_action)

    def add_done_to_leaves(self, chcs: list[CHC]):
        """Add dummy done actions to leaves of the dependency graph"""

        def is_done(action: PredicateInstance) -> bool:
            return action.predicate_def.name == "Done"

        dep_dag = get_dependency_dag_from_chcs(chcs)
        leaves = dep_dag.leaves
        non_done_leaves = []

        for leaf in leaves:
            action = chcs[leaf].action
            if not is_done(action):
                non_done_leaves.append(leaf)

        for leaf in non_done_leaves:
            if self.predicates.get("Done") is None:
                self.predicates["Done"] = PredicateDef(
                    name="Done", arguments={}, is_action=True, description=""
                )
            done_def = self.predicates["Done"]

            done_action = PredicateInstance(predicate_def=done_def)
            formula = Formula([chcs[leaf].action])
            chc = CHC(formula=formula, action=done_action)
            chcs.append(chc)

        new_dep_dag = get_dependency_dag_from_chcs(chcs)
        new_leaves = new_dep_dag.leaves
        assert all(
            is_done(chcs[leaf].action) for leaf in new_leaves
        ), "All leaves must have done action"
        return chcs

    def parse_chcs(self, raw_chc: str) -> list[CHC]:
        """
        Parse multiple Constrained Horn Clauses from a string representation.

        Args:
            raw_chc: String containing multiple CHCs, one per line
            predicates: Dictionary of predicate definitions

        Returns:
            list[CHC]: List of parsed Constrained Horn Clause objects
        """
        result = [self.parse_chc(line.strip()) for line in raw_chc.split("\n") if line]
        chcs = []
        for r in result:
            if isinstance(r, list):
                chcs.extend(r)
            elif isinstance(r, CHC):
                chcs.append(r)

        chcs = self.add_done_to_leaves(chcs)

        return chcs

    def parse(self, encoded: str | None) -> list[CHC]:
        CHC_PATTERN = r"[*]{0,2}<CHC>[*]{0,2}\s+(.*)\s+[*]{0,2}<\/CHC>"
        if not encoded:
            return []
        chc_match = re.search(CHC_PATTERN, encoded, re.DOTALL)
        chcs = self.parse_chcs(chc_match.group(1).strip()) if chc_match else []
        return chcs


def get_dependency_dag_from_chcs(chcs: list[CHC]) -> MinimizedDAG:
    """
    Build a dependency graph between CHCs where each CHC may depend on others.

    Args:
        chcs: List of Constrained Horn Clauses

    Returns:
        list[list[int]]: result[i] contains indices of CHCs that CHC i depends on
    """
    dependency = MinimizedDAG()
    for i in range(len(chcs)):
        dependency.add_vertice(i)
        for j in range(len(chcs)):
            if i != j and chcs[j].action in chcs[i].formula:  # i depends on j (j -> i)
                dependency.add_edge_with_reduction(j, i)
    return dependency
