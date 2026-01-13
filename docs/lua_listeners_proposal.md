# Lua Listeners Proposal

**Status:** Draft / Discussion

## Problem

For a SaaS offering, users want custom agent logic without:
- Uploading Python code (security nightmare)
- Forking the codebase
- Complex deployment pipelines

## Solution

Allow users to write handler logic in Lua, which can be sandboxed effectively.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LuaListener                            │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ XML Input   │───▶│ Lua Sandbox │───▶│ XML Output  │     │
│  │ (validated) │    │ (user code) │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         ▲                                     │             │
│         │                                     ▼             │
│    XSD validates                      XSD validates         │
│    on input                           on output             │
└─────────────────────────────────────────────────────────────┘
```

### Key Insight

XSD is the source of truth. If validation passes, data is correct. The Python handler can be generic - it just bridges XML ↔ Lua tables. No typed Python dataclasses needed in the handler.

### Flow

1. Message arrives, pump validates against input XSD
2. Generic `LuaListener` converts XML → Lua table
3. User's Lua `handle()` function is called
4. Lua returns `{to = "target", payload = {...}}`
5. Handler converts Lua table → XML
6. Pump validates output against target's XSD
7. Message delivered

## User Experience

### What user provides:

1. **XSD schema** for their payload (or simpler DSL that generates XSD)
2. **Lua script** with handler function

### Example Lua script:

```lua
-- my_handler.lua

-- Called for each incoming message
function handle(payload, meta)
    -- payload is a Lua table matching the XSD structure
    local name = payload.name
    local greeting = "Hello, " .. name .. "!"

    -- Return response
    return {
        to = "next-agent",
        payload = {
            message = greeting,
            original_sender = meta.from_id
        }
    }
end

-- Optional: called once on load
function init(config)
    print("Handler initialized")
end
```

### Example XSD:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="MyPayload">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="name" type="xs:string"/>
        <xs:element name="count" type="xs:integer" minOccurs="0"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

### Registration in organism.yaml:

```yaml
listeners:
  - name: my-custom-agent
    type: lua
    xsd: schemas/my_payload.xsd
    script: scripts/my_handler.lua  # or UUID for SaaS
    description: My custom processing agent
    peers: [next-agent]

    # Optional Lua config passed to init()
    config:
      greeting_style: enthusiastic
```

## Implementation

### Python side:

```python
class LuaListener:
    """Generic listener that delegates processing to Lua."""

    def __init__(self, name: str, xsd_path: str, script_path: str, config: dict = None):
        self.name = name
        self.xsd = load_xsd(xsd_path)
        self.sandbox = LuaSandbox()
        self.sandbox.load_script(script_path)

        # Call init if defined
        if self.sandbox.has_function("init"):
            self.sandbox.call("init", config or {})

    async def handle(self, xml_payload: str, metadata: HandlerMetadata) -> HandlerResponse:
        # Convert XML to Lua table
        lua_table = xml_to_lua_table(xml_payload)

        # Convert metadata
        lua_meta = {
            "thread_id": metadata.thread_id,
            "from_id": metadata.from_id,
            "own_name": metadata.own_name,
        }

        # Call user's Lua handler
        result = self.sandbox.call("handle", lua_table, lua_meta)

        # Convert response back to XML
        response_xml = lua_table_to_xml(result["payload"])

        return HandlerResponse(
            payload=response_xml,
            to=result["to"]
        )
```

### Lua Sandbox:

Using `lupa` (LuaJIT bindings for Python):

```python
from lupa import LuaRuntime

class LuaSandbox:
    def __init__(self, memory_limit_mb: int = 50, time_limit_sec: float = 5.0):
        # Create restricted Lua runtime
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.memory_limit = memory_limit_mb * 1024 * 1024
        self.time_limit = time_limit_sec

        # Remove dangerous functions
        self._restrict_globals()

    def _restrict_globals(self):
        """Remove dangerous Lua functions."""
        dangerous = [
            'os', 'io', 'loadfile', 'dofile',
            'load', 'loadstring', 'require', 'package',
            'debug', 'collectgarbage'
        ]
        for name in dangerous:
            self.lua.globals()[name] = None

        # Provide safe subset
        self.lua.globals()['print'] = self._safe_print
        self.lua.globals()['json'] = self._json_module()

    def _safe_print(self, *args):
        """Print that goes to log, not stdout."""
        # Log instead of print
        pass

    def call(self, func_name: str, *args):
        """Call Lua function with timeout."""
        func = self.lua.globals()[func_name]
        # TODO: implement timeout
        return func(*args)
```

### XML ↔ Lua conversion:

```python
import xml.etree.ElementTree as ET

def xml_to_lua_table(xml_str: str) -> dict:
    """Convert XML to nested dict (becomes Lua table)."""
    root = ET.fromstring(xml_str)
    return element_to_dict(root)

def element_to_dict(elem) -> dict:
    result = {}
    for child in elem:
        if len(child) > 0:
            result[child.tag] = element_to_dict(child)
        else:
            result[child.tag] = child.text
    return result

def lua_table_to_xml(table: dict, root_name: str = "Payload") -> str:
    """Convert Lua table (dict) back to XML."""
    root = ET.Element(root_name)
    dict_to_element(table, root)
    return ET.tostring(root, encoding='unicode')

def dict_to_element(d: dict, parent):
    for key, value in d.items():
        child = ET.SubElement(parent, key)
        if isinstance(value, dict):
            dict_to_element(value, child)
        else:
            child.text = str(value)
```

## Sandbox Security

### Restricted Lua environment:

| Removed | Why |
|---------|-----|
| `os` | File system, env vars, process control |
| `io` | File I/O |
| `loadfile`, `dofile` | Load external code |
| `require`, `package` | Module system |
| `debug` | Introspection, can escape sandbox |

### Provided safe functions:

| Function | Description |
|----------|-------------|
| `print()` | Logs to agent log (not stdout) |
| `json.encode()` | Table to JSON string |
| `json.decode()` | JSON string to table |
| `string.*` | String manipulation |
| `table.*` | Table manipulation |
| `math.*` | Math functions |

### Resource limits:

- **Memory:** 50MB per script (configurable)
- **CPU time:** 5 seconds per invocation (configurable)
- **Stack depth:** Limited to prevent recursion attacks

## Alternative: Schema DSL

Instead of requiring XSD, provide a simpler schema language:

```lua
-- In the Lua script itself
schema = {
    name = "string",
    count = "number?",  -- optional
    tags = {"string"},  -- list of strings
    address = {         -- nested object
        street = "string",
        city = "string"
    }
}
```

Python generates XSD from this declaration at registration time.

### Type mappings:

| Lua DSL | XSD Type |
|---------|----------|
| `"string"` | `xs:string` |
| `"number"` | `xs:decimal` |
| `"integer"` | `xs:integer` |
| `"boolean"` | `xs:boolean` |
| `"string?"` | `xs:string` with `minOccurs="0"` |
| `{"string"}` | `xs:string` with `maxOccurs="unbounded"` |
| `{...}` | Nested `xs:complexType` |

## Hot Reload

For SaaS, scripts should be hot-reloadable:

1. User updates Lua script via GUI/API
2. System detects change (or explicit reload trigger)
3. New sandbox created with new script
4. Old sandbox drained (finish in-flight requests)
5. New requests go to new sandbox
6. Old sandbox destroyed

```yaml
# API endpoint
POST /agents/{name}/reload
```

## Error Handling

Lua errors should:
1. Not crash the organism
2. Be logged with context
3. Return error response to caller
4. Optionally trigger alerting

```python
try:
    result = self.sandbox.call("handle", payload, meta)
except LuaError as e:
    log.error(f"Lua error in {self.name}: {e}")
    return HandlerResponse(
        error=str(e),
        to="error-handler"
    )
```

## Open Questions

- [ ] How to handle async operations in Lua? (LLM calls, HTTP requests)
- [ ] Should Lua scripts be able to call other agents directly?
- [ ] Version control for scripts? (rollback support)
- [ ] Testing framework for Lua handlers?
- [ ] How to expose `platform.complete()` to Lua safely?
- [ ] Metrics/observability for Lua execution?

## Pros/Cons

### Pros
- Users can customize without Python knowledge
- Strong sandboxing possible
- Hot reload without restart
- Portable scripts (no Python dependencies)

### Cons
- Another language to support
- XML ↔ Lua conversion overhead
- Limited async support in Lua
- Users still need to understand XSD (or we need DSL)

## Next Steps

1. Prototype `lupa` integration
2. Benchmark XML ↔ Lua conversion
3. Design schema DSL
4. Security audit of sandbox
5. Design hot-reload mechanism
