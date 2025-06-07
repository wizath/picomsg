"""
Tests for PicoMsg alignment utilities.
"""

import pytest
from picomsg.format.alignment import (
    align_offset, calculate_padding, calculate_struct_layout, calculate_message_layout,
    get_c_alignment_attribute, get_c_packed_attribute, calculate_padding_bytes
)
from picomsg.schema.ast import (
    Field, Message, PrimitiveType, StringType, BytesType, ArrayType, StructType
)


class TestAlignmentUtilities:
    """Test alignment utility functions."""
    
    def test_align_offset_no_alignment(self):
        """Test aligning offset with no alignment requirement."""
        assert align_offset(0, 1) == 0
        assert align_offset(5, 1) == 5
        assert align_offset(100, 1) == 100
    
    def test_align_offset_power_of_two(self):
        """Test aligning offset to power-of-two boundaries."""
        # 2-byte alignment
        assert align_offset(0, 2) == 0
        assert align_offset(1, 2) == 2
        assert align_offset(2, 2) == 2
        assert align_offset(3, 2) == 4
        
        # 4-byte alignment
        assert align_offset(0, 4) == 0
        assert align_offset(1, 4) == 4
        assert align_offset(2, 4) == 4
        assert align_offset(3, 4) == 4
        assert align_offset(4, 4) == 4
        assert align_offset(5, 4) == 8
        
        # 8-byte alignment
        assert align_offset(0, 8) == 0
        assert align_offset(1, 8) == 8
        assert align_offset(7, 8) == 8
        assert align_offset(8, 8) == 8
        assert align_offset(9, 8) == 16
    
    def test_calculate_padding(self):
        """Test calculating padding bytes."""
        # No padding needed
        assert calculate_padding(0, 4) == 0
        assert calculate_padding(4, 4) == 0
        assert calculate_padding(8, 4) == 0
        
        # Padding needed
        assert calculate_padding(1, 4) == 3
        assert calculate_padding(2, 4) == 2
        assert calculate_padding(3, 4) == 1
        assert calculate_padding(5, 4) == 3
        
        # 8-byte alignment
        assert calculate_padding(1, 8) == 7
        assert calculate_padding(4, 8) == 4
        assert calculate_padding(9, 8) == 7
    
    def test_calculate_padding_bytes(self):
        """Test calculate_padding_bytes function (alias)."""
        assert calculate_padding_bytes(1, 4) == 3
        assert calculate_padding_bytes(5, 8) == 3
        assert calculate_padding_bytes(8, 8) == 0
    
    def test_calculate_struct_layout_simple(self):
        """Test calculating layout for simple struct."""
        fields = [
            Field(name='a', type=PrimitiveType(name='u8')),   # 1 byte, align 1
            Field(name='b', type=PrimitiveType(name='u32')),  # 4 bytes, align 4
            Field(name='c', type=PrimitiveType(name='u16')),  # 2 bytes, align 2
        ]
        
        layout, total_size = calculate_struct_layout(fields)
        
        # Expected layout:
        # a: offset 0, size 1
        # padding: 3 bytes (to align b to 4-byte boundary)
        # b: offset 4, size 4
        # c: offset 8, size 2
        # padding: 2 bytes (to align struct to 4-byte boundary)
        # total: 12 bytes
        
        assert len(layout) == 3
        assert layout[0] == ('a', 0, 1)
        assert layout[1] == ('b', 4, 4)
        assert layout[2] == ('c', 8, 2)
        assert total_size == 12
    
    def test_calculate_struct_layout_no_padding(self):
        """Test calculating layout for struct that needs no padding."""
        fields = [
            Field(name='x', type=PrimitiveType(name='f32')),  # 4 bytes, align 4
            Field(name='y', type=PrimitiveType(name='f32')),  # 4 bytes, align 4
        ]
        
        layout, total_size = calculate_struct_layout(fields)
        
        assert len(layout) == 2
        assert layout[0] == ('x', 0, 4)
        assert layout[1] == ('y', 4, 4)
        assert total_size == 8
    
    def test_calculate_struct_layout_with_u64(self):
        """Test calculating layout with 8-byte aligned field."""
        fields = [
            Field(name='a', type=PrimitiveType(name='u8')),   # 1 byte, align 1
            Field(name='b', type=PrimitiveType(name='u64')),  # 8 bytes, align 8
        ]
        
        layout, total_size = calculate_struct_layout(fields)
        
        # Expected layout:
        # a: offset 0, size 1
        # padding: 7 bytes (to align b to 8-byte boundary)
        # b: offset 8, size 8
        # total: 16 bytes (aligned to 8-byte boundary)
        
        assert len(layout) == 2
        assert layout[0] == ('a', 0, 1)
        assert layout[1] == ('b', 8, 8)
        assert total_size == 16
    
    def test_calculate_struct_layout_empty(self):
        """Test calculating layout for empty struct."""
        fields = []
        layout, total_size = calculate_struct_layout(fields)
        
        assert len(layout) == 0
        assert total_size == 4  # Aligned to base alignment
    
    def test_calculate_struct_layout_custom_base_alignment(self):
        """Test calculating layout with custom base alignment."""
        fields = [
            Field(name='a', type=PrimitiveType(name='u8')),  # 1 byte, align 1
        ]
        
        layout, total_size = calculate_struct_layout(fields, base_alignment=8)
        
        assert len(layout) == 1
        assert layout[0] == ('a', 0, 1)
        assert total_size == 8  # Aligned to 8-byte boundary
    
    def test_calculate_struct_layout_variable_size_fields(self):
        """Test calculating layout with variable-size fields."""
        fields = [
            Field(name='id', type=PrimitiveType(name='u32')),  # 4 bytes, align 4
            Field(name='name', type=StringType()),             # 2 bytes (length prefix), align 2
            Field(name='data', type=BytesType()),              # 2 bytes (length prefix), align 2
            Field(name='tags', type=ArrayType(element_type=PrimitiveType(name='u8'))),  # 2 bytes (count prefix), align 2
        ]
        
        layout, total_size = calculate_struct_layout(fields)
        
        # Expected layout:
        # id: offset 0, size 4
        # name: offset 4, size 2 (length prefix only)
        # data: offset 6, size 2 (length prefix only)
        # tags: offset 8, size 2 (count prefix only)
        # padding: 2 bytes (to align to 4-byte boundary)
        # total: 12 bytes
        
        assert len(layout) == 4
        assert layout[0] == ('id', 0, 4)
        assert layout[1] == ('name', 4, 2)
        assert layout[2] == ('data', 6, 2)
        assert layout[3] == ('tags', 8, 2)
        assert total_size == 12
    
    def test_calculate_message_layout(self):
        """Test calculating layout for message (should be same as struct)."""
        fields = [
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='y', type=PrimitiveType(name='f32')),
        ]
        
        message = Message(name='TestMessage', fields=fields)
        layout, total_size = calculate_message_layout(message)
        
        assert len(layout) == 2
        assert layout[0] == ('x', 0, 4)
        assert layout[1] == ('y', 4, 4)
        assert total_size == 8
    
    def test_get_c_alignment_attribute(self):
        """Test generating C alignment attributes."""
        assert get_c_alignment_attribute(1) == ""
        assert get_c_alignment_attribute(0) == ""
        assert get_c_alignment_attribute(4) == "__attribute__((aligned(4)))"
        assert get_c_alignment_attribute(8) == "__attribute__((aligned(8)))"
        assert get_c_alignment_attribute(16) == "__attribute__((aligned(16)))"
    
    def test_get_c_packed_attribute(self):
        """Test generating C packed attribute."""
        assert get_c_packed_attribute() == "__attribute__((packed))"
    
    def test_struct_type_field_size(self):
        """Test that struct type fields have size 0 (to be resolved later)."""
        fields = [
            Field(name='point', type=StructType(name='Point')),
        ]
        
        layout, total_size = calculate_struct_layout(fields)
        
        # StructType fields should have size 0 since they need to be resolved
        assert len(layout) == 1
        assert layout[0] == ('point', 0, 0)
        assert total_size == 4  # Base alignment
    
    def test_array_alignment_with_different_elements(self):
        """Test array alignment with different element types."""
        # Array of u8 - alignment should be max(2, 1) = 2
        fields = [Field(name='bytes', type=ArrayType(element_type=PrimitiveType(name='u8')))]
        layout, _ = calculate_struct_layout(fields)
        assert layout[0] == ('bytes', 0, 2)
        
        # Array of u64 - alignment should be max(2, 8) = 8
        fields = [Field(name='longs', type=ArrayType(element_type=PrimitiveType(name='u64')))]
        layout, _ = calculate_struct_layout(fields)
        assert layout[0] == ('longs', 0, 2)  # Size is still 2 (count prefix)
    
    def test_complex_struct_layout(self):
        """Test calculating layout for complex struct with mixed types."""
        fields = [
            Field(name='magic', type=PrimitiveType(name='u16')),     # 2 bytes, align 2
            Field(name='version', type=PrimitiveType(name='u8')),    # 1 byte, align 1
            Field(name='flags', type=PrimitiveType(name='u8')),      # 1 byte, align 1
            Field(name='timestamp', type=PrimitiveType(name='u64')), # 8 bytes, align 8
            Field(name='length', type=PrimitiveType(name='u32')),    # 4 bytes, align 4
            Field(name='data', type=BytesType()),                    # 2 bytes, align 2
        ]
        
        layout, total_size = calculate_struct_layout(fields)
        
        # Expected layout:
        # magic: offset 0, size 2
        # version: offset 2, size 1
        # flags: offset 3, size 1
        # padding: 4 bytes (to align timestamp to 8-byte boundary)
        # timestamp: offset 8, size 8
        # length: offset 16, size 4
        # data: offset 20, size 2
        # padding: 2 bytes (to align struct to 8-byte boundary)
        # total: 24 bytes
        
        assert len(layout) == 6
        assert layout[0] == ('magic', 0, 2)
        assert layout[1] == ('version', 2, 1)
        assert layout[2] == ('flags', 3, 1)
        assert layout[3] == ('timestamp', 8, 8)
        assert layout[4] == ('length', 16, 4)
        assert layout[5] == ('data', 20, 2)
        assert total_size == 24 
