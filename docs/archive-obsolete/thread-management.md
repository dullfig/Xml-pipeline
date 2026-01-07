# Thread Management in AgentServer v2.0
**January 04, 2026**

## Overview
Thread IDs are dynamic hierarchical paths that trace the exact call chain through the organism. The message pump builds and maintains them automatically.  
Agents, tools, and handlers are **completely oblivious** to thread IDs — they never read, copy, or emit them.

No explicit spawn primitives are required. Topology emerges solely from the shape (single vs multiple) and targets of emitted payloads.

## Wire Format
- Mandatory `<thread/>` contains a readable dot-notation string (e.g., `sess-abcd1234.researcher.search.calc`).
- Root segment is an opaque server-generated session identifier.
- Subsequent segments are registered listener short names appended during routing.

## Dynamic Call Tracing Rules
1. **Emission** (from current path `parent.path`):
   - After handler execution and multi-payload extraction:
     - For each payload, determine target listener name.
     - Append that name → new path = `parent.path.target_name`.
   - Single payload → sequential delegation (one deepened path).
   - Multiple payloads → parallel forks (one deepened path per target, each with its own queue).

2. **Response Bubbling**:
   - On emission from path `parent.path.listener_name`:
     - Pump removes the last segment.
     - Routes all response payloads to `parent.path`.
     - Injects `<from>` as the responding listener’s registered name.
   - Replies land directly in the immediate parent’s history.

3. **Broadcast**:
   - Single payload to a capability with multiple gateways → fanned out.
   - All responses pop to the same parent path, distinguished by their individual `<from>` values.

4. **Internal Uniqueness**:
   - Readable paths are mapped to UUIDs via a bidirectional resolver.
   - New unique logical path → new UUID and queue.
   - Ensures collision-free scheduling while keeping wire paths clean and meaningful.

## Termination
- Paths become idle when their queues empty.
- Detection of `<final-answer>` (meta namespace) in the root path triggers terminal egress to the originating client.

## Key Advantages
- Complete thread obliviousness eliminates prompt bloat and copy errors.
- Natural sequential delegation and parallelism without manual management.
- Full provenance via trustworthy `<from>` injection.
- Audit trails are self-documenting call traces built from registered capability names.

The organism owns memory and topology. Threads are the living, transparent traces of computation.