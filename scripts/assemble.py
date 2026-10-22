#!/usr/bin/env python3
"""Assemble the user's adopted candidates into timeline v2 (the render input).

Order follows selection.json `order` when given, otherwise shooting order. Consecutive candidates
that share a BGM asset get one continuous cue; BGM ducks under the transcript's speech. Caption
edits must be resolved (rebuild the review and select again) before assembling.
"""
import argparse
from datetime import datetime, timezone
import json
import re
import signal

import audio_library
import caption_sync
import common
from common import digest, read_json, run_lock, safe_path, write_json
import ingest
import production
import review
import sound

FPS = review.FPS


def source_map(entries, library):
    sources = {}
    for entry in entries.values():
        if entry["kind"] == "video":
            sources[entry["id"]] = {"kind": "video", "frames": entry["frames"], "has_audio": entry.get("has_audio", True)}
        else:
            sources[entry["id"]] = {"kind": "image"}
    for asset in library:
        sources[asset["id"]] = {"kind": "audio", "frames": max(1, int(asset["duration_seconds"] * FPS))}
    return sources


def ordered(candidates, decisions, entries, order=None):
    kept = [c for c in candidates if decisions[c["id"]]["decision"] != "drop"]
    pending = [c["id"] for c in kept if decisions[c["id"]]["decision"] == "caption_edit"]
    if pending:
        raise ValueError(f"Resolve caption edits first (rebuild the review and select again): {', '.join(pending)}")
    if order is not None:
        if sorted(order) != sorted(c["id"] for c in kept):
            raise ValueError("selection order must list every kept candidate exactly once")
        by_id = {c["id"]: c for c in kept}
        return [by_id[cid] for cid in order]
    position = {entry_id: index for index, entry_id in enumerate(entries)}
    return sorted(kept, key=lambda c: (position[c["source"]], (c.get("range") or [0])[0]))


def build_timeline(run, kept, entries, library):
    clips, audio, captions, overlays, effects, bgm_spans, speech, warnings = [], [], [], [], [], [], [], []
    cursor = 0
    for authored in kept:
        entry = entries[authored["source"]]
        candidate, _ = caption_sync.sync_candidate(authored, entry, caption_sync.load_words(run, entry),
                                                   caption_sync.load_voicing(run, entry))
        plan, cid = candidate["plan"], candidate["id"]
        start = cursor
        if entry["kind"] == "video":
            speed = plan.get("speed", 1)
            mutes = sound.map_mutes(plan["cuts"], speed, plan.get("mute", []))
            for index, (cut_in, cut_out) in enumerate(plan["cuts"]):
                frames = max(1, round((cut_out - cut_in) * FPS / speed))
                clip = {"id": f"{cid}-k{index}", "source": entry["id"], "from": cursor, "duration": frames,
                        "in": round(cut_in * FPS), "speed": speed, "zoom": plan.get("zoom", 1), "tag": candidate["tag"],
                        "aspect": review.display_aspect(entry),
                        "transition": plan.get("transition", "cut") if index == 0 else "cut"}
                if plan.get("deflicker"):
                    clip["deflicker"] = True
                clips.append(clip)
                if entry.get("has_audio", True):
                    db = plan.get("original_gain_db", 0)
                    audio.append({"id": f"{cid}-o{index}", "kind": "original", "clip": clip["id"], "from": cursor,
                                  "duration": frames, "gain_db": sound.mute_envelope(frames, mutes[index], base_db=db)})
                cursor += frames
            # Muted lines no longer sound, so the BGM should not duck under them.
            talk = review.audible_speech(plan, review.speech_segments(run, entry))
            speech += [[start + a, start + b] for a, b in sound.map_speech(plan["cuts"], speed, talk)]
        else:
            frames = round(plan.get("photo_seconds", 3.0) * FPS)
            clips.append({"id": f"{cid}-k0", "source": entry["id"], "from": cursor, "duration": frames, "aspect": review.display_aspect(entry),
                          "zoom": plan.get("zoom", 1), "tag": candidate["tag"], "transition": plan.get("transition", "cut")})
            cursor += frames
        for index, caption in enumerate(plan.get("captions", [])):
            at = start + round(caption["at"] * FPS)
            captions.append({"id": f"{cid}-t{index}", "kind": caption["kind"],
                             "preset": production.validate_caption_text(caption, False), "text": caption["text"],
                             "position": caption.get("position", "bottom"), "speaker": caption.get("speaker"), "sub": caption.get("sub"),
                             "from": min(at, cursor - 1), "duration": max(1, min(round(caption["duration"] * FPS), cursor - at))})
        for index, insert in enumerate(plan.get("inserts", [])):
            at = min(start + round(insert["at"] * FPS), cursor - 1)
            cue = {"id": f"{cid}-p{index}", "from": at, "duration": max(1, min(round(insert["duration"] * FPS), cursor - at))}
            if "photos" in insert:
                step = review.stack_interval(insert)
                cue |= {"style": "stack", "sources": insert["photos"], "interval": step, "position": insert.get("position", "center")}
                if insert.get("sfx"):
                    # One shutter per photo as it lands; only registered, usable audio reaches this point.
                    for shot in range(len(insert["photos"])):
                        shot_at = at + shot * step
                        if shot_at >= cursor - 1:
                            break
                        frames = max(2, min(library[insert["sfx"]]["frames"], cursor - shot_at))
                        audio.append({"id": f"{cid}-p{index}-s{shot}", "kind": "sfx", "source": insert["sfx"], "from": shot_at,
                                      "duration": frames, "in": 0, "gain_db": [[0, -10], [frames - 1, -10]]})
            else:
                cue |= {"source": insert["photo"], "position": insert.get("position", "right"), "tilt": insert.get("tilt", 0)}
            overlays.append(cue)
        for index, fx in enumerate(plan.get("effects", [])):
            at = min(start + round(fx["at"] * FPS), cursor - 1)
            effects.append({"id": f"{cid}-f{index}", "type": fx["type"], "from": at,
                            "duration": max(1, min(round(fx["duration"] * FPS), cursor - at)), "strength": fx.get("strength", 1)})
        for index, sfx in enumerate(plan.get("sfx", [])):
            if not sfx.get("asset"):
                warnings.append(f"{cid}: 효과음 '{sfx['name']}'에 음원이 없어 넣지 않았습니다")
                continue
            at = min(start + round(sfx["at"] * FPS), cursor - 1)
            frames = max(2, min(library[sfx["asset"]]["frames"], cursor - at))
            db = sfx.get("gain_db", -6)
            audio.append({"id": f"{cid}-s{index}", "kind": "sfx", "source": sfx["asset"], "from": at, "duration": frames,
                          "in": 0, "gain_db": [[0, db], [frames - 1, db]]})
        bgm = plan.get("bgm")
        if isinstance(bgm, dict):
            if bgm_spans and bgm_spans[-1]["asset"] == bgm["asset"] and bgm_spans[-1]["end"] == start:
                bgm_spans[-1]["end"] = cursor
            else:
                bgm_spans.append({"asset": bgm["asset"], "start": start, "end": cursor, "in": round(bgm.get("offset", 0) * FPS),
                                  "gain_db": bgm.get("gain_db", sound.BGM_BASE_DB)})
    for index, span in enumerate(bgm_spans):
        frames = span["end"] - span["start"]
        available = library[span["asset"]]["frames"] - span["in"]
        if frames > available:
            warnings.append(f"{span['asset']}: 곡이 {available / FPS:.0f}초라 {frames / FPS:.0f}초 구간을 다 채우지 못합니다(반복 재생 없음)")
            frames = available
        if frames < 2:
            continue
        talk = [[a - span["start"], b - span["start"]] for a, b in speech if b > span["start"] and a < span["start"] + frames]
        audio.append({"id": f"bgm-{index}", "kind": "bgm", "source": span["asset"], "from": span["start"], "duration": frames,
                      "in": span["in"], "gain_db": sound.duck_envelope(frames, talk, base_db=span["gain_db"])})
    timeline = {"schema_version": 2, "purpose": "production", "fps": FPS, "width": 1920, "height": 1080,
                "duration_frames": cursor, "clips": clips, "audio": audio, "captions": captions, "overlays": overlays,
                "effects": effects}
    # Photo-stack shutters are one intentional burst, not separate effects, so they skip the density/repeat advice.
    warnings += sound.sfx_warnings([{"asset": c["source"], "from": c["from"]} for c in audio
                                    if c["kind"] == "sfx" and not re.search(r"-p\d+-s\d+$", c["id"])])
    warnings += production.preset_warnings(captions)
    return timeline, warnings


def assemble(run_id):
    config = production.require_production_scope()
    run = production.production_run_path(run_id)
    with run_lock(run):
        state = ingest.status(run_id)
        if (state.get("stage"), state.get("status")) not in {("selected", "pending"), ("assembled", "pending")}:
            raise ValueError(f"Assemble needs a selected run, got {state.get('stage')}/{state.get('status')}")
        entries = review.read_entries(run)
        candidates_path, selection_path = safe_path(run, "candidates.json", True), safe_path(run, "selection.json", True)
        if digest(candidates_path) != state.get("candidates_sha256") or digest(selection_path) != state.get("selection_sha256"):
            raise ValueError("candidates.json or selection.json changed after selection; review and select again")
        candidates = review.validate_candidates(read_json(candidates_path), entries)
        selection = read_json(selection_path)
        decisions = review.validate_selection(selection, candidates)
        kept = ordered(candidates, decisions, entries, selection.get("order"))
        staged = review.stage_audio(run, review.used_audio(kept), config.get("audio_platforms", ["youtube"]))
        library = {a["id"]: a for a in audio_library.load_library()["assets"] if a["id"] in staged}
        sources = source_map(entries, library.values())
        timeline, warnings = build_timeline(run, kept, entries, {k: sources[k] for k in library})
        duration = production.validate_timeline_v2(timeline, sources)
        target = run / "timeline.json"
        if target.exists():
            # Keep the previous edit for comparison; never overwrite it in place.
            target.rename(run / f"timeline.prev-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json")
        write_json(target, timeline)
        share = production.caption_style_share(timeline)
        report = [f"# 조립 결과 · {run_id}", "", f"- 길이 {duration / FPS:.1f}초 · 클립 {len(timeline['clips'])}개 · 후보 {len(kept)}개",
                  f"- 자막: 예능 {share['variety']} · 감성 {share['mood']} · 대사 {share['dialogue']}"
                  + (f" (예능 {share['variety_share']:.0%})" if share["variety_share"] is not None else ""),
                  f"- 음원: {', '.join(sorted(library)) or '없음'}", "", "## 확인할 점"]
        report += [f"- {w}" for w in warnings] or ["- 없음"]
        (run / "assemble-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        state.update(stage="assembled", status="pending", timeline_sha256=digest(target), duration_seconds=round(duration / FPS, 2),
                     next_action="render with render_prod.py (needs production_render: true)")
        write_json(run / "state.json", state, replace=True)
        return {**state, "warnings": warnings}


def main():
    def interrupted(signum, _frame):
        raise InterruptedError(f"Stopped by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(assemble(args.run_id), indent=2, ensure_ascii=False))
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
