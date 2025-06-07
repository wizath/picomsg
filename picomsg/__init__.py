"""
PicoMsg - Lightweight binary serialization format for embedded and performance-critical applications.

This package provides tools for defining message schemas and generating language-specific
bindings for efficient binary serialization/deserialization.
"""

from .__version__ import __version__, __version_info__

__author__ = "PicoMsg Team"

from .schema.parser import SchemaParser
from .format.binary import BinaryFormat
from .codegen.c import CCodeGenerator

__all__ = [
    "SchemaParser",
    "BinaryFormat", 
    "CCodeGenerator",
    "__version__",
    "__version_info__",
] 
