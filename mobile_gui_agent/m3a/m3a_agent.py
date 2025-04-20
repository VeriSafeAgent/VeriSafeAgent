"""M3A agent. Multi-Modal Autonomous Agent from Android World by Google."""


import os
from PIL import Image

from model.GPT_model import GPT_Model

from mobile_gui_agent.agent import Agent, AgentInteractionData
from mobile_gui_agent.m3a.m3a_prompt import action_selection_prompt
from mobile_gui_agent.m3a.m3a_parser import m3aParser
from utils_.utils_ import generate_numbered_list

class M3AAgent(Agent):
    def __init__(self, save_path: str):
        super().__init__(GPT_Model(), 'm3a')
        self.history = []
        self.parser = m3aParser()
        self.natural_history = ['Opened the target app.']
        self.generated_action = None
        self.roadmap_feedback = None
        self.feedback = ""

        self.save = save_path
        os.makedirs(self.save, exist_ok=True)

        self.task_count = 0
        self.step_count = 0

    def get_generated_action(self):
        """ 생성된 액션을 반환 """
        return self.generated_action

    def get_action_history(self):
        """ 실행된 액션 히스토리를 반환 """
        return self.natural_history

    def reset(self, instruction: str) -> None:
        super().reset(instruction)
        
        folder_count = len([
            name for name in os.listdir(self.save)
            if os.path.isdir(os.path.join(self.save, name))
        ])
        folder_count = folder_count + 1

        self.save = os.path.join(self.save, str(folder_count))

        os.makedirs(self.save, exist_ok=True)

        file = open(self.save + '/instruction.txt', 'w')
        file.write(instruction)
        file.close()

        self.task_count += 1
        self.step_count = 0
        self.history = []
        self.natural_history = ['Opened the target app.']

    def set_Roadmap_feedback(self, roadmap_feedback: str) -> None:
        self.roadmap_feedback = roadmap_feedback

    def save_parsed_pair_and_get_path(self, xml, image):
        """PIL 이미지 객체를 temp 폴더에 저장하고 경로를 반환"""
        if image is None:
            print("Warning: Image is None!")
            return None
        
        image_path = os.path.join(self.save, f'{self.step_count}.png')
        xml_path = os.path.join(self.save, f'{self.step_count}.xml')

        image.save(image_path)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml)
        return xml_path, image_path

    def step(self, raw_xml: str, raw_screenshot: Image.Image) -> AgentInteractionData:    
        processed_screenshot, parsed_xml = self.parser.SoM(raw_screenshot, raw_xml)

        action_prompt = action_selection_prompt(
            self.instruction,
            generate_numbered_list(self.natural_history),
            parsed_xml,
            self.roadmap_feedback,
        )

        action_prompt = action_prompt + self.feedback
        _, screenshot_path = self.save_parsed_pair_and_get_path(parsed_xml, processed_screenshot)

        action = None
        reason = None
        description = None
        is_critical = None

        print(screenshot_path)

        while action is None or reason is None or description is None or is_critical is None:
            result = self.model.vision_query(action_prompt, "", [screenshot_path])
            response = result['answer']

            action = response.get('Action', None)
            reason = response.get('Reason', None)
            description = response.get('Description', None)
            is_critical = response.get('IsCritical', None)
            real_critical = response.get("Critical's_last_action?", None)
        
        self.natural_history.append(description)
        self.history.append(action)

        if real_critical.lower() != "yes":
            is_critical = "NONE"

        self.step_count += 1

        return AgentInteractionData(
            parsed_xml=parsed_xml,
            screenshot=processed_screenshot,
            is_critical=is_critical,
            reason=reason,
            description=description,
            action=action,
            response=response
        )
