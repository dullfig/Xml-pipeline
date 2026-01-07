G# Configuration — organism.yaml (v2.1)

The entire organism is declared in a single YAML file (default: `config/organism.yaml`).  
Loaded at bootstrap — single source of truth for initial composition.  
Runtime changes (hot-reload) via local OOB privileged commands.

## Example Full Configuration

```yaml
organism:
  name: "ResearchSwarm-01"
  identity: "config/identity/private.ed25519"   # Ed25519 private key
  port: 8765                                    # Main message bus WSS
  tls:
    cert: "certs/fullchain.pem"
    key: "certs/privkey.pem"

oob:  # Out-of-band privileged channel (GUI/hot-reload ready)
  enabled: true
  bind: "127.0.0.1"       # Localhost-only default
  port: 8766              # Separate WSS port
  # unix_socket: "/tmp/organism.sock"  # Alternative

thread_scheduling: "breadth-first"  # or "depth-first" (default: breadth-first)

meta:
  enabled: true
  allow_list_capabilities: true
  allow_schema_requests: "admin"     # "admin" | "authenticated" | "none"
  allow_example_requests: "admin"
  allow_prompt_requests: "admin"
  allow_remote: false                # Federation peers query meta

listeners:
  - name: calculator.add
    payload_class: examples.calculator.AddPayload
    handler: examples.calculator.add_handler
    description: "Adds two integers and returns their sum."  # Mandatory for usable tool prompts

  - name: summarizer
    payload_class: agents.summarizer.SummarizePayload
    handler: agents.summarizer.summarize_handler
    description: "Summarizes text via local LLM."

agents:
  - name: researcher
    system_prompt: "prompts/researcher_system.txt"
    tools:
      - calculator.add
      - summarizer
      - name: web_search
        remote: true
        gateways: 
          - search_node1
          - search_node2 
          - search_node3  # list = broadcast to all
        mode: "first-answer-wins"  # optional: "all" (collect responses), default "single" if one gateway
        
gateways:
  - name: web_search
    remote_url: "wss://trusted-search-node.example.org"
    trusted_identity: "pubkeys/search_node.ed25519.pub"
    description: "Federated web search capability."
```

## Sections Explained

### `organism`
Core settings.
- `name`: Logs/discovery.
- `identity`: Ed25519 private key path.
- `port` / `tls`: Main WSS bus.

### `oob`
Privileged local control channel.
- `enabled: false` → pure static (restart for changes).
- Localhost default for GUI safety.
- Separate from main port — bus oblivious.

### `thread_scheduling`
Balanced subthread execution.
- `"breadth-first"`: Fair round-robin (default, prevents deep starvation).
- `"depth-first"`: Dive deep into branches.

### `meta`
Introspection controls (`https://xml-pipeline.org/ns/meta/v1`).

### `listeners`
Bounded capabilities.
- `name`: Discovery/logging (dots for hierarchy).
- `payload_class`: Full import to `@xmlify` dataclass.
- `handler`: Full import to function (dataclass → bytes).
- `description`: **Mandatory** human-readable blurb (lead-in for auto-prompt; fallback to generic if omitted).

At startup/hot-reload: imports → Listener instantiation → bus.register() → XSD/example/prompt synthesis.

Cached XSDs: `schemas/<name>/v1.xsd`.

### `agents`
LLM reasoners.
- `system_prompt`: Static file path.
- `tools`: Local names or remote references.
- Auto-injected live tool prompts at runtime.

### `gateways`
Federation peers.
- Trusted public key required.
- Bidirectional regular traffic only.

## Notes
- Hot-reload: Future privileged OOB commands (apply new YAML fragments, add/remove listeners).
- Namespaces: Capabilities under `https://xml-pipeline.org/ns/<category>/<name>/v1` (served live if configured).
- Edit → reload/restart → new bounded minds, self-describing and attack-resistant.

This YAML is the organism's DNA — precise, auditable, and evolvable locally.