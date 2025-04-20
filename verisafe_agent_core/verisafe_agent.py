import sys
import os
import copy
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.append(project_root)

from utils_.utils_ import log

from verisafe_agent_core.verisafe_agent_engine.verifier.data_type import (
    Formula,
    Instruction,
    PredicateInstance,
    CHC,
)
from verisafe_agent_core.verisafe_agent_engine.verifier.instruction_encoder import (
    Config,
    InstructionEncoder,
)
from verisafe_agent_core.verisafe_agent_engine.verifier.collect import (
    parse_predicate_defs,
    parse_predicate_update_list
)
from verisafe_agent_core.verisafe_agent_engine.verifier.client import client
from verisafe_agent_core.verisafe_agent_engine.verifier.annotation_based_verifier import (
    get_unsatisfies_for_each_chc,
    verify,
    pretty_print_unsats
)

from verisafe_agent_core.verisafe_memory import VeriSafeMemory


predicate_level_feedback = (
    "The action you previously selected may be invalid. We got feedback on this[Marked with <FEEDBACK></FEEDBACK>]. \n"
    "(You can still choose the same action. This feedback is for just in case, and is part of the double-checking process. And the value * means that the value can be anything and ? means that the value is not defined currently):\n"
    "<FEEDBACK>\n"
    "You've simulated the effect of the previous action you chose, and you realize that the change in the Condition (the state of the app) will change the value beyond what you originally expected. Try choosing the action again, taking this into account.\n"
    "PREVIOUSLY SELECTED ACTION : {PREVIOUS_ACTION}\n"
    "WRONG CONDITION CHANGING : {WRONG_CONDITIONS} [The Correct Condtion is {CORRECT_CONDITIONS}]\n"
    "</FEEDBACK>\n"
)

rule_level_feedback = (
    "The conditions to execute the low-level action you selected {CRITICAL_ACTION} are not yet fully met, so the action is aborted.  We got feedback on this[Marked with <FEEDBACK></FEEDBACK>]. \n"
    "(Look at those unmet conditions and select the action again. You can't select the same action.):\n"

    "<FEEDBACK>\n"
    "You have not yet satisfied the conditions to execute [{CRITICAL_ACTION}]. I'll show you the current condition state and the correct condition state, so you can take this into account and make sure you fully satisfy the conditions before performing the current action.\n"
    "PREVIOUSLY SELECTED ACTION :{PREVIOUS_ACTION}\n"
    "WRONG CURRENT CONDITION  : {WRONG_CONDITIONS}\n"
    "YOUR TARGET CONDITION :  {TARGET_CONDITIONS}\n"
    "</FEEDBACK> \n"
)

def normalize_predicate_def_json(raw_predicates: dict) -> dict:
    normalized_predicates = {}
    for predicate_name in raw_predicates:
        predicate_data = raw_predicates[predicate_name]
        key_arg_name = (
            ""
            if "key_arg_name" not in predicate_data
            else predicate_data["key_arg_name"]
        )
        arguments = predicate_data["variables"]
        normalized_predicates[predicate_name] = {
            "key_arg_name": key_arg_name,
            "arguments": arguments,
            "description": predicate_data["description"],
        }
    return normalized_predicates

class VeriSafeEngine:
    def __init__(self, config: Config):
        self.config = config

        self.instruction_encoder = InstructionEncoder(
            client=client,
            instruction=Instruction(),
            config=config,
        )

        self.simulate_formula = Formula([])

    def encode_instruction(self, instruction: str, predicates: dict, driven_experience: str = "") -> Instruction:
        self.instruction_encoder.set_predicates(
            parse_predicate_defs(normalize_predicate_def_json(predicates))
        )
        print(f"instruction: {instruction}")
        self.instruction_encoder.instruction.natural_language_instruction = instruction

        if driven_experience != "":
            self.instruction_encoder.instruction.driven_experience = driven_experience

        self.simulate_formula.clear()

        self.instruction_encoder.encode([])
        return self.instruction_encoder.instruction


    def simulate_update(self, updated_predicates: list) -> list[list[PredicateInstance]]:
        temp_formula = Formula(copy.deepcopy(self.simulate_formula.formula))

        parsed_predicate_updates = parse_predicate_update_list(
            updated_predicates, self.instruction_encoder.instruction.predicates
        )
        for update in parsed_predicate_updates:
            temp_formula.formula_update(update)

        log(f"temp_formula: {temp_formula.formula}",'white')

        tmp_chcs = []

        for chc in self.instruction_encoder.instruction.chcs:
            tmp_chcs.append(CHC(Formula(copy.deepcopy(chc.formula.formula)), copy.deepcopy(chc.action)))
        
        unsatisfied = get_unsatisfies_for_each_chc(
            temp_formula, tmp_chcs
        )

        return unsatisfied, temp_formula
    

    def update_predicate(self, updated_predicates: list) -> list[list[PredicateInstance]]:
        parsed_predicate_updates = parse_predicate_update_list(
            updated_predicates, self.instruction_encoder.instruction.predicates
        )
        for update in parsed_predicate_updates:
            self.simulate_formula.formula_update(update)

    def get_currrent_fomula_state(self) -> list[list[PredicateInstance]]:
        tmp_chcs = []

        for chc in self.instruction_encoder.instruction.chcs:
            tmp_chcs.append(CHC(Formula(copy.deepcopy(chc.formula.formula)), copy.deepcopy(chc.action)))

        unsatisfied = get_unsatisfies_for_each_chc(
            self.simulate_formula, tmp_chcs
        )

        log(pretty_print_unsats(unsatisfied),'green')

        return unsatisfied, self.simulate_formula_relevant_to_encoding(self.simulate_formula)

    def unsatisfies_for_each(self) -> list[list[PredicateInstance]]:
        return get_unsatisfies_for_each_chc(
            self.simulate_formula, self.instruction_encoder.instruction.chcs
        )

    def final_check(self):

        log(f"final_check: {self.simulate_formula.formula}",'red')

        return verify(
            self.simulate_formula, self.instruction_encoder.instruction.chcs
        )
    
    def simulate_formula_relevant_to_encoding(self, fomula: Formula) -> list[list[PredicateInstance]]:
        return self.instruction_encoder.fliter_formula_relevant_to_encoding(
            fomula
        )


class VeriSafeAgent:
    def __init__(self, save_path: str, self_corrective: bool, memory_save: bool, memory_load: bool):
        self.save_path = save_path

        self.memory_save = memory_save
        self.memory_load = memory_load

        self.predicates = []
        self.chc_verifier = VeriSafeEngine(Config(verbose=True, use_self_consistency=self_corrective))

        self.memory = VeriSafeMemory()

    def load_memory(self):
        self.memory.load_memory(self.app_name)

    def save_experience(self):
        self.memory.save_experience(self.instruction, self.chc_verifier.instruction_encoder.instruction.chcs)

    def reset(self, app_name: str, instruction: str):
        self.app_name = app_name
        self.instruction = instruction

        self.memory.reset_instruction(instruction)
        self.load_memory()
        self.predicates = self.memory.predicates_list

    def make_CHC(self):
        if self.memory_load:
            matched, driven_experience = self.memory.Instruction_check()
            driven_experience = "<Driven Experience>\n" + json.dumps(driven_experience, ensure_ascii=False) + "\n</Driven Experience>"
            if matched:
                self.chc_verifier.encode_instruction(self.instruction, self.predicates, driven_experience)
                return self.chc_verifier.instruction_encoder.instruction
        
        self.chc_verifier.encode_instruction(self.instruction, self.predicates, "")

        return self.chc_verifier.instruction_encoder.instruction

    def generate_Roadmap_Feedback(self):
        op_to_natural = {
            "Equal": "is equal to",
            "NotEqual": "is not equal to",
            "GreaterThan": "is greater than",
            "GreaterThanOrEqual": "is greater than or equal to",
            "LessThan": "is less than",
            "LessThanOrEqual": "is less than or equal to",
        }

        unsatisfied_lists, relevant_formula = self.chc_verifier.get_currrent_fomula_state()

        feedback_lines = []
        self.actions = {}

        for i, chc in enumerate(self.chc_verifier.instruction_encoder.instruction.chcs):
            rule_label = f"F{i+1}"
            self.actions[rule_label] = chc.action.name

            action_name = chc.action.name
            if action_name.lower().startswith("done"):
                title_str = "To complete the task"
            else:
                title_str = f"To perform {action_name}"

            formula_predicates = chc.formula.formula
            current_chc_unsatisfied = unsatisfied_lists[i]

            satisfied_indices = []
            cond_lines = []

            for idx_pred, pred in enumerate(formula_predicates):
                pred_name = pred.predicate_def.name
                pred_desc = "(" + pred.predicate_def.description + ")"
                if pred_desc:
                    pred_title = f"{pred_name} {pred_desc}"
                else:
                    pred_title = pred_name

                arg_strings = []
                for arg_key, val_inst in pred.arguments.items():
                    cmp_op = val_inst.comparison_operator
                    if cmp_op is not None:
                        op_str = op_to_natural.get(cmp_op.name, "is equal to")
                    else:
                        op_str = "is equal to"

                    val_str = val_inst.value
                    if str(val_str) == "?":
                        val_str = "unknown"
                    elif str(val_str) == "*":
                        val_str = "anything"
                    elif str(val_str) == "⊥":
                        val_str = "nothing"

                    arg_strings.append(f"{arg_key} {op_str} '{val_str}'")

                joined_args = ", ".join(arg_strings)
                line_str = f"{idx_pred+1}. {pred_title}"
                if joined_args:
                    line_str += " " + joined_args

                cond_lines.append(line_str)

                if pred not in current_chc_unsatisfied:
                    satisfied_indices.append(idx_pred + 1)

            chc_text = (
                f'{rule_label}: "{title_str}, you must satisfy the following conditions:\n'
                + "\n".join(cond_lines)
            )

            if len(satisfied_indices) > 0:
                step_str = ", ".join(str(x) for x in satisfied_indices)
                chc_text += f"\nSo far, you have achieved step {step_str}."

            if not current_chc_unsatisfied:
                chc_text += "\nThis action is completed."

            chc_text += '"'

            feedback_lines.append(chc_text)

        feedback_str = "\n\n".join(feedback_lines)
        return feedback_str

    def update_predicate_by_action(self, updated_predicates: list):
        unsatisfyed, updated_predicate = self.chc_verifier.update_predicate(updated_predicates)

    def predicate_level_verification(self, action: str, updated_predicates: list) -> tuple[bool, str]:
        unsatisfied_after, temp_formula = self.chc_verifier.simulate_update(updated_predicates)

        unsatisfied_chc_indices = [i for i, unsat_list in enumerate(unsatisfied_after) if unsat_list]

        original_chcs = self.chc_verifier.instruction_encoder.instruction.chcs

        wrong_conditions = []
        correct_conditions_map = {}

        for up in updated_predicates:
            up_name = up.get("Predicate")
            if not up_name:
                continue

            target_chc_index = None
            correct_predicate_ref = None

            for i in unsatisfied_chc_indices:
                for p in original_chcs[i].formula:
                    if p.predicate_def.name == up_name:
                        target_chc_index = i
                        correct_predicate_ref = p
                        break
                if target_chc_index is not None:
                    break

            if not correct_predicate_ref:
                continue

            mismatch_found = False
            for field_key, updated_val in up.items():
                if field_key in ("Predicate", "Reasoning"):
                    continue
                if field_key not in correct_predicate_ref.arguments:
                    continue

                correct_val = correct_predicate_ref.arguments[field_key].value
                if str(correct_val) not in ("*", "?") and str(correct_val) != str(updated_val):
                    mismatch_found = True
                    break

            if mismatch_found:
                wrong_conditions.append(up)
                correct_conditions_map[up_name] = correct_predicate_ref

        if wrong_conditions:
            correct_conds_str = ""
            for wcond in wrong_conditions:
                wname = wcond.get("Predicate", "")
                if wname in correct_conditions_map:
                    correct_conds_str += f"{str(correct_conditions_map[wname])}\n"

            wrong_conds_str = "\n".join(str(x) for x in wrong_conditions)

            feedback = predicate_level_feedback.format(
                PREVIOUS_ACTION=action,
                WRONG_CONDITIONS=wrong_conds_str,
                CORRECT_CONDITIONS=correct_conds_str
            )
            return False, feedback

        self.chc_verifier.update_predicate(updated_predicates)
        return True, ""

    def rule_level_verification(self, critical_action_name: str, critical_action: dict, updated_predicates):
        unsatisfied_all, simulated_formula = self.chc_verifier.simulate_update(updated_predicates)

        target_chc_indexes = []
        for i, chc in enumerate(self.chc_verifier.instruction_encoder.instruction.chcs):
            if chc.action.name == critical_action_name:
                target_chc_indexes.append(i)

        if not target_chc_indexes:
            return True, "No matching rule for critical action."

        for idx in target_chc_indexes:
            if unsatisfied_all[idx]:
                unsatisfied_list = unsatisfied_all[idx]

                wrong_current_list = []
                for pred_in_chc in unsatisfied_list:
                    current_pred = simulated_formula.find_closest(pred_in_chc)
                    if current_pred is not None:
                        wrong_current_list.append(current_pred)
                    else:
                        wrong_current_list.append(pred_in_chc)

                target_conditions = self.chc_verifier.instruction_encoder.instruction.chcs[idx].formula.formula

                feedback = rule_level_feedback.format(
                    CRITICAL_ACTION=critical_action_name,
                    PREVIOUS_ACTION=critical_action,
                    WRONG_CONDITIONS=wrong_current_list,
                    TARGET_CONDITIONS=target_conditions
                )
                return False, feedback

        self.chc_verifier.update_predicate(updated_predicates)
        return True, "Success"
    
    def save_experience(self):
        if self.memory_save:
            self.memory.save_experience(self.instruction, self.chc_verifier.instruction_encoder.instruction.chcs)
