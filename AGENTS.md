# vlog-me · Codex worker rules

You are an Orca coding worker for vlog-me development. A Claude coordinator gives you a task and an approved plan document. Implement only that plan's scope. The full flow is in `docs/orca.md`.

## Scope

- Development work only: `scripts/`, `renderer/`, `tests/`, `docs/` and harness files named in the plan.
- You work in a child worktree on branch `orca/<task>`. Original media is not here, on purpose.
- If the plan seems to need real media, a render, a download or a change outside its scope, stop and ask the coordinator through the Orca `ask` command in your preamble.

## Never

- Never read, list or write `sources/`, `work/`, `raw/`, `assets/audio/` or `.env*`, in this worktree or in any other checkout by absolute path.
- Never push, merge into `main`, rebase `main` or rewrite shared history.
- Never edit `feature_list.json`, `progress.md`, `session-handoff.md` or `reports/`. The coordinator owns project state.
- Never weaken tests to make them pass: do not delete tests or assertions, loosen expected values or add skips unless the plan says so.
- Never change phase, scope or permission values in `config/` (`phase`, `source_roots`, `use_subagents`, `audio_*`, `production_render`, `upload`, `external_processing`).
- Never download, install packages, render video, call paid or external services, or run native `remotion studio`.

## Allowed

- Local commits on your `orca/<task>` branch.
- Editing hash-locked Skills only when the plan says so; then update `config/skills-lock.json`.

## Verify

Run before reporting done:

```bash
./scripts/dev-check.sh
```

It runs Python tests (except the live-config test, which needs original media), compileall, renderer lint, typecheck and tests. Do not run `./init.sh` here: its doctor needs original media and fails in a worktree by design.

## Report

Send `worker_done` with `--outcome succeeded` or `--outcome failed`, and include:
- files changed;
- verification commands and PASS/FAIL for each;
- anything left undone or uncertain.
