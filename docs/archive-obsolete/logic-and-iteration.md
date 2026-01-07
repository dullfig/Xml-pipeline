# Reasoning & Iteration in AgentServer v2.0
**January 03, 2026**

LLM-based listeners (agents) achieve multi-step reasoning, planning, tool use, and iteration through **open, auditable self-calls and subthreading** — not hidden loops or state machines.

## Core Mechanism

1. **Thread = Memory**  
   Full conversation history (all messages in the thread, including thoughts/tools/system) is the only memory.  
   Each LLM call receives the complete thread context (system prompt + prior messages).

2. **Self-Reflection = Self-Message**  
   To think step-by-step or continue reasoning, the agent emits its own root tag in the same thread:
   ```xml
   <researcher xmlns="https://xml-pipeline.org/ns/researcher/v1">
     <thought>Outlining steps...</thought>
     <!-- more thoughts or tool calls -->
   </researcher>
   ```
   Pump routes it back → appended to history → next LLM call sees it.

3. **Iteration Emerges Naturally**  
   Repeated self-calls continue until the agent emits a final response (e.g., structured answer to human).

4. **Subthreading for Parallel/Branched Computation**  
   See [Thread Management](thread-management.md) for details.  
   Agents spawn branches explicitly:
   ```xml
   <spawn-thread suggested_sub_id="image-analysis">
     <initial-payload>
       <analyze-image>...</analyze-image>
     </initial-payload>
   </spawn-thread>
   ```
   Core confirms with assigned ID → parallel queue drains independently.

## System Messages (Core-Generated Feedback)

The organism injects visible system payloads for primitives and errors — ensuring no silent failure and aiding LLM recovery:

- Spawn confirmation:
  ```xml
  <thread-spawned assigned_id="sess-abcd1234.research" parent_id="sess-abcd1234"/>
  ```

- Unknown thread error:
  ```xml
  <system-thread-error unknown_id="bad" code="unknown_thread"
    message="Unknown thread; emit <spawn-thread/> to create."/>
  ```

- Context management confirmation (agent-requested):
  ```xml
  <context-cleared kept_messages="10"/>
  ```

- Future primitives (timer, etc.) follow the same pattern — always visible, immediate response.

## Structured Planning Support

Agents are encouraged to use visible structures for coordination:
```xml
<todo-until condition="all sources checked">
  <step done="true">Search web</step>
  <step done="false">Analyze results</step>
</todo-until>
```
Enables self-reading, GUI rendering, explicit termination.

## Key Properties

- **No Hidden State**: Thread history is the sole memory.
- **Fully Auditable**: Every thought, plan, spawn, system feedback, and step is a logged message.
- **Tool Use Identical**: Calls to other listeners are normal payloads.
- **Termination Natural**: Agent decides final output tag.

The framework turns conversation into visible, branched computation — safe, transparent, and Turing-complete within bounds.
