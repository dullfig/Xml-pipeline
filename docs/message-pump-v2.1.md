
# Message Pump Architecture v2.1
**January 06, 2026**  
**AgentServer: Pipeline-per-Listener + Dispatcher Pattern**

This document is the canonical specification for the AgentServer message pump. All implementation must conform to this architecture.

---

## Core Pattern: Dictionary of Pipelines → Message Pump → Dispatcher

The message pump implements a three-stage architecture:

1. **Pipeline Stage**: Parallel preprocessing pipelines (one per registered listener) that sanitize, validate, and prepare messages
2. **Message Pump**: Async event loop that orchestrates concurrent message processing, manages scheduling and backpressure
3. **Dispatcher**: Simple async function that delivers messages to handlers and awaits responses

```
Raw Message Ingress
    ↓
Pipeline Lookup & Assignment
    ↓
[Pipeline 1]  [Pipeline 2]  [Pipeline N]  (parallel preprocessing)
    ↓              ↓              ↓
Pipeline Output Queues (processed messages ready for dispatch)
    ↓
Message Pump Event Loop
  - Gathers ready messages
  - Launches concurrent dispatcher(msg, handler) invocations
  - Manages concurrency/scheduling/backpressure
    ↓
[dispatcher()]  [dispatcher()]  [dispatcher()]  (concurrent, async)
    ↓                ↓                ↓
Handler Execution → await Response
    ↓
Message Pump Response Processing
  - Extract multi-payloads (dummy wrap → parse → extract)
  - Create envelopes with <from> injection
  - Re-inject to appropriate pipelines
    ↓
Pipeline Re-injection (cycle continues)
```

---

## Pipeline Architecture

### Pipeline Registration

At boot (or hot-reload), each listener registration creates:
- Dedicated preprocessing pipeline instance
- Entry in routing table: `Dict[root_tag, Dict[listener_name, Pipeline]]`
- Cached XSD schema (derived from `@xmlify` dataclass)
- Example XML and tool description fragments

**Example Registration**:
```python
@xmlify
@dataclass
class CalculatorAdd:
    """Add two numbers and return the sum."""
    a: float
    b: float

# Creates:
# - Pipeline instance for "calculator/add"
# - XSD cached at schemas/calculator/add/v1.xsd
# - Routing entry: pipelines["add"]["calculator"] = pipeline_instance
```

### Pipeline Structure

Each pipeline is identical in structure but operates on messages bound for its specific listener. A pipeline consists of an ordered array of processing tasks:

**Standard Task Sequence**:
1. **Repair**: Fix malformed XML (lxml recovery mode)
2. **Canonicalization (C14N)**: Normalize whitespace, attributes, namespaces
3. **Envelope Validation**: Verify against `envelope.xsd`
4. **Payload Extraction**: Extract payload from `<message>` wrapper
5. **XSD Validation**: Validate payload against listener's cached schema
6. **Deserialization**: Convert XML to typed `@dataclass` instance via `xmlable.from_xml`
7. **Error Injection**: On failure, inject `<huh>` error tag instead of discarding

**Error Handling Philosophy**:
- Early pipelines (repair, C14N): May discard truly corrupt messages
- Later stages (validation): Inject `<huh>error description</huh>` into response
- LLMs see their errors and can self-correct
- Prevents silent failures while maintaining flow

### System Pipeline

A special system pipeline handles messages not bound for user listeners:
- Processes `<boot/>` messages (startup trigger for human/keyboard listeners)
- Handles system-generated error responses
- Uses same task sequence but no XSD validation step

---

## Dispatcher Architecture

### Dispatcher Responsibilities

The dispatcher is a **simple async function** that delivers a message to a handler and awaits the response:

```python
async def dispatcher(msg, handler):
    """Thin async routing layer - delivers message and awaits response"""
    response = await handler(msg)
    return response
```

**Critical Property**: The dispatcher itself has no loop, no queue management, no concurrency control. It's a pure async delivery mechanism. All orchestration happens in the message pump.

### Routing Logic

**Lookup Key**: `(root_tag, listener_name)` from pipeline's registered listener

**Delivery Rules**:
- **`<to/>` present**: Direct delivery to specific listener at `root_tag/listener_name`
- **`<to/>` absent**: Broadcast to ALL listeners registered for `root_tag`

**Broadcast Semantics**:
- All handlers for a given root tag execute concurrently (via concurrent task launch).
- Responses are processed progressively as each handler completes (streaming/as-completed semantics).
- Each response is fully handled independently (multi-payload extraction, enveloping, re-injection).
- Responses bubble up in completion order (nondeterministic); no waiting for the full group.
- Ideal for racing parallel tools; agents handle any needed synchronization.

**Example**: Message with root tag `<search>` and no `<to/>`:
```
Pump sees: root_tag="search", to=None
Lookup: pipelines["search"] → {"google": pipeline_1, "bing": pipeline_2}
Execute:
  - Launch concurrent dispatchers for all handlers
  - Monitor tasks via asyncio.as_completed
  - As each completes: extract payloads, envelope, re-inject immediately
  - No batch wait—fast responses bubble first
```

---

## Message Pump Event Loop

The message pump is the orchestration layer that manages concurrency, scheduling, and message flow:

```python
async def message_pump():
    """Main event loop - orchestrates concurrent message processing"""
    while True:
        # Gather all ready messages from pipeline outputs
        ready_messages = await gather_ready_messages_from_pipelines()
        
        # For each message, lookup handler(s) and launch dispatcher(s)
        tasks = []
        for msg in ready_messages:
            handlers = lookup_handlers(msg)  # may return multiple for broadcast
            for handler in handlers:
                task = asyncio.create_task(dispatcher(msg, handler))
                tasks.append(task)
        
        # Process responses as they complete (streaming)
        for completed_task in asyncio.as_completed(tasks):
            response = await completed_task
            # Extract multi-payloads (dummy wrap → parse → extract)
            payloads = extract_payloads(response)
            
            # Wrap each in envelope, inject <from>, re-route to pipelines
            for payload in payloads:
                enveloped = create_envelope(payload, response.context)
                await send_to_pipeline(enveloped)
```

**Key Responsibilities**:
1. **Concurrency Control**: Decides how many dispatchers to launch simultaneously
2. **Fair Scheduling**: Can implement priority queues, round-robin, or other fairness policies
3. **Backpressure**: Monitors pipeline queue depths, throttles if needed
4. **Response Handling**: Extracts multi-payloads and re-injects each response as soon as its handler completes (progressive streaming for broadcasts)

**Concurrency Model**: Unbounded concurrent dispatchers; responses stream independently. Future enhancements include per-listener semaphores, global limits, and token-rate throttling.

---

## Message Flow Example: Complete Cycle (Broadcast <search>)

1. **Ingress**: External `<message><thread>root</thread><search query="weather today"/></message>`
2. **Pipeline Assignment**: Root tag "search" → multiple pipelines (google, bing)
3. **Pipeline Processing** (parallel per listener): Repair/C14N/validation/deserialization
4. **Message Pump**: Gathers ready messages, launches concurrent dispatchers
5. **Concurrent Handler Execution**:
   - google_handler completes first (500ms): `<search-result>Sunny, 72°F</search-result>` → processed/bubbled immediately
   - bing_handler completes second (700ms): `<search-result>Clear skies, 70°F</search-result>` → processed/bubbled next
   - No waiting—receiver sees results as they arrive
6. **Response Processing** (progressive): As each completes, extract, envelope with `<from>`, re-inject to target pipeline
7. **Response Bubbling**: Results route back to parent (e.g., researcher/user) in completion order

---

## Boot Sequence

1. On startup, system generates: `<message><from>system</from><thread>root</thread><boot/></message>`
2. Sent to system pipeline
3. Dispatched to ALL listeners registered for `<boot/>` root tag
4. Human listener can register for `<boot/>` to:
   - Display welcome message
   - Await keyboard input
   - Initiate first real conversation

**Example Human Listener**:
```python
@xmlify
@dataclass  
class Boot:
    """System boot notification"""
    pass

async def human_boot_handler(msg: Boot) -> bytes:
    print("System ready. Type your message:")
    user_input = await async_input()
    return f"<message>{user_input}</message>".encode()
```

---

## Out-of-Band (OOB) Privileged Messages

### Separation of Concerns

Privileged operations (defined in `privileged-msg.xsd`) operate on a completely separate channel:
- Dedicated websocket port (or Unix socket)
- Bound to localhost by default
- Uses Ed25519 signature verification

**The message pump dispatcher has NO knowledge of privileged messages**:
- Main dispatcher only routes messages with user/capability payloads
- Privileged messages like `<add-listener>`, `<remove-listener>`, `<hot-reload>` are handled by separate OOB handler
- No possibility of privilege escalation via main message flow

**Security Guarantee**: Remote clients cannot send privileged messages (channel not exposed). Even if leaked to main port, dispatcher would fail routing lookup (no pipeline registered for privileged root tags).

---

## Pipeline Optimization & Scheduling

### Pipeline Parallelism

Pipelines process independently and in parallel:
- Each listener's pipeline can execute simultaneously
- No shared state between pipelines (XSD schemas are cached read-only)
- Enables high throughput for multi-listener broadcasts

### Future: Token-Rate Monitoring

Currently not implemented, but architecture supports:
- Each pipeline tracks tokens processed per minute
- Dispatcher can throttle high-volume agents
- Fair-share scheduling to prevent LLM monopolization

**Placeholder**: Token counting will be integrated once LLM abstraction layer is defined.

---

## Configuration & Wiring

### YAML Bootstrap (`organism.yaml`)

Defines initial swarm topology:
```yaml
listeners:
  - name: calculator
    capability: calculator.add
    root_tag: add
    namespace: https://xml-pipeline.org/ns/tools/calculator/v1
    
  - name: researcher  
    capability: llm.researcher
    root_tag: research-query
    namespace: https://xml-pipeline.org/ns/agents/researcher/v1
    tools:
      - calculator  # researcher can see/call calculator
      - websearch

  - name: websearch
    capability: tools.google_search  
    root_tag: search
    namespace: https://xml-pipeline.org/ns/tools/websearch/v1

agents:
  - name: researcher
    type: llm
    model: claude-sonnet-4
    system_prompt: "You are a research assistant..."
    visible_tools:  # restricts which listeners this agent can call
      - calculator
      - websearch

meta:
  allow_list_capabilities: admin  # or "all", "none"
  allow_schema_requests: admin
```

**Key Properties**:
- Defines initial routing table (`root_tag → listener_name`)
- Controls visibility (agent A may not know agent B exists)
- Meta introspection privileges
- All structural changes require OOB privileged commands (hot-reload)

---

## Summary: Critical Invariants

1. **Pipeline-per-Listener**: Each registered listener has dedicated preprocessing pipeline
2. **Async Concurrency**: Message pump launches concurrent dispatcher invocations; handlers run in parallel via asyncio
3. **Stateless Dispatcher**: Dispatcher is a simple async function `(msg, handler) → response`, no loop or state
4. **Pump Orchestrates**: Message pump event loop controls concurrency, scheduling, backpressure, and response handling
5. **UUID Privacy**: Thread paths are opaque UUIDs; system maintains actual tree privately
6. **Error Injection**: Validation failures inject `<huh>` instead of silent discard
7. **Multi-Payload Extraction**: Handlers may emit multiple payloads; pump extracts, envelopes, and re-injects each
8. **Broadcast = Streaming Concurrent**: Multiple listeners execute in parallel; responses processed and bubbled as they complete (no group wait)
9. **OOB Isolation**: Privileged messages never touch main message pump or dispatcher
10. **Boot Message**: System-generated `<boot/>` enables listener-only architecture
11. **Stateless Handlers**: All routing, thread context, and identity is managed externally; handlers remain pure
12. **Parallel Everything**: Pipelines preprocess concurrently, pump launches dispatchers concurrently, responses stream progressively

---

## Next Steps

This document establishes the foundational architecture. Implementation priorities:

1. **Immediate (Echo Chamber Milestone)**:
   - Implement basic pipeline task sequence (repair → C14N → validate)
   - Implement sequential dispatcher with simple routing
   - Basic `<huh>` error injection on validation failure
   - Boot message generation

2. **Near-Term**:
   - Multi-payload extraction and re-injection
   - UUID path registry and privacy enforcement
   - YAML-driven listener registration
   - Pipeline parallelism

3. **Future**:
   - Token-rate monitoring per pipeline
   - Fair-share dispatcher scheduling
   - Advanced error recovery strategies
   - Hot-reload capability via OOB

---

**Status**: This document is now the single source of truth for message pump architecture. All code, diagrams, and decisions must align with this specification.
