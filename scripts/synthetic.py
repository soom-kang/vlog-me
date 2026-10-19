#!/usr/bin/env python3
"""Create, render and verify synthetic fixtures; never accept source media paths."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import time
import uuid
from common import (ROOT, OWNER, check_assets, digest, input_fingerprint, read_json,
                    run_command, run_lock, safe_path, validate_run, write_json,
                    require_setup_scope, read_state, run_path)
from inventory import collect


def create(seconds):
    config = require_setup_scope()
    if type(seconds) is not int or not 2 <= seconds <= 30:
        raise ValueError("Synthetic test length must be 2..30 seconds; this is not a vlog length limit")
    run_id = "synthetic-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    run = run_path(run_id)
    run.parent.mkdir(exist_ok=True)
    run.mkdir()
    with run_lock(run):
        state = {"owner": OWNER, "run_id": run_id, "stage": "fixture_generation", "status": "running",
                 "next_action": "wait for fixture preparation; do not resume partial output"}
        write_json(run / "state.json", state)
        print(json.dumps({"allocated_run": run_id}), flush=True)
        try:
            _prepare(run_id, run, seconds, config)
        except BaseException as exc:
            state.update(status="paused" if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else "failed",
                         error=str(exc)[:2000] or type(exc).__name__,
                         next_action="inspect retained generation artifacts; create a fresh synthetic run")
            write_json(run / "state.json", state, replace=True)
            raise
    return run_id


def _prepare(run_id, run, seconds, config):
    assets = run / "assets"
    assets.mkdir()
    fps = 30
    total_frames = (seconds + 2) * fps
    specifications = {
        "video": {"file": "video.mp4", "kind": "video", "frames": seconds * fps},
        "photo": {"file": "photo.png", "kind": "image"},
        "bgm": {"file": "bgm.wav", "kind": "audio", "frames": total_frames},
        "sfx": {"file": "sfx.wav", "kind": "audio", "frames": 15},
    }
    commands = [
        ["-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={seconds}", "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(assets / "video.mp4")],
        ["-f", "lavfi", "-i", "color=c=0x426e75:size=1280x720", "-frames:v", "1", str(assets / "photo.png")],
        ["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:duration={seconds + 2}", "-c:a", "pcm_s16le", str(assets / "bgm.wav")],
        ["-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=0.5", "-c:a", "pcm_s16le", str(assets / "sfx.wav")],
    ]
    for command in commands:
        run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", *command])
    for asset in specifications.values():
        asset["sha256"] = digest(assets / asset["file"])
    write_json(run / "fixture-manifest.json", {"owner": OWNER, "generator": "ffmpeg lavfi testsrc2/color/sine", "assets": specifications})
    write_json(run / "brief.json", {"purpose": "synthetic_setup", "source_roots": [], "vlog_type": None,
        "runtime_policy": "content_driven", "target_duration_seconds": None,
        "prompt_evidence": "Environment setup only; no original media or audio downloads.",
        "resolved_config": config})
    timeline = {"schema_version": 1, "purpose": "synthetic_setup", "fps": fps, "width": 1280, "height": 720,
        "duration_frames": total_frames,
        "clips": [{"id": "clip-video", "asset": "video", "from": 0, "duration": seconds * fps, "trim": 0},
                  {"id": "clip-photo", "asset": "photo", "from": seconds * fps, "duration": 60}],
        "audio": [
            {"id": "original-audio", "asset": "video", "audio_track": 1, "from": 0, "duration": seconds * fps, "trim": 0,
             "gain_db": [[0, -6], [seconds * fps - 1, -6]]},
            {"id": "background-test-tone", "asset": "bgm", "from": 0, "duration": total_frames, "trim": 0,
             "gain_db": [[0, -60], [15, -12], [30, -24], [seconds * fps - 15, -24], [seconds * fps, -12], [total_frames - 16, -12], [total_frames - 1, -60]]},
            {"id": "accent-test-tone", "asset": "sfx", "from": 30, "duration": 15, "trim": 0,
             "gain_db": [[0, -40], [2, -6], [12, -6], [14, -40]]}],
        "captions": [{"id": "caption-setup", "from": 15, "duration": 30, "kind": "editorial", "text": "영상·자막·오디오 연결 확인"},
                     {"id": "caption-photo", "from": seconds * fps, "duration": 60, "kind": "editorial", "text": "사진 구간 · 원본 미디어 미사용"}]}
    write_json(run / "timeline.json", timeline)
    write_json(run / "inventory.json", collect(run_id))
    require_setup_scope()
    write_json(run / "state.json", {"owner": OWNER, "run_id": run_id, "stage": "prepared", "status": "pending",
        "input_fingerprint": input_fingerprint(run), "next_action": "render synthetic preview", "human_review": "not_run"}, replace=True)


def status(run_id):
    state = read_state(run_id)
    if state["stage"] == "fixture_generation":
        return state
    try:
        run, _, _ = validate_run(run_id)
        if state.get("input_fingerprint") != input_fingerprint(run):
            return {**state, "recorded_status": state["status"], "status": "stale",
                    "reason": "input/code/config changed; preserve old output and create a new run"}
        if state["status"] == "succeeded":
            if set(state.get("outputs", {})) != {"preview.mp4", "frame.png", "verify.json", "audio-credits.md"}:
                raise ValueError("Succeeded state must contain the complete output set")
            for filename, expected in state["outputs"].items():
                if digest(safe_path(run, filename, True)) != expected:
                    raise ValueError("output hash mismatch")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {**state, "recorded_status": state["status"], "status": "stale", "reason": str(exc)}
    return state


def render(run_id):
    require_setup_scope()
    run, manifest, timeline = validate_run(run_id)
    with run_lock(run):
        saved = read_state(run_id)
        # Preparation is not a completed render or an approval. Revalidate edits
        # before the first render, while never refreshing a completed stale run.
        state = saved if saved.get('status') == 'pending' and saved.get('stage') == 'prepared' and not saved.get('outputs') else status(run_id)
        if state["status"] == "succeeded":
            return state
        if state["status"] != "pending":
            raise ValueError(f"Cannot resume {state['status']}; preserve the run and create a new synthetic run")
        for name in ["preview.mp4", "preview.partial.mp4", "bundle", "verify.json", "audio-credits.md", "frame.png"]:
            if safe_path(run, name).exists():
                raise ValueError("Existing partial/output requires inspection; no automatic overwrite")
        state.update(status="running", stage="render", input_fingerprint=input_fingerprint(run))
        write_json(run / "state.json", state, replace=True)
        started = time.monotonic()
        try:
            rendered = run_command(["node", str(ROOT / "renderer/scripts/render.mjs"), run_id], timeout=read_json(run / "brief.json")["resolved_config"]["synthetic_profile"]["timeout_seconds"])
            partial = safe_path(run, "preview.partial.mp4", True)
            probe = json.loads(run_command(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(partial)]).stdout)
            video = next(s for s in probe["streams"] if s["codec_type"] == "video")
            audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
            expected_duration = timeline["duration_frames"] / timeline["fps"]
            if abs(float(probe["format"]["duration"]) - expected_duration) > 0.1:
                raise ValueError("Unexpected encoded duration")
            if (video["width"], video["height"], video["codec_name"], audio["codec_name"]) != (1280, 720, "h264", "aac"):
                raise ValueError("Unexpected encoded streams")
            run_command(["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(partial), "-f", "null", "-"])
            measurement = run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(partial), "-vn", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
            loudness = json.loads(re.search(r'\{\s*"input_i".*?\}', measurement, re.S).group())
            if not all(math.isfinite(float(loudness[key])) for key in ["input_i", "input_tp"]) or float(loudness["input_tp"]) > -1:
                raise ValueError("Synthetic mix true peak exceeds test ceiling -1 dBTP")
            check_assets(run, manifest)
            require_setup_scope()
            if input_fingerprint(run) != state["input_fingerprint"]:
                raise ValueError("Inputs changed during render")
            # Exclusive link commits the verified file without replacing an existing target.
            os.link(partial, run / "preview.mp4")
            partial.unlink()
            run_command(["ffmpeg", "-v", "error", "-nostdin", "-n", "-ss", "1", "-i", str(run / "preview.mp4"), "-frames:v", "1", str(run / "frame.png")])
            with safe_path(run, "audio-credits.md").open("x", encoding="utf-8") as credit:
                credit.write("# Synthetic setup audio\n\nFFmpeg-generated 220/440/880 Hz test tones only. No library music acquired. Not a published vlog or platform license approval.\n")
            qa = {"status": "PASS", "scope": "synthetic_encoded_output", "duration_seconds": expected_duration,
                "dimensions": [video["width"], video["height"]], "codecs": [video["codec_name"], audio["codec_name"]],
                "loudness": loudness, "elapsed_seconds": round(time.monotonic() - started, 2),
                "child_max_rss_bytes_macos": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                "artifact_bytes": sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),
                "human_listen": "NOT_RUN", "platform_check": "not_checked", "asr": "NOT_RUN",
                "renderer_result": rendered.stdout[-1000:]}
            write_json(run / "verify.json", qa)
            state.update(status="succeeded", stage="synthetic_encoded_output", next_action="report synthetic evidence; real media remains disabled",
                outputs={name: digest(run / name) for name in ["preview.mp4", "frame.png", "verify.json", "audio-credits.md"]})
            write_json(run / "state.json", state, replace=True)
            return state
        except BaseException as exc:
            state.update(status="paused" if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else "failed", next_action="inspect retained partial artifacts; do not overwrite", error=str(exc)[:2000] or type(exc).__name__)
            write_json(run / "state.json", state, replace=True)
            raise


def main():
    def interrupted(signum, _frame):
        raise InterruptedError(f"Stopped by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "render", "status", "smoke"])
    parser.add_argument("--seconds", type=int, default=4)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.action in {"create", "smoke"}:
            if args.run_id:
                raise ValueError("create/smoke allocate a fresh run; do not accept --run-id")
            run_id = create(args.seconds)
            print(json.dumps({"created_run": run_id}), flush=True)
            if args.action == "smoke":
                print(json.dumps(render(run_id), indent=2))
        else:
            if not args.run_id:
                raise ValueError("--run-id is required")
            print(json.dumps(render(args.run_id) if args.action == "render" else status(args.run_id), indent=2))
    except KeyboardInterrupt:
        parser.exit(130, "PAUSED: interrupted; inspect retained run state\n")
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
