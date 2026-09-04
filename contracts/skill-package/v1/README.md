# Skill Package Contract v1

An unpacked skill package has this layout:

```text
skills/<namespace>/<skill-id>/
  SKILL.md
  references/   optional
  scripts/      optional
  assets/       optional
```

The namespace and skill ID are derived from the directory path, which remains authoritative. `SKILL.md` must begin with YAML frontmatter whose parsed value conforms to `skill.schema.json`. A frontmatter `name` or optional `metadata.ai4sdlc.namespace` that disagrees with the path produces validation feedback; it does not replace the path-derived identity.

All regular files below the skill directory contribute to its content hash. Published packages must not contain symbolic links or paths that escape the skill directory. These filesystem rules are part of the contract even though JSON Schema cannot express them.
