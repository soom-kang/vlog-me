"""Find low-pitched (likely male) voice in a clip's audio.

Speaking pitch is tracked every 50 ms on a 4 kHz mono copy of the proxy audio. A frame counts as voiced
when its normalized autocorrelation is strong and it is loud enough relative to the clip. The lag picked is
the shortest one close to the best, so a female voice is not halved into the male range (octave error).
Runs of voiced frames whose pitch sits in the male range become segments in source seconds.

This is a heuristic: low female voices, laughter and music can be flagged, and a male voice under loud
street noise can be missed. Review cards show the result as a warning; a person still listens.
"""
import array
import json
import math
import sys

from common import read_json, run_command, write_json

VERSION = 7          # bump when the rules change; cached profiles are recomputed
RATE = 4000
HOP = 0.05
WINDOW = 0.04
MIN_HZ, MAX_HZ = 70, 400
MALE_MAX_HZ = 175     # the female performer speaks around 190–300 Hz; a raised male voice reaches ~170 Hz
VOICED = 0.6
OCTAVE_SLACK = 0.85
MIN_SEGMENT = 0.25
LOUDNESS_SHARE = 0.25
MERGE_GAP = 0.25


def load_samples(path, timeout=600):
    raw = run_command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-vn",
                       "-af", "highpass=f=60,lowpass=f=900", "-ar", str(RATE), "-ac", "1", "-f", "s16le", "-"],
                      timeout=timeout, binary=True).stdout
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) // 2 * 2])
    return samples


def pitch_track(samples, rate=RATE, hop=HOP, window=WINDOW):
    """[(time, f0 or None, rms)] every hop seconds."""
    size, step = int(rate * window), int(rate * hop)
    lo, hi = rate // MAX_HZ, rate // MIN_HZ
    track = []
    for start in range(0, max(0, len(samples) - size - hi), step):
        frame = samples[start:start + size + hi]
        mean = sum(frame) / len(frame)
        frame = [v - mean for v in frame]
        head = frame[:size]
        energy = sum(v * v for v in head)
        rms = math.sqrt(energy / size)
        if energy <= 0:
            track.append((start / rate, None, 0.0))
            continue
        scores = []
        for lag in range(lo, hi + 1):
            other = frame[lag:lag + size]
            corr = sum(a * b for a, b in zip(head, other))
            norm = math.sqrt(energy * sum(b * b for b in other)) or 1.0
            scores.append(corr / norm)
        best = max(scores)
        f0 = None
        if best >= VOICED:
            lag = lo + next(i for i, s in enumerate(scores) if s >= best * OCTAVE_SLACK)
            f0 = rate / lag
        track.append((start / rate, f0, rms))
    return track


def loudness_floor(track):
    """Frames quieter than a quarter of the loud voiced frames are background, not someone talking nearby."""
    loud = sorted(r for _, f, r in track if f)
    return loud[int(len(loud) * 0.9)] * LOUDNESS_SHARE if loud else 0.0


def male_segments(track, hop=HOP):
    """Source-second [start, end] runs of loud voiced frames in the male pitch range."""
    floor = loudness_floor(track)
    runs = []
    for t, f0, rms in track:
        if f0 is None or rms < floor or f0 > MALE_MAX_HZ:
            continue
        if runs and t - runs[-1][1] <= MERGE_GAP:
            runs[-1][1] = t + hop
            runs[-1][2] += 1
        else:
            runs.append([t, t + hop, 1])
    kept = [[a, b] for a, b, n in runs if b - a >= MIN_SEGMENT and n * hop >= MIN_SEGMENT * 0.6]
    return [[round(a, 2), round(b, 2)] for a, b in kept if not octave_of_her(track, a, b)]


def octave_of_her(track, a, b):
    """True when the low run sits at half of her pitch around it: an octave error of her own voice."""
    low = [f0 for t, f0, _ in track if f0 and a <= t < b and f0 <= MALE_MAX_HZ]
    near = sorted(f0 for t, f0, _ in track if f0 and f0 >= HIGH_HZ and a - OCTAVE_WINDOW <= t <= b + OCTAVE_WINDOW)
    return bool(low and near) and abs(2 * sum(low) / len(low) / near[len(near) // 2] - 1) <= OCTAVE_TOLERANCE


BLIP_MAX_HZ = 150     # well below the female performer's range: short replies such as "응"
BLIP_PAD = 0.08


HIGH_HZ = 180        # frames this high belong to the female performer
DETACH = 0.1         # a burst touching her voice is the end of her own word, not a reply
OCTAVE_WINDOW = 0.15  # octave errors sit right next to her voice
BLIP_MIN = 0.1       # one 50 ms frame alone is too weak to call a reply
OCTAVE_TOLERANCE = 0.15


def blips(track, hop=HOP):
    """Short low-pitch bursts detached from her voice, padded by BLIP_PAD, for muting inside dialogue lines."""
    floor = loudness_floor(track)
    runs = []
    for t, f0, rms in track:
        if f0 is None or rms < floor or f0 > BLIP_MAX_HZ:
            continue
        if runs and t - runs[-1][1] <= hop * 1.5:
            runs[-1][1] = t + hop
        else:
            runs.append([t, t + hop])
    high = [(t, f0) for t, f0, _ in track if f0 and f0 >= HIGH_HZ]
    out = []
    for a, b in runs:
        if b - a < BLIP_MIN - 1e-6:
            continue
        if any(a - DETACH - hop <= t <= b + DETACH for t, _ in high):
            continue
        # Half of her nearby pitch is an octave error of her own voice, not another speaker.
        if octave_of_her(track, a, b):
            continue
        out.append([round(max(0.0, a - BLIP_PAD), 2), round(b + BLIP_PAD, 2)])
    return out


def analyze(proxy, timeout=600):
    track = pitch_track(load_samples(proxy, timeout))
    return {"version": VERSION, "hop_seconds": HOP, "male_max_hz": MALE_MAX_HZ, "segments": male_segments(track),
            "blip_max_hz": BLIP_MAX_HZ, "blips": blips(track)}


def load(run, entry):
    path = run / "analysis" / entry["id"] / "voices.json"
    if entry["kind"] != "video" or not path.is_file():
        return None
    return read_json(path)


def unmuted(segments, cuts, mute=(), gain_db=0.0):
    """Male segments that remain audible inside the cuts after mute ranges and clip gain."""
    if gain_db is not None and gain_db <= -60:
        return []
    out = []
    for start, end in segments:
        for cut_in, cut_out in cuts:
            a, b = max(start, cut_in), min(end, cut_out)
            pieces = [[a, b]] if b - a > 0.05 else []
            for m_in, m_out in mute:
                pieces = [p for piece in pieces for p in _subtract(piece, m_in, m_out)]
            out += [[round(x, 2), round(y, 2)] for x, y in pieces if y - x >= 0.15]
    return out


def _subtract(piece, m_in, m_out):
    a, b = piece
    if m_out <= a or m_in >= b:
        return [piece]
    return [p for p in ([a, m_in], [m_out, b]) if p[1] - p[0] > 0.05]


if __name__ == "__main__":
    print(json.dumps(analyze(sys.argv[1]), ensure_ascii=False))
    if len(sys.argv) > 2:
        write_json(sys.argv[2], analyze(sys.argv[1]))
