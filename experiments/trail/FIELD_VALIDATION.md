# ΦTrail physical qualification plan

**Nothing in this document reports completed field testing.** Lab/software
results must not be promoted to radio coverage, physical safety or emergency
communications claims.

## Stage 0: deterministic software (this PR)

- Run the offline scenarios and adversarial tests on Linux / Windows / Pi.
- Prove malicious or malformed observations HOLD, and all outputs reject
  actuation permissions even when metrics are nominal.
- Capture test logs, git commit SHA, Python version and source hashes.

## Stage 1: two physically owned PhiPies, stationary and supervised

- Authenticate each device identity *outside* this prototype.
- Establish a real legal/authorized backhaul; record radio hardware, firmware,
  interfaces, antennas, channel/width, topology and transmit-power constraints.
- Measure actual per-hop RTT, loss and TCP/UDP throughput against both idle and
  loaded conditions, with repeatable sample windows and timestamps.
- Measure power draw/battery depletion; retain raw measurements separately
  from the advisory results.
- Run disconnected and interference/degradation cases. **No remote router writes**.

## Stage 2: three stationary nodes and fail/recover

- Add a relay and show the true multi-hop transport separately from the
  observer. Verify path reachability and routing with independent tools.
- Induce relay power loss, intermittent links, stale readings, topology changes
  and operator absence. Every degraded/unknown case should HOLD.
- Confirm reconnect and recovery without unauthorized configuration changes.
- Check effect of additional hop on *actual* end-to-end performance. The
  summed-latency proxy is not proof of that performance.

## Stage 3: Park Rover *survey vehicle only*

- Use operator-controlled or stationary rover with existing E-stop,
  independent safety spine, geofence/spotter and site permission.
- Observe its beacon from an independently authenticated connection.
- Map measured RF conditions while moving, but make no autonomous relay
  placement, remote drive, or unattended operation claims.
- Log observations and review proposed relay locations manually.

## Stage 4: separate deployment approval research

Only after radio, field safety, land access, regulatory, security, battery,
cryptographic provenance and failure/rollback evaluations may an independent
authorization design be considered. **This PR implements none of that stage.**

## Field receipt minimum

Date/site authorization ID; operator and observer roles; node identities;
firmware and radio configuration; test topology; actual measurement commands
and units; raw samples; source clocks; link states; power snapshots; weather/
terrain notes; failures; refusal reasons; results; and caveats. Minimize
bystander/location data and protect keys/secrets.

Do not market this as safety-critical or emergency coverage. Carry reliable
off-grid communications appropriate to the trip.
