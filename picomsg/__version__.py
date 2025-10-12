"""
Version information for PicoMsg.
"""

__version__ = "0.6.2"
__version_info__ = (0, 6, 2)

# Version components
MAJOR = 0
MINOR = 6
PATCH = 2

# Build metadata
BUILD_DATE = "2025-10-12"
BUILD_STATUS = "alpha"

def get_version():
    """Get the version string."""
    return __version__

def get_version_info():
    """Get the version as a tuple."""
    return __version_info__ 
