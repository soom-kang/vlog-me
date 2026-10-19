"""Production scope and timeline v2 contracts. These guards are not an OS security boundary.

Synthetic setup keeps its own strict contract in common.py. The two phases are exclusive:
`phase: production` blocks synthetic create/render, and the setup phase blocks everything here.
"""
import json
import math
from pathlib import Path
import re

from common import ROOT, read_json, safe_path

PRODUCTION_PHASE = "production"
RUN_PATTERN = r"prod-[a-z0-9][a-z0-9-]{0,70}"
SOURCE_PARENT = "sources"
PROFILE_LIMITS = {"concurrency": 8, "timeout_seconds": 14400}
CLIP_TAGS = {"fun", "mood"}
TRANSITIONS = {"cut", "fade", "whip"}
# Shared with the renderer so Python validation and Remotion presets cannot drift apart.
CAPTION_REGISTRY = json.loads((Path(__file__).resolve().parents[1] / "renderer/src/production/presets.json").read_text(encoding="utf-8"))
CAPTION_KINDS = set(CAPTION_REGISTRY["kinds"])
VARIETY_CAPTIONS = {k for k, v in CAPTION_REGISTRY["kinds"].items() if v["group"] == "variety"}
MOOD_CAPTIONS = {k for k, v in CAPTION_REGISTRY["kinds"].items() if v["group"] == "mood"}
CAPTION_POSITIONS = {"bottom", "top", "center", "upper_left", "upper_right", "lower_left", "lower_right"}
AUDIO_KINDS = {"original", "bgm", "sfx"}


def _is_flag(value):
    return type(value) is bool


def validate_production_config(config):
    expected = {"agent_runtime": "claude-code", "phase": PRODUCTION_PHASE, "runtime_policy": "content_driven",
                "target_duration_seconds": None, "use_subagents": False, "external_processing": False,
                "upload": False}
    if any(key not in config or config[key] != value for key, value in expected.items()):
        raise ValueError("Current operation requires Claude-only production scope without uploads or external processing")
    for key in ["asr_local", "audio_search", "audio_downloads", "production_render"]:
        if not _is_flag(config.get(key)):
            raise ValueError(f"Production flag {key} must be true or false")
    model = config.get("asr_model")
    if model is not None and (not config["asr_local"] or not isinstance(model, str)
                              or not re.fullmatch(r"ggml-[A-Za-z0-9._-]+\.bin", model)):
        raise ValueError("asr_model must be a local ggml-*.bin file name and requires asr_local")
    roots = config.get("source_roots")
    if not isinstance(roots, list) or not roots or len(set(roots)) != len(roots):
        raise ValueError("Production requires at least one unique source root")
    for root in roots:
        parts = Path(root).parts if isinstance(root, str) else ()
        if len(parts) < 2 or parts[0] != SOURCE_PARENT:
            raise ValueError("Source roots must be folders under sources/")
        if not safe_path(ROOT, root).is_dir():
            raise ValueError("Source root folder does not exist")
    profile = config.get("production_profile", {})
    if any(profile.get(k) != v for k, v in {"width": 1920, "height": 1080, "fps": 30, "color": "SDR BT.709"}.items()):
        raise ValueError("Unsupported production output profile")
    chunk = profile.get("chunk_seconds", 300)
    if type(chunk) is not int or not 30 <= chunk <= 900:
        raise ValueError("Production chunk_seconds must be 30..900")
    for key, maximum in PROFILE_LIMITS.items():
        value = profile.get(key)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"Production {key} must be 1..{maximum}")
    return config


def require_production_scope():
    return validate_production_config(read_json(safe_path(ROOT, "config/project.json", True)))


def production_run_path(run_id):
    if not isinstance(run_id, str) or not re.fullmatch(RUN_PATTERN, run_id):
        raise ValueError("Production run IDs must match prod-*")
    return safe_path(ROOT, f"work/{run_id}")


def source_path(config, relative, exists=True):
    """Resolve an original inside an allowed source root. Originals are read-only inputs."""
    for root in config["source_roots"]:
        base = safe_path(ROOT, root)
        try:
            inner = Path(relative).relative_to(root)
        except ValueError:
            continue
        if not inner.parts:
            break
        return safe_path(base, inner, exists=exists)
    raise ValueError("Path is outside the allowed source roots")


def validate_caption_text(caption, require_preset=True):
    """Kind, preset and line length checks shared by timeline v2 and candidate cards. Returns the preset."""
    spec = CAPTION_REGISTRY["kinds"].get(caption.get("kind"))
    if spec is None:
        raise ValueError("Unknown caption kind")
    preset = caption.get("preset")
    if preset is None and not require_preset:
        preset = spec["presets"][0]
    if preset not in spec["presets"]:
        raise ValueError(f"Caption preset must be one of {spec['presets']} for {caption['kind']}")
    text = caption.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Empty caption")
    lines = text.split("\n")
    if len(lines) > CAPTION_REGISTRY["max_lines"] or any(len(line) > spec["max_chars"] for line in lines):
        raise ValueError(f"{caption['kind']} captions allow {CAPTION_REGISTRY['max_lines']} lines of {spec['max_chars']} characters")
    if caption.get("position", "bottom") not in CAPTION_POSITIONS:
        raise ValueError("Unknown caption position")
    return preset


def _interval(cue, limit=None):
    start, duration = cue.get("from"), cue.get("duration")
    if type(start) is not int or type(duration) is not int or start < 0 or duration <= 0:
        raise ValueError("Invalid frame interval")
    if limit is not None and start + duration > limit:
        raise ValueError(f"Cue {cue.get('id')} exceeds timeline")


def _gain(points, duration):
    if not isinstance(points, list) or len(points) < 2 or points[0][0] != 0 or points[-1][0] != duration - 1:
        raise ValueError("Gain envelope must cover cue endpoints")
    previous = -1
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("Gain points are [frame, dB]")
        frame, db = point
        if type(frame) is not int or frame <= previous or frame >= duration:
            raise ValueError("Invalid gain envelope frame")
        if isinstance(db, bool) or not isinstance(db, (int, float)) or not math.isfinite(db) or not -80 <= db <= 0:
            raise ValueError("Invalid gain level")
        previous = frame


def validate_timeline_v2(timeline, sources):
    """Validate a production edit. `sources` maps id -> {kind, frames?, has_audio?}."""
    if timeline.get("schema_version") != 2 or timeline.get("purpose") != "production":
        raise ValueError("Only production timeline v2 is accepted here")
    if timeline.get("fps") != 30 or (timeline.get("width"), timeline.get("height")) != (1920, 1080):
        raise ValueError("Production renderer supports 1920x1080 CFR 30 only")
    clips, audio, captions = timeline.get("clips", []), timeline.get("audio", []), timeline.get("captions", [])
    if not clips:
        raise ValueError("Empty timeline")
    ids = set()
    for cue in clips + audio + captions:
        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not cue_id or cue_id in ids:
            raise ValueError("Duplicate or missing cue ID")
        ids.add(cue_id)
        _interval(cue)

    cursor = 0
    clip_by_id = {}
    for clip in clips:
        source = sources.get(clip.get("source"))
        if clip["from"] != cursor or not source or source.get("kind") not in {"video", "image"}:
            raise ValueError("Clips must be contiguous video or image sources")
        if clip.get("tag") not in CLIP_TAGS:
            raise ValueError("Each clip needs a fun or mood tag")
        if clip.get("transition", "cut") not in TRANSITIONS:
            raise ValueError("Unknown transition")
        zoom = clip.get("zoom", 1)
        if isinstance(zoom, bool) or not isinstance(zoom, (int, float)) or not 1 <= zoom <= 3:
            raise ValueError("Zoom must be 1..3")
        if source["kind"] == "video":
            start, speed = clip.get("in", 0), clip.get("speed", 1)
            if type(start) is not int or start < 0:
                raise ValueError("Invalid source in-point")
            if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 0.25 <= speed <= 4:
                raise ValueError("Speed must be 0.25..4")
            if start + math.ceil(clip["duration"] * speed) > source["frames"]:
                raise ValueError("Clip exceeds source video")
        elif "in" in clip or "speed" in clip:
            raise ValueError("Image clips have no in-point or speed")
        clip_by_id[clip["id"]] = clip
        cursor += clip["duration"]
    if timeline.get("duration_frames") != cursor:
        raise ValueError("Duration must equal selected content, not a fixed target")

    originals = []
    for cue in audio:
        _interval(cue, cursor)
        kind = cue.get("kind")
        if kind not in AUDIO_KINDS:
            raise ValueError("Unknown audio kind")
        _gain(cue.get("gain_db"), cue["duration"])
        if kind == "original":
            clip = clip_by_id.get(cue.get("clip"))
            if not clip or sources[clip["source"]]["kind"] != "video":
                raise ValueError("Original audio must reference a video clip")
            if (cue["from"], cue["duration"]) != (clip["from"], clip["duration"]):
                raise ValueError("Original audio must align with its clip")
            originals.append(cue["clip"])
            continue
        source = sources.get(cue.get("source"))
        if not source or source.get("kind") != "audio":
            raise ValueError("BGM and SFX must use registered audio sources")
        start = cue.get("in", 0)
        if type(start) is not int or start < 0 or start + cue["duration"] > source["frames"]:
            raise ValueError("Audio source bounds exceeded; looping is not enabled")
    with_sound = sorted(c["id"] for c in clips if sources[c["source"]]["kind"] == "video"
                        and sources[c["source"]].get("has_audio", True))
    if sorted(originals) != with_sound:
        raise ValueError("Each video clip with sound needs exactly one original audio cue")

    for caption in captions:
        _interval(caption, cursor)
        validate_caption_text(caption)
    return cursor


def caption_style_share(timeline):
    """Report the variety/mood caption split. A guide for review, never an enforced quota."""
    counts = {"variety": 0, "mood": 0, "dialogue": 0}
    for caption in timeline.get("captions", []):
        kind = caption.get("kind")
        counts["variety" if kind in VARIETY_CAPTIONS else "mood" if kind in MOOD_CAPTIONS else "dialogue"] += 1
    styled = counts["variety"] + counts["mood"]
    share = round(counts["variety"] / styled, 2) if styled else None
    low, high = CAPTION_REGISTRY["share_window"]
    return {**counts, "variety_share": share, "target": CAPTION_REGISTRY["target_variety_share"],
            "in_window": share is not None and low <= share <= high}
