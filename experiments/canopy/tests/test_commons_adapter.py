"""C2 regressions: portable Canopy C1 envelope -> canonical Infinite Commons files."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from commons_adapter import ARTIFACT, BOOTSTRAP, CapsuleRefused, repack, unpack, validate  # noqa: E402

SAMPLE = ROOT / "react/src/capsules/scout-grove.commons.json"
UPSTREAM = os.environ.get("CANOPY_COMMONS_SRC")


def modified(change):
    obj = json.loads(SAMPLE.read_text(encoding="utf-8"))
    change(obj)
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


class CanopyCommonsC2Tests(unittest.TestCase):
    def test_validate_and_create_canonical_bootstrap(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "isolated-export"
            receipt = unpack(SAMPLE, out)
            self.assertEqual(receipt["state"], "CANONICAL_FILES_WRITTEN_NOT_AUTHORIZED")
            self.assertFalse(receipt["publication_authorized"])
            self.assertFalse(receipt["network_authorized"])
            self.assertFalse(receipt["runtime_authorized"])
            self.assertIsNone(receipt["infinite_commons_loader_passed"])
            self.assertEqual(sorted(receipt["files"]), sorted([BOOTSTRAP, ARTIFACT]))
            self.assertTrue((out / BOOTSTRAP).is_file())
            self.assertTrue((out / ARTIFACT).is_file())
            self.assertEqual(sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()),
                             sorted([BOOTSTRAP, ARTIFACT]))
            boot = json.loads((out / BOOTSTRAP).read_text(encoding="utf-8"))
            manifest = json.loads((out / ARTIFACT).read_text(encoding="utf-8"))
            original = validate(SAMPLE.read_bytes())
            self.assertEqual(boot, original["bootstrap"])
            self.assertEqual(manifest, original["artifacts"][ARTIFACT])
            self.assertEqual(len(manifest["rooms"]), 5)
            self.assertEqual(receipt["source_sha256"], hashlib.sha256(SAMPLE.read_bytes()).hexdigest())
            with self.assertRaises(CapsuleRefused):
                unpack(SAMPLE, out)  # existing output is never overwritten

    def test_repack_detached_content_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            dest = folder / "canonical"
            unpack(SAMPLE, dest)
            packed = folder / "repacked.commons"
            receipt = repack(dest, packed)
            self.assertEqual(receipt["state"], "PORTABLE_CAPSULE_CREATED_NOT_PUBLISHED")
            self.assertFalse(receipt["publication_authorized"])
            self.assertFalse(receipt["network_authorized"])
            self.assertEqual(validate(packed.read_bytes()), validate(SAMPLE.read_bytes()))
            with self.assertRaises(CapsuleRefused):
                repack(dest, packed)
            self.assertEqual(validate(packed.read_bytes())["bootstrap"]["candidate_id"], "canopy-scout-grove-v01")

    def test_refuses_unknown_artifacts_forged_authority_and_unsafe_paths_before_write(self):
        changes = [
            lambda obj: obj["bootstrap"]["artifacts"][0].update(path="../escape.json"),
            lambda obj: obj["bootstrap"]["artifacts"][0].update(required=False),
            lambda obj: obj["artifacts"][ARTIFACT].update(provenance="VERIFIED"),
            lambda obj: obj["artifacts"][ARTIFACT].update(publication_mode="approved"),
            lambda obj: obj["artifacts"][ARTIFACT].update(remote_url="http://localhost:9999/private"),
            lambda obj: obj.update(permissions=["root"]),
            lambda obj: obj["artifacts"][ARTIFACT]["rooms"].append(copy.deepcopy(obj["artifacts"][ARTIFACT]["rooms"][0])),
            lambda obj: obj["artifacts"][ARTIFACT]["rooms"][0]["exits"][0].update(to="missing"),
            lambda obj: obj["artifacts"][ARTIFACT]["rooms"][0].update(description="<script>run</script>"),
        ]
        with tempfile.TemporaryDirectory() as d:
            for i, change in enumerate(changes):
                source = Path(d) / f"bad{i}.commons"
                source.write_bytes(modified(change))
                destination = Path(d) / f"out{i}"
                with self.subTest(case=i), self.assertRaises(CapsuleRefused):
                    unpack(source, destination)
                self.assertFalse(destination.exists())

    def test_duplicate_keys_large_files_and_existing_destinations_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            duplicate = folder / "duplicate.commons"
            duplicate.write_bytes(SAMPLE.read_bytes().replace(b'"format":', b'"format":"spoof", "format":', 1))
            with self.assertRaises(CapsuleRefused):
                unpack(duplicate, folder / "bad")
            huge = folder / "huge.commons"
            huge.write_bytes(b"x" * 65537)
            with self.assertRaises(CapsuleRefused):
                unpack(huge, folder / "huge-dest")
            occupied = folder / "occupied"
            occupied.mkdir()
            keep = occupied / "existing.txt"
            keep.write_text("keep", encoding="utf-8")
            with self.assertRaises(CapsuleRefused):
                unpack(SAMPLE, occupied)
            self.assertEqual(keep.read_text(), "keep")

    def test_repack_refuses_modified_canonical_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "canonical"
            unpack(SAMPLE, root)
            target = Path(d) / "bad.commons"
            broken = json.loads((root / ARTIFACT).read_text(encoding="utf-8"))
            broken["publication_mode"] = "private-to-public"
            (root / ARTIFACT).write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(CapsuleRefused):
                repack(root, target)
            self.assertFalse(target.exists())

    @unittest.skipUnless(UPSTREAM, "Real Infinite Commons checkout provided by integration CI")
    def test_real_original_infinite_commons_loader_consumes_export(self):
        """Test the actual pinned upstream code rather than a recreated loader."""
        assert UPSTREAM is not None
        self.assertTrue((Path(UPSTREAM) / "infinite_commons/proof_service.py").is_file(),
                        "Configured real upstream code must exist")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "canonical"
            unpack(SAMPLE, root)
            environment = dict(os.environ, PYTHONPATH=str(Path(UPSTREAM).resolve()))
            process = subprocess.run(
                [sys.executable, "-m", "infinite_commons.cli",
                 "bootstrap-check", "--repo-root", str(root)],
                capture_output=True, text=True, env=environment, check=False,
                timeout=30,
            )
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            report = json.loads(process.stdout)
            self.assertTrue(report["success"], report)
            self.assertEqual(report["target"], "commons")
            self.assertEqual(report["candidate_id"], "canopy-scout-grove-v01")
            self.assertEqual(report["loaded_artifacts"], [ARTIFACT])
            self.assertEqual(report["missing_required_artifacts"], [])
            # Loading is not approval, identity or deep schema inspection.
            self.assertEqual(json.loads((root / ARTIFACT).read_text(encoding="utf-8"))["provenance"], "SIMULATED")


if __name__ == "__main__":
    unittest.main()
