from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable
from openai.types.chat import ChatCompletionMessageParam
from openai.types.completion_usage import CompletionUsage
import os
import re
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__)))

from data_type import (
    CHC,
    Arg,
    Formula,
    Instruction,
    PredicateDef,
    PredicateDefDict,
    PredicateInstance,
    ValueType,
)
from llm_output_parser import (
    Parser,
    UndefinedPredicateHandleOption,
    get_dependency_dag_from_chcs,
)
from dotenv import load_dotenv
from openai import OpenAI
from utils import log, prefix_adder
from prompts import (
    feedback_prompt,
    normal_prompt,
    nl_based_equiv_checker_system_prompt,
    nl_based_equiv_checker_user_prompt,
    chc_based_equiv_checker_system_prompt,
    chc_based_equiv_checker_user_prompt,
    instruction_decoding_prompt,
    instruction_encoding_system_prompt,
    instruction_encoding_user_prompt_predicates,
    instruction_encoding_user_prompt_memory_begin,
    instruction_encoding_user_prompt_memory_fewshot_template,
    instruction_prompt,
)
from string_similarity import embedding_model, string_similarity_threshold


@dataclass
class Config:
    verbose: bool = False
    undefined_predicate_handle_option: UndefinedPredicateHandleOption = (
        UndefinedPredicateHandleOption.Leave
    )
    max_retry: int = 3
    use_self_consistency: bool = False
    temperature: float = 0.0
    string_similarity_threshold: float = 0.7
    seed: int = 42
    model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    chc_based_reflection: bool = False

    def __str__(self) -> str:
        result = "Config:\n"
        for field in self.__dataclass_fields__.values():
            value = getattr(self, field.name)
            result += f"    {field.name}: {str(value)}\n"
        return result


@dataclass
class OpenAIQueryResult:
    query: Iterable[ChatCompletionMessageParam]
    response: str
    usage: CompletionUsage
    latency: float  # "seconds"

    def to_dict(self) -> dict:
        return {
            "query": [dict(message) for message in self.query],
            "response": self.response,
            "usage": self.usage.to_dict(),
            "latency": self.latency,
        }


@dataclass
class Memory:
    past_instruction: str
    past_execution_flow: str
    past_relevant_predicates: list[PredicateDef]
    past_chcs: list[CHC]


class InstructionEncoder:

    def __init__(
        self,
        client: OpenAI,
        instruction: Instruction,
        config: Config,
    ) -> None:
        self.client = client
        self.instruction = instruction
        self.retry_count = 0
        self._config = config
        self.feedbacks = defaultdict(list)
        self.messages: list[ChatCompletionMessageParam] = [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "text",
                        "text": instruction_encoding_system_prompt,
                    }
                ],
            },
        ]
        if self.config.verbose:
            log(str(self.config), "white")
        self.query_results: list[OpenAIQueryResult] = []

    @property
    def config(self) -> Config:
        return self._config

    @config.setter
    def config(self, config: Config) -> None:
        global embedding_model, string_similarity_threshold
        self._config = config
        embedding_model = config.embedding_model
        string_similarity_threshold = config.string_similarity_threshold

    def set_predicates(self, predicates: PredicateDefDict) -> None:
        self.instruction.predicates = predicates

    def clear_messages(self) -> None:
        self.messages.clear()
        self.messages = [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "text",
                        "text": instruction_encoding_system_prompt,
                    }
                ],
            },
        ]

    @staticmethod
    def listup_iterable(iterable: Iterable) -> str:
        return "\n".join(
            [f"  [{idx}] {str(item)}" for idx, item in enumerate(iterable)]
        )

    @staticmethod
    def tagging(instruction: str, tag: str) -> str:
        return f"<{tag}>\n{instruction}\n</{tag}>"

    def instruction_tagging(self, instruction: str) -> str:
        return self.tagging(instruction, "Instruction")

    def tag_predicates(self, predicates: PredicateDefDict) -> str:
        return self.tagging(self.listup_iterable(predicates.values()), "Predicates")

    def query_to_openai(self, messages: Iterable[ChatCompletionMessageParam]) -> str:
        start_time = time.time()
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_format={"type": "text"},
            temperature=float(self.config.temperature),
            seed=int(self.config.seed),
        )
        end_time = time.time()
        latency = end_time - start_time

        usage = response.usage
        if usage is None:
            raise ValueError("Usage is None")
        if not response.choices or response.choices[0].message.content is None:
            raise ValueError("No response from OpenAI")
        result = response.choices[0].message.content
        self.query_results.append(
            OpenAIQueryResult(
                query=messages,
                response=result,
                usage=usage,
                latency=latency,
            )
        )
        return result

    @classmethod
    def memory_to_prompt(cls, memory: list[Memory]) -> str:
        result = ""
        for idx, m in enumerate(memory):
            joined_predicates = cls.listup_iterable(m.past_relevant_predicates)
            joined_chcs = cls.listup_iterable(m.past_chcs)
            result += instruction_encoding_user_prompt_memory_fewshot_template.format(
                idx=idx,
                past_instruction=m.past_instruction,
                past_execution_flow=m.past_execution_flow,
                past_relevant_predicates=joined_predicates,
                past_chcs=joined_chcs,
            )
        return result

    def instruction_to_prompt(
        self, instruction: Instruction, memory: list[Memory] = []
    ) -> str:
        if len(self.feedbacks) > 0:
            return feedback_prompt.format(feedback_list=self.feedback_to_str())
        if memory:
            return (
                instruction_encoding_user_prompt_predicates.format(
                    predicates=self.listup_iterable(instruction.predicates.values())
                )
                + instruction_encoding_user_prompt_memory_begin
                + self.memory_to_prompt(memory)
                + instruction_prompt.format(
                    instruction=instruction.natural_language_instruction
                )
            )
        return normal_prompt.format(
            instruction=self.instruction_tagging(
                instruction.natural_language_instruction
            ),
            predicates=self.tag_predicates(instruction.predicates),
            driven_experience=self.instruction.driven_experience
        )

    def get_relevant_predicates(self, formulas: list[Formula]) -> str:
        if len(formulas) == 0:
            return ""
        relevant_predicate_definitions = PredicateDefDict({})
        for formula in formulas:
            for predicate in formula:
                if predicate.name not in relevant_predicate_definitions:
                    relevant_predicate_definitions[predicate.name] = (
                        self.instruction.predicates[predicate.name]
                    )
        result_str = ""
        for idx, predicate in enumerate(relevant_predicate_definitions.values()):
            result_str += f"  [{idx}] {str(predicate)}\n"
        return result_str

    def fliter_formula_relevant_to_encoding(
        self, formula: Formula
    ) -> list[list[PredicateInstance]]:
        result = [[] for _ in self.instruction.chcs]
        for idx, chc in enumerate(self.instruction.chcs):
            for predicate in formula:
                if chc.formula.find_closest(predicate) is not None:
                    result[idx].append(predicate)
        return result

    def get_relevant_predicate_definitions(self) -> str:
        formulas = [chc.formula for chc in self.instruction.chcs]
        return self.get_relevant_predicates(formulas)

    def feedback_to_str(self):
        result = ""
        for count in self.feedbacks:
            result += f"\n---Attempt {count}---\n"
            result += "\n".join(self.feedbacks[count])
        if result:
            result += "\n---End of Feedback---\n"
        return result

    def complete(self, memory: list[Memory] = []):
        prompt = self.instruction_to_prompt(self.instruction, memory)
        self.messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        )
        log(f"Last Prompt:\n{prefix_adder(prompt, ' ' * 4)}", "yellow")
        response = self.query_to_openai(self.messages)
        self.messages.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": response}],
            }
        )
        return response

    def decode(self) -> str:
        predicates = self.get_relevant_predicate_definitions()
        chcs = self.tagging(str(self.instruction), "CHC")
        response = self.query_to_openai(
            [
                {"role": "developer", "content": instruction_decoding_prompt},
                {"role": "user", "content": predicates + "\n" + chcs},
            ],
        )
        instruction_pattern = r"<Instruction>(.*)</Instruction>"
        instruction = re.search(instruction_pattern, response, re.DOTALL)
        if instruction is None:
            return response
        return instruction.group(1).strip()

    def check_equiv(self, target: str | list[CHC]) -> bool:
        if isinstance(target, str):
            system_prompt = nl_based_equiv_checker_system_prompt
            user_prompt = nl_based_equiv_checker_user_prompt.format(
                oracle_instruction=self.instruction.natural_language_instruction,
                target_instruction=target,
            )
        else:
            system_prompt = chc_based_equiv_checker_system_prompt
            user_prompt = chc_based_equiv_checker_user_prompt.format(
                predicates=self.get_relevant_predicate_definitions(),
                oracle_instruction=self.instruction.natural_language_instruction,
                target_chc=target,
            )
        response = self.query_to_openai(
            [
                {"role": "developer", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                    ],
                },
            ],
        )
        if self.config.verbose:
            log(f"Equivalence Checker Response: {response}")

        result_pattern = r"<Result>(.*)</Result>"
        result = re.search(result_pattern, response, re.DOTALL)
        if result is None:
            raise ValueError("No result from OpenAI")

        self.feedbacks[self.retry_count].append(
            ">>> Your Encoding\n"
            + prefix_adder(str(self.instruction), " " * 4)
            + "\n<<<"
        )
        self.feedbacks[self.retry_count].append(
            ">>> Equivalence Checker Response\n"
            + prefix_adder(response, " " * 4)
            + "\n<<<"
        )

        return result.group(1).strip() == "True"

    def check_encoded_chc_is_good(self) -> bool:
        if self.config.chc_based_reflection:
            output = self.check_equiv(self.instruction.chcs)
            return output
        else:
            decoded = self.decode()
            self.feedbacks[self.retry_count].append(
                ">>> Decoded Natural Language Instruction\n"
                + prefix_adder(decoded, " " * 4)
                + "\n<<<"
            )
            if self.config.verbose:
                log(f"Decoded: {decoded}", "blue")
            return self.check_equiv(decoded)

    def encode(self, memory: list[Memory] = []) -> Instruction:
        self.retry_count = 0
        self.instruction.chcs.clear()
        self.feedbacks.clear()
        self.clear_messages()

        while self.retry_count <= self.config.max_retry:
            response_text = self.complete(memory)
            if self.config.verbose:
                log(response_text)

            parser = Parser(
                self.instruction.predicates,
                self.config.undefined_predicate_handle_option,
            )

            try:
                self.instruction.chcs = parser.parse(response_text)
            except ValueError as e:
                self.feedbacks[self.retry_count].append(str(self.instruction))
                self.feedbacks[self.retry_count].append(response_text)
                self.feedbacks[self.retry_count].append(str(e))
                self.retry_count += 1
                continue

            if not self.config.use_self_consistency:
                if self.instruction.chcs:
                    break
            else:
                if self.instruction.chcs and self.check_encoded_chc_is_good():
                    break

            self.retry_count += 1

        log(f"Retry: {self.retry_count}")
        if self.retry_count > self.config.max_retry:
            log(
                "[Warning] Failed to encode instruction in {self.max_retry} retries",
                "red",
            )
        return self.instruction

    @property
    def is_succeed_last_encoding(self) -> bool:
        return self.retry_count <= self.config.max_retry


if __name__ == "__main__":
    result = load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
    if not result:
        print("Failed to load .env file")
        exit(1)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    instruction = Instruction(
        natural_language_instruction="Book 2 flight tickets to Tokyo with total price less than 200,000 USD",
        predicates=PredicateDefDict(
            {
                "Destination": PredicateDef(
                    name="Destination",
                    arguments={"city": Arg(name="city", type=ValueType.Text)},
                    description="The destination city for the flight",
                ),
                "NumTickets": PredicateDef(
                    name="NumTickets",
                    arguments={"count": Arg(name="count", type=ValueType.Number)},
                    description="Number of tickets to book",
                ),
                "TotalPrice": PredicateDef(
                    name="TotalPrice",
                    arguments={
                        "amount": Arg(name="amount", type=ValueType.Number),
                        "currency": Arg(name="currency", type=ValueType.Text),
                    },
                    description="Total price for all tickets",
                ),
                "FlightDate": PredicateDef(
                    name="FlightDate",
                    arguments={"date": Arg(name="date", type=ValueType.Date)},
                    description="Date of the flight",
                ),
                "FlightTime": PredicateDef(
                    name="FlightTime",
                    arguments={"time": Arg(name="time", type=ValueType.Time)},
                    description="Departure time of the flight",
                ),
                "SearchCompleted": PredicateDef(
                    name="SearchCompleted",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    description="Whether flight search is completed",
                ),
                "FlightSelected": PredicateDef(
                    name="FlightSelected",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    description="Whether a flight is selected",
                ),
                "PaymentCompleted": PredicateDef(
                    name="PaymentCompleted",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    description="Whether payment is completed",
                ),
                "BookingConfirmed": PredicateDef(
                    name="BookingConfirmed",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    description="Whether booking is confirmed",
                ),
                "PassengerInfo": PredicateDef(
                    name="PassengerInfo",
                    arguments={"value": Arg(name="value", type=ValueType.Boolean)},
                    description="Whether passenger information is filled",
                ),
            }
        ),
        chcs=[],
    )
    instruction_encoder = InstructionEncoder(
        client, instruction, Config(verbose=True, max_retry=1)
    )
    instruction = instruction_encoder.encode()

    dep_dag = get_dependency_dag_from_chcs(instruction_encoder.instruction.chcs)
    dep_dag.draw_graphdot()
    print(str(instruction))
