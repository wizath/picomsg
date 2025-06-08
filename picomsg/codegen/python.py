"""
Python code generator for PicoMsg.
"""

from typing import Dict, List
from ..schema.ast import (
    Schema, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, StructType
)
from .base import CodeGenerator


class PythonCodeGenerator(CodeGenerator):
    """Generate Python code from PicoMsg schema."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
        self.type_id_counter = 1  # Start from 1, 0 reserved for invalid
    
    def generate(self) -> Dict[str, str]:
        """Generate Python module file."""
        module_name = self.get_option('module_name', 'picomsg_generated')
        
        files = {}
        files[f"{module_name}.py"] = self._generate_module()
        
        return files
    
    def _generate_module(self) -> str:
        """Generate Python module file."""
        lines = [
            '"""Generated PicoMsg Python bindings"""',
            '# This file is auto-generated. Do not edit manually.',
            '',
            'import struct',
            'import json',
            'from typing import Dict, Any, Optional, Union, List',
            'from io import BytesIO',
            '',
        ]
        
        # Generate constants
        lines.extend(self._generate_constants())
        lines.append('')
        
        # Generate error classes
        lines.extend(self._generate_error_classes())
        lines.append('')
        
        # Generate base class
        lines.extend(self._generate_base_class())
        lines.append('')
        
        # Generate struct classes
        for struct in self.schema.structs:
            lines.extend(self._generate_struct_class(struct))
            lines.append('')
        
        # Generate message classes
        for message in self.schema.messages:
            lines.extend(self._generate_message_class(message))
            lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_constants(self) -> List[str]:
        """Generate constants and type IDs."""
        namespace_prefix = self._get_namespace_prefix()
        const_prefix = namespace_prefix.upper() + '_' if namespace_prefix else ''
        schema_version = self.schema.version if self.schema.version is not None else 1
        
        lines = [
            '# PicoMsg format constants',
            f'{const_prefix}MAGIC_BYTE_1 = 0xAB',
            f'{const_prefix}MAGIC_BYTE_2 = 0xCD',
            f'{const_prefix}VERSION = {schema_version}',
            f'{const_prefix}HEADER_SIZE = 8',
            '',
            '# Message type IDs',
        ]
        
        # Generate message type IDs
        for message in self.schema.messages:
            type_id = self.type_id_counter
            self.type_id_counter += 1
            lines.append(f'{const_prefix}{message.name.upper()}_TYPE_ID = {type_id}')
        
        return lines
    
    def _generate_error_classes(self) -> List[str]:
        """Generate error classes."""
        namespace_prefix = self._get_namespace_prefix()
        error_name = f'{namespace_prefix}Error' if namespace_prefix else 'PicoMsgError'
        
        lines = [
            '# Error classes',
            f'class {error_name}(Exception):',
            '    """Base exception for PicoMsg errors."""',
            '    pass',
            '',
            f'class {error_name}InvalidHeader({error_name}):',
            '    """Invalid header error."""',
            '    pass',
            '',
            f'class {error_name}BufferTooSmall({error_name}):',
            '    """Buffer too small error."""',
            '    pass',
            '',
            f'class {error_name}InvalidData({error_name}):',
            '    """Invalid data error."""',
            '    pass',
        ]
        
        return lines
    
    def _generate_base_class(self) -> List[str]:
        """Generate base class for all PicoMsg types."""
        namespace_prefix = self._get_namespace_prefix()
        base_name = f'{namespace_prefix}Base' if namespace_prefix else 'PicoMsgBase'
        error_name = f'{namespace_prefix}Error' if namespace_prefix else 'PicoMsgError'
        
        lines = [
            f'class {base_name}:',
            '    """Base class for all PicoMsg types."""',
            '    ',
            '    def __init__(self):',
            '        pass',
            '    ',
            '    @classmethod',
            '    def from_bytes(cls, data: bytes) -> "Self":',
            '        """Create instance from binary data."""',
            '        instance = cls()',
            '        instance._deserialize_from_bytes(data)',
            '        return instance',
            '    ',
            '    def to_bytes(self) -> bytes:',
            '        """Convert to binary data."""',
            '        return self._serialize_to_bytes()',
            '    ',
            '    def _serialize_to_bytes(self) -> bytes:',
            '        """Serialize instance to bytes with proper variable-length handling."""',
            '        buffer = BytesIO()',
            '        self._write_to_buffer(buffer)',
            '        return buffer.getvalue()',
            '    ',
            '    def _deserialize_from_bytes(self, data: bytes) -> None:',
            '        """Deserialize instance from bytes with proper variable-length handling."""',
            '        buffer = BytesIO(data)',
            '        self._read_from_buffer(buffer)',
            '    ',
            '    def _write_to_buffer(self, buffer: BytesIO) -> None:',
            '        """Write instance to buffer. Must be implemented by subclasses."""',
            '        raise NotImplementedError("Subclasses must implement _write_to_buffer")',
            '    ',
            '    def _read_from_buffer(self, buffer: BytesIO) -> None:',
            '        """Read instance from buffer. Must be implemented by subclasses."""',
            '        raise NotImplementedError("Subclasses must implement _read_from_buffer")',
            '    ',
            '    @classmethod',
            '    def from_buffer(cls, buffer: BytesIO) -> "Self":',
            '        """Create instance from buffer."""',
            '        instance = cls()',
            '        instance._read_from_buffer(buffer)',
            '        return instance',
            '    ',
            '    def to_buffer(self, buffer: BytesIO) -> None:',
            '        """Write to buffer."""',
            '        self._write_to_buffer(buffer)',
            '    ',
            '    def to_dict(self) -> Dict[str, Any]:',
            '        """Convert to dictionary for JSON serialization."""',
            '        raise NotImplementedError("Subclasses must implement to_dict")',
            '    ',
            '    @classmethod',
            '    def from_dict(cls, data: Dict[str, Any]) -> "Self":',
            '        """Create instance from dictionary."""',
            '        raise NotImplementedError("Subclasses must implement from_dict")',
            '    ',
            '    def to_json(self, indent: Optional[int] = None) -> str:',
            '        """Convert to JSON string."""',
            '        return json.dumps(self.to_dict(), indent=indent)',
            '    ',
            '    @classmethod',
            '    def from_json(cls, json_str: str) -> "Self":',
            '        """Create instance from JSON string."""',
            '        data = json.loads(json_str)',
            '        return cls.from_dict(data)',
        ]
        
        return lines
    
    def _generate_struct_class(self, struct: Struct) -> List[str]:
        """Generate Python class for a struct."""
        namespace_prefix = self._get_namespace_prefix()
        base_name = f'{namespace_prefix}Base' if namespace_prefix else 'PicoMsgBase'
        class_name = f'{namespace_prefix}{struct.name}' if namespace_prefix else struct.name
        
        lines = [
            f'class {class_name}({base_name}):',
            f'    """Struct: {struct.name}"""',
            '    ',
        ]
        
        # Generate constructor
        lines.extend(self._generate_struct_constructor(struct))
        lines.append('')
        
        # Generate properties
        for field in struct.fields:
            lines.extend(self._generate_field_property(field))
            lines.append('')
        
        # Generate serialization methods
        lines.extend(self._generate_serialization_methods(struct))
        lines.append('')
        
        # Generate to_dict method
        lines.extend(self._generate_struct_to_dict(struct))
        lines.append('')
        
        # Generate from_dict method
        lines.extend(self._generate_struct_from_dict(struct, class_name))
        
        return lines
    
    def _generate_message_class(self, message: Message) -> List[str]:
        """Generate Python class for a message."""
        namespace_prefix = self._get_namespace_prefix()
        base_name = f'{namespace_prefix}Base' if namespace_prefix else 'PicoMsgBase'
        class_name = f'{namespace_prefix}{message.name}' if namespace_prefix else message.name
        
        lines = [
            f'class {class_name}({base_name}):',
            f'    """Message: {message.name}"""',
            '    ',
        ]
        

        
        # Generate constructor
        lines.extend(self._generate_message_constructor(message))
        lines.append('')
        
        # Generate properties
        for field in message.fields:
            lines.extend(self._generate_field_property(field))
            lines.append('')
        
        # Generate serialization methods
        lines.extend(self._generate_serialization_methods(message))
        lines.append('')
        
        # Generate to_dict method
        lines.extend(self._generate_message_to_dict(message))
        lines.append('')
        
        # Generate from_dict method
        lines.extend(self._generate_message_from_dict(message, class_name))
        
        return lines
    

    
    def _generate_struct_constructor(self, struct: Struct) -> List[str]:
        """Generate constructor for struct."""
        lines = [
            '    def __init__(self, **kwargs):',
            '        super().__init__()',
            '        ',
            '        # Initialize fields with default values',
        ]
        
        # Set default values for each field
        for field in struct.fields:
            default_value = self._get_default_value(field.type)
            lines.append(f'        self._{field.name} = kwargs.get("{field.name}", {default_value})')
        
        return lines
    
    def _generate_message_constructor(self, message: Message) -> List[str]:
        """Generate constructor for message."""
        lines = [
            '    def __init__(self, **kwargs):',
            '        super().__init__()',
            '        ',
            '        # Initialize fields with default values',
        ]
        
        # Set default values for each field
        for field in message.fields:
            default_value = self._get_default_value(field.type)
            lines.append(f'        self._{field.name} = kwargs.get("{field.name}", {default_value})')
        
        return lines
    
    def _generate_field_property(self, field: Field) -> List[str]:
        """Generate simple property for direct attribute access."""
        default_value = self._get_default_value(field.type)
        
        return [
            f'    @property',
            f'    def {field.name}(self):',
            f'        """Get {field.name}."""',
            f'        return self._{field.name}',
            f'    ',
            f'    @{field.name}.setter',
            f'    def {field.name}(self, value):',
            f'        """Set {field.name}."""',
            f'        self._{field.name} = value',
        ]
    

    
    def _generate_serialization_methods(self, struct: Struct) -> List[str]:
        """Generate _write_to_buffer and _read_from_buffer methods."""
        lines = []
        
        # Generate _write_to_buffer method
        lines.extend([
            '    def _write_to_buffer(self, buffer: BytesIO) -> None:',
            '        """Write struct to buffer using struct module."""',
        ])
        
        for field in struct.fields:
            lines.extend(self._generate_field_write(field))
        
        lines.extend([
            '    ',
            '    def _read_from_buffer(self, buffer: BytesIO) -> None:',
            '        """Read struct from buffer using struct module."""',
        ])
        
        for field in struct.fields:
            lines.extend(self._generate_field_read(field))
        
        return lines
    
    def _generate_field_write(self, field: Field) -> List[str]:
        """Generate write code for a specific field."""
        if isinstance(field.type, PrimitiveType):
            return self._generate_primitive_write(field)
        elif isinstance(field.type, StringType):
            return self._generate_string_write(field)
        elif isinstance(field.type, BytesType):
            return self._generate_bytes_write(field)
        elif isinstance(field.type, ArrayType):
            return self._generate_array_write(field)
        elif isinstance(field.type, StructType):
            return self._generate_struct_write(field)
        else:
            return [f'        # TODO: Unsupported type for field {field.name}']
    
    def _generate_field_read(self, field: Field) -> List[str]:
        """Generate read code for a specific field."""
        if isinstance(field.type, PrimitiveType):
            return self._generate_primitive_read(field)
        elif isinstance(field.type, StringType):
            return self._generate_string_read(field)
        elif isinstance(field.type, BytesType):
            return self._generate_bytes_read(field)
        elif isinstance(field.type, ArrayType):
            return self._generate_array_read(field)
        elif isinstance(field.type, StructType):
            return self._generate_struct_read(field)
        else:
            return [f'        # TODO: Unsupported type for field {field.name}']
    
    def _generate_primitive_write(self, field: Field) -> List[str]:
        """Generate write code for primitive types."""
        format_char = self._get_struct_format(field.type)
        return [f'        buffer.write(struct.pack("<{format_char}", self._{field.name}))']
    
    def _generate_primitive_read(self, field: Field) -> List[str]:
        """Generate read code for primitive types."""
        format_char = self._get_struct_format(field.type)
        size = self._get_type_size(field.type)
        return [f'        self._{field.name} = struct.unpack("<{format_char}", buffer.read({size}))[0]']
    
    def _generate_string_write(self, field: Field) -> List[str]:
        """Generate write code for string types."""
        return [
            f'        # String field: [u16 length][UTF-8 bytes]',
            f'        data = self._{field.name}.encode("utf-8")',
            f'        buffer.write(struct.pack("<H", len(data)))',
            f'        buffer.write(data)',
        ]
    
    def _generate_string_read(self, field: Field) -> List[str]:
        """Generate read code for string types."""
        return [
            f'        # String field: [u16 length][UTF-8 bytes]',
            f'        length = struct.unpack("<H", buffer.read(2))[0]',
            f'        data = buffer.read(length)',
            f'        self._{field.name} = data.decode("utf-8")',
        ]
    
    def _generate_bytes_write(self, field: Field) -> List[str]:
        """Generate write code for bytes types."""
        return [
            f'        # Bytes field: [u16 length][raw bytes]',
            f'        buffer.write(struct.pack("<H", len(self._{field.name})))',
            f'        buffer.write(self._{field.name})',
        ]
    
    def _generate_bytes_read(self, field: Field) -> List[str]:
        """Generate read code for bytes types."""
        return [
            f'        # Bytes field: [u16 length][raw bytes]',
            f'        length = struct.unpack("<H", buffer.read(2))[0]',
            f'        self._{field.name} = buffer.read(length)',
        ]
    
    def _generate_array_write(self, field: Field) -> List[str]:
        """Generate write code for array types."""
        lines = [
            f'        # Array field: [u16 count][elements]',
            f'        buffer.write(struct.pack("<H", len(self._{field.name})))',
        ]
        
        if isinstance(field.type.element_type, PrimitiveType):
            format_char = self._get_struct_format(field.type.element_type)
            lines.extend([
                f'        for item in self._{field.name}:',
                f'            buffer.write(struct.pack("<{format_char}", item))',
            ])
        elif isinstance(field.type.element_type, StringType):
            lines.extend([
                f'        for item in self._{field.name}:',
                f'            data = item.encode("utf-8")',
                f'            buffer.write(struct.pack("<H", len(data)))',
                f'            buffer.write(data)',
            ])
        elif isinstance(field.type.element_type, BytesType):
            lines.extend([
                f'        for item in self._{field.name}:',
                f'            buffer.write(struct.pack("<H", len(item)))',
                f'            buffer.write(item)',
            ])
        elif isinstance(field.type.element_type, StructType):
            lines.extend([
                f'        for item in self._{field.name}:',
                f'            item._write_to_buffer(buffer)',
            ])
        elif isinstance(field.type.element_type, ArrayType):
            lines.extend([
                f'        for item in self._{field.name}:',
                f'            # Nested array: write count then elements',
                f'            buffer.write(struct.pack("<H", len(item)))',
            ])
            # Handle the nested array elements
            if isinstance(field.type.element_type.element_type, PrimitiveType):
                format_char = self._get_struct_format(field.type.element_type.element_type)
                lines.extend([
                    f'            for nested_item in item:',
                    f'                buffer.write(struct.pack("<{format_char}", nested_item))',
                ])
            elif isinstance(field.type.element_type.element_type, StringType):
                lines.extend([
                    f'            for nested_item in item:',
                    f'                data = nested_item.encode("utf-8")',
                    f'                buffer.write(struct.pack("<H", len(data)))',
                    f'                buffer.write(data)',
                ])
            elif isinstance(field.type.element_type.element_type, ArrayType):
                # 3D array: [[[type]]]
                lines.extend([
                    f'            for nested_array in item:',
                    f'                buffer.write(struct.pack("<H", len(nested_array)))',
                ])
                if isinstance(field.type.element_type.element_type.element_type, PrimitiveType):
                    format_char = self._get_struct_format(field.type.element_type.element_type.element_type)
                    lines.extend([
                        f'                for deep_item in nested_array:',
                        f'                    buffer.write(struct.pack("<{format_char}", deep_item))',
                    ])
                else:
                    lines.append(f'                # TODO: 4D+ arrays not yet supported')
            else:
                lines.append(f'            # TODO: Complex nested array elements not yet supported')
        else:
            lines.append(f'            # TODO: Unsupported array element type')
        
        return lines
    
    def _generate_array_read(self, field: Field) -> List[str]:
        """Generate read code for array types."""
        lines = [
            f'        # Array field: [u16 count][elements]',
            f'        count = struct.unpack("<H", buffer.read(2))[0]',
            f'        self._{field.name} = []',
            f'        for _ in range(count):',
        ]
        
        if isinstance(field.type.element_type, PrimitiveType):
            format_char = self._get_struct_format(field.type.element_type)
            size = self._get_type_size(field.type.element_type)
            lines.append(f'            item = struct.unpack("<{format_char}", buffer.read({size}))[0]')
        elif isinstance(field.type.element_type, StringType):
            lines.extend([
                f'            length = struct.unpack("<H", buffer.read(2))[0]',
                f'            data = buffer.read(length)',
                f'            item = data.decode("utf-8")',
            ])
        elif isinstance(field.type.element_type, BytesType):
            lines.extend([
                f'            length = struct.unpack("<H", buffer.read(2))[0]',
                f'            item = buffer.read(length)',
            ])
        elif isinstance(field.type.element_type, StructType):
            namespace_prefix = self._get_namespace_prefix()
            element_class = f'{namespace_prefix}{field.type.element_type.name}' if namespace_prefix else field.type.element_type.name
            lines.append(f'            item = {element_class}.from_buffer(buffer)')
        elif isinstance(field.type.element_type, ArrayType):
            lines.extend([
                f'            # Nested array: read count then elements',
                f'            nested_count = struct.unpack("<H", buffer.read(2))[0]',
                f'            item = []',
                f'            for _ in range(nested_count):',
            ])
            # Handle the nested array elements
            if isinstance(field.type.element_type.element_type, PrimitiveType):
                format_char = self._get_struct_format(field.type.element_type.element_type)
                size = self._get_type_size(field.type.element_type.element_type)
                lines.append(f'                nested_item = struct.unpack("<{format_char}", buffer.read({size}))[0]')
                lines.append(f'                item.append(nested_item)')
            elif isinstance(field.type.element_type.element_type, StringType):
                lines.extend([
                    f'                length = struct.unpack("<H", buffer.read(2))[0]',
                    f'                data = buffer.read(length)',
                    f'                nested_item = data.decode("utf-8")',
                    f'                item.append(nested_item)',
                ])
            elif isinstance(field.type.element_type.element_type, ArrayType):
                # 3D array: [[[type]]]
                lines.extend([
                    f'                deep_count = struct.unpack("<H", buffer.read(2))[0]',
                    f'                nested_array = []',
                    f'                for _ in range(deep_count):',
                ])
                if isinstance(field.type.element_type.element_type.element_type, PrimitiveType):
                    format_char = self._get_struct_format(field.type.element_type.element_type.element_type)
                    size = self._get_type_size(field.type.element_type.element_type.element_type)
                    lines.extend([
                        f'                    deep_item = struct.unpack("<{format_char}", buffer.read({size}))[0]',
                        f'                    nested_array.append(deep_item)',
                    ])
                else:
                    lines.extend([
                        f'                    # TODO: 4D+ arrays not yet supported',
                        f'                    nested_array.append(None)',
                    ])
                lines.append(f'                item.append(nested_array)')
            else:
                lines.extend([
                    f'                # TODO: Complex nested array elements not yet supported',
                    f'                item.append(None)',
                ])
        else:
            lines.append(f'            # TODO: Unsupported array element type')
            lines.append(f'            item = None')
        
        lines.append(f'            self._{field.name}.append(item)')
        return lines
    
    def _generate_struct_write(self, field: Field) -> List[str]:
        """Generate write code for nested struct types."""
        return [f'        self._{field.name}._write_to_buffer(buffer)']
    
    def _generate_struct_read(self, field: Field) -> List[str]:
        """Generate read code for nested struct types."""
        namespace_prefix = self._get_namespace_prefix()
        struct_class = f'{namespace_prefix}{field.type.name}' if namespace_prefix else field.type.name
        return [f'        self._{field.name} = {struct_class}.from_buffer(buffer)']
    
    def _get_struct_format(self, type_: Type) -> str:
        """Get struct module format character for a primitive type."""
        if isinstance(type_, PrimitiveType):
            format_map = {
                'u8': 'B', 'i8': 'b',
                'u16': 'H', 'i16': 'h', 
                'u32': 'I', 'i32': 'i',
                'u64': 'Q', 'i64': 'q',
                'f32': 'f', 'f64': 'd',
            }
            return format_map.get(type_.name, 'B')
        return 'B'
    
    def _generate_struct_to_dict(self, struct: Struct) -> List[str]:
        """Generate to_dict method for struct."""
        lines = [
            '    def to_dict(self) -> Dict[str, Any]:',
            '        """Convert to dictionary."""',
            '        return {',
        ]
        
        for field in struct.fields:
            if isinstance(field.type, StructType):
                # For struct fields, call their to_dict method
                lines.append(f'            "{field.name}": self.{field.name}.to_dict(),')
            else:
                lines.append(f'            "{field.name}": self.{field.name},')
        
        lines.extend([
            '        }',
        ])
        
        return lines
    
    def _generate_struct_from_dict(self, struct: Struct, class_name: str) -> List[str]:
        """Generate from_dict method for struct."""
        lines = [
            '    @classmethod',
            '    def from_dict(cls, data: Dict[str, Any]) -> "Self":',
            '        """Create instance from dictionary."""',
            '        kwargs = {}',
        ]
        
        # Handle each field appropriately
        for field in struct.fields:
            if isinstance(field.type, StructType):
                # For struct fields, create instance from nested dict
                namespace_prefix = self._get_namespace_prefix()
                struct_class = f'{namespace_prefix}{field.type.name}' if namespace_prefix else field.type.name
                lines.extend([
                    f'        if "{field.name}" in data and data["{field.name}"] is not None:',
                    f'            kwargs["{field.name}"] = {struct_class}.from_dict(data["{field.name}"])',
                ])
            else:
                lines.append(f'        kwargs["{field.name}"] = data.get("{field.name}")')
        
        lines.extend([
            '        return cls(**kwargs)',
        ])
        
        return lines
    
    def _generate_message_to_dict(self, message: Message) -> List[str]:
        """Generate to_dict method for message."""
        return self._generate_struct_to_dict(message)
    
    def _generate_message_from_dict(self, message: Message, class_name: str) -> List[str]:
        """Generate from_dict method for message."""
        return self._generate_struct_from_dict(message, class_name)
    

    
    def _get_python_type_hint(self, type_: Type) -> str:
        """Get Python type hint for a PicoMsg type."""
        if isinstance(type_, PrimitiveType):
            if type_.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
                return 'int'
            elif type_.name in ['f32', 'f64']:
                return 'float'
        elif isinstance(type_, StringType):
            return 'str'
        elif isinstance(type_, BytesType):
            return 'bytes'
        elif isinstance(type_, ArrayType):
            element_hint = self._get_python_type_hint(type_.element_type)
            return f'List[{element_hint}]'
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            return f'{namespace_prefix}{type_.name}' if namespace_prefix else type_.name
        
        return 'Any'
    
    def _get_default_value(self, type_: Type) -> str:
        """Get default value for a type."""
        if isinstance(type_, PrimitiveType):
            if type_.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
                return '0'
            elif type_.name in ['f32', 'f64']:
                return '0.0'
        elif isinstance(type_, StringType):
            return '""'
        elif isinstance(type_, BytesType):
            return 'b""'
        elif isinstance(type_, ArrayType):
            return '[]'
        elif isinstance(type_, StructType):
            namespace_prefix = self._get_namespace_prefix()
            struct_name = f'{namespace_prefix}{type_.name}' if namespace_prefix else type_.name
            return f'{struct_name}()'
        
        return 'None'
    

    
    def _get_type_size(self, type_: Type) -> int:
        """Get size of a type in bytes."""
        if isinstance(type_, PrimitiveType):
            size_map = {
                'u8': 1, 'i8': 1,
                'u16': 2, 'i16': 2,
                'u32': 4, 'i32': 4, 'f32': 4,
                'u64': 8, 'i64': 8, 'f64': 8,
            }
            return size_map.get(type_.name, 1)
        elif isinstance(type_, (StringType, BytesType, ArrayType)):
            # Variable-length types use a length/count prefix
            return 2  # u16 prefix
        elif isinstance(type_, StructType):
            # For struct references, calculate the actual struct size
            for struct in self.schema.structs:
                if struct.name == type_.name:
                    return self._calculate_struct_size(struct)
            # If not found in structs, check messages
            for message in self.schema.messages:
                if message.name == type_.name:
                    return self._calculate_struct_size(message)
            # Fallback if not found
            return 4
        else:
            return 1
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize identifier for Python."""
        # Replace invalid characters and handle Python keywords
        import keyword
        
        # Replace invalid characters
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        # Handle Python keywords
        if keyword.iskeyword(sanitized):
            sanitized += '_'
        
        return sanitized or '_'
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for generated identifiers."""
        if self.schema.namespace:
            parts = self.schema.namespace.name.split('.')
            # Convert to PascalCase for Python classes
            return ''.join(part.capitalize() for part in parts)
        return '' 
