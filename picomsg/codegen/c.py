"""
C code generator for PicoMsg.
"""

from typing import Dict, List, Tuple
from ..schema.ast import (
    Schema, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
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
        structs_only = self.get_option('structs_only', False)
        
        files = {}
        files[f"{header_name}.h"] = self._generate_header()
        
        # Only generate implementation file if not structs_only mode
        if not structs_only:
            files[f"{header_name}.c"] = self._generate_implementation()
        
        return files
    
    def _generate_header(self) -> str:
        """Generate C header file."""
        header_name = self.get_option('header_name', 'picomsg_generated')
        structs_only = self.get_option('structs_only', False)
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
        
        # Generate type definitions only if not structs_only mode
        if not structs_only:
            lines.extend(self._generate_type_definitions())
            lines.append("")
        
        # Generate enum definitions
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
        
        # Generate function declarations only if not structs_only mode
        if not structs_only:
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
        schema_version = self.schema.version if self.schema.version is not None else 1
        
        lines = [
            "// PicoMsg format constants",
            f"#define {namespace_prefix.upper()}MAGIC_BYTE_1 0xAB",
            f"#define {namespace_prefix.upper()}MAGIC_BYTE_2 0xCD",
            f"#define {namespace_prefix.upper()}VERSION {schema_version}",
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
    
    def _generate_enum_definition(self, enum) -> List[str]:
        """Generate C enum definition."""
        from ..schema.ast import Enum
        namespace_prefix = self._get_namespace_prefix()
        enum_name = f"{namespace_prefix}{enum.name.lower()}_t"
        
        # Get the backing type
        backing_type_map = {
            'u8': 'uint8_t', 'u16': 'uint16_t', 'u32': 'uint32_t', 'u64': 'uint64_t',
            'i8': 'int8_t', 'i16': 'int16_t', 'i32': 'int32_t', 'i64': 'int64_t'
        }
        backing_type = backing_type_map.get(enum.backing_type.name, 'int')
        
        lines = [
            f"// Enum: {enum.name}",
            f"typedef enum {{",
        ]
        
        # Generate enum values
        for value in enum.values:
            lines.append(f"    {namespace_prefix.upper()}{enum.name.upper()}_{value.name.upper()} = {value.value},")
        
        lines.extend([
            f"}} {enum_name};",
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
            if isinstance(field.type, FixedArrayType):
                element_type = self._get_c_type(field.type.element_type)
                lines.append(f"    {element_type} {field.name}[{field.type.size}];")
            elif isinstance(field.type, (ArrayType, StringType, BytesType)):
                # Variable-length types need pointer + length
                element_type = self._get_c_type(field.type.element_type) if isinstance(field.type, ArrayType) else "uint8_t"
                lines.append(f"    {element_type}* {field.name};")
                lines.append(f"    uint16_t {field.name}_len;")
            else:
                c_type = self._get_c_type(field.type)
                lines.append(f"    {c_type} {field.name};")

        lines.append(f"}} {struct_name};")

        # Generate initialization macro with defaults
        lines.extend(self._generate_init_macro(struct.name, struct.fields))

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
            if isinstance(field.type, FixedArrayType):
                element_type = self._get_c_type(field.type.element_type)
                lines.append(f"    {element_type} {field.name}[{field.type.size}];")
            elif isinstance(field.type, (ArrayType, StringType, BytesType)):
                # Variable-length types need pointer + length
                element_type = self._get_c_type(field.type.element_type) if isinstance(field.type, ArrayType) else "uint8_t"
                lines.append(f"    {element_type}* {field.name};")
                lines.append(f"    uint16_t {field.name}_len;")
            else:
                c_type = self._get_c_type(field.type)
                lines.append(f"    {c_type} {field.name};")

        lines.append(f"}} {message_name};")

        # Generate initialization macro with defaults
        lines.extend(self._generate_init_macro(message.name, message.fields))

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

        # Check if struct has variable-length fields
        has_varlen = any(isinstance(f.type, (ArrayType, StringType, BytesType)) for f in struct.fields)

        if not has_varlen:
            # Simple memcpy for fixed-size structs
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
        else:
            # Complex serialization for variable-length fields
            lines = [
                f"// {struct.name} serialization functions",
                f"{namespace_prefix}error_t {func_prefix}_from_bytes(",
                f"    const uint8_t* data, size_t len, {struct_name}* out) {{",
                f"    if (!data || !out) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
                f"    size_t offset = 0;",
                f"",
            ]

            # Generate deserialization for each field
            for field in struct.fields:
                lines.extend(self._generate_field_deserialize(field, namespace_prefix))

            lines.extend([
                f"    return {namespace_prefix.upper()}OK;",
                f"}}",
                f"",
                f"{namespace_prefix}error_t {func_prefix}_to_bytes(",
                f"    const {struct_name}* msg, uint8_t* buf, size_t* len) {{",
                f"    if (!msg || !buf || !len) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
                f"    size_t offset = 0;",
                f"",
            ])

            # Generate serialization for each field
            for field in struct.fields:
                lines.extend(self._generate_field_serialize(field, namespace_prefix))

            lines.extend([
                f"    *len = offset;",
                f"    return {namespace_prefix.upper()}OK;",
                f"}}",
            ])

        return lines
    
    def _generate_message_functions(self, message: Message) -> List[str]:
        """Generate serialization functions for a message."""
        namespace_prefix = self._get_namespace_prefix()
        message_name = f"{namespace_prefix}{message.name.lower()}_t"
        func_prefix = f"{namespace_prefix}{message.name.lower()}"

        # Check if message has variable-length fields
        has_varlen = any(isinstance(f.type, (ArrayType, StringType, BytesType)) for f in message.fields)

        if not has_varlen:
            # Simple memcpy for fixed-size messages
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
        else:
            # Complex serialization for variable-length fields
            lines = [
                f"// {message.name} serialization functions",
                f"{namespace_prefix}error_t {func_prefix}_from_bytes(",
                f"    const uint8_t* data, size_t len, {message_name}* out) {{",
                f"    if (!data || !out) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
                f"    size_t offset = 0;",
                f"",
            ]

            # Generate deserialization for each field
            for field in message.fields:
                lines.extend(self._generate_field_deserialize(field, namespace_prefix))

            lines.extend([
                f"    return {namespace_prefix.upper()}OK;",
                f"}}",
                f"",
                f"{namespace_prefix}error_t {func_prefix}_to_bytes(",
                f"    const {message_name}* msg, uint8_t* buf, size_t* len) {{",
                f"    if (!msg || !buf || !len) return {namespace_prefix.upper()}ERROR_NULL_POINTER;",
                f"    size_t offset = 0;",
                f"",
            ])

            # Generate serialization for each field
            for field in message.fields:
                lines.extend(self._generate_field_serialize(field, namespace_prefix))

            lines.extend([
                f"    *len = offset;",
                f"    return {namespace_prefix.upper()}OK;",
                f"}}",
            ])

        return lines
    
    def _generate_field_deserialize(self, field: Field, namespace_prefix: str) -> List[str]:
        """Generate deserialization code for a single field."""
        lines = []

        if isinstance(field.type, (ArrayType, StringType, BytesType)):
            # Variable-length field: read u16 length, then data
            element_type = self._get_c_type(field.type.element_type) if isinstance(field.type, ArrayType) else "uint8_t"
            element_size = self._get_type_size(field.type.element_type if isinstance(field.type, ArrayType) else PrimitiveType("u8"))

            lines.extend([
                f"    // Field: {field.name} (variable-length)",
                f"    if (offset + 2 > len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    out->{field.name}_len = data[offset] | (data[offset + 1] << 8);",
                f"    offset += 2;",
                f"    if (offset + out->{field.name}_len * {element_size} > len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    out->{field.name} = ({element_type}*)(data + offset);",
                f"    offset += out->{field.name}_len * {element_size};",
                f"",
            ])
        elif isinstance(field.type, FixedArrayType):
            # Fixed array
            element_size = self._get_type_size(field.type.element_type)
            total_size = element_size * field.type.size
            lines.extend([
                f"    // Field: {field.name} (fixed array)",
                f"    if (offset + {total_size} > len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    memcpy(out->{field.name}, data + offset, {total_size});",
                f"    offset += {total_size};",
                f"",
            ])
        else:
            # Primitive field
            size = self._get_type_size(field.type)
            lines.extend([
                f"    // Field: {field.name}",
                f"    if (offset + {size} > len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    memcpy(&out->{field.name}, data + offset, {size});",
                f"    offset += {size};",
                f"",
            ])

        return lines

    def _generate_field_serialize(self, field: Field, namespace_prefix: str) -> List[str]:
        """Generate serialization code for a single field."""
        lines = []

        if isinstance(field.type, (ArrayType, StringType, BytesType)):
            # Variable-length field: write u16 length, then data
            element_size = self._get_type_size(field.type.element_type if isinstance(field.type, ArrayType) else PrimitiveType("u8"))

            lines.extend([
                f"    // Field: {field.name} (variable-length)",
                f"    if (offset + 2 + msg->{field.name}_len * {element_size} > *len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    buf[offset] = msg->{field.name}_len & 0xFF;",
                f"    buf[offset + 1] = (msg->{field.name}_len >> 8) & 0xFF;",
                f"    offset += 2;",
                f"    memcpy(buf + offset, msg->{field.name}, msg->{field.name}_len * {element_size});",
                f"    offset += msg->{field.name}_len * {element_size};",
                f"",
            ])
        elif isinstance(field.type, FixedArrayType):
            # Fixed array
            element_size = self._get_type_size(field.type.element_type)
            total_size = element_size * field.type.size
            lines.extend([
                f"    // Field: {field.name} (fixed array)",
                f"    if (offset + {total_size} > *len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    memcpy(buf + offset, msg->{field.name}, {total_size});",
                f"    offset += {total_size};",
                f"",
            ])
        else:
            # Primitive field
            size = self._get_type_size(field.type)
            lines.extend([
                f"    // Field: {field.name}",
                f"    if (offset + {size} > *len) return {namespace_prefix.upper()}ERROR_BUFFER_TOO_SMALL;",
                f"    memcpy(buf + offset, &msg->{field.name}, {size});",
                f"    offset += {size};",
                f"",
            ])

        return lines

    def _get_type_size(self, type_: Type) -> int:
        """Get size of a type in bytes."""
        if isinstance(type_, PrimitiveType):
            type_sizes = {
                'u8': 1, 'i8': 1, 'bool': 1,
                'u16': 2, 'i16': 2,
                'u32': 4, 'i32': 4, 'f32': 4,
                'u64': 8, 'i64': 8, 'f64': 8,
            }
            return type_sizes.get(type_.name, 1)
        elif isinstance(type_, StructType):
            # For structs, we'd need to calculate the size - for now return 0 to indicate complex type
            return 0
        elif isinstance(type_, EnumType):
            # Enums use their backing type size
            return self._get_type_size(type_.backing_type) if hasattr(type_, 'backing_type') else 4
        else:
            return 1

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
                'bool': 'bool',
            }
            return type_map.get(type_.name, type_.name)
        
        elif isinstance(type_, StringType):
            return "uint16_t"  # Length prefix only for now
        
        elif isinstance(type_, BytesType):
            return "uint16_t"  # Length prefix only for now
        
        elif isinstance(type_, ArrayType):
            return "uint16_t"  # Count prefix only for now
        
        elif isinstance(type_, FixedArrayType):
            element_type = self._get_c_type(type_.element_type)
            # For fixed arrays, we need to handle the array syntax differently
            # Return just the element type, and handle the array size in field generation
            return element_type
        
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            return f"{namespace_prefix}{type_.name.lower()}_t"
        
        elif isinstance(type_, EnumType):
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
    
    def _generate_init_macro(self, type_name: str, fields: List[Field]) -> List[str]:
        """Generate initialization macro with default values."""
        namespace_prefix = self._get_namespace_prefix()
        macro_name = f"{namespace_prefix.upper()}{type_name.upper()}_INIT"
        type_name_c = f"{namespace_prefix}{type_name.lower()}_t"
        
        lines = [
            "",
            f"// Initialization macro for {type_name} with default values",
            f"#define {macro_name}(...) ({type_name_c}){{ \\",
        ]
        
        # Generate default values for each field
        defaults = []
        for field in fields:
            default_val = self._get_c_default_value(field)
            defaults.append(f"    .{field.name} = {default_val}")
        
        # Join defaults with commas and backslashes
        for i, default in enumerate(defaults):
            if i < len(defaults) - 1:
                lines.append(f"{default}, \\")
            else:
                lines.append(f"{default}, \\")
        
        lines.extend([
            "    __VA_ARGS__ \\",
            "}",
        ])
        
        return lines
    
    def _get_c_default_value(self, field: Field) -> str:
        """Get the C representation of a field's default value."""
        if field.default_value is None:
            # No default value specified
            if isinstance(field.type, StringType):
                return "NULL"
            elif isinstance(field.type, (ArrayType, BytesType)):
                return "NULL"  # Variable-length types default to NULL
            elif isinstance(field.type, FixedArrayType):
                return "{0}"  # Fixed arrays default to zero-initialized
            else:
                return "0"  # Primitive types default to 0
        
        # Convert default value to C representation
        if isinstance(field.default_value, bool):
            return "true" if field.default_value else "false"
        elif isinstance(field.default_value, str):
            # Escape string for C
            escaped = field.default_value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(field.default_value, (int, float)):
            return str(field.default_value)
        else:
            return "0"  # Fallback 
