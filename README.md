# AgentServer — The Living Substrate (v2.0)
***"It just works... safely."***

**January 03, 2026**  
**Architecture: Autonomous Schema-Driven, Turing-Complete Multi-Agent Organism**

## What It Is
AgentServer is a production-ready substrate for the `xml-pipeline` nervous system. Version 2.0 stabilizes the design around exact XSD validation, typed dataclass handlers, mandatory hierarchical threading, and strict out-of-band privileged control.

See [Core Architectural Principles](docs/core-principles-v2.0.md) for the single canonical source of truth.

## Core Philosophy
- **Autonomous DNA:** Listeners declare their contract via `@xmlify` dataclasses; the organism auto-generates XSDs, examples, and tool prompts.
- **Schema-Locked Intelligence:** Payloads validated directly against XSD (lxml) → deserialized to typed instances → pure handlers.
- **Multi-Response Tolerance:** Handlers return raw bytes; bus wraps in `<dummy></dummy>` and extracts multiple payloads (perfect for parallel tool calls or dirty LLM output).
- **Computational Sovereignty:** Turing-complete via self-calls, subthreading primitives, and visible reasoning — all bounded by thread hierarchy and local-only control.

## Developer Experience — Create a Listener in 12 Lines
That's it. No manual XML, no schemas, no prompts.

```python
from xmlable import xmlify
from dataclasses import dataclass
from xml_pipeline import Listener, bus  # bus is the global MessageBus

@xmlify
@dataclass
class AddPayload:
    a: int
    b: int

def add_handler(payload: AddPayload) -> bytes:
    result = payload.a + payload.b
    return f"<result>{result}</result>".encode("utf-8")

Listener(
    payload_class=AddPayload,
    handler=add_handler,
    name="calculator.add",
    description="Adds two integers and returns their sum."
).register()  # ← Boom: XSD, example, prompt auto-generated + registered
```

The organism now speaks `<add>` — fully validated, typed, and discoverable.

## Key Features
### 1. The Autonomous Schema Layer
- Dataclass → cached XSD + example + rich tool prompt (mandatory description + field docs).
- Namespaces: `https://xml-pipeline.org/ns/<category>/<name>/v1` (served live via domain for discoverability).

### 2. Thread-Based Lifecycle & Reasoning
- Mandatory `<thread/>` with hierarchical IDs for reliable subthreading and audit trails.
- LLM agents reason via open self-calls and optional `<todo-until/>`.
- All thought steps visible as messages — no hidden state.

### 3. Message Pump
- Single linear pipeline with repair, C14N, XSD validation, deserialization, handler execution, and multi-payload extraction.
- Supports clean tools and forgiving LLM streams alike.
- Thread-base message queue with bounded memory.

### 4. Structural Control
- Bootstrap from `organism.yaml`.
- Runtime changes (hot-reload, add/remove listeners) via local-only OOB channel (localhost WSS or Unix socket — GUI-ready).
- Main bus oblivious to privileged ops.

### 5. Federation & Introspection
- YAML-declared gateways with trusted keys.
- Controlled meta queries (schema/example/prompt/capability list).

## Technical Stack
- **Validation & Parsing:** lxml (XSD, C14N, repair) + xmlable (round-trip).
- **Protocol:** Mandatory WSS (TLS) + TOTP on main port.
- **Identity:** Ed25519 (signing, federation, privileged).
- **Format:** Exclusive C14N XML (wire sovereign).

## Why This Matters
AgentServer v2.0 is a bounded, auditable, owner-controlled organism where the **XSD is the security**, the **thread is the memory**, and the **OOB channel is the sovereignty**.

One port. Many bounded minds. Autonomous yet obedient evolution. 🚀

---
*XML wins. Safely. Permanently.*