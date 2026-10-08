"""PR19: additive ninth-file TCP benchmark evidence; keeps #18 eight-file ABI.

A local, strictly bounded iperf3 client report is a measurement CLAIM, not
independent verification of the remote server or a specific Wi-Fi hop.
"""
from __future__ import annotations

from hashlib import sha256
import math
import os
from pathlib import Path
import stat
from typing import Any

from .evidence_binding import FILE_RE, _read_dir_file
from .field_witness import _hash
from .linux_radio import _private_ipv4
from .probe_bundle import ALL_SLOTS, probe_manifest_template, verify_probe_bundle
from .soma_observation import canonical_json
from .tcp_observer import SCHEMA, PORT, TARGET_RATE_BPS, TEST_SECONDS

CONTRACT="phipie-trail-tcp-bundle-assessment/v0.1"
MANIFEST="phipie-trail-private-tcp-manifest/v0.1"
NINE_SLOTS=(*ALL_SLOTS,"tcp_observation")


def tcp_manifest_template(test_id="trial-001"):
    item=probe_manifest_template(test_id)
    item["contract"]=MANIFEST
    item["files"]["tcp_observation"]="tcp-observation.json"
    return item


def _finite(x: Any, minimum: float, maximum: float) -> bool:
    if type(x) not in (int, float):
        return False
    try:
        return math.isfinite(x) and minimum <= x <= maximum
    except (TypeError, OverflowError, ValueError):
        return False


def valid_tcp_record(rec: Any) -> bool:
    if not isinstance(rec, dict) or set(rec)!={
        "schema","status","reason","target","metrics","limits","provenance",
        "network_change_authorized","rover_motion_authorized",
        "physical_deployment_authorized","hardware_qualified","evidence_sha256",
    }:
        return False
    if (rec["schema"]!=SCHEMA or rec["status"]!="LOCAL_TCP_OBSERVED"
        or rec["reason"] is not None or not _private_ipv4(rec["target"])
        or any(rec[x] is not False for x in (
            "network_change_authorized","rover_motion_authorized",
            "physical_deployment_authorized","hardware_qualified"))):
        return False
    if rec["limits"] != {
        "port": PORT, "configured_seconds": TEST_SECONDS,
        "pacing_target_bps": TARGET_RATE_BPS, "pacing_is_hard_cap": False,
        "one_stream_only": True,
    }:
        return False
    if rec["provenance"] != {
        "source":"operator-approved-iperf3-client",
        "client_report_only": True,"server_identity_attested":False,
        "network_interface_bound":False,"route_proven":False,
        "traffic_generated":True,
    }:
        return False
    m=rec["metrics"]
    if not isinstance(m, dict) or set(m)!={
        "sent_bytes","received_bytes","duration_sent_s",
        "duration_received_s","sent_mbps","received_mbps","retransmits",
    }:
        return False
    if (type(m["sent_bytes"]) is not int or type(m["received_bytes"]) is not int
        or not 1<=m["received_bytes"]<=m["sent_bytes"]<=1_500_000
        or not _finite(m["duration_sent_s"],1,6)
        or not _finite(m["duration_received_s"],1,6)
        or not _finite(m["sent_mbps"],0.000001,3)
        or not _finite(m["received_mbps"],0.000001,3)):
        return False
    if (m["retransmits"] is not None
        and (type(m["retransmits"]) is not int or not 0<=m["retransmits"]<=1_000_000)):
        return False
    if (abs(m["sent_mbps"] - (8*m["sent_bytes"]/m["duration_sent_s"]/1_000_000)) > .1
        or abs(m["received_mbps"] - (8*m["received_bytes"]/m["duration_received_s"]/1_000_000)) > .1):
        return False
    try:
        canonical=canonical_json({k:v for k,v in rec.items() if k!="evidence_sha256"})
    except (TypeError,ValueError,OverflowError):
        return False
    return isinstance(rec["evidence_sha256"],str) and sha256(canonical).hexdigest()==rec["evidence_sha256"]


def verify_tcp_bundle(witness: Any, manifest: Any, evidence_dir: str|Path) -> dict[str,Any]:
    reasons=[]
    checks={k:"NOT_CHECKED" for k in NINE_SLOTS}
    reported_rate=None
    if (not isinstance(manifest,dict)
        or set(manifest)!={"contract","test_id","files"}
        or manifest.get("contract")!=MANIFEST
        or not isinstance(witness,dict)
        or manifest.get("test_id")!=witness.get("test_id")
        or not isinstance(manifest.get("files"),dict)
        or set(manifest["files"])!=set(NINE_SLOTS)
        or any(not isinstance(n,str) or FILE_RE.fullmatch(n) is None
               for n in manifest["files"].values())
        or len(set(manifest["files"].values()))!=len(NINE_SLOTS)):
        reasons.append("INVALID_TCP_MANIFEST")
    else:
        old={"contract":"phipie-trail-private-probe-manifest/v0.1",
             "test_id":manifest["test_id"],
             "files":{k:manifest["files"][k] for k in ALL_SLOTS}}
        prior=verify_probe_bundle(witness,old,evidence_dir)
        checks.update(prior["checks"])
        if prior["status"]!="LOCAL_PROBE_EVIDENCE_MATCH":
            reasons.append("EIGHT_FILE_BASELINE_HOLD")
        dirfd=None
        try:
            p=Path(evidence_dir)
            if p.is_symlink():
                raise ValueError("symlink directory")
            flags=os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0)
            dirfd=os.open(p,flags)
            st=os.fstat(dirfd)
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError("not directory")
            if os.name=="posix" and (st.st_uid!=os.geteuid() or st.st_mode & 0o077):
                raise PermissionError("directory not private")
            rec,_=_read_dir_file(dirfd,manifest["files"]["tcp_observation"])
            if valid_tcp_record(rec):
                checks["tcp_observation"]="MATCH"
                reported_rate=rec["metrics"]["received_mbps"]
            else:
                checks["tcp_observation"]="HOLD"
                reasons.append("TCP_EVIDENCE_MISMATCH")
        except (OSError,ValueError,TypeError,UnicodeError,OverflowError,PermissionError):
            checks["tcp_observation"]="HOLD"
            reasons.append("TCP_UNREADABLE_OR_UNSAFE")
        finally:
            if dirfd is not None:
                os.close(dirfd)
    complete=not reasons and all(v=="MATCH" for v in checks.values())
    result={
        "contract":CONTRACT,
        "status":"LOCAL_TCP_EVIDENCE_MATCH" if complete else "HOLD",
        "reasons":sorted(set(reasons)),
        "checks":checks,
        "reported_receiver_mbps":reported_rate if complete else None,
        "witness_sha256":_hash(witness),
        "manifest_sha256":_hash(manifest),
        "local_report_consistency_only":True,
        "actual_link_path_verified":False,
        "hard_rate_limit_guaranteed":False,
        "hardware_qualified":False,
        "physical_hardware_qualified":False,
        "receiver_identity_attested":False,
        "server_identity_attested":False,
        "mesh_transport_verified":False,
        "end_to_end_capacity_qualified":False,
        "network_change_authorized":False,
        "rover_motion_authorized":False,
        "physical_deployment_authorized":False,
    }
    result["assessment_sha256"]=_hash(result)
    return result
