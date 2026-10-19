# vlog-me · Claude Code harness

## Startup Workflow

1. Confirm this directory is `vlog-me`. Read `progress.md`, `feature_list.json`, and `session-handoff.md`.
2. Read `docs/workflow.md` for the current operation; consult the design for deeper decisions.
3. Run `./init.sh`. It checks local tools, contracts, lint and types without installing, rendering, downloading audio or calling a model.
4. Inspect existing changes before editing. This folder is not a Git repository; do not initialize or commit unless requested.

Start Claude Code with `./scripts/claude.sh` so it inherits project-local Node/npm. An earlier `./init.sh` invocation does not export its environment to the parent shell.

## Working Rules

- **Stay in scope — VLOG_SETUP_ONLY:** current authorization is environment setup and synthetic fixtures only. Do not read/process original photos or videos, download music/SFX/ASR models, upload, use paid media providers, or start production rendering.
- **One feature at a time:** maintain one active feature. Do not automatically start deferred features after setup passes.
- Claude Code is the only production agent interface. No Codex handoff, external coordinator or subagent workflow is configured.
- Use the unchanged official `.claude/skills/remotion-best-practices/SKILL.md` and relevant references. Project scope overrides upstream examples suggesting downloads, paid transcription, voiceover, automatic installs or rendering.
- Prefer existing Skills and tools. No Custom Skill is currently needed. Put project facts in project docs.
- Vlog type, story and tone come from each production prompt. Runtime is content-driven, without a fixed target duration. Earlier style preferences are references, not forced defaults.
- Preserve originals and existing artifacts. Helpers accept only generated `synthetic-*` runs. Never label real media as synthetic to bypass scope.
- `timeline.json` is the render input. Edit through Claude Code; do not maintain a second master timeline or launch native Remotion Studio from upstream examples.
- Permission patterns and helper checks are defense in depth, not an OS sandbox. Do not use direct commands to widen the authorized scope.
- Never print secrets, change global settings, push, deploy, send external messages or commit without the relevant explicit request.

## Verification Commands

```bash
./init.sh
./scripts/smoke-render.sh
```

The second command creates a new synthetic run, renders, decodes and measures it. It needs localhost port and browser permissions. No missing dependencies are downloaded automatically.

```bash
python3 scripts/synthetic.py status --run-id synthetic-RUN-ID
```

Use an actual ID from `work/`. `./scripts/npm.sh` supplies project-local Node/npm without changing shell settings.

## Definition of Done

A feature is done only when its scope has recorded evidence: relevant tests, lint, typecheck, render/negative cases and report links. Report PASS, FAIL, NOT_RUN and BLOCKED separately. Synthetic success does not establish ASR, editorial taste, real-media throughput, VFR/HDR support or platform copyright clearance.

## State and Recovery

Root `feature_list.json` tracks implementation; per-run `state.json` tracks execution. Notes summarize these states. A brief freezes run settings, but cannot override current authorization.

Failed/partial/locked/stale runs are retained. Inspect before recovery; create a fresh synthetic run instead of overwriting. Do not automatically remove locks. Reuse succeeded output only while input and output hashes match.

New-run defaults do not invalidate an existing run's frozen brief. Every write entrypoint rechecks current setup scope. `status` can inspect recorded generation failures without a complete manifest. Ctrl-C/SIGTERM cleanup stops owned command groups before releasing the lock; SIGKILL cannot be handled and requires inspection.

`./scripts/studio.sh RUN-ID` and the npm `studio` alias open only the verified encoded preview. They never start native Remotion Studio, a coding agent, a renderer or an install command. The loopback-only viewer serves a page and a frozen video snapshot; no write APIs or project directory access exist. It requires an unlocked, succeeded, hash-valid synthetic run and does not modify state or props. Stop it with Ctrl-C after use.

Live `--refresh` is removed and exits without changes. To see timeline edits, use Claude Code to edit a new pending synthetic run, render it, and open that succeeded run. Old props remain untouched. The 128 MiB snapshot cap applies to this synthetic viewer, not to production vlog duration. Do not bypass the viewer by running upstream `remotion studio` examples.

## End of Session

Update feature status, `progress.md`, `session-handoff.md`, and `reports/setup-report.md`. Record remaining limits and the next permitted action. Leave a restartable project with `./init.sh`; do not commit automatically.
