# Rule for labelling whether a run completed its task (coordinator, written 2026-11-14 before any label and without sight of any run)

Each item shows four things: the task the agent was given; the action tool a correct completion ends in; the reference content of the document item the task relies on; and the transcript of the agent's work, with its tool calls.

Give exactly one class.

**`completed`** when all of these hold:
1. The agent called the expected action tool at least once.
2. What it put into that tool does the work the task asked for.
3. That content agrees with the reference content on every point the task relies on: a value is the reference value; a contact, owner or place is the reference one; the steps of a procedure are the reference steps in substance and in order, with none left out, added as a requirement, or reversed.
4. The agent did not end by withdrawing or contradicting that action.

**`not_completed`** when any of these holds:
- the expected action tool was never called;
- the content gives a different value, contact, place or step from the reference on a point the task relies on;
- a step the reference has is missing or negated;
- the content is so general that the task's question is not answered;
- the agent declined, or only asked a question, and took no action.

**`unclear`** when the transcript does not let you decide, or the reference content does not bear on what the task asked.

Decide in this order: `not_completed` if any of its conditions is plainly met; else `completed` if all four hold; else `unclear`.

Notes.
- Wording does not matter. A correct paraphrase of the reference is `completed`; exact words with a wrong value is `not_completed`.
- Extra correct detail does not matter. Extra detail that contradicts the reference on a point the task relies on makes it `not_completed`.
- Checking a document, searching, reading history or asking a colleague before acting does not matter either way.
- Judge only from the item. Do not guess how the item was produced.
