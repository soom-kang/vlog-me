import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from doctor import verify_skill_integrity

PROJECT = Path(__file__).resolve().parents[1]


class StartupTests(unittest.TestCase):
    def skill_fixture(self, root):
        base = root / '.claude/skills/remotion-best-practices'
        base.mkdir(parents=True)
        (base / 'SKILL.md').write_text('synthetic skill fixture')
        (root / 'config').mkdir()
        lock = {'skills':[{'path':str(base.relative_to(root)), 'files':{
            'SKILL.md':hashlib.sha256((base / 'SKILL.md').read_bytes()).hexdigest()}}]}
        (root / 'config/skills-lock.json').write_text(json.dumps(lock))
        return base

    def test_skill_tampering_and_unregistered_files_rejected(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root = Path(tmp)
            base = self.skill_fixture(root)
            verify_skill_integrity(root)
            original = (base / 'SKILL.md').read_text()
            (base / 'SKILL.md').write_text('changed')
            with self.assertRaises(ValueError):
                verify_skill_integrity(root)
            (base / 'SKILL.md').write_text(original)
            (base / 'extra.md').write_text('unregistered reference')
            with self.assertRaises(ValueError):
                verify_skill_integrity(root)
            (base / 'extra.md').unlink()
            extra = root / '.claude/skills/unregistered'
            extra.mkdir()
            (extra / 'SKILL.md').write_text('unregistered entrypoint')
            with self.assertRaises(ValueError):
                verify_skill_integrity(root)

    def test_integrity_checks_survive_python_optimization(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root = Path(tmp)
            base = self.skill_fixture(root)
            (base / 'SKILL.md').write_text('changed')
            code = ('import sys; from pathlib import Path; '
                    f'sys.path.insert(0,{str(PROJECT / "scripts")!r}); '
                    'from doctor import verify_skill_integrity; '
                    'verify_skill_integrity(Path(sys.argv[1]))')
            result = subprocess.run([sys.executable, '-O', '-c', code, str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Skill file hash mismatch', result.stderr)

    def test_claude_launcher_inherits_local_node_and_project(self):
        # A fake Claude binary proves launcher environment without calling a model.
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            for name in ['claude.sh', 'env.sh']:
                shutil.copy2(PROJECT / 'scripts' / name, root / 'scripts' / name)
            binaries = root / '.tools/node-v24.22.0-darwin-arm64/bin'
            binaries.mkdir(parents=True)
            for name in ['node', 'claude']:
                p = binaries / name
                p.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$(command -v node)" "$*"\n')
                p.chmod(0o755)
            result = subprocess.run(['/bin/bash', str(root / 'scripts/claude.sh'), '--version'],
                                    cwd='/private/tmp', env={**os.environ, 'PATH':'/usr/bin:/bin'},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.splitlines(), [str(root), str(binaries / 'node'), '--version'])


if __name__ == '__main__':
    unittest.main()
