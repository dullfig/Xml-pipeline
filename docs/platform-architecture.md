# Platform Architecture — Context & Prompt Management

**Status:** Design Draft
**Date:** January 2026

## Overview

The platform is the **trusted orchestration layer** that manages:
1. **Context buffers** — message history per thread
2. **Prompt registry** — immutable system prompts per agent
3. **LLM call assembly** — platform controls what goes to the LLM

Agents are **sandboxed**. They receive messages and return responses. They cannot see or modify prompts, and cannot directly access the LLM.

## Trust Model

```
┌─────────────────────────────────────────────────────────────┐
│  PLATFORM (trusted)                                          │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ PromptRegistry  │    │ ContextBuffer   │                 │
│  │                 │    │                 │                 │
│  │ [agent] → prompt│    │ [thread] → slots│                 │
│  │ (immutable)     │    │ (append-only)   │                 │
│  └─────────────────┘    └─────────────────┘                 │
│            │                     │                           │
│            └──────────┬──────────┘                           │
│                       ▼                                      │
│             ┌─────────────────┐                             │
│             │  LLM Assembler  │                             │
│             │                 │                             │
│             │  system: prompt │  ← from registry            │
│             │  history: slots │  ← from buffer              │
│             │  user: message  │  ← validated input          │
│             └─────────────────┘                             │
│                       │                                      │
└───────────────────────│──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  AGENT HANDLER (sandboxed)                                   │
│                                                              │
│  Receives:                                                   │
│    - payload (validated, from buffer)                        │
│    - metadata (thread_id, from_id, own_name)                │
│                                                              │
│  Can request:                                                │
│    - LLM completion (platform assembles the call)           │
│    - Read own thread's history (via platform API)           │
│                                                              │
│  Cannot:                                                     │
│    - See system prompt                                       │
│    - Modify history                                          │
│    - Call LLM directly                                       │
│    - Access other threads                                    │
│                                                              │
│  Returns:                                                    │
│    - HandlerResponse(payload, to) or None                   │
└─────────────────────────────────────────────────────────────┘
```

## Context Buffer

The context buffer is **the virtual memory for agents**. Thread-scoped, append-only, immutable.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Keyed by UUID** | `buffer[thread_uuid]` → list of slots |
| **Append-only** | No modification after insertion |
| **Immutable slots** | `frozen=True` dataclasses |
| **Auto-GC** | Prune thread → buffer deleted |
| **Pure history** | No prompt, no config — just messages |

### Slot Structure

```python
@dataclass(frozen=True)
class BufferSlot:
    payload: Any           # The validated message
    thread_id: str         # Thread UUID
    from_id: str           # Sender
    to_id: str             # Receiver
    index: int             # Position in thread
    timestamp: str         # ISO timestamp
    payload_type: str      # Class name for routing
```

Note: No `usage_instructions` or prompt fields. Buffer is pure message history.

### Lifecycle

```
Thread created (new UUID)
    │
    ▼
Buffer[uuid] initialized (empty list)
    │
    ├── Message arrives → append slot
    ├── Message arrives → append slot
    ├── Message arrives → append slot
    │
    ▼
Thread pruned (response sent to caller)
    │
    ▼
Buffer[uuid] deleted → GC'd
```

## Prompt Registry

Prompts are **privileged configuration**, managed by platform, immutable at runtime.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Per-agent** | `registry[agent_name]` → system prompt |
| **Immutable** | Set at startup from config, never modified |
| **Invisible to agents** | Handlers never see their own prompt |
| **Versioned** | Hash stored for audit trail |

### Prompt Structure

```python
@dataclass(frozen=True)
class AgentPrompt:
    agent_name: str
    system_prompt: str      # The actual prompt text
    prompt_hash: str        # SHA256 for audit
    peer_schemas: str       # Generated from peer XSDs
    created_at: str         # When loaded
```

### Source

Prompts assembled at startup from:
1. `organism.yaml` → agent description, peers
2. Peer XSD schemas → what messages agent can send
3. Platform boilerplate → response semantics, constraints

```yaml
# organism.yaml
listeners:
  - name: greeter
    prompt: |
      You are a friendly greeter. Respond enthusiastically.
      Keep responses short (1-2 sentences).
    peers: [shouter]
```

## LLM Call Assembly

The platform **controls all LLM calls**. Agents request completions, platform assembles them.

### Agent Request

```python
# Agent handler (sandboxed)
async def handle_greeting(payload, metadata):
    # Agent requests LLM call — doesn't control prompt
    response = await platform.complete(
        thread_id=metadata.thread_id,
        user_message=f"Greet {payload.name}",
        temperature=0.9,
    )

    return HandlerResponse(
        payload=GreetingResponse(message=response),
        to="shouter",
    )
```

### Platform Assembly

```python
# Platform (trusted)
async def complete(thread_id: str, user_message: str, **kwargs):
    # Get agent's prompt (agent can't see this)
    prompt = prompt_registry.get(current_agent)

    # Get thread history (agent can read, not modify)
    history = context_buffer.get_thread(thread_id)

    # Assemble messages
    messages = [
        {"role": "system", "content": prompt.system_prompt},
        {"role": "system", "content": prompt.peer_schemas},
    ]

    # Add history as conversation
    for slot in history:
        role = "assistant" if slot.from_id == current_agent else "user"
        messages.append({"role": role, "content": serialize(slot.payload)})

    # Add current request
    messages.append({"role": "user", "content": user_message})

    # Make LLM call (with rate limiting, caching, etc.)
    return await llm.complete(messages, **kwargs)
```

### Security Benefits

| Threat | Mitigation |
|--------|------------|
| Prompt injection via message | User messages go in `user` role, prompt in `system` |
| Agent modifies own prompt | Prompt is immutable, agent never sees it |
| Agent accesses other threads | Platform enforces thread isolation |
| Runaway LLM costs | Platform controls all calls, can rate limit |
| Prompt leakage | Agent only sees LLM response, not assembled prompt |

## Handler Sandbox

Agents run in a restricted environment:

### Allowed

- Receive validated payloads from buffer
- Read own thread's message history (via platform API)
- Request LLM completions (platform assembles)
- Return HandlerResponse to route messages
- Return None to end conversation

### Forbidden

- Direct LLM API calls
- Access to prompt registry
- Modification of buffer slots
- Access to other threads
- Network calls (future: allowlist)
- File system access (future: sandbox)

### Implementation Path

1. **Phase 1 (current):** Convention-based — handlers *could* call LLM directly but shouldn't
2. **Phase 2:** Platform API — `platform.complete()` as the only LLM interface
3. **Phase 3:** Process isolation — handlers run in separate process/container

## Thread Lifecycle & GC

```
┌─────────────────────────────────────────────────────────────┐
│                     Thread Lifecycle                         │
└─────────────────────────────────────────────────────────────┘

1. CREATION
   ─────────
   External message arrives OR console sends @listener
        │
        ▼
   Platform assigns UUID
        │
        ▼
   Buffer[uuid] = []  (empty context)
   Registry.register(uuid, from, to)

2. EXECUTION
   ──────────
   Message → validate → append to buffer → dispatch to handler
        │
        ▼
   Handler returns response
        │
        ▼
   If forward: extend chain, new target
   If response: prune chain, back to caller

3. PRUNING
   ────────
   Handler returns is_response=True
        │
        ▼
   Registry.prune(uuid) → get parent thread
        │
        ├── If parent exists: continue in parent thread
        │
        └── If no parent: thread complete
                 │
                 ▼
            Buffer[uuid].delete()  ← Auto GC
            Registry.remove(uuid)

4. TIMEOUT (future)
   ─────────────────
   Thread idle > threshold
        │
        ▼
   Platform sends timeout warning to agent
        │
        ▼
   If no response: force prune + GC
```

## Configuration

### organism.yaml

```yaml
organism:
  name: hello-world

# Platform settings
platform:
  context_buffer:
    max_slots_per_thread: 1000
    max_threads: 10000
    ttl_hours: 24              # Auto-GC idle threads

  prompt_registry:
    allow_runtime_update: false  # Immutable after startup

  llm:
    rate_limit_per_agent: 100    # Requests per minute
    cache_ttl_seconds: 3600      # Cache identical prompts
    max_tokens_per_request: 4096

listeners:
  - name: greeter
    prompt: |
      You are a friendly greeter.
      Keep responses short and enthusiastic.
    peers: [shouter]

  - name: shouter
    # No prompt — not an LLM agent
    # Just transforms messages
```

## Migration Path

### Current State (v2.x)
- Handlers call `llm.complete()` directly
- Prompts built in handler code
- `usage_instructions` passed through metadata

### Target State (v3.x)
- Handlers call `platform.complete()`
- Prompts from registry only
- Buffer contains pure message history

### Steps
1. Create `PromptRegistry` with immutable storage
2. Create `platform.complete()` API
3. Update handlers to use platform API
4. Remove prompt-related fields from `SlotMetadata`
5. Add process isolation (future)

## Open Questions

1. **History format in LLM calls?** Serialize payloads as XML or natural language summary?
2. **Prompt versioning?** Hot-reload prompts or restart required?
3. **Agent-to-agent history?** Does agent A see messages from agent B in same thread?
4. **Audit logging?** Store all assembled prompts for debugging/compliance?

---

*This architecture ensures agents are sandboxed while the platform maintains full control over context and prompts. The separation enables security, auditability, and future scaling (prompts in config store, buffers in Redis).*
