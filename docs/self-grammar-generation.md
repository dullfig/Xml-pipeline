# Autonomous Registration & Introspection (v2.0)
In AgentServer v2.0, tool definition is radically simple: one `@xmlify` dataclass + handler + description. **No manual XSDs, no fragile JSON item mappings, no custom prompt engineering.** The organism auto-generates everything needed for validation, routing, and LLM wiring.<br/>
Manual XSDs, grammars, and tool descriptions are obsolete. Listeners **autonomously generate** their contracts and metadata at registration time. Introspection is a privileged core facility.

## The Developer Experience

Declare your payload contract as an `@xmlify` dataclass + a pure handler function that returns raw bytes. Register with a name and description. That's it.

```python
from xmlable import xmlify
from dataclasses import dataclass
from xml_pipeline import Listener, bus  # bus is the global MessageBus

@xmlify
@dataclass
class AddPayload:
    """Addition capability."""
    a: int = 0  # First operand
    b: int = 0  # Second operand

def add_handler(payload: AddPayload) -> bytes:
    result = payload.a + payload.b
    return f"<result>{result}</result>".encode("utf-8")

# LLM example: multi-payload emission tolerated
def agent_handler(payload: AgentPayload) -> bytes:
    return b"""
    <thought>Analyzing...</thought>
    <tool-call xmlns="https://xml-pipeline.org/ns/search/v1">
      <query>weather</query>
    </tool-call>
    """.strip()

Listener(
    payload_class=AddPayload,
    handler=add_handler,
    name="calculator.add",
    description="Adds two integers and returns their sum."  # Mandatory for usable tool prompts
).register()  # ← XSD, example, prompt auto-generated + registered
```

The bus validates input against the XSD, deserializes to the dataclass instance, calls the handler, wraps output bytes in `<dummy></dummy>`, and extracts multiple payloads if emitted.

## Autonomous Chain Reaction on Registration

1. **XSD Synthesis**  
   From `@xmlify` payload_class → generates/caches `schemas/calculator.add/v1.xsd`.  
   Namespace: `https://xml-pipeline.org/ns/calculator/v1` (derived or explicit). Root = lowercase class name.

2. **Example & Prompt Synthesis**  
   From dataclass fields + description:  
   ```
   Tool: calculator.add
   Description: Adds two integers and returns their sum.

   Example Input:
   <add>
     <a>40</a>
     <b>2</b>
   </add>

   Params: a(int) - First operand, b(int) - Second operand
   Returns: Raw XML fragment (e.g., <result>)
   ```
   Auto-injected into wired agents' system prompts.

3. **Registry Update**  
   Bus catalogs by `name` and `(namespace, root)`. Ready for routing + meta queries.

## Introspection: Privileged Meta Facility

Query the core MessageBus via reserved `https://xml-pipeline.org/ns/meta/v1`:

```xml
<message ...>
  <payload xmlns="https://xml-pipeline.org/ns/meta/v1">
    <request-schema>
      <capability>calculator.add</capability>
    </request-schema>
  </payload>
</message>
```

Core handler returns XSD bytes, example XML, or prompt fragment.  
Controlled per YAML (`meta.allow_schema_requests: "admin"` etc.). No topology leaks.

Other ops: `request-example`, `request-prompt`, `list-capabilities`.

## Multi-Handler Organs

Need multiple functions in one service? Register separate listeners or subclass Listener for shared state.

## Key Advantages

- **Zero Drift**: Edit dataclass → restart/hot-reload → XSD/example/prompt regenerate.
- **Attack-Resistant**: lxml XSD validation → typed instance → handler.
- **LLM-Tolerant**: Raw bytes output → dummy extraction supports multi-payload and dirty streams.
- **Sovereign Wiring**: YAML agents get live prompt fragments at startup.
- **Discoverable**: Namespaces served live at https://xml-pipeline.org/ns/... for tools and federation.

*The tool declares its contract and purpose. The organism enforces and describes it exactly.*
