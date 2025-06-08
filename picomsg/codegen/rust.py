"""
Rust code generator for PicoMsg.
"""

from typing import Dict, List
from ..schema.ast import (
    Schema, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType
)
from .base import CodeGenerator


class RustCodeGenerator(CodeGenerator):
    """Generate Rust code from PicoMsg schema."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
        self.type_id_counter = 1  # Start from 1, 0 reserved for invalid
    
    def generate(self) -> Dict[str, str]:
        """Generate Rust module file."""
        module_name = self.get_option('module_name', 'picomsg_generated')
        
        files = {}
        files[f"{module_name}.rs"] = self._generate_module()
        
        return files
    
    def _generate_module(self) -> str:
        """Generate Rust module file."""
        lines = [
            "//! Generated PicoMsg Rust bindings",
            "//! This file is auto-generated. Do not edit manually.",
            "",
            "use serde::{Deserialize, Serialize};",
            "use std::io::{Read, Write};",
            "use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};",
            "",
        ]
        
        # Generate constants
        lines.extend(self._generate_constants())
        lines.append("")
        
        # Generate error types
        lines.extend(self._generate_error_types())
        lines.append("")
        
        # Generate struct definitions
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_definition(struct))
            lines.append("")
        
        # Generate message definitions
        for message in self.schema.messages:
            lines.extend(self._generate_message_definition(message))
            lines.append("")
        
        # Generate serialization trait
        lines.extend(self._generate_serialization_trait())
        lines.append("")
        
        # Generate implementations for structs
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_impl(struct))
            lines.append("")
        
        # Generate implementations for messages
        for message in self.schema.messages:
            lines.extend(self._generate_message_impl(message))
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_constants(self) -> List[str]:
        """Generate constants and type IDs."""
        namespace_prefix = self._get_namespace_prefix()
        const_prefix = namespace_prefix.upper() + "_" if namespace_prefix else ""
        schema_version = self.schema.version if self.schema.version is not None else 1
        
        lines = [
            "// PicoMsg format constants",
            f"pub const {const_prefix}MAGIC_BYTE_1: u8 = 0xAB;",
            f"pub const {const_prefix}MAGIC_BYTE_2: u8 = 0xCD;",
            f"pub const {const_prefix}VERSION: u8 = {schema_version};",
            f"pub const {const_prefix}HEADER_SIZE: usize = 8;",
            "",
            "// Message type IDs",
        ]
        
        # Generate message type IDs
        for message in self.schema.messages:
            type_id = self.type_id_counter
            self.type_id_counter += 1
            lines.append(f"pub const {const_prefix}{message.name.upper()}_TYPE_ID: u16 = {type_id};")
        
        return lines
    
    def _generate_error_types(self) -> List[str]:
        """Generate error types."""
        namespace_prefix = self._get_namespace_prefix()
        error_name = f"{namespace_prefix}Error" if namespace_prefix else "PicoMsgError"
        result_name = f"{namespace_prefix}Result" if namespace_prefix else "PicoMsgResult"
        
        lines = [
            "// Error types",
            "#[derive(Debug, Clone, PartialEq)]",
            f"pub enum {error_name} {{",
            "    InvalidHeader,",
            "    BufferTooSmall,",
            "    InvalidData,",
            "    IoError(String),",
            "}",
            "",
            f"impl std::fmt::Display for {error_name} {{",
            "    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {",
            "        match self {",
            f"            {error_name}::InvalidHeader => write!(f, \"Invalid header\"),",
            f"            {error_name}::BufferTooSmall => write!(f, \"Buffer too small\"),",
            f"            {error_name}::InvalidData => write!(f, \"Invalid data\"),",
            f"            {error_name}::IoError(msg) => write!(f, \"IO error: {{}}\", msg),",
            "        }",
            "    }",
            "}",
            "",
            f"impl std::error::Error for {error_name} {{}}",
            "",
            f"impl From<std::io::Error> for {error_name} {{",
            "    fn from(err: std::io::Error) -> Self {",
            f"        {error_name}::IoError(err.to_string())",
            "    }",
            "}",
            "",
            f"pub type {result_name}<T> = Result<T, {error_name}>;",
        ]
        
        return lines
    
    def _generate_struct_definition(self, struct: Struct) -> List[str]:
        """Generate Rust struct definition."""
        namespace_prefix = self._get_namespace_prefix()
        struct_name = f"{namespace_prefix}{struct.name}" if namespace_prefix else struct.name
        
        lines = [
            f"/// Struct: {struct.name}",
            "#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]",
            f"pub struct {struct_name} {{",
        ]
        
        # Generate fields
        for field in struct.fields:
            rust_type = self._get_rust_type(field.type)
            lines.append(f"    pub {field.name}: {rust_type},")
        
        lines.append("}")
        
        return lines
    
    def _generate_message_definition(self, message: Message) -> List[str]:
        """Generate Rust message definition."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name}" if namespace_prefix else message.name
        
        lines = [
            f"/// Message: {message.name}",
            "#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]",
            f"pub struct {message_name} {{",
        ]
        
        # Generate fields
        for field in message.fields:
            rust_type = self._get_rust_type(field.type)
            lines.append(f"    pub {field.name}: {rust_type},")
        
        lines.append("}")
        
        return lines
    
    def _generate_serialization_trait(self) -> List[str]:
        """Generate serialization trait."""
        namespace_prefix = self._get_namespace_prefix()
        trait_name = f"{namespace_prefix}Serialize" if namespace_prefix else "PicoMsgSerialize"
        result_type = f"{namespace_prefix}Result" if namespace_prefix else "PicoMsgResult"
        
        lines = [
            "/// Trait for PicoMsg serialization",
            f"pub trait {trait_name} {{",
            f"    fn from_bytes(data: &[u8]) -> {result_type}<Self> where Self: Sized;",
            f"    fn to_bytes(&self) -> {result_type}<Vec<u8>>;",
            f"    fn from_reader<R: Read>(reader: &mut R) -> {result_type}<Self> where Self: Sized;",
            f"    fn to_writer<W: Write>(&self, writer: &mut W) -> {result_type}<()>;",
            "}",
        ]
        
        return lines
    
    def _generate_struct_impl(self, struct: Struct) -> List[str]:
        """Generate implementation for a struct."""
        namespace_prefix = self._get_namespace_prefix()
        struct_name = f"{namespace_prefix}{struct.name}" if namespace_prefix else struct.name
        trait_name = f"{namespace_prefix}Serialize" if namespace_prefix else "PicoMsgSerialize"
        result_type = f"{namespace_prefix}Result" if namespace_prefix else "PicoMsgResult"
        
        lines = [
            f"impl {trait_name} for {struct_name} {{",
            f"    fn from_bytes(data: &[u8]) -> {result_type}<Self> {{",
            "        let mut cursor = std::io::Cursor::new(data);",
            "        Self::from_reader(&mut cursor)",
            "    }",
            "",
            f"    fn to_bytes(&self) -> {result_type}<Vec<u8>> {{",
            "        let mut buffer = Vec::new();",
            "        self.to_writer(&mut buffer)?;",
            "        Ok(buffer)",
            "    }",
            "",
            f"    fn from_reader<R: Read>(reader: &mut R) -> {result_type}<Self> {{",
        ]
        
        # Generate deserialization code
        lines.append("        Ok(Self {")
        for field in struct.fields:
            lines.extend(self._generate_field_read(field, "            "))
        lines.extend([
            "        })",
            "    }",
            "",
            f"    fn to_writer<W: Write>(&self, writer: &mut W) -> {result_type}<()> {{",
        ])
        
        # Generate serialization code
        for field in struct.fields:
            lines.extend(self._generate_field_write(field, "        "))
        
        lines.extend([
            "        Ok(())",
            "    }",
            "}",
        ])
        
        return lines
    
    def _generate_message_impl(self, message: Message) -> List[str]:
        """Generate implementation for a message."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name}" if namespace_prefix else message.name
        trait_name = f"{namespace_prefix}Serialize" if namespace_prefix else "PicoMsgSerialize"
        result_type = f"{namespace_prefix}Result" if namespace_prefix else "PicoMsgResult"
        
        lines = [
            f"impl {trait_name} for {message_name} {{",
            f"    fn from_bytes(data: &[u8]) -> {result_type}<Self> {{",
            "        let mut cursor = std::io::Cursor::new(data);",
            "        Self::from_reader(&mut cursor)",
            "    }",
            "",
            f"    fn to_bytes(&self) -> {result_type}<Vec<u8>> {{",
            "        let mut buffer = Vec::new();",
            "        self.to_writer(&mut buffer)?;",
            "        Ok(buffer)",
            "    }",
            "",
            f"    fn from_reader<R: Read>(reader: &mut R) -> {result_type}<Self> {{",
        ]
        
        # Generate deserialization code
        lines.append("        Ok(Self {")
        for field in message.fields:
            lines.extend(self._generate_field_read(field, "            "))
        lines.extend([
            "        })",
            "    }",
            "",
            f"    fn to_writer<W: Write>(&self, writer: &mut W) -> {result_type}<()> {{",
        ])
        
        # Generate serialization code
        for field in message.fields:
            lines.extend(self._generate_field_write(field, "        "))
        
        lines.extend([
            "        Ok(())",
            "    }",
            "}",
        ])
        
        return lines
    
    def _generate_field_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read a field from a reader."""
        if isinstance(field.type, PrimitiveType):
            return self._generate_primitive_read(field, indent)
        elif isinstance(field.type, StringType):
            return self._generate_string_read(field, indent)
        elif isinstance(field.type, BytesType):
            return self._generate_bytes_read(field, indent)
        elif isinstance(field.type, ArrayType):
            return self._generate_array_read(field, indent)
        elif isinstance(field.type, FixedArrayType):
            return self._generate_fixed_array_read(field, indent)
        elif isinstance(field.type, StructType):
            return self._generate_struct_read(field, indent)
        else:
            return [f"{indent}{field.name}: Default::default(), // TODO: Unsupported type"]
    
    def _generate_field_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write a field to a writer."""
        if isinstance(field.type, PrimitiveType):
            return self._generate_primitive_write(field, indent)
        elif isinstance(field.type, StringType):
            return self._generate_string_write(field, indent)
        elif isinstance(field.type, BytesType):
            return self._generate_bytes_write(field, indent)
        elif isinstance(field.type, ArrayType):
            return self._generate_array_write(field, indent)
        elif isinstance(field.type, FixedArrayType):
            return self._generate_fixed_array_write(field, indent)
        elif isinstance(field.type, StructType):
            return self._generate_struct_write(field, indent)
        else:
            return [f"{indent}// TODO: Unsupported type for field {field.name}"]
    
    def _generate_primitive_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read a primitive field."""
        type_name = field.type.name
        read_method = {
            'u8': 'read_u8()',
            'i8': 'read_i8()',
            'u16': 'read_u16::<LittleEndian>()',
            'i16': 'read_i16::<LittleEndian>()',
            'u32': 'read_u32::<LittleEndian>()',
            'i32': 'read_i32::<LittleEndian>()',
            'u64': 'read_u64::<LittleEndian>()',
            'i64': 'read_i64::<LittleEndian>()',
            'f32': 'read_f32::<LittleEndian>()',
            'f64': 'read_f64::<LittleEndian>()',
        }.get(type_name, 'read_u8()')
        
        return [f"{indent}{field.name}: reader.{read_method}?,"]
    
    def _generate_primitive_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write a primitive field."""
        type_name = field.type.name
        write_method = {
            'u8': 'write_u8',
            'i8': 'write_i8',
            'u16': 'write_u16::<LittleEndian>',
            'i16': 'write_i16::<LittleEndian>',
            'u32': 'write_u32::<LittleEndian>',
            'i32': 'write_i32::<LittleEndian>',
            'u64': 'write_u64::<LittleEndian>',
            'i64': 'write_i64::<LittleEndian>',
            'f32': 'write_f32::<LittleEndian>',
            'f64': 'write_f64::<LittleEndian>',
        }.get(type_name, 'write_u8')
        
        return [f"{indent}writer.{write_method}(self.{field.name})?;"]
    
    def _generate_string_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read a string field."""
        namespace_prefix = self._get_namespace_prefix()
        error_name = f"{namespace_prefix}Error" if namespace_prefix else "PicoMsgError"
        return [
            f"{indent}{field.name}: {{",
            f"{indent}    let len = reader.read_u16::<LittleEndian>()? as usize;",
            f"{indent}    let mut buf = vec![0u8; len];",
            f"{indent}    reader.read_exact(&mut buf)?;",
            f"{indent}    String::from_utf8(buf).map_err(|_| {error_name}::InvalidData)?",
            f"{indent}}},",
        ]
    
    def _generate_string_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write a string field."""
        return [
            f"{indent}writer.write_u16::<LittleEndian>(self.{field.name}.len() as u16)?;",
            f"{indent}writer.write_all(self.{field.name}.as_bytes())?;",
        ]
    
    def _generate_bytes_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read a bytes field."""
        return [
            f"{indent}{field.name}: {{",
            f"{indent}    let len = reader.read_u16::<LittleEndian>()? as usize;",
            f"{indent}    let mut buf = vec![0u8; len];",
            f"{indent}    reader.read_exact(&mut buf)?;",
            f"{indent}    buf",
            f"{indent}}},",
        ]
    
    def _generate_bytes_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write a bytes field."""
        return [
            f"{indent}writer.write_u16::<LittleEndian>(self.{field.name}.len() as u16)?;",
            f"{indent}writer.write_all(&self.{field.name})?;",
        ]
    
    def _generate_array_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read an array field."""
        element_type = self._get_rust_type(field.type.element_type)
        
        if isinstance(field.type.element_type, PrimitiveType):
            # For primitive arrays, we can read more efficiently
            return [
                f"{indent}{field.name}: {{",
                f"{indent}    let count = reader.read_u16::<LittleEndian>()? as usize;",
                f"{indent}    let mut vec = Vec::with_capacity(count);",
                f"{indent}    for _ in 0..count {{",
                f"{indent}        vec.push({self._get_primitive_read_expr(field.type.element_type)});",
                f"{indent}    }}",
                f"{indent}    vec",
                f"{indent}}},",
            ]
        else:
            # For complex types, use the trait
            return [
                f"{indent}{field.name}: {{",
                f"{indent}    let count = reader.read_u16::<LittleEndian>()? as usize;",
                f"{indent}    let mut vec = Vec::with_capacity(count);",
                f"{indent}    for _ in 0..count {{",
                f"{indent}        vec.push({element_type}::from_reader(reader)?);",
                f"{indent}    }}",
                f"{indent}    vec",
                f"{indent}}},",
            ]
    
    def _generate_array_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write an array field."""
        if isinstance(field.type.element_type, PrimitiveType):
            # For primitive arrays
            write_expr = self._get_primitive_write_expr(field.type.element_type, "item")
            return [
                f"{indent}writer.write_u16::<LittleEndian>(self.{field.name}.len() as u16)?;",
                f"{indent}for item in &self.{field.name} {{",
                f"{indent}    {write_expr}",
                f"{indent}}}",
            ]
        else:
            # For complex types
            return [
                f"{indent}writer.write_u16::<LittleEndian>(self.{field.name}.len() as u16)?;",
                f"{indent}for item in &self.{field.name} {{",
                f"{indent}    item.to_writer(writer)?;",
                f"{indent}}}",
            ]
    
    def _generate_fixed_array_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read a fixed array field."""
        if isinstance(field.type.element_type, PrimitiveType):
            # For primitive fixed arrays
            return [
                f"{indent}{field.name}: {{",
                f"{indent}    let mut arr = [{self._get_rust_type(field.type.element_type)}::default(); {field.type.size}];",
                f"{indent}    for i in 0..{field.type.size} {{",
                f"{indent}        arr[i] = {self._get_primitive_read_expr(field.type.element_type)};",
                f"{indent}    }}",
                f"{indent}    arr",
                f"{indent}}},",
            ]
        else:
            # For complex types, use Vec for now (Rust arrays with complex types are tricky)
            element_type = self._get_rust_type(field.type.element_type)
            return [
                f"{indent}{field.name}: {{",
                f"{indent}    let mut vec = Vec::with_capacity({field.type.size});",
                f"{indent}    for _ in 0..{field.type.size} {{",
                f"{indent}        vec.push({element_type}::from_reader(reader)?);",
                f"{indent}    }}",
                f"{indent}    vec",
                f"{indent}}},",
            ]
    
    def _generate_fixed_array_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write a fixed array field."""
        if isinstance(field.type.element_type, PrimitiveType):
            # For primitive fixed arrays
            write_expr = self._get_primitive_write_expr(field.type.element_type, "item")
            return [
                f"{indent}for item in &self.{field.name} {{",
                f"{indent}    {write_expr}",
                f"{indent}}}",
            ]
        else:
            # For complex types
            return [
                f"{indent}for item in &self.{field.name} {{",
                f"{indent}    item.to_writer(writer)?;",
                f"{indent}}}",
            ]
    
    def _generate_struct_read(self, field: Field, indent: str) -> List[str]:
        """Generate code to read a struct field."""
        namespace_prefix = self._get_namespace_prefix()
        struct_type = f"{namespace_prefix}{field.type.name}" if namespace_prefix else field.type.name
        
        return [f"{indent}{field.name}: {struct_type}::from_reader(reader)?,"]
    
    def _generate_struct_write(self, field: Field, indent: str) -> List[str]:
        """Generate code to write a struct field."""
        return [f"{indent}self.{field.name}.to_writer(writer)?;"]
    
    def _get_primitive_read_expr(self, prim_type: PrimitiveType) -> str:
        """Get the read expression for a primitive type."""
        type_name = prim_type.name
        read_method = {
            'u8': 'reader.read_u8()?',
            'i8': 'reader.read_i8()?',
            'u16': 'reader.read_u16::<LittleEndian>()?',
            'i16': 'reader.read_i16::<LittleEndian>()?',
            'u32': 'reader.read_u32::<LittleEndian>()?',
            'i32': 'reader.read_i32::<LittleEndian>()?',
            'u64': 'reader.read_u64::<LittleEndian>()?',
            'i64': 'reader.read_i64::<LittleEndian>()?',
            'f32': 'reader.read_f32::<LittleEndian>()?',
            'f64': 'reader.read_f64::<LittleEndian>()?',
        }
        return read_method.get(type_name, 'reader.read_u8()?')
    
    def _get_primitive_write_expr(self, prim_type: PrimitiveType, var_name: str) -> str:
        """Get the write expression for a primitive type."""
        type_name = prim_type.name
        write_method = {
            'u8': f'writer.write_u8(*{var_name})?;',
            'i8': f'writer.write_i8(*{var_name})?;',
            'u16': f'writer.write_u16::<LittleEndian>(*{var_name})?;',
            'i16': f'writer.write_i16::<LittleEndian>(*{var_name})?;',
            'u32': f'writer.write_u32::<LittleEndian>(*{var_name})?;',
            'i32': f'writer.write_i32::<LittleEndian>(*{var_name})?;',
            'u64': f'writer.write_u64::<LittleEndian>(*{var_name})?;',
            'i64': f'writer.write_i64::<LittleEndian>(*{var_name})?;',
            'f32': f'writer.write_f32::<LittleEndian>(*{var_name})?;',
            'f64': f'writer.write_f64::<LittleEndian>(*{var_name})?;',
        }
        return write_method.get(type_name, f'writer.write_u8(*{var_name})?;')
    
    def _get_rust_type(self, type_: Type) -> str:
        """Convert PicoMsg type to Rust type."""
        if isinstance(type_, PrimitiveType):
            return type_.name
        elif isinstance(type_, StringType):
            return "String"
        elif isinstance(type_, BytesType):
            return "Vec<u8>"
        elif isinstance(type_, ArrayType):
            element_type = self._get_rust_type(type_.element_type)
            return f"Vec<{element_type}>"
        elif isinstance(type_, FixedArrayType):
            element_type = self._get_rust_type(type_.element_type)
            if isinstance(type_.element_type, PrimitiveType):
                return f"[{element_type}; {type_.size}]"
            else:
                # For complex types, use Vec for now (Rust arrays with complex types are tricky)
                return f"Vec<{element_type}>"
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            return f"{namespace_prefix}{type_.name}" if namespace_prefix else type_.name
        else:
            return "String"  # Fallback
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize an identifier for Rust."""
        # Rust keywords that need to be escaped
        rust_keywords = {
            'as', 'break', 'const', 'continue', 'crate', 'else', 'enum', 'extern',
            'false', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop', 'match',
            'mod', 'move', 'mut', 'pub', 'ref', 'return', 'self', 'Self',
            'static', 'struct', 'super', 'trait', 'true', 'type', 'unsafe',
            'use', 'where', 'while', 'async', 'await', 'dyn'
        }
        
        if name in rust_keywords:
            return f"r#{name}"
        return name
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for generated identifiers."""
        if self.schema.namespace:
            # Convert to PascalCase for Rust types
            parts = self.schema.namespace.name.replace('.', '_').split('_')
            return ''.join(word.capitalize() for word in parts)
        return '' 
