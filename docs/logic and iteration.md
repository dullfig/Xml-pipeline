# Executive Summary: Self-Calling Iteration Framework in xml-pipeline

**Date**: December 29, 2025  
**Component**: Core reasoning mechanism for LLM personalities

### Principle

In xml-pipeline, **multi-step reasoning, planning, tool use, and iteration are implemented through open, auditable self-calls** — not hidden loops or state machines.

The LLM personality participates in the conversation exactly like any other listener: it can send messages to its own root tag.

### How It Works

1. **Conversation thread = memory**  
   Every message (user, personality, tool) is appended to history keyed by `convo_id`.

2. **Self-reflection = self-message**  
   To think step-by-step, the LLM emits its own root tag with the same `convo_id`:
   ```xml
   <ask-grok convo_id="123">
     First, let's outline the steps...
   </ask-grok>
   ```

3. **MessageBus routes it back** to the same personality instance.

4. **Personality appends its own message** to history and calls the LLM again.

5. **LLM sees full context** — including its previous thoughts — and continues.

6. **Iteration emerges naturally** from repeated self-calls until final response.

### Key Properties

- **No hidden state** — the thread history is the only memory
- **No special controller** — MessageBus and `convo_id` do all coordination
- **Fully auditable** — every thought, plan, and intermediate step is a logged message
- **Tool use fits identically** — tool calls are messages to other root tags
- **Termination is natural** — LLM decides when to emit final response tag (e.g., `<grok-response>`)

### Structured Planning Support

Personalities are encouraged to use visible structures:

```xml
<todo-until condition="all primes under 100 listed">
  <step done="true">List 2</step>
  <step done="true">List 3</step>
  <step done="false">List 5</step>
</todo-until>
```

This enables:
- Self-coordination (LLM reads its own plan)
- GUI progress rendering
- Explicit termination conditions

### Owner Control

- `iteration-capacity` config (`high`/`medium`/`low`/`none`) tunes how strongly the personality is prompted to iterate
- All behavior governed by owner-provided prompts and response templates
- No personality can loop indefinitely without owner consent

### Result

The framework turns **conversation into computation**.

Loops, conditionals, and planning become **visible message patterns** rather than hidden code.

The organism reasons by talking to itself in the open — producing a complete, transparent trace of thought at every step.

This is the core iteration mechanism for all LLM personalities in xml-pipeline.
