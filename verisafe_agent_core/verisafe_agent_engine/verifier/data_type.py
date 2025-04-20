from __future__ import annotations
from datetime import datetime
from enum import Enum, auto
from functools import lru_cache
import os
from typing import NewType, Optional
from dataclasses import dataclass, field, asdict
from typing import List

import sys

sys.path.append(os.path.join(os.path.dirname(__file__)))
from utils import log
from solver import is_valid
from string_similarity import (
    ratio_sim,
    jaro_sim,
    jaro_winkler_sim,
    embedding_sim,
    string_similarity_threshold,
)


@dataclass
class EnumValues:
    values: list[str] = field(default_factory=list)

    def __str__(self):
        return f"[{', '.join(self.values)}]"


class ValueType(Enum):
    Boolean = auto()
    Text = auto()
    Time = auto()
    Date = auto()
    Number = auto()
    Enum = auto()

    def __str__(self):
        match self.name:
            case "Boolean":
                return "Boolean"
            case "Text":
                return "Text"
            case "Time":
                return "Time"
            case "Date":
                return "Date"
            case "Number":
                return "Number"
            case "Enum":
                return "Enum"

    def __eq__(self, other):
        if type(self).__qualname__ != type(other).__qualname__:
            return NotImplemented
        return self.name == other.name and self.value == other.value


class CmpOp(Enum):
    Equal = auto()  # ==
    NotEqual = auto()  # !=
    GreaterThan = auto()  # >
    GreaterThanOrEqual = auto()  # >=
    LessThan = auto()  # <
    LessThanOrEqual = auto()  # <=

    def __str__(self):
        match self.name:
            case "Equal":
                return "=="
            case "NotEqual":
                return "!="
            case "GreaterThan":
                return ">"
            case "GreaterThanOrEqual":
                return ">="
            case "LessThan":
                return "<"
            case "LessThanOrEqual":
                return "<="

    def __eq__(self, other):
        if type(self).__qualname__ != type(other).__qualname__:
            return NotImplemented
        return self.name == other.name and self.value == other.value


class PredicateUpdateOp(Enum):
    Add = auto()
    Update = auto()
    Delete = auto()

    def __str__(self):
        match self.name:
            case "Add":
                return "Add"
            case "Update":
                return "Update"
            case "Delete":
                return "Delete"
            case _:
                raise ValueError(f"Invalid predicate update operation: {self.name}")

    def __eq__(self, other):
        if type(self).__qualname__ != type(other).__qualname__:
            return NotImplemented
        return self.name == other.name and self.value == other.value


@dataclass
class Arg:
    name: str = ""
    type: ValueType = field(default_factory=lambda: ValueType.Boolean)
    enum_values: EnumValues = field(default_factory=EnumValues)

    def __str__(self):
        if self.type == ValueType.Enum:
            return f"{self.name}: {self.type}{str(self.enum_values)}"
        else:
            return f"{self.name}: {self.type}"


@dataclass
class PredicateDef:
    name: str = ""
    is_action: bool = False
    num_repeat: int = 1
    arguments: dict[str, Arg] = field(default_factory=dict)
    description: str = ""
    arg_keys: list[str] = field(default_factory=list)

    def __str__(self):
        return f"{self.name}({', '.join([str(arg) for arg in self.arguments.values()])}): {self.description}"

    def __eq__(self, other):
        # Don't care about description
        if self.name != other.name:
            return False
        if self.arguments != other.arguments:
            return False
        if self.arg_keys != other.arg_keys:
            return False
        return True


class MetaclassSingleton(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MetaclassSingleton, cls).__call__(*args, **kwargs)
        return cls._instance


class Anything(metaclass=MetaclassSingleton):
    """
    Anything means that the value can be anything. So, negation of anything is Nothing.
    """

    def __str__(self):
        return "*"

    def __eq__(self, other):
        return str(self) == str(other)


class Unknown(metaclass=MetaclassSingleton):
    """
    Unknown means that the value not specified yet. So, negation of unknown is unknown.
    """

    def __str__(self):
        return "?"

    def __eq__(self, other):
        return str(self) == str(other)


class Nothing(metaclass=MetaclassSingleton):
    """
    Nothing means that the value is not possible. So, negation of nothing is anything.
    """

    def __str__(self):
        return "⊥"

    def __eq__(self, other):
        return str(self) == str(other)


def get_anything():
    return Anything()


def get_nothing():
    return Nothing()


def get_unknown():
    return Unknown()


@dataclass
class ValueInstance:

    arg_ty: Arg
    value: str | int | float | bool | datetime | Anything | Unknown | Nothing = field(
        default_factory=Anything
    )
    comparison_operator: Optional[CmpOp] = None

    def __str__(self):
        if self.comparison_operator is not None:
            return f"{self.arg_ty.name}=({self.value}, {self.comparison_operator})"
        else:
            return f"{self.arg_ty.name}={self.value}"

    @staticmethod
    def datetime_to_number(datetime: datetime) -> int:
        return int(datetime.timestamp())

    def __hash__(self) -> int:
        return hash(str(self))

    # check self -> other is valid
    @lru_cache(maxsize=256)
    def implies(self, other: ValueInstance) -> bool:
        if self.arg_ty != other.arg_ty:
            return False
        elif (
            other.value == get_anything() or other.value == get_unknown()
        ):  # ◻︎ -> * / ?
            return True
        elif other.value == get_nothing():  # ◻︎ -> ⊥
            return False
        elif self.value == get_anything() or self.value == get_unknown():  # * / ? -> ◻︎
            return False
        elif self.value == get_nothing():  # ⊥ -> ◻︎
            return False

        match self.arg_ty.type:
            case ValueType.Boolean:
                return bool(self.value) == bool(other.value)

            case ValueType.Text:
                if str(self.value) == str(other.value):
                    return True

                # Lower s1 and s2
                s1 = str(self.value).lower().strip()
                s2 = str(other.value).lower().strip()

                r_sim = ratio_sim(s1, s2)
                j_sim = jaro_sim(s1, s2)
                jw_sim = jaro_winkler_sim(s1, s2)
                e_sim = embedding_sim(s1, s2)

                log(f"s1: {s1} s2: {s2}")
                log(f"r_sim: {r_sim} j_sim: {j_sim} jw_sim: {jw_sim} e_sim: {e_sim}")

                sims = (r_sim, j_sim, jw_sim, e_sim)
                if any(sim >= string_similarity_threshold for sim in sims):
                    return True
                return False
            case ValueType.Number:
                value, cmp_op = self.value, self.comparison_operator
                other_value, other_cmp_op = other.value, other.comparison_operator
                if cmp_op is None:  # Default to Equal
                    cmp_op = CmpOp.Equal
                if other_cmp_op is None:  # Default to Equal
                    other_cmp_op = CmpOp.Equal
                str_chc = f"x {cmp_op} {value} → x {other_cmp_op} {other_value}"
                return is_valid(str_chc)
            case ValueType.Date | ValueType.Time:
                if isinstance(self.value, datetime) and isinstance(
                    other.value, datetime
                ):
                    value, cmp_op = (
                        self.datetime_to_number(self.value),
                        self.comparison_operator,
                    )
                    other_value, other_cmp_op = (
                        self.datetime_to_number(other.value),
                        other.comparison_operator,
                    )
                else:
                    raise TypeError(
                        f"Value of {str(self.arg_ty.type)} type must be datetime, but got {type(self.value)} and {type(other.value)}"
                    )
                if cmp_op is None:  # Default to Equal
                    cmp_op = CmpOp.Equal
                if other_cmp_op is None:  # Default to Equal
                    other_cmp_op = CmpOp.Equal
                str_chc = f"x {cmp_op} {value} → x {other_cmp_op} {other_value}"
                return is_valid(str_chc)
            case ValueType.Enum:
                return self.value == other.value


@dataclass
class PredicateInstance:
    predicate_def: PredicateDef
    arguments: dict[str, ValueInstance] = field(default_factory=dict)

    def __post_init__(self):
        for arg_name in self.predicate_def.arguments:
            if arg_name not in self.arguments:
                self.arguments[arg_name] = ValueInstance(
                    arg_ty=self.predicate_def.arguments[arg_name],
                    value=get_unknown(),
                )

    def __str__(self):
        specified_args = [
            str(arg) for arg in self.arguments.values() if arg.value != get_anything()
        ]
        return f"{self.predicate_def.name}({', '.join(specified_args)})"

    def __repr__(self):
        return f"{self.predicate_def.name}({', '.join([str(arg) for arg in self.arguments.values()])})"

    def __eq__(self, other):
        if not isinstance(other, PredicateInstance):
            return False
        if self.predicate_def != other.predicate_def:  # Different predicate definition
            return False

        for arg_name, arg_value in self.arguments.items():
            if arg_name not in other.arguments:
                return False
            if arg_value.arg_ty.name != other.arguments[arg_name].arg_ty.name:
                return False
            if arg_value.value != other.arguments[arg_name].value:
                return False
            if (
                arg_value.comparison_operator
                != other.arguments[arg_name].comparison_operator
            ):
                return False

        return True

    @property
    def name(self) -> str:
        return self.predicate_def.name

    def check_same_key(self, other: PredicateInstance) -> bool:
        if self.predicate_def != other.predicate_def:
            return False
        if self.get_key_args() != other.get_key_args():
            return False
        return True

    # check logical implication self -> other
    def implies(self, other: PredicateInstance) -> bool:
        if self.predicate_def != other.predicate_def:
            return False

        return all(
            self.arguments[arg_name].implies(other.arguments[arg_name])
            for arg_name in self.predicate_def.arguments
        )

    def is_every_arg_anything(self) -> bool:
        for arg in self.arguments.values():
            if arg.value != get_anything():
                return False
        return True

    def has_key(self) -> bool:
        """Check if this predicate instance has a key argument."""
        if self.predicate_def.arg_keys:
            return True
        return False

    def get_key_args(self) -> list[ValueInstance]:
        """Get the key argument if exists."""
        return [self.arguments[key_name] for key_name in self.predicate_def.arg_keys]

    def matches_key(self, other: PredicateInstance) -> bool:
        """Check if this predicate has the same key value as another predicate. If there is no key, it return False"""
        if self.predicate_def != other.predicate_def:
            return False
        if not self.has_key() or not other.has_key():
            return False

        self_keys = self.get_key_args()
        other_keys = other.get_key_args()

        if len(self_keys) != len(other_keys):
            return False

        return all(
            self_key.arg_ty.name == other_key.arg_ty.name
            and self_key.value == other_key.value
            for self_key, other_key in zip(self_keys, other_keys)
        )


@dataclass
class PredicateUpdate:
    predicate: PredicateInstance  # Add, Update, Remove 작업에 공통으로 사용 (필수 필드)
    operation: PredicateUpdateOp = field(default_factory=lambda: PredicateUpdateOp.Add)

    def __str__(self):
        match self.operation:
            case PredicateUpdateOp.Add:
                return f"Add {str(self.predicate)}"
            case PredicateUpdateOp.Update:
                return f"Update to {str(self.predicate)}"
            case PredicateUpdateOp.Delete:
                return f"Delete {str(self.predicate)}"


PredicateDefDict = NewType("PredicateDefDict", dict[str, PredicateDef])
PredicateInstanceDict = NewType("PredicateInstanceDict", dict[str, PredicateInstance])


class Formula:

    def __init__(self, formula: list[PredicateInstance]):
        self.formula = formula

    def __str__(self):
        if len(self.formula) == 0:
            return "True"
        return " ∧ ".join([str(f) for f in self.formula])

    def __dict__(self):
        return {
            "formula": [asdict(f) for f in self.formula],
        }

    def __contains__(self, item: PredicateInstance):
        """
        Check self => item
        """
        if len(self.formula) == 0:  # bottom -> item
            return False
        for predicate in self.formula:
            if predicate.implies(item):
                return True
        return False

    def __len__(self):
        return len(self.formula)

    def __iter__(self):
        return iter(self.formula)

    def clear(self):
        self.formula.clear()

    def implies(self, other: Formula) -> bool:
        # self => other
        return all(pred in self for pred in other)

    def implies_verbose(self, other: Formula) -> list[PredicateInstance]:
        """
        Check why other is unsatisfiable
        """
        unsatisfies = []
        for pred in other:
            if pred not in self:
                unsatisfies.append(pred)
        return unsatisfies

    def find_closest(self, predicate: PredicateInstance) -> Optional[PredicateInstance]:
        """
        Find the closest predicate in the formula that matches the given predicate.

        This implements the Closest function from the mathematical definition:
        - If the predicate has a key, find the predicate with the same key
        - If the predicate doesn't have a key, find the most similar predicate
        - Return None if no matching predicate exists
        """
        if predicate.has_key():
            # If predicate has a key, find predicates with the same key
            key_args = predicate.get_key_args()
            if not key_args:
                return None

            for p in self.formula:
                # Find the predicate with same key.
                if predicate.matches_key(p):
                    return p
            return None
        else:
            # If predicate doesn't have a key, find most similar predicate
            matching_preds = [
                p for p in self.formula if p.predicate_def == predicate.predicate_def
            ]

            if not matching_preds:
                return None

            # Count the number of matching arguments for each predicate
            def count_matching_args(p: PredicateInstance) -> int:
                return sum(
                    p.arguments[arg_name].implies(predicate.arguments[arg_name])
                    for arg_name in p.arguments
                    if arg_name in predicate.arguments
                )

            # Return the predicate with the most matching arguments
            return max(matching_preds, key=count_matching_args)

    def formula_update(self, predicate_update: PredicateUpdate):
        """
        Update the formula based on the predicate update operation.
        Implements the Update and Delete functions from the mathematical definition.
        """
        log(f"{str(predicate_update)}", "cyan")
        if (
            predicate_update.operation == PredicateUpdateOp.Add
            or predicate_update.operation == PredicateUpdateOp.Update
        ):
            target_predicate = self.find_closest(predicate_update.predicate)
            if target_predicate is None:
                log(
                    f"[Warning]No predicate to update: {str(predicate_update.predicate)}. Add it.",
                    "red",
                )
                self.formula.append(predicate_update.predicate)
            else:
                new_predicate = predicate_update.predicate
                for arg_name in target_predicate.arguments:
                    # Replace the argument with unknown with the new argument
                    if new_predicate.arguments[arg_name].value == get_unknown():
                        continue
                    target_predicate.arguments[arg_name] = new_predicate.arguments[
                        arg_name
                    ]
        elif predicate_update.operation == PredicateUpdateOp.Delete:
            target_predicate = self.find_closest(predicate_update.predicate)
            if target_predicate is None:
                log(
                    f"[Warning] No predicate to delete: {str(predicate_update.predicate)}. Do nothing.",
                    "red",
                )
            else:
                self.formula.remove(target_predicate)


@dataclass
class CHC:
    formula: Formula
    action: PredicateInstance

    def __str__(self):
        return f"{str(self.formula)} → {str(self.action)}"

    def __dict__(self):
        return {
            "formula": self.formula.__dict__(),
            "action": asdict(self.action),
        }


def chcs_to_str(chcs: list[CHC], indent=0) -> str:
    output = ""
    for idx, chc in enumerate(chcs):
        output += f"{' ' * indent}[{idx}]: {str(chc)}\n"
    return output


@dataclass
class Instruction:
    predicates: PredicateDefDict = field(default_factory=lambda: PredicateDefDict({}))
    natural_language_instruction: str = ""
    driven_experience: str = ""
    memory: str = ""
    chcs: List[CHC] = field(default_factory=list)

    def __str__(self):
        return chcs_to_str(self.chcs, indent=4)

    def __dict__(self):
        return {
            "predicates": dict(self.predicates),
            "natural_language_instruction": self.natural_language_instruction,
            "memory": self.memory,
            "chcs": [chc.__dict__() for chc in self.chcs],
        }
