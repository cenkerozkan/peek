# Task protocol

One file = one task. Read this file before starting any task.

## Layout

```
tasks/
  README.md      this protocol
  TEMPLATE.md    the shape of a task file
  todo/          tasks not yet done — work these in ascending number order
  done/          finished tasks, with their Outcome section filled in
```

## How to work a task

1. **Pick the lowest-numbered file in `tasks/todo/`.** Do not skip ahead. Later tasks
   assume earlier ones are finished.
2. **Read the whole task file before writing code.** Also read `CLAUDE.md` for the project's
   facts and constraints, and `CONVENTIONS.md` for how the code must be written. Both, every
   time.
3. **Implement only what the task says.** The task lists the files you may create or modify.
   Do not touch anything outside that list. If the task seems to require a change to a file
   it does not list, stop and write that in the Outcome section instead of doing it.
4. **Run the acceptance check** given in the task. It must pass.
5. **Fill in the `## Outcome` section** at the bottom of the task file (see below).
6. **Stop and wait for the review.** Leave everything uncommitted in the working tree. Do not
   commit, do not move the task file, do not start anything else.
7. **Once the review is approved:** commit, then move the file —
   `git mv tasks/todo/003-x.md tasks/done/003-x.md`.
8. **Stop.** One task per session. Do not start the next one.

## The Outcome section

Before moving a task to `done/`, append this to the task file and fill it in honestly:

```markdown
## Outcome

**Status:** done | partial | blocked

**Files changed:**
- path/to/file.py (new)
- path/to/other.py (modified)

**Acceptance check:** passed | failed — paste the actual command output

**Deviations:** anything you did differently from the task, and why. "none" if none.

**Problems:** anything unclear in the task, anything you could not do, anything you
guessed at. Be specific. This section is read — an honest "the task did not say what
the return type should be, I assumed list[dict]" is more useful than silence.
```

**Report what actually happened.** If the acceptance check failed, say so and paste the
output. If you finished only part of the task, mark it `partial` and say which part is
missing. A task marked `done` that is not done costs far more to discover later than an
honest `partial` costs now.

## Rules

- **Never reopen a task in `done/`.** If something needs fixing, the architect writes a new
  task. Do not edit files in `done/` except to fill in the Outcome section.
- **Never write your own task files.** If you think work is missing, note it in Outcome.
- **Never delete task files.**
- Task files are committed to git. They are the project record.
