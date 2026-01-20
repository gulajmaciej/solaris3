"""Module entrypoint for the Solaris3 game prototype."""

import argparse

from agents.types import DecisionMode
from core.state import GameState
from game.app import SolarisApp, build_runner


def _format_state(state: GameState) -> str:
    return (
        f"tension={state.tension:.2f}, "
        f"ocean_activity={state.ocean_activity:.2f}, "
        f"crew_load={state.crew_load:.2f}, "
        f"earth_pressure={state.earth_pressure:.2f}, "
        f"station_power={state.station_power:.2f}"
    )


def _run_cli(decision_mode: DecisionMode) -> None:
    runner = build_runner(decision_mode)
    run_id = runner.start_run()
    print(f"Run {run_id} started")

    decisions = {
        "instrument_specialist": {"stance": "PROBE"},
        "crew_officer": {"stance": "BALANCE"},
    }

    for _ in range(5):
        result = runner.step(decisions)
        state = result.state
        tool_map = {tool.agent_id: tool.tool_call.tool_name for tool in result.tool_phase_results}
        instrument_tool = tool_map.get("instrument_specialist", "skipped")
        crew_tool = tool_map.get("crew_officer", "skipped")
        tool_summary = f"instrument_specialist->{instrument_tool}, crew_officer->{crew_tool}"
        print(f"Turn {state.turn}: {tool_summary}")
        print(f"  {_format_state(state)}")
        if result.ending is not None:
            print(f"Ending triggered: {result.ending.title}")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Solaris3.")
    parser.add_argument("--cli", action="store_true", help="Run the CLI loop instead of the TUI.")
    parser.add_argument(
        "--decision-mode",
        choices=[mode.value for mode in DecisionMode],
        default=DecisionMode.DETERMINISTIC.value,
        help="Decision mode for agent tool selection.",
    )
    args = parser.parse_args()
    decision_mode = DecisionMode(args.decision_mode)

    if args.cli:
        _run_cli(decision_mode)
        return

    app = SolarisApp(decision_mode)
    app.run()


if __name__ == "__main__":
    main()
