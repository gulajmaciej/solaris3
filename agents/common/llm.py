"""LLM-backed tool selection with JSON validation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Set

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from agents.common.decision import (
    apply_guardrails_tool_call,
    deterministic_tool_choice_crew,
    deterministic_tool_choice_instrument,
    validate_tool_call,
)
from agents.types import ToolCall
from core.state import GameState


def _build_llm(model_name: str, temperature: float) -> ChatOllama:
    return ChatOllama(model=model_name, temperature=temperature)


def _parse_tool_call(payload: str) -> ToolCall:
    data = json.loads(payload)
    return ToolCall(
        tool_name=str(data.get("tool", "")),
        args=data.get("args", {}) or {},
        reason=str(data.get("reason", "")),
        chosen_by="llm",
    )


def llm_choose_tool_instrument(
    stance: str,
    belief: Dict[str, Any],
    allowed_tools: Set[str],
    model_name: str,
    state: GameState,
    temperature: float = 0.7,
) -> ToolCall:
    system_prompt = (
        "You are selecting a tool for the instrument specialist. "
        "Respond with strict JSON only: "
        "{\"tool\": \"<tool_name>\", \"args\": {...}, \"reason\": \"...\"}. "
        "Use only allowed tools and exact argument keys."
    )
    user_prompt = json.dumps(
        {
            "stance": stance,
            "belief": belief,
            "allowed_tools": sorted(list(allowed_tools)),
        }
    )
    llm = _build_llm(model_name, temperature)

    for _ in range(2):
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        try:
            tool_call = _parse_tool_call(response.content)
        except json.JSONDecodeError:
            continue
        ok, _reason = validate_tool_call("instrument_specialist", tool_call, allowed_tools)
        if not ok:
            continue
        tool_call = apply_guardrails_tool_call(state, tool_call)
        return tool_call

    fallback = deterministic_tool_choice_instrument(stance, belief)
    return ToolCall(
        tool_name=fallback.tool_name,
        args=fallback.args,
        reason=fallback.reason,
        chosen_by="fallback",
    )


def llm_choose_tool_crew(
    stance: str,
    belief: Dict[str, Any],
    allowed_tools: Set[str],
    model_name: str,
    state: GameState,
    temperature: float = 0.7,
) -> ToolCall:
    system_prompt = (
        "You are selecting a tool for the crew officer. "
        "Respond with strict JSON only: "
        "{\"tool\": \"<tool_name>\", \"args\": {...}, \"reason\": \"...\"}. "
        "Use only allowed tools and exact argument keys."
    )
    user_prompt = json.dumps(
        {
            "stance": stance,
            "belief": belief,
            "allowed_tools": sorted(list(allowed_tools)),
        }
    )
    llm = _build_llm(model_name, temperature)

    for _ in range(2):
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        try:
            tool_call = _parse_tool_call(response.content)
        except json.JSONDecodeError:
            continue
        ok, _reason = validate_tool_call("crew_officer", tool_call, allowed_tools)
        if not ok:
            continue
        tool_call = apply_guardrails_tool_call(state, tool_call)
        return tool_call

    fallback = deterministic_tool_choice_crew(stance, belief)
    return ToolCall(
        tool_name=fallback.tool_name,
        args=fallback.args,
        reason=fallback.reason,
        chosen_by="fallback",
    )


def resolve_model_name(default_name: str = "qwen2.5:7b") -> str:
    return os.getenv("OLLAMA_MODEL", default_name)
