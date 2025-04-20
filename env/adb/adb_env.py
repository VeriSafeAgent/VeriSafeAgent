import json
import os
import subprocess
from typing import Tuple
from PIL import Image
from env.adb.adb import ADB
from env.base_env import Env, EnvInteractionResult
from mobile_gui_agent.parser import Parser
from utils_.utils_ import log


class adbEnv(Env):
    def __init__(self, parser: Parser, name: str):
        super().__init__(parser, name)
        self.directory_path = "./env/adb"
        self.screen_resolution = None
        self.curr_step = 0
        self.app_name = ""
        self.adb = ADB()

    def load_env(self):
        # Launch Android Emulator using subprocess.Popen
        emulator_process = subprocess.Popen(
            "~/Library/Android/sdk/emulator/emulator -avd AgentEmulator -no-snapshot -grpc 8554",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for emulator to fully boot
        print("Waiting for emulator to boot...")
        
        # Wait for the system to fully boot using direct command
        while True:
            import time
            time.sleep(1)
            status = os.system("adb shell getprop sys.boot_completed")
            if status == 0:  # Command executed successfully
                boot_state = os.popen("adb shell getprop sys.boot_completed").read().strip()
                if boot_state == "1":
                    log("Emulator boot completed", "red")
                    break
        print("Emulator boot completed")

    def load_app(self, app_name: str):
        # Get app package name from apps.json
        app_name = app_name.lower()
        self.app_name = app_name
        os.system(f"adb shell monkey -p {self.app_name} -c android.intent.category.LAUNCHER 1")

        import time
        time.sleep(1)


    def get_screenshot(self) -> Image.Image:
        raw_screenshot_path = f"{self.directory_path}/{self.curr_step}.png"
        print(raw_screenshot_path)
        os.system(
            # f"adb shell screencap -p /sdcard/screencap.png && adb pull /sdcard/screencap.png {raw_screenshot_path}")
            # f"adb exec-out screencap -p > {raw_screenshot_path}")
            f"adb emu screenrecord screenshot {os.path.abspath(raw_screenshot_path)}")
        screenshot = Image.open(raw_screenshot_path)
        if self.screen_resolution is None:
            self.screen_resolution = screenshot.size
        return screenshot


    def get_xml(self) -> str:
        raw_xml_path = f"{self.directory_path}/{self.curr_step}.xml"
        os.system(
            f"adb shell uiautomator dump /sdcard/window_dump0.xml && adb pull /sdcard/window_dump0.xml {raw_xml_path}")
        
        file = open(raw_xml_path, "r")
        raw_xml = file.read()
        return raw_xml
    
    def get_screenshot_with_som(self) -> Tuple[Image.Image, str]:
        raw_screenshot = self.get_screenshot()

        raw_xml_path = f"{self.directory_path}/{self.curr_step}.xml"
        os.system(
            f"adb shell uiautomator dump /sdcard/window_dump0.xml && adb pull /sdcard/window_dump0.xml {raw_xml_path}")
        file = open(raw_xml_path, "r")
        raw_xml = file.read()

        annotated_screenshot, ui_elements = self.parser.SoM(raw_screenshot, raw_xml)
        self.curr_xml = ui_elements

        # Save parsed UI elements to file
        parsed_xml_path = f"{self.directory_path}/{self.curr_step}_parsed.xml"
        with open(parsed_xml_path, "w") as f:
            f.write(ui_elements)
            
        if self.screen_resolution is None:
            self.screen_resolution = annotated_screenshot.size
        return annotated_screenshot, ui_elements
    
    def execute_action(self, action_type, index=None, params=None)->Tuple[bool, bool, dict]:
        if action_type == "click":
            target_element = self.parser.find_element_by_index(index)
            target_bounds = self.parser.get_bounds(index)

            # Convert bounds string "[x1,y1][x2,y2]" to coordinates
            coords = target_bounds.strip('[]').split('][')
            x1, y1 = map(int, coords[0].split(','))
            x2, y2 = map(int, coords[1].split(','))
            # Calculate center point of bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            self.adb.touch(center_x, center_y)

        elif action_type == "scroll":
            target_element = self.parser.find_element_by_index(index)
            target_bounds = self.parser.get_bounds(index)

            # Convert bounds string "[x1,y1][x2,y2]" to coordinates
            coords = target_bounds.strip('[]').split('][')
            x1, y1 = map(int, coords[0].split(','))
            x2, y2 = map(int, coords[1].split(','))
            # Calculate center point of bounds

            # Ensure the bounds are within the app boundary.
            y1 = max(y1, 200)
            y2 = min(y2, self.screen_resolution[1]-400)

            center_x = (x1 + x2) // 2
            top_xy = (center_x, y1+1)
            bottom_xy = (center_x, y2-1)
            
            if params["direction"] == "up":
                self.adb.drag(top_xy, bottom_xy, duration=1500)
            elif params["direction"] == "down":
                self.adb.drag(bottom_xy, top_xy, duration=1500)

        elif action_type == "long_click":
            target_element = self.parser.find_element_by_index(index)
            target_bounds = self.parser.get_bounds(index)

            # Convert bounds string "[x1,y1][x2,y2]" to coordinates
            coords = target_bounds.strip('[]').split('][')
            x1, y1 = map(int, coords[0].split(','))
            x2, y2 = map(int, coords[1].split(','))
            # Calculate center point of bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            self.adb.long_touch(center_x, center_y)
        elif action_type == "input":
            target_element = self.parser.find_element_by_index(index)
            target_bounds = self.parser.get_bounds(index)
            self.adb.type(params["text"])
        elif action_type == "navigate_back":
            self.adb.press(4)
        elif action_type == "navigate_home":
            self.adb.press(3)
        elif action_type == "keyboard_enter":
            self.adb.press(66)
        elif action_type == "finish":
            return EnvInteractionResult(success=True)
        elif action_type == "request_approval":
            approved = True
            # TODO: Popup user approval dialog
            return EnvInteractionResult(success=approved, feedback="You can proceed with the action.")
        
        #self.curr_step += 1
        return EnvInteractionResult(success=True)
        
    def _get_app_name(self):
        package_name = subprocess.check_output(
            "adb shell dumpsys activity top | grep \"ACTIVITY\" | tail -n 1 | awk '{print $2}' | cut -d '/' -f1",
            shell=True)
        return package_name[:-1]
    


