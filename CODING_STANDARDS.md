# Coding Standards

- **Deliver the agreed outcome.** Trace requirements to the originating task and
  later accepted decisions. Add dependencies, schemas, abstractions, options, and
  compatibility paths only for a current acceptance criterion or binding
  requirement. Resolve conflicts with older specifications explicitly; preserve
  accepted behavior while simplifying.
- **Keep contributions reviewable.** Simplify before splitting. Target a diff a
  maintainer can review in one hour, normally at most 300 manually reviewed changed
  lines across code, tests, configuration, and documentation. Report generated
  changes separately and explain necessary exceptions. Preserve readability and
  required behavior rather than compressing code to meet the target.
- **Respect responsibility boundaries.** Keep related decisions together and
  follow existing ownership conventions. Add indirection when it reduces the work
  needed to understand or change the code. Preserve unrelated and concurrent work.
- **Use existing tool capabilities.** Consult the supported public interface
  before adding wrappers or validators. Let standard tools own their format and
  build mechanics; verify the inputs, integration, failure handling, and consumer
  outcome this project owns. Reuse existing gates; repeat checks after relevant
  changes, failures, or new evidence that questions the result.
- **Test meaningful behavior.** Exercise observable outcomes and deliberate
  interfaces, including important failures and side effects. Establish external
  expectations from a supported public interface or authentic output, independently
  of the implementation. Assert diagnostic wording only when it is an explicit
  contract. Preserve unrelated authorization, validation, and integrity coverage.
- **Make intent readable.** Use meaningful names, clear test scenarios, and brief
  explanations of non-obvious choices. Comments should explain decisions rather
  than restate code.
- **Keep review fixes focused.** Inspect the cumulative diff after the first
  working implementation, before expanding it, and before requesting review.
  Remove unjustified additions and resolve scope growth against the current task.
  Report the acceptance evidence and any workflow that remains unverified.
