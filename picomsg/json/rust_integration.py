"""
Rust JSON integration for PicoMsg.

This module enhances the Rust code generator with advanced JSON conversion
capabilities, including serde integration and custom serialization.
"""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from ..codegen.rust import RustCodeGenerator
from ..schema.ast import Schema, Struct, Message, Field, Type as PicoType
from ..schema.ast import PrimitiveType, StringType, BytesType, ArrayType, StructType


class RustJSONCodeGenerator(RustCodeGenerator):
    """
    Enhanced Rust code generator with advanced JSON support.
    
    This generator adds:
    - Serde integration with custom serialization
    - JSON validation methods
    - Schema-aware JSON conversion
    - Error handling for JSON operations
    """
    
    def __init__(self, schema: Schema, module_name: str = "picomsg_types"):
        """Initialize the enhanced Rust JSON code generator."""
        super().__init__(schema, module_name)
        self.json_features = {
            'serde_json': True,
            'validation': True,
            'custom_serialization': True,
            'error_handling': True
        }
    
    def generate_code(self) -> str:
        """Generate enhanced Rust code with JSON support."""
        code_parts = []
        
        # Add enhanced imports
        code_parts.append(self._generate_enhanced_imports())
        code_parts.append("")
        
        # Add JSON error types
        code_parts.append(self._generate_json_error_types())
        code_parts.append("")
        
        # Add JSON validation traits
        code_parts.append(self._generate_json_validation_traits())
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
        
        # Add schema validation functions
        code_parts.append(self._generate_schema_validation())
        
        return "\n".join(code_parts)
    
    def _generate_enhanced_imports(self) -> str:
        """Generate enhanced imports for JSON support."""
        imports = [
            "use serde::{Deserialize, Serialize, Deserializer, Serializer};",
            "use serde_json::{Value, Map};",
            "use std::collections::HashMap;",
            "use std::fmt;",
            "use std::error::Error;",
            "use std::io::{Read, Write};",
            "use std::str::FromStr;",
        ]
        
        # Add base imports from parent class
        base_imports = super()._generate_imports()
        if base_imports:
            imports.insert(0, base_imports)
        
        return "\n".join(imports)
    
    def _generate_json_error_types(self) -> str:
        """Generate JSON-specific error types."""
        return '''/// JSON conversion errors for PicoMsg types
#[derive(Debug, Clone)]
pub enum JsonError {
    /// Schema validation error
    ValidationError(String),
    /// Type conversion error
    ConversionError(String),
    /// Missing required field
    MissingField(String),
    /// Invalid field value
    InvalidValue(String, String),
    /// Serde JSON error
    SerdeError(String),
}

impl fmt::Display for JsonError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            JsonError::ValidationError(msg) => write!(f, "Validation error: {}", msg),
            JsonError::ConversionError(msg) => write!(f, "Conversion error: {}", msg),
            JsonError::MissingField(field) => write!(f, "Missing required field: {}", field),
            JsonError::InvalidValue(field, msg) => write!(f, "Invalid value for field '{}': {}", field, msg),
            JsonError::SerdeError(msg) => write!(f, "JSON error: {}", msg),
        }
    }
}

impl Error for JsonError {}

impl From<serde_json::Error> for JsonError {
    fn from(err: serde_json::Error) -> Self {
        JsonError::SerdeError(err.to_string())
    }
}

/// Result type for JSON operations
pub type JsonResult<T> = Result<T, JsonError>;'''
    
    def _generate_json_validation_traits(self) -> str:
        """Generate traits for JSON validation."""
        return '''/// Trait for JSON validation
pub trait JsonValidation {
    /// Validate JSON data against schema
    fn validate_json(&self) -> JsonResult<()>;
    
    /// Validate a JSON value against this type's schema
    fn validate_json_value(value: &Value) -> JsonResult<()>;
}

/// Trait for enhanced JSON conversion
pub trait JsonConversion: Serialize + for<'de> Deserialize<'de> {
    /// Convert to JSON with validation
    fn to_json_validated(&self) -> JsonResult<String> {
        self.validate_json()?;
        serde_json::to_string(self).map_err(JsonError::from)
    }
    
    /// Convert to pretty JSON with validation
    fn to_json_pretty(&self) -> JsonResult<String> {
        self.validate_json()?;
        serde_json::to_string_pretty(self).map_err(JsonError::from)
    }
    
    /// Parse from JSON with validation
    fn from_json_validated(json: &str) -> JsonResult<Self> {
        let value: Value = serde_json::from_str(json)?;
        Self::validate_json_value(&value)?;
        serde_json::from_value(value).map_err(JsonError::from)
    }
    
    /// Convert to JSON Value with validation
    fn to_json_value(&self) -> JsonResult<Value> {
        self.validate_json()?;
        serde_json::to_value(self).map_err(JsonError::from)
    }
    
    /// Parse from JSON Value with validation
    fn from_json_value(value: Value) -> JsonResult<Self> {
        Self::validate_json_value(&value)?;
        serde_json::from_value(value).map_err(JsonError::from)
    }
}'''
    
    def _generate_enhanced_struct(self, struct: Struct) -> str:
        """Generate a struct with enhanced JSON support."""
        struct_name = self._to_pascal_case(struct.name)
        
        # Generate the basic struct
        basic_struct = super()._generate_struct(struct)
        
        # Add JSON validation implementation
        validation_impl = self._generate_struct_validation(struct)
        
        # Add JSON conversion implementation
        conversion_impl = self._generate_struct_conversion(struct)
        
        return f"{basic_struct}\n\n{validation_impl}\n\n{conversion_impl}"
    
    def _generate_enhanced_message(self, message: Message) -> str:
        """Generate a message with enhanced JSON support."""
        message_name = self._to_pascal_case(message.name)
        
        # Generate the basic message
        basic_message = super()._generate_message(message)
        
        # Add JSON validation implementation
        validation_impl = self._generate_message_validation(message)
        
        # Add JSON conversion implementation
        conversion_impl = self._generate_message_conversion(message)
        
        return f"{basic_message}\n\n{validation_impl}\n\n{conversion_impl}"
    
    def _generate_struct_validation(self, struct: Struct) -> str:
        """Generate JSON validation implementation for a struct."""
        struct_name = self._to_pascal_case(struct.name)
        
        # Generate field validations
        field_validations = []
        for field in struct.fields:
            validation = self._generate_field_validation(field)
            if validation:
                field_validations.append(validation)
        
        validation_body = "\n        ".join(field_validations) if field_validations else "Ok(())"
        
        # Generate value validation
        value_validations = []
        for field in struct.fields:
            field_name = field.name
            value_validation = self._generate_field_value_validation(field)
            if value_validation:
                value_validations.append(f'''
        let {field_name}_value = value.get("{field_name}")
            .ok_or_else(|| JsonError::MissingField("{field_name}".to_string()))?;
        {value_validation}''')
        
        value_validation_body = "".join(value_validations) if value_validations else ""
        
        return f'''impl JsonValidation for {struct_name} {{
    fn validate_json(&self) -> JsonResult<()> {{
        {validation_body}
    }}
    
    fn validate_json_value(value: &Value) -> JsonResult<()> {{
        if !value.is_object() {{
            return Err(JsonError::ValidationError("Expected JSON object".to_string()));
        }}{value_validation_body}
        Ok(())
    }}
}}'''
    
    def _generate_message_validation(self, message: Message) -> str:
        """Generate JSON validation implementation for a message."""
        # Messages use the same validation logic as structs
        return self._generate_struct_validation(message)
    
    def _generate_struct_conversion(self, struct: Struct) -> str:
        """Generate JSON conversion implementation for a struct."""
        struct_name = self._to_pascal_case(struct.name)
        
        return f'''impl JsonConversion for {struct_name} {{}}'''
    
    def _generate_message_conversion(self, message: Message) -> str:
        """Generate JSON conversion implementation for a message."""
        message_name = self._to_pascal_case(message.name)
        
        return f'''impl JsonConversion for {message_name} {{}}'''
    
    def _generate_field_validation(self, field: Field) -> str:
        """Generate validation code for a field."""
        field_name = field.name
        field_type = field.type
        
        if isinstance(field_type, PrimitiveType):
            return self._generate_primitive_validation(field_name, field_type)
        elif isinstance(field_type, StringType):
            return f'// String field "{field_name}" - no additional validation needed'
        elif isinstance(field_type, BytesType):
            return f'// Bytes field "{field_name}" - no additional validation needed'
        elif isinstance(field_type, ArrayType):
            return self._generate_array_validation(field_name, field_type)
        elif isinstance(field_type, StructType):
            return f'self.{field_name}.validate_json()?;'
        
        return ""
    
    def _generate_field_value_validation(self, field: Field) -> str:
        """Generate validation code for a field value from JSON."""
        field_name = field.name
        field_type = field.type
        
        if isinstance(field_type, PrimitiveType):
            return self._generate_primitive_value_validation(field_name, field_type)
        elif isinstance(field_type, StringType):
            return f'''if !{field_name}_value.is_string() {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), "Expected string".to_string()));
        }}'''
        elif isinstance(field_type, BytesType):
            return f'''if !{field_name}_value.is_array() && !{field_name}_value.is_string() {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), "Expected array or string".to_string()));
        }}'''
        elif isinstance(field_type, ArrayType):
            return f'''if !{field_name}_value.is_array() {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), "Expected array".to_string()));
        }}'''
        elif isinstance(field_type, StructType):
            struct_name = self._to_pascal_case(field_type.name)
            return f'{struct_name}::validate_json_value({field_name}_value)?;'
        
        return ""
    
    def _generate_primitive_validation(self, field_name: str, prim_type: PrimitiveType) -> str:
        """Generate validation for primitive types."""
        type_name = prim_type.name
        
        if type_name in ['u8', 'u16', 'u32', 'u64']:
            max_val = (2 ** int(type_name[1:])) - 1
            return f'''if self.{field_name} > {max_val} {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), 
                format!("Value {{}} exceeds maximum for {type_name}", self.{field_name})));
        }}'''
        elif type_name in ['i8', 'i16', 'i32', 'i64']:
            bits = int(type_name[1:])
            min_val = -(2 ** (bits - 1))
            max_val = (2 ** (bits - 1)) - 1
            return f'''if self.{field_name} < {min_val} || self.{field_name} > {max_val} {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), 
                format!("Value {{}} out of range for {type_name}", self.{field_name})));
        }}'''
        
        return f'// Primitive field "{field_name}" ({type_name}) - basic validation'
    
    def _generate_primitive_value_validation(self, field_name: str, prim_type: PrimitiveType) -> str:
        """Generate JSON value validation for primitive types."""
        type_name = prim_type.name
        
        if type_name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
            return f'''if !{field_name}_value.is_number() {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), "Expected number".to_string()));
        }}'''
        elif type_name in ['f32', 'f64']:
            return f'''if !{field_name}_value.is_number() {{
            return Err(JsonError::InvalidValue("{field_name}".to_string(), "Expected number".to_string()));
        }}'''
        
        return ""
    
    def _generate_array_validation(self, field_name: str, array_type: ArrayType) -> str:
        """Generate validation for array types."""
        return f'''for item in &self.{field_name} {{
            // Validate array elements
        }}'''
    
    def _generate_json_utilities(self) -> str:
        """Generate JSON utility functions."""
        return '''/// JSON utility functions for PicoMsg types
pub mod json_utils {
    use super::*;
    
    /// Validate a JSON string against a schema type
    pub fn validate_json_string<T: JsonValidation + for<'de> Deserialize<'de>>(
        json: &str
    ) -> JsonResult<T> {
        let value: Value = serde_json::from_str(json)?;
        T::validate_json_value(&value)?;
        serde_json::from_value(value).map_err(JsonError::from)
    }
    
    /// Pretty-print JSON with validation
    pub fn pretty_print_json<T: JsonConversion>(data: &T) -> JsonResult<String> {
        data.to_json_pretty()
    }
    
    /// Convert between JSON formats with validation
    pub fn convert_json<T: JsonConversion>(json: &str) -> JsonResult<String> {
        let data = T::from_json_validated(json)?;
        data.to_json_validated()
    }
    
    /// Batch validate JSON objects
    pub fn batch_validate_json<T: JsonValidation + for<'de> Deserialize<'de>>(
        json_array: &str
    ) -> JsonResult<Vec<T>> {
        let values: Vec<Value> = serde_json::from_str(json_array)?;
        let mut results = Vec::new();
        
        for (i, value) in values.iter().enumerate() {
            T::validate_json_value(value)
                .map_err(|e| JsonError::ValidationError(format!("Item {}: {}", i, e)))?;
            let item: T = serde_json::from_value(value.clone())?;
            results.push(item);
        }
        
        Ok(results)
    }
}'''
    
    def _generate_schema_validation(self) -> str:
        """Generate schema validation functions."""
        struct_names = [self._to_pascal_case(s.name) for s in self.schema.structs]
        message_names = [self._to_pascal_case(m.name) for m in self.schema.messages]
        
        all_types = struct_names + message_names
        type_matches = []
        
        for type_name in all_types:
            type_matches.append(f'        "{type_name}" => {{' + f'''
            {type_name}::validate_json_value(value)?;
            Ok(())
        }}''')
        
        type_match_body = "\n".join(type_matches)
        
        return f'''/// Schema validation functions
pub mod schema_validation {{
    use super::*;
    
    /// Validate JSON against a named schema type
    pub fn validate_by_type_name(type_name: &str, value: &Value) -> JsonResult<()> {{
        match type_name {{
{type_match_body}
            _ => Err(JsonError::ValidationError(format!("Unknown type: {{}}", type_name))),
        }}
    }}
    
    /// Get all available type names
    pub fn get_type_names() -> Vec<&'static str> {{
        vec![{", ".join(f'"{name}"' for name in all_types)}]
    }}
    
    /// Check if a type name is valid
    pub fn is_valid_type_name(type_name: &str) -> bool {{
        get_type_names().contains(&type_name)
    }}
}}'''


def enhance_rust_json_support(schema_file: Path, output_file: Path, 
                             module_name: str = "picomsg_types") -> None:
    """
    Generate enhanced Rust code with JSON support.
    
    Args:
        schema_file: Path to the .pico schema file
        output_file: Path to write the generated Rust code
        module_name: Name of the generated module
    """
    from ..schema.parser import SchemaParser
    
    parser = SchemaParser()
    schema = parser.parse_file(schema_file)
    
    generator = RustJSONCodeGenerator(schema, module_name)
    code = generator.generate_code()
    
    with open(output_file, 'w') as f:
        f.write(code)


def generate_rust_json_cargo_toml(output_dir: Path, package_name: str = "picomsg-types") -> None:
    """
    Generate Cargo.toml with JSON dependencies.
    
    Args:
        output_dir: Directory to write Cargo.toml
        package_name: Name of the Rust package
    """
    cargo_toml_content = f'''[package]
name = "{package_name}"
version = "0.1.0"
edition = "2021"
description = "PicoMsg types with enhanced JSON support"
license = "MIT OR Apache-2.0"

[dependencies]
serde = {{ version = "1.0", features = ["derive"] }}
serde_json = "1.0"

[dev-dependencies]
serde_test = "1.0"

[features]
default = ["json"]
json = ["serde", "serde_json"]
validation = []
'''
    
    cargo_file = output_dir / "Cargo.toml"
    with open(cargo_file, 'w') as f:
        f.write(cargo_toml_content) 
