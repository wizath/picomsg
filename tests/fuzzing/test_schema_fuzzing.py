"""
Schema parser fuzzing tests.

Tests the robustness of the schema parser against malformed,
edge case, and randomly generated input.
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from picomsg.schema.parser import SchemaParser
from picomsg.schema.ast import Schema


class TestSchemaFuzzing:
    """Fuzzing tests for schema parser robustness."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = SchemaParser()
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_parser_robustness_random_text(self, schema_text):
        """Test parser robustness against random text input."""
        # Parser should never crash, only raise expected exceptions
        try:
            self.parser.parse_string(schema_text)
        except Exception as e:
            # These are expected exception types - parser should handle gracefully
            expected_exceptions = (
                ValueError,  # Parse errors
                SyntaxError,  # Syntax errors
                TypeError,   # Type errors
                AttributeError,  # Missing attributes
                KeyError,    # Missing keys
            )
            assert isinstance(e, expected_exceptions), \
                f"Unexpected exception type: {type(e).__name__}: {e}"
    
    @given(st.text(alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd', 'Pc']), 
                   min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_identifier_fuzzing(self, identifier):
        """Test identifier parsing with valid identifier characters."""
        assume(identifier[0].isalpha() or identifier[0] == '_')  # Valid identifier start
        
        schema_content = f"""
        namespace test.fuzz;
        
        struct {identifier} {{
            field: u32;
        }}
        """
        
        try:
            schema = self.parser.parse_string(schema_content)
            # If parsing succeeds, verify the identifier was preserved
            assert len(schema.structs) == 1
            struct = schema.structs[0]
            assert struct.name == identifier
        except Exception as e:
            # Some identifiers might be keywords - that's expected
            expected_exceptions = (ValueError, SyntaxError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.integers(min_value=0, max_value=2**32-1))
    @settings(max_examples=100)
    def test_version_number_fuzzing(self, version):
        """Test version number parsing with random values."""
        schema_content = f"""
        namespace test.fuzz;
        version {version};
        
        struct TestStruct {{
            field: u32;
        }}
        """
        
        try:
            schema = self.parser.parse_string(schema_content)
            assert schema.version == version
        except Exception as e:
            # Very large version numbers might be rejected
            expected_exceptions = (ValueError, OverflowError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.lists(st.sampled_from(['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64', 'f32', 'f64']),
                    min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_primitive_type_combinations(self, types):
        """Test various combinations of primitive types."""
        fields = []
        for i, type_name in enumerate(types):
            fields.append(f"    field_{i}: {type_name};")
        
        schema_content = f"""
        namespace test.fuzz;
        
        struct TestStruct {{
{chr(10).join(fields)}
        }}
        """
        
        schema = self.parser.parse_string(schema_content)
        assert len(schema.structs) == 1
        struct = schema.structs[0]
        assert len(struct.fields) == len(types)
        
        for i, expected_type in enumerate(types):
            field = struct.fields[i]
            assert field.name == f"field_{i}"
            assert field.type.name == expected_type
    
    @given(st.text(alphabet=st.characters(whitelist_categories=['Lu', 'Ll']), 
                   min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_namespace_fuzzing(self, namespace_part):
        """Test namespace parsing with various valid namespace components."""
        # Create a valid namespace by joining parts with dots
        namespace = f"test.{namespace_part.lower()}"
        
        schema_content = f"""
        namespace {namespace};
        
        struct TestStruct {{
            field: u32;
        }}
        """
        
        try:
            schema = self.parser.parse_string(schema_content)
            assert schema.namespace.name == namespace
        except Exception as e:
            # Some namespace parts might be invalid
            expected_exceptions = (ValueError, SyntaxError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=30)
    def test_nested_struct_depth_fuzzing(self, depth):
        """Test deeply nested struct definitions."""
        # Create nested struct definitions
        structs = []
        for i in range(depth):
            if i == 0:
                # Base struct with primitive field
                structs.append(f"""
        struct Struct{i} {{
            field: u32;
        }}""")
            else:
                # Nested struct referencing previous struct
                structs.append(f"""
        struct Struct{i} {{
            nested: Struct{i-1};
            field: u32;
        }}""")
        
        schema_content = f"""
        namespace test.fuzz;
        
{chr(10).join(structs)}
        """
        
        try:
            schema = self.parser.parse_string(schema_content)
            assert len(schema.structs) == depth
        except Exception as e:
            # Very deep nesting might hit recursion limits
            expected_exceptions = (RecursionError, ValueError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.text(min_size=0, max_size=500))
    @settings(max_examples=100)
    def test_comment_fuzzing(self, comment_text):
        """Test comment parsing with various comment content."""
        # Escape any existing comment markers to avoid breaking the schema
        safe_comment = comment_text.replace('*/', '* /').replace('//', '/ /')
        
        schema_content = f"""
        namespace test.fuzz;
        
        // {safe_comment}
        struct TestStruct {{
            /* {safe_comment} */
            field: u32; // {safe_comment}
        }}
        """
        
        try:
            schema = self.parser.parse_string(schema_content)
            assert len(schema.structs) == 1
        except Exception as e:
            # Some comment content might break parsing
            expected_exceptions = (ValueError, SyntaxError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.lists(st.text(alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd']),
                            min_size=1, max_size=20), 
                    min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_multiple_struct_fuzzing(self, struct_names):
        """Test parsing multiple structs with various names."""
        # Ensure unique struct names
        unique_names = list(dict.fromkeys(struct_names))  # Preserve order, remove duplicates
        assume(len(unique_names) >= 1)
        
        structs = []
        for i, name in enumerate(unique_names):
            # Ensure valid identifier
            if not name[0].isalpha():
                name = f"S{name}"
            
            structs.append(f"""
        struct {name} {{
            field_{i}: u32;
        }}""")
        
        schema_content = f"""
        namespace test.fuzz;
        
{chr(10).join(structs)}
        """
        
        try:
            schema = self.parser.parse_string(schema_content)
            assert len(schema.structs) == len(unique_names)
        except Exception as e:
            # Some names might be keywords or invalid
            expected_exceptions = (ValueError, SyntaxError)
            assert isinstance(e, expected_exceptions)
    
    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_binary_input_robustness(self, binary_data):
        """Test parser robustness against binary input."""
        try:
            # Try to decode as UTF-8 first
            text = binary_data.decode('utf-8', errors='ignore')
            self.parser.parse_string(text)
        except Exception as e:
            # Parser should handle any text gracefully
            expected_exceptions = (
                ValueError, SyntaxError, TypeError, AttributeError, KeyError,
                UnicodeDecodeError, UnicodeError
            )
            assert isinstance(e, expected_exceptions)
    
    def test_empty_schema_fuzzing(self):
        """Test parsing completely empty schemas."""
        empty_inputs = [
            "",
            "   ",
            "\n\n\n",
            "\t\t\t",
            "// just a comment",
            "/* block comment */",
            "// comment\n\n/* another */\n   ",
        ]
        
        for empty_input in empty_inputs:
            try:
                schema = self.parser.parse_string(empty_input)
                # Empty schema should be valid but have no content
                assert schema.namespace is None or schema.namespace == ""
                assert len(schema.structs) == 0
                assert len(schema.messages) == 0
            except Exception as e:
                # Some parsers might require minimum content
                expected_exceptions = (ValueError, SyntaxError)
                assert isinstance(e, expected_exceptions)
    
    @given(st.text(alphabet='()[]{};"\'\\', min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_special_character_fuzzing(self, special_chars):
        """Test parser robustness against special characters."""
        try:
            self.parser.parse_string(special_chars)
        except Exception as e:
            # Special characters should cause expected parse errors
            expected_exceptions = (
                ValueError, SyntaxError, TypeError, AttributeError, KeyError
            )
            assert isinstance(e, expected_exceptions)
    
    def test_file_parsing_robustness(self):
        """Test file parsing with various file conditions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test non-existent file
            non_existent = temp_path / "does_not_exist.pico"
            with pytest.raises(FileNotFoundError):
                self.parser.parse_file(non_existent)
            
            # Test empty file
            empty_file = temp_path / "empty.pico"
            empty_file.write_text("")
            try:
                schema = self.parser.parse_file(empty_file)
                assert len(schema.structs) == 0
            except Exception as e:
                expected_exceptions = (ValueError, SyntaxError)
                assert isinstance(e, expected_exceptions)
            
            # Test binary file
            binary_file = temp_path / "binary.pico"
            binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe\xfd')
            try:
                self.parser.parse_file(binary_file)
            except Exception as e:
                expected_exceptions = (
                    ValueError, SyntaxError, UnicodeDecodeError, UnicodeError
                )
                assert isinstance(e, expected_exceptions) 
