"""
End-to-end integration tests for Python code generation.
These tests generate Python code and verify it works correctly.
"""

import unittest
import tempfile
import subprocess
import sys
import json
from pathlib import Path
from picomsg.schema.parser import SchemaParser
from picomsg.codegen.python import PythonCodeGenerator
from picomsg.codegen.python_json import PythonJsonCodeGenerator


def python_available():
    """Check if Python is available (should always be true)."""
    return True


class TestPythonEndToEnd(unittest.TestCase):
    """End-to-end tests for Python code generation and execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def _create_python_project(self, temp_path: Path, files: dict):
        """Create a Python project structure with generated files."""
        # Write all files
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
    
    def test_basic_python_binary_generation(self):
        """Test basic Python binary format generation and usage."""
        schema_text = """
        namespace game;
        
        message Player {
            id: u32;
            name: string;
            health: u32;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Create test script
        test_script = '''
import sys
import io
from picomsg_generated import *

def main():
    print("Testing basic Python binary generation...")
    
    # Create a player
    player = GamePlayer()
    player.id = 12345
    player.name = "TestPlayer"
    player.health = 100
    
    # Serialize to bytes
    try:
        data = player.to_bytes()
        print(f"SUCCESS: Wrote {len(data)} bytes")
        
        # Deserialize back
        read_player = GamePlayer.from_bytes(data)
        
        print("SUCCESS: Read player back")
        print(f"  ID: {read_player.id}")
        print(f"  Name: {read_player.name}")
        print(f"  Health: {read_player.health}")
        
        # Verify data integrity
        if (read_player.id == player.id and
            read_player.name == player.name and
            read_player.health == player.health):
            print("SUCCESS: Data integrity verified")
        else:
            print("ERROR: Data integrity check failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    print("All tests passed!")

if __name__ == "__main__":
    main()
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Verify output
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: Wrote", result.stdout)
            self.assertIn("SUCCESS: Read player back", result.stdout)
            self.assertIn("SUCCESS: Data integrity verified", result.stdout)
            self.assertIn("All tests passed!", result.stdout)
    
    def test_python_json_validation_end_to_end(self):
        """Test Python JSON validation generation and usage."""
        schema_text = """
        namespace api;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        message UserProfile {
            id: u32;
            username: string = "anonymous";
            email: string;
            age: u8 = 18;
            location: Point;
            verified: bool = false;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonJsonCodeGenerator(schema)
        files = generator.generate()
        
        # Create test script
        test_script = '''
import sys
import json
from picomsg_json import *

def main():
    print("Testing Python JSON validation end-to-end...")
    
    # Test 1: Create and validate a user profile
    try:
        profile = ApiUserProfile(
            id=1001,
            username="testuser",
            email="test@example.com",
            age=25,
            location=ApiPoint(x=37.7749, y=-122.4194),
            verified=True
        )
        
        print("SUCCESS: User profile created and validated")
        
        # Test 2: Serialize to JSON
        json_str = profile.model_dump_json(indent=2)
        print("SUCCESS: Serialized to JSON:")
        print(json_str)
        
        # Test 3: Parse JSON with defaults
        minimal_json = """{
            "id": 2002,
            "email": "minimal@example.com",
            "location": {"x": 40.7128, "y": -74.0060}
        }"""
        
        parsed_profile = ApiUserProfile.model_validate_json(minimal_json)
        
        print("SUCCESS: Parsed minimal JSON with defaults")
        print(f"  Username: {parsed_profile.username} (default)")
        print(f"  Age: {parsed_profile.age} (default)")
        print(f"  Verified: {parsed_profile.verified} (default)")
        
        # Test 4: Validation should reject invalid data
        try:
            invalid_json = """{
                "id": 3003,
                "email": "invalid@example.com",
                "age": 300,
                "location": {"x": 0.0, "y": 0.0}
            }"""
            
            ApiUserProfile.model_validate_json(invalid_json)
            print("ERROR: Should have rejected invalid age")
            sys.exit(1)
        except Exception:
            print("SUCCESS: Correctly rejected invalid age (300 > 255)")
        
        # Test 5: Test helper functions
        test_data = {
            "id": 4004,
            "username": "helper_test",
            "email": "helper@example.com",
            "age": 30,
            "location": {"x": 51.5074, "y": -0.1278},
            "verified": True
        }
        
        validated_profile = validate_dict(ApiUserProfile, test_data)
        print("SUCCESS: Helper function validation passed")
        print(f"  Validated user: {validated_profile.username}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("All JSON validation tests passed!")

if __name__ == "__main__":
    main()
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Verify output
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: User profile created and validated", result.stdout)
            self.assertIn("SUCCESS: Serialized to JSON", result.stdout)
            self.assertIn("SUCCESS: Parsed minimal JSON with defaults", result.stdout)
            self.assertIn("SUCCESS: Correctly rejected invalid age", result.stdout)
            self.assertIn("SUCCESS: Helper function validation passed", result.stdout)
            self.assertIn("All JSON validation tests passed!", result.stdout)
    
    def test_python_complex_structures(self):
        """Test Python generation with complex nested structures and arrays."""
        schema_text = """
        namespace complex;
        
        struct Vector3 {
            x: f32;
            y: f32;
            z: f32;
        }
        
        struct Transform {
            position: Vector3;
            rotation: Vector3;
            scale: Vector3;
        }
        
        message GameObject {
            id: u64;
            name: string;
            transform: Transform;
            tags: [string];
        }
        
        message Scene {
            name: string;
            objects: [GameObject];
            camera_position: Vector3;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Create test script
        test_script = '''
import sys
import io
from picomsg_generated import *

def main():
    print("Testing complex Python structures...")
    
    try:
        # Create complex nested structure
        scene = ComplexScene()
        scene.name = "TestScene"
        scene.camera_position = ComplexVector3()
        scene.camera_position.x = 0.0
        scene.camera_position.y = 5.0
        scene.camera_position.z = -10.0
        
        # Create first game object
        obj1 = ComplexGameObject()
        obj1.id = 1
        obj1.name = "Player"
        
        obj1.transform = ComplexTransform()
        obj1.transform.position = ComplexVector3()
        obj1.transform.position.x = 0.0
        obj1.transform.position.y = 1.0
        obj1.transform.position.z = 0.0
        
        obj1.transform.rotation = ComplexVector3()
        obj1.transform.rotation.x = 0.0
        obj1.transform.rotation.y = 45.0
        obj1.transform.rotation.z = 0.0
        
        obj1.transform.scale = ComplexVector3()
        obj1.transform.scale.x = 1.0
        obj1.transform.scale.y = 1.0
        obj1.transform.scale.z = 1.0
        
        obj1.tags = ["player", "controllable"]
        
        # Create second game object
        obj2 = ComplexGameObject()
        obj2.id = 2
        obj2.name = "Enemy"
        
        obj2.transform = ComplexTransform()
        obj2.transform.position = ComplexVector3()
        obj2.transform.position.x = 10.0
        obj2.transform.position.y = 0.0
        obj2.transform.position.z = 5.0
        
        obj2.transform.rotation = ComplexVector3()
        obj2.transform.rotation.x = 0.0
        obj2.transform.rotation.y = 180.0
        obj2.transform.rotation.z = 0.0
        
        obj2.transform.scale = ComplexVector3()
        obj2.transform.scale.x = 1.2
        obj2.transform.scale.y = 1.2
        obj2.transform.scale.z = 1.2
        
        obj2.tags = ["enemy", "ai"]
        
        scene.objects = [obj1, obj2]
        
        # Serialize and deserialize
        data = scene.to_bytes()
        
        print(f"SUCCESS: Wrote complex scene ({len(data)} bytes)")
        
        # Read back
        read_scene = ComplexScene.from_bytes(data)
        
        print("SUCCESS: Read complex scene back")
        print(f"  Scene name: {read_scene.name}")
        print(f"  Object count: {len(read_scene.objects)}")
        
        # Verify first object
        if read_scene.objects:
            first_obj = read_scene.objects[0]
            print(f"  First object: {first_obj.name}")
            print(f"    Position: ({first_obj.transform.position.x}, {first_obj.transform.position.y}, {first_obj.transform.position.z})")
            print(f"    Tags: {first_obj.tags}")
        
        # Verify data integrity
        if (read_scene.name == scene.name and
            len(read_scene.objects) == len(scene.objects) and
            read_scene.objects[0].name == scene.objects[0].name and
            len(read_scene.objects[0].tags) == len(scene.objects[0].tags)):
            print("SUCCESS: Complex structure integrity verified")
        else:
            print("ERROR: Complex structure integrity check failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("Complex structure test passed!")

if __name__ == "__main__":
    main()
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Verify output
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: Wrote complex scene", result.stdout)
            self.assertIn("SUCCESS: Read complex scene back", result.stdout)
            self.assertIn("SUCCESS: Complex structure integrity verified", result.stdout)
            self.assertIn("Complex structure test passed!", result.stdout)
    
    def test_python_default_values_integration(self):
        """Test Python generation with default values in real usage."""
        schema_text = """
        namespace config;
        
        message ServerConfig {
            host: string = "localhost";
            port: u16 = 8080;
            max_connections: u32 = 1000;
            enable_ssl: bool = false;
            timeout_seconds: u32 = 30;
            debug_mode: bool = false;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Create test script
        test_script = '''
import sys
import io
from picomsg_generated import *

def main():
    print("Testing Python default values integration...")
    
    try:
        # Test 1: Create config with some custom values
        config = ConfigServerConfig()
        config.host = "production.example.com"
        config.port = 443
        config.max_connections = 5000
        config.enable_ssl = True
        config.timeout_seconds = 60
        config.debug_mode = False
        
        # Test 2: Serialize and verify
        data = config.to_bytes()
        print(f"SUCCESS: Wrote config ({len(data)} bytes)")
        
        # Read back
        read_config = ConfigServerConfig.from_bytes(data)
        
        print("SUCCESS: Read config back")
        print(f"  Host: {read_config.host}")
        print(f"  Port: {read_config.port}")
        print(f"  Max connections: {read_config.max_connections}")
        print(f"  SSL enabled: {read_config.enable_ssl}")
        print(f"  Timeout: {read_config.timeout_seconds}s")
        print(f"  Debug mode: {read_config.debug_mode}")
        
        # Verify values
        if (read_config.host == "production.example.com" and
            read_config.port == 443 and
            read_config.max_connections == 5000 and
            read_config.enable_ssl == True and
            read_config.timeout_seconds == 60 and
            read_config.debug_mode == False):
            print("SUCCESS: All values verified correctly")
        else:
            print("ERROR: Value verification failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("Default values integration test passed!")

if __name__ == "__main__":
    main()
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Verify output
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("SUCCESS: Wrote config", result.stdout)
            self.assertIn("SUCCESS: Read config back", result.stdout)
            self.assertIn("SUCCESS: All values verified correctly", result.stdout)
            self.assertIn("Default values integration test passed!", result.stdout)
    
    def test_python_performance_benchmark(self):
        """Test Python generation with performance benchmarking."""
        schema_text = """
        namespace perf;
        
        message DataPoint {
            timestamp: u64;
            value: f64;
            label: string;
        }
        
        message Dataset {
            name: string;
            points: [DataPoint];
            metadata: string;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = PythonCodeGenerator(schema)
        files = generator.generate()
        
        # Create test script
        test_script = '''
import sys
import io
import time
from picomsg_generated import *

def main():
    print("Testing Python performance benchmark...")
    
    try:
        # Create a dataset with many points
        dataset = PerfDataset()
        dataset.name = "Performance Test Dataset"
        dataset.metadata = "Generated for performance testing"
        dataset.points = []
        
        for i in range(1000):
            point = PerfDataPoint()
            point.timestamp = 1000000 + i
            point.value = float(i) * 3.14159
            point.label = f"point_{i}"
            dataset.points.append(point)
        
        print(f"Created dataset with {len(dataset.points)} points")
        
        # Benchmark serialization
        start_write = time.time()
        data = dataset.to_bytes()
        write_duration = time.time() - start_write
        
        print(f"SUCCESS: Wrote {len(data)} bytes in {write_duration:.4f}s")
        throughput_write = (len(data) / (1024 * 1024)) / write_duration
        print(f"Write throughput: {throughput_write:.2f} MB/s")
        
        # Benchmark deserialization
        start_read = time.time()
        read_dataset = PerfDataset.from_bytes(data)
        read_duration = time.time() - start_read
        
        print(f"SUCCESS: Read {len(read_dataset.points)} points in {read_duration:.4f}s")
        throughput_read = (len(data) / (1024 * 1024)) / read_duration
        print(f"Read throughput: {throughput_read:.2f} MB/s")
        
        # Verify data integrity
        if (read_dataset.name == dataset.name and
            len(read_dataset.points) == len(dataset.points) and
            read_dataset.metadata == dataset.metadata):
            print("SUCCESS: Data integrity verified")
            
            # Check a few sample points
            sample_indices = [0, 100, 500, 999]
            for i in sample_indices:
                orig = dataset.points[i]
                read = read_dataset.points[i]
                if (orig.timestamp != read.timestamp or
                    abs(orig.value - read.value) > 1e-10 or
                    orig.label != read.label):
                    print(f"ERROR: Data mismatch at point {i}")
                    sys.exit(1)
            print("SUCCESS: Sample point verification passed")
        else:
            print("ERROR: Data integrity check failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("Performance benchmark completed successfully!")

if __name__ == "__main__":
    main()
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["test_script.py"] = test_script
            
            self._create_python_project(temp_path, files)
            
            result = self._run_python_script(temp_path, "test_script.py")
            
            # Verify output
            self.assertEqual(result.returncode, 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            self.assertIn("Created dataset with 1000 points", result.stdout)
            self.assertIn("SUCCESS: Wrote", result.stdout)
            self.assertIn("Write throughput:", result.stdout)
            self.assertIn("SUCCESS: Read 1000 points", result.stdout)
            self.assertIn("Read throughput:", result.stdout)
            self.assertIn("SUCCESS: Data integrity verified", result.stdout)
            self.assertIn("SUCCESS: Sample point verification passed", result.stdout)
            self.assertIn("Performance benchmark completed successfully!", result.stdout)


if __name__ == '__main__':
    unittest.main() 
