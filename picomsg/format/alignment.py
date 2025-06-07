"""
Memory alignment utilities for PicoMsg binary format.
"""

from typing import List, Tuple
from ..schema.ast import Type, Field, Struct, Message, PrimitiveType, StringType, BytesType, ArrayType, StructType


def align_offset(offset: int, alignment: int) -> int:
    """Align an offset to the specified alignment boundary."""
    if alignment <= 1:
        return offset
    return (offset + alignment - 1) & ~(alignment - 1)


def calculate_padding(offset: int, alignment: int) -> int:
    """Calculate padding bytes needed to align offset."""
    aligned = align_offset(offset, alignment)
    return aligned - offset


def calculate_struct_layout(fields: List[Field], base_alignment: int = 4) -> Tuple[List[Tuple[str, int, int]], int]:
    """
    Calculate memory layout for struct fields.
    
    Returns:
        List of (field_name, offset, size) tuples and total struct size
    """
    layout = []
    current_offset = 0
    max_alignment = 1
    
    for field in fields:
        field_alignment = field.type.alignment()
        max_alignment = max(max_alignment, field_alignment)
        
        # Align current offset to field alignment
        current_offset = align_offset(current_offset, field_alignment)
        
        # Calculate field size
        field_size = _calculate_field_size(field.type)
        
        layout.append((field.name, current_offset, field_size))
        current_offset += field_size
    
    # For empty structs or structs with only zero-size fields, use base alignment
    if not fields or current_offset == 0:
        return layout, base_alignment
    
    # Align total struct size to maximum field alignment or base alignment
    struct_alignment = max(max_alignment, base_alignment)
    total_size = align_offset(current_offset, struct_alignment)
    
    return layout, total_size


def calculate_message_layout(message: Message) -> Tuple[List[Tuple[str, int, int]], int]:
    """Calculate memory layout for a message."""
    return calculate_struct_layout(message.fields)


def _calculate_field_size(type_: Type) -> int:
    """Calculate the size of a field type."""
    if isinstance(type_, PrimitiveType):
        size = type_.size_bytes()
        if size is None:
            raise ValueError(f"Unknown primitive type: {type_.name}")
        return size
    
    elif isinstance(type_, StringType):
        return 2  # u16 length prefix (actual string data is variable)
    
    elif isinstance(type_, BytesType):
        return 2  # u16 length prefix (actual bytes data is variable)
    
    elif isinstance(type_, ArrayType):
        return 2  # u16 count prefix (actual array data is variable)
    
    elif isinstance(type_, StructType):
        # For struct references, we need the actual struct definition
        # This is a placeholder - in practice, we'd need to resolve the reference
        return 0  # Will be resolved during code generation
    
    else:
        raise ValueError(f"Unknown type: {type_}")


def get_c_alignment_attribute(alignment: int) -> str:
    """Get the C alignment attribute string for the given alignment."""
    if alignment <= 1:
        return ""
    return f"__attribute__((aligned({alignment})))"


def get_c_packed_attribute() -> str:
    """Get the C packed attribute string."""
    return "__attribute__((packed))"


def calculate_padding_bytes(current_size: int, target_alignment: int) -> int:
    """Calculate how many padding bytes are needed."""
    return calculate_padding(current_size, target_alignment) 
