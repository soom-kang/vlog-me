#!/usr/bin/env python3
"""Read-only project preflight; never installs or invokes a model."""
import json
import shutil
import subprocess
from common import ROOT, digest, read_json, safe_path, validate_setup_config


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


def scope_status(root):
    """Validate config/project.json for whichever phase it declares."""
    import production
    config = read_json(safe_path(root, "config/project.json", True))
    phase = config.get("phase")
    if phase == "production":
        production.validate_production_config(config)
    else:
        validate_setup_config(config)
    return phase, config


def asr_status(root, config):
    """READY when the configured whisper.cpp model exists with the recorded size; NOT_CONFIGURED is fine."""
    name = config.get("asr_model")
    if not name:
        return "PASS", "NOT_CONFIGURED"
    if not shutil.which("whisper-cli"):
        return "FAIL", "NO_ENGINE (whisper-cli not on PATH)"
    model = safe_path(root, f".tools/whisper/{name}")
    if not model.is_file():
        return "FAIL", f"MISSING_MODEL {name}"
    recorded = read_json(safe_path(root, "config/toolchain.json", True)).get("asr", {})
    if recorded.get("model") == name and recorded.get("bytes") not in (None, model.stat().st_size):
        return "FAIL", f"MODEL_SIZE_MISMATCH {name}"
    return "PASS", f"READY {name}"


def audio_status(root, config):
    import audio_library
    report = audio_library.check(root, config.get("audio_platforms", ["youtube"]))
    usable = sum(item["usable"] for item in report)
    return f"{len(report)} registered, {usable} usable" if report else "EMPTY"


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
    phase, config, asr, audio = "unknown", {}, "NOT_CHECKED", "NOT_CHECKED"
    try:
        phase, config = scope_status(ROOT)
        checks.append({"name": "scope", "status": "PASS", "phase": phase})
    except (AssertionError, KeyError, OSError, ValueError) as exc:
        checks.append({"name": "scope", "status": "FAIL", "phase": phase, "reason": str(exc)[:300]})
    try:
        status, asr = asr_status(ROOT, config)
        checks.append({"name": "asr", "status": status, "detail": asr})
    except (KeyError, OSError, ValueError) as exc:
        checks.append({"name": "asr", "status": "FAIL", "reason": str(exc)[:300]})
    try:
        audio = audio_status(ROOT, config)
        checks.append({"name": "audio_library", "status": "PASS", "detail": audio})
    except (KeyError, OSError, ValueError) as exc:
        checks.append({"name": "audio_library", "status": "FAIL", "reason": str(exc)[:300]})
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
    print(json.dumps({"checks": checks, "phase": phase, "source_roots": config.get("source_roots", []),
                      "free_disk_bytes": shutil.disk_usage(ROOT).free, "asr": asr, "audio_library": audio}, indent=2))
    return 0 if all(check["status"] == "PASS" for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
