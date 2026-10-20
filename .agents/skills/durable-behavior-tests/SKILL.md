---
name: durable-behavior-tests
description: Use when adding, revising, or reviewing automated tests for a feature change, especially when a request adds or removes UI, API fields, routes, or other visible behavior.
---

# Durable Behavior Tests

Keep committed tests focused on observable behavior and stable contracts. A test is worth maintaining when it can catch a plausible regression that matters to a user or caller, and an ordinary implementation change should not require rewriting it.

## Choose what to keep

Before committing a new test, identify the behavior it protects and how a real defect would make it fail. Exercise that behavior through the closest practical public interface, with enough real components to catch integration mistakes. Mock external systems at their boundary; avoid mocking the code whose behavior the test claims to verify.

Prefer a small number of representative scenarios that cover important states and transitions over many assertions that repeat the change request. Assert outcomes rather than component structure, internal calls, exact wording, or incidental layout unless those details are themselves the contract.

When a behavior distinguishes owners, other users, administrators, or anonymous callers, actually switch identity before observing each actor's result. After a denied mutation, verify the protected state is unchanged. A test name or comment that claims another actor saw the result does not substitute for that actor's request.

Tests written to guide an edit can be useful temporarily. Remove them before committing if their only purpose is to prove that a named control, function, parameter, or old implementation was added or deleted. The positive mirror can be just as weak: “the new button exists” often says little about whether its action works. Keep a test when it exercises the resulting workflow and would fail for a meaningful defect.

Absence is worth asserting when absence *is* the behavior: access must be denied, sensitive content must be hidden, a deleted item must not appear in results, or closing a panel must remove it. Test the relevant state and consequence, rather than every removed artifact.

When revising existing tests, preserve independent protections that still apply. Replace assertions invalidated by the requested behavior without dropping coverage for unrelated validation, authorization, or data integrity. If an actor loses access to a workflow, a denial test cannot prove that the workflow still validates input or protects immutable data for actors who retain access; move those checks to an authorized path. Review the test diff before committing.

## Review test value

For each new test, ask:

1. What user or caller outcome fails if this test fails?
2. Could the feature be broken while this test still passes? If so, strengthen the scenario or use a broader boundary.
3. Would a harmless refactor or copy change break it? If so, assert a more stable outcome.
4. Is it redundant with a stronger test? If so, remove it.

Trim assertions about exact HTML wrappers, CSS classes, messages, incidental timestamps, and unchanged unrelated fields unless one protects a specific contract or likely regression. A missing control can be a useful UI check, but it does not prove that a direct request is denied; test the resulting permission boundary and state as well. Do not keep a separate assertion merely to make the test count look comprehensive.

If a test asserts a button label or error sentence, ask whether a copy edit should fail the test. If not, assert the accessible action, response status, and resulting state instead. Keep a UI absence check only when it catches a user-facing defect beyond the direct-request test. Do not use raw HTML snippets such as `href=`, `action=`, tag names, or classes as stand-ins for an unavailable action; use a semantic control query when the UI contract matters, or omit the redundant assertion.

For example, after moving assessments out of a catalog, a durable test opens an assessment, shows the latest scan state and report, then closes it. A temporary change check merely asserts that the catalog no longer contains an “Assessment” tab. Keep the former; discard the latter once the edit is verified.
