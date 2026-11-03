# Fresh-reader testing

Use this for a new guide or a substantial change to documentation structure. Test whether the documentation supplies understanding, separately from checking whether its claims are true.

Give the reader agent:

- Only the relevant persona's knowledge and task.
- The document and the linked prerequisites in the intended reading order.
- Realistic questions or a task the reader must accomplish.

Start the agent without parent conversation history. Do not provide the audit, expected answers, author rationale, hidden reference material, or implementation source. These can supply knowledge the documentation itself must provide. Ask the reader to stay within the supplied documents, cite passages supporting its answers, and explicitly identify anything it had to infer. No external browsing, edits, installations, or deployments are needed for this comprehension test.

Ask the reader to explain the purpose, choose the appropriate path, identify prerequisites, describe expected results and their limitations, and name the next action. Select questions relevant to the actual document rather than forcing every category into every test. Also ask where the reading order, terminology, or unexplained rules obstructed the task.

Compare its answers against independently verified facts. Correct wrong or unsupported answers, missing information, and confusing handoffs. A fluent answer based on outside knowledge is not a pass. Rerun affected questions with a fresh context after meaningful revisions. Stop when the scoped task can be completed from the intended path and no material comprehension gap remains; disclose unresolved failures or resource limits rather than looping indefinitely.

For example, a first-assessment guide should let a reader identify what to install, obtain a summary, explain why command success does not establish safety, and choose an action for an unresolved finding. The evaluator establishes correct answers from source separately; the reader receives only the guide and its documented prerequisites.

Report what documents and reader tasks were tested, the gaps found and corrected, and what was not exercised. Reading commands is not executing them, and agent comprehension is not proof of usability for every human reader.
