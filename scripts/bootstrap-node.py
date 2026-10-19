#!/usr/bin/env python3
"""Explicit, project-local installation of the pinned official Node distribution."""
import hashlib
import json
import platform
from pathlib import Path
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v24.22.0"


def main():
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise SystemExit("Unsupported bootstrap platform; provide Node 24 on PATH instead.")
    folder = f"node-{VERSION}-darwin-arm64"
    destination = ROOT / ".tools" / folder
    if destination.exists():
        raise SystemExit(f"Refusing to replace existing runtime: {destination}")
    parent = destination.parent
    if parent.is_symlink():
        raise SystemExit("Refusing symlinked .tools directory")
    parent.mkdir(exist_ok=True)
    filename = folder + ".tar.gz"
    base = f"https://nodejs.org/dist/{VERSION}/"
    with tempfile.TemporaryDirectory(prefix="node-download-", dir=parent) as temp:
        temp = Path(temp)
        checksums = urllib.request.urlopen(base + "SHASUMS256.txt", timeout=60).read().decode()
        expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == filename)
        archive = temp / filename
        with urllib.request.urlopen(base + filename, timeout=60) as response, archive.open("xb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 150 * 1024 * 1024:
                    raise ValueError("Unexpected archive size")
                output.write(chunk)
        actual = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
        if actual != expected:
            raise ValueError("Node archive checksum mismatch")
        with tarfile.open(archive) as bundle:
            if any(not item.name.startswith(folder + "/") and item.name != folder for item in bundle.getmembers()):
                raise ValueError("Unexpected archive root")
            bundle.extractall(temp, filter="data")
        (temp / folder).rename(destination)
        (destination / "vlog-install-receipt.json").write_text(json.dumps({
            "source": base + filename, "sha256": actual, "version": VERSION,
            "checksum_source": base + "SHASUMS256.txt"
        }, indent=2) + "\n")
    print(f"Installed {VERSION} at {destination}; global PATH unchanged.")


if __name__ == "__main__":
    main()
