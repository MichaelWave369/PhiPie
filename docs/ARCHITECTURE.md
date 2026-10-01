# Architecture

## System view

```text
Human / Vessie / PhiBot / local client
                 │
                 ▼
          PhiOS authority boundary
                 │
         ┌───────┴────────┐
         │                │
      PhiShell        governed APIs
         │                │
         └───────┬────────┘
                 ▼
             PhiOS Core
   Spine / Memory / Ledger / Apps /
   Covenant / Reality / MCP / Reflex
                 │
                 ▼
        PhiPie platform adapter
                 │
   ┌─────────────┼─────────────┐
   │             │             │
 storage      graphics      networking
   │             │             │
   └─────────────┼─────────────┘
                 ▼
          ARM64 Linux layer
                 │
                 ▼
        Pi-family hardware
```

## Image composition

The planned image system is layered rather than a monolithic shell script.

```text
hardware base
    +
PhiOS package source/pin
    +
PhiPie platform configuration
    +
desktop or node profile
    +
governance defaults
    =
versioned ARM64 image artifact
```

The exact image builder is intentionally not locked by PHIPIE-00. PHIPIE-02 will select and pin the builder as an implementation dependency.

## Runtime plane

A future PhiPie agent mission should be expressed as a bounded request, not an unrestricted login.

```text
mission
  ↓
identity check
  ↓
authority evaluation
  ↓
resource/network/filesystem sandbox
  ↓
tool execution
  ↓
artifacts + receipts
  ↓
teardown
```

## Agent abstraction

A PhiBot is not a model.

```text
PhiBot =
  identity
+ role
+ authority
+ mission
+ tools
+ memory scope
+ budgets
+ receipts
+ optional model provider
```

This allows a PhiBot to move between PhiOS Live, desktop PhiOS and PhiPie without collapsing identity into the host machine or model backend.

## Update direction

The long-term target is an atomic or A/B-style system update model with independently persistent governed state. That mechanism is **not implemented or qualified yet**.
