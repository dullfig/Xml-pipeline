# AgentServer v2.1 — Core Architectural Principles
**January 06, 2026**  
**Architecture: Autonomous Schema-Driven, Turing-Complete Multi-Agent Organism**

These principles are the single canonical source of truth for the project. All documentation, code, and future decisions must align with this file. This version incorporates Message Pump v2.1 parallelism and refines agent iteration patterns for blind, name-oblivious self-routing.

## Identity & Communication
- All traffic uses the universal `<message>` envelope defined in `envelope.xsd` (namespace `https://xml-pipeline.org/ns/envelope/v1`).
- Mandatory `<from/>` and `<thread/>` (opaque UUID strings; system privately maps to hierarchical paths for subthreading and audit trails).
- Optional `<to/>` (for rare direct routing; most flows use payload root tag with broadcast semantics).
- Exclusive C14N on ingress and egress.
- Malformed XML repaired on ingress; repairs logged in `<huh/>` metadata.

## Identity Injection & Handler Purity
- Handlers are pure, stateless functions with no knowledge of routing, thread context, their own registered name, or organism topology.
- On ingress (external or gateway messages): `<from>` is provided and authenticated by the client/gateway (enforced by envelope validation).
- On response generation (after handler execution and multi-payload extraction):
  - The message pump injects `<from>` using the executing listener's registered name (e.g., "calculator.add" or "researcher").
  - For meta/primitive responses: `<from>` is injected as "core".
- `<thread>` is inherited from the incoming message (or assigned/updated for primitives like spawn-thread).
- `<to>` remains optional and rarely used.
- This ensures every enveloped message has a trustworthy, auditable `<from>` without handler involvement, preventing spoofing and keeping capability code minimal/testable.

## Configuration & Composition
- YAML file (`organism.yaml`) is the bootstrap source of truth, loaded at startup.
- Defines initial listeners, agents, gateways, meta privileges, OOB channel configuration, and routing table (including multiple listeners per root tag).
- LLM-based agents must use unique root tags (enforced on registration/hot-reload) to enable blind self-iteration.
- Runtime structural changes (add/remove listeners, rewire agents, etc.) via local-only privileged commands on the dedicated OOB channel (hot-reload capability).
- No remote or unprivileged structural changes ever.

## Autonomous Schema Layer
- Listeners defined by `@xmlify`-decorated dataclass (payload contract) + pure handler function.
- Mandatory human-readable description string (short "what this does" blurb for tool prompt lead-in).
- Registration (at startup or via hot-reload) automatically generates:
  - XSD cached on disk (`schemas/<name>/v1.xsd`)
  - Example XML
  - Tool description prompt fragment (includes description, params with field docs if present, example input)
- All capability namespaces under `https://xml-pipeline.org/ns/<category>/<name>/v1`.
- Root element derived from payload class name (lowercase) or explicit.
- Multiple listeners may register for the same root tag (enabling broadcast parallelism); LLM agents require unique root tags.

## Message Pump
- Parallel preprocessing pipelines (one per registered listener): ingress → repair → C14N → envelope validation → payload extraction → XSD validation → deserialization → error injection on failure.
- Central async message pump orchestrates:
  - Gathering ready messages from pipeline outputs
  - Routing lookup: direct (`<to/>`) or broadcast (all listeners for root tag; unique roots naturally self-route for agents)
  - Launching concurrent thin dispatchers (`await handler(msg)`)
  - Response processing: multi-payload extraction (dummy wrap → parse → extract), envelope creation with `<from>` injection, re-injection to target pipelines
- Thin, stateless dispatcher: pure async delivery mechanism with no loops or orchestration.
- Supports true parallelism: pipeline preprocessing concurrent, broadcast handlers concurrent via asyncio.gather.
- Validation failures inject `<huh>` error elements (LLM-friendly self-correction).
- Message pump tracks token budgets per agent and thread, enforcing limits and preventing abuse. The LLM abstraction layer informs the message bus on actual token usage.
- Message pump uses asynchronous non-blocking I/O for maximum throughput, with provisions for concurrency limits, fair scheduling, and backpressure.

## Reasoning & Iteration
- LLM agents iterate via blind self-calls: with unique root tags, emitting payloads using their own root tag automatically routes back to themselves—no `<to/>`, name knowledge, or special primitives required.
- This enables natural looping, multi-step continuation, and parallelism via multi-payload emission (e.g., simultaneous tool calls or branched reasoning).
- Conversation thread = complete memory and audit trail (all messages logged).
- Subthreading natively supported via private hierarchical path registry (system appends/prunes listener names on delegation/responses; agents see only opaque UUIDs).
- Optional structured constructs like `<todo-until/>` are encouraged in visible reasoning text (e.g., inside `<answer>`) for planning clarity and auditability but are not system-interpreted.
- Broadcast enables natural parallelism (e.g., simultaneous tool calls) without agent-managed fan-out.
- Thread path privacy: Agents remain oblivious to topology, preventing leakage or probing.
- No hidden loops or state machines; all reasoning steps are visible messages.

## Security & Sovereignty
- Privileged messages (per `privileged-msg.xsd`) handled exclusively on dedicated OOB channel.
- OOB channel bound to localhost by default (safe for local GUI); separate port/socket from main bus.
- Main message pump and dispatcher oblivious to privileged operations — no routing or handling for privileged roots.
- Remote privileged attempts impossible (channel not exposed); any leak to main port logged as security event and dropped.
- Ed25519 identity key used for envelope signing, federation auth, and privileged command verification.
- No agent may modify organism structure, register listeners, or access host resources beyond declared scope.
- Opaque thread UUIDs + private path registry prevent topology disclosure.
- “No Paperclippers” manifesto injected as first system message for every LLM-based listener.

### Privileged Operations
- Privileged messages (per `privileged-msg.xsd`) handled exclusively on dedicated OOB channel.
- OOB channel bound to localhost by default (safe for local GUI); separate port/socket from main bus.
- Main message pump and dispatcher oblivious to privileged operations – no routing or handling for privileged roots.
- Remote privileged attempts impossible (channel not exposed); any leak to main port logged as security event and dropped.

### Identity & Cryptography
- Ed25519 identity key used for envelope signing, federation auth, and privileged command verification.
- All traffic on main bus uses mandatory WSS (TLS) + TOTP authentication.

### Handler Isolation (NEW)
- **Handlers are untrusted code** running in coroutine sandboxes with minimal context.
- Security-critical metadata (sender identity, thread path, routing) captured in coroutine scope before handler execution.
- Handler output never trusted for identity, routing, or thread context – all envelope metadata injected from coroutine-captured state.
- Even compromised handlers cannot forge messages, escape threads, or discover topology beyond declared peers.

### Topology Privacy
- Opaque thread UUIDs prevent topology disclosure to handlers and agents.
- Private path registry maps UUIDs to hierarchical paths (e.g., `agent.tool.subtool`) for routing and audit.
- Agents receive only opaque UUIDs; system maintains authoritative path mapping.
- Peers list enforces capability boundaries: agents can only call declared tools.

### Anti-Paperclip Guarantees
- No persistent cross-thread memory (threads are ephemeral audit trails).
- Token budgets per thread enforce computational bounds.
- Thread pruning on delegation return prevents state accumulation.
- All agent reasoning visible in message history (no hidden state machines).
- "No Paperclippers" manifesto injected as first system message for every LLM-based listener.

### Audit & Forensics
- Complete message history per thread provides full audit trail.
- Privileged introspection (via OOB) can map UUID→path for forensics without exposing to agents.
- All structural changes (hot-reload, listener registration) logged as audit events on main bus.

## Federation
- Gateways declared in YAML with trusted remote public key.
- Remote tools referenced by gateway name in agent tool lists.
- Regular messages flow bidirectionally; privileged messages never forwarded or accepted.

## Introspection (Meta)
- Controlled via YAML flags (`allow_list_capabilities`, `allow_schema_requests`, etc.).
- Supports `request-schema`, `request-example`, `request-prompt`, `list-capabilities`.
- Remote meta queries optionally allowed per YAML (federation peers).

## Technical Constraints
- Mandatory WSS (TLS) + TOTP on main port.
- OOB channel WSS or Unix socket, localhost-default.
- Internal: lxml trees → XSD validation → xmlable deserialization → dataclass → handler → bytes → dummy extraction → multi-envelope re-injection.
- Single process, async non-blocking.
- XML is the sovereign wire format; everything else is implementation detail.

## Scheduled Computation
- Timers and delays implemented as normal listeners using async sleeps.
- Caller idles naturally; wakeup messages bubble back via standard tracing.
- Enables recurrent tasks (e.g., periodic monitoring) without blocking or external schedulers.

## Bounded Stateful Listeners
- Pure tools remain stateless.
- Stateful capabilities (e.g., calculator memory, game state) store data per thread path UUID.
- Ensures isolation across conversations, automatic cleanup on idle, and minimal mutable state.
- Handler closes over or receives UUID for access — still oblivious to readable path.

## Resource Stewardship 
- The Message Pump ensures fair execution and prevents "Paperclip" runaway scenarios via Thread-Level Scheduling and Concurrency Controls. Every thread is subject to Token-Rate Monitoring and Fair-Share Queuing, ensuring that a high-volume agent cannot block high-priority events or starve simpler organs.

These principles are now locked for v2.1. The Message Pump v2.1 specification remains the canonical detail for pump behavior. Future changes require explicit discussion and amendment here first.

## Handler Trust Boundary & Coroutine Isolation

Handlers are treated as **untrusted code** that runs in an isolated coroutine context. 
The message pump maintains authoritative metadata in coroutine scope and never trusts 
handler output to preserve security-critical properties.

### Coroutine Capture Pattern

When dispatching a message to a handler, the pump captures metadata in coroutine scope 
BEFORE handler execution:
```python
async def dispatch(msg: ParsedMessage):
    # TRUSTED: Captured before handler runs
    thread_uuid = msg.thread_id
    sender_name = msg.listener_name  
    thread_path = path_registry[thread_uuid]
    parent = get_parent_from_path(thread_path)
    allowed_peers = registry.get_listener(sender_name).peers
    
    # UNTRUSTED: Handler executes with minimal context
    response_bytes = await handler(
        payload=msg.deserialized_payload,
        meta=HandlerMetadata(thread_id=thread_uuid)  # Opaque UUID only
    )
    
    # TRUSTED: Coroutine scope still has authoritative metadata
    # Process response using captured context, not handler claims
    await process_response(
        response_bytes,
        actual_sender=sender_name,     # From coroutine, not handler
        actual_thread=thread_uuid,     # From coroutine, not handler  
        actual_parent=parent,          # From coroutine, not handler
        allowed_peers=allowed_peers    # From registration, not handler
    )
```

### What Handlers Cannot Do

Even compromised or malicious handlers cannot:

- **Forge identity**: `<from>` is always injected from coroutine-captured sender name
- **Escape thread context**: `<thread>` is always from coroutine-captured UUID
- **Route arbitrarily**: `<to>` is computed from coroutine-captured peers list and thread path
- **Access other threads**: UUIDs are opaque; path registry is private
- **Discover topology**: Only peers list is visible; no access to path structure
- **Spoof system messages**: `<from>core</from>` only injectable by system, never handlers

### What Handlers Can Do

Handlers can only:

- **Call declared peers**: Emit XML matching peer schemas (validated against peers list)
- **Self-iterate**: Emit `<todo-until>` (routes back to sender automatically)
- **Return to caller**: Emit any other payload (routes to parent in thread path)
- **Access thread-scoped storage**: Via opaque UUID (isolated per delegation chain)

### Response Processing Security

Handler output (raw bytes) undergoes full security processing:

1. **Wrap in dummy tags** and parse with repair mode
2. **Extract payloads** via C14N and XSD validation
3. **Determine routing** using coroutine-captured metadata (never handler claims)
4. **Inject envelope** with trusted `<from>`, `<thread>`, `<to>` from coroutine scope
5. **Re-inject to pipeline** for identical security processing

Any envelope metadata in handler output is **ignored and overwritten**.

### Trust Architecture
```
┌─────────────────────────────────────────────────────┐
│              TRUSTED ZONE (System)                  │
│  • Path registry (UUID → hierarchical path)         │
│  • Listener registry (name → peers, schema)         │
│  • Thread management (pruning, parent lookup)       │
│  • Envelope injection (<from>, <thread>, <to>)      │
└─────────────────────────────────────────────────────┘
                        ↕
            Coroutine Capture Boundary
                        ↕
┌─────────────────────────────────────────────────────┐
│            UNTRUSTED ZONE (Handler)                 │
│  • Receives: typed payload + opaque UUID            │
│  • Returns: raw bytes                               │
│  • Cannot: forge identity, escape thread, probe     │
│  • Can: call peers, self-iterate, return to caller  │
└─────────────────────────────────────────────────────┘
```

This design ensures handlers are **capability-safe by construction**: even fully 
compromised handler code cannot violate security boundaries or topology privacy.
---

This integrates the blind self-iteration pattern cleanly—no contradictions, stronger obliviousness, and explicit guidance on `<todo-until/>`. The unique-root enforcement for agents is called out in Configuration and Schema layers.
