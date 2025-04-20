import os
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
from openai.types.create_embedding_response import CreateEmbeddingResponse, Usage
from openai.types.embedding import Embedding


result = os.getenv("OPENAI_API_KEY")

if result is None:
    print("Failed to load .env file")

    class MockChatCompletion:
        def create(self, **kwargs):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "This is a mock response from the OpenAI API.",
                            "role": "assistant",
                        },
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
                "created": 0,
                "id": "mock-id",
                "model": kwargs.get("model", "gpt-3.5-turbo"),
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 0,
                    "prompt_tokens": 0,
                    "total_tokens": 0,
                },
            }

    class MockCompletion:
        def create(self, **kwargs):
            return {
                "choices": [
                    {
                        "text": "This is a mock text completion from the OpenAI API.",
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
                "created": 0,
                "id": "mock-id",
                "model": kwargs.get("model", "text-davinci-003"),
                "object": "text_completion",
                "usage": {
                    "completion_tokens": 0,
                    "prompt_tokens": 0,
                    "total_tokens": 0,
                },
            }

    class MockEmbeddings:
        def create(self, **kwargs):
            input_texts = kwargs.get("input", [])
            if isinstance(input_texts, str):
                input_texts = [input_texts]

            embedding_dimension = 1536
            embeddings = []

            for _ in input_texts:
                vector = np.random.randn(embedding_dimension)
                normalized_vector = vector / np.linalg.norm(vector)
                embeddings.append(normalized_vector.tolist())

            # CreateEmbeddingResponse 타입을 사용하여 응답 생성
            embedding_objects = [
                Embedding(embedding=embedding, index=i, object="embedding")
                for i, embedding in enumerate(embeddings)
            ]

            return CreateEmbeddingResponse(
                data=embedding_objects,
                model=kwargs.get("model", "text-embedding-ada-002"),
                object="list",
                usage=Usage(prompt_tokens=0, total_tokens=0),
            )

    class MockOpenAI:
        def __init__(self, **kwargs):
            self.chat = MockChatCompletion()
            self.completions = MockCompletion()
            self.embeddings = MockEmbeddings()

    client = MockOpenAI()

else:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
