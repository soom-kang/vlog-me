"""Male-voice control: pitch tracking, dialogue-only gating, caption overlap and reading time. Synthetic data only."""
import array
import math
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import caption_sync
import voices


def tone(hz, seconds, rate=voices.RATE, amplitude=8000):
    """A voiced-like tone with a few harmonics, as voices.load_samples would return it."""
    return array.array("h", [int(amplitude * sum(math.sin(2 * math.pi * hz * k * i / rate) / k for k in (1, 2, 3)) / 1.8)
                             for i in range(int(seconds * rate))])


def silence(seconds, rate=voices.RATE):
    return array.array("h", [0] * int(seconds * rate))


class PitchTests(unittest.TestCase):
    def test_low_voice_is_found_and_high_voice_is_not(self):
        samples = tone(240, 1.0) + silence(0.3) + tone(120, 0.8) + silence(0.3) + tone(260, 1.0)
        track = voices.pitch_track(samples)
        segments = voices.male_segments(track)
        self.assertEqual(len(segments), 1)
        start, end = segments[0]
        self.assertAlmostEqual(start, 1.3, delta=0.1)
        self.assertAlmostEqual(end, 2.1, delta=0.15)

    def test_female_tone_is_not_halved(self):
        track = voices.pitch_track(tone(230, 1.0))
        pitches = [f for _, f, _ in track if f]
        self.assertTrue(pitches)
        self.assertTrue(all(f > 200 for f in pitches))

    def test_blips_skip_her_own_word_endings_and_octave_errors(self):
        hop = voices.HOP
        her = [(i * hop, 230.0, 1000.0) for i in range(20)]
        # A detached low reply 0.5 s after she stops.
        reply = [(1.5 + i * hop, 110.0, 1000.0) for i in range(4)]
        # A low frame touching her voice (end of her own word).
        tail = [(1.0, 140.0, 1000.0)]
        gap = [(1.05 + i * hop, None, 10.0) for i in range(9)]
        blips = voices.blips(her + tail + gap + reply)
        self.assertEqual(len(blips), 1)
        self.assertAlmostEqual(blips[0][0], 1.5 - voices.BLIP_PAD, delta=0.01)
        # Exactly half of her pitch nearby is an octave error, not a reply.
        octave = [(1.4 + i * hop, 115.0, 1000.0) for i in range(3)]
        near = [(1.7 + i * hop, 230.0, 1000.0) for i in range(10)]
        self.assertEqual(voices.blips(her + gap + octave + [(1.55, None, 10.0), (1.6, None, 10.0), (1.65, None, 10.0)] + near), [])

    def test_unmuted_respects_cuts_mutes_and_silence(self):
        segments = [[1.0, 2.0], [5.0, 6.0]]
        self.assertEqual(voices.unmuted(segments, [[0.0, 3.0]], [[1.2, 1.8]]), [[1.0, 1.2], [1.8, 2.0]])
        self.assertEqual(voices.unmuted(segments, [[0.0, 10.0]], gain_db=-80), [])
        self.assertEqual(voices.unmuted(segments, [[2.5, 4.0]]), [])


class CaptionControlTests(unittest.TestCase):
    def candidate(self, captions, **plan):
        return {"id": "c01", "plan": {"cuts": [[10.0, 14.0], [20.0, 24.0]], "captions": captions} | plan}

    def test_same_position_captions_never_overlap(self):
        captions = [{"kind": "dialogue", "text": "그냥 가든 뷰 했는데", "at": 1.0, "duration": 3.0},
                    {"kind": "dialogue", "text": "마음에 너무 들어", "at": 2.0, "duration": 2.0},
                    {"kind": "variety", "text": "가든뷰", "at": 2.0, "duration": 2.0, "position": "top"}]
        timed, notes = caption_sync.sync_candidate(self.candidate(captions), {"kind": "video"}, [])
        first, second, top = timed["plan"]["captions"]
        self.assertLessEqual(first["at"] + first["duration"], second["at"])
        self.assertEqual((top["at"], top["duration"]), (2.0, 2.0))
        self.assertEqual([n["status"] for n in notes], ["separated"])

    def test_dialogue_only_mutes_everything_outside_the_lines(self):
        captions = [{"kind": "dialogue", "text": "안녕", "at": 1.0, "duration": 1.0, "sync": "manual"},
                    {"kind": "dialogue", "text": "다시 안녕", "at": 5.0, "duration": 1.0, "sync": "manual"}]
        timed, notes = caption_sync.sync_candidate(self.candidate(captions, original="dialogue_only"), {"kind": "video"}, [])
        self.assertEqual(timed["plan"]["mute"], [[10.0, 11.0], [12.0, 14.0], [20.0, 21.0], [22.0, 24.0]])
        self.assertEqual(notes[0]["status"], "gated")

    def test_soft_sentence_end_keeps_word_timing(self):
        words = [{"text": t, "start": s, "end": e} for t, s, e in [("칵테일을", 10.2, 11.0), ("마실", 11.0, 11.5), ("수", 11.5, 11.7),
                                                                    ("있는", 11.7, 12.0), ("것", 12.0, 12.2), ("같아요", 12.2, 13.0)]]
        # Only the loud start is voiced (10.5–11.5); the soft ending is not.
        voicing = {"hop_seconds": 0.05, "scores": [0.0] * 210 + [0.9] * 20 + [0.0] * 200}
        captions = [{"kind": "dialogue", "text": "칵테일을 마실 수 있는 것 같아요", "at": 0.0, "duration": 1.0}]
        timed, _ = caption_sync.sync_candidate(self.candidate(captions), {"kind": "video"}, words, voicing)
        caption = timed["plan"]["captions"][0]
        self.assertAlmostEqual(caption["at"] + caption["duration"], 13.3 - 10.0 + caption_sync.TAIL, delta=0.06)

    def test_long_sentence_keeps_its_spoken_length_and_reading_time(self):
        words = [{"text": t, "start": s, "end": e} for t, s, e in [
            ("이", 10.0, 10.2), ("리조트의", 10.2, 10.8), ("장점은", 10.8, 11.4), ("선셋을", 11.4, 12.0),
            ("보면서", 12.0, 12.6), ("수영과", 12.6, 13.2), ("칵테일", 13.2, 13.9)]]
        # The sentence is three voiced phrases (10.0–11.0, 11.6–12.6, 13.2–13.9) with pauses between them.
        voicing = {"hop_seconds": 0.05, "scores": [0.0] * 200 + [0.9] * 20 + [0.0] * 12 + [0.9] * 20 + [0.0] * 12
                   + [0.9] * 14 + [0.0] * 200}
        captions = [{"kind": "dialogue", "text": "이 리조트의 장점은 선셋을 보면서 수영과 칵테일", "at": 0.0, "duration": 1.0}]
        timed, _ = caption_sync.sync_candidate(self.candidate(captions), {"kind": "video"}, words, voicing)
        caption = timed["plan"]["captions"][0]
        self.assertGreaterEqual(caption["at"] + caption["duration"], 3.9 - 0.01)
        short = [{"kind": "dialogue", "text": "이 리조트의 장점은 선셋을 보면서 수영과 칵테일", "at": 0.0, "duration": 1.0}]
        words_short = [{"text": "이리조트의장점은선셋을보면서수영과칵테일", "start": 10.0, "end": 10.3}]
        timed, _ = caption_sync.sync_candidate(self.candidate(short), {"kind": "video"}, words_short)
        caption = timed["plan"]["captions"][0]
        self.assertGreaterEqual(caption["duration"], caption_sync.reading_seconds(short[0]["text"]) - 0.01)


if __name__ == "__main__":
    unittest.main()


class PreviewSoundTests(unittest.TestCase):
    STAGED = {"bgm-a": {"src": "work/run/audio/bgm-a.wav", "frames": 3000}}
    SPEECH = [{"start": 11.0, "end": 12.0}, {"start": 21.0, "end": 22.0}]

    def plan(self, **extra):
        return {"plan": {"cuts": [[10.0, 14.0], [20.0, 24.0]], "captions": [], "bgm": {"asset": "bgm-a", "gain_db": -9}} | extra}

    def bgm(self, candidate):
        import review
        return [c for c in review.audio_cues(candidate, {"kind": "video"}, 240, self.STAGED, self.SPEECH) if c["id"] == "bgm"][0]

    def test_bgm_does_not_duck_under_muted_or_silenced_lines(self):
        import review
        silenced = self.plan(original_gain_db=-80)
        self.assertEqual(review.audible_speech(silenced["plan"], self.SPEECH), [])
        # Only the track's own fade-in/out (-60 dB ends) and the base level; no ducking dips.
        self.assertEqual({db for _, db in self.bgm(silenced)["gain"]} - {-60}, {-9})
        muted = self.plan(mute=[[20.5, 22.5]])
        self.assertEqual(review.audible_speech(muted["plan"], self.SPEECH), [self.SPEECH[0]])
        self.assertLess(min(db for _, db in self.bgm(muted)["gain"]), -9)

    def test_bgm_offset_starts_the_track_later(self):
        candidate = self.plan()
        candidate["plan"]["bgm"]["offset"] = 90
        cue = self.bgm(candidate)
        self.assertEqual(cue["in"], 90 * 30)
        self.assertEqual(cue["duration"], 240)

    def test_sound_opens_only_while_she_speaks(self):
        words = [{"text": w, "start": 11.0 + i * 0.1, "end": 11.1 + i * 0.1} for i, w in enumerate(["렛츠", "고", "노을", "보러", "가요"])]
        captions = [{"kind": "dialogue", "text": "렛츠 고 노을 보러 가요", "at": 1.0, "duration": 0.5}]
        candidate = {"id": "c01", "plan": {"cuts": [[10.0, 14.0], [20.0, 24.0]], "captions": captions, "original": "dialogue_only"}}
        timed, _ = caption_sync.sync_candidate(candidate, {"kind": "video"}, words)
        caption = timed["plan"]["captions"][0]
        # The caption stays up for reading time, but the sound closes TAIL seconds after the last word.
        self.assertGreater(caption["at"] + caption["duration"], 1.5 + caption_sync.TAIL)
        opened_until = min(a for a, b in timed["plan"]["mute"] if a > 10.5)
        self.assertAlmostEqual(opened_until, 11.5 + caption_sync.TAIL, delta=0.01)
        self.assertNotIn("_spoken", caption)


class DuckEnvelopeTests(unittest.TestCase):
    def test_speech_over_the_whole_cue_keeps_ducked_music(self):
        import sound
        # A transcript line longer than the cue used to remove every inner point and silence the music.
        points = sound.duck_envelope(162, [[-50, 400]], base_db=-9)
        inner = [db for frame, db in points if 0 < frame < 161]
        self.assertTrue(inner)
        self.assertEqual(set(inner), {-9 - sound.DUCK_DEPTH_DB})
