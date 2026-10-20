"""Small setup-only contracts. These guards are not an OS security boundary."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OWNER = "vlog-me.synthetic.v1"
PLATFORMS = {"youtube", "instagram", "tiktok"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_path(root, relative, exists=False):
    root = Path(root).absolute()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Expected a non-empty relative path without traversal")
    candidate = root / relative
    for parent in [candidate, *candidate.parents]:
        if parent.is_symlink():
            raise ValueError(f"Symlink path rejected: {parent.name}")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escaped allowed root")
    if exists and not candidate.is_file():
        raise ValueError(f"Missing regular file: {relative}")
    if candidate.is_file() and candidate.stat().st_nlink != 1:
        raise ValueError("Hard-linked file rejected")
    return candidate


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path, data, replace=False):
    path = Path(path)
    safe_path(path.parent, path.name)
    encoded = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if not replace:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        return
    if not path.is_file():
        raise ValueError("Replacement requires an existing owned file")
    fd, temporary = tempfile.mkstemp(prefix=".update-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run_command(command, timeout=120, binary=False):
    """Run a command in its own process group. `binary=True` returns stdout as bytes (e.g. raw audio)."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=not binary, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException as exc:
        # Terminate only this command's process group, including its browser children.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        if isinstance(exc, subprocess.TimeoutExpired):
            raise RuntimeError(f"{Path(command[0]).name} exceeded {timeout}s; owned process group stopped") from exc
        raise
    if binary:
        stderr = stderr.decode("utf-8", "replace")
    if process.returncode:
        diagnostic = stderr if len(stderr) < 2200 else stderr[:1600] + "\n...\n" + stderr[-500:]
        raise RuntimeError(f"{Path(command[0]).name} exited {process.returncode}: {diagnostic}")
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def require_run(run_id):
    run = run_path(run_id)
    marker = read_json(safe_path(run, "fixture-manifest.json", exists=True))
    if marker.get("owner") != OWNER:
        raise ValueError("Unrecognized synthetic run owner")
    return run, marker


def run_path(run_id):
    if not re.fullmatch(r"synthetic-[a-z0-9][a-z0-9-]{0,70}", run_id):
        raise ValueError("Only synthetic-* runs are implemented; real media processing is disabled")
    return safe_path(ROOT, f"work/{run_id}")


def validate_setup_config(config):
    expected = {"agent_runtime": "claude-code", "phase": "setup_synthetic_only",
                "source_roots": [], "runtime_policy": "content_driven", "target_duration_seconds": None}
    if any(key not in config or config[key] != value for key, value in expected.items()):
        raise ValueError("Current operation requires Claude-only synthetic setup scope")
    if any(config.get(key) is not False for key in
           ["external_processing", "audio_downloads", "production_render", "upload", "use_subagents"]):
        raise ValueError("Setup cannot enable external processing, downloads, production or agents")
    profile = config.get("synthetic_profile", {})
    if any(profile.get(k) != v for k, v in {"width":1280, "height":720, "fps":30, "color":"SDR BT.709"}.items()):
        raise ValueError("Unsupported synthetic output profile")
    for key, maximum in [("concurrency", 2), ("timeout_seconds", 180)]:
        value = profile.get(key)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"Synthetic {key} must be 1..{maximum}")
    return config


def require_setup_scope():
    return validate_setup_config(read_json(safe_path(ROOT, "config/project.json", True)))


def read_state(run_id):
    run = run_path(run_id)
    state = read_json(safe_path(run, "state.json", True))
    if state.get("owner") != OWNER or state.get("run_id") != run_id:
        raise ValueError("State owner/run ID mismatch; preserve and inspect")
    states = {"fixture_generation": {"running", "failed", "paused"}, "prepared": {"pending"},
              "render": {"running", "failed", "paused"}, "synthetic_encoded_output": {"succeeded", "failed", "paused"}}
    if state.get("status") not in states.get(state.get("stage"), set()):
        raise ValueError("Invalid persisted state; preserve and inspect")
    return state


@contextmanager
def run_lock(run):
    lock = safe_path(run, ".lock")
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def check_assets(run, manifest):
    if set(manifest.get("assets", {})) != {"video", "photo", "bgm", "sfx"}:
        raise ValueError("Unexpected synthetic asset set")
    expected_files = {asset['file'] for asset in manifest['assets'].values()}
    if {p.name for p in (run / 'assets').iterdir()} != expected_files:
        raise ValueError("Unregistered files in synthetic asset directory")
    for asset in manifest["assets"].values():
        path = safe_path(run / "assets", asset["file"], exists=True)
        if digest(path) != asset["sha256"]:
            raise ValueError("Synthetic asset hash mismatch")


def audio_eligibility(asset):
    """Production policy predicate only; no library search/download is implemented."""
    if asset.get("free") is not True:
        return False, "not_free"
    if set(asset.get("allowed_platforms", [])) != PLATFORMS:
        return False, "platform_rights_incomplete"
    if asset.get("license_status") != "verified" or not asset.get("license_evidence"):
        return False, "license_pending"
    if asset.get("claim_status") != "documented_low_risk" or not asset.get("claim_evidence"):
        return False, "claim_pending"
    if asset.get("known_claim") or asset.get("requires_whitelist"):
        return False, "known_claim_requirement"
    if asset.get("attribution_satisfied") is not True:
        return False, "attribution_pending"
    return True, "eligible_for_local_render_not_platform_certified"


def validate_timeline(timeline, manifest):
    if timeline.get("schema_version") != 1 or timeline.get("purpose") != "synthetic_setup":
        raise ValueError("Only synthetic_setup timeline v1 is implemented")
    fps = timeline.get("fps")
    if fps != 30 or (timeline.get("width"), timeline.get("height")) != (1280, 720):
        raise ValueError("Setup renderer supports 1280x720 CFR 30 only")
    assets = manifest["assets"]
    clips = timeline.get("clips", [])
    if not clips:
        raise ValueError("Empty timeline")
    cursor = 0
    ids = set()
    for cue in clips + timeline.get("audio", []) + timeline.get("captions", []):
        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not cue_id or cue_id in ids:
            raise ValueError("Duplicate or missing cue ID")
        ids.add(cue_id)
        start, duration = cue.get("from"), cue.get("duration")
        if type(start) is not int or type(duration) is not int or start < 0 or duration <= 0:
            raise ValueError("Invalid frame interval")
    for clip in clips:
        if clip["from"] != cursor or clip.get("asset") not in {"video", "photo"}:
            raise ValueError("Clips must be contiguous supported assets")
        cursor += clip["duration"]
        trim = clip.get("trim", 0)
        if type(trim) is not int or trim < 0:
            raise ValueError("Invalid source trim")
        if clip["asset"] == "video" and trim + clip["duration"] > assets["video"]["frames"]:
            raise ValueError("Source trim exceeds video")
    if timeline.get("duration_frames") != cursor:
        raise ValueError("Duration must equal selected content, not a fixed target")
    for cue in timeline.get("audio", []):
        if cue.get("asset") not in {"video", "bgm", "sfx"}:
            raise ValueError("Unknown audio asset")
        if cue["from"] + cue["duration"] > cursor:
            raise ValueError("Audio exceeds timeline")
        trim = cue.get("trim", 0)
        if type(trim) is not int or trim < 0 or trim + cue["duration"] > assets[cue["asset"]]["frames"]:
            raise ValueError("Audio source bounds exceeded; looping is not enabled")
        if cue["asset"] == "video":
            matching = [c for c in clips if c["asset"] == "video" and c["from"] == cue["from"] and c["duration"] == cue["duration"] and c.get("trim", 0) == trim]
            if not matching or cue.get("audio_track") != 1:
                raise ValueError("Original audio must use the generated stream and video mapping")
        points = cue.get("gain_db", [])
        if len(points) < 2 or points[0][0] != 0 or points[-1][0] != cue["duration"] - 1:
            raise ValueError("Gain envelope must cover cue endpoints")
        previous = -1
        for frame, db in points:
            if type(frame) is not int or frame <= previous or frame >= cue["duration"]:
                raise ValueError("Invalid gain envelope frame")
            if not isinstance(db, (int, float)) or not math.isfinite(db) or not -80 <= db <= 0:
                raise ValueError("Invalid gain level")
            previous = frame
    originals = [c for c in timeline.get("audio", []) if c["asset"] == "video"]
    video_mappings = [(c["from"], c["duration"], c.get("trim", 0)) for c in clips if c["asset"] == "video"]
    audio_mappings = [(c["from"], c["duration"], c.get("trim", 0)) for c in originals]
    if sorted(audio_mappings) != sorted(video_mappings):
        raise ValueError("Missing or duplicate original audio cue")
    for caption in timeline.get("captions", []):
        if caption["from"] + caption["duration"] > cursor or caption.get("kind") != "editorial":
            raise ValueError("Invalid synthetic caption")
        if not isinstance(caption.get("text"), str) or not caption["text"].strip():
            raise ValueError("Empty caption")
    return cursor


def input_fingerprint(run):
    paths = [run / name for name in ["fixture-manifest.json", "brief.json", "timeline.json"]]
    # Per-run defaults are frozen in brief.json. Unused library entries and new-run
    # defaults do not change a synthetic render; current scope is checked separately.
    paths += [ROOT / "renderer/package-lock.json", ROOT / "renderer/package.json", ROOT / ".tools/browser.json"]
    paths += sorted((ROOT / "renderer/src").glob("*"))
    paths += sorted((ROOT / "renderer/scripts").glob("*.mjs"))
    paths += sorted((ROOT / "scripts").glob("*.py"))
    return hashlib.sha256(json.dumps([(str(p.relative_to(ROOT)), digest(safe_path(ROOT, p.relative_to(ROOT), True))) for p in paths if p.is_file()]).encode()).hexdigest()


def validate_run(run_id):
    run, manifest = require_run(run_id)
    check_assets(run, manifest)
    timeline = read_json(safe_path(run, "timeline.json", exists=True))
    validate_timeline(timeline, manifest)
    brief = read_json(safe_path(run, "brief.json", exists=True))
    if brief.get("source_roots") != [] or brief.get("purpose") != "synthetic_setup":
        raise ValueError("Real source access is disabled")
    validate_setup_config(brief.get("resolved_config", {}))
    return run, manifest, timeline
