"""
Python JSON integration for PicoMsg.

This module enhances the Python code generator with advanced JSON conversion
capabilities, including schema validation and streaming support.
"""

from typing import Dict, Any, List, Optional, Set, Union
from pathlib import Path
import json

from ..codegen.python import PythonCodeGenerator
from ..schema.ast import Schema, Struct, Message, Field, Type as PicoType
from ..schema.ast import PrimitiveType, StringType, BytesType, ArrayType, StructType


class PythonJSONCodeGenerator(PythonCodeGenerator):
    """
    Enhanced Python code generator with advanced JSON support.
    
    This generator adds:
    - Enhanced JSON validation with detailed error messages
    - Schema-aware JSON conversion with type coercion
    - Streaming JSON support for large datasets
    - Cross-platform JSON compatibility
    """
    
    def __init__(self, schema: Schema, module_name: str = "picomsg_types"):
        """Initialize the enhanced Python JSON code generator."""
        super().__init__(schema, module_name)
        self.json_features = {
            'validation': True,
            'streaming': True,
            'type_coercion': True,
            'error_handling': True
        }
    
    def generate_code(self) -> str:
        """Generate enhanced Python code with JSON support."""
        code_parts = []
        
        # Add enhanced imports
        code_parts.append(self._generate_enhanced_imports())
        code_parts.append("")
        
        # Add JSON error classes
        code_parts.append(self._generate_json_error_classes())
        code_parts.append("")
        
        # Add JSON validation utilities
        code_parts.append(self._generate_json_validation_utilities())
        code_parts.append("")
        
        # Add enhanced base class
        code_parts.append(self._generate_enhanced_base_class())
        code_parts.append("")
        
        # Generate structs with enhanced JSON support
        for struct in self.schema.structs:
            code_parts.append(self._generate_enhanced_struct(struct))
            code_parts.append("")
        
        # Generate messages with enhanced JSON support
        for message in self.schema.messages:
            code_parts.append(self._generate_enhanced_message(message))
            code_parts.append("")
        
        # Add JSON utility functions
        code_parts.append(self._generate_json_utilities())
        code_parts.append("")
        
        # Add streaming JSON support
        code_parts.append(self._generate_streaming_json_support())
        
        return "\n".join(code_parts)
    
    def _generate_enhanced_imports(self) -> str:
        """Generate enhanced imports for JSON support."""
        imports = [
            "import json",
            "import io",
            "from typing import Dict, Any, List, Optional, Union, Iterator, Type, BinaryIO, TextIO",
            "from pathlib import Path",
            "import re",
            "from decimal import Decimal",
            "from datetime import datetime",
        ]
        
        # Add base imports from parent class
        base_imports = super()._generate_imports()
        if base_imports:
            imports.insert(0, base_imports)
        
        return "\n".join(imports)
    
    def _generate_json_error_classes(self) -> str:
        """Generate JSON-specific error classes."""
        return '''class PicoMsgJSONError(Exception):
    """Base exception for PicoMsg JSON operations."""
    pass


class JSONValidationError(PicoMsgJSONError):
    """Schema validation error during JSON conversion."""
    
    def __init__(self, message: str, field_path: str = "", value: Any = None):
        self.field_path = field_path
        self.value = value
        full_message = f"{message}"
        if field_path:
            full_message = f"Field '{field_path}': {message}"
        if value is not None:
            full_message += f" (got: {repr(value)})"
        super().__init__(full_message)


class JSONConversionError(PicoMsgJSONError):
    """Type conversion error during JSON processing."""
    pass


class JSONStreamingError(PicoMsgJSONError):
    """Error during streaming JSON operations."""
    pass'''
    
    def _generate_json_validation_utilities(self) -> str:
        """Generate JSON validation utility functions."""
        return '''class JSONValidator:
    """JSON validation utilities for PicoMsg types."""
    
    @staticmethod
    def validate_primitive_type(value: Any, type_name: str, field_path: str = "") -> Any:
        """Validate and coerce primitive type values."""
        if type_name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
            if not isinstance(value, (int, float, str)):
                raise JSONValidationError(f"Expected number, got {type(value).__name__}", field_path, value)
            
            try:
                int_value = int(value)
            except (ValueError, TypeError):
                raise JSONValidationError(f"Cannot convert to integer", field_path, value)
            
            # Check range
            if type_name.startswith('u'):  # Unsigned
                bits = int(type_name[1:])
                min_val, max_val = 0, (2 ** bits) - 1
            else:  # Signed
                bits = int(type_name[1:])
                min_val, max_val = -(2 ** (bits - 1)), (2 ** (bits - 1)) - 1
            
            if not (min_val <= int_value <= max_val):
                raise JSONValidationError(
                    f"Value {int_value} out of range for {type_name} "
                    f"(valid range: {min_val} to {max_val})",
                    field_path, value
                )
            
            return int_value
        
        elif type_name in ['f32', 'f64']:
            if not isinstance(value, (int, float, str)):
                raise JSONValidationError(f"Expected number, got {type(value).__name__}", field_path, value)
            
            try:
                float_value = float(value)
            except (ValueError, TypeError):
                raise JSONValidationError(f"Cannot convert to float", field_path, value)
            
            return float_value
        
        else:
            raise JSONValidationError(f"Unknown primitive type: {type_name}", field_path, value)
    
    @staticmethod
    def validate_string_type(value: Any, field_path: str = "") -> str:
        """Validate string type values."""
        if not isinstance(value, str):
            raise JSONValidationError(f"Expected string, got {type(value).__name__}", field_path, value)
        return value
    
    @staticmethod
    def validate_bytes_type(value: Any, field_path: str = "") -> bytes:
        """Validate bytes type values."""
        if isinstance(value, str):
            # Assume base64 or hex encoding
            try:
                import base64
                return base64.b64decode(value)
            except Exception:
                try:
                    return bytes.fromhex(value)
                except Exception:
                    raise JSONValidationError(f"Cannot decode bytes from string", field_path, value)
        elif isinstance(value, list):
            # Array of integers
            try:
                return bytes(value)
            except (ValueError, TypeError):
                raise JSONValidationError(f"Cannot convert array to bytes", field_path, value)
        else:
            raise JSONValidationError(f"Expected string or array for bytes, got {type(value).__name__}", field_path, value)
    
    @staticmethod
    def validate_array_type(value: Any, element_validator, field_path: str = "") -> List[Any]:
        """Validate array type values."""
        if not isinstance(value, list):
            raise JSONValidationError(f"Expected array, got {type(value).__name__}", field_path, value)
        
        validated_elements = []
        for i, element in enumerate(value):
            element_path = f"{field_path}[{i}]" if field_path else f"[{i}]"
            validated_element = element_validator(element, element_path)
            validated_elements.append(validated_element)
        
        return validated_elements
    
    @staticmethod
    def coerce_json_types(data: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce JSON types for better compatibility."""
        coerced = {}
        for key, value in data.items():
            if isinstance(value, dict):
                coerced[key] = JSONValidator.coerce_json_types(value)
            elif isinstance(value, list):
                coerced[key] = [
                    JSONValidator.coerce_json_types(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str) and value.isdigit():
                # Try to convert string numbers to integers
                try:
                    coerced[key] = int(value)
                except ValueError:
                    coerced[key] = value
            elif isinstance(value, str) and re.match(r'^-?\\d+\\.\\d+$', value):
                # Try to convert string floats to floats
                try:
                    coerced[key] = float(value)
                except ValueError:
                    coerced[key] = value
            else:
                coerced[key] = value
        
        return coerced'''
    
    def _generate_enhanced_base_class(self) -> str:
        """Generate enhanced base class with JSON support."""
        base_class = super()._generate_base_class()
        
        # Add enhanced JSON methods to the base class
        enhanced_methods = '''
    def to_json_validated(self, validate: bool = True) -> str:
        """Convert to JSON with optional validation."""
        if validate:
            self.validate_json()
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))
    
    def to_json_pretty(self, validate: bool = True, indent: int = 2) -> str:
        """Convert to pretty-printed JSON with optional validation."""
        if validate:
            self.validate_json()
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_json_validated(cls, json_str: str, validate: bool = True):
        """Create instance from JSON with optional validation."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise JSONConversionError(f"Invalid JSON: {e}")
        
        if validate:
            cls.validate_json_data(data)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_json_coerced(cls, json_str: str):
        """Create instance from JSON with type coercion."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise JSONConversionError(f"Invalid JSON: {e}")
        
        coerced_data = JSONValidator.coerce_json_types(data)
        return cls.from_dict(coerced_data)
    
    def validate_json(self) -> None:
        """Validate this instance against its schema."""
        # To be implemented by subclasses
        pass
    
    @classmethod
    def validate_json_data(cls, data: Dict[str, Any]) -> None:
        """Validate JSON data against this class's schema."""
        # To be implemented by subclasses
        pass
    
    def to_json_stream(self, stream: Union[TextIO, BinaryIO], validate: bool = True) -> None:
        """Write JSON to a stream."""
        json_str = self.to_json_validated(validate)
        if hasattr(stream, 'mode') and 'b' in stream.mode:
            stream.write(json_str.encode('utf-8'))
        else:
            stream.write(json_str)
    
    @classmethod
    def from_json_stream(cls, stream: Union[TextIO, BinaryIO], validate: bool = True):
        """Read JSON from a stream."""
        if hasattr(stream, 'mode') and 'b' in stream.mode:
            json_str = stream.read().decode('utf-8')
        else:
            json_str = stream.read()
        
        return cls.from_json_validated(json_str, validate)'''
        
        # Insert enhanced methods before the closing of the base class
        if base_class:
            lines = base_class.split('\n')
            # Find the last method or the class definition
            insert_index = -1
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() and not lines[i].startswith('    '):
                    insert_index = i + 1
                    break
            
            if insert_index > 0:
                lines.insert(insert_index, enhanced_methods)
                return '\n'.join(lines)
        
        # Fallback: return base class with enhanced methods appended
        return f"{base_class}\n{enhanced_methods}" if base_class else enhanced_methods
    
    def _generate_enhanced_struct(self, struct: Struct) -> str:
        """Generate a struct with enhanced JSON support."""
        # Generate the basic struct
        basic_struct = super()._generate_struct(struct)
        
        # Add JSON validation methods
        validation_methods = self._generate_struct_validation_methods(struct)
        
        return f"{basic_struct}\n{validation_methods}"
    
    def _generate_enhanced_message(self, message: Message) -> str:
        """Generate a message with enhanced JSON support."""
        # Generate the basic message
        basic_message = super()._generate_message(message)
        
        # Add JSON validation methods
        validation_methods = self._generate_message_validation_methods(message)
        
        return f"{basic_message}\n{validation_methods}"
    
    def _generate_struct_validation_methods(self, struct: Struct) -> str:
        """Generate JSON validation methods for a struct."""
        struct_name = self._to_class_name(struct.name)
        
        # Generate field validations
        field_validations = []
        for field in struct.fields:
            validation = self._generate_field_validation(field)
            if validation:
                field_validations.append(f"        {validation}")
        
        validation_body = "\n".join(field_validations) if field_validations else "        pass"
        
        # Generate data validation
        data_validations = []
        for field in struct.fields:
            data_validation = self._generate_field_data_validation(field)
            if data_validation:
                data_validations.append(f"        {data_validation}")
        
        data_validation_body = "\n".join(data_validations) if data_validations else "        pass"
        
        return f'''
    def validate_json(self) -> None:
        """Validate this {struct_name} instance against its schema."""
{validation_body}
    
    @classmethod
    def validate_json_data(cls, data: Dict[str, Any]) -> None:
        """Validate JSON data against {struct_name} schema."""
        if not isinstance(data, dict):
            raise JSONValidationError("Expected JSON object")
        
        # Check for required fields
        required_fields = {{{", ".join(f'"{field.name}"' for field in struct.fields)}}}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise JSONValidationError(f"Missing required fields: {{', '.join(missing_fields)}}")
        
        # Check for extra fields
        extra_fields = set(data.keys()) - required_fields
        if extra_fields:
            raise JSONValidationError(f"Unexpected fields: {{', '.join(extra_fields)}}")
        
{data_validation_body}'''
    
    def _generate_message_validation_methods(self, message: Message) -> str:
        """Generate JSON validation methods for a message."""
        # Messages use the same validation logic as structs
        return self._generate_struct_validation_methods(message)
    
    def _generate_field_validation(self, field: Field) -> str:
        """Generate validation code for a field."""
        field_name = field.name
        field_type = field.type
        
        if isinstance(field_type, PrimitiveType):
            return f'JSONValidator.validate_primitive_type(self.{field_name}, "{field_type.name}", "{field_name}")'
        elif isinstance(field_type, StringType):
            return f'JSONValidator.validate_string_type(self.{field_name}, "{field_name}")'
        elif isinstance(field_type, BytesType):
            return f'# Bytes field "{field_name}" - validated during construction'
        elif isinstance(field_type, ArrayType):
            return self._generate_array_field_validation(field_name, field_type)
        elif isinstance(field_type, StructType):
            return f'self.{field_name}.validate_json()'
        
        return ""
    
    def _generate_field_data_validation(self, field: Field) -> str:
        """Generate validation code for field data from JSON."""
        field_name = field.name
        field_type = field.type
        
        if isinstance(field_type, PrimitiveType):
            return f'JSONValidator.validate_primitive_type(data["{field_name}"], "{field_type.name}", "{field_name}")'
        elif isinstance(field_type, StringType):
            return f'JSONValidator.validate_string_type(data["{field_name}"], "{field_name}")'
        elif isinstance(field_type, BytesType):
            return f'JSONValidator.validate_bytes_type(data["{field_name}"], "{field_name}")'
        elif isinstance(field_type, ArrayType):
            return self._generate_array_data_validation(field_name, field_type)
        elif isinstance(field_type, StructType):
            struct_name = self._to_class_name(field_type.name)
            return f'{struct_name}.validate_json_data(data["{field_name}"])'
        
        return ""
    
    def _generate_array_field_validation(self, field_name: str, array_type: ArrayType) -> str:
        """Generate validation for array fields."""
        element_type = array_type.element_type
        
        if isinstance(element_type, PrimitiveType):
            return f'''JSONValidator.validate_array_type(
            self.{field_name}, 
            lambda x, path: JSONValidator.validate_primitive_type(x, "{element_type.name}", path),
            "{field_name}"
        )'''
        elif isinstance(element_type, StringType):
            return f'''JSONValidator.validate_array_type(
            self.{field_name}, 
            JSONValidator.validate_string_type,
            "{field_name}"
        )'''
        elif isinstance(element_type, StructType):
            return f'''for i, item in enumerate(self.{field_name}):
            item.validate_json()'''
        
        return f'# Array field "{field_name}" - basic validation'
    
    def _generate_array_data_validation(self, field_name: str, array_type: ArrayType) -> str:
        """Generate validation for array data from JSON."""
        element_type = array_type.element_type
        
        if isinstance(element_type, PrimitiveType):
            return f'''JSONValidator.validate_array_type(
            data["{field_name}"], 
            lambda x, path: JSONValidator.validate_primitive_type(x, "{element_type.name}", path),
            "{field_name}"
        )'''
        elif isinstance(element_type, StringType):
            return f'''JSONValidator.validate_array_type(
            data["{field_name}"], 
            JSONValidator.validate_string_type,
            "{field_name}"
        )'''
        elif isinstance(element_type, StructType):
            struct_name = self._to_class_name(element_type.name)
            return f'''if not isinstance(data["{field_name}"], list):
            raise JSONValidationError("Expected array", "{field_name}", data["{field_name}"])
        for i, item in enumerate(data["{field_name}"]):
            {struct_name}.validate_json_data(item)'''
        
        return f'# Array field "{field_name}" - basic validation'
    
    def _generate_json_utilities(self) -> str:
        """Generate JSON utility functions."""
        struct_names = [self._to_class_name(s.name) for s in self.schema.structs]
        message_names = [self._to_class_name(m.name) for m in self.schema.messages]
        all_types = struct_names + message_names
        
        type_mapping = {}
        for struct in self.schema.structs:
            type_mapping[struct.name] = self._to_class_name(struct.name)
        for message in self.schema.messages:
            type_mapping[message.name] = self._to_class_name(message.name)
        
        type_map_entries = [f'    "{name}": {class_name}' for name, class_name in type_mapping.items()]
        type_map_str = ",\n".join(type_map_entries)
        
        return f'''# JSON utility functions
TYPE_MAP = {{
{type_map_str}
}}

def validate_json_by_type(type_name: str, json_data: Union[str, Dict[str, Any]]) -> Any:
    """Validate JSON data against a named schema type."""
    if type_name not in TYPE_MAP:
        raise JSONValidationError(f"Unknown type: {{type_name}}")
    
    type_class = TYPE_MAP[type_name]
    
    if isinstance(json_data, str):
        return type_class.from_json_validated(json_data)
    else:
        type_class.validate_json_data(json_data)
        return type_class.from_dict(json_data)

def convert_json_format(json_str: str, from_type: str, to_type: str) -> str:
    """Convert JSON from one type format to another."""
    if from_type not in TYPE_MAP or to_type not in TYPE_MAP:
        raise JSONValidationError("Unknown type in conversion")
    
    # Parse with source type
    source_obj = validate_json_by_type(from_type, json_str)
    
    # Convert to target type (this would need custom conversion logic)
    # For now, just validate that both types are compatible
    target_class = TYPE_MAP[to_type]
    
    # This is a simplified conversion - in practice, you'd need
    # custom conversion logic between different types
    return source_obj.to_json_validated()

def get_available_types() -> List[str]:
    """Get list of all available schema types."""
    return list(TYPE_MAP.keys())

def batch_validate_json(json_array_str: str, type_name: str) -> List[Any]:
    """Validate an array of JSON objects."""
    if type_name not in TYPE_MAP:
        raise JSONValidationError(f"Unknown type: {{type_name}}")
    
    try:
        json_array = json.loads(json_array_str)
    except json.JSONDecodeError as e:
        raise JSONConversionError(f"Invalid JSON array: {{e}}")
    
    if not isinstance(json_array, list):
        raise JSONValidationError("Expected JSON array")
    
    type_class = TYPE_MAP[type_name]
    results = []
    
    for i, item in enumerate(json_array):
        try:
            type_class.validate_json_data(item)
            obj = type_class.from_dict(item)
            results.append(obj)
        except Exception as e:
            raise JSONValidationError(f"Item {{i}}: {{e}}")
    
    return results'''
    
    def _generate_streaming_json_support(self) -> str:
        """Generate streaming JSON support."""
        return '''# Streaming JSON support
class JSONStreamer:
    """Streaming JSON processor for large datasets."""
    
    def __init__(self, type_name: str):
        if type_name not in TYPE_MAP:
            raise JSONValidationError(f"Unknown type: {type_name}")
        self.type_class = TYPE_MAP[type_name]
        self.type_name = type_name
    
    def stream_json_array(self, stream: Union[TextIO, BinaryIO], 
                         validate: bool = True) -> Iterator[Any]:
        """Stream parse a JSON array, yielding one object at a time."""
        if hasattr(stream, 'mode') and 'b' in stream.mode:
            content = stream.read().decode('utf-8')
        else:
            content = stream.read()
        
        try:
            json_array = json.loads(content)
        except json.JSONDecodeError as e:
            raise JSONStreamingError(f"Invalid JSON: {e}")
        
        if not isinstance(json_array, list):
            raise JSONStreamingError("Expected JSON array")
        
        for i, item in enumerate(json_array):
            try:
                if validate:
                    self.type_class.validate_json_data(item)
                obj = self.type_class.from_dict(item)
                yield obj
            except Exception as e:
                raise JSONStreamingError(f"Item {i}: {e}")
    
    def stream_json_lines(self, stream: Union[TextIO, BinaryIO],
                         validate: bool = True) -> Iterator[Any]:
        """Stream parse JSON Lines format (one JSON object per line)."""
        if hasattr(stream, 'mode') and 'b' in stream.mode:
            lines = stream.read().decode('utf-8').splitlines()
        else:
            lines = stream.read().splitlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                item = json.loads(line)
                if validate:
                    self.type_class.validate_json_data(item)
                obj = self.type_class.from_dict(item)
                yield obj
            except Exception as e:
                raise JSONStreamingError(f"Line {line_num}: {e}")
    
    def write_json_array(self, objects: Iterator[Any], 
                        stream: Union[TextIO, BinaryIO],
                        validate: bool = True, pretty: bool = False) -> None:
        """Write objects as a JSON array to stream."""
        indent = 2 if pretty else None
        separator = ',\\n' if pretty else ','
        
        if hasattr(stream, 'mode') and 'b' in stream.mode:
            write_func = lambda s: stream.write(s.encode('utf-8'))
        else:
            write_func = stream.write
        
        write_func('[')
        first = True
        
        for obj in objects:
            if not first:
                write_func(separator)
            
            if validate:
                obj.validate_json()
            
            json_str = obj.to_json_pretty() if pretty else obj.to_json_validated()
            if pretty and not first:
                # Indent the JSON
                lines = json_str.split('\\n')
                indented_lines = ['  ' + line for line in lines]
                json_str = '\\n'.join(indented_lines)
            
            write_func(json_str)
            first = False
        
        write_func(']')
    
    def write_json_lines(self, objects: Iterator[Any],
                        stream: Union[TextIO, BinaryIO],
                        validate: bool = True) -> None:
        """Write objects as JSON Lines format to stream."""
        if hasattr(stream, 'mode') and 'b' in stream.mode:
            write_func = lambda s: stream.write(s.encode('utf-8'))
        else:
            write_func = stream.write
        
        for obj in objects:
            if validate:
                obj.validate_json()
            
            json_str = obj.to_json_validated()
            write_func(json_str + '\\n')

def stream_convert_json_format(input_stream: Union[TextIO, BinaryIO],
                              output_stream: Union[TextIO, BinaryIO],
                              type_name: str,
                              input_format: str = 'array',
                              output_format: str = 'array',
                              validate: bool = True,
                              pretty: bool = False) -> None:
    """Convert between JSON formats using streaming."""
    streamer = JSONStreamer(type_name)
    
    # Read objects
    if input_format == 'array':
        objects = streamer.stream_json_array(input_stream, validate)
    elif input_format == 'lines':
        objects = streamer.stream_json_lines(input_stream, validate)
    else:
        raise JSONStreamingError(f"Unknown input format: {input_format}")
    
    # Write objects
    if output_format == 'array':
        streamer.write_json_array(objects, output_stream, validate, pretty)
    elif output_format == 'lines':
        streamer.write_json_lines(objects, output_stream, validate)
    else:
        raise JSONStreamingError(f"Unknown output format: {output_format}")'''


def enhance_python_json_support(schema_file: Path, output_file: Path,
                               module_name: str = "picomsg_types") -> None:
    """
    Generate enhanced Python code with JSON support.
    
    Args:
        schema_file: Path to the .pico schema file
        output_file: Path to write the generated Python code
        module_name: Name of the generated module
    """
    from ..schema.parser import SchemaParser
    
    parser = SchemaParser()
    schema = parser.parse_file(schema_file)
    
    generator = PythonJSONCodeGenerator(schema, module_name)
    code = generator.generate_code()
    
    with open(output_file, 'w') as f:
        f.write(code) 
