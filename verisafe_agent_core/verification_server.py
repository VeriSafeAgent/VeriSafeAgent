import json
import socket
import threading
import time
import os

from typing import Optional

from env.adb.adb_env import adbEnv
from mobile_gui_agent.agent import Agent
from verisafe_agent_core.verisafe_agent import VeriSafeAgent
from utils_.utils_ import log

REAL_DEVICE_TIMEOUT = 0.3

class VeriSafeServer:

    def __init__(self, host='0.0.0.0', port=12345, buffer_size=4096):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size

        self.client_socket = None
        self.client_address = None
        self.connected = False

        self.agent_control = False
        self.action_update_waiting = False

        self.mobile_device = None
        self.verifier: Optional[VeriSafeAgent] = None
        self.agent: Optional[Agent] = None
        self.env: Optional[adbEnv] = None

        self.previous_action = {}

        self.current_action = {}
        self.current_action_verified = False
        self.critical_action = False

        self.stop_operation = False

    def server_open(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()

        print(f"[VeriSafeServer] Listening on {self.host}:{self.port}")
        client, addr = server.accept()
        print(f"[VeriSafeServer] Connected to client: {addr}")
        self.client_socket = client
        self.client_address = addr
        self.connected = True

        thread = threading.Thread(target=self.handle_client, args=(client, addr), daemon=True)
        thread.start()

    def handle_client(self, client_socket, client_address):
        while True:
            data_line = self.readline(client_socket)
            if not data_line:
                print("[VeriSafeServer] 클라이언트 연결 종료 또는 데이터 수신 실패.")
                self.connected = False
                break

            try:
                data = json.loads(data_line)
            except json.JSONDecodeError as e:
                log(f"[VeriSafeServer] JSONDecodeError: {e}", "red")
                continue

            msg_type = data.get("type", "")

            if msg_type == "updateState":
                updates = data.get("updates", [])
                self.handle_updates(updates)
            else:
                log(f"[VeriSafeServer] Unknown msg_type or no 'type': {msg_type}", "yellow")

    def readline(self, client_socket):
        buffer = b""
        while True:
            try:
                chunk = client_socket.recv(1)
            except:
                return None
            if not chunk:
                return None
            buffer += chunk
            if chunk == b"\n":
                break
        return buffer.strip().decode()

    def send_json(self, data_dict):
        if not self.connected or not self.client_socket:
            return
        msg = json.dumps(data_dict) + "\n"
        try:
            self.client_socket.send(msg.encode())
            log(f"[VeriSafeServer -> Client] {msg}", "green")
        except Exception as e:
            log(f"[VeriSafeServer] Failed to send JSON: {e}", "red")

    def send_agent_control(self, value: bool):
        data = {"Agent_Control": value}
        self.send_json(data)

    def send_app_name(self, app_name: str):
        data = {"appName": app_name}
        self.send_json(data)

    def send_action_verified(self, verified: bool):
        data = {"Action_Verified": verified}
        self.send_json(data)

    def send_action(self, action: dict):
        data = {"Action": action}
        self.send_json(data)

    def handle_updates(self, updates):
        print(f"[VeriSafeServer] update: {updates}")

        if not self.action_update_waiting:
            self.verifier.update_predicate_by_action(updates)
            print("[VeriSafeServer] (No action waiting) 단순히 predicate만 업데이트했습니다.")
            return

        if self.critical_action != "NONE":
            success, feedback = self.verifier.rule_level_verification(
                critical_action_name=self.verifier.actions[self.critical_action],
                critical_action=self.current_action,
                updated_predicates=updates
            )
        else:
            if self.previous_action == self.current_action:
                success = True
                feedback = ""
                self.previous_action = {}
            else:
                success, feedback = self.verifier.predicate_level_verification(
                    action=self.current_action,
                    updated_predicates=updates
                )
                self.previous_action = self.current_action

        if not success:
            print("[VeriSafeServer] 검증 실패 -> Agent에게 피드백 전달 및 액션 재생성")
            del self.agent.natural_history[-1]
            self.agent.feedback = self.agent.feedback + "\nprevious output: " + str(self.output_action) + "\n" + feedback + "\n"

            self.current_action = {}
            self.current_action_verified = False
            self.critical_action = False
            self.action_update_waiting = False
        else:
            print("[VeriSafeServer] 검증 성공.")
            self.current_action_verified = True
            if self.mobile_device == "emulator":
                self.execute_adb_action(self.current_action)
                self.agent.feedback = ""
            else:
                self.send_action_verified(True)
                time.sleep(REAL_DEVICE_TIMEOUT)
                self.execute_adb_action(self.current_action)
                self.agent.feedback = ""

            self.action_update_waiting = False

    def operate(self, mobile_device: str, verifier: VeriSafeAgent, agent: Agent):
        self.mobile_device = mobile_device
        self.verifier = verifier
        self.agent = agent
        self.agent.reset(verifier.instruction)

        app_name = verifier.app_name

        self.env = adbEnv(parser=self.agent.parser, name="ADB_ENV")  
        self.env.load_env()
        self.env.load_app(app_name)

        self.server_open()

        print("[VeriSafeServer] Sending Agent_Control=True")
        self.send_agent_control(True)

        if self.mobile_device == "emulator":
            print(f"[VeriSafeServer] Sending appName={app_name}")
            self.send_app_name(app_name)

        encoded_instruction = verifier.make_CHC()

        instr_file = os.path.join(self.agent.save, "instruction.txt")
        with open(instr_file, "a+", encoding="utf-8") as f:
            f.write("\n"+str(encoded_instruction))
            f.write("\n")

        while not self.stop_operation:
            raw_xml = ""
            screenshot = None

            screenshot = self.env.get_screenshot()
            raw_xml = self.env.get_xml()

            roadmap = verifier.generate_Roadmap_Feedback()
            agent.roadmap_feedback = roadmap

            interaction_data = agent.step(raw_xml, screenshot)
            self.current_action = interaction_data.action
            self.critical_action = interaction_data.is_critical
            self.output_action = interaction_data.response

            if self.current_action.get("type", "") == "finish":
                print("[VeriSafeServer] finish action detected. final_check()..")
                success, feedback = self.verifier.rule_level_verification("Done", self.current_action, [])
                if success:
                    print("[VeriSafeServer] final_check passed! 종료합니다.")
                    self.stop_operation = True
                else:
                    print("[VeriSafeServer] final_check failed")
                    del self.agent.natural_history[-1]
                    self.agent.feedback += "previous output: " + str(self.output_action) + "\n" + feedback + "\n"
            else:
                self.current_action_verified = False
                self.send_action_verified(False)

                if self.mobile_device == "emulator":
                    self.send_action(self.current_action)
                else:
                    self.execute_adb_action(self.current_action)
                self.action_update_waiting = True

                if self.mobile_device == "emulator":
                    updated = self.wait_for_client_update(timeout=None)
                else:
                    updated = self.wait_for_client_update(timeout=REAL_DEVICE_TIMEOUT)

                if not updated and self.mobile_device == "emulator":
                    print("[VeriSafeServer] No_update")

        print("[VeriSafeServer] operate() 종료.")

    def wait_for_client_update(self, timeout: Optional[float]):
        start = time.time()
        if timeout is None:
            while self.action_update_waiting:
                time.sleep(0.05)
            return True

        while time.time() - start < timeout:
            if not self.action_update_waiting:
                return True
            time.sleep(0.05)
        return not self.action_update_waiting

    def execute_adb_action(self, action: dict):
        action_type = action.get("type")
        index = action.get("index")
        params = action.get("params", {})

        res = self.env.execute_action(action_type, index, params)
        if not res.success:
            print("[VeriSafeServer] adb_env.execute_action 실패:", res.feedback)
        else:
            print("[VeriSafeServer] adb_env.execute_action 성공.")
