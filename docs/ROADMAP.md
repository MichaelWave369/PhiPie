# PhiPie Roadmap

Each rung should remain small enough to fail clearly.

| Rung | State | Goal | Exit signal |
| --- | --- | --- | --- |
| **PHIPIE-00** | complete | Platform contract + repo skeleton | docs + structural CI |
| **PHIPIE-01** | complete | ARM64 software CI | PhiOS/PhiShell native ARM64 test evidence |
| **PHIPIE-02** | complete | Minimal image builder | versioned ARM64 image artifact + provenance |
| **PHIPIE-03** | field candidate | Raspberry Pi 5 boot | two real-board boots + retained evidence |
| **PHIPIE-04** | blocked by PHIPIE-03 | PhiOS runtime | PhiOS core services execute on board |
| **PHIPIE-05** | planned | PhiShell desktop | qualified display/input/session path |
| **PHIPIE-06** | planned | Headless node mode | bounded remote status/control |
| **PHIPIE-07** | planned | Mission sandbox | isolated bounded mission execution |
| **PHIPIE-08** | planned | Vessie bridge | governed discovery + mission submission |
| **PHIPIE-09** | planned | First PhiBot | one role completes a mission with receipts |
| **PHIPIE-10** | planned | Think Tank | multiple roles preserve independent evidence |
| **PHIPIE-11** | planned | Reliable updates | atomic/A-B update + rollback evidence |
| **PHIPIE-12** | planned | CM5 appliance | separate Compute Module 5 qualification |
| **PHIPIE-13** | planned | Production security | signed boot/encrypted state/provisioning evaluation |

No later rung is implied by completion of an earlier rung.

PHIPIE-03 is intentionally different from the first three rungs: CI can produce a
qualified *field candidate*, but only physical Raspberry Pi 5 observations can complete
the rung.
