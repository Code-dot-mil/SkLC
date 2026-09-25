# Assessment kit

Validate one local skill directory with Python 3.12 or newer. Validation requires
a readable UTF-8 `SKILL.md` with YAML frontmatter containing nonempty string
fields `name` and `description`. The name must match the directory name.
Additional metadata is allowed. Validation does not execute skill content or
assess its safety.

From the repository root, build the wheel:

```sh
uv build --wheel products/assessment-kit --out-dir release/assessment-kit
```

Copy the wheel into a separate working directory, then install and run it:

```sh
uv venv --python 3.12
uv pip install skill_assessment-0.1.0-py3-none-any.whl
uv run --no-project skill-assessment validate --skill ./my-skill
```

The command accepts a single directory, without a namespace or repository layout
requirement. It needs no exchange policy, site, scanner, or provider credentials.
Exit status is `0` for valid input, `1` for invalid or unreadable input, and `2`
for incorrect command usage. Diagnostics go to standard error on failure.

This first increment supports `validate` only. The
[roadmap](https://github.com/Code-dot-mil/SkLC/blob/main/docs/roadmap.md)
describes the remaining assessment-kit work.
