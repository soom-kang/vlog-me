#!/usr/bin/env python3
"""Read-only project preflight; never installs or invokes a model."""
import json
import shutil
import subprocess
from common import ROOT, digest, read_json, safe_path, require_setup_scope


def verify_skill_integrity(root):
    skills = read_json(safe_path(root, "config/skills-lock.json", True))["skills"]
    if not skills:
        raise ValueError("No registered Skill")
    expected_entries = set()
    for skill in skills:
        base = safe_path(root, skill["path"])
        expected_entries.add(base / 'SKILL.md')
        declared = skill["files"]
        actual = {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() or p.is_symlink()}
        if not declared or set(declared) != actual or 'SKILL.md' not in declared:
            raise ValueError("Skill file set differs from lock")
        for relative, expected in declared.items():
            if digest(safe_path(base, relative, True)) != expected:
                raise ValueError("Skill file hash mismatch")
    if set((root / '.claude/skills').glob('*/SKILL.md')) != expected_entries:
        raise ValueError("Unregistered or missing project Skill")


def verify_font_integrity(root):
    lock = read_json(safe_path(root, "config/fonts-lock.json", True))
    base = safe_path(root, lock["path"])
    declared = {name: sha for font in lock["fonts"] for name, sha in font["files"].items()}
    actual = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() or p.is_symlink()}
    if not declared or set(declared) != actual:
        raise ValueError("Font file set differs from lock")
    for relative, expected in declared.items():
        if digest(safe_path(base, relative, True)) != expected:
            raise ValueError("Font file hash mismatch")


def main():
    checks = []
    for binary in ["claude", "node", "npm", "ffmpeg", "ffprobe", "python3"]:
        executable = shutil.which(binary)
        if executable:
            flag = "-version" if binary in {"ffmpeg", "ffprobe"} else "--version"
            result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=15)
            checks.append({"name": binary, "status": "PASS" if result.returncode == 0 else "FAIL", "path": executable,
                           "version": (result.stdout or result.stderr).splitlines()[0]})
        else:
            checks.append({"name": binary, "status": "FAIL", "reason": "not on project PATH"})
    for name in ["CLAUDE.md", "feature_list.json", "config/project.json", "renderer/package-lock.json", ".tools/browser.json"]:
        checks.append({"name": name, "status": "PASS" if (ROOT / name).is_file() else "FAIL"})
    try:
        require_setup_scope()
        checks.append({"name": "setup_scope", "status": "PASS"})
    except (AssertionError, KeyError, OSError, ValueError):
        checks.append({"name": "setup_scope", "status": "FAIL"})
    try:
        verify_skill_integrity(ROOT)
        checks.append({"name": "upstream_skill_integrity", "status": "PASS"})
    except (AssertionError, KeyError, OSError, ValueError):
        checks.append({"name": "upstream_skill_integrity", "status": "FAIL"})
    try:
        verify_font_integrity(ROOT)
        checks.append({"name": "bundled_fonts", "status": "PASS"})
    except (AssertionError, KeyError, OSError, ValueError):
        checks.append({"name": "bundled_fonts", "status": "FAIL"})
    try:
        browser = read_json(ROOT / ".tools/browser.json")
        safe_path(ROOT, browser["path"], True)
        checks.append({"name": "local_browser", "status": "PASS"})
    except (AssertionError, KeyError, OSError, ValueError):
        checks.append({"name": "local_browser", "status": "FAIL"})
    try:
        if not subprocess.check_output(['node','--version'], text=True).startswith('v24.'):
            raise ValueError('Node 24 is required')
        package = read_json(ROOT / 'renderer/package.json')
        for name, version in (package['dependencies'] | package['devDependencies']).items():
            if read_json(ROOT / 'renderer/node_modules' / name / 'package.json')['version'] != version:
                raise ValueError(f'Installed version mismatch: {name}')
        checks.append({'name':'pinned_dependencies','status':'PASS'})
    except (AssertionError, KeyError, OSError, ValueError, subprocess.SubprocessError):
        checks.append({'name':'pinned_dependencies','status':'FAIL'})
    print(json.dumps({"checks": checks, "free_disk_bytes": shutil.disk_usage(ROOT).free,
                      "real_media": "NOT_RUN", "asr": "NOT_INSTALLED", "audio_library": "EMPTY"}, indent=2))
    return 0 if all(check["status"] == "PASS" for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
