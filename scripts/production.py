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
TRANSITIONS = {"cut", "fade", "whip", "dissolve"}
# Shared with the renderer so Python validation and Remotion presets cannot drift apart.
CAPTION_REGISTRY = json.loads((Path(__file__).resolve().parents[1] / "renderer/src/production/presets.json").read_text(encoding="utf-8"))
NARRATION = CAPTION_REGISTRY["narration"]
LOOK = CAPTION_REGISTRY["look"]
MOTION = CAPTION_REGISTRY["motion"]
CAPTION_KINDS = set(CAPTION_REGISTRY["kinds"])
VARIETY_CAPTIONS = {k for k, v in CAPTION_REGISTRY["kinds"].items() if v["group"] == "variety"}
MOOD_CAPTIONS = {k for k, v in CAPTION_REGISTRY["kinds"].items() if v["group"] == "mood"}
CAPTION_POSITIONS = {"bottom", "top", "center", "upper_left", "upper_right", "lower_left", "lower_right"}
AUDIO_KINDS = {"original", "bgm", "sfx"}
OVERLAY_POSITIONS = {"left", "right"}
STACK_POSITIONS = {"left", "right", "center"}
STACK_PHOTOS = (2, 12)
EFFECT_TYPES = {"punch_zoom", "shake", "flash", "speedlines", "light_leak"}
OVERLAY_MAX_TILT = 10


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
    max_lines = spec.get("max_lines", CAPTION_REGISTRY["max_lines"])
    if len(lines) > max_lines or any(len(line) > spec["max_chars"] for line in lines):
        raise ValueError(f"{caption['kind']} captions allow {max_lines} lines of {spec['max_chars']} characters")
    if caption.get("position", "bottom") not in CAPTION_POSITIONS:
        raise ValueError("Unknown caption position")
    sub = caption.get("sub")
    if sub is not None and (not isinstance(sub, str) or not sub.strip() or len(sub) > CAPTION_REGISTRY["max_sub_chars"]):
        raise ValueError(f"Caption sub line must be 1..{CAPTION_REGISTRY['max_sub_chars']} characters")
    if caption.get("sync", "speech") not in {"speech", "manual"}:
        raise ValueError("Caption sync must be speech or manual")
    return preset


def narration_seconds(text):
    """Recommended reading time; only the absolute minimum is enforced."""
    reading = sum(NARRATION["read_base_seconds"] + NARRATION["read_per_char_seconds"] * len(re.sub(r"\s", "", line))
                  for line in text.split("\n"))
    return max(NARRATION["min_seconds"], reading + NARRATION["fade_frames"] / 30 + 1)


def narration_warnings(captions, fps=30):
    """Use fps=1 for candidate durations expressed in seconds."""
    warnings = []
    for caption in captions:
        if caption.get("kind") != "narration":
            continue
        seconds = caption["duration"] / fps
        recommended = narration_seconds(caption["text"])
        if seconds < recommended:
            warnings.append(f"'{caption['text'][:12]}…' 내레이션이 읽기에 짧습니다(현재 {seconds:.1f}초, 권장 {recommended:.1f}초)")
    return warnings


def preset_warnings(captions):
    """Variation advice: the same preset many times in a row, or one preset carrying a whole kind."""
    limit = CAPTION_REGISTRY["max_same_preset_in_a_row"]
    warnings, run, previous = [], 0, None
    ordered = sorted(captions, key=lambda c: c.get("from", c.get("at", 0)))
    for caption in ordered:
        preset = caption.get("preset") or CAPTION_REGISTRY["kinds"][caption["kind"]]["presets"][0]
        run = run + 1 if preset == previous else 1
        if run == limit + 1:
            warnings.append(f"'{preset}' 자막이 {limit + 1}번 이상 연달아 나옵니다. 같은 kind의 다른 preset을 섞어 보세요")
        previous = preset
    for kind, spec in CAPTION_REGISTRY["kinds"].items():
        used = [c.get("preset") or spec["presets"][0] for c in ordered if c["kind"] == kind]
        if len(used) >= 4 and len(set(used)) == 1 and len(spec["presets"]) > 1:
            warnings.append(f"{kind} 자막 {len(used)}개가 모두 '{used[0]}'입니다. 다른 preset: {', '.join(p for p in spec['presets'] if p != used[0])}")
    return warnings


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


def validate_look(look):
    """Validate the optional global look without adding defaults to saved timelines."""
    allowed = {"grade", "grade_strength", "grain", "vignette", "letterbox"}
    if not isinstance(look, dict) or set(look) - allowed:
        raise ValueError("Look must be an object with only grade, grade_strength, grain, vignette and letterbox")
    if "grade" in look and look["grade"] not in LOOK["grades"]:
        raise ValueError("Unknown look grade")
    for key in ["grade_strength", "grain", "vignette"]:
        if key in look:
            value = look[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= LOOK[f"max_{key}"]:
                raise ValueError(f"Look {key} must be a finite number in 0..{LOOK[f'max_{key}']}")
    if look.get("letterbox") is not None:
        value = look["letterbox"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value not in LOOK["letterbox"]:
            raise ValueError("Unknown letterbox aspect")
    return look


def validate_timeline_v2(timeline, sources):
    """Validate a production edit. `sources` maps id -> {kind, frames?, has_audio?}."""
    if timeline.get("schema_version") != 2 or timeline.get("purpose") != "production":
        raise ValueError("Only production timeline v2 is accepted here")
    if timeline.get("fps") != 30 or (timeline.get("width"), timeline.get("height")) != (1920, 1080):
        raise ValueError("Production renderer supports 1920x1080 CFR 30 only")
    if "look" in timeline:
        validate_look(timeline["look"])
    clips, audio, captions = timeline.get("clips", []), timeline.get("audio", []), timeline.get("captions", [])
    overlays = timeline.get("overlays", [])
    if not clips:
        raise ValueError("Empty timeline")
    if not isinstance(overlays, list):
        raise ValueError("Overlays must be a list")
    ids = set()
    effects = timeline.get("effects", [])
    if not isinstance(effects, list):
        raise ValueError("effects must be a list")
    for cue in clips + audio + captions + overlays + effects:
        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not cue_id or cue_id in ids:
            raise ValueError("Duplicate or missing cue ID")
        ids.add(cue_id)
        _interval(cue)

    cursor = 0
    clip_by_id = {}
    for index, clip in enumerate(clips):
        source = sources.get(clip.get("source"))
        if clip["from"] != cursor or not source or source.get("kind") not in {"video", "image"}:
            raise ValueError("Clips must be contiguous video or image sources")
        if clip.get("tag") not in CLIP_TAGS:
            raise ValueError("Each clip needs a fun or mood tag")
        if not isinstance(clip.get("deflicker", False), bool):
            raise ValueError("deflicker must be true or false")
        if clip.get("transition", "cut") not in TRANSITIONS:
            raise ValueError("Unknown transition")
        if "drift" in clip:
            if type(clip["drift"]) is not bool:
                raise ValueError("drift must be true or false")
            if source["kind"] != "video":
                raise ValueError("Photos already drift")
        if clip.get("transition") == "dissolve":
            d = MOTION["dissolve_frames"]
            if index == 0:
                raise ValueError("First clip cannot dissolve")
            previous = clips[index - 1]
            if min(previous["duration"], clip["duration"]) < d:
                raise ValueError("Dissolve needs both clips to last at least D frames")
            previous_source = sources[previous["source"]]
            if (previous_source["kind"] == "video" and previous.get("in", 0)
                    + math.ceil((previous["duration"] + d) * previous.get("speed", 1)) > previous_source["frames"]):
                raise ValueError("Dissolve needs D more source frames after the previous clip")
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
        if caption["kind"] == "narration" and caption["duration"] < round(NARRATION["min_seconds"] * 30):
            raise ValueError("Narration duration is below the minimum reading time")
    for overlay in overlays:
        # Photo inserts float over the running video; they never replace a clip.
        _interval(overlay, cursor)
        if overlay.get("style") == "stack":
            # A burst of photos dropping onto a pile, e.g. for "사진 엄청 찍음" moments.
            names = overlay.get("sources")
            if not isinstance(names, list) or not STACK_PHOTOS[0] <= len(names) <= STACK_PHOTOS[1]:
                raise ValueError(f"Photo stacks need {STACK_PHOTOS[0]}..{STACK_PHOTOS[1]} photos")
            if any(sources.get(n, {}).get("kind") != "image" for n in names):
                raise ValueError("Photo stacks must show photo sources")
            step = overlay.get("interval")
            if type(step) is not int or not 3 <= step <= 45:
                raise ValueError("Photo stack interval must be 3..45 frames")
            if overlay.get("position") not in STACK_POSITIONS:
                raise ValueError("Photo stack position must be left, right or center")
            continue
        source = sources.get(overlay.get("source"))
        if not source or source.get("kind") != "image":
            raise ValueError("Overlays must show a photo source")
        if overlay.get("position") not in OVERLAY_POSITIONS:
            raise ValueError("Overlay position must be left or right")
        tilt = overlay.get("tilt", 0)
        if isinstance(tilt, bool) or not isinstance(tilt, (int, float)) or abs(tilt) > OVERLAY_MAX_TILT:
            raise ValueError(f"Overlay tilt must be within ±{OVERLAY_MAX_TILT} degrees")
    for effect in effects:
        _interval(effect, cursor)
        if effect.get("type") not in EFFECT_TYPES:
            raise ValueError(f"Effect type must be one of {sorted(EFFECT_TYPES)}")
        if effect["type"] == "light_leak" and effect["duration"] < MOTION["light_leak_min_frames"]:
            raise ValueError("Light leak is shorter than the minimum duration")
        strength = effect.get("strength", 1)
        if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not 0.5 <= strength <= 2:
            raise ValueError("Effect strength must be 0.5..2")
    return cursor


def caption_style_share(timeline):
    """Report the mood/variety caption split. A guide for review, never an enforced quota."""
    counts = {"mood": 0, "variety": 0, "dialogue": 0}
    for caption in timeline.get("captions", []):
        kind = caption.get("kind")
        counts["mood" if kind in MOOD_CAPTIONS else "variety" if kind in VARIETY_CAPTIONS else "dialogue"] += 1
    styled = counts["mood"] + counts["variety"]
    mood = round(counts["mood"] / styled, 2) if styled else None
    low, high = CAPTION_REGISTRY["share_window"]
    return {**counts, "mood_share": mood, "variety_share": None if mood is None else round(1 - mood, 2),
            "target": CAPTION_REGISTRY["target_mood_share"], "in_window": mood is not None and low <= mood <= high}
