"""Standalone skill assessment kit."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("skill-assessment")
except PackageNotFoundError:
    __version__ = "source"
