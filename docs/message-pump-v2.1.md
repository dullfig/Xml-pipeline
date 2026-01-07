**AgentServer v2.1 — Message Pump & Pipeline Architecture**

This document is the canonical specification for the AgentServer message pump in v2.1.  
The previous version dated January 06, 2026 is hereby superseded.  
All implementation must conform to this architecture.

---

### Core Model

- **Pipeline-per-listener** — each registered listener owns one dedicated preprocessing pipeline.
- **Permanent system pipeline** — always exists at bootstrap, even with zero user listeners.
- **Configurable ordered steps** — each pipeline is an ordered list of async coroutine functions that transform a universal `MessageState`.
- **Routing resolution inside pipeline** — routing is just another step; the dispatcher receives fully routed messages.
- **Dumb dispatcher** — only awaits handler(s) and processes responses.
- **Hard-coded multi-payload extraction** — handler responses are specially processed outside normal pipelines to support 1..n emitted payloads.

---

### Universal Intermediate Representation: MessageState

```python
@dataclass
class MessageState:
    raw_bytes: bytes | None = None          # Initial ingress or extracted payload bytes
    envelope_tree: Element | None = None    # Full <message> envelope after repair/C14N
    payload_tree: Element | None = None     # Extracted payload element
    payload: Any | None = None              # Deserialized @xmlify dataclass instance
    thread_id: str | None = None            # Opaque UUID inherited/carried
    from_id: str | None = None              # Registered name of sender (trustworthy)
    target_listeners: list[Listener] | None = None  # Resolved by routing step
    error: str | None = None                # Diagnostic message if step fails
    metadata: dict[str, Any] = field(default_factory=dict)  # Extension point
```

Every pipeline step receives and returns a `MessageState`.

---

### Default Listener Pipeline Steps (in order)

```python
default_listener_steps = [
    repair_step,                    # raw_bytes → envelope_tree (lxml recovery)
    c14n_step,                      # normalize envelope_tree
    envelope_validation_step,       # validate against envelope.xsd
    payload_extraction_step,        # set payload_tree
    xsd_validation_step,            # validate against listener's cached XSD
    deserialization_step,           # set payload (dataclass instance)
    routing_resolution_step,        # set target_listeners based on root tag
]
```

Each step is an `async def step(state: MessageState) -> MessageState`.

---

### System Pipeline (fixed, shorter steps)

```python
system_steps = [
    repair_step,
    c14n_step,
    envelope_validation_step,
    payload_extraction_step,
    system_routing_and_handler_step,   # handles unknown roots, meta, leaked privileged, boot, emits <huh> or system messages
]
```

The system pipeline is instantiated at organism bootstrap and never removed.

---

### Pipeline Execution (shared by all pipelines)

```python
async def run_pipeline(state: MessageState, pipeline: Pipeline):
    for step in pipeline.steps:
        try:
            state = await step(state)
            if state.error:                        # early diagnostic
                break
        except Exception as exc:
            state.error = f"Pipeline step {step.__name__} failed: {exc}"
            break

    if state.target_listeners:
        await dispatcher(state)
    else:
        # Unroutable → send to system pipeline for <huh>
        await system_pipeline.process(state)
```

Pipelines run concurrently; messages within a single pipeline are processed sequentially.

---

### Handler Response Processing (hard-coded path)

After dispatcher awaits a handler:

```python
response_bytes = await handler(state.payload, metadata)

# Safety guard
if response_bytes is None or not isinstance(response_bytes, bytes):
    response_bytes = b"<huh>Handler failed to return valid bytes — likely missing return or wrong type</huh>"

# Dedicated multi-payload extraction (hard-coded, tolerant)
payloads_bytes_list = await multi_payload_extract(response_bytes)

for payload_bytes in payloads_bytes_list:
    # Create fresh initial state for each emitted payload
    new_state = MessageState(
        raw_bytes=payload_bytes,
        thread_id=state.thread_id,                    # inherited
        from_id=current_listener.name,                # provenance injection
    )
    # Route through normal pipeline resolution (root tag lookup)
    await route_and_process(new_state)
```

`multi_payload_extract` wraps in `<dummy>` (idempotent), repairs/parses, extracts all root elements, returns list of bytes. If none found → single diagnostic `<huh>`.

---

### Routing Resolution Step

Inside the pipeline, after deserialization:

- Compute root tag = `{state.from_id.lower()}.{type(state.payload).__name__.lower()}`
- Lookup in primary routing table (root_tag → Listener)
- If found → `state.target_listeners = [listener]`
- If broadcast case matches → `state.target_listeners = list_of_matching_listeners`
- Else → `state.error = "Unknown capability"`

Agents calling peers: pump enforces payload root tag is in allowed peers list (or broadcast group when we add it).

---

### Dispatcher (dumb fire-and-await)

```python
async def dispatcher(state: MessageState):
    if not state.target_listeners:
        return

    if len(state.target_listeners) == 1:
        await process_single_handler(state)
    else:  # broadcast
        tasks = [
            process_single_handler(state, listener_override=listener)
            for listener in state.target_listeners
        ]
        for future in asyncio.as_completed(tasks):
            await future   # responses processed immediately as they complete
```

`process_single_handler` awaits the handler and triggers the hard-coded response processing path above.

---

### Key Invariants (v2.1)

1. One dedicated pipeline per registered listener + permanent system pipeline.
2. Pipelines are ordered lists of async steps operating on universal `MessageState`.
3. Routing resolution is a normal pipeline step → dispatcher receives pre-routed targets.
4. Handler responses go through hard-coded multi-payload extraction → each payload becomes fresh `MessageState` routed normally.
5. Provenance (`<from>`) and thread continuity injected by pump, never by handlers.
6. `<huh>` guards protect against missing returns and step failures.
7. Extensibility: new steps (token counting, rate limiting, logging) insert anywhere in default list.

---

### Future Extensions (not v2.1)

- Hot-reload replace pipeline step list per listener
- Broadcast groups via `group:` YAML key (v2.2 candidate)
- Per-thread token bucket enforcement step

---

This specification is now aligned with listener-class-v2.1.md and configuration-v2.1.md.  
The message pump is simple, auditable, high-throughput, and infinitely extensible via pipeline steps.

