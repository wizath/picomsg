"""
Tests for PicoMsg schema AST classes.
"""

import pytest
from picomsg.schema.ast import (
    Schema, Namespace, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, StructType
)


class TestPrimitiveType:
    """Test PrimitiveType class."""
    
    def test_primitive_type_sizes(self):
        """Test that primitive types return correct sizes."""
        test_cases = [
            ('u8', 1), ('i8', 1),
            ('u16', 2), ('i16', 2),
            ('u32', 4), ('i32', 4),
            ('u64', 8), ('i64', 8),
            ('f32', 4), ('f64', 8),
        ]
        
        for type_name, expected_size in test_cases:
            ptype = PrimitiveType(name=type_name)
            assert ptype.size_bytes() == expected_size
            assert ptype.alignment() == expected_size
    
    def test_unknown_primitive_type(self):
        """Test that unknown primitive types return None for size."""
        ptype = PrimitiveType(name='unknown')
        assert ptype.size_bytes() is None
        assert ptype.alignment() == 1


class TestStringType:
    """Test StringType class."""
    
    def test_string_type_properties(self):
        """Test string type properties."""
        stype = StringType()
        assert stype.size_bytes() is None  # Variable size
        assert stype.alignment() == 2  # u16 length prefix


class TestBytesType:
    """Test BytesType class."""
    
    def test_bytes_type_properties(self):
        """Test bytes type properties."""
        btype = BytesType()
        assert btype.size_bytes() is None  # Variable size
        assert btype.alignment() == 2  # u16 length prefix


class TestArrayType:
    """Test ArrayType class."""
    
    def test_array_type_properties(self):
        """Test array type properties."""
        element_type = PrimitiveType(name='u32')
        atype = ArrayType(element_type=element_type)
        assert atype.size_bytes() is None  # Variable size
        assert atype.alignment() == 4  # max(2, element_alignment)
    
    def test_array_alignment_with_small_element(self):
        """Test array alignment with small element type."""
        element_type = PrimitiveType(name='u8')
        atype = ArrayType(element_type=element_type)
        assert atype.alignment() == 2  # u16 count prefix is larger


class TestStructType:
    """Test StructType class."""
    
    def test_struct_type_properties(self):
        """Test struct type properties."""
        stype = StructType(name='TestStruct')
        assert stype.name == 'TestStruct'
        assert stype.size_bytes() is None  # Depends on definition
        assert stype.alignment() == 4  # Default alignment


class TestField:
    """Test Field class."""
    
    def test_field_creation(self):
        """Test field creation with valid name."""
        field_type = PrimitiveType(name='u32')
        field = Field(name='test_field', type=field_type)
        assert field.name == 'test_field'
        assert field.type == field_type
    
    def test_field_invalid_name(self):
        """Test field creation with invalid name."""
        field_type = PrimitiveType(name='u32')
        with pytest.raises(ValueError, match="Invalid field name"):
            Field(name='123invalid', type=field_type)
        
        with pytest.raises(ValueError, match="Invalid field name"):
            Field(name='invalid-name', type=field_type)


class TestStruct:
    """Test Struct class."""
    
    def test_struct_creation(self):
        """Test struct creation with valid fields."""
        fields = [
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='y', type=PrimitiveType(name='f32')),
        ]
        struct = Struct(name='Point', fields=fields)
        assert struct.name == 'Point'
        assert len(struct.fields) == 2
    
    def test_struct_invalid_name(self):
        """Test struct creation with invalid name."""
        fields = [Field(name='x', type=PrimitiveType(name='f32'))]
        with pytest.raises(ValueError, match="Invalid struct name"):
            Struct(name='123Invalid', fields=fields)
    
    def test_struct_duplicate_fields(self):
        """Test struct creation with duplicate field names."""
        fields = [
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='x', type=PrimitiveType(name='f32')),  # Duplicate
        ]
        with pytest.raises(ValueError, match="Duplicate field names"):
            Struct(name='Point', fields=fields)
    
    def test_struct_size_calculation(self):
        """Test struct size calculation for fixed-size fields."""
        fields = [
            Field(name='x', type=PrimitiveType(name='f32')),  # 4 bytes
            Field(name='y', type=PrimitiveType(name='f32')),  # 4 bytes
        ]
        struct = Struct(name='Point', fields=fields)
        assert struct.size_bytes() == 8
    
    def test_struct_size_with_variable_field(self):
        """Test struct size calculation with variable-size field."""
        fields = [
            Field(name='x', type=PrimitiveType(name='f32')),  # 4 bytes
            Field(name='name', type=StringType()),  # Variable size
        ]
        struct = Struct(name='NamedPoint', fields=fields)
        assert struct.size_bytes() is None
    
    def test_struct_alignment(self):
        """Test struct alignment calculation."""
        fields = [
            Field(name='a', type=PrimitiveType(name='u8')),   # align 1
            Field(name='b', type=PrimitiveType(name='u64')),  # align 8
            Field(name='c', type=PrimitiveType(name='u16')),  # align 2
        ]
        struct = Struct(name='MixedStruct', fields=fields)
        assert struct.alignment() == 8  # Max alignment


class TestMessage:
    """Test Message class."""
    
    def test_message_creation(self):
        """Test message creation with valid fields."""
        fields = [
            Field(name='id', type=PrimitiveType(name='u32')),
            Field(name='data', type=BytesType()),
        ]
        message = Message(name='TestMessage', fields=fields)
        assert message.name == 'TestMessage'
        assert len(message.fields) == 2
    
    def test_message_invalid_name(self):
        """Test message creation with invalid name."""
        fields = [Field(name='id', type=PrimitiveType(name='u32'))]
        with pytest.raises(ValueError, match="Invalid message name"):
            Message(name='123Invalid', fields=fields)
    
    def test_message_duplicate_fields(self):
        """Test message creation with duplicate field names."""
        fields = [
            Field(name='id', type=PrimitiveType(name='u32')),
            Field(name='id', type=PrimitiveType(name='u32')),  # Duplicate
        ]
        with pytest.raises(ValueError, match="Duplicate field names"):
            Message(name='TestMessage', fields=fields)


class TestNamespace:
    """Test Namespace class."""
    
    def test_namespace_creation(self):
        """Test namespace creation with valid name."""
        namespace = Namespace(name='com.example.api')
        assert namespace.name == 'com.example.api'
    
    def test_namespace_invalid_name(self):
        """Test namespace creation with invalid name."""
        with pytest.raises(ValueError, match="Invalid namespace part"):
            Namespace(name='com.123invalid.api')
        
        with pytest.raises(ValueError, match="Invalid namespace part"):
            Namespace(name='com.invalid-name.api')


class TestSchema:
    """Test Schema class."""
    
    def test_schema_creation(self):
        """Test schema creation with valid components."""
        namespace = Namespace(name='test.schema')
        
        struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
            Field(name='y', type=PrimitiveType(name='f32')),
        ])
        
        message = Message(name='TestMessage', fields=[
            Field(name='point', type=StructType(name='Point')),
            Field(name='id', type=PrimitiveType(name='u32')),
        ])
        
        schema = Schema(enums=[], namespace=namespace, structs=[struct], messages=[message])
        assert schema.namespace == namespace
        assert len(schema.structs) == 1
        assert len(schema.messages) == 1
    
    def test_schema_duplicate_struct_names(self):
        """Test schema creation with duplicate struct names."""
        struct1 = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
        ])
        struct2 = Struct(name='Point', fields=[  # Duplicate name
            Field(name='y', type=PrimitiveType(name='f32')),
        ])
        
        with pytest.raises(ValueError, match="Duplicate struct names"):
            Schema(enums=[], namespace=None, structs=[struct1, struct2], messages=[])
    
    def test_schema_duplicate_message_names(self):
        """Test schema creation with duplicate message names."""
        message1 = Message(name='Test', fields=[
            Field(name='a', type=PrimitiveType(name='u32')),
        ])
        message2 = Message(name='Test', fields=[  # Duplicate name
            Field(name='b', type=PrimitiveType(name='u32')),
        ])
        
        with pytest.raises(ValueError, match="Duplicate message names"):
            Schema(enums=[], namespace=None, structs=[], messages=[message1, message2])
    
    def test_schema_struct_message_name_conflict(self):
        """Test schema creation with conflicting struct and message names."""
        struct = Struct(name='Test', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
        ])
        message = Message(name='Test', fields=[  # Same name as struct
            Field(name='y', type=PrimitiveType(name='f32')),
        ])
        
        with pytest.raises(ValueError, match="Conflicting enum, struct, and message names"):
            Schema(enums=[], namespace=None, structs=[struct], messages=[message])
    
    def test_schema_get_struct(self):
        """Test getting struct by name."""
        struct = Struct(name='Point', fields=[
            Field(name='x', type=PrimitiveType(name='f32')),
        ])
        schema = Schema(enums=[], namespace=None, structs=[struct], messages=[])
        
        found_struct = schema.get_struct('Point')
        assert found_struct == struct
        
        not_found = schema.get_struct('NotFound')
        assert not_found is None
    
    def test_schema_get_message(self):
        """Test getting message by name."""
        message = Message(name='TestMessage', fields=[
            Field(name='id', type=PrimitiveType(name='u32')),
        ])
        schema = Schema(enums=[], namespace=None, structs=[], messages=[message])
        
        found_message = schema.get_message('TestMessage')
        assert found_message == message
        
        not_found = schema.get_message('NotFound')
        assert not_found is None
    
    def test_schema_get_type_by_name(self):
        """Test getting types by name from schema."""
        struct = Struct(name='TestStruct', fields=[
            Field(name='field1', type=PrimitiveType(name='u32'))
        ])
        message = Message(name='TestMessage', fields=[
            Field(name='field1', type=PrimitiveType(name='u32'))
        ])
        schema = Schema(enums=[], namespace=None, structs=[struct], messages=[message])
        
        # Test getting struct
        result = schema.get_type_by_name('TestStruct')
        assert result is not None
        assert isinstance(result, Struct)
        assert result.name == 'TestStruct'
        
        # Test getting message
        result = schema.get_type_by_name('TestMessage')
        assert result is not None
        assert isinstance(result, Message)
        assert result.name == 'TestMessage'
        
        # Test non-existent type
        result = schema.get_type_by_name('NonExistent')
        assert result is None

    def test_schema_version_field(self):
        """Test schema version field."""
        # Test schema without version (should default to None)
        schema = Schema(enums=[], namespace=None, structs=[], messages=[])
        assert schema.version is None
        
        # Test schema with valid version
        schema = Schema(enums=[], namespace=None, structs=[], messages=[], version=5)
        assert schema.version == 5
        
        # Test schema with version 1 (minimum valid)
        schema = Schema(enums=[], namespace=None, structs=[], messages=[], version=1)
        assert schema.version == 1
        
        # Test schema with version 255 (maximum valid)
        schema = Schema(enums=[], namespace=None, structs=[], messages=[], version=255)
        assert schema.version == 255

    def test_schema_version_validation(self):
        """Test schema version validation."""
        # Test invalid version 0
        with pytest.raises(ValueError, match="Schema version must be between 1 and 255"):
            Schema(enums=[], namespace=None, structs=[], messages=[], version=0)
        
        # Test invalid version 256
        with pytest.raises(ValueError, match="Schema version must be between 1 and 255"):
            Schema(enums=[], namespace=None, structs=[], messages=[], version=256)
        
        # Test invalid negative version
        with pytest.raises(ValueError, match="Schema version must be between 1 and 255"):
            Schema(enums=[], namespace=None, structs=[], messages=[], version=-1) 
