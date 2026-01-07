# Proposed Scheduling Enhancements for Token-Constrained Environments

**January 05, 2026**

These ideas (originally surfaced by Gemini) introduce token-aware and fairness-oriented scheduling on top of the current AgentServer v2.0 message pump. The current pump already uses per-thread queues with configurable breadth-first or depth-first draining, but these suggestions shift focus to **per-agent** fairness and explicit handling of shared LLM API rate limits (TPM/RPM).

They are presented here cleaned up and structured for easier discussion and potential adoption.

### Per-Agent Buffer Pools (Targeted Fairness)

**Concept**  
Instead of a single global queue or purely thread-based queues, each registered agent (especially LLM-based listeners) gets its own dedicated message buffer.

**Benefit**  
- Guarantees "system attention" round-robin across all agents.  
- Prevents a high-volume agent (e.g., a central researcher or coordinator) from starving others.  
- Caps the number of active queues to the number of agents rather than potentially unbounded threads.

### Token-Aware Weighted Deficit Round Robin (TA-WDRR)

**Concept**  
Treat the provider's Tokens Per Minute (TPM) limit as a shared "power budget". Each agent maintains a deficit counter that accumulates each scheduling round.

**Logic**  
1. The pump looks at the next message in an agent's buffer.  
2. It estimates the token cost of that message (prompt + max_tokens).  
3. If the cost exceeds the agent's current deficit **or** the remaining global budget, skip that agent and try another.  
4. Select a smaller job from another agent that fits the remaining budget "bin".

**Benefit**  
Maximizes overall throughput by opportunistically filling small budget gaps with lightweight tasks while large reasoning jobs wait for the next budget refill.

### Adaptive Congestion Control (Servo Loop)

**Concept**  
A feedback control system that reacts to 429 rate-limit errors by dynamically adjusting the pump's assumed TPM budget.

**Mechanism**  
- Uses Additive Increase Multiplicative Decrease (AIMD).  
- On rate-limit error → immediately halve the local TPM budget.  
- On successful calls → gradually increase the budget to probe the provider's true capacity.

**Benefit**  
Avoids "thundering herd" retry storms and smoothly converges to the maximum sustainable rate without manual tuning.

### Feedforward Prep-Side Token Estimation

**Concept**  
During early message preparation (repair, validation, deserialization), pre-compute and tag each message with an `estimated_tokens` attribute.

**Logic**  
The scheduler can use this tag to make informed decisions **before** handing the message to the LLM abstraction layer, avoiding late failures.

**Benefit**  
Enables predictive skipping/reordering without waiting for the API call to fail.

### Context-Isolated Memory via Dot-Notation Thread Paths

**Concept**  
Use the full hierarchical thread path (e.g., `sess-abcd1234.researcher.search.calc`) as the unique key for per-conversation memory/state.

**Logic**  
Even when multiple threads call the same shared tool/agent, their histories and any "memory button" state remain strictly partitioned by the thread path.

**Benefit**  
- Prevents context poisoning across parallel branches.  
- Allows stateless, horizontally scalable agents while preserving private conversation continuity.

### Key Metrics for Monitoring ("Speedometer")

| Metric                  | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| TPM (Tokens Per Minute) | Real-time rolling window of input + output tokens across the organism.      |
| RPM (Requests Per Minute) | Count of individual API calls to avoid separate request-rate throttling.   |
| Reservation Variance    | Difference between reserved max_tokens and actual consumption; used to "refund" budget in real time. |

These enhancements would layer naturally on top of the existing per-thread queue model:

- Threads remain the unit of conversation memory and hierarchical tracing (unchanged).  
- Agents become the unit of scheduling fairness and token budgeting.  
- The dispatcher loop could select the next **agent** to service (round-robin or weighted), then drain the highest-priority thread queue belonging to that agent, applying the token-aware checks.

This keeps the current thread-oblivious, provenance-preserving design while adding production-grade rate-limit resilience and fairness for LLM-heavy workloads. Worth considering for a future v2.1 scheduling module.