# PhiPie Canopy Commons Capsule C2: canonical handoff

**Status: cross-repository verification candidate, not a qualified physical network or public content publisher.**

C1 introduced a self-contained fictional forest world with a Commons-shaped bootstrap. C2 makes it readable by the **actual** original Infinite Commons Python bootstrap loader through two exact filesystem files. It does not copy the upstream loader or alter Infinite Commons.

## Exported filesystem tree

The canonical files created in a **new, nonexistent destination** are:

- commons_data/bootstrap/latest_contract.json
- commons_data/artifacts/manifest.json

The exporter only writes those two hardcoded paths. Caller-provided JSON is never used as an arbitrary path, URL, instruction, script or repository update. The manifest contains the same five fictional rooms as the original .commons sample.

## Run locally

Python 3.10+, standard library only. From the PhiPie repository root, run:

    python experiments/canopy/tools/commons_adapter.py unpack experiments/canopy/react/src/capsules/scout-grove.commons.json output-c2
    python experiments/canopy/tools/commons_adapter.py repack output-c2 output-repacked.commons
    python -m unittest discover -s experiments/canopy/tests -p test_commons_adapter.py -v

Use a **nonexistent** directory output-c2 and nonexistent output-repacked.commons. Use Windows paths in PowerShell if required. Existing output destinations are refused.

JSON receipts carry SHA-256 content checksums and explicit publication_authorized: false, network_authorized: false. These are not identity signatures.

## Real upstream interoperability gate

GitHub Actions checks out original Infinite Commons at pinned commit:

9c45db9bd5fa308a7cfb4bf4e32b0816dd68aa53

It runs the **unmodified** upstream infinite_commons.cli bootstrap-check on the generated canonical output and verifies exactly one loaded manifest. Adapter tests check malformed inputs, arbitrary paths, forged provenance, repack roundtrip, and refusal before creating outputs.

This establishes **bootstrap file interoperability with that exact original loader**, **not** shared interactive scene rendering. The Infinite Commons Python loader currently only parses required JSON objects. It does not render Lantern Grove as the Midnight Sierra React experience; that is a separate future milestone.

## Safety and limitation contract

- C1 input must be 100 bytes to 64 KiB, valid UTF-8 JSON, with exact allowlisted fields and without duplicate JSON keys.
- Validate one immutable relative artifact path, allowed room types/symbols, safe identifiers, text limits, graph reachability and exits.
- Reject false provenance/publication claims, HTML/URL-like content, unsafe Unicode, unexpected authority fields and existing destinations.
- No network, model download, Porch/LightBridge connection, disk scan, service install, device control or physical-network claims.
- Writes occur under a new operator-selected directory; I/O failure can leave an incomplete newly created directory, which must be treated as invalid until verified. No hardened attacker-controlled filesystem/symlink-race security claim.
- SHA-256 records content bytes, not true authorship, authorization, independently verified source truth or a physical-device proof.
- Neither the upstream original repo nor PhiPie PHIPIE-03 qualification status is changed.

## Acceptance

1. Valid portable capsule exported to exactly two canonical files.
2. Invalid files and existing destinations refused before writing.
3. Repack returns equivalent parsed C1 JSON.
4. Unmodified upstream Python loader reports success with exactly one loaded manifest.
5. No code execution, authority grant, browser dependency or hardware behavior change.

**Capability is not authority. Ledger Above Ego.**
