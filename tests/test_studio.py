from http.client import HTTPResponse
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common
import studio
from test_contracts import fixture

PROJECT_CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config/project.json").read_text())


class MemorySocket:
    def __init__(self, data):
        self.data = data
        self.sent = bytearray()

    def makefile(self, *_args, **_kwargs):
        return io.BytesIO(self.data)

    def sendall(self, data):
        self.sent.extend(data)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="vlog-preview-test-", dir="/private/tmp")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        patcher = patch.object(common, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "config").mkdir()
        common.write_json(self.root / "config/project.json", PROJECT_CONFIG)
        self.run_id = "synthetic-viewer-test"
        self.run = self.root / "work" / self.run_id
        (self.run / "assets").mkdir(parents=True)
        timeline, manifest = fixture()
        manifest["owner"] = common.OWNER
        for name, asset in manifest["assets"].items():
            asset["file"] = name + ".txt"
            source = self.run / "assets" / asset["file"]
            source.write_text("synthetic text fixture")
            asset["sha256"] = common.digest(source)
        common.write_json(self.run / "fixture-manifest.json", manifest)
        common.write_json(self.run / "timeline.json", timeline)
        common.write_json(self.run / "brief.json", {
            "purpose": "synthetic_setup", "source_roots": [], "resolved_config": PROJECT_CONFIG})
        self.video = bytes(range(256))
        (self.run / "preview.mp4").write_bytes(self.video)
        for name in ["verify.json", "frame.png", "audio-credits.md"]:
            (self.run / name).write_text("synthetic test output")
        self.state = {"owner": common.OWNER, "run_id": self.run_id,
                      "stage": "synthetic_encoded_output", "status": "succeeded",
                      "input_fingerprint": common.input_fingerprint(self.run),
                      "outputs": {name:common.digest(self.run / name) for name in
                                  ["preview.mp4", "frame.png", "verify.json", "audio-credits.md"]}}
        common.write_json(self.run / "state.json", self.state)

    def request(self, method="GET", target="/", headers=None):
        lines = {"Host":"127.0.0.1:8765", **(headers or {})}
        data = (f"{method} {target} HTTP/1.0\r\n" + "".join(f"{k}: {v}\r\n" for k,v in lines.items()) + "\r\n").encode()
        connection = MemorySocket(data)
        studio.handler_for(self.run_id, self.video)(connection, ("127.0.0.1", 1), SimpleNamespace(server_port=8765))
        response = HTTPResponse(MemorySocket(bytes(connection.sent)), method=method)
        response.begin()
        return response, response.read()

    def test_verified_snapshot_reads_without_mutations_or_commands(self):
        before = {p: (p.read_bytes(),p.stat().st_mtime_ns) for p in self.run.rglob('*') if p.is_file()}
        with patch('subprocess.Popen', side_effect=AssertionError('No command may run')):
            self.assertEqual(studio.load_preview(self.run_id), self.video)
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.run.rglob('*') if p.is_file()})
        self.assertFalse((self.run / '.lock').exists())

    def test_pending_failed_stale_locked_and_wrong_scope_are_rejected(self):
        for stage, state in [('prepared','pending'),('render','failed'),('render','paused')]:
            with self.subTest(state=state):
                common.write_json(self.run / 'state.json',{**self.state,'stage':stage,'status':state},replace=True)
                with self.assertRaisesRegex(ValueError,'verified succeeded'):
                    studio.load_preview(self.run_id)
        common.write_json(self.run / 'state.json',self.state,replace=True)
        (self.run / '.lock').write_text('123')
        with self.assertRaisesRegex(ValueError,'locked'):
            studio.load_preview(self.run_id)
        (self.run / '.lock').unlink()
        (self.run / 'timeline.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'stale'):
            studio.load_preview(self.run_id)
        common.write_json(self.root / 'config/project.json',{**PROJECT_CONFIG,'audio_downloads':True},replace=True)
        with self.assertRaisesRegex(ValueError,'Setup cannot'):
            studio.load_preview(self.run_id)

    def test_changed_output_and_symlink_are_rejected(self):
        (self.run / 'preview.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'stale'):
            studio.load_preview(self.run_id)
        (self.run / 'preview.mp4').unlink()
        outside = self.root / 'outside.mp4'
        outside.write_bytes(self.video)
        (self.run / 'preview.mp4').symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'stale'):
            studio.load_preview(self.run_id)

    def test_post_validation_change_and_oversized_snapshot_rejected(self):
        with patch.object(studio,'status',return_value=self.state):
            (self.run / 'preview.mp4').write_bytes(b'changed after status')
            with self.assertRaisesRegex(ValueError,'changed while loading'):
                studio.load_preview(self.run_id)
            with patch.object(studio,'MAX_PREVIEW_BYTES',2):
                with self.assertRaisesRegex(ValueError,'128 MiB'):
                    studio.load_preview(self.run_id)

    def test_page_is_native_video_with_no_script_form_or_remote_resources(self):
        response, body = self.request()
        self.assertEqual(response.status,200)
        self.assertIn(b'<video controls',body)
        for forbidden in [b'<script',b'<form',b'remotion',b'Generate with agent',b'https://']:
            self.assertNotIn(forbidden,body)
        self.assertIn("default-src 'none'",response.getheader('Content-Security-Policy'))
        self.assertEqual(response.getheader('Cache-Control'),'no-store')

    def test_media_get_head_and_byte_ranges(self):
        cases = [(None,200,self.video),('bytes=2-5',206,self.video[2:6]),
                 ('bytes=253-',206,self.video[253:]),('bytes=-3',206,self.video[-3:]),
                 ('bytes=254-999',206,self.video[254:])]
        for requested, code, expected in cases:
            with self.subTest(requested=requested):
                headers={'Range':requested} if requested else {}
                response,body=self.request(target='/preview.mp4',headers=headers)
                self.assertEqual((response.status,body),(code,expected))
                self.assertEqual(int(response.getheader('Content-Length')),len(expected))
                head,body=self.request('HEAD','/preview.mp4',headers)
                self.assertEqual((head.status,body),(code,b''))

    def test_invalid_ranges_are_rejected(self):
        for value in ['bytes=999-','bytes=8-2','bytes=-0','bytes=-','bytes=0-1,3-4','items=0-1','bytes='+'9'*5000+'-']:
            with self.subTest(value=value):
                response,body=self.request(target='/preview.mp4',headers={'Range':value})
                self.assertEqual((response.status,body),(416,b''))

    def test_routes_do_not_expose_project_assets_or_write_apis(self):
        for target in ['/api/ai/execute','/api/update-default-props','/api/render','/api/install-package',
                       '/api/transcribe','/ws','/CLAUDE.md','/state.json','/assets/video.mp4',
                       '/../config/project.json','/%2e%2e/config/project.json','/preview.mp4?path=secret','//preview.mp4/']:
            with self.subTest(target=target), patch('builtins.open',side_effect=AssertionError('HTTP must not open files')):
                response,_=self.request(target=target)
                self.assertEqual(response.status,404)
        for method in ['POST','PUT','PATCH','DELETE','OPTIONS']:
            with self.subTest(method=method):
                response,body=self.request(method,'/api/ai/execute')
                self.assertEqual((response.status,body),(405,b''))
                self.assertEqual(response.getheader('Allow'),'GET, HEAD')

    def test_foreign_host_origin_and_websocket_are_rejected(self):
        for headers,code in [({'Host':'attacker.example'},403),({'Origin':'https://attacker.example'},403),
                             ({'Upgrade':'websocket'},400)]:
            with self.subTest(headers=headers):
                response,_=self.request(headers=headers)
                self.assertEqual(response.status,code)

    def test_main_binds_loopback_and_no_longer_starts_native_studio(self):
        with (patch.object(studio,'PreviewServer') as server,
              patch('subprocess.Popen',side_effect=AssertionError('No child')),
              redirect_stdout(io.StringIO())):
            server.return_value.__enter__.return_value.server_port=8765
            server.return_value.__enter__.return_value.serve_forever.side_effect=KeyboardInterrupt
            self.assertEqual(studio.main([self.run_id]),0)
            self.assertEqual(server.call_args.args[0],('127.0.0.1',0))
            server.return_value.__exit__.assert_called_once()

    def test_binding_does_not_resolve_hosts(self):
        server = SimpleNamespace(server_address=('127.0.0.1',8765))
        with (patch.object(studio.TCPServer,'server_bind') as bind,
              patch('socket.getfqdn',side_effect=AssertionError('No DNS lookup'))):
            studio.PreviewServer.server_bind(server)
        bind.assert_called_once_with(server)
        self.assertEqual((server.server_name,server.server_port),('127.0.0.1',8765))

    def test_refresh_exits_before_read_or_write(self):
        with patch.object(studio,'load_preview') as load, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                studio.main(['--refresh',self.run_id])
            self.assertEqual(exc.exception.code,2)
            load.assert_not_called()

    def test_stop_signal_is_not_swallowed_by_selectors(self):
        with self.assertRaises(KeyboardInterrupt):
            studio.interrupted(15,None)


if __name__ == '__main__':
    unittest.main()
