# Local GitLab Mock

This directory is a local development surface for the static skill exchange MVP.

It does not implement the GitLab API. It records enough local state to test the exchange building blocks before real GitLab integration:

- `mr/<id>.md.jsonl` stores mock MR and pipeline events.
- `mr-artifacts/<id>/<run-id>/` stores local MR review artifacts.
- `ci/scan.py` simulates the MR assessment job.
- `ci/publish.py` simulates the protected scheduled publication job.

Generated MR logs and artifacts are local throwaway outputs.
