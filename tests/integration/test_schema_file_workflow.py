"""
Test demonstrating proper integration test workflow using .pico schema files.
This test shows how integration tests should work: load .pico files, generate code, test cross-language compatibility.
"""

import unittest
import tempfile
import sys
from pathlib import Path
from picomsg.codegen.python import PythonCodeGenerator
from .common_schemas import IntegrationSchemas, load_schema, IntegrationTestData


class TestIntegrationSchemaFileWorkflow(unittest.TestCase):
    """Test proper integration test workflow using schema files."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cross_language_enum_workflow(self):
        """Test complete workflow: .pico file -> generated code -> cross-language compatibility."""
        # Step 1: Load schema from .pico file
        schema = load_schema(IntegrationSchemas.CROSS_LANGUAGE_ENUMS)
        
        # Step 2: Generate Python code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Step 3: Import and test the generated code
        sys.path.insert(0, str(self.temp_dir))
        
        try:
            # Clear module cache
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            
            import picomsg_generated
            
            # Step 4: Test enum functionality
            # Test enum values
            assert picomsg_generated.TestEnumsPriority.Low.value == 1
            assert picomsg_generated.TestEnumsPriority.Medium.value == 5
            assert picomsg_generated.TestEnumsPriority.High.value == 10
            
            assert picomsg_generated.TestEnumsStatus.Inactive.value == 0
            assert picomsg_generated.TestEnumsStatus.Active.value == 100
            assert picomsg_generated.TestEnumsStatus.Pending.value == 101
            assert picomsg_generated.TestEnumsStatus.Complete.value == 1000
            
            # Step 5: Test struct with enums
            task = picomsg_generated.TestEnumsTask(
                id=42,
                name="Test Task",
                priority=picomsg_generated.TestEnumsPriority.High,
                status=picomsg_generated.TestEnumsStatus.Active
            )
            
            # Step 6: Test serialization/deserialization
            data = task.to_bytes()
            task2 = picomsg_generated.TestEnumsTask.from_bytes(data)
            
            assert task2.id == 42
            assert task2.name == "Test Task"
            assert task2.priority == picomsg_generated.TestEnumsPriority.High
            assert task2.status == picomsg_generated.TestEnumsStatus.Active
            
            print("SUCCESS: Cross-language enum workflow completed!")
            
        finally:
            sys.path.remove(str(self.temp_dir))
    
    def test_primitive_types_workflow(self):
        """Test workflow with all primitive types from schema file."""
        # Step 1: Load schema from file
        schema = load_schema(IntegrationSchemas.ALL_PRIMITIVES)
        
        # Step 2: Generate code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Step 3: Test with predefined test data
        sys.path.insert(0, str(self.temp_dir))
        
        try:
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            
            import picomsg_generated
            
            # Find the AllPrimitives class
            AllPrimitives = None
            for attr_name in dir(picomsg_generated):
                if attr_name.endswith('AllPrimitives'):
                    AllPrimitives = getattr(picomsg_generated, attr_name)
                    break
            
            assert AllPrimitives is not None, "AllPrimitives class not found"
            
            # Step 4: Test with common test data
            for test_case in IntegrationTestData.PRIMITIVE_TEST_CASES:
                # Create instance
                instance = AllPrimitives(**test_case['data'])
                
                # Test serialization
                data = instance.to_bytes()
                
                # Test deserialization
                deserialized = AllPrimitives.from_bytes(data)
                
                # Verify data integrity
                for field_name, expected_value in test_case['data'].items():
                    actual_value = getattr(deserialized, field_name)
                    if isinstance(expected_value, float):
                        # Use appropriate tolerance for f32 vs f64
                        tolerance = 1e-5 if field_name.endswith('f32_field') else 1e-10
                        assert abs(actual_value - expected_value) < tolerance, f"Float mismatch in {test_case['name']}.{field_name}"
                    else:
                        assert actual_value == expected_value, f"Value mismatch in {test_case['name']}.{field_name}"
            
            print("SUCCESS: Primitive types workflow completed!")
            
        finally:
            sys.path.remove(str(self.temp_dir))
    
    def test_fixed_arrays_workflow(self):
        """Test workflow with fixed arrays from schema file."""
        # Step 1: Load schema from file
        schema = load_schema(IntegrationSchemas.FIXED_ARRAYS)
        
        # Step 2: Generate code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Step 3: Test fixed array functionality
        sys.path.insert(0, str(self.temp_dir))
        
        try:
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            
            import picomsg_generated
            
            # Test Vector3 with fixed array
            vec = picomsg_generated.TestArraysVector3(coords=[1.0, 2.0, 3.0])
            data = vec.to_bytes()
            vec2 = picomsg_generated.TestArraysVector3.from_bytes(data)
            assert vec2.coords == [1.0, 2.0, 3.0]
            
            # Test Transform with multiple fixed arrays
            transform = picomsg_generated.TestArraysTransform(
                position=[10.0, 20.0, 30.0],
                rotation=[0.0, 0.0, 0.0, 1.0],
                scale=[1.0, 1.0, 1.0]
            )
            
            data = transform.to_bytes()
            transform2 = picomsg_generated.TestArraysTransform.from_bytes(data)
            
            assert transform2.position == [10.0, 20.0, 30.0]
            assert transform2.rotation == [0.0, 0.0, 0.0, 1.0]
            assert transform2.scale == [1.0, 1.0, 1.0]
            
            print("SUCCESS: Fixed arrays workflow completed!")
            
        finally:
            sys.path.remove(str(self.temp_dir))
    
    def test_comprehensive_workflow(self):
        """Test comprehensive schema with all features from schema file."""
        # Step 1: Load comprehensive schema
        schema = load_schema(IntegrationSchemas.COMPREHENSIVE)
        
        # Step 2: Generate code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        python_file = self.temp_dir / "picomsg_generated.py"
        python_file.write_text(files["picomsg_generated.py"])
        
        # Step 3: Test all features
        sys.path.insert(0, str(self.temp_dir))
        
        try:
            if 'picomsg_generated' in sys.modules:
                del sys.modules['picomsg_generated']
            
            import picomsg_generated
            
            # Test enums
            msg_type = picomsg_generated.TestComprehensiveMessageType.Data
            priority = picomsg_generated.TestComprehensivePriority.High
            
            # Test fixed arrays
            color = picomsg_generated.TestComprehensiveColor()
            color.rgba = [255, 128, 64, 255]
            
            metadata = picomsg_generated.TestComprehensiveMetadata()
            metadata.tags = ["tag1", "tag2", "tag3"]
            metadata.values = [1.5, 2.5]
            metadata.flags = [True, False, True, False]
            
            # Test complex nested structure
            data = picomsg_generated.TestComprehensiveComplexData()
            data.id = 12345
            data.type = msg_type
            data.priority = priority
            data.timestamp = 1000000
            
            data.position = picomsg_generated.TestComprehensivePoint3D()
            data.position.x = 1.0
            data.position.y = 2.0
            data.position.z = 3.0
            
            data.color = color
            data.metadata = metadata
            
            # Fixed array of structs
            points = []
            for i in range(5):
                point = picomsg_generated.TestComprehensivePoint3D()
                point.x = float(i)
                point.y = float(i * 2)
                point.z = float(i * 3)
                points.append(point)
            data.points = points
            
            # Fixed array of enums
            data.priorities = [
                picomsg_generated.TestComprehensivePriority.Low,
                picomsg_generated.TestComprehensivePriority.Normal,
                picomsg_generated.TestComprehensivePriority.High
            ]
            
            # Create message
            message = picomsg_generated.TestComprehensiveComplexMessage()
            message.header_id = 999
            message.data = data
            message.checksum = 0xDEADBEEF
            
            # Test serialization/deserialization
            serialized = message.to_bytes()
            deserialized = picomsg_generated.TestComprehensiveComplexMessage.from_bytes(serialized)
            
            # Verify complex data integrity
            assert deserialized.header_id == 999
            assert deserialized.data.id == 12345
            assert deserialized.data.type == picomsg_generated.TestComprehensiveMessageType.Data
            assert deserialized.data.priority == picomsg_generated.TestComprehensivePriority.High
            assert len(deserialized.data.points) == 5
            assert len(deserialized.data.priorities) == 3
            assert deserialized.data.color.rgba == [255, 128, 64, 255]
            assert deserialized.checksum == 0xDEADBEEF
            
            print("SUCCESS: Comprehensive workflow completed!")
            
        finally:
            sys.path.remove(str(self.temp_dir))


if __name__ == '__main__':
    unittest.main() 