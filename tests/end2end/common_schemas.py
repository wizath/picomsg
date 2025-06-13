"""
Common schema utilities for end-to-end tests.
These utilities help load and work with .pico schema files consistently across tests.
"""

from pathlib import Path
from picomsg.schema.parser import SchemaParser

# Schema file paths
SCHEMAS_DIR = Path(__file__).parent / "schemas"

class SchemaFiles:
    """Schema file paths for end-to-end tests."""
    
    BASIC_PLAYER = SCHEMAS_DIR / "basic_player.pico"
    COMPLEX_STRUCTURES = SCHEMAS_DIR / "complex_structures.pico"
    DEFAULT_VALUES = SCHEMAS_DIR / "default_values.pico"
    JSON_VALIDATION = SCHEMAS_DIR / "json_validation.pico"
    STATIC_FACTORY = SCHEMAS_DIR / "static_factory.pico"
    TYPE_SAFETY = SCHEMAS_DIR / "type_safety.pico"
    PERFORMANCE = SCHEMAS_DIR / "performance.pico"
    COMPREHENSIVE = SCHEMAS_DIR / "comprehensive.pico"

def load_schema(schema_file: Path):
    """Load and parse a schema file."""
    parser = SchemaParser()
    return parser.parse_file(schema_file)

def load_schema_text(schema_file: Path) -> str:
    """Load schema file content as text."""
    return schema_file.read_text()

# Test data constants
class TestData:
    """Common test data values for consistency across tests."""
    
    # Basic player data
    PLAYER_ID = 12345
    PLAYER_NAME = "TestPlayer"
    PLAYER_HEALTH = 100
    
    # Scene data
    SCENE_NAME = "TestScene"
    CAMERA_POSITION = (0.0, 5.0, -10.0)
    
    # Game objects
    PLAYER_OBJECT = {
        "id": 1,
        "name": "Player",
        "position": (0.0, 1.0, 0.0),
        "rotation": (0.0, 45.0, 0.0),
        "scale": (1.0, 1.0, 1.0),
        "tags": ["player", "controllable"]
    }
    
    ENEMY_OBJECT = {
        "id": 2,
        "name": "Enemy",
        "position": (10.0, 0.0, 5.0),
        "rotation": (0.0, 180.0, 0.0),
        "scale": (1.2, 1.2, 1.2),
        "tags": ["enemy", "ai"]
    }
    
    # Server config data
    SERVER_CONFIG = {
        "host": "production.example.com",
        "port": 443,
        "max_connections": 5000,
        "enable_ssl": True,
        "timeout_seconds": 60,
        "debug_mode": False
    }
    
    # User profile data
    USER_PROFILE = {
        "id": 1001,
        "username": "testuser",
        "email": "test@example.com",
        "age": 25,
        "location": {"x": 37.7749, "y": -122.4194},
        "verified": True
    }
    
    MINIMAL_USER_PROFILE = {
        "id": 2002,
        "email": "minimal@example.com",
        "location": {"x": 40.7128, "y": -74.0060}
    }
    
    # Config data
    CONFIG_DATA = {
        "name": "test_config",
        "value": 42,
        "enabled": True
    } 