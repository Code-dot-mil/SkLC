"""Assess a skill package using the same workflow as the command-line interface."""

from .adjudication import adjudicate_report as adjudicate
from .commands.assess import assess_skill as assess

__all__ = ["assess", "adjudicate"]
