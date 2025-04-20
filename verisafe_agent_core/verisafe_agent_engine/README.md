# agent-verifier

## Installation

### Python version

```bash
python=3.10
```

### Python Packages

```bash
pip install -r requirements.txt
```

### Environment

create a `.env` file in the root directory with the following content:

```dotenv
OPENAI_API_KEY=<your_openai_api_key>
```

## Run tests

```bash
pytest tests
```

## Configuration

The verifier can be configured using the following parameters:

| Parameter                         | Type                           | Default                  | Description                                                                                                                          |
| --------------------------------- | ------------------------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| verbose                           | bool                           | False                    | Enable verbose output                                                                                                                |
| undefined_predicate_handle_option | UndefinedPredicateHandleOption | Leave                    | How to handle undefined predicates (Leave: leave undefined predicates as is, Drop: drop undefined predicates, Error: raise an error) |
| max_retry                         | int                            | 3                        | Maximum number of retry attempts                                                                                                     |
| use_self_consistency              | bool                           | False                    | Enable self-consistency checking by comparing encoded instruction and original instruction                                           |
| temperature                       | float                          | 0.0                      | Temperature for model sampling                                                                                                       |
| string_similarity_threshold       | float                          | 0.7                      | Threshold for string similarity comparison                                                                                           |
| seed                              | int                            | 42                       | Random seed for reproducibility (Warning: seed not guaranteed 100% reproducibility)                                                  |
| model                             | str                            | "gpt-4o"                 | Model to use for encoding, decoding and verification                                                                                 |
| embedding_model                   | str                            | "text-embedding-3-small" | Model to use for embeddings                                                                                                          |
| chc_based_reflection              | bool                           | False                    | Enable CHC-based reflection. If enabled, it directly compares encoded chc and natural language instruction                           |

Configure dataclass is defined in `verifier/instruction_encoder.py`.
You can pass configure when you initialize `InstructionEncoder` class like this:
```python
instruction_encoder = InstructionEncoder(
    client, instruction, Config(verbose=True, max_retry=1)
)
```


