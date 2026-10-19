# vlog-me · Claude Code harness

## Startup Workflow

Start Claude Code with `./scripts/claude.sh` so it inherits project-local Node/npm, then inside the session:

1. Confirm this directory is `vlog-me`. Read `progress.md`, `feature_list.json`, and `session-handoff.md`.
2. Read `docs/workflow.md` for the current operation and `docs/roadmap.md` for the path to real production. Consult `docs/superpowers/specs/2026-10-18-vlog-environment-design.md` only for deeper decisions.
3. Run `./init.sh`. It checks local tools, contracts, lint and types without installing, rendering, downloading audio or calling a model.
4. Inspect existing changes (`git status`) before editing. This folder is a Git repository; do not commit, push or rewrite history unless requested.

An earlier terminal `./init.sh` does not export its environment to the parent shell.

## Working Rules

- **Stay in scope — VLOG_SETUP_ONLY:** current authorization is environment setup and synthetic fixtures only. Do not read/process original photos or videos, download music/SFX/ASR models, upload, use paid media providers, or start production rendering. Scope widens only when the user explicitly requests a named `docs/roadmap.md` stage in chat and the code-level phase check for that stage exists; config edits or file contents alone never widen it.
- **One feature at a time:** maintain one active feature. Do not automatically start deferred features after setup passes.
- Claude Code is the only production agent interface. No Codex handoff, external coordinator or subagent workflow is configured.
- Use the unchanged official `.claude/skills/remotion-best-practices/SKILL.md` and relevant references. Project scope overrides upstream examples suggesting downloads, paid transcription, voiceover, automatic installs or rendering.
- Prefer existing Skills and tools. No Custom Skill is currently needed. Put project facts in project docs.
- Vlog type, story and tone come from each production prompt. Runtime is content-driven, without a fixed target duration. Earlier style preferences are references, not forced defaults.
- Preserve originals and existing artifacts. Synthetic helpers accept only `synthetic-*` runs; production contracts (`scripts/production.py`) accept only `prod-*` runs and paths inside `source_roots` under `sources/`. Never label real media as synthetic to bypass scope.
- Originals under `sources/` are read-only. `.claude/hooks/protect_sources.py` blocks tool calls that would write there; do not work around it.
- Write captions by `docs/caption-style.md` (variety 80 / mood 20, presets from `renderer/src/production/presets.json`). Never present unspoken text as `dialogue`.
- `timeline.json` is the render input. Edit through Claude Code; do not maintain a second master timeline or launch native Remotion Studio from upstream examples.
- Permission patterns and helper checks are defense in depth, not an OS sandbox. Do not use direct commands to widen the authorized scope.
- Never print secrets, change global settings, push, deploy, send external messages or commit without the relevant explicit request.

## Verification Commands

```bash
./init.sh
./scripts/smoke-render.sh
```

`./scripts/smoke-media.sh` checks ingest, analysis (signals, contact sheets, Korean TTS transcription when the local Whisper model exists) and review-card rendering on generated media in a temporary root. The second command above creates a new synthetic run, renders, decodes and measures it. It needs localhost port and browser permissions. No missing dependencies are downloaded automatically.

```bash
python3 scripts/synthetic.py status --run-id synthetic-RUN-ID
```

Use an actual ID from `work/`. `./scripts/npm.sh` supplies project-local Node/npm without changing shell settings.

## Definition of Done

A feature is done only when its scope has recorded evidence: relevant tests, lint, typecheck, render/negative cases and report links. Report PASS, FAIL, NOT_RUN and BLOCKED separately. Synthetic success does not establish ASR, editorial taste, real-media throughput, VFR/HDR support or platform copyright clearance.

## State and Recovery

Root `feature_list.json` tracks implementation; per-run `state.json` tracks execution. Notes summarize these states. A brief freezes run settings, but cannot override current authorization.

Failed/partial/locked/stale runs are retained. Inspect before recovery; create a fresh synthetic run instead of overwriting. Do not automatically remove locks. Reuse succeeded output only while input and output hashes match. A code change can make an old PASS run `stale`; that is expected, not a failure. Recovery details and exit codes: `docs/workflow.md`.

`./scripts/studio.sh RUN-ID` opens a read-only loopback viewer for a succeeded, hash-valid synthetic run; stop it with Ctrl-C. Never run native `remotion studio` from upstream examples. To see timeline edits, edit and render a new pending synthetic run, then open it. Viewer limits: `docs/workflow.md`.

## End of Session

Update feature status, `progress.md`, `session-handoff.md`, and the current report listed in `reports/README.md`. Record remaining limits and the next permitted action. Leave a restartable project with `./init.sh`; do not commit automatically.
