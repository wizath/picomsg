"""
C code generator for PicoMsg.
"""

from typing import Dict, List, Tuple
from ..schema.ast import (
    Schema, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, StructType
)
from ..format.alignment import calculate_struct_layout, get_c_packed_attribute
from .base import CodeGenerator


class CCodeGenerator(CodeGenerator):
    """Generate C code from PicoMsg schema."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
        self.type_id_counter = 1  # Start from 1, 0 reserved for invalid
    
    def generate(self) -> Dict[str, str]:
        """Generate C header and implementation files."""
        header_name = self.get_option('header_name', 'picomsg_generated')
        
        files = {}
        files[f"{header_name}.h"] = self._generate_header()
        files[f"{header_name}.c"] = self._generate_implementation()
        
        return files
    
    def _generate_header(self) -> str:
        """Generate C header file."""
        header_name = self.get_option('header_name', 'picomsg_generated')
        guard_name = f"{header_name.upper()}_H"
        namespace_prefix = self._get_namespace_prefix()
        
        lines = [
            f"#ifndef {guard_name}",
            f"#define {guard_name}",
            "",
            "#include <stdint.h>",
            "#include <stddef.h>",
            "#include <stdbool.h>",
            "",
            "#ifdef __cplusplus",
            "extern \"C\" {",
            "#endif",
            "",
        ]
        
        # Generate type definitions
        lines.extend(self._generate_type_definitions())
        lines.append("")
        
        # Generate struct definitions
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_definition(struct))
            lines.append("")
        
        # Generate message definitions
        for message in self.schema.messages:
            lines.extend(self._generate_message_definition(message))
            lines.append("")
        
        # Generate function declarations
        lines.extend(self._generate_function_declarations())
        
        lines.extend([
            "",
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            f"#endif // {guard_name}",
        ])
        
        return "\n".join(lines)
    
    def _generate_implementation(self) -> str:
        """Generate C implementation file."""
        header_name = self.get_option('header_name', 'picomsg_generated')
        
        lines = [
            f"#include \"{header_name}.h\"",
            "#include <string.h>",
            "#include <assert.h>",
            "",
        ]
        
        # Generate serialization functions
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_functions(struct))
            lines.append("")
        
        for message in self.schema.messages:
            lines.extend(self._generate_message_functions(message))
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_type_definitions(self) -> List[str]:
        """Generate type definitions and constants."""
        namespace_prefix = self._get_namespace_prefix()
        
        lines = [
            "// PicoMsg format constants",
            f"#define {namespace_prefix.upper()}MAGIC_BYTE_1 0xAB",
            f"#define {namespace_prefix.upper()}MAGIC_BYTE_2 0xCD",
            f"#define {namespace_prefix.upper()}VERSION 1",
            f"#define {namespace_prefix.upper()}HEADER_SIZE 8",
            "",
            "// Message type IDs",
        ]
        
        # Generate message type IDs
        for message in self.schema.messages:
            type_id = self.type_id_counter
            self.type_id_counter += 1
            lines.append(f"#define {namespace_prefix.upper()}{message.name.upper()}_TYPE_ID {type_id}")
        
        lines.extend([
            "",
            "// Error codes",
            f"typedef enum {{",
            f"    {namespace_prefix.upper()}OK = 0,",
            f"    {namespace_prefix.upper()}ERROR_INVALID_HEADER,",
            f"    {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL,",
            f"    {namespace_prefix.upper()}ERROR_INVALID_DATA,",
            f"    {namespace_prefix.upper()}ERROR_NULL_POINTER",
            f"}} {namespace_prefix}error_t;",
        ])
        
        return lines
    
    def _generate_struct_definition(self, struct: Struct) -> List[str]:
        """Generate C struct definition."""
        namespace_prefix = self._get_namespace_prefix()
        struct_name = f"{namespace_prefix}{struct.name.lower()}_t"
        
        lines = [
            f"// Struct: {struct.name}",
            f"typedef struct {get_c_packed_attribute()} {{",
        ]
        
        # Generate fields
        for field in struct.fields:
            c_type = self._get_c_type(field.type)
            lines.append(f"    {c_type} {field.name};")
        
        lines.append(f"}} {struct_name};")
        
        return lines
    
    def _generate_message_definition(self, message: Message) -> List[str]:
        """Generate C message definition."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name.lower()}_t"
        
        lines = [
            f"// Message: {message.name}",
            f"typedef struct {get_c_packed_attribute()} {{",
        ]
        
        # Generate fields
        for field in message.fields:
            c_type = self._get_c_type(field.type)
            lines.append(f"    {c_type} {field.name};")
        
        lines.append(f"}} {message_name};")
        
        return lines
    
    def _generate_function_declarations(self) -> List[str]:
        """Generate function declarations."""
        namespace_prefix = self._get_namespace_prefix()
        lines = ["// Function declarations"]
        
        # Generate functions for structs
        for struct in self.schema.structs:
            struct_name = f"{namespace_prefix}{struct.name.lower()}_t"
            lines.extend([
                f"{namespace_prefix}error_t {namespace_prefix}{struct.name.lower()}_from_bytes(",
                f"    const uint8_t* data, size_t len, {struct_name}* out);",
                f"{namespace_prefix}error_t {namespace_prefix}{struct.name.lower()}_to_bytes(",
                f"    const {struct_name}* msg, uint8_t* buf, size_t* len);",
            ])
        
        # Generate functions for messages
        for message in self.schema.messages:
            message_name = f"{namespace_prefix}{message.name.lower()}_t"
            lines.extend([
                f"{namespace_prefix}error_t {namespace_prefix}{message.name.lower()}_from_bytes(",
                f"    const uint8_t* data, size_t len, {message_name}* out);",
                f"{namespace_prefix}error_t {namespace_prefix}{message.name.lower()}_to_bytes(",
                f"    const {message_name}* msg, uint8_t* buf, size_t* len);",
            ])
        
        return lines
    
    def _generate_struct_functions(self, struct: Struct) -> List[str]:
        """Generate serialization functions for a struct."""
        namespace_prefix = self._get_namespace_prefix()
        struct_name = f"{namespace_prefix}{struct.name.lower()}_t"
        func_prefix = f"{namespace_prefix}{struct.name.lower()}"
        
        lines = [
            f"// {struct.name} serialization functions",
            f"{namespace_prefix}error_t {func_prefix}_from_bytes(",
            f"    const uint8_t* data, size_t len, {struct_name}* out) {{",
            f"    if (!data || !out) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
            f"    if (len < sizeof({struct_name})) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
            f"    ",
            f"    memcpy(out, data, sizeof({struct_name}));",
            f"    return {namespace_prefix.upper()}OK;",
            f"}}",
            f"",
            f"{namespace_prefix}error_t {func_prefix}_to_bytes(",
            f"    const {struct_name}* msg, uint8_t* buf, size_t* len) {{",
            f"    if (!msg || !buf || !len) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
            f"    if (*len < sizeof({struct_name})) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
            f"    ",
            f"    memcpy(buf, msg, sizeof({struct_name}));",
            f"    *len = sizeof({struct_name});",
            f"    return {namespace_prefix.upper()}OK;",
            f"}}",
        ]
        
        return lines
    
    def _generate_message_functions(self, message: Message) -> List[str]:
        """Generate serialization functions for a message."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name.lower()}_t"
        func_prefix = f"{namespace_prefix}{message.name.lower()}"
        
        lines = [
            f"// {message.name} serialization functions",
            f"{namespace_prefix}error_t {func_prefix}_from_bytes(",
            f"    const uint8_t* data, size_t len, {message_name}* out) {{",
            f"    if (!data || !out) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
            f"    if (len < sizeof({message_name})) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
            f"    ",
            f"    memcpy(out, data, sizeof({message_name}));",
            f"    return {namespace_prefix.upper()}OK;",
            f"}}",
            f"",
            f"{namespace_prefix}error_t {func_prefix}_to_bytes(",
            f"    const {message_name}* msg, uint8_t* buf, size_t* len) {{",
            f"    if (!msg || !buf || !len) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
            f"    if (*len < sizeof({message_name})) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
            f"    ",
            f"    memcpy(buf, msg, sizeof({message_name}));",
            f"    *len = sizeof({message_name});",
            f"    return {namespace_prefix.upper()}OK;",
            f"}}",
        ]
        
        return lines
    
    def _get_c_type(self, type_: Type) -> str:
        """Convert PicoMsg type to C type."""
        if isinstance(type_, PrimitiveType):
            type_map = {
                'u8': 'uint8_t',
                'u16': 'uint16_t',
                'u32': 'uint32_t',
                'u64': 'uint64_t',
                'i8': 'int8_t',
                'i16': 'int16_t',
                'i32': 'int32_t',
                'i64': 'int64_t',
                'f32': 'float',
                'f64': 'double',
            }
            return type_map.get(type_.name, type_.name)
        
        elif isinstance(type_, StringType):
            return "uint16_t"  # Length prefix only for now
        
        elif isinstance(type_, BytesType):
            return "uint16_t"  # Length prefix only for now
        
        elif isinstance(type_, ArrayType):
            return "uint16_t"  # Count prefix only for now
        
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            return f"{namespace_prefix}{type_.name.lower()}_t"
        
        else:
            raise ValueError(f"Unknown type: {type_}")
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize identifier for C."""
        # Replace invalid characters with underscores
        result = ""
        for char in name:
            if char.isalnum() or char == '_':
                result += char
            else:
                result += '_'
        
        # Ensure it doesn't start with a digit
        if result and result[0].isdigit():
            result = '_' + result
        
        return result 
