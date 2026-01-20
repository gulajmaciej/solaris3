# Instrument Specialist

## Role In Solaris3
The instrument specialist is the station's sensor and sampling operator. Each turn it reads noisy telemetry, fuses it into a belief about the ocean and station power, and chooses a sampling action (probe, filter, or hold). The agent's decisions are informed by player stance selections and the current game state.

In the TUI, the player selects an instrument stance (PROBE, FILTER, HOLD). That stance feeds this agent's tool-selection logic for the turn.

## Game State Inputs
The agent operates on the core `GameState` fields:

- tension
- ocean_activity
- crew_load
- earth_pressure
- station_power
- turn

These values are used for both noisy sensor reads and for power constraints on write tools.

## Phases And Graph Flow
The agent is a LangGraph with two phases:

Tool phase (default):
1) route_phase -> read_memory
2) sense_world
3) fuse
4) decide_tool
5) apply_tool
6) write_memory -> END

Observe phase:
1) route_phase -> observe_stub -> END

The observe phase returns a short observation string that summarizes the current inferred ocean activity, station power, and the last chosen tool.

## Memory And Belief
The agent stores short-lived memory in TinyDB per run:

- belief: last fused belief state
- last_tool: last applied tool name
- notes_tail: the last 5 fusion notes

On each tool phase it reloads this memory, fuses new readings with the prior belief, and then saves the updated belief and notes.

## Sensor Reads (MCP Read Tools)
During sense_world, the agent calls:

- sensor_ocean_signal (mode NORMAL)
- telemetry_power_bus

Each read returns a noisy value with flags for glitch, stale, or missing data. The agent also records an exact snapshot of the current game state for reference in fusion.

## Fusion And Belief Quality
Readings are fused via `fuse_readings`, which outputs:

- belief: a denoised estimate, including hats for key values
- belief_quality: scalar [0, 1] confidence
- contradictions: count of sensor conflicts
- notes: short textual notes about fusion

Belief quality and contradictions influence whether the agent chooses a deterministic tool or defers to an LLM decision.

## Tool Decisions
Inputs:

- stance: player-selected stance (PROBE, FILTER, HOLD)
- belief: fused belief
- mode: DecisionMode (DETERMINISTIC, LLM, or AUTO)

Allowed tools:

- probe_sampling
- filter_pipeline
- hold_sampling

Decision logic:

- DETERMINISTIC: uses `deterministic_tool_choice_instrument`
- LLM: uses `llm_choose_tool_instrument`
- AUTO: deterministic if belief_quality >= 0.70 and contradictions == 0, otherwise LLM

All tool calls are validated; invalid calls fall back to deterministic choices. Guardrails are applied to prevent unsafe actions for the current state.

## Tool Writes (MCP Write Tools)
The instrument specialist can apply one of three write tools, each affecting the game state and consuming station power:

- probe_sampling(intensity: LOW | MEDIUM | HIGH)
  - Raises ocean_activity; also increases tension, crew_load, and earth_pressure; higher intensities cost more power.
- filter_pipeline(strength: LOW | MEDIUM | HIGH)
  - Lowers ocean_activity and tension, slightly increases crew_load; moderate power cost.
- hold_sampling()
  - A low-power stabilize action that slightly reduces ocean_activity, tension, and crew_load.

Power cost is scaled by available station power via a power factor, which reduces both the cost and the effective delta when power is low.

## Events And Telemetry Logging
The agent logs detailed events each step:

- agent_log and agent_edge entries for graph traversal
- tool_read entries for sensor calls
- tool_write entries for applied tools

These events are returned in the tool phase result and surfaced in the TUI terminal output.

## Outputs
Tool phase returns:

- tool_call: chosen tool and arguments
- tool_write_output: MCP write response
- belief, belief_quality, contradictions
- agent_events: log and tool event stream

Observe phase returns:

- observation: "Instrument report: ocean {value}, power {value}, action {tool}."
