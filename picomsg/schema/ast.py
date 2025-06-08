"""
Abstract Syntax Tree definitions for PicoMsg schema language.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from abc import ABC, abstractmethod


@dataclass
class Type(ABC):
    """Base class for all types in the schema."""
    
    @abstractmethod
    def size_bytes(self) -> Optional[int]:
        """Return the size in bytes if fixed-size, None if variable-size."""
        pass
    
    @abstractmethod
    def alignment(self) -> int:
        """Return the alignment requirement in bytes."""
        pass


@dataclass
class PrimitiveType(Type):
    """Primitive types like u8, u16, u32, u64, i8, i16, i32, i64, f32, f64."""
    name: str
    
    _SIZES = {
        'u8': 1, 'i8': 1,
        'u16': 2, 'i16': 2,
        'u32': 4, 'i32': 4,
        'u64': 8, 'i64': 8,
        'f32': 4, 'f64': 8,
        'bool': 1,
    }
    
    def size_bytes(self) -> Optional[int]:
        return self._SIZES.get(self.name)
    
    def alignment(self) -> int:
        size = self.size_bytes()
        return size if size else 1


@dataclass
class StringType(Type):
    """Variable-length string type."""
    
    def size_bytes(self) -> Optional[int]:
        return None  # Variable size
    
    def alignment(self) -> int:
        return 2  # u16 length prefix alignment


@dataclass
class BytesType(Type):
    """Variable-length bytes type."""
    
    def size_bytes(self) -> Optional[int]:
        return None  # Variable size
    
    def alignment(self) -> int:
        return 2  # u16 length prefix alignment


@dataclass
class ArrayType(Type):
    """Variable-length array type with element type."""
    element_type: Type
    
    def size_bytes(self) -> Optional[int]:
        return None  # Variable size
    
    def alignment(self) -> int:
        return max(2, self.element_type.alignment())  # u16 count prefix + element alignment


@dataclass
class FixedArrayType(Type):
    """Fixed-size array type with element type and size."""
    element_type: Type
    size: int
    
    def __post_init__(self):
        if self.size <= 0:
            raise ValueError(f"Fixed array size must be positive, got {self.size}")
        if self.size > 65535:
            raise ValueError(f"Fixed array size too large, maximum is 65535, got {self.size}")
    
    def size_bytes(self) -> Optional[int]:
        element_size = self.element_type.size_bytes()
        if element_size is None:
            return None  # Variable-size elements make the array variable-size
        return element_size * self.size
    
    def alignment(self) -> int:
        return self.element_type.alignment()  # No prefix, just element alignment


@dataclass
class UserType(Type):
    """Reference to a user-defined type (struct or enum)."""
    name: str
    
    def size_bytes(self) -> Optional[int]:
        return None  # Depends on actual type definition
    
    def alignment(self) -> int:
        return 1  # Default alignment, will be updated based on actual type


@dataclass
class StructType(Type):
    """Reference to a struct type."""
    name: str
    
    def size_bytes(self) -> Optional[int]:
        return None  # Depends on struct definition
    
    def alignment(self) -> int:
        return 4  # Default struct alignment


@dataclass
class EnumType(Type):
    """Reference to an enum type."""
    name: str
    
    def size_bytes(self) -> Optional[int]:
        return None  # Depends on enum definition
    
    def alignment(self) -> int:
        return 1  # Default to u8 alignment, will be updated based on backing type


@dataclass
class EnumValue:
    """A value in an enum definition."""
    name: str
    value: Optional[int] = None  # None means auto-increment
    
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"Invalid enum value name: {self.name}")
        if self.value is not None and (self.value < 0 or self.value > 4294967295):
            raise ValueError(f"Enum value out of range: {self.value}")


@dataclass
class Enum:
    """An enum definition."""
    name: str
    backing_type: PrimitiveType
    values: List[EnumValue]
    
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"Invalid enum name: {self.name}")
        
        # Validate backing type is an integer type
        if self.backing_type.name not in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
            raise ValueError(f"Enum backing type must be an integer type, got {self.backing_type.name}")
        
        # Check for duplicate value names
        value_names = [v.name for v in self.values]
        if len(value_names) != len(set(value_names)):
            raise ValueError(f"Duplicate enum value names in enum {self.name}")
        
        # Assign auto-increment values and validate ranges
        self._assign_values()
    
    def _assign_values(self):
        """Assign auto-increment values and validate ranges."""
        next_value = 0
        max_value = self._get_max_value()
        
        for value in self.values:
            if value.value is not None:
                if value.value > max_value:
                    raise ValueError(f"Enum value {value.value} exceeds maximum for type {self.backing_type.name}")
                next_value = value.value + 1
            else:
                if next_value > max_value:
                    raise ValueError(f"Auto-increment enum value {next_value} exceeds maximum for type {self.backing_type.name}")
                value.value = next_value
                next_value += 1
    
    def _get_max_value(self) -> int:
        """Get the maximum value for the backing type."""
        type_ranges = {
            'u8': 255, 'u16': 65535, 'u32': 4294967295, 'u64': 18446744073709551615,
            'i8': 127, 'i16': 32767, 'i32': 2147483647, 'i64': 9223372036854775807
        }
        return type_ranges[self.backing_type.name]
    
    def size_bytes(self) -> int:
        """Return the size of the enum (same as backing type)."""
        return self.backing_type.size_bytes()
    
    def alignment(self) -> int:
        """Return the alignment of the enum (same as backing type)."""
        return self.backing_type.alignment()


@dataclass
class Field:
    """A field in a struct or message."""
    name: str
    type: Type
    
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"Invalid field name: {self.name}")


@dataclass
class Struct:
    """A struct definition."""
    name: str
    fields: List[Field]
    
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"Invalid struct name: {self.name}")
        
        field_names = [f.name for f in self.fields]
        if len(field_names) != len(set(field_names)):
            raise ValueError(f"Duplicate field names in struct {self.name}")
    
    def size_bytes(self) -> Optional[int]:
        """Calculate struct size if all fields are fixed-size."""
        total_size = 0
        for field in self.fields:
            field_size = field.type.size_bytes()
            if field_size is None:
                return None  # Variable size
            total_size += field_size
        return total_size
    
    def alignment(self) -> int:
        """Calculate struct alignment requirement."""
        max_align = 1
        for field in self.fields:
            max_align = max(max_align, field.type.alignment())
        return max_align


@dataclass
class Message:
    """A message definition (same as struct but semantically different)."""
    name: str
    fields: List[Field]
    
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"Invalid message name: {self.name}")
        
        field_names = [f.name for f in self.fields]
        if len(field_names) != len(set(field_names)):
            raise ValueError(f"Duplicate field names in message {self.name}")
    
    def size_bytes(self) -> Optional[int]:
        """Calculate message size if all fields are fixed-size."""
        total_size = 0
        for field in self.fields:
            field_size = field.type.size_bytes()
            if field_size is None:
                return None  # Variable size
            total_size += field_size
        return total_size
    
    def alignment(self) -> int:
        """Calculate message alignment requirement."""
        max_align = 1
        for field in self.fields:
            max_align = max(max_align, field.type.alignment())
        return max_align


@dataclass
class Namespace:
    """A namespace declaration."""
    name: str
    
    def __post_init__(self):
        parts = self.name.split('.')
        for part in parts:
            if not part.isidentifier():
                raise ValueError(f"Invalid namespace part: {part}")


@dataclass
class Schema:
    """Complete schema with namespace, enums, structs, and messages."""
    namespace: Optional[Namespace]
    enums: List[Enum]
    structs: List[Struct]
    messages: List[Message]
    version: Optional[int] = None
    
    def __post_init__(self):
        # Check for duplicate enum names
        enum_names = [e.name for e in self.enums]
        if len(enum_names) != len(set(enum_names)):
            raise ValueError("Duplicate enum names in schema")
        
        # Check for duplicate struct names
        struct_names = [s.name for s in self.structs]
        if len(struct_names) != len(set(struct_names)):
            raise ValueError("Duplicate struct names in schema")
        
        # Check for duplicate message names
        message_names = [m.name for m in self.messages]
        if len(message_names) != len(set(message_names)):
            raise ValueError("Duplicate message names in schema")
        
        # Check for conflicts between all type names
        all_names = enum_names + struct_names + message_names
        if len(all_names) != len(set(all_names)):
            raise ValueError("Conflicting enum, struct, and message names in schema")
        
        # Validate version if provided
        if self.version is not None and (self.version < 1 or self.version > 255):
            raise ValueError("Schema version must be between 1 and 255")
    
    def get_enum(self, name: str) -> Optional[Enum]:
        """Get an enum by name."""
        for enum in self.enums:
            if enum.name == name:
                return enum
        return None
    
    def get_struct(self, name: str) -> Optional[Struct]:
        """Get a struct by name."""
        for struct in self.structs:
            if struct.name == name:
                return struct
        return None
    
    def get_message(self, name: str) -> Optional[Message]:
        """Get a message by name."""
        for message in self.messages:
            if message.name == name:
                return message
        return None
    
    def get_type_by_name(self, name: str) -> Optional[Union[Enum, Struct, Message]]:
        """Get an enum, struct, or message by name."""
        result = self.get_enum(name)
        if result:
            return result
        result = self.get_struct(name)
        if result:
            return result
        return self.get_message(name) 
