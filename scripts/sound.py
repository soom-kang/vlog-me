"""Sound placement rules: BGM ducking under speech and SFX density. Pure functions, no media access."""

BGM_BASE_DB = -16
DUCK_DEPTH_DB = 12
DUCK_FADE = 6
EDGE_FADE = 15
MERGE_GAP = 15
SILENT_DB = -60
SFX_PER_MINUTE = 8
SAME_SFX_GAP_SECONDS = 3
MUTE_DB = -80
MUTE_FADE = 4


def merge(intervals, gap=MERGE_GAP):
    merged = []
    for start, end in sorted(intervals):
        if merged and start - merged[-1][1] <= gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def duck_envelope(duration, speech, base_db=BGM_BASE_DB, depth_db=DUCK_DEPTH_DB, fade=DUCK_FADE, edge=EDGE_FADE):
    """Gain points [[frame, dB], ...] for a BGM cue of `duration` frames.

    `speech` holds [start, end) frame intervals relative to the cue. The music fades in and out at the
    edges and drops by `depth_db` while people talk, so dialogue stays clear.
    """
    if duration < 2:
        raise ValueError("Cue too short for an envelope")
    last = duration - 1
    duck_db = max(-80, base_db - depth_db)
    points = {0: SILENT_DB if last > 2 * edge else base_db, last: SILENT_DB if last > 2 * edge else base_db}
    if last > 2 * edge:
        points[edge] = base_db
        points[last - edge] = base_db
    for start, end in merge([[max(0, s), min(last, e)] for s, e in speech if e > 0 and s < last]):
        for frame, db in [(start - fade, base_db), (start, duck_db), (end, duck_db), (end + fade, base_db)]:
            if 0 < frame < last:
                points[frame] = min(points.get(frame, db), db)
    # A speech region inside the edge fades keeps the duck level; drop base points it overlaps.
    for start, end in merge([[s, e] for s, e in speech]):
        for frame in [f for f, db in points.items() if start < f < end and db != duck_db and 0 < f < last]:
            del points[frame]
    return [[frame, points[frame]] for frame in sorted(points)]


def mute_envelope(duration, mutes, base_db=0, fade=MUTE_FADE):
    """Gain points for an original-sound cue that dips to silence over `mutes` ([start, end) frames).

    Short linear fades keep the cut from clicking, so a muted voice disappears under the BGM.
    """
    last = duration - 1
    spans = merge([[max(0, s), min(last, e)] for s, e in mutes if e > 0 and s < last], gap=2 * fade)
    if last < 1 or not spans:
        return [[0, base_db], [max(last, 1), base_db]] if last >= 1 else [[0, base_db]]

    def level(frame):
        db = base_db
        for start, end in spans:
            if start <= frame <= end:
                return MUTE_DB
            if start - fade < frame < start:
                db = min(db, base_db + (MUTE_DB - base_db) * (frame - (start - fade)) / fade)
            if end < frame < end + fade:
                db = min(db, MUTE_DB + (base_db - MUTE_DB) * (frame - end) / fade)
        return round(db, 2)

    frames = {0, last}
    for start, end in spans:
        frames |= {f for f in (start - fade, start, end, end + fade) if 0 <= f <= last}
    return [[frame, level(frame)] for frame in sorted(frames)]


def map_mutes(cuts, speed, mutes, fps=30):
    """Per-cut [start, end) frame ranges, relative to each cut, for source-time mute ranges."""
    per_cut = []
    for cut_in, cut_out in cuts:
        ranges = []
        for start, end in mutes:
            a, b = max(cut_in, start), min(cut_out, end)
            if b > a:
                ranges.append([round((a - cut_in) / speed * fps), round((b - cut_in) / speed * fps)])
        per_cut.append(ranges)
    return per_cut


def map_speech(cuts, speed, segments, fps=30):
    """Map source-time speech segments into edited-candidate frames through the cut list."""
    mapped, offset = [], 0.0
    for cut_in, cut_out in cuts:
        for segment in segments:
            start, end = max(cut_in, segment["start"]), min(cut_out, segment["end"])
            if end > start:
                mapped.append([round((offset + start - cut_in) / speed * fps), round((offset + end - cut_in) / speed * fps)])
        offset += cut_out - cut_in
    return mapped


def sfx_warnings(cues, fps=30):
    """Density and repetition warnings for SFX cues ({asset, from}). Advice for review, not a hard rule."""
    warnings = []
    starts = sorted(c["from"] for c in cues)
    window = 60 * fps
    for index, start in enumerate(starts):
        count = sum(1 for s in starts[index:] if s < start + window)
        if count > SFX_PER_MINUTE:
            warnings.append(f"{count} SFX within one minute from {start / fps:.0f}s (guide: {SFX_PER_MINUTE} or fewer)")
            break
    by_asset = {}
    for cue in sorted(cues, key=lambda c: c["from"]):
        previous = by_asset.get(cue["asset"])
        if previous is not None and cue["from"] - previous < SAME_SFX_GAP_SECONDS * fps:
            warnings.append(f"{cue['asset']} repeats within {SAME_SFX_GAP_SECONDS}s at {cue['from'] / fps:.1f}s")
        by_asset[cue["asset"]] = cue["from"]
    return warnings
