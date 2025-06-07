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
    """Array type with element type."""
    element_type: Type
    
    def size_bytes(self) -> Optional[int]:
        return None  # Variable size
    
    def alignment(self) -> int:
        return max(2, self.element_type.alignment())  # u16 count prefix + element alignment


@dataclass
class StructType(Type):
    """Reference to a struct type."""
    name: str
    
    def size_bytes(self) -> Optional[int]:
        return None  # Depends on struct definition
    
    def alignment(self) -> int:
        return 4  # Default struct alignment


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
    """Complete schema with namespace, structs, and messages."""
    namespace: Optional[Namespace]
    structs: List[Struct]
    messages: List[Message]
    
    def __post_init__(self):
        # Check for duplicate struct names
        struct_names = [s.name for s in self.structs]
        if len(struct_names) != len(set(struct_names)):
            raise ValueError("Duplicate struct names in schema")
        
        # Check for duplicate message names
        message_names = [m.name for m in self.messages]
        if len(message_names) != len(set(message_names)):
            raise ValueError("Duplicate message names in schema")
        
        # Check for conflicts between struct and message names
        all_names = struct_names + message_names
        if len(all_names) != len(set(all_names)):
            raise ValueError("Conflicting struct and message names in schema")
    
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
    
    def get_type_by_name(self, name: str) -> Optional[Union[Struct, Message]]:
        """Get a struct or message by name."""
        result = self.get_struct(name)
        if result:
            return result
        return self.get_message(name) 
