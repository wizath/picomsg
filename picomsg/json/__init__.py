"""
JSON Conversion System for PicoMsg.

This module provides unified JSON conversion utilities that work across
all language bindings, with schema-aware validation and streaming support.
"""

from typing import Dict, Any, Optional, Union, List, Type, BinaryIO
import json
import io
from pathlib import Path

from ..schema.ast import Schema, Struct, Message, Field, Type as PicoType
from ..schema.parser import SchemaParser


class JSONConversionError(Exception):
    """Base exception for JSON conversion errors."""
    pass


class JSONValidationError(JSONConversionError):
    """Schema validation error during JSON conversion."""
    pass


class JSONStreamingError(JSONConversionError):
    """Error during streaming JSON operations."""
    pass


class SchemaAwareJSONConverter:
    """
    Schema-aware JSON converter that validates JSON against PicoMsg schemas.
    
    This converter provides:
    - Schema validation for JSON data
    - Type coercion and validation
    - Pretty-printing with schema information
    - Cross-language JSON compatibility
    """
    
    def __init__(self, schema: Schema):
        """Initialize converter with a PicoMsg schema."""
        self.schema = schema
        self._struct_cache = {struct.name: struct for struct in schema.structs}
        self._message_cache = {msg.name: msg for msg in schema.messages}
    
    def validate_json(self, json_data: Dict[str, Any], type_name: str) -> bool:
        """
        Validate JSON data against a schema type.
        
        Args:
            json_data: JSON data to validate
            type_name: Name of the struct or message type
            
        Returns:
            True if valid, raises JSONValidationError if invalid
        """
        # Find the type definition
        type_def = self._struct_cache.get(type_name) or self._message_cache.get(type_name)
        if not type_def:
            raise JSONValidationError(f"Unknown type: {type_name}")
        
        # Validate all fields
        for field in type_def.fields:
            if field.name not in json_data:
                raise JSONValidationError(f"Missing required field: {field.name}")
            
            field_value = json_data[field.name]
            self._validate_field_value(field, field_value)
        
        # Check for extra fields
        expected_fields = {field.name for field in type_def.fields}
        actual_fields = set(json_data.keys())
        extra_fields = actual_fields - expected_fields
        if extra_fields:
            raise JSONValidationError(f"Unexpected fields: {extra_fields}")
        
        return True
    
    def _validate_field_value(self, field: Field, value: Any) -> None:
        """Validate a single field value against its type."""
        from ..schema.ast import (
            PrimitiveType, StringType, BytesType, ArrayType, StructType
        )
        
        field_type = field.type
        
        if isinstance(field_type, PrimitiveType):
            self._validate_primitive_value(field_type, value, field.name)
        elif isinstance(field_type, StringType):
            if not isinstance(value, str):
                raise JSONValidationError(f"Field {field.name} must be a string, got {type(value)}")
        elif isinstance(field_type, BytesType):
            if not isinstance(value, (str, list)):
                raise JSONValidationError(f"Field {field.name} must be a string or array, got {type(value)}")
        elif isinstance(field_type, ArrayType):
            if not isinstance(value, list):
                raise JSONValidationError(f"Field {field.name} must be an array, got {type(value)}")
            # Validate each element
            for i, elem in enumerate(value):
                try:
                    self._validate_type_value(field_type.element_type, elem)
                except JSONValidationError as e:
                    raise JSONValidationError(f"Field {field.name}[{i}]: {e}")
        elif isinstance(field_type, StructType):
            if not isinstance(value, dict):
                raise JSONValidationError(f"Field {field.name} must be an object, got {type(value)}")
            # Recursively validate nested struct
            self.validate_json(value, field_type.name)
    
    def _validate_primitive_value(self, prim_type, value: Any, field_name: str) -> None:
        """Validate a primitive type value."""
        type_name = prim_type.name
        
        if type_name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
            if not isinstance(value, int):
                raise JSONValidationError(f"Field {field_name} must be an integer, got {type(value)}")
            
            # Check range
            if type_name.startswith('u'):  # Unsigned
                bits = int(type_name[1:])
                min_val, max_val = 0, (2 ** bits) - 1
            else:  # Signed
                bits = int(type_name[1:])
                min_val, max_val = -(2 ** (bits - 1)), (2 ** (bits - 1)) - 1
            
            if not (min_val <= value <= max_val):
                raise JSONValidationError(
                    f"Field {field_name} value {value} out of range for {type_name} "
                    f"(valid range: {min_val} to {max_val})"
                )
        
        elif type_name in ['f32', 'f64']:
            if not isinstance(value, (int, float)):
                raise JSONValidationError(f"Field {field_name} must be a number, got {type(value)}")
    
    def _validate_type_value(self, type_def, value: Any) -> None:
        """Validate a value against a type definition."""
        from ..schema.ast import (
            PrimitiveType, StringType, BytesType, ArrayType, StructType
        )
        
        if isinstance(type_def, PrimitiveType):
            self._validate_primitive_value(type_def, value, "array_element")
        elif isinstance(type_def, StringType):
            if not isinstance(value, str):
                raise JSONValidationError(f"Array element must be a string, got {type(value)}")
        elif isinstance(type_def, StructType):
            if not isinstance(value, dict):
                raise JSONValidationError(f"Array element must be an object, got {type(value)}")
            self.validate_json(value, type_def.name)
    
    def pretty_print(self, json_data: Dict[str, Any], type_name: str, indent: int = 2) -> str:
        """
        Pretty-print JSON with schema information.
        
        Args:
            json_data: JSON data to format
            type_name: Name of the struct or message type
            indent: Indentation level
            
        Returns:
            Formatted JSON string with type annotations
        """
        # First validate the data
        self.validate_json(json_data, type_name)
        
        # Add schema information as comments (in a JSON-compatible way)
        annotated_data = self._add_type_annotations(json_data, type_name)
        
        return json.dumps(annotated_data, indent=indent, ensure_ascii=False)
    
    def _add_type_annotations(self, json_data: Dict[str, Any], type_name: str) -> Dict[str, Any]:
        """Add type annotations to JSON data."""
        type_def = self._struct_cache.get(type_name) or self._message_cache.get(type_name)
        if not type_def:
            return json_data
        
        # Create annotated copy
        annotated = {"$schema_type": type_name}
        annotated.update(json_data)
        
        return annotated
    
    def coerce_types(self, json_data: Dict[str, Any], type_name: str) -> Dict[str, Any]:
        """
        Coerce JSON data types to match schema requirements.
        
        This is useful when JSON data comes from sources that don't preserve
        exact type information (e.g., string numbers that should be integers).
        """
        type_def = self._struct_cache.get(type_name) or self._message_cache.get(type_name)
        if not type_def:
            raise JSONValidationError(f"Unknown type: {type_name}")
        
        coerced = {}
        for field in type_def.fields:
            if field.name in json_data:
                coerced[field.name] = self._coerce_field_value(field, json_data[field.name])
        
        return coerced
    
    def _coerce_field_value(self, field: Field, value: Any) -> Any:
        """Coerce a single field value to the correct type."""
        from ..schema.ast import (
            PrimitiveType, StringType, BytesType, ArrayType, StructType
        )
        
        field_type = field.type
        
        if isinstance(field_type, PrimitiveType):
            return self._coerce_primitive_value(field_type, value)
        elif isinstance(field_type, StringType):
            return str(value)
        elif isinstance(field_type, ArrayType):
            if isinstance(value, list):
                return [self._coerce_type_value(field_type.element_type, elem) for elem in value]
            return value
        elif isinstance(field_type, StructType):
            if isinstance(value, dict):
                return self.coerce_types(value, field_type.name)
            return value
        else:
            return value
    
    def _coerce_primitive_value(self, prim_type, value: Any) -> Any:
        """Coerce a primitive value to the correct type."""
        type_name = prim_type.name
        
        if type_name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        elif type_name in ['f32', 'f64']:
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        else:
            return value
    
    def _coerce_type_value(self, type_def, value: Any) -> Any:
        """Coerce a value based on type definition."""
        from ..schema.ast import (
            PrimitiveType, StringType, BytesType, ArrayType, StructType
        )
        
        if isinstance(type_def, PrimitiveType):
            return self._coerce_primitive_value(type_def, value)
        elif isinstance(type_def, StringType):
            return str(value)
        elif isinstance(type_def, StructType):
            if isinstance(value, dict):
                return self.coerce_types(value, type_def.name)
            return value
        else:
            return value


def load_schema_from_file(schema_file: Union[str, Path]) -> Schema:
    """Load a schema from a .pico file."""
    parser = SchemaParser()
    return parser.parse_file(Path(schema_file))


def create_converter(schema_file: Union[str, Path, Schema]) -> SchemaAwareJSONConverter:
    """
    Create a schema-aware JSON converter.
    
    Args:
        schema_file: Path to .pico file or Schema object
        
    Returns:
        SchemaAwareJSONConverter instance
    """
    if isinstance(schema_file, Schema):
        schema = schema_file
    else:
        schema = load_schema_from_file(schema_file)
    
    return SchemaAwareJSONConverter(schema)


# Convenience functions for common operations
def validate_json_file(json_file: Union[str, Path], type_name: str, 
                      schema_file: Union[str, Path]) -> bool:
    """Validate a JSON file against a schema type."""
    converter = create_converter(schema_file)
    
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    return converter.validate_json(json_data, type_name)


def pretty_print_json_file(json_file: Union[str, Path], type_name: str,
                          schema_file: Union[str, Path], output_file: Optional[Union[str, Path]] = None) -> str:
    """Pretty-print a JSON file with schema annotations."""
    converter = create_converter(schema_file)
    
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    formatted = converter.pretty_print(json_data, type_name)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(formatted)
    
    return formatted 
