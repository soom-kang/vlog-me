"""Features from the first-sample feedback: caption timing, preset variation, photo stacks, effects, music audition."""
import copy
import json
import math
import random
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import analyze
import assemble
import audio_library
import caption_sync
import common
import production
import render_prod
import review
from test_longform import ADOPT_TWO, LongformFixture, plan_candidates
from test_production import edit_fixture
from test_sound import fake_measure, fields

# Words as the word-level Whisper pass reports them (source seconds).
WORDS = [{"text": w, "start": s, "end": e} for w, s, e in [
    ("미두", 22.0, 22.3), ("스파?", 22.6, 24.8), ("지금", 27.0, 27.3), ("마사지고", 27.3, 27.9), ("나발이고", 27.9, 28.9),
    ("호텔을", 28.9, 29.9), ("가고", 30.6, 31.3), ("싶어", 31.3, 32.0)]]


def hotel_candidate(**caption):
    return {"id": "c10", "plan": {"cuts": [[22.3, 34.0]], "captions": [
        {"kind": "dialogue", "text": "지금 마사지고 나발이고\n호텔을 가고 싶어", "at": 3.7, "duration": 3.4} | caption,
        {"kind": "variety", "text": "오늘의 결론: 호텔", "at": 9.0, "duration": 2.0, "position": "top"}]}}


class CaptionSyncTests(unittest.TestCase):
    def test_dialogue_snaps_to_spoken_words(self):
        timed, notes = caption_sync.sync_candidate(hotel_candidate(), {"kind": "video"}, WORDS)
        caption = timed["plan"]["captions"][0]
        self.assertAlmostEqual(caption["at"], 27.0 - 22.3 - caption_sync.LEAD, places=2)
        self.assertAlmostEqual(caption["at"] + caption["duration"], 32.0 - 22.3 + caption_sync.TAIL, places=2)
        self.assertEqual(notes[0]["status"], "synced")
        self.assertEqual(notes[0]["authored"], [3.7, 7.1])
        self.assertEqual(timed["plan"]["captions"][1]["at"], 9.0)

    def test_manual_unmatched_and_cut_edges(self):
        timed, notes = caption_sync.sync_candidate(hotel_candidate(sync="manual"), {"kind": "video"}, WORDS)
        self.assertEqual((timed["plan"]["captions"][0]["at"], notes), (3.7, []))
        timed, notes = caption_sync.sync_candidate(hotel_candidate(text="전혀 다른 문장이에요"), {"kind": "video"}, WORDS)
        self.assertEqual(notes[0]["status"], "unmatched")
        short = hotel_candidate()
        short["plan"]["cuts"] = [[22.3, 30.0]]
        timed, _ = caption_sync.sync_candidate(short, {"kind": "video"}, WORDS)
        caption = timed["plan"]["captions"][0]
        self.assertLessEqual(caption["at"] + caption["duration"], 30.0 - 22.3 + 1e-6)
        photo, notes = caption_sync.sync_candidate(hotel_candidate(), {"kind": "photo"}, WORDS)
        self.assertEqual((photo["plan"]["captions"][0]["at"], notes), (3.7, []))

    def test_voicing_moves_caption_to_real_speech(self):
        # Whisper says 27.0s, but the voice really starts at 28.25s (street noise before it).
        scores = [0.1] * int(28.25 / 0.05) + [0.8] * int(3.6 / 0.05) + [0.1] * 100
        voicing = {"hop_seconds": 0.05, "scores": scores}
        timed, notes = caption_sync.sync_candidate(hotel_candidate(), {"kind": "video"}, WORDS, voicing)
        caption = timed["plan"]["captions"][0]
        self.assertTrue(notes[0]["voiced"])
        self.assertAlmostEqual(caption["at"], 28.25 - 22.3 - caption_sync.LEAD, delta=0.06)
        self.assertAlmostEqual(caption["at"] + caption["duration"], 31.85 - 22.3 + caption_sync.TAIL, delta=0.06)

    def test_voiced_phrases_follow_cuts(self):
        voicing = {"hop_seconds": 0.05, "scores": [0.0] * 200 + [0.9] * 60 + [0.0] * 200 + [0.9] * 40 + [0.0] * 100}
        # Source 10–13 s and 23–25 s are voiced; cutting 11–13 and 23–24 joins them into one edited phrase.
        self.assertEqual([[round(a, 2), round(b, 2)] for a, b in caption_sync.voiced_phrases(voicing, [[11, 13], [23, 24]], 1)],
                         [[0.0, 3.0]])
        self.assertIsNone(caption_sync.snap(0.0, 1.0, "짧은 말", []))

    def test_voicing_scores_separate_tone_from_noise(self):
        rng = random.Random(7)
        noise = [int(rng.gauss(0, 1500)) for _ in range(4000)]
        tone = [int(6000 * math.sin(2 * math.pi * 220 * i / 8000)) for i in range(4000)]
        scores = analyze.voicing_scores(noise + tone)
        self.assertLess(max(scores[:8]), 0.45)
        self.assertGreater(min(scores[-6:]), 0.8)

    def test_word_pass_parsing(self):
        payload = {"transcription": [{"text": " 지금", "offsets": {"from": 27000, "to": 27300}},
                                     {"text": " ", "offsets": {"from": 27300, "to": 27400}},
                                     {"text": "싶어", "offsets": {"from": 31300, "to": 31300}}]}
        self.assertEqual(analyze.parse_words(payload), [{"text": "지금", "start": 27.0, "end": 27.3}])


class PresetTests(unittest.TestCase):
    def test_sub_line_and_sync_fields(self):
        production.validate_caption_text({"kind": "mood", "preset": "editorial", "text": "노을이 지는 시간", "sub": "golden hour"})
        for bad in [{"sub": ""}, {"sub": "x" * 40}, {"sync": "auto"}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                production.validate_caption_text({"kind": "mood", "preset": "editorial", "text": "노을"} | bad)

    def test_variation_warnings(self):
        same = [{"kind": "situation", "preset": "box-yellow", "from": i} for i in range(4)]
        warnings = production.preset_warnings(same)
        self.assertTrue(any("연달아" in w for w in warnings))
        self.assertTrue(any("모두 'box-yellow'" in w for w in warnings))
        mixed = [{"kind": "situation", "preset": p, "from": i} for i, p in enumerate(["box-yellow", "sticker", "box-pink", "ribbon"])]
        self.assertEqual(production.preset_warnings(mixed), [])

    def test_title_box_has_many_variants(self):
        self.assertGreaterEqual(len(production.CAPTION_REGISTRY["kinds"]["situation"]["presets"]), 8)
        self.assertGreaterEqual(len(production.CAPTION_REGISTRY["kinds"]["mood"]["presets"]), 5)


class TimelineEffectTests(unittest.TestCase):
    def test_effects_and_stacks_validate(self):
        timeline, sources = edit_fixture()
        sources |= {"p2": {"kind": "image"}, "p3": {"kind": "image"}}
        timeline["effects"] = [{"id": "fx1", "type": "punch_zoom", "from": 10, "duration": 15, "strength": 1.5},
                               {"id": "fx2", "type": "speedlines", "from": 30, "duration": 40}]
        timeline["overlays"] = [{"id": "st1", "style": "stack", "sources": ["p1", "p2", "p3"], "from": 0, "duration": 60,
                                 "interval": 10, "position": "center"}]
        self.assertEqual(production.validate_timeline_v2(timeline, sources), 240)
        for change in [lambda t: t["effects"][0].update(type="spin"), lambda t: t["effects"][0].update(strength=5),
                       lambda t: t["effects"][1].update(id="fx1"), lambda t: t["overlays"][0].update(sources=["p1"]),
                       lambda t: t["overlays"][0].update(sources=["p1", "v1"]), lambda t: t["overlays"][0].update(interval=1),
                       lambda t: t["overlays"][0].update(position="top")]:
            broken = copy.deepcopy(timeline)
            change(broken)
            with self.subTest(change=change), self.assertRaises(ValueError):
                production.validate_timeline_v2(broken, sources)


class FeedbackRunTests(LongformFixture):
    def setUp(self):
        super().setUp()
        for values in [fields(asset_id="sfx-shutter", file="assets/audio/user/sfx-shutter.wav"),
                       fields(asset_id="bgm-sunset", kind="bgm", file="assets/audio/user/bgm-sunset.wav", moods=["warm"])]:
            (self.root / values["file"]).write_text(f"audio {values['id']}")
            with patch.object(audio_library, "run_command", side_effect=fake_measure):
                audio_library.register(values)
        for name in ["IMG_0002.HEIC", "IMG_0003.HEIC"]:
            (self.root / "sources/trip" / name).write_text(f"original {name}")

    def candidates(self):
        data = plan_candidates()
        c01 = data["candidates"][0]
        c01["plan"]["effects"] = [{"type": "shake", "at": 1.0, "duration": 0.5}, {"type": "flash", "at": 0.2, "duration": 0.3}]
        c01["plan"]["bgm_options"] = ["bgm-walk", "bgm-sunset"]
        c01["plan"]["inserts"] = [{"photos": ["p001", "p001"], "at": 0.5, "duration": 1.5, "interval": 0.2, "sfx": "sfx-shutter"}]
        c01["plan"]["captions"].append({"kind": "mood", "preset": "editorial", "text": "그래도 좋았다", "sub": "anyway", "at": 0.1,
                                        "duration": 1.0})
        return data

    def test_review_renders_audition_variants_and_stack_sounds(self):
        common.write_json(self.run / "candidates.json", self.candidates())
        with patch.object(review, "run_command", side_effect=self.media):
            review.build(self.run_id)
        folder = self.run / "review/v1"
        jobs = {j["id"]: j for j in common.read_json(folder / "render-input.json")["jobs"]}
        self.assertEqual(sorted(jobs), ["c01", "c01--bgm-sunset", "c01--bgm-walk", "c02", "c03"])
        self.assertFalse(jobs["c01--bgm-sunset"]["still"])
        bgm = [c for c in jobs["c01--bgm-sunset"]["props"]["audio"] if c["id"] == "bgm"][0]
        self.assertIn("bgm-sunset", bgm["src"])
        props = jobs["c01"]["props"]
        self.assertEqual([c["id"] for c in props["audio"] if c["id"].startswith("stack-")], ["stack-0-0", "stack-0-1"])
        self.assertEqual(props["overlays"][0]["style"], "stack")
        self.assertEqual([e["type"] for e in props["effects"]], ["shake", "flash"])
        self.assertEqual([c["sub"] for c in props["captions"] if c["kind"] == "mood"], ["anyway"])
        page = (folder / "index.html").read_text(encoding="utf-8")
        self.assertIn("음악 비교", page)
        self.assertIn("c01--bgm-sunset/preview.mp4", page)

    def test_assemble_carries_effects_stacks_and_shutters(self):
        self.review_and_select(ADOPT_TWO, candidates=self.candidates())
        assemble.assemble(self.run_id)
        timeline = common.read_json(self.run / "timeline.json")
        self.assertEqual([e["type"] for e in timeline["effects"]], ["shake", "flash"])
        stack = [o for o in timeline["overlays"] if o.get("style") == "stack"][0]
        self.assertEqual((stack["sources"], stack["interval"]), (["p001", "p001"], 6))
        shutters = [a for a in timeline["audio"] if a.get("source") == "sfx-shutter"]
        self.assertEqual([a["from"] - shutters[0]["from"] for a in shutters], [0, 6])
        self.assertNotIn("sfx-shutter repeats", (self.run / "assemble-report.md").read_text(encoding="utf-8"))

    def test_vertical_sources_carry_aspect_for_blurred_backdrop(self):
        self.assertAlmostEqual(review.display_aspect({"display_size": [1080, 1920]}), 0.5625)
        self.assertAlmostEqual(review.display_aspect({}), 16 / 9, places=3)
        self.review_and_select(ADOPT_TWO, candidates=self.candidates())
        assemble.assemble(self.run_id)
        clip = common.read_json(self.run / "timeline.json")["clips"][1]
        self.assertIn("aspect", clip)

    def test_vertical_video_gets_a_blurred_fill_proxy(self):
        self.assertIn("crop=608:1080:656:0", review.fill_filter(0.5625))
        self.assertIn("crop=1920:822:0:129", review.fill_filter(2.3333))
        # The blurred background is averaged over time so moving highlights do not make it pulse.
        self.assertIn(f"tmix=frames={review.FILL_SMOOTH}", review.fill_filter(0.5625))
        entry = review.read_entries(self.run)["v001"]
        self.assertIs(review.filled(self.run, entry), entry)
        tall = entry | {"id": "v009", "display_size": [1080, 1920], "has_audio": True}
        with patch.object(review, "run_command", side_effect=self.media):
            filled = review.filled(self.run, tall)
        self.assertEqual((filled["proxy"], filled["display_size"]), (f"proxy/fill/v009-v{review.FILL_VERSION}.mp4", [16, 9]))
        self.assertTrue((self.run / f"proxy/fill/v009-v{review.FILL_VERSION}.mp4").is_file())
        with patch.object(review, "run_command", side_effect=AssertionError("cached")):
            self.assertEqual(review.filled(self.run, tall)["proxy"], f"proxy/fill/v009-v{review.FILL_VERSION}.mp4")

    def test_photos_get_a_baked_fill_and_videos_can_be_deflickered(self):
        commands = []

        def record(command, *args, **kwargs):
            commands.append(command)
            return self.media(command, *args, **kwargs)

        entries = review.read_entries(self.run)
        photo = entries["p001"] | {"display_size": [3024, 4032]}
        video = entries["v001"] | {"has_audio": True}
        with patch.object(review, "run_command", side_effect=record):
            filled = review.filled(self.run, photo)
            clean = review.deflickered(self.run, video)
        name = f"photos/fill/p001-v{review.PHOTO_FILL_VERSION}.jpg"
        self.assertEqual((filled["proxy"], filled["display_size"]), (name, [16, 9]))
        self.assertIn(review.PHOTO_FILL_FILTER, commands[0])
        self.assertEqual(clean["proxy"], f"proxy/clean/v001-deflicker-v{review.DEFLICKER_VERSION}.mp4")
        self.assertIn(review.DEFLICKER_FILTER, commands[1])
        # The final render gets the baked photo and tells the renderer not to draw a CSS blur behind it.
        timeline = {"clips": [{"source": "p001", "aspect": 0.75}, {"source": "v001", "deflicker": True}]}
        with patch.object(review, "run_command", side_effect=AssertionError("cached")):
            props = render_prod.render_props(self.run, timeline, {"p001": photo, "v001": video}, {})
        self.assertEqual(props["assets"]["p001"]["src"], name)
        self.assertEqual(props["assets"]["v001"]["src"], clean["proxy"])
        self.assertAlmostEqual(props["timeline"]["clips"][0]["aspect"], review.WIDE)
        self.assertEqual(timeline["clips"][0]["aspect"], 0.75)

    def test_bad_audition_and_stack_fields_rejected(self):
        entries = review.read_entries(self.run)
        for change in [lambda p: p.update(bgm_options=["bgm-walk"]), lambda p: p.update(bgm_options=["bgm-walk", "sfx-boing"]),
                       lambda p: p["inserts"][0].update(photos=["p001"]), lambda p: p["inserts"][0].update(photos=["p001", "v001"]),
                       lambda p: p["inserts"][0].update(position="top"), lambda p: p["effects"][0].update(type="spin")]:
            data = self.candidates()
            change(data["candidates"][0]["plan"])
            with self.subTest(change=change), self.assertRaises(ValueError):
                review.validate_candidates(data, entries)


if __name__ == "__main__":
    unittest.main()
