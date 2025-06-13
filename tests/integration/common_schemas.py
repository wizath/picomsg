"""
Common schema utilities for integration tests.
These utilities help load and work with .pico schema files consistently across integration tests.
"""

from pathlib import Path
from picomsg.schema.parser import SchemaParser

# Schema file paths
SCHEMAS_DIR = Path(__file__).parent / "schemas"

class IntegrationSchemas:
    """Schema file paths for integration tests."""
    
    CROSS_LANGUAGE_ENUMS = SCHEMAS_DIR / "cross_language_enums.pico"
    BINARY_FORMAT = SCHEMAS_DIR / "binary_format.pico"
    FIXED_ARRAYS = SCHEMAS_DIR / "fixed_arrays.pico"
    ALL_PRIMITIVES = SCHEMAS_DIR / "all_primitives.pico"
    VARIABLE_TYPES = SCHEMAS_DIR / "variable_types.pico"
    NESTED_STRUCTURES = SCHEMAS_DIR / "nested_structures.pico"
    COMPREHENSIVE = SCHEMAS_DIR / "comprehensive.pico"
    ARRAYS_OF_STRUCTS = SCHEMAS_DIR / "arrays_of_structs.pico"
    MULTIDIMENSIONAL_ARRAYS = SCHEMAS_DIR / "multidimensional_arrays.pico"

def load_schema(schema_file: Path):
    """Load and parse a schema file."""
    parser = SchemaParser()
    return parser.parse_file(schema_file)

def load_schema_text(schema_file: Path) -> str:
    """Load schema file content as text."""
    return schema_file.read_text()

# Test data constants for integration tests
class IntegrationTestData:
    """Common test data for integration tests."""
    
    # Primitive type test values
    PRIMITIVE_TEST_CASES = [
        {
            'name': 'zero_values',
            'data': {
                'u8_field': 0, 'u16_field': 0, 'u32_field': 0, 'u64_field': 0,
                'i8_field': 0, 'i16_field': 0, 'i32_field': 0, 'i64_field': 0,
                'f32_field': 0.0, 'f64_field': 0.0
            }
        },
        {
            'name': 'max_unsigned_values',
            'data': {
                'u8_field': 255, 'u16_field': 65535, 'u32_field': 4294967295, 'u64_field': 18446744073709551615,
                'i8_field': 127, 'i16_field': 32767, 'i32_field': 2147483647, 'i64_field': 9223372036854775807,
                'f32_field': 3.14159, 'f64_field': 2.718281828459045
            }
        },
        {
            'name': 'min_signed_values',
            'data': {
                'u8_field': 1, 'u16_field': 1, 'u32_field': 1, 'u64_field': 1,
                'i8_field': -128, 'i16_field': -32768, 'i32_field': -2147483648, 'i64_field': -9223372036854775808,
                'f32_field': -3.14159, 'f64_field': -2.718281828459045
            }
        },
        {
            'name': 'random_values',
            'data': {
                'u8_field': 42, 'u16_field': 1234, 'u32_field': 987654321, 'u64_field': 1234567890123456789,
                'i8_field': -42, 'i16_field': -1234, 'i32_field': -987654321, 'i64_field': -1234567890123456789,
                'f32_field': 123.456, 'f64_field': 123456.789012345
            }
        }
    ]
    
    # Variable type test values
    VARIABLE_TEST_CASES = [
        {
            'name': 'empty_values',
            'data': {
                'name': '',
                'data': b'',
                'numbers': [],
                'texts': []
            }
        },
        {
            'name': 'simple_values',
            'data': {
                'name': 'Hello, World!',
                'data': b'binary data here',
                'numbers': [1, 2, 3, 4, 5],
                'texts': ['first', 'second', 'third']
            }
        },
        {
            'name': 'unicode_and_large_arrays',
            'data': {
                'name': 'Unicode: 🚀 ñ ü 中文',
                'data': bytes(range(256)),  # All possible byte values
                'numbers': list(range(100)),  # Large array
                'texts': [f'item_{i}' for i in range(50)]  # Many strings
            }
        },
        {
            'name': 'special_characters',
            'data': {
                'name': 'Special: \n\t\r"\'\\',
                'data': b'\x00\x01\x02\xff\xfe\xfd',
                'numbers': [0, 1, 4294967295],  # Min and max u32
                'texts': ['', 'single', 'multiple words here']
            }
        }
    ] 