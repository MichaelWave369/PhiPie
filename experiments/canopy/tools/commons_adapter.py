"""PhiPie Canopy C2: create-only, offline export to canonical Infinite Commons files.

This original adapter validates the complete C1 capsule schema before writing
two fixed paths. It never installs code, communicates over a network, or grants
publication, device, or inference authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CAPSULE_FORMAT = "phipie.canopy.capsule.v0.1"
DISTRICT_SCHEMA = "phipie.canopy.district.v0.1"
ARTIFACT = "commons_data/artifacts/manifest.json"
BOOTSTRAP = "commons_data/bootstrap/latest_contract.json"
LIMIT = 65536
_SLUG = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")
_UNSAFE = re.compile(r"[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069\ud800-\udfff]")
_LINK = re.compile(r"<|>|https?://|javascript:|data:", re.IGNORECASE)
_KINDS = {"plaza", "library", "relay", "studio", "garden"}
_SYMBOLS = {"✳", "✦", "✺", "◇", "☾"}


class CapsuleRefused(ValueError):
    """Untrusted capsule did not pass the C1 contract."""


def _refuse(reason: str):
    raise CapsuleRefused("Capsule refused: " + reason)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _refuse("duplicate JSON key")
        result[key] = value
    return result


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        _refuse(label + " must have exactly its permitted fields")
    return value


def _list(value, low, high, label):
    if not isinstance(value, list) or not low <= len(value) <= high:
        _refuse(label + " count invalid")
    return value


def _text(value, label, limit=280):
    if (not isinstance(value, str) or not 1 <= len(value) <= limit
            or _UNSAFE.search(value) or _LINK.search(value)):
        _refuse(label + " contains unsafe or oversized text")
    return value


def _id(value, label):
    _text(value, label, 40)
    if not _SLUG.fullmatch(value):
        _refuse(label + " invalid identifier")
    return value


def _json_read(data: bytes):
    if not 100 <= len(data) <= LIMIT:
        _refuse("input size outside 100 bytes to 64 KiB")
    try:
        return json.loads(data.decode("utf-8", errors="strict"),
                          object_pairs_hook=_pairs,
                          parse_constant=lambda _: _refuse("nonfinite JSON number"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CapsuleRefused("Capsule refused: invalid UTF-8 JSON") from exc


def validate(data: bytes) -> dict:
    """Fail closed against the complete C1 field, text, and route constraints."""
    capsule = _keys(_json_read(data), {"format", "bootstrap", "artifacts"}, "capsule")
    if capsule["format"] != CAPSULE_FORMAT:
        _refuse("wrong capsule format")
    boot = _keys(capsule["bootstrap"],
                 {"target", "channel_name", "candidate_id", "artifacts"},
                 "bootstrap")
    if boot["target"] != "commons" or boot["channel_name"] != "stable":
        _refuse("unsupported bootstrap target or channel")
    _id(boot["candidate_id"], "candidate_id")
    refs = _list(boot["artifacts"], 1, 1, "bootstrap artifacts")
    ref = _keys(refs[0], {"name", "path", "required", "load_order"}, "artifact reference")
    if (ref["name"] != "commons_manifest" or ref["path"] != ARTIFACT
            or ref["required"] is not True or type(ref["load_order"]) is not int
            or ref["load_order"] != 10):
        _refuse("artifact reference must use the fixed, required C1 path")
    embedded = _keys(capsule["artifacts"], {ARTIFACT}, "artifacts")
    district = _keys(embedded[ARTIFACT],
                     {"schema", "district_id", "title", "subtitle", "welcome",
                      "provenance", "publication_mode", "start_room", "rooms"},
                     "district")
    if (district["schema"] != DISTRICT_SCHEMA or
            district["provenance"] != "SIMULATED" or
            district["publication_mode"] != "fictional-public-sample"):
        _refuse("invalid schema or alleged authority")
    _id(district["district_id"], "district_id")
    _text(district["title"], "district title", 90)
    _text(district["subtitle"], "subtitle", 140)
    _text(district["welcome"], "welcome", 280)
    _id(district["start_room"], "start_room")

    rooms = _list(district["rooms"], 2, 8, "rooms")
    known = set()
    for room in rooms:
        _keys(room, {"id", "kind", "symbol", "title", "description", "discovery", "exits"}, "room")
        room_id = _id(room["id"], "room id")
        if room_id in known:
            _refuse("duplicate room identifier")
        known.add(room_id)
        if (not isinstance(room["kind"], str) or not isinstance(room["symbol"], str)
                or room["kind"] not in _KINDS or room["symbol"] not in _SYMBOLS):
            _refuse("invalid room kind or symbol")
        _text(room["title"], "room title", 70)
        _text(room["description"], "room description", 360)
        _text(room["discovery"], "room discovery", 320)
        exits = _list(room["exits"], 1, 4, "room exits")
        destinations = set()
        for edge in exits:
            _keys(edge, {"to", "label"}, "exit")
            destination = _id(edge["to"], "exit destination")
            _text(edge["label"], "exit label", 65)
            if destination == room_id or destination in destinations:
                _refuse("duplicate or self exit")
            destinations.add(destination)
    if district["start_room"] not in known:
        _refuse("missing entry room")
    by_id = {room["id"]: room for room in rooms}
    for room in rooms:
        if any(edge["to"] not in known for edge in room["exits"]):
            _refuse("exit to missing room")
    seen = {district["start_room"]}
    queue = [district["start_room"]]
    while queue:
        room = by_id[queue.pop(0)]
        for edge in room["exits"]:
            if edge["to"] not in seen:
                seen.add(edge["to"])
                queue.append(edge["to"])
    if seen != known:
        _refuse("unreachable room")
    return capsule


def _json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _read_capsule(path: Path):
    if not path.is_file() or path.is_symlink():
        _refuse("capsule must be an existing regular file")
    if path.stat().st_size > LIMIT:
        _refuse("capsule exceeds 64 KiB")
    return path.read_bytes()


def unpack(source: Path, destination: Path) -> dict:
    """Create only two fixed files inside an exclusively new output directory."""
    source_data = _read_capsule(source)
    capsule = validate(source_data)
    if destination.exists() or destination.is_symlink():
        _refuse("destination already exists; never overwrite")
    parent = destination.parent
    if not parent.is_dir() or parent.is_symlink():
        _refuse("destination parent must be a normal existing directory")
    # Both output filenames are constants rather than paths from untrusted JSON.
    boot_content = _json_bytes(capsule["bootstrap"])
    artifact_content = _json_bytes(capsule["artifacts"][ARTIFACT])
    # Create the directory atomically: concurrent attempts cannot reuse it.
    destination.mkdir(mode=0o700)
    for relative, content in [(BOOTSTRAP, boot_content), (ARTIFACT, artifact_content)]:
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    return {
        "state": "CANONICAL_FILES_WRITTEN_NOT_AUTHORIZED",
        "target": "commons",
        "candidate_id": capsule["bootstrap"]["candidate_id"],
        "output_root": str(destination),
        "files": [BOOTSTRAP, ARTIFACT],
        "source_sha256": hashlib.sha256(source_data).hexdigest(),
        "bootstrap_sha256": hashlib.sha256(boot_content).hexdigest(),
        "artifact_sha256": hashlib.sha256(artifact_content).hexdigest(),
        "publication_authorized": False,
        "network_authorized": False,
        "runtime_authorized": False,
        "infinite_commons_loader_passed": None,
    }


def repack(root: Path, destination: Path) -> dict:
    """Recreate a C1 capsule from only its two expected canonical files."""
    if destination.exists() or destination.is_symlink():
        _refuse("destination already exists; never overwrite")
    boot_path = root / BOOTSTRAP
    artifact_path = root / ARTIFACT
    if any(not p.is_file() or p.is_symlink() for p in (boot_path, artifact_path)):
        _refuse("canonical files missing, nonregular or symlinks")
    if any(p.stat().st_size > LIMIT for p in (boot_path, artifact_path)):
        _refuse("canonical file exceeds bounds")
    try:
        boot = json.loads(boot_path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CapsuleRefused("Capsule refused: invalid canonical JSON") from exc
    content = _json_bytes({
        "format": CAPSULE_FORMAT,
        "bootstrap": boot,
        "artifacts": {ARTIFACT: artifact},
    })
    validate(content)
    with destination.open("xb") as stream:
        stream.write(content)
    return {
        "state": "PORTABLE_CAPSULE_CREATED_NOT_PUBLISHED",
        "capsule_sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "publication_authorized": False,
        "network_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline C1 capsule <-> canonical Commons files")
    sub = parser.add_subparsers(dest="action", required=True)
    ex = sub.add_parser("unpack", help="Create a new canonical filesystem tree")
    ex.add_argument("capsule", type=Path)
    ex.add_argument("destination", type=Path)
    pk = sub.add_parser("repack", help="Create a new portable capsule")
    pk.add_argument("canonical_root", type=Path)
    pk.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        result = (unpack(args.capsule, args.destination) if args.action == "unpack"
                  else repack(args.canonical_root, args.destination))
    except (CapsuleRefused, OSError) as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc),
                          "publication_authorized": False,
                          "network_authorized": False}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
