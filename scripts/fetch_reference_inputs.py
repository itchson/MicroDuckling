"""Fetch the four CAD inputs and upstream notices into the ignored local cache.

Only files listed in references/inputs.json are accepted. Existing files are
verified, never silently replaced. New downloads must match their recorded byte
count and SHA-256 before they are installed. No third-party file is published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "references/inputs.json"
DESTINATION = ROOT / "references/components_r02"
ALLOWED_HOSTS = {"raw.githubusercontent.com", "www.pololu.com"}


def read_manifest(path: Path = MANIFEST) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported reference manifest version")
    entries = document["files"]
    seen = set()
    for entry in entries:
        relative = PurePosixPath(entry["path"])
        if (relative.is_absolute() or ".." in relative.parts or not relative.parts
                or "\\" in entry["path"] or ":" in entry["path"]
                or entry["path"] in seen):
            raise ValueError(f"Unsafe or duplicate manifest path: {entry['path']}")
        parsed = urlparse(entry["url"])
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Unexpected reference source: {entry['url']}")
        if not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
            raise ValueError(f"Invalid SHA-256 for {entry['path']}")
        if not isinstance(entry["bytes"], int) or not 0 < entry["bytes"] < 20_000_000:
            raise ValueError(f"Invalid byte count for {entry['path']}")
        seen.add(entry["path"])
    return entries


def verify_bytes(data: bytes, entry: dict) -> None:
    if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Size or SHA-256 mismatch: {entry['path']}; the expected file was not accepted")


def destination(entry: dict, root: Path) -> Path:
    target = root.joinpath(*PurePosixPath(entry["path"]).parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Reference path escapes cache: {entry['path']}")
    return target


def fetch_one(entry: dict, root: Path, verify_only: bool = False) -> str:
    target = destination(entry, root)
    if target.exists():
        verify_bytes(target.read_bytes(), entry)
        return "verified"
    if verify_only:
        raise FileNotFoundError(f"Reference missing: {entry['path']}; run without --verify")
    request = Request(entry["url"], headers={"User-Agent": "MicroDuckling-reference-fetch/1.0"})
    with urlopen(request, timeout=45) as response:
        final = urlparse(response.url)
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Unexpected download redirect for {entry['path']}")
        data = response.read(entry["bytes"] + 1)
    verify_bytes(data, entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Keep unverified/interrupted downloads out of the active reference paths.
    with tempfile.TemporaryDirectory(prefix=".fetch-", dir=target.parent) as temporary:
        staged = Path(temporary) / "verified-input"
        staged.write_bytes(data)
        # Exclusive creation prevents an existing file from being overwritten.
        with target.open("xb") as output:
            output.write(staged.read_bytes())
    return "downloaded"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="Verify cached inputs and notices without network access")
    mode.add_argument("--list", action="store_true", help="List sources without downloading")
    args = parser.parse_args()
    entries = read_manifest()
    if args.list:
        for entry in entries:
            print(f"{entry['path']}\n  {entry['url']}\n  SHA-256 {entry['sha256']}")
        return
    for entry in entries:
        print(f"{fetch_one(entry, DESTINATION, args.verify)}: {entry['path']}", flush=True)
    print("Reference inputs and upstream notices verified. These files remain local and Git-ignored.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Reference fetch failed: {error}") from error
