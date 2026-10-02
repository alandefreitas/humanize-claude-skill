---
name: humanize
description: Remove AI writing patterns from a text in English, Spanish or Portuguese. Use when the user says humanize, "make this sound human", "remove AI tells", "de-slop", or wants a draft checked before it goes out. The bundled scanner (model-backed AI tells, core vocabulary, linters) does the detection. The skill acts on its report and re-runs until the text is clean.
argument-hint: <file-path or pasted text> [--lang en|es|pt] [--spoken]
---

# Humanize

The scanner finds the problems. You rewrite.

1. Put the text in a file. Pasted text goes to a temporary file whose name ends in `.md` (use `mktemp`). A file path is used as is.
2. Run the report:

   ```zsh
   ~/.claude/skills/humanize/humanize.py <file>
   ```

   Add `--lang en|es|pt` when the user named the language or the report says it could not tell. Add `--spoken` for a talk script. `--help` lists the rest.
3. Read the report. Each section says how to treat it. Deterministic findings and off-list words are binding: fix each one, or keep it with a one-line reason. For each model flag, read the sentence and confirm or reject the flag. Linter notes are a second opinion. The last section lists the rules only you can apply, including the delete test on every clause. Then rewrite. If the user gave a writing sample, match its register.
4. Re-run the report on the rewrite. Repeat until it meets its own "Done when" condition. Three rounds at most.
5. Deliver what "Done when" asks for: the final text (written back to the file when the input was a file), then the rejected flags, kept words and cut clauses, each with its reason.

Exit code 2 means the model server was down. The report says so and tells you what to do by reading. Say in your output that the model did not run. Never pretend it did.
