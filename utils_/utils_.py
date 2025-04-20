
import re
from termcolor import colored

def log(msg, color='white'):
    colored_log = colored(msg, color, attrs=['bold'])
    print(colored_log)

def parse_json(string: str):
    matches = re.search(r"\{.*\}", string, re.DOTALL)
    if matches:
        return matches.group(0)
    return None

def generate_numbered_list(items) -> str:
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))