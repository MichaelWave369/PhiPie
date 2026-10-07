# Raspberry Pi Read-Only Telemetry v0.1

Status: **experimental / non-qualifying**

This slice gives PhiPie its first host-specific observation adapter after the generic physical-host I/O boundary.

It is deliberately **read-only**.

No GPIO output, relay, motor, battery control, fan control, power switching, or other physical action is added by this work.

## Goal

Read locally available Raspberry Pi / Linux host telemetry and turn it into a receipt without silently promoting those observations into safety authority.

```text
Pi / Linux host
     |
     +-- device tree
     +-- /proc
     +-- /sys
     +-- optional vcgencmd
          |
          v
RaspberryPiTelemetryAdapter
          |
          v
read-only snapshot
          |
          v
PiTelemetryObserver
          |
          v
local receipt chain
```

## Observed fields

When available:

- Raspberry Pi model and compatibility strings;
- board serial as a SHA-256 fingerprint, not raw serial text;
- machine ID as a SHA-256 fingerprint;
- CPU temperature;
- uptime;
- 1 / 5 / 15 minute load averages;
- total and available memory;
- network interface name, operstate, and carrier only;
- Raspberry Pi `vcgencmd get_throttled` raw status plus decoded flags;
- Raspberry Pi `vcgencmd measure_volts core` observation.

No IP address, MAC address, SSID, route table, or remote endpoint is collected.

## Provenance

Every snapshot carries the source used for each field, including the relevant `/proc`, `/sys`, device-tree path, or fixed `vcgencmd` invocation.

Missing data remains missing. The adapter does not invent a healthy value.

## Authority boundary

These observations are **not calibrated Plane A safety inputs**.

For example, an observed CPU temperature means only that the operating system reported that value through the selected source. It does not qualify the sensor, thermal path, enclosure, threshold, or device for a safety claim.

Likewise, `vcgencmd get_throttled = 0x0` does not prove that the external power source is electrically qualified.

## Privacy boundary

Raw board serial and machine ID values are not written into the telemetry snapshot. They are reduced to SHA-256 fingerprints so repeated observations can be correlated locally without casually emitting the raw identifiers.

Network observation is limited to interface name, carrier, and operstate.

## Negative controls

Tests prove that:

1. missing telemetry is reported as unavailable rather than fabricated;
2. a non-Pi host is not declared to be a Raspberry Pi;
3. observing Pi telemetry does not change the host safety state;
4. the telemetry adapter exposes no actuator execution method;
5. raw serial and machine-ID values are not emitted;
6. only fixed, read-only `vcgencmd` commands are invoked.

## Run on a Pi

From the repository root:

```bash
python -m runtime.physical_host.pi_telemetry --pretty
```

The command exits successfully even when optional telemetry is unavailable and reports warnings in the JSON output.

## Boundary

```text
OS telemetry != calibrated sensor
Pi detected != Pi 5 qualification
temperature visible != thermal qualification
voltage visible != power qualification
throttled=0x0 != electrical certification
read-only adapter != actuator authority
receipt != independent verification
```

PHIPIE-03 remains the active Raspberry Pi 5 hardware field-candidate rung.
