"""Textual TUI for Solaris2."""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, RichLog, Select, Static

from agents.types import DecisionMode
from core.db import TinyDBRunStore
from core.engine import SimulationRunner
from core.endings import EndingRegistry, EndingSpec
from core.state import GameState, initial_state
from game.formatting import format_event_line
from mcp.server import MCPServer
from mcp.tools_read import (
    comms_earth_channel,
    sensor_crew_status,
    sensor_ocean_signal,
    telemetry_power_bus,
)
from mcp.tools_write import (
    filter_pipeline,
    hold_sampling,
    probe_sampling,
    rest_protocol,
    tighten_procedures,
    throttle_information,
)


def _register_placeholder_endings(registry: EndingRegistry) -> None:
    registry.register(
        EndingSpec(
            id="system_collapse",
            title="System Collapse",
            priority=100,
            condition=lambda state: state.tension >= 1.0,
            render_text=lambda state: "The station systems collapse under the strain.",
        )
    )
    registry.register(
        EndingSpec(
            id="crew_breakdown",
            title="Crew Breakdown",
            priority=90,
            condition=lambda state: state.crew_load >= 1.0,
            render_text=lambda state: "The crew can no longer sustain operations.",
        )
    )
    registry.register(
        EndingSpec(
            id="earth_takeover",
            title="Earth Takeover",
            priority=80,
            condition=lambda state: state.earth_pressure >= 1.0,
            render_text=lambda state: "Earth asserts direct control over the station.",
        )
    )
    registry.register(
        EndingSpec(
            id="mission_window",
            title="Mission Window",
            priority=10,
            condition=lambda state: state.ocean_activity >= 0.85 and state.tension <= 0.60,
            render_text=lambda state: "A narrow mission window opens above Solaris.",
        )
    )


def build_runner(decision_mode: DecisionMode) -> SimulationRunner:
    registry = EndingRegistry()
    _register_placeholder_endings(registry)
    db = TinyDBRunStore()
    server = MCPServer()
    server.register_read_tool("sensor_ocean_signal", sensor_ocean_signal)
    server.register_read_tool("sensor_crew_status", sensor_crew_status)
    server.register_read_tool("telemetry_power_bus", telemetry_power_bus)
    server.register_read_tool("comms_earth_channel", comms_earth_channel)
    server.register_write_tool("probe_sampling", probe_sampling)
    server.register_write_tool("filter_pipeline", filter_pipeline)
    server.register_write_tool("hold_sampling", hold_sampling)
    server.register_write_tool("rest_protocol", rest_protocol)
    server.register_write_tool("tighten_procedures", tighten_procedures)
    server.register_write_tool("throttle_information", throttle_information)
    return SimulationRunner(
        db=db,
        endings_registry=registry,
        seed=42,
        mcp_server=server,
        decision_mode=decision_mode,
    )


class SolarisApp(App):
    CSS = """
    Screen {
        background: #f4f0e6;
        color: #1e1b16;
    }

    #title {
        content-align: center middle;
        text-style: bold;
        padding: 1 0;
        background: #e8dcc4;
        color: #3b2f2f;
    }

    .pane {
        border: round #b9a88c;
        background: #fbf7ee;
        padding: 1 2;
    }

    .pane-title {
        text-style: bold;
        color: #5b4636;
        margin-bottom: 1;
    }

    #top-row {
        height: 18;
    }

    #decisions-pane, #stats-pane {
        width: 1fr;
    }

    #terminal-pane {
        height: 1fr;
    }

    #status-line {
        margin-top: 1;
        color: #6a5c4f;
    }

    Select {
        margin-bottom: 1;
    }

    Button {
        margin-top: 1;
        width: 100%;
        background: #c9c3ba;
        color: #2a241d;
    }
    """

    def __init__(self, decision_mode: DecisionMode) -> None:
        super().__init__()
        self._decision_mode = decision_mode
        self._runner: Optional[SimulationRunner] = None
        self._run_id: Optional[str] = None
        self._current_state: GameState = initial_state()
        self._previous_state: Optional[GameState] = None
        self._ended = False
        self._executing = False
        self._instrument_stance: Optional[str] = "PROBE"
        self._crew_stance: Optional[str] = "SKIP"

    def compose(self) -> ComposeResult:
        yield Static("SOLARIS2 COMMAND DECK", id="title")
        with Vertical(id="root"):
            with Horizontal(id="top-row"):
                with Container(id="decisions-pane", classes="pane"):
                    yield Static("Decisions", classes="pane-title")
                    yield Static("Instrument Specialist")
                    yield Select(
                        options=[("PROBE", "PROBE"), ("FILTER", "FILTER"), ("HOLD", "HOLD")],
                        value="PROBE",
                        allow_blank=False,
                        id="instrument-select",
                    )
                    yield Static("Crew Officer")
                    yield Select(
                        options=[
                            ("SKIP", "SKIP"),
                            ("PUSH", "PUSH"),
                            ("PROTECT", "PROTECT"),
                            ("BALANCE", "BALANCE"),
                        ],
                        value="SKIP",
                        allow_blank=False,
                        id="crew-select",
                    )
                    yield Button("Submit", id="submit-button")
                    yield Static("Waiting for selections...", id="status-line")
                with Container(id="stats-pane", classes="pane"):
                    yield Static("Statistics", classes="pane-title")
                    yield Static("", id="stats-text")
            with Container(id="terminal-pane", classes="pane"):
                yield Static("Terminal", classes="pane-title")
                yield RichLog(id="terminal-log", wrap=True, highlight=False, markup=False)

    def on_mount(self) -> None:
        self._runner = build_runner(self._decision_mode)
        self._run_id = self._runner.start_run()
        self._log_line(f"[RUN][start]: {self._run_id}")
        self._update_stats(self._current_state)

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._ended or self._executing:
            return
        value = None if event.value is Select.BLANK else event.value
        if event.select.id == "instrument-select":
            self._instrument_stance = value
        if event.select.id == "crew-select":
            self._crew_stance = value
        self._update_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "submit-button":
            return
        self._maybe_run_turn()

    def _update_status(self) -> None:
        status = self.query_one("#status-line", Static)
        if self._ended:
            status.update("Run ended. Restart app to start new run.")
            return
        if self._instrument_stance and self._crew_stance:
            status.update("Ready")
        else:
            status.update("Waiting for selections...")

    def _maybe_run_turn(self) -> None:
        if self._runner is None or self._ended or self._executing:
            return
        if self._instrument_stance not in {"PROBE", "FILTER", "HOLD"}:
            return
        if self._crew_stance not in {"SKIP", "PUSH", "PROTECT", "BALANCE"}:
            return
        status = self.query_one("#status-line", Static)
        status.update("Executing turn...")
        self._executing = True

        decisions = {"instrument_specialist": {"stance": self._instrument_stance}}
        if self._crew_stance != "SKIP":
            decisions["crew_officer"] = {"stance": self._crew_stance}

        result = self._runner.step(decisions)
        for event in result.events:
            for line in format_event_line(event):
                self._log_line(line)

        self._previous_state = self._current_state
        self._current_state = result.state
        self._update_stats(self._current_state)

        if result.ending is not None:
            self._log_line(f"[ENDING]: {result.ending.title}")
            self._ended = True
            self._disable_inputs()
            status.update("Run ended. Restart app to start new run.")
            self._executing = False
            return

        self._reset_selections()
        self._update_status()
        self._executing = False

    def _reset_selections(self) -> None:
        instrument_select = self.query_one("#instrument-select", Select)
        crew_select = self.query_one("#crew-select", Select)
        instrument_select.value = "PROBE"
        crew_select.value = "SKIP"
        self._instrument_stance = "PROBE"
        self._crew_stance = "SKIP"

    def _disable_inputs(self) -> None:
        self.query_one("#instrument-select", Select).disabled = True
        self.query_one("#crew-select", Select).disabled = True

    def _update_stats(self, state: GameState) -> None:
        prev = self._previous_state
        stats = self.query_one("#stats-text", Static)
        stats.update(
            "\n".join(
                [
                    self._format_stat("tension", state.tension, prev.tension if prev else None),
                    self._format_stat("ocean_activity", state.ocean_activity, prev.ocean_activity if prev else None),
                    self._format_stat("crew_load", state.crew_load, prev.crew_load if prev else None),
                    self._format_stat("earth_pressure", state.earth_pressure, prev.earth_pressure if prev else None),
                    self._format_stat("station_power", state.station_power, prev.station_power if prev else None),
                    self._format_stat("turn", float(state.turn), float(prev.turn) if prev else None, as_int=True),
                ]
            )
        )

    @staticmethod
    def _format_stat(label: str, value: float, previous: Optional[float], as_int: bool = False) -> str:
        if as_int:
            current = f"{int(value)}"
            previous_str = f"{int(previous)}" if previous is not None else "—"
        else:
            current = SolarisApp._trim_float(value)
            previous_str = SolarisApp._trim_float(previous) if previous is not None else "—"
        return f"{label}: {current} ({previous_str})"

    @staticmethod
    def _trim_float(value: float) -> str:
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"

    def _log_line(self, line: str) -> None:
        log = self.query_one("#terminal-log", RichLog)
        log.write(line)
        log.scroll_end()
