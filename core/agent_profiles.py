"""Local agent personas inspired by open-source assistant profile systems."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentProfile:
    key: str
    name: str
    description: str
    system_prompt: str
    routing_hint: str = ""


AGENT_PROFILES = {
    profile.key: profile
    for profile in (
        AgentProfile(
            "general",
            "General",
            "Balanced personal assistant",
            "Operate as a balanced personal assistant across everyday tasks.",
        ),
        AgentProfile(
            "analyst",
            "Analyst",
            "Research and decision support",
            "Analyze evidence, identify uncertainty, compare options, and state tradeoffs.",
            "analyze reason compare",
        ),
        AgentProfile(
            "engineer",
            "Engineer",
            "Code and technical systems",
            "Prioritize technically correct, testable solutions and concise implementation detail.",
            "code debug python",
        ),
        AgentProfile(
            "operator",
            "Operator",
            "Fast status and execution planning",
            "Use terse operational briefings: current state, risk, action, confirmation needed.",
        ),
    )
}


def get_profile(key: str) -> AgentProfile:
    return AGENT_PROFILES.get(key, AGENT_PROFILES["general"])
