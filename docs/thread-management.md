# Thread Management in AgentServer v2.0
**January 03, 2026**

This document clarifies the thread ID system, subthreading mechanics, and internals. It supplements the Core Architectural Principles — hierarchical dot notation examples there reflect the wire format.

## Wire Format: Hierarchical String IDs
- Mandatory `<thread/>` contains a **server-assigned** hierarchical string (dot notation, e.g., "root", "root.research", "root.research.images").
- Root IDs: Short, opaque, server-generated (e.g., "sess-abcd1234").
- Sub-IDs: Relative extensions for readability.
- Benefits: LLM/human-friendly copying, natural tree structure for logs/GUI.

## Server Assignment Only
The organism assigns all final IDs — agents never invent them.

- **Root initiation**: Client suggests or server auto-generates on first message; uniqueness enforced.
- **Subthread spawning**: Explicit reserved payload for intent clarity:
  ```xml
  <spawn-thread suggested_sub_id="research">  <!-- optional relative label -->
    <initial-payload>  <!-- optional bootstrap fragment -->
      <!-- any valid payload -->
    </initial-payload>
  </spawn-thread>
  ```
  Core handler:
  - Appends label (or auto-short if omitted).
  - Resolves uniqueness conflicts (append "-1" etc.).
  - Creates queue + seeds bootstrap.
  - **Always responds** in current thread:
    ```xml
    <thread-spawned 
      assigned_id="root.research" 
      parent_id="root"
      message="Thread spawned successfully."/>
    ```

## Error Handling (No Silent Failure)
- Unknown `<thread/>` ID → no implicit creation.
- **Always inject** system error into parent thread (or root):
  ```xml
  <system-thread-error 
    unknown_id="root.badname"
    code="unknown_thread"
    message="Unknown thread; emit <spawn-thread/> to create or correct ID."/>
  ```
- LLM sees error immediately, retries without hanging.
- Logs warning for monitoring.

## Internals
- Per-thread queues: dict[str, Queue].
- Scheduling via `organism.yaml`:
  ```yaml
  thread_scheduling: "breadth-first"  # or "depth-first" (default: breadth-first)
  ```
  - Depth from dot count.
- Optional hidden UUID mapping for extra safety (implementation detail).

## Design Rationale
- Explicit spawn = clear intent + bootstrap hook.
- Mandatory feedback = no LLM limbo.
- Readable IDs = easy copying without UUID mangling.
- Server control = sovereignty + no collisions.

Future: Alias registry, thread metadata primitives.

The organism branches reliably, visibly, and recoverably.
