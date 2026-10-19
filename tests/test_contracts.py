import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import audio_eligibility, safe_path, validate_timeline, write_json, run_lock, require_run
import common
import synthetic

PROJECT_CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/project.json').read_text())


def fixture():
    manifest = {"assets": {"video": {"frames": 90}, "photo": {}, "bgm": {"frames": 120}, "sfx": {"frames": 15}}}
    timeline = {"schema_version": 1, "purpose": "synthetic_setup", "fps": 30, "width": 1280, "height": 720,
        "duration_frames": 120,
        "clips": [{"id": "v", "asset": "video", "from": 0, "duration": 90}, {"id": "p", "asset": "photo", "from": 90, "duration": 30}],
        "audio": [{"id": "a", "asset": "video", "audio_track": 1, "from": 0, "duration": 90, "gain_db": [[0, -6], [89, -6]]}],
        "captions": [{"id": "c", "from": 0, "duration": 30, "kind": "editorial", "text": "synthetic"}]}
    return timeline, manifest


class ContractTests(unittest.TestCase):
    def test_content_driven_duration(self):
        t, m = fixture()
        self.assertEqual(validate_timeline(t, m), 120)
        t["clips"][-1]["duration"] = 90
        t["duration_frames"] = 180
        self.assertEqual(validate_timeline(t, m), 180)

    def test_invalid_edits_rejected(self):
        changes = [
            lambda t: t.update(duration_frames=300),
            lambda t: t["clips"][0].update(trim=30),
            lambda t: t["audio"][0].update(audio_track=2),
            lambda t: t["audio"].append(dict(t["audio"][0], id="duplicate-original")),
            lambda t: t["captions"][0].update(duration=200),
            lambda t: t["audio"][0].update(gain_db=[[0, -6], [89, float("nan")]]),
            lambda t: t.update(purpose="production"),
        ]
        for change in changes:
            with self.subTest(change=change):
                t, m = fixture()
                change(t)
                with self.assertRaises(ValueError):
                    validate_timeline(t, m)

    def test_path_aliases_and_overwrite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "original.txt").write_text("preserve")
            (root / "alias").symlink_to(root / "original.txt")
            for relative in ["../escape", "/tmp/escape", "alias"]:
                with self.assertRaises(ValueError):
                    safe_path(root, relative)
            with self.assertRaises(FileExistsError):
                write_json(root / "original.txt", {})
            self.assertEqual((root / "original.txt").read_text(), "preserve")
            os.link(root / 'original.txt', root / 'hard-alias.txt')
            with self.assertRaises(ValueError):
                safe_path(root, 'hard-alias.txt')
            with run_lock(root):
                with self.assertRaises(FileExistsError):
                    with run_lock(root):
                        pass

    def test_original_audio_maps_once_per_video_clip(self):
        t, m = fixture()
        t['clips'] = [
            {'id':'v1','asset':'video','from':0,'duration':45},
            {'id':'v2','asset':'video','from':45,'duration':45,'trim':45},
            t['clips'][1],
        ]
        first = {'id':'a1','asset':'video','audio_track':1,'from':0,'duration':45,
                 'gain_db':[[0,-6],[44,-6]]}
        t['audio'] = [first, dict(first, id='a2')]
        with self.assertRaises(ValueError):
            validate_timeline(t, m)
        t['audio'][1].update({'from':45, 'trim':45})
        self.assertEqual(validate_timeline(t, m), 120)

    def test_real_run_rejected_before_read(self):
        for name in ["episode-001", "synthetic-../../raw", "../raw"]:
            with self.assertRaises(ValueError):
                require_run(name)

    def test_audio_policy_unknown_is_not_clear(self):
        base = {"free": True, "allowed_platforms": ["youtube", "instagram", "tiktok"],
                "license_status": "verified", "license_evidence": "fixture://license",
                "claim_status": "documented_low_risk", "claim_evidence": "fixture://rights-holder",
                "attribution_satisfied": True, "platform_check": "not_checked"}
        self.assertTrue(audio_eligibility(base)[0])
        for update in [{"claim_status": "unknown"}, {"known_claim": True}, {"requires_whitelist": True},
                       {"allowed_platforms": ["youtube"]}, {"free": False}, {"attribution_satisfied": False},
                       {"license_evidence": ""}, {"claim_evidence": ""}]:
            with self.subTest(update=update):
                candidate = copy.deepcopy(base)
                candidate.update(update)
                self.assertFalse(audio_eligibility(candidate)[0])

    def test_resume_checks_inputs_outputs_and_partial_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run = root / 'work/synthetic-unit'
            (run / 'assets').mkdir(parents=True)
            (root / 'config').mkdir()
            common.write_json(root / 'config/project.json', PROJECT_CONFIG)
            timeline, manifest = fixture()
            manifest['owner'] = common.OWNER
            for key, asset in manifest['assets'].items():
                asset['file'] = key + '.txt'
                source = run / 'assets' / asset['file']
                source.write_text('synthetic placeholder for state tests')
                asset['sha256'] = common.digest(source)
            common.write_json(run / 'fixture-manifest.json', manifest)
            common.write_json(run / 'brief.json', {'purpose':'synthetic_setup','source_roots':[], 'resolved_config':PROJECT_CONFIG})
            common.write_json(run / 'timeline.json', timeline)
            names = ['preview.mp4','frame.png','verify.json','audio-credits.md']
            for name in names:
                (run / name).write_text('state verification fixture')
            with patch.object(common, 'ROOT', root):
                state = {'owner':common.OWNER,'run_id':run.name,'stage':'synthetic_encoded_output','status':'succeeded','input_fingerprint':common.input_fingerprint(run),
                         'outputs':{name:common.digest(run / name) for name in names}}
                common.write_json(run / 'state.json', state)
                with patch.object(synthetic, 'run_command', side_effect=AssertionError('must not rerender')):
                    self.assertEqual(synthetic.render('synthetic-unit')['status'],'succeeded')
                timeline['captions'][0]['text'] = 'edited'
                common.write_json(run / 'timeline.json', timeline, replace=True)
                self.assertEqual(synthetic.status('synthetic-unit')['status'],'stale')
                state['input_fingerprint'] = common.input_fingerprint(run)
                state['status'] = 'running'
                common.write_json(run / 'state.json', state, replace=True)
                with self.assertRaises(ValueError):
                    synthetic.render('synthetic-unit')
                state['status'] = 'succeeded'
                common.write_json(run / 'state.json', state, replace=True)
                (run / 'preview.mp4').write_text('changed output')
                self.assertEqual(synthetic.status('synthetic-unit')['status'],'stale')
                (run / 'assets/unregistered.txt').write_text('not a registered fixture')
                with self.assertRaises(ValueError):
                    common.validate_run('synthetic-unit')


if __name__ == "__main__":
    unittest.main()
