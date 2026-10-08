"""Run: python -m trailcore.demo [nominal|degraded|stale]"""
import json
import sys
from .governor import LinkObservation, assess_corridor


def run(scenario="nominal"):
    now = 1000.0  # fixed clock: repeatable, not a real-world timestamp
    path = ["base", "relay-a", "relay-b", "rover"]
    obs = [
        LinkObservation("base", "relay-a", now - 4, 30, 0.1, 18, 10, battery_pct=85, source="example-only"),
        LinkObservation("relay-a", "relay-b", now - 3, 45, 0.2, 11, 10, battery_pct=74, source="example-only"),
        LinkObservation("relay-b", "rover", now - 5, 60, 0.5, 5, 10, source="example-only"),
    ]
    if scenario == "degraded":
        obs[1] = LinkObservation("relay-a", "relay-b", now - 3, 380, 10.0, 0.1, 10, battery_pct=74, source="example-only")
    elif scenario == "stale":
        obs[1] = LinkObservation("relay-a", "relay-b", now - 200, 45, 0.2, 11, 10, battery_pct=74, source="example-only")
    elif scenario != "nominal":
        raise ValueError("scenario must be nominal|degraded|stale")
    return assess_corridor(path, obs, now_s=now,
        permission={"operator_present": True, "site_permission": True},
        rover_health={"last_decision": {"state": "BEACON_READY"},
                      "claim_boundary": {"does_not_grant_motion_authority": True}})


if __name__ == "__main__":
    try:
        print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else "nominal"), indent=2))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
