"""
Rust JSON validation code generator for PicoMsg using serde + validator.
"""

from typing import Dict, List
from ..schema.ast import (
    Schema, Struct, Message, Field, Type, Enum, EnumValue,
    PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
)
from .base import CodeGenerator


class RustJsonCodeGenerator(CodeGenerator):
    """Generate Rust JSON validation code using serde + validator."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
    
    def generate(self) -> Dict[str, str]:
        """Generate Rust JSON validation files."""
        module_name = self.get_option('module_name', 'picomsg_json')
        
        files = {}
        files[f"{module_name}.rs"] = self._generate_module()
        files["Cargo.toml"] = self._generate_cargo_toml()
        
        return files
    
    def _generate_module(self) -> str:
        """Generate Rust module file with JSON validation."""
        lines = [
            "//! Generated PicoMsg Rust JSON validation bindings",
            "//! This file is auto-generated. Do not edit manually.",
            "",
            "use serde::{Deserialize, Serialize};",
            "use validator::{Validate, ValidationError, ValidationErrors};",
            "",
        ]
        
        # Generate enum definitions (if any)
        if hasattr(self.schema, 'enums') and self.schema.enums:
            for enum in self.schema.enums:
                lines.extend(self._generate_enum_definition(enum))
                lines.append("")
        
        # Generate struct definitions
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_definition(struct))
            lines.append("")
        
        # Generate message definitions
        for message in self.schema.messages:
            lines.extend(self._generate_message_definition(message))
            lines.append("")
        
        # Generate default value functions
        lines.extend(self._generate_default_functions())
        lines.append("")
        
        # Generate custom validation functions
        lines.extend(self._generate_custom_validation_functions())
        lines.append("")
        
        # Generate validation helpers
        lines.extend(self._generate_validation_helpers())
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_cargo_toml(self) -> str:
        """Generate Cargo.toml with required dependencies."""
        namespace = self.schema.namespace.name if self.schema.namespace else "picomsg"
        package_name = namespace.replace('.', '_') + "_json"
        
        return f'''[package]
name = "{package_name}"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = {{ version = "1.0", features = ["derive"] }}
serde_json = "1.0"
validator = {{ version = "0.16", features = ["derive"] }}
'''
    
    def _generate_enum_definition(self, enum: Enum) -> List[str]:
        """Generate Rust enum definition with serde support."""
        namespace_prefix = self._get_namespace_prefix()
        enum_name = f"{namespace_prefix}{enum.name}" if namespace_prefix else enum.name
        
        lines = [
            f"/// Enum: {enum.name}",
            "#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]",
            "#[serde(rename_all = \"snake_case\")]",
            f"pub enum {enum_name} {{",
        ]
        
        for value in enum.values:
            lines.append(f"    {value.name} = {value.value},")
        
        lines.append("}")
        
        return lines
    
    def _generate_struct_definition(self, struct: Struct) -> List[str]:
        """Generate Rust struct definition with validation."""
        namespace_prefix = self._get_namespace_prefix()
        struct_name = f"{namespace_prefix}{struct.name}" if namespace_prefix else struct.name
        
        lines = [
            f"/// Struct: {struct.name}",
            "#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Validate)]",
            f"pub struct {struct_name} {{",
        ]
        
        # Generate fields with validation
        for field in struct.fields:
            rust_type = self._get_rust_type(field.type)
            validation_attrs = self._get_validation_attributes(field)
            
            if validation_attrs:
                for attr in validation_attrs:
                    lines.append(f"    {attr}")
            
            if field.has_default():
                default_value = self._get_rust_default_value(field)
                lines.append(f"    #[serde(default = \"{default_value}\")]")
            
            lines.append(f"    pub {field.name}: {rust_type},")
        
        lines.append("}")
        
        return lines
    
    def _generate_message_definition(self, message: Message) -> List[str]:
        """Generate Rust message definition with validation."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name}" if namespace_prefix else message.name
        
        lines = [
            f"/// Message: {message.name}",
            "#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Validate)]",
            f"pub struct {message_name} {{",
        ]
        
        # Generate fields with validation
        for field in message.fields:
            rust_type = self._get_rust_type(field.type)
            validation_attrs = self._get_validation_attributes(field)
            
            if validation_attrs:
                for attr in validation_attrs:
                    lines.append(f"    {attr}")
            
            if field.has_default():
                default_value = self._get_rust_default_value(field)
                lines.append(f"    #[serde(default = \"{default_value}\")]")
            elif not field.is_required():
                lines.append(f"    #[serde(skip_serializing_if = \"Option::is_none\")]")
            
            lines.append(f"    pub {field.name}: {rust_type},")
        
        lines.append("}")
        
        return lines
    
    def _generate_validation_helpers(self) -> List[str]:
        """Generate validation helper functions."""
        lines = [
            "/// Validation helper functions",
            "",
            "pub fn validate_json_string<T>(json_str: &str) -> Result<T, ValidationErrors>",
            "where",
            "    T: for<'de> Deserialize<'de> + Validate,",
            "{",
            "    let data: T = serde_json::from_str(json_str)",
            "        .map_err(|e| {",
            "            let mut errors = ValidationErrors::new();",
            "            errors.add(\"json\", ValidationError::new(\"parse_error\"));",
            "            errors",
            "        })?;",
            "    data.validate()?;",
            "    Ok(data)",
            "}",
            "",
            "pub fn to_validated_json<T>(data: &T) -> Result<String, ValidationErrors>",
            "where",
            "    T: Serialize + Validate,",
            "{",
            "    data.validate()?;",
            "    serde_json::to_string(data)",
            "        .map_err(|e| {",
            "            let mut errors = ValidationErrors::new();",
            "            errors.add(\"json\", ValidationError::new(\"serialize_error\"));",
            "            errors",
            "        })",
            "}",
        ]
        
        return lines
    
    def _generate_default_functions(self) -> List[str]:
        """Generate default value functions."""
        lines = ["/// Default value functions", ""]
        
        # Collect all default values used in the schema with their field types
        default_values = set()
        for struct in self.schema.structs:
            for field in struct.fields:
                if field.has_default():
                    rust_type = self._get_rust_type(field.type)
                    default_values.add((field.default_value, rust_type))
        
        for message in self.schema.messages:
            for field in message.fields:
                if field.has_default():
                    rust_type = self._get_rust_type(field.type)
                    default_values.add((field.default_value, rust_type))
        
        # Generate functions for each unique default value
        for value, rust_type in default_values:
            if value is None:
                lines.extend([
                    f"fn default_none_{rust_type.replace('<', '_').replace('>', '_')}() -> {rust_type} {{",
                    f"    {rust_type}::default()",
                    "}",
                    "",
                ])
            elif isinstance(value, bool):
                func_name = f"default_bool_{str(value).lower()}"
                lines.extend([
                    f"fn {func_name}() -> bool {{",
                    f"    {str(value).lower()}",
                    "}",
                    "",
                ])
            elif isinstance(value, (int, float)):
                func_name = f"default_{rust_type}_{value}".replace('.', '_').replace('-', 'neg')
                if isinstance(value, float):
                    if rust_type == "f64":
                        rust_value = f"{value}_f64"
                    else:
                        rust_value = f"{value}_f32"
                else:
                    rust_value = f"{value}_{rust_type}"
                lines.extend([
                    f"fn {func_name}() -> {rust_type} {{",
                    f"    {rust_value}",
                    "}",
                    "",
                ])
            elif isinstance(value, str):
                func_name = f"default_string_{hash(value) % 1000}"
                lines.extend([
                    f"fn {func_name}() -> String {{",
                    f"    \"{value}\".to_string()",
                    "}",
                    "",
                ])
        
        return lines
    
    def _generate_custom_validation_functions(self) -> List[str]:
        """Generate custom validation functions."""
        lines = ["/// Custom validation functions", ""]
        
        # Check if we need float validation
        has_floats = False
        for struct in self.schema.structs:
            for field in struct.fields:
                if isinstance(field.type, PrimitiveType) and field.type.name in ['f32', 'f64']:
                    has_floats = True
                    break
        
        for message in self.schema.messages:
            for field in message.fields:
                if isinstance(field.type, PrimitiveType) and field.type.name in ['f32', 'f64']:
                    has_floats = True
                    break
        
        if has_floats:
            lines.extend([
                "fn validate_finite_float(value: f32) -> Result<(), ValidationError> {",
                "    if value.is_finite() {",
                "        Ok(())",
                "    } else {",
                "        Err(ValidationError::new(\"must_be_finite\"))",
                "    }",
                "}",
                "",
                "fn validate_finite_double(value: f64) -> Result<(), ValidationError> {",
                "    if value.is_finite() {",
                "        Ok(())",
                "    } else {",
                "        Err(ValidationError::new(\"must_be_finite\"))",
                "    }",
                "}",
                "",
            ])
        
        return lines
    
    def _get_validation_attributes(self, field: Field) -> List[str]:
        """Get validation attributes for a field."""
        attrs = []
        
        if isinstance(field.type, PrimitiveType):
            if field.type.name in ['u8', 'i8', 'u16', 'i16', 'u32', 'i32', 'u64', 'i64']:
                # Integer range validation based on type
                min_val, max_val = self._get_integer_range(field.type.name)
                if min_val is not None and max_val is not None:
                    attrs.append(f"    #[validate(range(min = {min_val}, max = {max_val}))]")
            elif field.type.name in ['f32', 'f64']:
                # Float validation - ensure finite values
                attrs.append("    #[validate(custom = \"validate_finite_float\")]")
        
        elif isinstance(field.type, StringType):
            # String length validation
            attrs.append("    #[validate(length(min = 0, max = 65535))]")  # Max string length
        
        elif isinstance(field.type, BytesType):
            # Bytes length validation
            attrs.append("    #[validate(length(min = 0, max = 1048576))]")  # Max 1MB
        
        elif isinstance(field.type, ArrayType):
            # Array length validation
            attrs.append("    #[validate(length(min = 0, max = 10000))]")  # Reasonable max array size
        
        elif isinstance(field.type, FixedArrayType):
            # Fixed array validation
            attrs.append(f"    #[validate(length(min = {field.type.size}, max = {field.type.size}))]")
        
        return attrs
    
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
        return ranges.get(type_name, (None, None))
    
    def _get_rust_type(self, type_: Type) -> str:
        """Get Rust type for JSON validation."""
        if isinstance(type_, PrimitiveType):
            type_map = {
                'u8': 'u8', 'i8': 'i8', 'u16': 'u16', 'i16': 'i16',
                'u32': 'u32', 'i32': 'i32', 'u64': 'u64', 'i64': 'i64',
                'f32': 'f32', 'f64': 'f64', 'bool': 'bool'
            }
            return type_map.get(type_.name, type_.name)
        
        elif isinstance(type_, StringType):
            return "String"
        
        elif isinstance(type_, BytesType):
            return "Vec<u8>"
        
        elif isinstance(type_, ArrayType):
            element_type = self._get_rust_type(type_.element_type)
            return f"Vec<{element_type}>"
        
        elif isinstance(type_, FixedArrayType):
            element_type = self._get_rust_type(type_.element_type)
            return f"Vec<{element_type}>"  # Use Vec for JSON compatibility
        
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            return f"{namespace_prefix}{type_.name}" if namespace_prefix else type_.name
        
        elif isinstance(type_, EnumType):
            namespace_prefix = self._get_namespace_prefix()
            return f"{namespace_prefix}{type_.name}" if namespace_prefix else type_.name
        
        return "String"  # Fallback
    
    def _get_rust_default_value(self, field: Field) -> str:
        """Get Rust default value function name."""
        rust_type = self._get_rust_type(field.type)
        
        if field.default_value is None:
            return f"default_none_{rust_type.replace('<', '_').replace('>', '_')}"
        elif isinstance(field.default_value, bool):
            return f"default_bool_{str(field.default_value).lower()}"
        elif isinstance(field.default_value, (int, float)):
            return f"default_{rust_type}_{field.default_value}".replace('.', '_').replace('-', 'neg')
        elif isinstance(field.default_value, str):
            return f"default_string_{hash(field.default_value) % 1000}"
        else:
            return f"default_none_{rust_type.replace('<', '_').replace('>', '_')}"
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize identifier for Rust."""
        # Convert to snake_case and handle Rust keywords
        import re
        name = re.sub(r'([A-Z])', r'_\1', name).lower().lstrip('_')
        
        rust_keywords = {
            'as', 'break', 'const', 'continue', 'crate', 'else', 'enum', 'extern',
            'false', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop', 'match',
            'mod', 'move', 'mut', 'pub', 'ref', 'return', 'self', 'Self',
            'static', 'struct', 'super', 'trait', 'true', 'type', 'unsafe',
            'use', 'where', 'while'
        }
        
        if name in rust_keywords:
            return f"r#{name}"
        
        return name
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for generated identifiers."""
        if self.schema.namespace:
            return self.schema.namespace.name.replace('.', '_').title()
        return '' 
