#!/usr/bin/env python3
"""Local BGM/SFX library with license evidence. Registering never downloads anything.

Files live under assets/audio/ (Git-ignored). config/media-licenses.json keeps one entry per file
with its hash, measured length and loudness, and the license/claim evidence the design requires.
An asset is usable only when it is eligible for every platform in the production brief
(audio_platforms). Eligibility is a selection record, never a no-claim guarantee.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re

import common
from common import digest, read_json, run_command, safe_path, write_json

LIBRARY = "config/media-licenses.json"
AUDIO_ROOT = "assets/audio"
ASSET_ID = r"(bgm|sfx)-[a-z0-9][a-z0-9-]{1,40}"
KINDS = {"bgm", "sfx"}
ORIGINS = {"user", "claude_search"}
LICENSE_STATUS = {"verified", "pending"}
CLAIM_STATUS = {"documented_low_risk", "unknown", "known_claim"}
PLATFORMS = {"youtube", "instagram", "tiktok"}
MOODS = {"bright", "calm", "tense", "silly", "deflated", "warm", "epic", "travel"}


def load_library(root=None):
    path = safe_path(root or common.ROOT, LIBRARY, True)
    data = read_json(path)
    if data.get("schema_version") != 2 or not isinstance(data.get("assets"), list):
        raise ValueError("media-licenses.json must be schema_version 2 with an assets list")
    return data


def eligibility(asset, platforms):
    """Return (usable, reason). Only the platform list is narrowed by the brief; evidence rules stay strict."""
    if asset.get("free") is not True:
        return False, "not_free"
    if not set(platforms) <= set(asset.get("allowed_platforms", [])):
        return False, "platform_rights_incomplete"
    if asset.get("license_status") != "verified" or not asset.get("license_evidence"):
        return False, "license_pending"
    if asset.get("claim_status") == "known_claim" or asset.get("requires_whitelist"):
        return False, "known_claim_requirement"
    if asset.get("claim_status") != "documented_low_risk" or not asset.get("claim_evidence"):
        return False, "claim_pending"
    if asset.get("attribution_required") and not str(asset.get("attribution_text", "")).strip():
        return False, "attribution_text_missing"
    return True, "eligible_for_local_render_not_platform_certified"


def validate_entry(entry):
    if not isinstance(entry.get("id"), str) or not re.fullmatch(ASSET_ID, entry["id"]):
        raise ValueError("Asset IDs look like bgm-name or sfx-name")
    if entry.get("kind") not in KINDS or not entry["id"].startswith(entry["kind"] + "-"):
        raise ValueError(f"{entry.get('id')}: kind must match the ID prefix")
    if entry.get("origin") not in ORIGINS:
        raise ValueError(f"{entry['id']}: origin must be user or claude_search")
    if entry.get("license_status") not in LICENSE_STATUS or entry.get("claim_status") not in CLAIM_STATUS:
        raise ValueError(f"{entry['id']}: unknown license or claim status")
    if not set(entry.get("allowed_platforms", [])) <= PLATFORMS:
        raise ValueError(f"{entry['id']}: unknown platform")
    if not set(entry.get("moods", [])) <= MOODS:
        raise ValueError(f"{entry['id']}: moods must come from {sorted(MOODS)}")
    for key in ["title", "source", "license"]:
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            raise ValueError(f"{entry['id']}: {key} is required")
    parts = Path(entry.get("file", "")).parts
    if len(parts) < 3 or parts[:2] != ("assets", "audio"):
        raise ValueError(f"{entry['id']}: files must live under assets/audio/")
    return entry


def check(root=None, platforms=("youtube",)):
    """Verify every registered file and report eligibility. Raises on missing or changed files."""
    root = root or common.ROOT
    report = []
    ids = set()
    for entry in load_library(root)["assets"]:
        validate_entry(entry)
        if entry["id"] in ids:
            raise ValueError(f"Duplicate asset ID {entry['id']}")
        ids.add(entry["id"])
        path = safe_path(root, entry["file"], True)
        if digest(path) != entry["sha256"]:
            raise ValueError(f"{entry['id']}: file hash changed; re-register after checking the source")
        usable, reason = eligibility(entry, platforms)
        report.append({"id": entry["id"], "kind": entry["kind"], "usable": usable, "reason": reason,
                       "seconds": entry["duration_seconds"], "moods": entry.get("moods", [])})
    return report


def measure(path):
    probe = json.loads(run_command(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)
    stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    if stream is None:
        raise ValueError("No audio stream")
    log = run_command(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    summary = log.rsplit("Summary:", 1)[-1]
    integrated = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    return {"duration_seconds": round(float(probe["format"]["duration"]), 3), "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 0)),
            "integrated_lufs": float(integrated.group(1)) if integrated else None,
            "true_peak_dbtp": float(peak.group(1)) if peak and peak.group(1) != "-inf" else None}


def register(fields, root=None):
    """Add one file that already exists under assets/audio/. Downloads happen elsewhere, after user approval."""
    root = root or common.ROOT
    origin = fields.get("origin", "user")
    if origin == "claude_search":
        import production  # A Claude-found file is allowed only in a production brief that enables downloads.
        config = production.require_production_scope()
        if not (config["audio_search"] and config["audio_downloads"]):
            raise ValueError("claude_search assets need audio_search and audio_downloads enabled in the production config")
    library = load_library(root)
    if any(a["id"] == fields["id"] for a in library["assets"]):
        raise ValueError(f"{fields['id']} is already registered; use a new ID")
    path = safe_path(root, fields["file"], True)
    entry = {"id": fields["id"], "kind": fields["kind"], "file": fields["file"], "sha256": digest(path),
             "title": fields["title"], "author": fields.get("author") or None, "source": fields["source"],
             "origin": origin, "registered_on": date.today().isoformat(), "free": bool(fields.get("free", True)),
             "license": fields["license"], "license_status": fields.get("license_status", "pending"),
             "license_evidence": fields.get("license_evidence") or None,
             "claim_status": fields.get("claim_status", "unknown"), "claim_evidence": fields.get("claim_evidence") or None,
             "requires_whitelist": bool(fields.get("requires_whitelist", False)),
             "allowed_platforms": sorted(fields.get("allowed_platforms", [])),
             "attribution_required": bool(fields.get("attribution_text")), "attribution_text": fields.get("attribution_text") or None,
             "moods": sorted(fields.get("moods", [])), "vocals": bool(fields.get("vocals", False)),
             "platform_check": "not_checked"}
    entry |= measure(path)
    validate_entry(entry)
    library["assets"].append(entry)
    write_json(safe_path(root, LIBRARY, True), library, replace=True)
    return entry


def credits(asset_ids, root=None):
    """Attribution lines for the video description, only for assets actually used."""
    by_id = {a["id"]: a for a in load_library(root)["assets"]}
    lines = []
    for asset_id in asset_ids:
        asset = by_id[asset_id]
        lines.append(asset["attribution_text"] if asset.get("attribution_required") else
                     f"{asset['title']}{' - ' + asset['author'] if asset.get('author') else ''} ({asset['source']}, {asset['license']})")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    add = sub.add_parser("register")
    for name in ["id", "kind", "file", "title", "source", "license"]:
        add.add_argument(f"--{name}", required=True)
    add.add_argument("--author")
    add.add_argument("--origin", choices=sorted(ORIGINS), default="user")
    add.add_argument("--license-status", choices=sorted(LICENSE_STATUS), default="pending")
    add.add_argument("--license-evidence")
    add.add_argument("--claim-status", choices=sorted(CLAIM_STATUS), default="unknown")
    add.add_argument("--claim-evidence")
    add.add_argument("--platforms", default="", help="comma list of youtube,instagram,tiktok with confirmed rights")
    add.add_argument("--attribution-text")
    add.add_argument("--moods", default="")
    add.add_argument("--vocals", action="store_true")
    status = sub.add_parser("check")
    status.add_argument("--platforms", default="youtube")
    sub.add_parser("credits").add_argument("--ids", required=True)
    args = parser.parse_args()
    try:
        if args.action == "register":
            fields = {k: v for k, v in vars(args).items() if k not in {"action", "platforms", "moods"}}
            fields["allowed_platforms"] = [p for p in args.platforms.split(",") if p]
            fields["moods"] = [m for m in args.moods.split(",") if m]
            result = register(fields)
        elif args.action == "check":
            result = check(platforms=[p for p in args.platforms.split(",") if p])
        else:
            result = credits([i for i in args.ids.split(",") if i])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
