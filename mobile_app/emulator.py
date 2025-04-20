#!/usr/bin/env python3

import sys
import os
import json
import socket
import threading
import argparse
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
from typing import Dict, List, Optional

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from mobile_gui_agent.m3a.m3a_parser import m3aParser


class EmulatorGUI:
    def __init__(self, root, agent_name: str):
        self.root = root
        self.root.title("VeriSafe Emulator Client")
        self.root.geometry("630x720")

        self.agent_name = agent_name

        self.host = "127.0.0.1"
        self.port = 12345
        self.sock = None
        self.connected = False

        self.agent_control = False
        self.app_name = ""
        self.current_action = {}
        self.action_verified = False

        if self.agent_name == "m3a":
            self.parser = m3aParser()

        self.predicates_data = {}
        self.selected_predicate_name = tk.StringVar(value="")
        self.predicate_entries = {}

        self.pending_updates = []

        self.create_widgets()

        self.connect_to_server()
        threading.Thread(target=self.receive_loop, daemon=True).start()


    def create_widgets(self):
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.lbl_agent_control = ttk.Label(info_frame, text="Agent_Control: False")
        self.lbl_agent_control.pack(side=tk.LEFT, padx=10)

        self.lbl_app_name = ttk.Label(info_frame, text="appName: (none)")
        self.lbl_app_name.pack(side=tk.LEFT, padx=10)

        self.lbl_action_verified = ttk.Label(info_frame, text="Action_Verified: False")
        self.lbl_action_verified.pack(side=tk.LEFT, padx=10)

        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill=tk.X, padx=5, pady=(0,10))

        self.lbl_current_action = ttk.Label(action_frame, text="Action: (none)")
        self.lbl_current_action.pack(side=tk.LEFT, padx=10)

        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(self.root, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right_frame.pack_propagate(False)

        ttk.Label(right_frame, text="Select Predicate:").pack(anchor="w", pady=(5,2))
        self.combo_predicate = ttk.Combobox(
            right_frame,
            textvariable=self.selected_predicate_name,
            state='readonly'
        )
        self.combo_predicate.pack(fill=tk.X, padx=5)
        self.combo_predicate.bind('<<ComboboxSelected>>', self.on_select_predicate)

        self.predicate_value_frame = ttk.Frame(right_frame)
        self.predicate_value_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_add = ttk.Button(
            right_frame,
            text="Add This Predicate Update",
            command=self.on_add_update
        )
        btn_add.pack(fill=tk.X, padx=5, pady=(0,5))

        btn_send = ttk.Button(
            right_frame,
            text="Send Update",
            command=self.on_send_update
        )
        btn_send.pack(fill=tk.X, padx=5, pady=(0,5))

        btn_no_send = ttk.Button(
            right_frame,
            text="No Update",
            command=self.no_send_update
        )
        btn_no_send.pack(fill=tk.X, padx=5, pady=(0,5))

        btn_remove = ttk.Button(
            right_frame,
            text="Remove Selected Update",
            command=self.on_remove_selected
        )
        btn_remove.pack(fill=tk.X, padx=5, pady=(0,5))

        self.updates_listbox = tk.Listbox(right_frame, height=10)
        self.updates_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,0))
        self.updates_hscroll = ttk.Scrollbar(
            right_frame, orient="horizontal",
            command=self.updates_listbox.xview
        )
        self.updates_hscroll.pack(fill=tk.X, padx=5, pady=(0,5))
        self.updates_listbox.configure(xscrollcommand=self.updates_hscroll.set)


    def on_remove_selected(self):
        sel = self.updates_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.updates_listbox.delete(idx)
        del self.pending_updates[idx]


    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print("[EmulatorGUI] Connected to server.")
        except Exception as e:
            print("[EmulatorGUI] Connection failed:", e)


    def receive_loop(self):
        buf = b""
        while self.connected:
            try:
                chunk = self.sock.recv(1)
                if not chunk:
                    break
                if chunk == b"\n":
                    line = buf.decode().strip()
                    buf = b""
                    if line:
                        self.handle_server_message(line)
                else:
                    buf += chunk
            except:
                break
        print("[EmulatorGUI] receive_loop 종료")


    def handle_server_message(self, line: str):
        try:
            data = json.loads(line)
        except:
            print("[EmulatorGUI] JSON error:", line)
            return

        if "Agent_Control" in data:
            self.agent_control = data["Agent_Control"]
            self.lbl_agent_control.config(text=f"Agent_Control: {self.agent_control}")

        elif "appName" in data:
            self.app_name = data["appName"]
            self.lbl_app_name.config(text=f"appName: {self.app_name}")
            self.load_predicates_for_app(self.app_name)

        elif "Action_Verified" in data:
            self.action_verified = data["Action_Verified"]
            self.lbl_action_verified.config(text=f"Action_Verified: {self.action_verified}")

        elif "Action" in data:
            self.current_action = data["Action"]
            self.lbl_current_action.config(text=f"Action: {self.current_action}")
            print("[EmulatorGUI] Received Action:", self.current_action)
            self.draw_screenshot_with_box()

        else:
            print("[EmulatorGUI] Unknown:", data)


    def load_predicates_for_app(self, app_name: str):
        path = os.path.join(project_root, "dataset", "predicates", f"{app_name}.json")
        if not os.path.isfile(path):
            print(f"[EmulatorGUI] No predicate file: {path}")
            return
        with open(path, 'r', encoding='utf-8') as f:
            self.predicates_data = json.load(f)

        names = list(self.predicates_data.keys())
        self.combo_predicate["values"] = names
        if names:
            self.combo_predicate.current(0)


    def on_select_predicate(self, event=None):
        """콤보박스에서 predicate 선택 시: description + enum/Text/Boolean UI 생성"""
        # 기존 위젯 모두 제거
        for w in self.predicate_value_frame.winfo_children():
            w.destroy()

        pname = self.selected_predicate_name.get()
        if pname not in self.predicates_data:
            return

        # 1) description 레이블
        desc = self.predicates_data[pname].get("description", "")
        ttk.Label(self.predicate_value_frame,
                  text=desc,
                  wraplength=280,        # 텍스트 길면 자동 줄바꿈
                  foreground="gray30").grid(
                      row=0, column=0, columnspan=2,
                      sticky="w", pady=(0,8)
                  )
        self.predicate_value_frame.columnconfigure(1, weight=1)

        var_defs = self.predicates_data[pname].get("variables", [])
        self.predicate_entries = {}

        # 2) 변수별 입력 위젯
        for i, var_def in enumerate(var_defs, start=1):
            name       = var_def["name"]
            vtype      = var_def.get("type", "Text")
            enum_vals  = var_def.get("enum_values")   # enum 리스트

            # 레이블
            ttk.Label(self.predicate_value_frame,
                      text=f"{name} ({vtype}):")\
                .grid(row=i, column=0, sticky="w", pady=2)

            # a) enum_values 가 있으면 → readonly Combobox
            if enum_vals:
                cb = ttk.Combobox(
                    self.predicate_value_frame,
                    values=enum_vals,
                    state="readonly"
                )
                cb.grid(row=i, column=1, sticky="ew", padx=2)
                cb.current(0)
                self.predicate_entries[name] = cb

            # b) Boolean 타입 → True/False Combobox
            elif vtype.lower() == "boolean":
                cb = ttk.Combobox(
                    self.predicate_value_frame,
                    values=["True", "False"],
                    state="readonly"
                )
                cb.grid(row=i, column=1, sticky="ew", padx=2)
                cb.current(0)
                self.predicate_entries[name] = cb

            # c) 그 외 (Text, Time, Date, Number 등) → Entry
            else:
                ent = ttk.Entry(self.predicate_value_frame)
                ent.grid(row=i, column=1, sticky="ew", padx=2)
                self.predicate_entries[name] = ent


    def on_add_update(self):
        pname = self.selected_predicate_name.get()
        if pname not in self.predicates_data:
            return
        upd = {"Predicate": pname}
        for k, w in self.predicate_entries.items():
            v = w.get().strip()
            if v:
                upd[k] = v
        if len(upd) > 1:
            self.pending_updates.append(upd)
            self.updates_listbox.insert(tk.END, json.dumps(upd, ensure_ascii=False))


    def on_send_update(self):
        if not self.pending_updates:
            return
        msg = {
            "type": "updateState",
            "appName": self.app_name,
            "updates": self.pending_updates
        }
        self.sock.sendall((json.dumps(msg) + "\n").encode())
        self.pending_updates.clear()
        self.updates_listbox.delete(0, tk.END)

    def no_send_update(self):
        msg = {
            "type": "updateState",
            "appName": self.app_name,
            "updates": []
        }
        self.sock.sendall((json.dumps(msg) + "\n").encode())
        self.pending_updates.clear()
        self.updates_listbox.delete(0, tk.END)


    def draw_screenshot_with_box(self):
        if not self.current_action:
            return

        os.system("adb shell screencap -p /sdcard/emulator_screenshot.png")
        os.system("adb pull /sdcard/emulator_screenshot.png emulator_screenshot.png")

        os.system("adb shell uiautomator dump /sdcard/emulator_dump.xml")
        os.system("adb pull /sdcard/emulator_dump.xml emulator_dump.xml")

        try:
            im = Image.open("emulator_screenshot.png")
        except:
            im = Image.new("RGB", (400, 600), "gray")

        if not os.path.isfile("emulator_dump.xml"):
            return self.show_image_on_canvas(im)
        raw_xml = open("emulator_dump.xml", "r", encoding="utf-8").read()

        annotated, _ = self.parser.SoM(im, raw_xml)

        idx = self.current_action.get("index")
        if idx is not None:
            elem = self.parser.find_element_by_index(idx)
            if elem and elem.bbox_pixels:
                draw = ImageDraw.Draw(annotated)
                x1, y1 = elem.bbox_pixels.x_min, elem.bbox_pixels.y_min
                x2, y2 = elem.bbox_pixels.x_max, elem.bbox_pixels.y_max
                col = "green" if self.action_verified else "red"
                draw.rectangle([x1, y1, x2, y2], outline=col, width=5)

        self.show_image_on_canvas(annotated)


    def show_image_on_canvas(self, pil_img: Image.Image):
        """원본 비율 유지, 최대크기(600×1000) 이하로 축소해서 Canvas에 표시"""
        max_w, max_h = 300, 1000
        w, h = pil_img.size
        scale = min(max_w/w, max_h/h, 1.0)
        nw, nh = int(w*scale), int(h*scale)
        resized = pil_img.resize((nw, nh), Image.Resampling.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0,0,nw,nh))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "--agent",
        choices=["m3a"],
        default="m3a",
        help="Which agent parser to use?"
    )
    args = argp.parse_args()

    root = tk.Tk()
    EmulatorGUI(root, agent_name=args.agent)
    root.mainloop()


if __name__ == "__main__":
    main()
