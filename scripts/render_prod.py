#!/usr/bin/env python3
"""Render timeline.json of an assembled prod-* run into a long-form 1080p30 video.

Video renders in silent chunks that can resume after an interruption; the full mix renders once
as WAV, is loudness-normalized (about -14 LUFS, true peak -1.5 dBTP) and muxed. Each render goes to
a new render/vN/ folder and finishes as final.mp4 only after QA. Needs `production_render: true`.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import time

import audio_library
import common
from common import digest, read_json, run_command, run_lock, safe_path, write_json
import ingest
import production
import review
import assemble

FPS = 30
TARGET_LUFS = -14.0
TARGET_TP = -1.5
DEFAULT_CHUNK_SECONDS = 300


def chunk_plan(duration_frames, chunk_seconds):
    size = chunk_seconds * FPS
    return [{"id": f"{index:03d}", "start": start, "end": min(start + size, duration_frames)}
            for index, start in enumerate(range(0, duration_frames, size))]


def render_props(run, timeline, entries, staged):
    assets = {}
    used = {clip["source"] for clip in timeline["clips"]}
    # Deflicker is per source: one cleaned asset serves every clip of that source.
    clean = {clip["source"] for clip in timeline["clips"] if clip.get("deflicker")}
    baked = set()
    for entry in entries.values():
        if entry["id"] in clean:
            entry = review.deflickered(run, entry)
        if entry["id"] in used:
            entry = review.filled(run, entry)
            if "fill_of" in entry:
                baked.add(entry["id"])
        assets[entry["id"]] = {"src": entry["proxy"], "kind": "video" if entry["kind"] == "video" else "image"}
    for asset_id, info in staged.items():
        assets[asset_id] = {"src": info["src"], "kind": "audio"}
    # A baked fill already fills the 16:9 frame, so the renderer must not draw its own (CSS) blur behind it.
    clips = [{**clip, "aspect": review.WIDE} if clip["source"] in baked else clip for clip in timeline["clips"]]
    return {"timeline": {**timeline, "clips": clips}, "assets": assets}


def pick_version(run, props_sha):
    """Resume the newest version when its inputs match and it never finished; otherwise start a new one."""
    root = run / "render"
    root.mkdir(exist_ok=True)
    versions = sorted(int(p.name[1:]) for p in root.glob("v*") if p.name[1:].isdigit())
    if versions:
        last = root / f"v{versions[-1]}"
        plan = last / "render-plan.json"
        if plan.is_file() and not (last / "final.mp4").exists() and read_json(plan)["props_sha256"] == props_sha:
            return versions[-1], last, True
    version = (versions[-1] if versions else 0) + 1
    folder = safe_path(root, f"v{version}")
    folder.mkdir()
    (folder / "chunks").mkdir()
    return version, folder, False


LIMIT = 0.70   # linear peak ceiling before AAC; keeps the final true peak at or below -1 dBTP


def loudness(path, extra=""):
    log = run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vn", "-af",
                       f"{extra}loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json", "-f", "null", "-"]).stderr
    return json.loads(re.search(r'\{\s*"input_i".*?\}', log, re.S).group())


def finish(folder, timeline, timeout):
    chunks = read_json(folder / "chunks.json")["chunks"]
    listing = folder / "concat.txt"
    listing.write_text("".join(f"file 'chunks/{cid}.mp4'\n" for cid in sorted(chunks)), encoding="utf-8")
    video = safe_path(folder, "video.mp4")
    if not video.exists():
        run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-f", "concat", "-safe", "0",
                     "-i", str(listing), "-c", "copy", str(video)], timeout=timeout)
    mix = safe_path(folder, "mix.wav", True)
    measured = loudness(mix)
    normalize = (f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:measured_I={measured['input_i']}:"
                 f"measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
                 f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true,"
                 # quiet, peaky field audio makes loudnorm fall back to dynamic mode; cap peaks before AAC overshoot.
                 # Limiting at 4x the sample rate also catches inter-sample peaks (0.75 at 48 kHz measured -0.57 dBTP).
                 f"aresample=192000,alimiter=limit={LIMIT}:attack=5:release=50:level=disabled,aresample=48000")
    partial = safe_path(folder, "final.partial.mp4")
    if partial.exists():
        raise ValueError("Existing final.partial.mp4 requires inspection; no automatic overwrite")
    run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-i", str(video), "-i", str(mix),
                 "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", normalize, "-ar", "48000", "-c:a", "aac",
                 "-b:a", "256k", "-movflags", "+faststart", str(partial)], timeout=timeout)
    return partial, measured


def qa(partial, timeline, timeout):
    probe = json.loads(run_command(["ffprobe", "-v", "error", "-count_packets", "-show_streams", "-show_format", "-of", "json",
                                    str(partial)], timeout=timeout).stdout)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
    expected = timeline["duration_frames"] / FPS
    checks = {
        "dimensions": (video["width"], video["height"]) == (1920, 1080),
        "codec": video["codec_name"] == "h264" and video["r_frame_rate"] == "30/1",
        "frames": int(video.get("nb_read_packets", 0)) == timeline["duration_frames"],
        "video_duration": abs(float(video.get("duration", probe["format"]["duration"])) - expected) <= 0.05,
        "audio_present": audio is not None,
        "audio_duration": audio is not None and abs(float(audio["duration"]) - expected) <= 0.1,
    }
    run_command(["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(partial), "-f", "null", "-"], timeout=timeout)
    final_loudness = loudness(partial)
    checks["true_peak"] = float(final_loudness["input_tp"]) <= -1.0
    checks["loudness"] = abs(float(final_loudness["input_i"]) - TARGET_LUFS) <= 1.5
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"Render QA failed: {', '.join(failed)}")
    return {"checks": checks, "frames": timeline["duration_frames"], "duration_seconds": round(expected, 3),
            "integrated_lufs": float(final_loudness["input_i"]), "true_peak_dbtp": float(final_loudness["input_tp"])}


def node_timeout(profile, duration_frames):
    """Whole-render limit: the profile value, or six times the video length plus ten minutes if longer."""
    return max(profile["timeout_seconds"], int(duration_frames / FPS * 6) + 600)


def check(run_id):
    """Validate timeline.json (and its audio) without rendering. Does not need production_render."""
    config = production.require_production_scope()
    run = production.production_run_path(run_id)
    entries = review.read_entries(run)
    timeline = read_json(safe_path(run, "timeline.json", True))
    used = sorted({c.get("source") for c in timeline.get("audio", []) if c.get("kind") in {"bgm", "sfx"}})
    library = {a["id"]: a for a in audio_library.load_library()["assets"]}
    platforms = config.get("audio_platforms", ["youtube"])
    problems = [f"{asset_id}: {'not registered' if asset_id not in library else audio_library.eligibility(library[asset_id], platforms)[1]}"
                for asset_id in used if asset_id not in library or not audio_library.eligibility(library[asset_id], platforms)[0]]
    if problems:
        raise ValueError("Audio not usable: " + "; ".join(problems))
    duration = production.validate_timeline_v2(timeline, assemble.source_map(entries, [library[i] for i in used]))
    return {"status": "PASS", "run_id": run_id, "duration_seconds": round(duration / FPS, 2),
            "captions": production.caption_style_share(timeline), "clips": len(timeline["clips"])}


def render(run_id):
    config = production.require_production_scope()
    if not config["production_render"]:
        raise ValueError("Production rendering is off; set production_render: true only when the user asks for a render")
    run = production.production_run_path(run_id)
    profile = config["production_profile"]
    timeout = profile["timeout_seconds"]
    with run_lock(run):
        state = ingest.status(run_id)
        allowed = {("assembled", "pending"), ("render", "failed"), ("render", "paused"), ("rendered", "succeeded")}
        if (state.get("stage"), state.get("status")) not in allowed:
            raise ValueError(f"Render needs an assembled run, got {state.get('stage')}/{state.get('status')}")
        entries = review.read_entries(run)
        timeline = read_json(safe_path(run, "timeline.json", True))
        staged = review.stage_audio(run, sorted({c["source"] for c in timeline["audio"] if c["kind"] != "original"}),
                                    config.get("audio_platforms", ["youtube"]))
        library = [a for a in audio_library.load_library()["assets"] if a["id"] in staged]
        production.validate_timeline_v2(timeline, assemble.source_map(entries, library))
        props = render_props(run, timeline, entries, staged)
        props_sha = hashlib.sha256(json.dumps(props, sort_keys=True).encode()).hexdigest()
        if state.get("stage") == "rendered" and state.get("props_sha256") == props_sha:
            return state
        version, folder, resumed = pick_version(run, props_sha)
        if not resumed:
            write_json(folder / "props.json", props)
            write_json(folder / "render-plan.json", {"props_sha256": props_sha, "concurrency": profile["concurrency"],
                                                     "chunks": chunk_plan(timeline["duration_frames"],
                                                                          profile.get("chunk_seconds", DEFAULT_CHUNK_SECONDS))})
        previous = {k: v for k, v in state.items() if k not in {"error", "outputs"}}
        state = {**previous, "stage": "render", "status": "running", "render_version": version, "props_sha256": props_sha,
                 "next_action": "wait for rendering; completed chunks are reused if interrupted"}
        write_json(run / "state.json", state, replace=True)
        started = time.monotonic()
        try:
            rendered = run_command(["node", str(common.ROOT / "renderer/scripts/render-prod.mjs"), run_id, str(version), str(run)],
                                   timeout=node_timeout(profile, timeline["duration_frames"]))
            partial, measured_mix = finish(folder, timeline, timeout)
            report = qa(partial, timeline, timeout)
            production.require_production_scope()
            final = folder / "final.mp4"
            os.link(partial, final)
            partial.unlink()
            used = sorted(staged)
            credits = ["# 크레딧", "", "## 음원"] + ([f"- {line}" for line in audio_library.credits(used)] if used else ["- 없음"])
            fonts = read_json(common.ROOT / "config/fonts-lock.json")["fonts"]
            credits += ["", "## 자막 폰트 (SIL Open Font License 1.1)"] + [f"- {f['family']}" for f in fonts]
            (folder / "credits.md").write_text("\n".join(credits) + "\n", encoding="utf-8")
            write_json(folder / "verify.json", {**report, "mix_before_normalize": {k: measured_mix[k] for k in ["input_i", "input_tp"]},
                                                "chunks": len(read_json(folder / "chunks.json")["chunks"]), "resumed": resumed,
                                                "elapsed_seconds": round(time.monotonic() - started, 1),
                                                "human_review": "NOT_RUN", "platform_check": "not_checked",
                                                "renderer_log": rendered.stdout[-1500:]})
            state.update(stage="rendered", status="succeeded",
                         outputs={name: digest(folder / name) for name in ["final.mp4", "verify.json", "credits.md"]},
                         next_action=f"watch render/v{version}/final.mp4; edit timeline.json and render again for changes")
            write_json(run / "state.json", state, replace=True)
            return {**state, "final": str(final), "qa": report}
        except BaseException as exc:
            state.update(status="paused" if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else "failed",
                         error=str(exc)[:2000] or type(exc).__name__,
                         next_action=f"inspect render/v{version}; run render_prod.py again to resume finished chunks")
            write_json(run / "state.json", state, replace=True)
            raise


def main():
    def interrupted(signum, _frame):
        raise InterruptedError(f"Stopped by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true", help="validate timeline.json without rendering")
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.run_id) if args.check else render(args.run_id), indent=2, ensure_ascii=False))
    except KeyboardInterrupt:
        parser.exit(130, "PAUSED: interrupted; finished chunks are kept for resume\n")
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
