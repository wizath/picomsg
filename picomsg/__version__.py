"""
Version information for PicoMsg.
"""

__version__ = "0.6.1"
__version_info__ = (0, 6, 1)

# Version components
MAJOR = 0
MINOR = 6
PATCH = 1

# Build metadata
BUILD_DATE = "2025-09-26"
BUILD_STATUS = "alpha"

def get_version():
    """Get the version string."""
    return __version__

def get_version_info():
    """Get the version as a tuple."""
    return __version_info__ 
