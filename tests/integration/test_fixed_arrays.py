"""
Comprehensive tests for fixed-size arrays in PicoMsg.
"""

import pytest
import tempfile
import os
from pathlib import Path

from picomsg.schema.parser import SchemaParser
from picomsg.schema.ast import FixedArrayType, PrimitiveType, StringType, StructType
from picomsg.codegen.python import PythonCodeGenerator
from picomsg.codegen.c import CCodeGenerator
from picomsg.codegen.rust import RustCodeGenerator


class TestFixedArrayParsing:
    """Test parsing of fixed-size array syntax."""
    
    def test_parse_fixed_primitive_arrays(self):
        """Test parsing fixed arrays of primitive types."""
        schema_text = """
        struct FixedArrays {
            bytes3: [u8:3];
            coords: [f32:4];
            matrix: [f64:9];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        assert len(schema.structs) == 1
        struct = schema.structs[0]
        assert len(struct.fields) == 3
        
        # bytes3: [u8:3]
        field = struct.fields[0]
        assert field.name == "bytes3"
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, PrimitiveType)
        assert field.type.element_type.name == "u8"
        assert field.type.size == 3
        
        # coords: [f32:4]
        field = struct.fields[1]
        assert field.name == "coords"
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, PrimitiveType)
        assert field.type.element_type.name == "f32"
        assert field.type.size == 4
        
        # matrix: [f64:9]
        field = struct.fields[2]
        assert field.name == "matrix"
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, PrimitiveType)
        assert field.type.element_type.name == "f64"
        assert field.type.size == 9
    
    def test_parse_fixed_string_arrays(self):
        """Test parsing fixed arrays of strings."""
        schema_text = """
        struct StringArrays {
            names: [string:5];
            labels: [string:10];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        struct = schema.structs[0]
        
        # names: [string:5]
        field = struct.fields[0]
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, StringType)
        assert field.type.size == 5
        
        # labels: [string:10]
        field = struct.fields[1]
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, StringType)
        assert field.type.size == 10
    
    def test_parse_fixed_struct_arrays(self):
        """Test parsing fixed arrays of structs."""
        schema_text = """
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct FixedStructArrays {
            triangle: [Point:3];
            polygon: [Point:8];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        struct = schema.structs[1]  # FixedStructArrays
        
        # triangle: [Point:3]
        field = struct.fields[0]
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, StructType)
        assert field.type.element_type.name == "Point"
        assert field.type.size == 3
        
        # polygon: [Point:8]
        field = struct.fields[1]
        assert isinstance(field.type, FixedArrayType)
        assert isinstance(field.type.element_type, StructType)
        assert field.type.element_type.name == "Point"
        assert field.type.size == 8
    
    def test_fixed_array_size_validation(self):
        """Test validation of fixed array sizes."""
        parser = SchemaParser()
        
        # Test zero size (should fail)
        with pytest.raises(ValueError, match="Fixed array size must be positive"):
            schema_text = """
            struct BadArray {
                empty: [u32:0];
            }
            """
            schema = parser.parse_string(schema_text)
        
        # Test negative size (should fail at parse time)
        with pytest.raises(ValueError, match="Parse error"):
            schema_text = """
            struct BadArray {
                negative: [u32:-1];
            }
            """
            schema = parser.parse_string(schema_text)
        
        # Test very large size (should fail)
        with pytest.raises(ValueError, match="Fixed array size too large"):
            schema_text = """
            struct BadArray {
                huge: [u32:100000];
            }
            """
            schema = parser.parse_string(schema_text)


class TestFixedArrayCodeGeneration:
    """Test code generation for fixed-size arrays."""
    
    def test_python_fixed_array_generation(self):
        """Test Python code generation for fixed arrays."""
        schema_text = """
        namespace test.fixed;
        
        struct FixedArrayStruct {
            coords: [f32:3];
            flags: [u8:4];
            names: [string:2];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.py"]
        
        # Check that fixed arrays are handled
        assert "coords" in code
        assert "flags" in code
        assert "names" in code
        
        # Check default values for fixed arrays
        assert "[0.0] * 3" in code  # f32 default
        assert "[0] * 4" in code    # u8 default
        assert '[""] * 2' in code   # string default
        
        # Check validation in write methods
        assert "len(self._coords) != 3" in code
        assert "len(self._flags) != 4" in code
        assert "len(self._names) != 2" in code
        
        # Check fixed array read/write loops
        assert "for _ in range(3):" in code
        assert "for _ in range(4):" in code
        assert "for _ in range(2):" in code
    
    def test_c_fixed_array_generation(self):
        """Test C code generation for fixed arrays."""
        schema_text = """
        namespace test.fixed;
        
        struct FixedArrayStruct {
            coords: [f32:3];
            flags: [u8:4];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        generator = CCodeGenerator(schema)
        files = generator.generate()
        header = files["picomsg_generated.h"]
        
        # Check that fixed arrays are declared as C arrays
        assert "float coords[3];" in header
        assert "uint8_t flags[4];" in header
    
    def test_rust_fixed_array_generation(self):
        """Test Rust code generation for fixed arrays."""
        schema_text = """
        namespace test.fixed;
        
        struct FixedArrayStruct {
            coords: [f32:3];
            flags: [u8:4];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        code = files["picomsg_generated.rs"]
        
        # Check that fixed arrays are declared as Rust arrays
        assert "pub coords: [f32; 3]," in code
        assert "pub flags: [u8; 4]," in code
        
        # Check array initialization in read methods
        assert "let mut arr = [f32::default(); 3];" in code
        assert "let mut arr = [u8::default(); 4];" in code


class TestFixedArraySerialization:
    """Test serialization and deserialization of fixed arrays."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.schema_file = Path(self.temp_dir) / "test.pico"
        self.python_file = Path(self.temp_dir) / "picomsg_generated.py"
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_fixed_primitive_array_serialization(self):
        """Test serialization of fixed primitive arrays."""
        schema_text = """
        namespace test.fixed;
        
        struct Vector3 {
            coords: [f32:3];
        }
        """
        
        # Write schema and generate Python code
        self.schema_file.write_text(schema_text)
        
        parser = SchemaParser()
        schema = parser.parse_file(self.schema_file)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        self.python_file.write_text(files["picomsg_generated.py"])
        
        # Import generated module
        import sys
        import importlib
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear any cached module
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test serialization
        vector = picomsg_generated.TestFixedVector3(coords=[1.0, 2.0, 3.0])
        data = vector.to_bytes()
        
        # Test deserialization
        vector2 = picomsg_generated.TestFixedVector3.from_bytes(data)
        assert vector2.coords == [1.0, 2.0, 3.0]
        
        # Test validation - wrong size should fail
        with pytest.raises(ValueError, match="must have exactly 3 elements"):
            vector_bad = picomsg_generated.TestFixedVector3(coords=[1.0, 2.0])
            vector_bad.to_bytes()
    
    def test_fixed_string_array_serialization(self):
        """Test serialization of fixed string arrays."""
        schema_text = """
        namespace test.fixed;
        
        struct StringPair {
            names: [string:2];
        }
        """
        
        # Write schema and generate Python code
        self.schema_file.write_text(schema_text)
        
        parser = SchemaParser()
        schema = parser.parse_file(self.schema_file)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        self.python_file.write_text(files["picomsg_generated.py"])
        
        # Import generated module
        import sys
        import importlib
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear any cached module
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test serialization
        pair = picomsg_generated.TestFixedStringPair(names=["Alice", "Bob"])
        data = pair.to_bytes()
        
        # Test deserialization
        pair2 = picomsg_generated.TestFixedStringPair.from_bytes(data)
        assert pair2.names == ["Alice", "Bob"]
        
        # Test validation - wrong size should fail
        with pytest.raises(ValueError, match="must have exactly 2 elements"):
            pair_bad = picomsg_generated.TestFixedStringPair(names=["Alice"])
            pair_bad.to_bytes()
    
    def test_fixed_struct_array_serialization(self):
        """Test serialization of fixed struct arrays."""
        schema_text = """
        namespace test.fixed;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Triangle {
            vertices: [Point:3];
        }
        """
        
        # Write schema and generate Python code
        self.schema_file.write_text(schema_text)
        
        parser = SchemaParser()
        schema = parser.parse_file(self.schema_file)
        
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        self.python_file.write_text(files["picomsg_generated.py"])
        
        # Import generated module
        import sys
        import importlib
        sys.path.insert(0, str(self.temp_dir))
        
        # Clear any cached module
        if 'picomsg_generated' in sys.modules:
            del sys.modules['picomsg_generated']
        
        import picomsg_generated
        
        # Test serialization
        p1 = picomsg_generated.TestFixedPoint(x=0.0, y=0.0)
        p2 = picomsg_generated.TestFixedPoint(x=1.0, y=0.0)
        p3 = picomsg_generated.TestFixedPoint(x=0.5, y=1.0)
        triangle = picomsg_generated.TestFixedTriangle(vertices=[p1, p2, p3])
        
        data = triangle.to_bytes()
        
        # Test deserialization
        triangle2 = picomsg_generated.TestFixedTriangle.from_bytes(data)
        assert len(triangle2.vertices) == 3
        assert triangle2.vertices[0].x == 0.0
        assert triangle2.vertices[0].y == 0.0
        assert triangle2.vertices[1].x == 1.0
        assert triangle2.vertices[1].y == 0.0
        assert triangle2.vertices[2].x == 0.5
        assert triangle2.vertices[2].y == 1.0


class TestFixedArrayProperties:
    """Test properties and characteristics of fixed arrays."""
    
    def test_fixed_array_size_calculation(self):
        """Test size calculation for fixed arrays."""
        schema_text = """
        struct FixedSizes {
            bytes4: [u8:4];
            ints2: [u32:2];
            floats3: [f64:3];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        struct = schema.structs[0]
        
        # bytes4: [u8:4] = 4 bytes
        field = struct.fields[0]
        assert field.type.size_bytes() == 4
        assert field.type.alignment() == 1
        
        # ints2: [u32:2] = 8 bytes
        field = struct.fields[1]
        assert field.type.size_bytes() == 8
        assert field.type.alignment() == 4
        
        # floats3: [f64:3] = 24 bytes
        field = struct.fields[2]
        assert field.type.size_bytes() == 24
        assert field.type.alignment() == 8
    
    def test_fixed_array_with_variable_elements(self):
        """Test fixed arrays with variable-size elements."""
        schema_text = """
        struct VariableElements {
            strings: [string:3];
            bytes_array: [bytes:2];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        struct = schema.structs[0]
        
        # Fixed arrays with variable-size elements are variable-size
        field = struct.fields[0]  # strings: [string:3]
        assert field.type.size_bytes() is None
        assert field.type.alignment() == 2  # String alignment
        
        field = struct.fields[1]  # bytes_array: [bytes:2]
        assert field.type.size_bytes() is None
        assert field.type.alignment() == 2  # Bytes alignment
    
    def test_cli_type_formatting(self):
        """Test CLI formatting of fixed array types."""
        from picomsg.cli import _format_type
        from picomsg.schema.ast import FixedArrayType, PrimitiveType, StringType
        
        # Test primitive fixed array
        fixed_u32 = FixedArrayType(element_type=PrimitiveType(name="u32"), size=5)
        assert _format_type(fixed_u32) == "[u32:5]"
        
        # Test string fixed array
        fixed_string = FixedArrayType(element_type=StringType(), size=3)
        assert _format_type(fixed_string) == "[string:3]"
        
        # Test nested fixed array (if supported in future)
        nested = FixedArrayType(
            element_type=FixedArrayType(element_type=PrimitiveType(name="f32"), size=2),
            size=3
        )
        assert _format_type(nested) == "[[f32:2]:3]"


class TestFixedArrayEdgeCases:
    """Test edge cases and error conditions for fixed arrays."""
    
    def test_maximum_array_size(self):
        """Test maximum allowed array size."""
        parser = SchemaParser()
        
        # Test maximum size (65535)
        schema_text = """
        struct MaxArray {
            big: [u8:65535];
        }
        """
        schema = parser.parse_string(schema_text)
        field = schema.structs[0].fields[0]
        assert field.type.size == 65535
        
        # Test size too large (should fail)
        with pytest.raises(ValueError, match="Fixed array size too large"):
            schema_text = """
            struct TooBigArray {
                huge: [u8:65536];
            }
            """
            schema = parser.parse_string(schema_text)
    
    def test_fixed_array_type_references(self):
        """Test type reference validation for fixed arrays."""
        parser = SchemaParser()
        
        # Valid reference
        schema_text = """
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct ValidArray {
            points: [Point:3];
        }
        """
        schema = parser.parse_string(schema_text)
        assert len(schema.structs) == 2
        
        # Invalid reference (should fail)
        with pytest.raises(ValueError, match="Undefined type"):
            schema_text = """
            struct InvalidArray {
                points: [UnknownType:3];
            }
            """
            schema = parser.parse_string(schema_text)
    
    def test_mixed_array_types(self):
        """Test mixing fixed and variable arrays."""
        schema_text = """
        struct MixedArrays {
            fixed_ints: [u32:5];
            variable_ints: [u32];
            fixed_strings: [string:3];
            variable_strings: [string];
        }
        """
        
        parser = SchemaParser()
        schema = parser.parse_string(schema_text)
        struct = schema.structs[0]
        
        # Check types are correctly identified
        from picomsg.schema.ast import FixedArrayType, ArrayType
        
        assert isinstance(struct.fields[0].type, FixedArrayType)  # fixed_ints
        assert isinstance(struct.fields[1].type, ArrayType)      # variable_ints
        assert isinstance(struct.fields[2].type, FixedArrayType) # fixed_strings
        assert isinstance(struct.fields[3].type, ArrayType)     # variable_strings 
