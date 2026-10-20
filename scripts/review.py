#!/usr/bin/env python3
"""Turn Claude's candidates.json into review cards with expected frames, then record the user's selection.

`build` renders, per candidate: four source frames, an expected still with captions composited
(Remotion renderStill) and, when requested, a 960x540 preview clip. Output goes to a new
review/vN/ folder with a static index.html (no scripts) that opens straight from disk.
`select` validates selection.json written from the user's chat answer and records it.
"""
import argparse
import copy
import html
import json
import math
from pathlib import Path
import re
import shutil
import signal

import audio_library
import caption_sync
import common
from common import digest, read_json, run_command, run_lock, safe_path, write_json
import ingest
import production
import sound

FPS = 30
CANDIDATE_ID = r"c\d{2,3}"
DECISIONS = {"adopt", "caption_edit", "drop"}
MIN_CUT = 0.3
PHOTO_SECONDS = (1.0, 10.0)
INSERT_MIN = 0.5
KIND_LABELS = {"variety": "예능", "situation": "상황", "sfx_text": "효과 글자", "inner_voice": "속마음",
               "dialogue": "대사", "mood": "감성", "place": "장소"}


def _number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be {low}..{high}")
    return float(value)


def edited_seconds(candidate, entry):
    plan = candidate["plan"]
    if entry["kind"] == "photo":
        return float(plan.get("photo_seconds", 3.0))
    return sum(end - start for start, end in plan["cuts"]) / plan.get("speed", 1)


def edited_to_source(candidate, t):
    """Map a time in the edited candidate to the source proxy time."""
    plan = candidate["plan"]
    speed = plan.get("speed", 1)
    remaining = t * speed
    for start, end in plan["cuts"]:
        if remaining <= end - start:
            return start + remaining
        remaining -= end - start
    return plan["cuts"][-1][1]


def validate_candidates(data, entries):
    """`entries` maps source id -> sources.json entry. Returns candidates in order."""
    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates.json needs a non-empty candidates list")
    seen = set()
    for c in candidates:
        cid = c.get("id")
        if not isinstance(cid, str) or not re.fullmatch(CANDIDATE_ID, cid) or cid in seen:
            raise ValueError("Candidate IDs must be unique c01-style IDs")
        seen.add(cid)
        for key in ["title", "reason"]:
            if not isinstance(c.get(key), str) or not c[key].strip():
                raise ValueError(f"{cid}: {key} is required")
        if c.get("tag") not in production.CLIP_TAGS:
            raise ValueError(f"{cid}: tag must be fun or mood")
        if not isinstance(c.get("evidence", []), list) or not all(isinstance(e, str) for e in c.get("evidence", [])):
            raise ValueError(f"{cid}: evidence must be a list of strings")
        entry = entries.get(c.get("source"))
        if not entry:
            raise ValueError(f"{cid}: unknown source")
        plan = c.get("plan")
        if not isinstance(plan, dict):
            raise ValueError(f"{cid}: plan is required")
        _number(plan.get("zoom", 1), 1, 3, f"{cid}: zoom")
        if entry["kind"] == "video":
            start, end = (c.get("range") or [None, None])[:2]
            _number(start, 0, entry["duration_seconds"], f"{cid}: range start")
            _number(end, start + MIN_CUT, entry["duration_seconds"], f"{cid}: range end")
            _number(plan.get("speed", 1), 0.25, 4, f"{cid}: speed")
            cuts = plan.get("cuts")
            if not isinstance(cuts, list) or not cuts:
                raise ValueError(f"{cid}: cuts are required for video")
            previous = start
            for cut in cuts:
                if not isinstance(cut, list) or len(cut) != 2:
                    raise ValueError(f"{cid}: cuts are [in, out] seconds")
                cut_in = _number(cut[0], previous, end, f"{cid}: cut in")
                _number(cut[1], cut_in + MIN_CUT, end, f"{cid}: cut out")
                previous = cut[1]
        else:
            if c.get("range") is not None or "cuts" in plan or "speed" in plan:
                raise ValueError(f"{cid}: photos have no range, cuts or speed")
            _number(plan.get("photo_seconds", 3.0), *PHOTO_SECONDS, f"{cid}: photo_seconds")
        length = edited_seconds(c, entry)
        _number(c.get("key_moment"), 0, length, f"{cid}: key_moment")
        for insert in plan.get("inserts", []):
            if not isinstance(insert, dict):
                raise ValueError(f"{cid}: inserts are objects")
            if "photos" in insert:
                names = insert["photos"]
                if (not isinstance(names, list) or not production.STACK_PHOTOS[0] <= len(names) <= production.STACK_PHOTOS[1]
                        or any(entries.get(n, {}).get("kind") != "photo" for n in names)):
                    raise ValueError(f"{cid}: a photo stack needs {production.STACK_PHOTOS[0]}..{production.STACK_PHOTOS[1]} photo sources")
                _number(insert.get("interval", 0.35), 0.1, 1.5, f"{cid}: stack interval")
                if insert.get("position", "center") not in production.STACK_POSITIONS:
                    raise ValueError(f"{cid}: stack position must be left, right or center")
                if insert.get("sfx") is not None and not str(insert["sfx"]).startswith("sfx-"):
                    raise ValueError(f"{cid}: stack sfx must be a registered sfx-* ID")
                at = _number(insert.get("at"), 0, length - INSERT_MIN, f"{cid}: insert at")
                _number(insert.get("duration"), INSERT_MIN, length - at + 0.01, f"{cid}: insert duration")
                continue
            photo = entries.get(insert.get("photo"))
            if not photo or photo["kind"] != "photo":
                raise ValueError(f"{cid}: inserts need a photo source")
            at = _number(insert.get("at"), 0, length - INSERT_MIN, f"{cid}: insert at")
            _number(insert.get("duration"), INSERT_MIN, length - at + 0.01, f"{cid}: insert duration")
            if insert.get("position", "right") not in production.OVERLAY_POSITIONS:
                raise ValueError(f"{cid}: insert position must be left or right")
            _number(insert.get("tilt", 0), -production.OVERLAY_MAX_TILT, production.OVERLAY_MAX_TILT, f"{cid}: insert tilt")
        for effect in plan.get("effects", []):
            if not isinstance(effect, dict) or effect.get("type") not in production.EFFECT_TYPES:
                raise ValueError(f"{cid}: effect type must be one of {sorted(production.EFFECT_TYPES)}")
            at = _number(effect.get("at"), 0, length - 0.1, f"{cid}: effect at")
            _number(effect.get("duration"), 0.1, length - at + 0.01, f"{cid}: effect duration")
            _number(effect.get("strength", 1), 0.5, 2, f"{cid}: effect strength")
        mutes = plan.get("mute", [])
        if mutes and entry["kind"] != "video":
            raise ValueError(f"{cid}: only video candidates can mute original sound")
        for mute in mutes:
            if not isinstance(mute, list) or len(mute) != 2:
                raise ValueError(f"{cid}: mute ranges are [start, end] source seconds")
            low = _number(mute[0], c["range"][0], c["range"][1], f"{cid}: mute start")
            _number(mute[1], low + 0.05, c["range"][1], f"{cid}: mute end")
        for caption in plan.get("captions", []):
            try:
                production.validate_caption_text(caption, require_preset=False)
            except ValueError as exc:
                raise ValueError(f"{cid}: {exc}") from exc
            at = _number(caption.get("at"), 0, length, f"{cid}: caption at")
            _number(caption.get("duration"), 0.2, length - at + 0.01, f"{cid}: caption duration")
        for sfx in plan.get("sfx", []):
            if not isinstance(sfx.get("name"), str) or not sfx["name"].strip():
                raise ValueError(f"{cid}: sfx needs a name")
            _number(sfx.get("at"), 0, length, f"{cid}: sfx at")
            if "asset" in sfx and not re.fullmatch(audio_library.ASSET_ID, str(sfx["asset"])) or str(sfx.get("asset", "sfx-")).startswith("bgm-"):
                raise ValueError(f"{cid}: sfx asset must be a registered sfx-* ID")
            _number(sfx.get("gain_db", -6), -40, 0, f"{cid}: sfx gain_db")
        options = plan.get("bgm_options")
        if options is not None and (not isinstance(options, list) or not 2 <= len(options) <= 4 or len(set(options)) != len(options)
                                    or not all(isinstance(o, str) and re.fullmatch(audio_library.ASSET_ID, o) and o.startswith("bgm-")
                                               for o in options)):
            raise ValueError(f"{cid}: bgm_options lists 2..4 different bgm-* IDs to compare")
        bgm = plan.get("bgm")
        if isinstance(bgm, dict):
            if not re.fullmatch(audio_library.ASSET_ID, str(bgm.get("asset"))) or not bgm["asset"].startswith("bgm-"):
                raise ValueError(f"{cid}: bgm asset must be a registered bgm-* ID")
            _number(bgm.get("gain_db", sound.BGM_BASE_DB), -40, -6, f"{cid}: bgm gain_db")
        elif bgm is not None and not isinstance(bgm, str):
            raise ValueError(f"{cid}: bgm is a note string or {{asset, gain_db}}")
        if not isinstance(c.get("preview", False), bool):
            raise ValueError(f"{cid}: preview must be true or false")
    return candidates


def used_audio(candidates):
    ids = set()
    for candidate in candidates:
        plan = candidate["plan"]
        ids |= {s["asset"] for s in plan.get("sfx", []) if s.get("asset")}
        ids |= {i["sfx"] for i in plan.get("inserts", []) if i.get("sfx")}
        ids |= set(plan.get("bgm_options", []))
        if isinstance(plan.get("bgm"), dict):
            ids.add(plan["bgm"]["asset"])
    return sorted(ids)


def stage_audio(run, asset_ids, platforms):
    """Copy eligible library files into run/audio/ so the bundle can serve them. Refuses ineligible assets."""
    if not asset_ids:
        return {}
    library = {a["id"]: a for a in audio_library.load_library()["assets"]}
    staged = {}
    folder = run / "audio"
    folder.mkdir(exist_ok=True)
    for asset_id in asset_ids:
        asset = library.get(asset_id)
        if asset is None:
            raise ValueError(f"{asset_id} is not registered in config/media-licenses.json")
        usable, reason = audio_library.eligibility(asset, platforms)
        if not usable:
            raise ValueError(f"{asset_id} cannot be used yet: {reason}")
        source = safe_path(common.ROOT, asset["file"], True)
        target = safe_path(folder, asset_id + source.suffix.lower())
        if not target.exists():
            shutil.copyfile(source, target)
        if digest(target) != asset["sha256"]:
            raise ValueError(f"{asset_id}: staged file differs from the registered hash")
        staged[asset_id] = {"src": str(target.relative_to(run)), "frames": max(1, int(asset["duration_seconds"] * FPS))}
    return staged


def speech_segments(run, entry):
    path = run / "analysis" / entry["id"] / "transcript.json"
    if entry["kind"] != "video" or not path.is_file():
        return []
    return [s for s in read_json(path)["segments"] if not s.get("suspect")]


def audio_cues(candidate, entry, total, staged, speech):
    plan = candidate["plan"]
    cues = []
    bgm = plan.get("bgm")
    if isinstance(bgm, dict):
        frames = min(total, staged[bgm["asset"]]["frames"])
        talk = sound.map_speech(plan["cuts"], plan.get("speed", 1), speech) if entry["kind"] == "video" else []
        cues.append({"id": "bgm", "src": staged[bgm["asset"]]["src"], "from": 0, "duration": frames,
                     "gain": sound.duck_envelope(frames, talk, base_db=bgm.get("gain_db", sound.BGM_BASE_DB)) if frames > 1 else [[0, -80]]})
    for index, sfx in enumerate(plan.get("sfx", [])):
        if not sfx.get("asset"):
            continue
        start = min(round(sfx["at"] * FPS), total - 1)
        frames = max(2, min(staged[sfx["asset"]]["frames"], total - start))
        db = sfx.get("gain_db", -6)
        cues.append({"id": f"sfx-{index}", "src": staged[sfx["asset"]]["src"], "from": start, "duration": frames,
                     "gain": [[0, db], [frames - 1, db]]})
    for index, insert in enumerate(plan.get("inserts", [])):
        if not insert.get("sfx") or "photos" not in insert:
            continue
        step, at = stack_interval(insert), round(insert["at"] * FPS)
        for shot in range(len(insert["photos"])):
            shot_at = at + shot * step
            if shot_at >= total - 1:
                break
            frames = max(2, min(staged[insert["sfx"]]["frames"], total - shot_at))
            cues.append({"id": f"stack-{index}-{shot}", "src": staged[insert["sfx"]]["src"], "from": shot_at,
                         "duration": frames, "gain": [[0, -10], [frames - 1, -10]]})
    return cues


def stack_interval(insert):
    return max(3, min(45, round(insert.get("interval", 0.35) * FPS)))


def render_props(candidate, entry, staged=None, speech=(), photos=None):
    """Frame-exact props for the Remotion CandidatePreview composition."""
    plan = candidate["plan"]
    if entry["kind"] == "video":
        speed = plan.get("speed", 1)
        mutes = sound.map_mutes(plan["cuts"], speed, plan.get("mute", []))
        segments = [{"src": entry["proxy"], "trimBefore": round(start * FPS),
                     "frames": max(1, round((end - start) * FPS / speed)), "playbackRate": speed}
                    for start, end in plan["cuts"]]
        for segment, ranges in zip(segments, mutes):
            segment["gain"] = sound.mute_envelope(segment["frames"], ranges, base_db=plan.get("original_gain_db", 0))
        kind = "video"
    else:
        segments = [{"src": entry["proxy"], "trimBefore": 0, "frames": round(plan.get("photo_seconds", 3.0) * FPS),
                     "playbackRate": 1}]
        kind = "image"
    total = sum(s["frames"] for s in segments)
    captions = []
    for index, caption in enumerate(plan.get("captions", [])):
        start = min(round(caption["at"] * FPS), total - 1)
        captions.append({"id": f"cap-{index}", "kind": caption["kind"], "preset": production.validate_caption_text(caption, False),
                         "text": caption["text"], "position": caption.get("position", "bottom"),
                         "speaker": caption.get("speaker"), "sub": caption.get("sub"), "from": start,
                         "duration": max(1, min(round(caption["duration"] * FPS), total - start))})
    overlays = []
    for index, insert in enumerate(plan.get("inserts", [])):
        start = min(round(insert["at"] * FPS), total - 1)
        cue = {"id": f"ins-{index}", "from": start, "duration": max(1, min(round(insert["duration"] * FPS), total - start))}
        if "photos" in insert:
            cue |= {"style": "stack", "srcs": [(photos or {})[n] for n in insert["photos"]],
                    "interval": stack_interval(insert), "position": insert.get("position", "center")}
        else:
            cue |= {"src": (photos or {})[insert["photo"]], "position": insert.get("position", "right"), "tilt": insert.get("tilt", 0)}
        overlays.append(cue)
    effects = [{"id": f"fx-{index}", "type": fx["type"], "from": min(round(fx["at"] * FPS), total - 1),
                "duration": max(1, min(round(fx["duration"] * FPS), total - min(round(fx["at"] * FPS), total - 1))),
                "strength": fx.get("strength", 1)} for index, fx in enumerate(plan.get("effects", []))]
    return {"kind": kind, "segments": segments, "zoom": plan.get("zoom", 1), "captions": captions, "overlays": overlays,
            "effects": effects,
            "audio": audio_cues(candidate, entry, total, staged or {}, list(speech)),
            "durationInFrames": total, "keyFrame": min(round(candidate["key_moment"] * FPS), total - 1)}


def clock(seconds):
    seconds = max(0.0, float(seconds))
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


def card_html(candidate, entry, folder, timing=()):
    e = html.escape
    cid = candidate["id"]
    plan = candidate["plan"]
    length = edited_seconds(candidate, entry)
    if entry["kind"] == "video":
        span = f"{e(Path(entry['original']).name)} · {clock(candidate['range'][0])}–{clock(candidate['range'][1])} → 편집 후 {length:.1f}초"
        frames = "".join(f'<figure><img src="{cid}/src-{i}.jpg" alt=""><figcaption>{clock(t)}</figcaption></figure>'
                         for i, t in enumerate(source_times(candidate, entry), start=1))
        cuts = " · ".join(f"{clock(a)}–{clock(b)}" for a, b in plan["cuts"])
        edit = [f"컷 {cuts}", f"속도 ×{plan.get('speed', 1):g} · 줌 ×{plan.get('zoom', 1):g}"]
    else:
        span = f"{e(Path(entry['original']).name)} · 사진 {length:.1f}초"
        frames = f'<figure><img src="{cid}/src-1.jpg" alt=""><figcaption>사진</figcaption></figure>'
        edit = [f"줌 ×{plan.get('zoom', 1):g}(천천히 확대)"]
    edit += [f"자막 [{KIND_LABELS[c['kind']]}·{e(production.validate_caption_text(c, False))}] “{e(c['text'])}” {c['at']:.1f}s" for c in plan.get("captions", [])]
    edit += [f"효과음 {e(s['name'])} {s['at']:.1f}s" + (f" · {e(s['asset'])} {s.get('gain_db', -6)} dB" if s.get("asset") else " · (음원 미지정, 계획만)")
             for s in plan.get("sfx", [])]
    bgm = plan.get("bgm")
    if isinstance(bgm, dict):
        edit.append(f"BGM {e(bgm['asset'])} {bgm.get('gain_db', sound.BGM_BASE_DB)} dB · 대사 중 -{sound.DUCK_DEPTH_DB} dB" +
                    (f" · {e(bgm['note'])}" if bgm.get("note") else ""))
    elif bgm:
        edit.append(f"BGM {e(bgm)} (음원 미지정, 계획만)")
    sides = {"right": "오른쪽", "left": "왼쪽", "center": "가운데"}
    for i in plan.get("inserts", []):
        if "photos" in i:
            edit.append(f"사진 쌓기 {len(i['photos'])}장 {i['at']:.1f}s부터 {i.get('interval', 0.35):.2f}초 간격 · "
                        f"{sides[i.get('position', 'center')]}" + (f" · 셔터 {e(i['sfx'])}" if i.get("sfx") else ""))
        else:
            edit.append(f"사진 띄우기 {e(i['photo'])} {i['at']:.1f}s부터 {i['duration']:.1f}초 · {sides[i.get('position', 'right')]}")
    edit += [f"효과 {e(fx['type'])} {fx['at']:.1f}s · {fx['duration']:.1f}초" for fx in plan.get("effects", [])]
    edit += [f"원음 음소거 {clock(a)}–{clock(b)}" for a, b in plan.get("mute", [])]
    warnings = sound.sfx_warnings([{"asset": s.get("asset") or s["name"], "from": round(s["at"] * FPS)} for s in plan.get("sfx", [])])
    edit += [f"주의: {e(w)}" for w in warnings]
    edit += [e(n) for n in plan.get("notes", [])]
    for note in timing:
        first_line = e(note["text"].split("\n")[0])
        if note["status"] == "synced":
            how = "목소리 구간" if note.get("voiced") else "전사 시각(목소리 구간을 찾지 못함)"
            edit.append(f"자막 타이밍 “{first_line}” {note['authored'][0]:.1f}s → {how} {note['spoken'][0]:.1f}–{note['spoken'][1]:.1f}s에 맞춤")
        else:
            edit.append(f"주의: 대사 자막 “{first_line}”을 전사에서 찾지 못해 작성한 시각을 그대로 씁니다")
    preview = (f'<video controls preload="metadata" src="{cid}/preview.mp4"></video>'
               if (folder / cid / "preview.mp4").is_file() else "")
    options = plan.get("bgm_options", [])
    if options:
        library = {a["id"]: a for a in audio_library.load_library()["assets"]}
        cells = []
        for asset_id in options:
            asset = library.get(asset_id, {})
            origin = "추천 음원" if asset.get("origin") == "claude_search" else "저장된 음원"
            clip = f"{cid}--{asset_id}/preview.mp4"
            player = f'<video controls preload="none" src="{clip}"></video>' if (folder / clip).is_file() else ""
            cells.append(f'<figure><figcaption>{e(origin)} · {e(asset.get("title", asset_id))} ({e(asset_id)})</figcaption>{player}</figure>')
        preview += f'<h3>음악 비교: 같은 장면, 다른 BGM</h3><div class="audition">{"".join(cells)}</div>'
    dialogue = f'<p class="quote">“{e(candidate["dialogue"])}”</p>' if candidate.get("dialogue") else ""
    evidence = "".join(f"<li>{e(x)}</li>" for x in candidate.get("evidence", []))
    return f'''<article id="{cid}">
<header><b>#{cid} {e(candidate["title"])}</b><span class="tag {candidate["tag"]}">{candidate["tag"]}</span><span class="span">{span}</span></header>
<div class="cols"><section><h3>현재 원본</h3><div class="frames">{frames}</div>{dialogue}
<p class="why">왜: {e(candidate["reason"])}</p><ul class="evidence">{evidence}</ul></section>
<section><h3>기대 화면 ({candidate["key_moment"]:.1f}s)</h3><img class="expected" src="{cid}/expected.jpg" alt="기대 화면">{preview}
<ul>{"".join(f"<li>{x}</li>" for x in edit)}</ul></section></div>
<footer>채팅으로 답해 주세요: <code>{cid} 채택</code> · <code>{cid} 자막 수정: …</code> · <code>{cid} 제외</code></footer>
</article>'''


def source_times(candidate, entry):
    if entry["kind"] != "video":
        return [0.0]
    key = candidate["key_moment"]
    length = edited_seconds(candidate, entry)
    return [edited_to_source(candidate, t) for t in (0.0, max(0.0, key - 1.0), key, max(0.0, length - 0.05))]


def page_html(run_id, version, candidates, entries, folder, timing=None):
    groups = {}
    for candidate in candidates:
        groups.setdefault(candidate["source"], []).append(candidate)
    body = "".join(f'<h2>{e_id} · {html.escape(Path(entries[e_id]["original"]).name)}</h2>' +
                   "".join(card_html(c, entries[e_id], folder, (timing or {}).get(c["id"], ())) for c in items)
                   for e_id, items in groups.items())
    fun = sum(c["tag"] == "fun" for c in candidates)
    share = production.caption_style_share({"captions": [x for c in candidates for x in c["plan"].get("captions", [])]})
    ratio = ("자막 비율: 스타일 자막 없음" if share["variety_share"] is None else
             f"자막 비율: 예능 {share['variety']} · 감성 {share['mood']} · 대사 {share['dialogue']} "
             f"(예능 {share['variety_share']:.0%}, 목표 {share['target']:.0%} 참고" +
             ("" if share["in_window"] else " · 목표 범위 밖") + ")")
    variation = production.preset_warnings([x for c in candidates for x in c["plan"].get("captions", [])])
    if variation:
        ratio += " · 자막 variation: " + " / ".join(variation)
    return f'''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>vlog-me · 후보 리뷰 v{version}</title>
<style>
:root{{--bg:#f6f5f2;--card:#fff;--text:#1d1d1b;--muted:#6b6a66;--line:#dedcd6;--fun:#fdeccf;--fun-t:#7a4a00;--mood:#dcecf7;--mood-t:#0c447c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#191918;--card:#232321;--text:#f1f0ec;--muted:#a9a7a0;--line:#3a3936;--fun:#5a3c0c;--fun-t:#fde3b5;--mood:#173a57;--mood-t:#cfe5f7}}}}
body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 -apple-system,"Apple SD Gothic Neo",sans-serif}}
main{{max-width:1180px;margin:auto;padding:24px 16px}}h1{{font-size:22px;margin:0 0 4px}}h2{{font-size:17px;margin:32px 0 12px}}
h3{{font-size:13px;color:var(--muted);font-weight:500;margin:0 0 8px}}
article{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:0 0 16px}}
header{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}}.span{{margin-left:auto;color:var(--muted);font-size:13px}}
.tag{{font-size:12px;padding:2px 10px;border-radius:8px}}.tag.fun{{background:var(--fun);color:var(--fun-t)}}.tag.mood{{background:var(--mood);color:var(--mood-t)}}
.cols{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}}@media (max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.frames{{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}}figure{{margin:0}}figure img{{width:100%;display:block;border-radius:4px}}
figcaption{{font-size:12px;color:var(--muted)}}.expected,video{{width:100%;display:block;border-radius:8px;border:1px solid var(--line);margin-bottom:8px}}
.audition{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}.quote{{margin:10px 0 0}}.why{{color:var(--muted);margin:6px 0 0}}.evidence{{font-size:13px;color:var(--muted);margin:4px 0 0;padding-left:18px}}
ul{{font-size:14px;padding-left:18px;margin:6px 0 0}}footer{{margin-top:12px;font-size:13px;color:var(--muted)}}code{{font-size:12px}}
</style><main><h1>후보 리뷰 v{version}</h1>
<p style="color:var(--muted);margin:0">{html.escape(run_id)} · 후보 {len(candidates)}개 (fun {fun} · mood {len(candidates) - fun}) · 기대 화면은 편집안대로 자막을 합성한 장면입니다. 등록된 음원을 지정한 BGM·효과음은 미리보기에 들어가고, 음원을 지정하지 않은 항목은 계획만 표시합니다.<br>{html.escape(ratio)}</p>
{body}</main></html>'''


def read_entries(run):
    return {e["id"]: e for e in read_json(safe_path(run, "sources.json", True))["entries"]}


def build(run_id):
    config = production.require_production_scope()
    run = production.production_run_path(run_id)
    timeout = config["production_profile"]["timeout_seconds"]
    with run_lock(run):
        state = ingest.status(run_id)
        # Later stages may be reviewed again, e.g. after caption edits or to change scenes after a render.
        allowed = {("analyzed", "pending"), ("reviewed", "pending"), ("review", "failed"), ("review", "paused"),
                   ("selected", "pending"), ("assembled", "pending"), ("rendered", "succeeded")}
        if (state.get("stage"), state.get("status")) not in allowed:
            raise ValueError(f"Review needs an analyzed run, got {state.get('stage')}/{state.get('status')}")
        entries = read_entries(run)
        candidates_path = safe_path(run, "candidates.json", True)
        candidates = validate_candidates(read_json(candidates_path), entries)
        staged = stage_audio(run, used_audio(candidates), config.get("audio_platforms", ["youtube"]))
        review_root = run / "review"
        review_root.mkdir(exist_ok=True)
        version = 1 + max([int(p.name[1:]) for p in review_root.glob("v*") if p.name[1:].isdigit()], default=0)
        folder = safe_path(review_root, f"v{version}")
        folder.mkdir()
        previous = {k: v for k, v in state.items() if k not in {"error"}}
        state = {**previous, "stage": "review", "status": "running", "next_action": "wait for review rendering"}
        write_json(run / "state.json", state, replace=True)
        try:
            jobs, timed, timing = [], [], {}
            for authored in candidates:
                entry = entries[authored["source"]]
                # Dialogue captions are re-timed to the spoken words; candidates.json keeps the authored values.
                candidate, timing[authored["id"]] = caption_sync.sync_candidate(authored, entry, caption_sync.load_words(run, entry),
                                                                                 caption_sync.load_voicing(run, entry))
                timed.append(candidate)
                (folder / candidate["id"]).mkdir()
                proxy = safe_path(run, entry["proxy"], True)
                for index, t in enumerate(source_times(candidate, entry), start=1):
                    out = str(folder / candidate["id"] / f"src-{index}.jpg")
                    if entry["kind"] == "video":
                        run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-ss", f"{t:.3f}",
                                     "-i", str(proxy), "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", out], timeout=timeout)
                    else:
                        run_command(["sips", "-Z", "480", str(proxy), "--out", out], timeout=timeout)
                photos = {k: v["proxy"] for k, v in entries.items()}
                jobs.append({"id": candidate["id"], "props": render_props(candidate, entry, staged, speech_segments(run, entry), photos),
                             "preview": bool(candidate.get("preview"))})
                # Music audition: the same edit once per BGM option, compared by ear before choosing.
                for asset_id in candidate["plan"].get("bgm_options", []):
                    variant = copy.deepcopy(candidate)
                    gain = candidate["plan"]["bgm"].get("gain_db", sound.BGM_BASE_DB) if isinstance(candidate["plan"].get("bgm"), dict) else sound.BGM_BASE_DB
                    variant["plan"]["bgm"] = {"asset": asset_id, "gain_db": gain}
                    (folder / f"{candidate['id']}--{asset_id}").mkdir()
                    jobs.append({"id": f"{candidate['id']}--{asset_id}", "still": False, "preview": True,
                                 "props": render_props(variant, entry, staged, speech_segments(run, entry), photos)})
            write_json(folder / "render-input.json", {"run_id": run_id, "version": version, "jobs": jobs})
            run_command(["node", str(common.ROOT / "renderer/scripts/review.mjs"), run_id, str(version), str(run)], timeout=timeout)
            for job in jobs:
                if job.get("still", True):
                    safe_path(folder, f"{job['id']}/expected.jpg", True)
                if job["preview"]:
                    safe_path(folder, f"{job['id']}/preview.mp4", True)
            (folder / "index.html").write_text(page_html(run_id, version, timed, entries, folder, timing), encoding="utf-8")
            production.require_production_scope()
            state.update(stage="reviewed", status="pending", review_version=version,
                         candidates_sha256=digest(candidates_path),
                         next_action=f"open review/v{version}/index.html; record the user's choices with review.py select")
            write_json(run / "state.json", state, replace=True)
            return {**state, "page": str(folder / "index.html")}
        except BaseException as exc:
            state.update(status="paused" if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else "failed",
                         error=str(exc)[:2000] or type(exc).__name__,
                         next_action=f"inspect review/v{version}; fix candidates.json and build again")
            write_json(run / "state.json", state, replace=True)
            raise


def validate_selection(data, candidates):
    decisions = data.get("decisions") if isinstance(data, dict) else None
    ids = {c["id"] for c in candidates}
    if not isinstance(decisions, dict) or set(decisions) != ids:
        raise ValueError("selection.json must decide every candidate exactly once")
    for cid, decision in decisions.items():
        if not isinstance(decision, dict) or decision.get("decision") not in DECISIONS:
            raise ValueError(f"{cid}: decision must be adopt, caption_edit or drop")
        if decision["decision"] == "caption_edit" and not str(decision.get("note", "")).strip():
            raise ValueError(f"{cid}: caption_edit needs the user's note")
    if not any(d["decision"] != "drop" for d in decisions.values()):
        raise ValueError("At least one candidate must be kept")
    return decisions


def select(run_id):
    production.require_production_scope()
    run = production.production_run_path(run_id)
    with run_lock(run):
        state = ingest.status(run_id)
        if (state.get("stage"), state.get("status")) != ("reviewed", "pending"):
            raise ValueError("Selection needs a reviewed run")
        candidates_path = safe_path(run, "candidates.json", True)
        if digest(candidates_path) != state.get("candidates_sha256"):
            raise ValueError("candidates.json changed after the review was built; build the review again")
        candidates = validate_candidates(read_json(candidates_path), read_entries(run))
        selection_path = safe_path(run, "selection.json", True)
        decisions = validate_selection(read_json(selection_path), candidates)
        state.update(stage="selected", status="pending", selection_sha256=digest(selection_path),
                     counts_selected={k: sum(d["decision"] == k for d in decisions.values()) for k in sorted(DECISIONS)},
                     next_action="assemble timeline v2 from adopted candidates (unit 5+)")
        write_json(run / "state.json", state, replace=True)
        return state


def main():
    def interrupted(signum, _frame):
        raise InterruptedError(f"Stopped by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "select"])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = build(args.run_id) if args.action == "build" else select(args.run_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except KeyboardInterrupt:
        parser.exit(130, "PAUSED: interrupted; inspect retained run state\n")
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
