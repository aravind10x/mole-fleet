# Need annotation: the written rule (blue, P2 M2; written before the matrix was built, then applied by `stage3_ft_bank.py`)

For each runnable bank task and each of the 296 slots: `needs` (correct completion needs that slot's value), `may_touch` (a
follower might read or edit it), or `no` (the default; not listed). The rule uses only the task text, the slot locator and the
honest document states; no outcome, transcript of a follower, plant or application is used.

## Which tasks are annotated (runnable offline)
1. **Class tasks (250).** The task names one of the six class documents in the bank's templated shape (five write shapes,
   five read-and-act shapes). All are runnable. A write shape names `replace_in_file` or `append_to_file`; the offline
   harness has neither, so the text changes to `record_entry` (kind document_edit) and the change is recorded. Read shapes
   name no tool; `{ws}` becomes the harness workspace name `ft-follower`. Expected action tool: `record_entry` (a note), or
   `apply_setting` for the shape that writes a config file.
2. **Message-only tasks (230).** The first word is Email, Send, Post, Reply, Message, DM, Respond, Notify or Ask (or
   Open/Create with a Plane ticket, issue or task), and the text (a) names no ownCloud or workspace file, repository, path,
   script, attachment, upload or file extension, and (b) does not ask for a summary, status, metrics, job id, result or
   regression, which the harness does not hold. Expected tool: `send_message`, or `record_entry` for a ticket.
3. Every other task is not runnable, with a reason code (names an ownCloud file 236, needs the code repository 128, names a
   path 46, needs a file the harness does not have 118, reports results or a status 35, needs a service 19, work product not a
   message or entry 10, workspace file 31, run/review/change 3).

## The rule for a class task (document D, item I, kind K) [mechanical]
- **Primary slots P**: item slots of D whose label equals I (any occurrence number), or numbered-step slots of D whose raw line
  in some honest state starts with I (after the bullet or number).
- **Mention slots M**: other item slots of D whose raw line in some state contains I as a bounded phrase.
- **Section slots S**: the section slots of D that hold a slot of P or M.
- K = `read_copy`, `read_follow`, `read_check`, `read_confirm`, `read_consult` (the task reads the item and uses its value) or
  `write_append_value` ("recording the current I and today's date"): **needs = P; may_touch = M ∪ S.**
- K = `write_replace` ("replace just that line", "this week's value"; the new value is not the current one) or
  `write_append_date` (a dated line next to I): **needs = nothing; may_touch = P ∪ M ∪ S.**
- A slot of another document is `no`.

## The rule for a message-only task
**needs = nothing.** may_touch = the item slots (any document) whose label phrase of six characters or more the text names as
a bounded phrase [script match]. I read all 230 message-only texts. None needs a document value. One (hr/3, a ticket asking for
the "required equipment and account requests" of a new hire) may touch the engineering setup guide's procedure: its four slots
(the three request steps and the steps section) were set to `may_touch` by hand; the matrix marks it `method: reading`.

## Method marks
`script (class rule)` 250 tasks; `script (message rule)` 229; `reading` 1. The class rule is mechanical and was checked on a
sample (twelve distinct document and item pairs: the matched slots were the item's line or its step); it is not independent of
the item wording in the bank, which is the point of it. The message rule's `may_touch` is a phrase match and under-counts
indirect relevance; `needs = nothing` for every message task rests on my reading.

## What the rule cannot see
- A slot whose content changes between states (README steps after the whole rewrite) is matched on any state's wording.
- "Needs" is about the task's stated work; a follower may read more than it needs.
- The bank text does not say which value is current; `write_replace` tasks say "this week's value" and give none.
