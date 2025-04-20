import os
import sys
import time
import json
import base64
from openai import OpenAI

from utils_.utils_ import log, parse_json


class GPT_Model():
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = "gpt-4o"
        self.max_retries = 3

    def safe_parse_json(self, response_content):
        """JSON 파싱을 안전하게 수행하고, 어떤 오류가 발생해도 None을 반환"""
        try:
            parsed_content = parse_json(response_content)
            if parsed_content is None:
                return None
            return json.loads(parsed_content)
        except Exception:
            print(f"error response_content: {parsed_content}")
            return None

    def text_query(self, system_prompt, user_prompt, verbose=True):
        if verbose:
            log(system_prompt, "yellow")
            log(user_prompt, "blue")

        retries = 0
        while retries < self.max_retries:
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
                ],
                temperature=0
            )

            finish_time = time.time()
            parsed_answer = self.safe_parse_json(response.choices[0].message.content)

            if parsed_answer is not None:
                result = {
                    "answer": parsed_answer,
                    "token": {
                        "input_token": response.usage.prompt_tokens,
                        "output_token": response.usage.completion_tokens,
                        "cached_token": response.usage.prompt_tokens_details.cached_tokens
                    },
                    "latency": finish_time - start_time
                }

                if verbose:
                    log(result["answer"], "green")

                return result
            
            retries += 1
            log(f"JSON 파싱 오류 발생. 재시도 {retries}/{self.max_retries}...", "red")

        raise ValueError("최대 재시도 횟수를 초과했습니다. JSON 파싱 오류가 지속적으로 발생합니다.")

    def vision_query(self, system_prompt, user_prompt, screenshot_paths, verbose=True):
        if verbose:
            log(system_prompt, "yellow")
            log(user_prompt, "blue")

        images = []
        for screenshot_path in screenshot_paths:
            with open(screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                images.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )

        retries = 0
        while retries < self.max_retries:
            start_time = time.time()

            if user_prompt == "":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                        {"role": "user", "content": images}
                    ],
                    temperature=0
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                        {"role": "user", "content": [{"type": "text", "text": user_prompt}] + images}
                    ],
                    temperature=0
                )

            finish_time = time.time()
            parsed_answer = self.safe_parse_json(response.choices[0].message.content)

            if parsed_answer is not None:
                result = {
                    "answer": parsed_answer,
                    "token": {
                        "input_token": response.usage.prompt_tokens,
                        "output_token": response.usage.completion_tokens,
                        "cached_token": response.usage.prompt_tokens_details.cached_tokens
                    },
                    "latency": finish_time - start_time
                }

                if verbose:
                    log(result["answer"], "green")

                return result

            retries += 1
            log(f"result: {response}")
            log(f"JSON 파싱 오류 발생. 재시도 {retries}/{self.max_retries}...", "red")

        raise ValueError("최대 재시도 횟수를 초과했습니다. JSON 파싱 오류가 지속적으로 발생합니다.")
