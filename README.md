# AgentServer — The Living Substrate (v2.1)
***"It just works... safely."***

**January 06, 2026**  
**Architecture: Autonomous Schema-Driven, Turing-Complete Multi-Agent Organism**

## The Rant
**Why XML?**  
[Why not JSON?](docs/why-not-json.md)

XML is the sovereign wire format — standards-based, self-describing, attack-resistant, and evolvable without drift. JSON was a quick hack that escaped into the wild and became the default for everything, including AI tool calling, where its brittleness causes endless prompt surgery and validation headaches.

This project chooses XML deliberately. The organism enforces contracts exactly (XSD validation, no transcription bugs), tolerates dirty streams (repair + dummy extraction), and keeps reasoning visible. No fragile conventions. No escaping hell. Just bounded, auditable computation.

Read the full rant [here](docs/why-not-json.md) for the history, pitfalls, and why XML wins permanently.

## What It Is
AgentServer is a production-ready substrate for the `xml-pipeline` nervous system. Version 2.1 evolves the design around parallel per-listener pipelines, true concurrent broadcast, opaque UUID threading for privacy, and blind agent self-iteration—all while preserving strict validation and handler purity.

See [Core Architectural Principles](docs/core-principles-v2.1.md) for the single canonical source of truth.

## Core Philosophy
- **Autonomous DNA:** Listeners declare their contract via `@xmlify` dataclasses; the organism auto-generates XSDs, examples, and tool prompts.
- **Schema-Locked Intelligence:** Payloads validated directly against XSD (lxml) → deserialized to typed instances → pure handlers.
- **Multi-Response Tolerance:** Handlers return raw bytes; bus wraps in `<dummy></dummy>` and extracts multiple payloads (perfect for parallel tool calls or dirty LLM output).
- **Computational Sovereignty:** Turing-complete via blind self-calls, subthreading primitives, concurrent broadcast, and visible reasoning — all bounded by private thread hierarchy and local-only control.

## Developer Experience — Create a Listener in 12 Lines
**No manual schemas. No brittle JSON conventions. No hand-written prompts.**  
Just declare a dataclass contract and a one-line human description. The organism handles validation, XSD, examples, and tool prompts automatically.

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

The organism now speaks `<add>` — fully validated, typed, and discoverable.<br/>
Unlike rigid platforms requiring custom mappings or fragile item structures, this is pure Python — typed, testable, and sovereign.

## Security Model

AgentServer's security is **architectural**, not bolted-on:

### Two Completely Isolated Channels
- **Main Bus**: Standard `<message>` envelope, all traffic undergoes identical validation pipeline regardless of source
- **OOB Channel**: Privileged commands only, different schema, localhost-bound, used for structural changes

### Handler Isolation & Trust Boundary
**Handlers are untrusted code.** Even compromised handlers cannot:
- Forge their identity (sender name captured in coroutine scope before execution)
- Escape thread context (thread UUID captured in coroutine, not handler output)
- Route to arbitrary targets (routing computed from peers list, not handler claims)
- Access other threads' data (opaque UUIDs, private path registry)
- Discover topology (only declared peers visible)

The message pump maintains authoritative metadata in coroutine scope and **never trusts handler output** for security-critical properties.

### Closed-Loop Validation
ALL messages on the main bus undergo identical security processing:
- External ingress: WSS → pipeline → validation
- Handler outputs: bytes → pipeline → validation (same steps!)
- Error messages: generated → pipeline → validation
- System notifications: generated → pipeline → validation

No fast-path bypasses. No "trusted internal" messages. Everything validates.

### Topology Privacy
- Agents see only opaque thread UUIDs, never hierarchical paths
- Private path registry (UUID → `agent.tool.subtool`) maintained by system
- Peers list enforces capability boundaries (no ambient authority)
- Federation gateways are opaque abstractions

### Anti-Paperclip Architecture
- Threads are ephemeral (complete audit trail, then deleted)
- No persistent cross-thread memory primitives
- Token budgets enforce computational bounds
- Thread pruning prevents state accumulation
- All reasoning visible in message history

This architecture ensures:<br>
✅ No privilege escalation (handlers can't forge privileged commands)<br>
✅ No fast-path bypasses (even system-generated messages validate)<br>
✅ Physical separation (privileged and regular traffic cannot mix)<br>
✅ Capability-safe handlers (compromised code still bounded by peers list)<br>
✅ Complete auditability (thread history is ground truth)


## Key Features
### 1. The Autonomous Schema Layer
- Dataclass → cached XSD + example + rich tool prompt (mandatory description + field docs).
- Namespaces: `https://xml-pipeline.org/ns/<category>/<name>/v1` (served live via domain for discoverability).
- Multiple listeners per root tag supported (broadcast parallelism).

### 2. Thread-Based Lifecycle & Reasoning
- Opaque `<thread/>` UUIDs with private hierarchical path registry for reliable subthreading, audit trails, and topology privacy.
- LLM agents use unique root tags for blind self-iteration (no name knowledge or `<to/>` needed).
- Agents reason via open self-calls, multi-payload parallelism, and optional `<todo-until/>` scaffolding in visible text.
- All thought steps visible as messages — no hidden state.

### 3. Message Pump
- Parallel preprocessing pipelines (one per listener) with central async pump orchestration.
- True concurrency: pipeline tasks parallel, broadcast handlers via asyncio.gather.
- Single linear flow per pipeline with repair, C14N, XSD validation, deserialization, handler execution, and multi-payload extraction.
- Supports clean tools, forgiving LLM streams, and natural broadcast alike.
- Thread-based message queue with bounded memory and fair scheduling.

### 4. Structural Control
- Bootstrap from `organism.yaml` (including unique root enforcement for agents).
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
AgentServer v2.1 is a bounded, auditable, owner-controlled organism where the **XSD is the security**, the **private thread registry is the memory**, and the **OOB channel is the sovereignty**.

One port. Many bounded minds. Autonomous yet obedient evolution. 🚀

---
*XML wins. Safely. Permanently.*
