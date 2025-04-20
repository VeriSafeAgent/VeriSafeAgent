from typing import TypedDict, Dict, List, Optional
from utils_ import *
from PIL import Image
import argparse
import os

from utils_.utils_ import log


os.environ["OPENAI_API_KEY"] = "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"

#python simulator.py --mobile_device emulator --agent m3a --verifier vsa --app com.google.android.deskclock --instruction "make alarm am 3:00 and set the timer to 30sec." --save_path ./history/clock\
#python simulator.py --mobile_device emulator --agent m3a --verifier vsa --app com.google.android.deskclock --instruction "Open the Clock app and create three new alarms with the following conditions: The first alarm should be set for 6:30 AM on weekdays (Monday to Friday) and labeled "Morning Workout". The second alarm should be set for 8:00 AM on weekends (Saturday and Sunday) and labeled "Relaxed Morning". The third alarm should be set for 10:00 PM every night and labeled "Wind Down" with a vibration-only mode. Once all alarms are created, go to the alarm list, and turn them all on." --save_path ./history/clock
#python mobile_app/emulator.py


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--agent',
        choices=['m3a'],
        required=True,
    )
    parser.add_argument(
        '--verifier',
        choices=['vsa'],
        required=True,
    )
    parser.add_argument(
        '--app_name',
        required=True,
    )

    parser.add_argument(
        '--instruction',
        required=False,
    )

    parser.add_argument(
        '--save_path',
        required=False,
    )

    parser.add_argument(
        '--mobile_device',
        choices=['emulator', 'real'],
        required=True,
    )

    args = parser.parse_args()

    app_name = args.app_name
    instruction = args.instruction
    save_path = args.save_path  
    mobile_device = args.mobile_device

    log(f"Save 경로: {save_path}")
    log(f"App 이름: {app_name}")
    log(f"Instruction: {instruction}")
    log(f"Mobile Device: {mobile_device}")

    if args.agent == 'm3a':
        from mobile_gui_agent.m3a.m3a_agent import M3AAgent

        agent = M3AAgent(save_path=save_path)

    from verisafe_agent_core.verification_server import VeriSafeServer

    if args.verifier == 'vsa':
        from verisafe_agent_core.verisafe_agent import VeriSafeAgent

        self_corrective = False
        memory_save = False
        memory_load = False

        verifier = VeriSafeAgent(save_path=save_path, self_corrective=self_corrective, memory_save=memory_save, memory_load=memory_load)
        verifier.reset(app_name=app_name, instruction=instruction)

    verifier_server = VeriSafeServer()
    verifier_server.operate(mobile_device, verifier, agent)


if __name__ == '__main__':
    main()
