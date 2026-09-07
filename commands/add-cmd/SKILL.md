---
name: add-cmd
description: Add a new reusable command to the POW Codex command collection when the user wants to create and validate a new POW workflow.
---

# Add a POW command

Create one focused Codex Skill in the POW repository.

## Confirm the workspace

Work only in a POW clone whose repository root contains both:

- `package.json` with the package name `pow-codex-commands`
- `scripts/pow.mjs`

If either marker is missing, stop and ask the user to open their POW clone. Do not create a `commands/` directory in an unrelated repository.

## Gather the command design

Ask one question at a time. Establish:

1. A short action-oriented name using lowercase kebab-case.
2. The command's purpose and observable result.
3. When the command should activate and when it should not.
4. The workflow, required inputs, and expected output.
5. Any side effects, approval boundaries, or failure conditions.
6. Whether deterministic scripts, references, or assets are genuinely needed.

Skip a question only when the user has already supplied its answer. Keep the command self-contained and avoid optional files that do not improve the workflow.

Present a concise design summary covering the destination, activation description, workflow, supporting files, and validation. Wait for explicit approval before writing files.

## Create the command

Before editing, confirm that `commands/<name>` does not exist. If it does, stop and explain that updating an existing command is a separate change.

Create `commands/<name>/SKILL.md` with:

- YAML frontmatter containing a matching `name` and a concise, discriminating `description`.
- Instructions that preserve the approved purpose, authorization boundaries, and stopping conditions.
- Supporting resources only when the approved design requires them.

Do not leave unfinished placeholders. Do not modify commands outside the new directory.

## Validate and hand off

Run:

```sh
node scripts/pow.mjs validate
git diff -- commands/<name>
```

Fix validation failures only within the new command. Report the files created and the validation result. Do not stage, commit, push, create branches, or open pull requests.
