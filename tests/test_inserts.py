"""Photo inserts over video and muted ranges of original sound (candidates, assemble, timeline v2)."""
import copy
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
import assemble
import common
import production
import review
import sound
from test_longform import ADOPT_TWO, LongformFixture, plan_candidates
from test_review import ENTRIES, candidates


def with_inserts():
    data = candidates()
    plan = data["candidates"][0]["plan"]
    plan["inserts"] = [{"photo": "p001", "at": 1.0, "duration": 3.0, "position": "left", "tilt": -4}]
    plan["mute"] = [[14.0, 15.0], [35.0, 40.0]]
    return data


class InsertContractTests(unittest.TestCase):
    def test_inserts_and_mutes_reach_the_preview(self):
        item = review.validate_candidates(with_inserts(), ENTRIES)[0]
        props = review.render_props(item, ENTRIES["v001"], photos={"p001": "photos/p001.jpg"})
        self.assertEqual(props["overlays"], [{"id": "ins-0", "src": "photos/p001.jpg", "from": 30, "duration": 90,
                                              "position": "left", "tilt": -4}])
        first, second = (s["gain"] for s in props["segments"])
        self.assertIn([60, -80], first)
        self.assertEqual(first[0], [0, 0])
        # 35–36 s is the last second of the second cut (30–36 s); the mute runs to the cut's end.
        self.assertEqual(second[-1], [179, -80])

    def test_bad_inserts_and_mutes_rejected(self):
        changes = [
            lambda p: p["inserts"][0].update(photo="v001"),
            lambda p: p["inserts"][0].update(photo="p999"),
            lambda p: p["inserts"][0].update(at=13.8),
            lambda p: p["inserts"][0].update(duration=20.0),
            lambda p: p["inserts"][0].update(position="center"),
            lambda p: p["inserts"][0].update(tilt=30),
            lambda p: p["mute"].append([5.0, 6.0]),
            lambda p: p["mute"].append([20.0, 20.01]),
            lambda p: p["mute"].append([20.0]),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                data = with_inserts()
                change(data["candidates"][0]["plan"])
                with self.assertRaises(ValueError):
                    review.validate_candidates(data, ENTRIES)
        photo = with_inserts()
        photo["candidates"][1]["plan"]["mute"] = [[0.0, 1.0]]
        with self.assertRaisesRegex(ValueError, "only video"):
            review.validate_candidates(photo, ENTRIES)

    def test_mute_envelope_fades_and_stays_valid(self):
        points = sound.mute_envelope(100, [[30, 50]])
        self.assertEqual(points, [[0, 0], [26, 0], [30, -80], [50, -80], [54, 0], [99, 0]])
        production._gain(points, 100)
        production._gain(sound.mute_envelope(100, [[0, 10], [95, 120]], base_db=-3), 100)
        self.assertEqual(sound.mute_envelope(100, []), [[0, 0], [99, 0]])
        self.assertEqual(sound.map_mutes([[10, 20], [30, 40]], 1, [[15, 32]]), [[[150, 300]], [[0, 60]]])


class InsertAssembleTests(LongformFixture):
    def test_assembled_timeline_carries_overlays_and_muted_sound(self):
        data = plan_candidates()
        data["candidates"][0]["plan"]["inserts"] = [{"photo": "p001", "at": 0.5, "duration": 1.5, "position": "right", "tilt": 3}]
        data["candidates"][0]["plan"]["mute"] = [[0.2, 0.9]]
        self.review_and_select(ADOPT_TWO, candidates=data)
        assemble.assemble(self.run_id)
        timeline = common.read_json(self.run / "timeline.json")
        self.assertEqual(timeline["overlays"], [{"id": "c01-p0", "source": "p001", "from": 105, "duration": 45,
                                                 "position": "right", "tilt": 3}])
        cues = {c["id"]: c for c in timeline["audio"]}
        self.assertIn([6, -80], cues["c01-o0"]["gain_db"])
        # The only transcribed line is muted, so the BGM keeps its level instead of ducking.
        self.assertNotIn(-30, [db for _, db in cues["bgm-0"]["gain_db"]])

    def test_silenced_original_does_not_duck_the_bgm(self):
        data = plan_candidates()
        data["candidates"][0]["plan"]["original_gain_db"] = -80
        self.review_and_select(ADOPT_TWO, candidates=data)
        assemble.assemble(self.run_id)
        cues = {c["id"]: c for c in common.read_json(self.run / "timeline.json")["audio"]}
        self.assertEqual({db for _, db in cues["c01-o0"]["gain_db"]}, {-80})
        self.assertNotIn(-30, [db for _, db in cues["bgm-0"]["gain_db"]])

    def test_timeline_rejects_bad_overlays(self):
        self.review_and_select(ADOPT_TWO)
        assemble.assemble(self.run_id)
        timeline = common.read_json(self.run / "timeline.json")
        sources = assemble.source_map(review.read_entries(self.run), [])
        sources |= {c["source"]: {"kind": "audio", "frames": 3000} for c in timeline["audio"] if c["kind"] != "original"}
        good = {"id": "o1", "source": "p001", "from": 0, "duration": 30, "position": "left", "tilt": 0}
        production.validate_timeline_v2(timeline | {"overlays": [good]}, sources)
        for bad in [{"source": "v001"}, {"position": "top"}, {"tilt": 15}, {"from": timeline["duration_frames"]},
                    {"id": timeline["clips"][0]["id"]}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                production.validate_timeline_v2(timeline | {"overlays": [good | bad]}, sources)


if __name__ == "__main__":
    unittest.main()
