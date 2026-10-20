#!/usr/bin/env python3
"""Analyze an ingested prod-* run so Claude can scout moments without reading whole videos.

Per clip: local Whisper transcript (when a model is configured), loudness events with reaction
hints, silences, scene cuts and 2-second contact sheets. Everything is summarized in
analysis/<id>/summary.md and analysis/index.md. Proxies are read; originals are never opened.
"""
import argparse
import array
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import signal
import statistics

import common
from common import digest, read_json, run_command, run_lock, safe_path, write_json
import ingest
import production

SHEET_INTERVAL = 2
SHEET_GRID = (6, 5)
SHEET_SPAN = SHEET_INTERVAL * SHEET_GRID[0] * SHEET_GRID[1]
LOUD_FLOOR = -35.0
LOUD_MARGIN = 8.0
MIN_SILENCE = 2.0
# Phrases Whisper is known to invent on music or silence (subtitle credits, outro lines).
HALLUCINATIONS = re.compile(r"자막|by\s*\S+$|시청해\s*주셔서|구독|좋아요|알림\s*설정|다음\s*영상에서|MBC|KBS|SBS|뉴스\s*\S+입니다")
# Published SHA-256 of approved models (config/toolchain.json); a mismatch stops analysis.
KNOWN_MODELS = {"ggml-large-v3-turbo.bin": "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"}


def clock(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60:02d}:{seconds % 60:02d}"


def parse_loudness(log):
    return [(float(t), float(m)) for t, m in re.findall(r"\bt:\s*([\d.]+)\s+TARGET:.*?\bM:\s*(-?[\d.]+|-inf)", log)
            if m != "-inf"]


def loud_events(series):
    """Group momentary loudness above max(floor, median+margin) into events, merging gaps under 0.5s."""
    if not series:
        return []
    baseline = statistics.median(max(m, -70.0) for _, m in series)
    threshold = max(LOUD_FLOOR, baseline + LOUD_MARGIN)
    events = []
    for t, m in series:
        if m < threshold:
            continue
        if events and t - events[-1]["end"] <= 0.5:
            events[-1]["end"] = t
            events[-1]["peak_lufs"] = max(events[-1]["peak_lufs"], m)
        else:
            events.append({"start": round(t - 0.4, 2), "end": t, "peak_lufs": m})
    for event in events:
        event["start"], event["end"] = max(0.0, event["start"]), round(event["end"], 2)
    return [{**e, "threshold_lufs": round(threshold, 1)} for e in events]


def parse_silences(log):
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return [{"start": round(max(0.0, s), 2), "end": round(e, 2)} for s, e in zip(starts, ends) if e - s >= MIN_SILENCE]


def parse_scenes(log):
    return [{"time": round(float(t), 2), "score": round(float(s), 1)}
            for s, t in re.findall(r"lavfi\.scd\.score: ([\d.]+), lavfi\.scd\.time: ([\d.]+)", log)]


def parse_transcript(payload):
    segments = []
    for item in payload.get("transcription", []):
        text = item.get("text", "").strip()
        if not text:
            continue
        words = [{"text": t["text"], "start": t["offsets"]["from"] / 1000, "end": t["offsets"]["to"] / 1000}
                 for t in item.get("tokens", []) if t.get("text", "").strip() and not t["text"].startswith("[_")]
        segments.append({"start": item["offsets"]["from"] / 1000, "end": item["offsets"]["to"] / 1000,
                         "text": text, "words": words})
    return segments


def mark_suspect(segments, silences):
    """Flag likely hallucinations: known invented phrases, or text mostly inside detected silence."""
    for segment in segments:
        length = max(segment["end"] - segment["start"], 0.1)
        quiet = sum(max(0.0, min(segment["end"], s["end"]) - max(segment["start"], s["start"])) for s in silences)
        reasons = (["known_phrase"] if HALLUCINATIONS.search(segment["text"]) else []) + (["in_silence"] if quiet >= 0.5 * length else [])
        segment["suspect"] = reasons
    return segments


def label_events(events, segments):
    """Mostly overlapping speech is loud_speech; otherwise (after speech or without speech) a reaction hint."""
    for event in events:
        length = max(event["end"] - event["start"], 0.1)
        overlap = sum(max(0.0, min(event["end"], s["end"]) - max(event["start"], s["start"]))
                      for s in segments if not s.get("suspect"))
        event["hint"] = "loud_speech" if overlap >= 0.5 * length else "reaction"
    return events


def model_path(config):
    name = config.get("asr_model")
    if not name:
        return None
    path = safe_path(common.ROOT, f".tools/whisper/{name}")
    if not path.is_file():
        return None
    if name in KNOWN_MODELS and digest(path) != KNOWN_MODELS[name]:
        raise ValueError(f"Whisper model hash mismatch: {name}")
    return path


def parse_words(payload):
    """Word-level pass (-ml 1 -sow): one entry per word with its own start/end, used to time captions."""
    words = []
    for item in payload.get("transcription", []):
        text = item.get("text", "").strip()
        start, end = item["offsets"]["from"] / 1000, item["offsets"]["to"] / 1000
        if text and end > start:
            words.append({"text": text, "start": round(start, 3), "end": round(end, 3)})
    return words


VOICE_HOP = 0.05


def voicing_scores(samples, rate=8000, hop=400, window=640, low_hz=140, high_hz=450):
    """Per-hop periodicity (0..1) of the speaking-pitch band. Street noise scores low, voiced speech high."""
    scores = []
    lo, hi = rate // high_hz, rate // low_hz
    for start in range(0, max(0, len(samples) - window), hop):
        frame = samples[start:start + window]
        mean = sum(frame) / window
        frame = [v - mean for v in frame]
        energy = sum(v * v for v in frame)
        if energy <= 0:
            scores.append(0.0)
            continue
        best = 0.0
        for lag in range(lo, hi, 2):
            corr = sum(frame[i] * frame[i + lag] for i in range(0, window - lag, 2))
            best = max(best, corr / (energy / 2))
        scores.append(round(max(0.0, min(1.0, best)), 2))
    return scores


def voicing_track(proxy, folder, timeout):
    """analysis/<id>/voicing.json: periodicity every 50 ms, used to snap captions to real speech."""
    raw = run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(proxy), "-vn",
                       "-af", "highpass=f=90,lowpass=f=1000", "-ar", "8000", "-ac", "1", "-f", "s16le", "-"],
                      timeout=timeout, binary=True).stdout
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) // 2 * 2])
    write_json(folder / "voicing.json", {"hop_seconds": VOICE_HOP, "scores": voicing_scores(samples)})


def extract_wav(proxy, folder, timeout):
    wav = safe_path(folder, "audio-16k.wav")
    run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-i", str(proxy),
                 "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], timeout=timeout)
    return wav


def word_pass(wav, folder, model, timeout):
    run_command(["whisper-cli", "-m", str(model), "-l", "ko", "-t", "8", "-np", "-oj", "-ml", "1", "-sow",
                 "-of", str(folder / "whisper-words"), "-f", str(wav)], timeout=timeout)
    words = parse_words(read_json(safe_path(folder, "whisper-words.json", True)))
    write_json(folder / "words.json", {"source": "whisper.cpp -ml 1 -sow", "words": words})
    return words


def transcribe(proxy, folder, model, timeout):
    wav = extract_wav(proxy, folder, timeout)
    try:
        run_command(["whisper-cli", "-m", str(model), "-l", "ko", "-t", "8", "-np", "-ojf",
                     "-of", str(folder / "whisper"), "-f", str(wav)], timeout=timeout)
        segments = parse_transcript(read_json(safe_path(folder, "whisper.json", True)))
        word_pass(wav, folder, model, timeout)
        return segments
    finally:
        wav.unlink(missing_ok=True)


def add_words(run_id):
    """Add analysis/<id>/words.json to an already analyzed run without redoing the analysis.

    Older runs only have segment times, which can be off by a second; captions need word timing.
    Existing words.json files are kept.
    """
    config = production.require_production_scope()
    run = production.production_run_path(run_id)
    model = model_path(config)
    if model is None:
        raise ValueError("Word timing needs the configured Whisper model")
    added = []
    with run_lock(run):
        state = ingest.status(run_id)
        if state.get("stage") in {"ingest", "ingested", "analyze"}:
            raise ValueError("Run the full analysis first")
        for entry in read_json(safe_path(run, "sources.json", True))["entries"]:
            folder = run / "analysis" / entry["id"]
            if entry["kind"] != "video" or not entry.get("has_audio"):
                continue
            timeout = config["production_profile"]["timeout_seconds"]
            proxy = safe_path(run, entry["proxy"], True)
            if not (folder / "voicing.json").exists():
                voicing_track(proxy, folder, timeout)
                added.append(f"{entry['id']}:voicing")
            if (folder / "words.json").exists() or read_json(safe_path(folder, "transcript.json", True)).get("status") != "done":
                continue
            wav = extract_wav(proxy, folder, timeout)
            try:
                word_pass(wav, folder, model, timeout)
            finally:
                wav.unlink(missing_ok=True)
            added.append(f"{entry['id']}:words")
    return {"run_id": run_id, "words_added": added}


def analyze_clip(run, entry, model, timeout):
    folder = safe_path(run / "analysis", entry["id"])
    folder.mkdir()
    proxy = safe_path(run, entry["proxy"], True)
    segments, transcript_status = [], "not_run: no audio" if not entry.get("has_audio") else "not_run: no asr_model"
    events, silences = [], []
    if entry.get("has_audio"):
        if model:
            segments = transcribe(proxy, folder, model, timeout)
            transcript_status = "done"
        voicing_track(proxy, folder, timeout)
        quiet = run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(proxy), "-vn", "-af",
                             "silencedetect=noise=-35dB:d=2", "-f", "null", "-"], timeout=timeout).stderr
        silences = parse_silences(quiet)
        segments = mark_suspect(segments, silences)
        loud = run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(proxy), "-vn", "-af", "ebur128",
                            "-f", "null", "-"], timeout=timeout).stderr
        events = label_events(loud_events(parse_loudness(loud)), segments)
    cuts = parse_scenes(run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(proxy), "-an", "-vf",
                                     "scdet=threshold=10", "-f", "null", "-"], timeout=timeout).stderr)
    run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-i", str(proxy), "-an", "-vf",
                 f"fps=1/{SHEET_INTERVAL}:eof_action=pass,scale=320:-2,tile={SHEET_GRID[0]}x{SHEET_GRID[1]}", "-q:v", "4",
                 str(folder / "sheet-%03d.jpg")], timeout=timeout)
    sheets = sorted(p.name for p in folder.glob("sheet-*.jpg"))
    write_json(folder / "transcript.json", {"status": transcript_status, "segments": segments})
    write_json(folder / "signals.json", {"loud_events": events, "silences": silences, "scene_cuts": cuts})
    duration = entry["duration_seconds"]
    lines = [f"# {entry['id']} · {Path(entry['original']).name}", "",
             f"- 길이 {clock(duration)} · 촬영 {entry.get('captured_at') or '미상'} · 회전 {entry.get('rotation', 0)}°"
             f" · VFR {'예' if entry.get('vfr') else '아니오'} · HDR {'예(색 확인 필요)' if entry.get('hdr') else '아니오'}"
             f" · 소리 {'있음' if entry.get('has_audio') else '없음'}",
             f"- 전사: {transcript_status}", "", "## 대사"]
    lines += [f"- [{clock(s['start'])}–{clock(s['end'])}] {'(의심: ' + ', '.join(s['suspect']) + ') ' if s.get('suspect') else ''}{s['text']}"
              for s in segments] or ["- (없음)"]
    lines += ["", "## 소리 이벤트 (reaction = 대사 직후·대사 밖의 큰 소리, 웃음 후보)"]
    lines += [f"- [{clock(e['start'])}–{clock(e['end'])}] {e['hint']} · 최대 {e['peak_lufs']:.0f} LUFS" for e in events] or ["- (없음)"]
    lines += ["", "## 2초 이상 정적"]
    lines += [f"- [{clock(s['start'])}–{clock(s['end'])}]" for s in silences] or ["- (없음)"]
    lines += ["", "## 장면 전환"]
    lines += [f"- {clock(c['time'])} (score {c['score']})" for c in cuts] or ["- (없음)"]
    lines += ["", f"## Contact sheet ({SHEET_INTERVAL}초 간격, {SHEET_GRID[0]}×{SHEET_GRID[1]}, 왼쪽 위부터 행 순서)"]
    lines += [f"- {name}: {clock(i * SHEET_SPAN)}–{clock(min(duration, (i + 1) * SHEET_SPAN))}" for i, name in enumerate(sheets)]
    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"id": entry["id"], "duration_seconds": duration, "transcript": transcript_status,
            "speech_segments": sum(not s.get("suspect") for s in segments), "suspect_segments": sum(bool(s.get("suspect")) for s in segments),
            "reactions": sum(e["hint"] == "reaction" for e in events), "silences": len(silences), "scene_cuts": len(cuts),
            "sheets": len(sheets)}


def photo_sheet(run, photos, timeout):
    if not photos:
        return None
    folder = safe_path(run / "analysis", "photos")
    folder.mkdir()
    for index, entry in enumerate(photos):
        run_command(["sips", "-Z", "480", str(safe_path(run, entry["proxy"], True)), "--out",
                     str(folder / f"thumb-{index:03d}.jpg")], timeout=timeout)
    run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-framerate", "1", "-i",
                 str(folder / "thumb-%03d.jpg"), "-vf",
                 "scale=320:320:force_original_aspect_ratio=decrease,pad=320:320:(ow-iw)/2:(oh-ih)/2,tile=6x5",
                 "-q:v", "4", str(folder / "sheet-%03d.jpg")], timeout=timeout)
    return sorted(p.name for p in folder.glob("sheet-*.jpg"))


def analyze(run_id):
    config = production.require_production_scope()
    run = production.production_run_path(run_id)
    timeout = config["production_profile"]["timeout_seconds"]
    with run_lock(run):
        state = ingest.status(run_id)
        retry = state.get("stage") == "analyze" and state.get("status") in {"failed", "paused"}
        if not (state.get("stage") == "ingested" and state.get("status") == "pending") and not retry:
            raise ValueError(f"Analyze needs an ingested run, got {state.get('stage')}/{state.get('status')}")
        if retry and (run / "analysis").exists():
            # Keep the failed attempt for inspection instead of deleting it.
            (run / "analysis").rename(run / f"analysis.failed-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}")
        if (run / "analysis").exists():
            raise ValueError("Existing analysis requires inspection; no automatic overwrite")
        sources = read_json(safe_path(run, "sources.json", True))
        if retry and digest(run / "sources.json") != state.get("sources_sha256"):
            raise ValueError("sources.json changed; preserve and inspect")
        model = model_path(config)
        if config.get("asr_model") and model is None:
            raise ValueError("Configured asr_model is missing under .tools/whisper/")
        state = {key: value for key, value in state.items() if key not in {"error", "recorded_status", "reason"}}
        state.update(stage="analyze", status="running", next_action="wait for analysis")
        write_json(run / "state.json", state, replace=True)
        try:
            (run / "analysis").mkdir()
            videos = [e for e in sources["entries"] if e["kind"] == "video"]
            photos = [e for e in sources["entries"] if e["kind"] == "photo"]
            clips = [analyze_clip(run, entry, model, timeout) for entry in videos]
            sheets = photo_sheet(run, photos, timeout)
            lines = ["# 분석 색인", "", f"- run: {run_id} · 영상 {len(clips)}개 · 사진 {len(photos)}장",
                     f"- 전사 모델: {config.get('asr_model') or '없음(대사 없이 소리·화면 신호만)'}", "",
                     "| 클립 | 길이 | 전사 | 대사 | 웃음 후보 | 장면 전환 | 요약 |", "| --- | --- | --- | --- | --- | --- | --- |"]
            lines += [f"| {c['id']} | {clock(c['duration_seconds'])} | {c['transcript']} | {c['speech_segments']} | "
                      f"{c['reactions']} | {c['scene_cuts']} | {c['id']}/summary.md |" for c in clips]
            if sheets:
                lines += ["", "## 사진", f"- contact sheet: {', '.join('photos/' + s for s in sheets)} (6×5, 촬영 순서)"]
                lines += [f"- {i + 1}. {e['id']} · {Path(e['original']).name} · {e.get('captured_at') or '촬영 시각 미상'}"
                          for i, e in enumerate(photos)]
            (run / "analysis/index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            write_json(run / "analysis/index.json", {"run_id": run_id, "clips": clips, "photo_sheets": sheets or []})
            production.require_production_scope()
            state.update(stage="analyzed", status="pending", analysis_sha256=digest(run / "analysis/index.json"),
                         next_action="scout candidates (unit 4) from analysis/index.md and clip summaries")
            write_json(run / "state.json", state, replace=True)
            return state
        except BaseException as exc:
            state.update(status="paused" if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else "failed",
                         error=str(exc)[:2000] or type(exc).__name__,
                         next_action="inspect analysis/; rerun analyze to retry (the failed attempt is kept)")
            write_json(run / "state.json", state, replace=True)
            raise


def main():
    def interrupted(signum, _frame):
        raise InterruptedError(f"Stopped by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--add-words", action="store_true", help="add word timing to an analyzed run")
    args = parser.parse_args()
    try:
        print(json.dumps(add_words(args.run_id) if args.add_words else analyze(args.run_id), indent=2, ensure_ascii=False))
    except KeyboardInterrupt:
        parser.exit(130, "PAUSED: interrupted; inspect retained run state\n")
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
