"""Time dialogue captions to the words actually spoken.

Whisper finds which words a caption says (analysis/<id>/words.json), but on noisy street audio its
timestamps can be off by about two seconds. The caption is then snapped to the voiced stretch around
that estimate (analysis/<id>/voicing.json, pitch periodicity every 50 ms), measured in edited time so
speech that continues across a cut keeps one caption. The caption appears LEAD seconds before the
voice starts and leaves TAIL seconds after it stops.

Set "sync": "manual" on a caption to keep its authored timing; "sync": "speech" times any kind.

A caption stays up long enough to read (READ_BASE + READ_PER_CHAR per character) even when the voice is
shorter. Captions that share a position never overlap: the earlier one ends just before the next starts.
With plan "original": "dialogue_only" the original sound is heard only while she speaks a dialogue line
(the synced spoken span, or the caption itself when timed by hand); everything else in the cuts is muted, so
other voices between the lines or during a caption's extra reading time are not heard.
"""
import copy
import difflib
import re

from common import read_json

LEAD = 0.15
TAIL = 0.3
MIN_RATIO = 0.6
VOICED = 0.45          # periodicity score that counts as voiced
MIN_RUN = 0.2          # shorter voiced blips are ignored
PHRASE_GAP = 0.45      # pauses shorter than this stay inside one phrase
SECONDS_PER_CHAR = 0.13
READ_BASE = 0.4
READ_PER_CHAR = 0.08
MIN_SHOWN = 0.6        # an overlapped caption keeps at least this long
GAP = 0.05
TRUST_SHIFT = 1.0      # seconds; larger snaps mean Whisper's word times are off


def normalize(text):
    return re.sub(r"[\s\.,!?~…·\"'()\[\]-]", "", text)


def load_words(run, entry):
    path = run / "analysis" / entry["id"] / "words.json"
    if entry["kind"] != "video" or not path.is_file():
        return []
    return read_json(path)["words"]


def load_voicing(run, entry):
    path = run / "analysis" / entry["id"] / "voicing.json"
    if entry["kind"] != "video" or not path.is_file():
        return None
    return read_json(path)


def _to_edited(cuts, speed, t):
    """Edited-time position of source time t. Outside the cuts, snap to the nearest cut edge."""
    offset = 0.0
    for cut_in, cut_out in cuts:
        if t < cut_in:
            return offset / speed
        if t <= cut_out:
            return (offset + t - cut_in) / speed
        offset += cut_out - cut_in
    return offset / speed


def _to_source(cuts, speed, t):
    """Source-time position of edited time t (inverse of _to_edited inside the cuts)."""
    remaining = t * speed
    for cut_in, cut_out in cuts:
        if remaining <= cut_out - cut_in:
            return cut_in + remaining
        remaining -= cut_out - cut_in
    return cuts[-1][1]


def reading_seconds(text):
    return READ_BASE + READ_PER_CHAR * len(normalize(text))


def separate(captions, length):
    """Trim captions that share a position so they never overlap. Returns notes."""
    notes = []
    by_position = {}
    for caption in captions:
        by_position.setdefault(caption.get("position", "bottom"), []).append(caption)
    for group in by_position.values():
        group.sort(key=lambda c: c["at"])
        for earlier, later in zip(group, group[1:]):
            end = earlier["at"] + earlier["duration"]
            if end <= later["at"] + 1e-6:
                continue
            if later["at"] - GAP - earlier["at"] >= MIN_SHOWN:
                earlier["duration"] = round(later["at"] - GAP - earlier["at"], 3)
            else:
                earlier["duration"] = round(MIN_SHOWN, 3)
                shift = earlier["at"] + MIN_SHOWN + GAP
                later["duration"] = round(max(MIN_SHOWN, later["at"] + later["duration"] - shift), 3)
                later["at"] = round(min(shift, max(0.0, length - later["duration"])), 3)
            notes.append({"text": earlier["text"], "status": "separated", "next": later["text"]})
    return notes


def dialogue_windows(captions):
    """Edited-time windows where dialogue is heard: the spoken span when synced, else the caption itself."""
    return sorted(c.get("_spoken") or [c["at"], c["at"] + c["duration"]] for c in captions if c["kind"] == "dialogue")


def gate_mutes(cuts, speed, windows):
    """Source-second mute ranges covering everything in the cuts outside the edited-time windows."""
    keep = [[_to_source(cuts, speed, a), _to_source(cuts, speed, b)] for a, b in windows]
    mutes = []
    for cut_in, cut_out in cuts:
        cursor = cut_in
        for a, b in sorted(keep):
            a, b = max(a, cut_in), min(b, cut_out)
            if b <= a:
                continue
            if a - cursor > GAP:
                mutes.append([round(cursor, 3), round(a, 3)])
            cursor = max(cursor, b)
        if cut_out - cursor > GAP:
            mutes.append([round(cursor, 3), round(cut_out, 3)])
    return mutes


def match(text, words):
    """Best run of consecutive words whose characters match `text`. Returns (first, last, ratio)."""
    target = normalize(text)
    if not target or not words:
        return None
    best = None
    for first in range(len(words)):
        joined = ""
        for last in range(first, len(words)):
            joined += normalize(words[last]["text"])
            ratio = difflib.SequenceMatcher(None, target, joined).ratio()
            if best is None or ratio > best[2]:
                best = (first, last, ratio)
            if len(joined) > len(target) * 1.5:
                break
    return best if best and best[2] >= MIN_RATIO else None


def voiced_phrases(voicing, cuts, speed):
    """Voiced phrases as [start, end] in edited seconds, following the cut list."""
    hop, scores = voicing["hop_seconds"], voicing["scores"]
    frames, offset = [], 0.0
    for cut_in, cut_out in cuts:
        for index in range(int(cut_in / hop), min(len(scores), int(cut_out / hop))):
            frames.append(((offset + index * hop - cut_in) / speed, scores[index] >= VOICED))
        offset += cut_out - cut_in
    step = hop / speed
    runs = []
    for t, voiced in frames:
        if not voiced:
            continue
        if runs and t - runs[-1][1] <= step * 1.5 + 0.25:
            runs[-1][1] = t + step
        else:
            runs.append([t, t + step])
    phrases = []
    for start, end in (r for r in runs if r[1] - r[0] >= MIN_RUN):
        if phrases and start - phrases[-1][1] <= PHRASE_GAP:
            phrases[-1][1] = end
        else:
            phrases.append([start, end])
    return phrases


def snap(start, end, text, phrases):
    """Pick the voiced phrase that best explains a Whisper estimate [start, end] (edited seconds)."""
    expected = max(end - start, len(normalize(text)) * SECONDS_PER_CHAR)
    best, best_score = None, 0.0
    for p_start, p_end in phrases:
        if p_end < start - 1.0 or p_start > end + 3.0:
            continue
        overlap = max(0.0, min(p_end, start + expected + 1.0) - max(p_start, start))
        score = overlap - 0.3 * abs(p_start - start)
        if overlap > 0 and score > best_score:
            best, best_score = (p_start, p_end), score
    return best


def sync_candidate(candidate, entry, words, voicing=None):
    """Return (timed copy of the candidate, notes). The authored candidate is not modified."""
    timed = copy.deepcopy(candidate)
    notes = []
    plan = timed["plan"]
    if entry["kind"] != "video":
        return timed, notes
    cuts, speed = plan["cuts"], plan.get("speed", 1)
    length = sum(b - a for a, b in cuts) / speed
    if words:
        notes += _sync_speech(plan, cuts, speed, length, words, voicing)
    # Gate on the spoken windows before overlapping captions are trimmed, so no line is cut short.
    if plan.get("original") == "dialogue_only":
        gated = gate_mutes(cuts, speed, dialogue_windows(plan.get("captions", [])))
        plan["mute"] = sorted(plan.get("mute", []) + gated)
        notes.append({"text": "", "status": "gated", "mutes": gated})
    notes += separate(plan.get("captions", []), length)
    for caption in plan.get("captions", []):
        caption.pop("_spoken", None)
    return timed, notes


def _sync_speech(plan, cuts, speed, length, words, voicing):
    notes = []
    inside = [w for w in words if any(a - 0.05 <= w["start"] < b for a, b in cuts)]
    phrases = voiced_phrases(voicing, cuts, speed) if voicing else []
    for caption in plan.get("captions", []):
        mode = caption.get("sync", "speech" if caption["kind"] == "dialogue" else "manual")
        if mode != "speech":
            continue
        found = match(caption["text"], inside)
        if found is None:
            notes.append({"text": caption["text"], "status": "unmatched", "at": caption["at"]})
            continue
        first, last, ratio = found
        start = _to_edited(cuts, speed, inside[first]["start"])
        end = _to_edited(cuts, speed, inside[last]["end"])
        voiced = snap(start, end, caption["text"], phrases)
        if voiced:
            # A long sentence spans several voiced phrases: keep the length the words measured.
            # A soft sentence ending can fall below the voicing threshold: when the snap moved the start only a
            # little, the word timing is trusted for the end as well.
            span, shift = end - start, voiced[0] - start
            ends = [voiced[1]] + [b for a, b in phrases if voiced[0] < a <= voiced[0] + span]
            if abs(shift) <= TRUST_SHIFT:
                ends.append(end + shift)
            start, end = voiced[0], max(ends)
        new_at = max(0.0, start - LEAD)
        new_end = min(length, max(end + TAIL, new_at + reading_seconds(caption["text"])))
        notes.append({"text": caption["text"], "status": "synced", "ratio": round(ratio, 2), "voiced": bool(voiced),
                      "authored": [round(caption["at"], 2), round(caption["at"] + caption["duration"], 2)],
                      "spoken": [round(start, 2), round(end, 2)],
                      "words": [round(inside[first]["start"], 2), round(inside[last]["end"], 2)]})
        caption["at"], caption["duration"] = round(new_at, 3), round(new_end - new_at, 3)
        # The sound is opened only while she speaks, not for the extra reading time of the caption.
        caption["_spoken"] = [round(new_at, 3), round(min(length, end + TAIL), 3)]
    return notes
