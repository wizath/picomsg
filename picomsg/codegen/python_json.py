"""
Python JSON validation code generator for PicoMsg using Pydantic.
"""

from typing import Dict, List
from ..schema.ast import (
    Schema, Struct, Message, Field, Type, Enum, EnumValue,
    PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
)
from .base import CodeGenerator


class PythonJsonCodeGenerator(CodeGenerator):
    """Generate Python JSON validation code using Pydantic."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
    
    def generate(self) -> Dict[str, str]:
        """Generate Python JSON validation files."""
        module_name = self.get_option('module_name', 'picomsg_json')
        
        files = {}
        files[f"{module_name}.py"] = self._generate_module()
        files["requirements.txt"] = self._generate_requirements()
        
        return files
    
    def _generate_module(self) -> str:
        """Generate Python module file with JSON validation."""
        lines = [
            '"""Generated PicoMsg Python JSON validation bindings"""',
            '# This file is auto-generated. Do not edit manually.',
            '',
            'from typing import Dict, List, Optional, Union, Any',
            'from enum import IntEnum',
            'from pydantic import BaseModel, Field, field_validator, ValidationError',
            'from pydantic.types import conint, confloat, constr, conlist',
            'import json',
            '',
        ]
        
        # Generate enum definitions (if any)
        if hasattr(self.schema, 'enums') and self.schema.enums:
            for enum in self.schema.enums:
                lines.extend(self._generate_enum_definition(enum))
                lines.append('')
        
        # Generate struct definitions
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_definition(struct))
            lines.append('')
        
        # Generate message definitions
        for message in self.schema.messages:
            lines.extend(self._generate_message_definition(message))
            lines.append('')
        
        # Generate validation helpers
        lines.extend(self._generate_validation_helpers())
        lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt with required dependencies."""
        return '''pydantic>=2.0.0
typing-extensions>=4.0.0
'''
    
    def _generate_enum_definition(self, enum: Enum) -> List[str]:
        """Generate Python enum definition."""
        namespace_prefix = self._get_namespace_prefix()
        enum_name = f"{namespace_prefix}{enum.name}" if namespace_prefix else enum.name
        
        lines = [
            f'class {enum_name}(IntEnum):',
            f'    """Enum: {enum.name}"""',
        ]
        
        for value in enum.values:
            lines.append(f'    {value.name} = {value.value}')
        
        return lines
    
    def _generate_struct_definition(self, struct: Struct) -> List[str]:
        """Generate Python struct definition with validation."""
        namespace_prefix = self._get_namespace_prefix()
        struct_name = f"{namespace_prefix}{struct.name}" if namespace_prefix else struct.name
        
        lines = [
            f'class {struct_name}(BaseModel):',
            f'    """Struct: {struct.name}"""',
            '',
        ]
        
        # Generate fields with validation
        for field in struct.fields:
            python_type = self._get_python_type(field)
            field_def = self._get_field_definition(field)
            
            lines.append(f'    {field.name}: {python_type} = {field_def}')
        
        # Generate custom validators if needed
        validators = self._generate_custom_validators(struct.fields)
        if validators:
            lines.append('')
            lines.extend(validators)
        
        # Generate model configuration
        lines.extend(self._generate_model_config())
        
        return lines
    
    def _generate_message_definition(self, message: Message) -> List[str]:
        """Generate Python message definition with validation."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name}" if namespace_prefix else message.name
        
        lines = [
            f'class {message_name}(BaseModel):',
            f'    """Message: {message.name}"""',
            '',
        ]
        
        # Generate fields with validation
        for field in message.fields:
            python_type = self._get_python_type(field)
            field_def = self._get_field_definition(field)
            
            lines.append(f'    {field.name}: {python_type} = {field_def}')
        
        # Generate custom validators if needed
        validators = self._generate_custom_validators(message.fields)
        if validators:
            lines.append('')
            lines.extend(validators)
        
        # Generate model configuration
        lines.extend(self._generate_model_config())
        
        return lines
    
    def _generate_validation_helpers(self) -> List[str]:
        """Generate validation helper functions."""
        lines = [
            '# Validation helper functions',
            '',
            'def validate_json_string(model_class: type[BaseModel], json_str: str) -> BaseModel:',
            '    """Validate JSON string and return model instance."""',
            '    try:',
            '        data = json.loads(json_str)',
            '        return model_class.model_validate(data)',
            '    except json.JSONDecodeError as e:',
            '        raise ValidationError(f"Invalid JSON: {e}") from e',
            '',
            'def to_validated_json(model: BaseModel, indent: Optional[int] = None) -> str:',
            '    """Convert validated model to JSON string."""',
            '    return model.model_dump_json(indent=indent)',
            '',
            'def validate_dict(model_class: type[BaseModel], data: Dict[str, Any]) -> BaseModel:',
            '    """Validate dictionary and return model instance."""',
            '    return model_class.model_validate(data)',
        ]
        
        return lines
    
    def _get_python_type(self, field: Field) -> str:
        """Get Python type annotation for a field."""
        base_type = self._get_base_python_type(field.type)
        
        # Handle optional fields (those with explicit defaults or not required)
        if field.has_default() or not field.is_required():
            if not base_type.startswith('Optional['):
                base_type = f'Optional[{base_type}]'
        
        return base_type
    
    def _get_base_python_type(self, type_: Type) -> str:
        """Get base Python type for validation."""
        if isinstance(type_, PrimitiveType):
            if type_.name in ['u8', 'i8', 'u16', 'i16', 'u32', 'i32', 'u64', 'i64']:
                # Use constrained integers with proper ranges
                min_val, max_val = self._get_integer_range(type_.name)
                return f'conint(ge={min_val}, le={max_val})'
            elif type_.name in ['f32', 'f64']:
                return 'confloat(allow_inf_nan=False)'
            elif type_.name == 'bool':
                return 'bool'
        
        elif isinstance(type_, StringType):
            return 'constr(max_length=65535)'  # Max string length
        
        elif isinstance(type_, BytesType):
            return 'conlist(int, max_length=1048576)'  # Max 1MB as list of bytes
        
        elif isinstance(type_, ArrayType):
            element_type = self._get_base_python_type(type_.element_type)
            return f'conlist({element_type}, max_length=10000)'  # Reasonable max array size
        
        elif isinstance(type_, FixedArrayType):
            element_type = self._get_base_python_type(type_.element_type)
            return f'conlist({element_type}, min_length={type_.size}, max_length={type_.size})'
        
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            return f'"{namespace_prefix}{type_.name}"' if namespace_prefix else f'"{type_.name}"'
        
        elif isinstance(type_, EnumType):
            namespace_prefix = self._get_namespace_prefix()
            return f'{namespace_prefix}{type_.name}' if namespace_prefix else type_.name
        
        return 'str'  # Fallback
    
    def _get_field_definition(self, field: Field) -> str:
        """Get Pydantic field definition."""
        if field.has_default():
            default_value = self._get_python_default_value(field)
            return f'Field(default={default_value})'
        elif not field.is_required():
            return 'Field(default=None)'
        else:
            return 'Field(...)'  # Required field
    
    def _get_python_default_value(self, field: Field) -> str:
        """Get Python default value representation."""
        if field.default_value is None:
            return 'None'
        elif isinstance(field.default_value, bool):
            return str(field.default_value)
        elif isinstance(field.default_value, (int, float)):
            return str(field.default_value)
        elif isinstance(field.default_value, str):
            return repr(field.default_value)  # Properly escape string
        else:
            return 'None'
    
    def _get_integer_range(self, type_name: str) -> tuple:
        """Get integer range for validation."""
        ranges = {
            'u8': (0, 255),
            'i8': (-128, 127),
            'u16': (0, 65535),
            'i16': (-32768, 32767),
            'u32': (0, 4294967295),
            'i32': (-2147483648, 2147483647),
            'u64': (0, 18446744073709551615),
            'i64': (-9223372036854775808, 9223372036854775807),
        }
        return ranges.get(type_name, (0, 2**63-1))
    
    def _generate_custom_validators(self, fields: List[Field]) -> List[str]:
        """Generate custom validators for complex validation logic."""
        validators = []
        
        # Check if we need any custom validators
        has_bytes_fields = any(isinstance(f.type, BytesType) for f in fields)
        has_float_fields = any(isinstance(f.type, PrimitiveType) and f.type.name in ['f32', 'f64'] for f in fields)
        
        if has_float_fields:
            validators.extend([
                '    @field_validator("*", mode="before")',
                '    @classmethod',
                '    def validate_float_fields(cls, v):',
                '        """Validate float fields are finite."""',
                '        if isinstance(v, float):',
                '            import math',
                '            if not math.isfinite(v):',
                '                raise ValueError("Float must be finite")',
                '        return v',
            ])
        
        return validators
    
    def _generate_model_config(self) -> List[str]:
        """Generate Pydantic model configuration."""
        return [
            '',
            '    model_config = {',
            '        "validate_assignment": True,',
            '        "extra": "forbid",',
            '        "use_enum_values": True,',
            '    }',
        ]
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize identifier for Python."""
        # Handle Python keywords
        python_keywords = {
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'with', 'yield'
        }
        
        if name in python_keywords:
            return f'{name}_'
        
        return name
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for generated identifiers."""
        if self.schema.namespace:
            return self.schema.namespace.name.replace('.', '_').title()
        return '' 
