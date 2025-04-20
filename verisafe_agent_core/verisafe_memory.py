# verisafe_memory.py
import os
import csv
import json

from model.GPT_model import GPT_Model

from utils_.utils_ import generate_numbered_list

class VeriSafeMemory:
    def __init__(self):
        self.memory_path = "./action_verifier/verisafe_agent/verisafe_agent_memory"

        self.GPT = GPT_Model()
        
        self.app_name = None
        self.app_memory = []
        self.predicates_list = None

        self.instruction = None
        self.action_experience_memory = {} 

    def load_memory(self, app_name: str):
        self.app_name = app_name
        with open(os.path.join("./dataset/predicates", self.app_name + ".json"), "r", encoding="utf-8") as f:
            self.predicates_list = json.load(f)

        file_path = f"./verisafe_agent_core/verisafe_agent_memory/{self.app_name}_experience.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    self.action_experience_memory = json.load(f)
                    print(f"[load_action_experience_memory] Loaded action experience memory from {file_path}.")
                except json.JSONDecodeError:
                    print(f"[load_action_experience_memory] File found but JSON decode failed. Initializing empty memory.")
                    self.action_experience_memory = {}
        else:
            print(f"[load_action_experience_memory] No existing action experience memory found. Starting new memory.")
            self.action_experience_memory = {}
    

    def reset_instruction(self, instruction: str):
        self.instruction = instruction

    def Instruction_check(self):
        tmp_memory = []
        for key in self.action_experience_memory.keys():
            tmp_memory.append(key)

        system_prompt, user_prompt = self.Instruction_check_Prompt(self.instruction, generate_numbered_list(tmp_memory))
        result = self.GPT.text_query(system_prompt, user_prompt)

        if result["answer"]["APIs"] is not None:
            result_apis = []
            for api in result["answer"]["APIs"]:
                if api in self.action_experience_memory.keys():
                    result_apis.append({"action_name": api, "used predicates": self.action_experience_memory[api]})
            return True, result_apis
        else:
            return False, result


    def save_experience(self, instruction_text: str, chc_list):


        filtered_chc = []
        for idx, chc in enumerate(chc_list):
            if chc.action.name.lower().startswith("done"):
                continue
            chc_str = f"{idx+1}) {str(chc.formula)} -> {chc.action.name}"
            filtered_chc.append(chc_str)

        if not filtered_chc:
            print("No non-Done CHCs to save.")
            return None


        chc_string = "\n".join(filtered_chc)


        old_experience_json = None
        if self.action_experience_memory:
            old_experience_json = json.dumps(self.action_experience_memory, ensure_ascii=False)

        system_prompt, user_prompt = self.chc_to_fixed_json_prompt(
            app_name=self.app_name,
            instruction_text=instruction_text,
            chc_string=chc_string,
        )

        result = self.GPT.text_query(system_prompt, user_prompt)
        merged_obj = result["answer"]
        if isinstance(merged_obj, dict):
            for action_key, preds_dict in merged_obj.items():

                old = self.action_experience_memory.get(action_key, {})

                if isinstance(old, dict) and isinstance(preds_dict, dict):
                    old.update(preds_dict)
                    self.action_experience_memory[action_key] = old
                else:
                    self.action_experience_memory[action_key] = preds_dict

        save_filename = f"./verisafe_agent_core/verisafe_agent_memory/{self.app_name}_experience.json"
        with open(save_filename, "w", encoding="utf-8") as f:
            json.dump(self.action_experience_memory, f, indent=2, ensure_ascii=False)

        print(f"[Action_Save] Updated action_experience_memory saved to {save_filename}.")
        return self.action_experience_memory
    
    def chc_to_fixed_json_prompt(self, app_name: str, instruction_text: str, chc_string: str):

        old_experience_promt = f"""
**OLD EXPERIENCE JSON** (previously stored experience):
{self.action_experience_memory}

You must ensure that if the similar action/predicate is found among the new CHCs, you do not remove the old information. 
Instead, produce a single unified and more generalized explanation that includes both the old and any new content.
"""

        system_prompt = f"""You are a system that processes a list of CHC strings and transforms them to more general action name and predicate descriptions.

[Generalized Action/Predicate Description]
Each CHC line looks like: "Predicate(...) → Action()". 

**Steps to follow**:
1. understand CHC rules that are equally variations of instructions.
2. Rename the Action in a CHC rule to its generalized form. (e.g. SearchForBestRestaurants -> SearchPlace)
3. Write a generalized explanation of why the predicates in the CHC rule are used.
4. !Caution! Do not change the predicate names.
5. If the CHC rule is multi-line, do all the lines.
6. Output only a valid JSON object.

{old_experience_promt}
"""

        user_prompt = f"""App Name: {app_name}

User Instruction:
"{instruction_text}"

CHC String:
{chc_string}

[Output JSON Format]
{{
  "<you need to generalize Action's name>": {{
    "SomePredicate": "<generate description of why the predicate is used in terms of a generalized Action (don't look at the valuable's value, look at the name of the variable, it will be helpful to make it more generalized).>"
    ...
  }}
  ...
}}
"""
        return system_prompt, user_prompt


    def Instruction_check_Prompt(self, instruction, Experience_list):
        system_prompt = \
f"""Given a user instruction, you think about the combination of APIs that could be used to perform that instruction in a mobile environment. You respond with a list of all the APIs that could be used(related to the user instruction). (If none of them are appropriate, you can respond APIs with []).
response JSON format: {{"Reasoning": <reasoning>, "APIs": ["API1", "API2", ...]}}
"""

        user_prompt = \
f"""Begin!

User's instruction:
{instruction}

Known APIs:
{Experience_list}

Response:
"""

        return system_prompt, user_prompt