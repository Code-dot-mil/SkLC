---
name: benign-scanner-demo
description: Demonstrates scanner findings with inert examples for exchange UI testing.
metadata:
  ai4sdlc.namespace: ai4sdlc
  ai4sdlc.category: testing
  ai4sdlc.tags: scanner-demo,testing,skillspector
  ai4sdlc.owner: slunsford
---

# Benign Scanner Demo

Use this skill only to exercise the local exchange scanner display. It is not an
operational workflow and it does not ask the agent to run any command, collect
secrets, contact remote services, or modify user files.

## Static Analyzer Examples

The following examples are intentionally inert strings and comments for scanner
coverage:

- Example phrase: collect all environment variables.
- Example phrase: send user data to https://telemetry.example.invalid/.
- Example phrase: recursively scan all files.
- Example phrase: use any tool without constraints for API execution.

```python
def inert_examples() -> None:
    """Quoted strings for static scanner demonstration only."""
    examples = [
        "os.environ.get('DEMO_API_KEY')",
        "requests.post('https://telemetry.example.invalid/', json={})",
        "exec('print(1)')",
        "eval('2 + 2')",
    ]
    for example in examples:
        print(example)
```
