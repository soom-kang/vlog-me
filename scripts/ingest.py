#!/usr/bin/env python3
"""Ingest one allowed source folder into a fresh prod-* run. Originals are read, never written.

Videos become CFR 30fps 1920x1080 SDR H.264 proxies (HDR goes through macOS avconvert first).
Photos (HEIC/JPEG/PNG) become JPEG copies via sips. Results are listed in sources.json.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import uuid

from common import digest, read_json, run_command, run_lock, safe_path, write_json
import production

OWNER = "vlog-me.production.v1"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
PHOTO_EXTENSIONS = {".heic", ".heif", ".jpg", ".jpeg", ".png"}
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
PROXY_FILTER = ("fps=30,scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p,"
                "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")


def _rate(text):
    try:
        numerator, denominator = (float(x) for x in str(text).split("/"))
        return numerator / denominator if denominator else 0.0
    except ValueError:
        return 0.0


def normalize_time(text):
    """Return a UTC ISO timestamp. Times without an offset (sips) are read in the machine's timezone."""
    if not text:
        return None
    value = str(text).strip().replace("Z", "+00:00")
    value = re.sub(r"^(\d{4}):(\d{2}):(\d{2}) ", r"\1-\2-\3T", value)
    value = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def describe_video(probe):
    """Summarize ffprobe JSON into the facts the edit needs."""
    video = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("No video stream")
    audio = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    rotation = 0
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = int(side["rotation"])
    rotation = int(video.get("tags", {}).get("rotate", rotation)) % 360
    nominal, average = _rate(video.get("r_frame_rate")), _rate(video.get("avg_frame_rate"))
    tags = probe.get("format", {}).get("tags", {}) | video.get("tags", {})
    width, height = int(video["width"]), int(video["height"])
    if rotation in {90, 270}:
        width, height = height, width
    return {
        "duration_seconds": round(float(probe["format"]["duration"]), 3),
        "codec": video.get("codec_name"),
        "display_size": [width, height],
        "rotation": rotation,
        "fps_nominal": round(nominal, 3),
        "fps_average": round(average, 3),
        "vfr": bool(nominal and average and abs(nominal - average) / nominal > 0.01),
        "hdr": video.get("color_transfer") in HDR_TRANSFERS,
        "color_transfer": video.get("color_transfer"),
        "has_audio": bool(audio),
        "captured_at": normalize_time(tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")),
    }


def describe_photo(sips_output):
    values = dict(re.findall(r"^\s+(\w+): (.+)$", sips_output, re.M))
    return {"display_size": [int(values.get("pixelWidth", 0)), int(values.get("pixelHeight", 0))],
            "format": values.get("format"), "captured_at": normalize_time(values.get("creation"))}


def probe(path):
    return json.loads(run_command(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)


def make_proxy(source, facts, run, entry_id, timeout):
    """Write proxy/<id>.mp4 through a partial file; never replace an existing proxy."""
    work = run / "tmp"
    work.mkdir(exist_ok=True)
    input_path = source
    if facts["hdr"]:
        # zscale is unavailable; AVFoundation converts HDR to SDR for an H.264 preset.
        input_path = work / f"{entry_id}.sdr.mov"
        run_command(["avconvert", "--source", str(source), "--output", str(input_path),
                     "--preset", "Preset1920x1080"], timeout=timeout)
    partial = safe_path(run / "proxy", f"{entry_id}.partial.mp4")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-i", str(input_path),
               "-map", "0:v:0", "-vf", PROXY_FILTER, "-c:v", "h264_videotoolbox", "-b:v", "12M",
               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
    command += ["-map", "0:a:0", "-c:a", "aac", "-ar", "48000", "-ac", "2"] if facts["has_audio"] else ["-an"]
    run_command(command + ["-movflags", "+faststart", str(partial)], timeout=timeout)
    result = probe(partial)
    video = next(s for s in result["streams"] if s["codec_type"] == "video")
    if (video["width"], video["height"], video["codec_name"]) != (1920, 1080, "h264") or _rate(video["r_frame_rate"]) != 30:
        raise ValueError(f"Proxy for {entry_id} is not 1920x1080 CFR 30 H.264")
    if abs(float(result["format"]["duration"]) - facts["duration_seconds"]) > 0.25:
        raise ValueError(f"Proxy duration for {entry_id} differs from the original")
    final = safe_path(run / "proxy", f"{entry_id}.mp4")
    os.link(partial, final)
    partial.unlink()
    if input_path != source:
        input_path.unlink()
    return final, int(round(float(result["format"]["duration"]) * 30))


def make_photo(source, run, entry_id, timeout):
    final = safe_path(run / "photos", f"{entry_id}.jpg")
    run_command(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "90", str(source), "--out", str(final)], timeout=timeout)
    return final


def scan(config, root):
    base = safe_path(production.ROOT, root)
    if root not in config["source_roots"] or not base.is_dir():
        raise ValueError("Source root folder does not exist")
    found, skipped = [], []
    for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.name.startswith(".")):
        relative = str(path.relative_to(production.ROOT))
        suffix = path.suffix.lower()
        kind = "video" if suffix in VIDEO_EXTENSIONS else "photo" if suffix in PHOTO_EXTENSIONS else None
        if kind is None:
            skipped.append({"original": relative, "reason": "unsupported type"})
            continue
        try:
            production.source_path(config, relative)
        except ValueError as exc:
            skipped.append({"original": relative, "reason": str(exc)})
            continue
        found.append((kind, path, relative))
    return found, skipped


def ingest(root):
    config = production.require_production_scope()
    if root not in config["source_roots"]:
        raise ValueError("Ingest only folders listed in source_roots")
    run_id = "prod-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    run = production.production_run_path(run_id)
    run.parent.mkdir(exist_ok=True)
    run.mkdir()
    timeout = config["production_profile"]["timeout_seconds"]
    with run_lock(run):
        state = {"owner": OWNER, "run_id": run_id, "stage": "ingest", "status": "running", "source_root": root,
                 "next_action": "wait for ingest; do not reuse partial proxies"}
        write_json(run / "state.json", state)
        print(json.dumps({"allocated_run": run_id}), flush=True)
        try:
            write_json(run / "brief.json", {"purpose": "production", "source_roots": [root], "resolved_config": config})
            (run / "proxy").mkdir()
            (run / "photos").mkdir()
            found, skipped = scan(config, root)
            entries, counters = [], {"video": 0, "photo": 0}
            for kind, path, relative in found:
                counters[kind] += 1
                entry_id = f"{kind[0]}{counters[kind]:03d}"
                before = path.stat()
                entry = {"id": entry_id, "kind": kind, "original": relative, "bytes": before.st_size,
                         "sha256": digest(path)}
                try:
                    if kind == "video":
                        facts = describe_video(probe(path))
                        proxy, frames = make_proxy(path, facts, run, entry_id, timeout)
                        entry |= facts | {"proxy": str(proxy.relative_to(run)), "frames": frames,
                                          "proxy_sha256": digest(proxy), "color_review": "needed" if facts["hdr"] else "not_needed"}
                    else:
                        photo = make_photo(path, run, entry_id, timeout)
                        entry |= describe_photo(run_command(["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "format",
                                                             "-g", "creation", str(path)]).stdout)
                        entry |= {"proxy": str(photo.relative_to(run)), "proxy_sha256": digest(photo)}
                except (RuntimeError, ValueError, KeyError, StopIteration) as exc:
                    skipped.append({"original": relative, "reason": str(exc)[:500]})
                    continue
                after = path.stat()
                if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
                    raise ValueError(f"Original changed during ingest: {relative}")
                entries.append(entry)
            entries.sort(key=lambda e: (e.get("captured_at") or "", e["original"]))
            if not entries:
                raise ValueError("No usable videos or photos in the source folder")
            shutil.rmtree(run / "tmp", ignore_errors=True)
            production.require_production_scope()
            write_json(run / "sources.json", {"owner": OWNER, "run_id": run_id, "source_root": root,
                                              "entries": entries, "skipped": skipped})
            state.update(stage="ingested", status="pending", sources_sha256=digest(run / "sources.json"),
                         counts={"video": sum(e["kind"] == "video" for e in entries),
                                 "photo": sum(e["kind"] == "photo" for e in entries), "skipped": len(skipped)},
                         next_action="analyze (unit 3); review color_review=needed HDR proxies by eye")
            write_json(run / "state.json", state, replace=True)
            return state
        except BaseException as exc:
            state.update(status="paused" if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else "failed",
                         error=str(exc)[:2000] or type(exc).__name__,
                         next_action="inspect retained proxies; start a fresh prod run")
            write_json(run / "state.json", state, replace=True)
            raise


def status(run_id):
    run = production.production_run_path(run_id)
    state = read_json(safe_path(run, "state.json", True))
    if state.get("owner") != OWNER or state.get("run_id") != run_id:
        raise ValueError("State owner/run ID mismatch; preserve and inspect")
    if state.get("stage") == "ingested" and digest(safe_path(run, "sources.json", True)) != state.get("sources_sha256"):
        return {**state, "recorded_status": state["status"], "status": "stale", "reason": "sources.json changed"}
    return state


def main():
    def interrupted(signum, _frame):
        raise InterruptedError(f"Stopped by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("run").add_argument("--source-root", required=True)
    sub.add_parser("status").add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = ingest(args.source_root) if args.action == "run" else status(args.run_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except KeyboardInterrupt:
        parser.exit(130, "PAUSED: interrupted; inspect retained run state\n")
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
