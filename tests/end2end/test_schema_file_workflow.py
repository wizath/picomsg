"""
Test demonstrating proper end-to-end workflow using .pico schema files.
This test shows how end-to-end tests should work: load .pico files, generate code, test functionality.
"""

import unittest
import tempfile
import subprocess
import sys
from pathlib import Path
from picomsg.codegen.python import PythonCodeGenerator
from .common_schemas import SchemaFiles, load_schema, TestData


class TestSchemaFileWorkflow(unittest.TestCase):
    """Test proper end-to-end workflow using schema files."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def _create_python_project(self, temp_path: Path, files: dict):
        """Create a Python project structure with generated files."""
        for filename, content in files.items():
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                f.write(content)
    
    def _run_python_script(self, temp_path: Path, script_name: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a Python script."""
        result = subprocess.run(
            [sys.executable, script_name], cwd=temp_path,
            capture_output=True, text=True, timeout=timeout
        )
        return result
    
    def test_schema_file_to_working_code(self):
        """Test complete workflow: .pico file -> generated code -> working functionality."""
        # Step 1: Load schema from .pico file
        schema = load_schema(SchemaFiles.BASIC_PLAYER)
        
        # Step 2: Generate Python code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Step 3: Create test script that uses the generated code
        test_script = '''
import sys
from picomsg_generated import *

def main():
    print("Testing schema file workflow...")
    
    # Create a player using generated code
    player = GamePlayer()
    player.id = TestData.PLAYER_ID
    player.name = TestData.PLAYER_NAME
    player.health = TestData.PLAYER_HEALTH
    
    # Test serialization
    data = player.to_bytes()
    print(f"Serialized player to {len(data)} bytes")
    
    # Test deserialization
    read_player = GamePlayer.from_bytes(data)
    
    # Verify data integrity
    assert read_player.id == TestData.PLAYER_ID
    assert read_player.name == TestData.PLAYER_NAME
    assert read_player.health == TestData.PLAYER_HEALTH
    
    print("SUCCESS: Schema file workflow completed!")

if __name__ == "__main__":
    main()
'''
        
        # Replace TestData references with actual values
        test_script = test_script.replace("TestData.PLAYER_ID", str(TestData.PLAYER_ID))
        test_script = test_script.replace("TestData.PLAYER_NAME", f'"{TestData.PLAYER_NAME}"')
        test_script = test_script.replace("TestData.PLAYER_HEALTH", str(TestData.PLAYER_HEALTH))
        
        # Step 4: Run the test
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Step 5: Verify results
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: Schema file workflow completed!", result.stdout)
    
    def test_complex_schema_file_workflow(self):
        """Test workflow with complex nested structures from schema file."""
        # Step 1: Load complex schema
        schema = load_schema(SchemaFiles.COMPLEX_STRUCTURES)
        
        # Step 2: Generate code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Step 3: Create comprehensive test
        test_script = '''
import sys
from picomsg_generated import *

def main():
    print("Testing complex schema file workflow...")
    
    # Create complex nested structure
    scene = ComplexScene()
    scene.name = "Test Scene"
    
    # Create game object with transform
    obj = ComplexGameObject()
    obj.id = 1
    obj.name = "Test Object"
    
    # Set up transform
    obj.transform = ComplexTransform()
    obj.transform.position = ComplexVector3()
    obj.transform.position.x = 1.0
    obj.transform.position.y = 2.0
    obj.transform.position.z = 3.0
    
    obj.transform.rotation = ComplexVector3()
    obj.transform.scale = ComplexVector3()
    obj.transform.scale.x = 1.0
    obj.transform.scale.y = 1.0
    obj.transform.scale.z = 1.0
    
    obj.tags = ["test", "object"]
    
    scene.objects = [obj]
    scene.camera_position = ComplexVector3()
    
    # Test serialization/deserialization
    data = scene.to_bytes()
    read_scene = ComplexScene.from_bytes(data)
    
    # Verify
    assert read_scene.name == scene.name
    assert len(read_scene.objects) == 1
    assert read_scene.objects[0].name == "Test Object"
    assert read_scene.objects[0].transform.position.x == 1.0
    
    print("SUCCESS: Complex schema file workflow completed!")

if __name__ == "__main__":
    main()
'''
        
        # Step 4: Run test
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Step 5: Verify
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: Complex schema file workflow completed!", result.stdout)
    
    def test_comprehensive_schema_features(self):
        """Test comprehensive schema with all advanced features."""
        # Step 1: Load comprehensive schema
        schema = load_schema(SchemaFiles.COMPREHENSIVE)
        
        # Step 2: Generate code
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Step 3: Test all features
        test_script = '''
import sys
from picomsg_generated import *

def main():
    print("Testing comprehensive schema features...")
    
    # Test enums
    msg_type = ComprehensiveMessageType.Data
    priority = ComprehensivePriority.High
    
    # Test fixed arrays
    color = ComprehensiveColor()
    color.rgba = [255, 128, 64, 255]
    
    metadata = ComprehensiveMetadata()
    metadata.tags = ["tag1", "tag2", "tag3"]
    metadata.values = [1.5, 2.5]
    metadata.flags = [True, False, True, False]
    
    # Test complex nested structure
    data = ComprehensiveComplexData()
    data.id = 12345
    data.type = msg_type
    data.priority = priority
    data.timestamp = 1000000
    
    data.position = ComprehensivePoint3D()
    data.position.x = 1.0
    data.position.y = 2.0
    data.position.z = 3.0
    
    data.color = color
    data.metadata = metadata
    
    # Fixed array of structs
    points = []
    for i in range(5):
        point = ComprehensivePoint3D()
        point.x = float(i)
        point.y = float(i * 2)
        point.z = float(i * 3)
        points.append(point)
    data.points = points
    
    # Fixed array of enums
    data.priorities = [
        ComprehensivePriority.Low,
        ComprehensivePriority.Normal,
        ComprehensivePriority.High
    ]
    
    # Create message
    message = ComprehensiveComplexMessage()
    message.header_id = 999
    message.data = data
    message.checksum = 0xDEADBEEF
    
    # Test serialization/deserialization
    serialized = message.to_bytes()
    deserialized = ComprehensiveComplexMessage.from_bytes(serialized)
    
    # Verify complex data integrity
    assert deserialized.header_id == 999
    assert deserialized.data.id == 12345
    assert deserialized.data.type == ComprehensiveMessageType.Data
    assert deserialized.data.priority == ComprehensivePriority.High
    assert len(deserialized.data.points) == 5
    assert len(deserialized.data.priorities) == 3
    assert deserialized.data.color.rgba == [255, 128, 64, 255]
    assert deserialized.checksum == 0xDEADBEEF
    
    print("SUCCESS: All comprehensive features verified!")

if __name__ == "__main__":
    main()
'''
        
        # Step 4: Run test
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Step 5: Verify
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: All comprehensive features verified!", result.stdout)


if __name__ == '__main__':
    unittest.main() 