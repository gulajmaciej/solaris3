# Crew Officer

## Role In Solaris3
The crew officer oversees crew welfare and operational discipline. Each turn it reads crew, Earth, power, and ocean telemetry, fuses those readings into a belief about station conditions, and applies a crew-focused action. The agent's decisions are guided by the player-selected stance and the current game state.

In the TUI, the player selects a crew stance (PUSH, PROTECT, BALANCE, or SKIP). If SKIP is selected, the crew officer is not invoked that turn.

## Game State Inputs
The agent operates on the core `GameState` fields:

- tension
- ocean_activity
- crew_load
- earth_pressure
- station_power
- turn

These values drive telemetry noise and determine the impact of crew actions.

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

The observe phase returns a short report about inferred crew load, tension, and the last action.

## Memory And Belief
The agent stores short-lived memory in TinyDB per run:

- belief: last fused belief state
- last_tool: last applied tool name
- notes_tail: the last 5 fusion notes (plus an action note)

On each tool phase it reloads memory, fuses new readings with the prior belief, then writes updated belief and notes.

## Sensor Reads (MCP Read Tools)
During sense_world, the agent calls:

- sensor_crew_status
- comms_earth_channel
- telemetry_power_bus
- sensor_ocean_signal (mode NORMAL)

Each read returns a noisy value with flags for glitch, stale, or missing data. The agent also records an exact snapshot of the current game state for reference in fusion.

## Fusion And Belief Quality
Readings are fused via `fuse_readings`, which outputs:

- belief: denoised estimates, including hats for key values
- belief_quality: scalar [0, 1] confidence
- contradictions: count of sensor conflicts
- notes: short textual notes about fusion

Belief quality and contradictions affect whether the agent chooses deterministic actions or defers to an LLM decision.

## Tool Decisions
Inputs:

- stance: player-selected stance (PUSH, PROTECT, BALANCE)
- belief: fused belief
- mode: DecisionMode (DETERMINISTIC, LLM, or AUTO)

Allowed tools:

- rest_protocol
- tighten_procedures
- throttle_information

Decision logic:

- DETERMINISTIC: uses `deterministic_tool_choice_crew`
- LLM: uses `llm_choose_tool_crew`
- AUTO: uses LLM when belief_quality < 0.70, contradictions > 0, or belief suggests high crew_load or tension; otherwise deterministic

All tool calls are validated; invalid calls fall back to deterministic choices. Guardrails are applied to prevent unsafe actions for the current state.

## Tool Writes (MCP Write Tools)
The crew officer applies one of three write tools, each affecting the game state and consuming station power:

- rest_protocol(duration: SHORT | STANDARD | LONG)
  - Reduces crew_load and tension at increasing power cost; may slightly raise earth_pressure.
- tighten_procedures(level: LOW | MEDIUM | HIGH)
  - Raises tension and crew_load to lower earth_pressure; higher levels cost more power.
- throttle_information(level: LOW | MEDIUM | HIGH)
  - Lowers tension and crew_load but increases earth_pressure; moderate power cost.

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

- observation: "Crew report: load {value}, tension {value}, action {tool}."
