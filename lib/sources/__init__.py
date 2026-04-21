"""Data source adapters. Each source ends in a Path on disk; everything
downstream is source-agnostic from there.
"""

from . import manual

__all__ = ["manual"]
