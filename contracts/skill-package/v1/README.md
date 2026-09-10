# Skill Package Contract v1

An unpacked skill package has this layout:

```text
<skill-name>/
  SKILL.md
  references/   optional
  scripts/      optional
  assets/       optional
```

The package directory name is the authoritative standard skill name. It must
match `^[a-z0-9](?:[a-z0-9-]{0,62})$`. The package may appear at any filesystem
depth; parent directories, including a catalog namespace directory when one is
present, are not part of the portable package identity.

`SKILL.md` must begin with YAML frontmatter whose parsed value conforms to
`metadata.schema.json`. Its required `name` must exactly match the package
directory name. A mismatch is a validation error. The optional
`metadata.ai4sdlc.namespace` value is descriptive catalog metadata only and
does not replace or qualify the standard skill name.

All regular files below the skill directory contribute to its content digest.
The SHA-256 input is constructed from every package file in sorted POSIX
relative-path order. For each file, hash these bytes in order:

1. The UTF-8 encoded POSIX relative path.
2. One NUL byte.
3. The exact file bytes.
4. One NUL byte.

Serialized contract fields represent the result as `sha256:<64 lowercase hex
characters>`. Implementations may use the lowercase hexadecimal value without
the prefix internally.

A package must contain no symbolic link at any depth, no resolved path that
escapes the package directory, no individual file larger than 5 MiB, and no
more than 500 regular files. Unreadable paths and unsupported filesystem object
types fail validation. These filesystem and digest rules are part of the
contract even though JSON Schema cannot express them.

When a consumer recursively discovers packages beneath a root, it selects the
outermost directory containing `SKILL.md` and does not descend into that
package. Discovery does not follow symbolic links. This prevents a nested
package-owned `SKILL.md` from being interpreted as a second package. The
selection root itself is a package when it contains `SKILL.md`; the root does
not otherwise need to be a package or follow a namespace layout.
