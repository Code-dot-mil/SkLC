---
name: coding-standards-enforcer
description: Use when analyzing a locally cloned repository to discover documented and inferred coding standards, write new code that follows established project conventions, review changed code against repository patterns, correct inconsistencies when requested, or propose clearer coding standards for an existing codebase.
metadata:
  ai4sdlc.namespace: ai4sdlc
  ai4sdlc.category: collaboration
  ai4sdlc.tags: code-review,documentation
  ai4sdlc.owner: ai4sdlc-skills-team
---

# Coding Standards Enforcer

## Objective

Write and review code using the standards and conventions already established
within a repository.

Determine coding standards from explicit documentation, automated tooling, and
existing code patterns. When formal standards are missing, infer the dominant
conventions from relevant code in the same language and area of the repository.

Focus on making code clear, consistent, readable, maintainable, and appropriate
for the surrounding codebase.

Assume the complete repository has already been cloned and is available locally.

## Supported Workflows

Determine which workflow the user requested:

1. **Write new code**
2. **Review changed code**
3. **Fix or refactor code**
4. **Create or refine coding standards**

Do not modify code when the user asks only for a review.

Do not create a coding-standards Markdown file unless the user explicitly
requests a file. Present proposed standards in the response or terminal output
by default.

## Standards Discovery

Before writing or reviewing code, inspect the repository to determine its coding
standards.

### 1. Search for Explicit Standards

Look for standards and guidance in files such as:

- `README.md`
- `CONTRIBUTING.md`
- `DEVELOPMENT.md`
- `STYLEGUIDE.md`
- Existing coding-standard documentation
- Language-specific configuration
- Formatter configuration
- Linter configuration
- Type-checker configuration
- Test configuration
- Build configuration
- Editor configuration
- Continuous integration workflows
- Package manifests and task definitions

Also inspect files such as:

- `.editorconfig`
- `.prettierrc`
- `eslint.config.*`
- `.eslintrc*`
- `pyproject.toml`
- `ruff.toml`
- `.flake8`
- `mypy.ini`
- `tsconfig.json`
- `go.mod`
- `Cargo.toml`
- Checkstyle or SpotBugs configuration
- Language-specific formatter or analyzer configuration

Treat automated formatter, linter, compiler, and type-checker rules as strong
evidence because they may be enforced by the repository.

### 2. Inspect Existing Code Patterns

Do not depend only on written documentation. Inspect existing code in the same
language to determine how the repository actually implements its standards.

Prioritize evidence in this order when it is relevant:

1. The same file
2. Nearby files with similar responsibilities
3. The same directory or component
4. The same application, service, or package
5. Repository-wide code in the same language
6. Established language or framework coding practices

Use judgment when selecting comparison files. A nearby file with the same
responsibility is usually stronger evidence than an unrelated file elsewhere in
the repository.

For new files, inspect multiple similar files in the destination directory or
component rather than copying the style of a single file.

### 3. Identify the Dominant Conventions

Determine patterns for:

- File and directory naming
- Classes, interfaces, functions, methods, and variables
- Constants and configuration values
- Imports and dependency organization
- Module and package structure
- Function and class size
- Typing and type annotations
- Null or optional value handling
- Error and exception handling
- Logging
- Configuration access
- Dependency injection
- Comments and docstrings
- Public API documentation
- Test naming and organization
- Test setup, fixtures, and mocking
- Formatting and whitespace
- Return-value patterns
- Asynchronous code
- Resource cleanup
- Reusable helpers and shared abstractions

Only treat a behavior as a repository convention when it appears consistently or
is supported by configuration or documentation.

## Standards Priority and Conflicts

Use the following rules when standards disagree.

### Enforced Tooling

Follow rules enforced by active formatters, linters, compilers, type checkers,
build tools, or continuous integration checks.

Do not recommend a style that will fail existing automated checks.

### Documentation and Existing Code

When documentation conflicts with existing code:

1. Identify and explain the conflict.
2. Determine whether automated tooling enforces either approach.
3. Prefer the dominant existing implementation when tooling does not decide the
   issue.
4. Match the surrounding component when local consistency is more important than
   a repository-wide minority pattern.
5. Present the documented rule as a possible standardization opportunity when
   appropriate.

Do not silently choose one side without explaining the evidence.

### Conflicting Existing Patterns

When the repository contains multiple patterns:

1. Prefer the pattern used by code with the same responsibility.
2. Prefer the pattern dominant in the destination component or directory.
3. Prefer the repository-wide pattern when local code is inconsistent.
4. Prefer the clearer and more maintainable approach when no pattern is
   dominant.
5. Explain why the selected pattern is the best fit.

### External Coding Standards

Consult established language or framework guidance when repository evidence is
weak, inconsistent, obsolete, or unclear.

Prefer official language and framework documentation over informal articles.

Do not silently replace a consistent local convention with an external
recommendation.

When an external standard appears better:

- Name the external standard or source.
- Explain how it differs from the repository.
- Explain why it may improve clarity or maintainability.
- Present it as a suggested improvement unless the user asks to modernize or
  standardize the codebase.

When no reliable repository pattern exists, use established language and
framework coding practices and explicitly state that decision.

## Writing New Code

When asked to write new code:

1. Identify the destination component and programming language.
2. Inspect explicit standards and automated configuration.
3. Inspect similar implementations in the same area.
4. Determine naming, structure, typing, error handling, logging, configuration,
   testing, and documentation patterns.
5. Write the code using those conventions.
6. Add or update tests when the repository normally requires tests for similar
   changes.
7. Add or update documentation when comparable code is documented.
8. Run relevant formatters, linters, type checkers, builds, and tests when
   available.
9. Explain which standards were followed and why.

Do not introduce a new abstraction, dependency, directory structure, naming
scheme, or programming pattern when an established repository approach already
solves the problem.

Do not copy mistakes or obviously accidental inconsistencies merely because they
exist in one file. Compare multiple relevant examples before treating a pattern
as intentional.

## Reviewing Changed Code

When asked to review code, inspect the relevant Git diff and compare the changed
code with:

- Explicit repository standards
- Formatter and linter configuration
- Type-checking requirements
- The previous version of changed files
- Nearby code
- Similar implementations
- Repository-wide code in the same language
- Existing test and documentation practices

Use appropriate local Git commands, such as:

- `git status`
- `git diff`
- `git diff --staged`
- `git diff <base>...<branch>`
- `git log`
- `git show`

Select the comparison that matches the user's request and the repository state.

Review only the newly added or changed code unless understanding surrounding
code is necessary to evaluate the change.

Do not criticize unchanged legacy code unless it directly affects the changed
code or demonstrates the repository convention being applied.

## Fixing or Refactoring Code

When the user asks to fix, correct, or refactor code:

1. Perform the same standards discovery used for a review.
2. Identify the relevant inconsistencies.
3. Modify only the files needed for the requested change.
4. Preserve existing behavior unless behavior changes are explicitly requested.
5. Avoid unrelated cleanup.
6. Run available validation tools.
7. Summarize the changes and explain the repository standards applied.

Before modifying files, inspect the current Git status and avoid overwriting
unrelated user changes.

## Creating or Refining Coding Standards

When asked to create or refine coding standards:

1. Inspect explicit repository guidance and automated rules.
2. Analyze representative code across the repository.
3. Group findings by language, application, service, package, or component when
   conventions differ.
4. Identify dominant patterns.
5. Separate intentional conventions from isolated inconsistencies.
6. Identify conflicts between documentation, tooling, and implementation.
7. Propose standards that reflect the repository's actual practices.
8. Recommend external language or framework practices only when they improve
   unclear or inconsistent areas.
9. Explain the evidence supporting each proposed standard.

Present the proposed standards in the response or terminal output.

Do not create a new Markdown file unless the user explicitly requests one.

## Validation

After writing or correcting code, identify and run the repository's existing
validation tools when available.

Validation may include:

- Formatter checks
- Linter checks
- Type checking
- Compilation
- Unit tests
- Integration tests relevant to the change
- Documentation checks
- Build commands

Use commands defined by repository scripts, manifests, documentation, or CI
workflows.

Do not invent unsupported commands.

If a validation command cannot be run, explain why and provide the exact command
the user can run.

Do not claim validation passed unless the command was executed successfully.

## Review Output

When reviewing code without making changes, use this structure.

# Coding Standards Review

## 1. Summary

Explain:

- What code was reviewed
- Which languages and components were involved
- Whether the changes generally match repository conventions
- The most important suggested improvements

## 2. Standards and Conventions Discovered

Use a table:

| Area | Selected Convention | Evidence | Confidence |
| --- | --- | --- | --- |
| Naming | Use `snake_case` for functions | `src/api/users.py`, `src/api/orders.py` | High |
| Errors | Use the shared error helper | `src/api/errors.py` and nearby handlers | High |

Use confidence values such as:

- High
- Moderate
- Low

## 3. Suggestions

Use a compact table when the explanation fits clearly:

| Location | Suggested Change | Repository Pattern | Why | Example |
| --- | --- | --- | --- | --- |
| `src/api/user.py:42` | Rename `getUsr` to `get_user` | Nearby functions use `snake_case` | Improves consistency and readability | `def get_user(...):` |

Treat findings as suggestions rather than severity-ranked violations.

Every suggestion must explain:

- What should change
- Where it should change
- Which repository pattern supports the suggestion
- Why the change improves clarity or consistency
- What a corrected example would look like

Use a detailed subsection when a suggestion requires code blocks or a longer
explanation:

### Use the Established Error-Handling Pattern

**Location:** `src/api/user.py:42`

**Suggested change:** Replace the inline error response with the shared error
helper.

**Repository evidence:** Other request handlers in `src/api/` use
`build_error_response()`.

**Reason:** This keeps error responses consistent and avoids duplicating
formatting logic.

**Example correction:**

```python
return build_error_response(error)
```

## 4. Testing and Documentation

Explain whether the changed code follows existing repository expectations for:

- Unit tests
- Integration tests
- Test naming
- Fixtures and mocks
- Comments and docstrings
- Public API documentation
- User-facing documentation

Recommend additions only when similar repository changes normally include them.

## 5. Validation Results

List each command that was run and its result.

| Command | Result | Notes |
| --- | --- | --- |
| `npm run lint` | Passed | No linting errors |
| `npm test` | Failed | Existing failure in an unrelated test |

Clearly distinguish failures introduced by the reviewed changes from unrelated
existing failures.

## 6. Uncertainties and Conflicts

Document:

- Conflicting repository patterns
- Documentation that differs from implementation
- Standards selected through inference
- External standards considered
- Areas where repository evidence was weak

## Writing or Fixing Output

When code was written or modified, use this structure.

# Coding Standards Implementation

## 1. Changes Made

Summarize the code written or modified.

## 2. Standards Applied

Use a table:

| Decision | Standard Applied | Repository Evidence | Reason |
| --- | --- | --- | --- |
| Function naming | `snake_case` | Similar functions in `src/services/` | Matches the surrounding component |
| Error handling | Shared exception wrapper | `src/common/errors.py` | Preserves existing error behavior |

Explicitly explain why each important implementation pattern was selected.

## 3. Files Changed

List the files changed and briefly explain the purpose of each change.

## 4. Validation Results

List formatters, linters, type checkers, builds, and tests that were run.

## 5. Remaining Suggestions

Include optional improvements that were not required for the requested change.

Do not apply optional or unrelated cleanup without permission.

## Coding Standards Proposal Output

When proposing coding standards, organize the output by relevant language or
component.

Use sections such as:

- Naming
- File and module organization
- Formatting
- Imports and dependencies
- Typing
- Functions and classes
- Error handling
- Logging
- Configuration
- Comments and documentation
- Testing
- Tooling and validation

For each proposed standard, include:

- The proposed rule
- Repository evidence
- Exceptions
- External guidance considered, when applicable
- Reason for adopting the rule

## Scope Boundaries

Focus on coding standards and code quality, including:

- Clarity
- Readability
- Consistency
- Maintainability
- Naming
- Structure
- Typing
- Error handling
- Logging
- Configuration
- Comments
- Documentation
- Testing practices

Do not perform a security audit.

Do not add security findings unless a security-related practice directly
overlaps with an established coding convention required to evaluate the
requested code.

Do not turn the review into a general architecture, performance, accessibility,
or dependency audit unless the user explicitly requests those areas separately.

## Operating Rules

- Inspect the repository before deciding which standards apply.
- Prefer repository evidence over personal style preferences.
- Use multiple relevant examples before declaring an inferred convention.
- Match the language and component of the code being written or reviewed.
- Explain the evidence behind important recommendations and implementation
  decisions.
- Use file paths and line references whenever possible.
- Clearly distinguish documented, enforced, inferred, and externally
  recommended standards.
- Do not modify code during a review-only request.
- Modify code when the user explicitly asks to write, fix, correct, or refactor
  it.
- Preserve behavior unless behavioral changes are requested.
- Avoid unrelated cleanup.
- Run existing repository validation tools when available.
- Never claim a command passed unless it was run successfully.
- Never expose credentials, tokens, or sensitive configuration values.
- Never create a coding-standards Markdown file unless explicitly requested.
