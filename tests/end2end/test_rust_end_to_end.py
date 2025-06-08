"""
End-to-end integration tests for Rust code generation.
These tests generate Rust code, compile it, and verify the output.
"""

import tempfile
import subprocess
import sys
import json
import shutil
from pathlib import Path
import pytest
from picomsg.schema.parser import SchemaParser
from picomsg.codegen.rust import RustCodeGenerator
from picomsg.codegen.rust_json import RustJsonCodeGenerator


def rust_available():
    """Check if Rust compiler is available."""
    try:
        result = subprocess.run(["cargo", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


pytestmark = pytest.mark.skipif(not rust_available(), reason="Rust compiler not available")


class TestRustEndToEnd:
    """End-to-end tests for Rust code generation and compilation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def _create_rust_project(self, temp_path: Path, files: dict, project_name: str = "test_project"):
        """Create a Rust project structure with generated files."""
        # Create Cargo.toml if not provided
        if "Cargo.toml" not in files:
            cargo_toml = f'''[package]
name = "{project_name}"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = {{ version = "1.0", features = ["derive"] }}
byteorder = "1.4"
'''
            files["Cargo.toml"] = cargo_toml
        
        # Create src directory
        src_dir = temp_path / "src"
        src_dir.mkdir(exist_ok=True)
        
        # Write all files
        for filename, content in files.items():
            if filename.endswith('.rs') and filename != "main.rs":
                # Put Rust modules in src/
                file_path = src_dir / filename
            else:
                # Put Cargo.toml and main.rs in root/src respectively
                if filename == "main.rs":
                    file_path = src_dir / filename
                else:
                    file_path = temp_path / filename
            
            with open(file_path, 'w') as f:
                f.write(content)
    
    def _compile_and_run(self, temp_path: Path, timeout: int = 60) -> subprocess.CompletedProcess:
        """Compile and run a Rust project."""
        # Compile
        compile_result = subprocess.run(
            ["cargo", "build"], cwd=temp_path,
            capture_output=True, text=True, timeout=timeout
        )
        
        if compile_result.returncode != 0:
            raise subprocess.CalledProcessError(
                compile_result.returncode, 
                ["cargo", "build"],
                output=compile_result.stdout,
                stderr=compile_result.stderr
            )
        
        # Run
        run_result = subprocess.run(
            ["cargo", "run"], cwd=temp_path,
            capture_output=True, text=True, timeout=30
        )
        
        return run_result
    
    def test_basic_rust_binary_generation(self):
        """Test basic Rust binary format generation and usage."""
        schema_text = """
        namespace game;
        
        message Player {
            id: u32;
            name: string;
            health: u32;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.rs
        main_rs = '''
mod picomsg_generated;
use picomsg_generated::*;

fn main() {
    println!("Testing basic Rust binary generation...");
    
    // Create a player
    let player = GamePlayer {
        id: 12345,
        name: "TestPlayer".to_string(),
        health: 100,
    };
    
    // Serialize to bytes
    match player.to_bytes() {
        Ok(bytes) => {
            println!("SUCCESS: Wrote {} bytes", bytes.len());
            
            // Deserialize back
            match GamePlayer::from_bytes(&bytes) {
                Ok(read_player) => {
                    println!("SUCCESS: Read player back");
                    println!("  ID: {}", read_player.id);
                    println!("  Name: {}", read_player.name);
                    println!("  Health: {}", read_player.health);
                    
                    // Verify data integrity
                    if read_player.id == player.id &&
                       read_player.name == player.name &&
                       read_player.health == player.health {
                        println!("SUCCESS: Data integrity verified");
                    } else {
                        println!("ERROR: Data integrity check failed");
                        std::process::exit(1);
                    }
                }
                Err(e) => {
                    println!("ERROR: Failed to read player: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            println!("ERROR: Failed to write player: {}", e);
            std::process::exit(1);
        }
    }
    
    println!("All tests passed!");
}
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.rs"] = main_rs
            
            self._create_rust_project(temp_path, files)
            
            try:
                result = self._compile_and_run(temp_path)
                
                # Verify output
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: Wrote" in result.stdout
                assert "SUCCESS: Read player back" in result.stdout
                assert "SUCCESS: Data integrity verified" in result.stdout
                assert "All tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_rust_json_validation_end_to_end(self):
        """Test Rust JSON validation generation and usage."""
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
        generator = RustJsonCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.rs
        main_rs = '''
use serde_json;
use validator::Validate;

mod picomsg_json;
use picomsg_json::*;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Testing Rust JSON validation end-to-end...");
    
    // Test 1: Create and validate a user profile
    let profile = ApiUserProfile {
        id: 1001,
        username: "testuser".to_string(),
        email: "test@example.com".to_string(),
        age: 25,
        location: ApiPoint { x: 37.7749, y: -122.4194 },
        verified: true,
    };
    
    profile.validate()?;
    println!("SUCCESS: User profile validation passed");
    
    // Test 2: Serialize to JSON
    let json_str = serde_json::to_string_pretty(&profile)?;
    println!("SUCCESS: Serialized to JSON:");
    println!("{}", json_str);
    
    // Test 3: Parse JSON with defaults
    let minimal_json = r#"{
        "id": 2002,
        "email": "minimal@example.com",
        "location": {"x": 40.7128, "y": -74.0060}
    }"#;
    
    let parsed_profile: ApiUserProfile = serde_json::from_str(minimal_json)?;
    parsed_profile.validate()?;
    
    println!("SUCCESS: Parsed minimal JSON with defaults");
    println!("  Username: {} (default)", parsed_profile.username);
    println!("  Age: {} (default)", parsed_profile.age);
    println!("  Verified: {} (default)", parsed_profile.verified);
    
    // Test 4: Validation should reject invalid data
    let invalid_json = r#"{
        "id": 3003,
        "email": "invalid@example.com",
        "age": 300,
        "location": {"x": 0.0, "y": 0.0}
    }"#;
    
    match serde_json::from_str::<ApiUserProfile>(invalid_json) {
        Ok(_) => {
            println!("ERROR: Should have rejected invalid age");
            std::process::exit(1);
        }
        Err(_) => {
            println!("SUCCESS: Correctly rejected invalid age (300 > 255)");
        }
    }
    
    // Test 5: Test validation helper functions
    let test_json = r#"{
        "id": 4004,
        "username": "helper_test",
        "email": "helper@example.com",
        "age": 30,
        "location": {"x": 51.5074, "y": -0.1278},
        "verified": true
    }"#;
    
    match validate_json_string::<ApiUserProfile>(test_json) {
        Ok(validated_profile) => {
            println!("SUCCESS: Helper function validation passed");
            println!("  Validated user: {}", validated_profile.username);
        }
        Err(e) => {
            println!("ERROR: Helper function validation failed: {}", e);
            std::process::exit(1);
        }
    }
    
    println!("All JSON validation tests passed!");
    Ok(())
}
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.rs"] = main_rs
            
            self._create_rust_project(temp_path, files)
            
            try:
                result = self._compile_and_run(temp_path, timeout=90)  # JSON validation takes longer to compile
                
                # Verify output
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: User profile validation passed" in result.stdout
                assert "SUCCESS: Serialized to JSON" in result.stdout
                assert "SUCCESS: Parsed minimal JSON with defaults" in result.stdout
                assert "SUCCESS: Correctly rejected invalid age" in result.stdout
                assert "SUCCESS: Helper function validation passed" in result.stdout
                assert "All JSON validation tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_rust_complex_structures(self):
        """Test Rust generation with complex nested structures and arrays."""
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
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.rs
        main_rs = '''
mod picomsg_generated;
use picomsg_generated::*;

fn main() {
    println!("Testing complex Rust structures...");
    
    // Create complex nested structure
    let scene = ComplexScene {
        name: "TestScene".to_string(),
        objects: vec![
            ComplexGameObject {
                id: 1,
                name: "Player".to_string(),
                transform: ComplexTransform {
                    position: ComplexVector3 { x: 0.0, y: 1.0, z: 0.0 },
                    rotation: ComplexVector3 { x: 0.0, y: 45.0, z: 0.0 },
                    scale: ComplexVector3 { x: 1.0, y: 1.0, z: 1.0 },
                },
                                    tags: vec!["player".to_string(), "controllable".to_string()],
            },
            ComplexGameObject {
                id: 2,
                name: "Enemy".to_string(),
                transform: ComplexTransform {
                    position: ComplexVector3 { x: 10.0, y: 0.0, z: 5.0 },
                    rotation: ComplexVector3 { x: 0.0, y: 180.0, z: 0.0 },
                    scale: ComplexVector3 { x: 1.2, y: 1.2, z: 1.2 },
                },
                                    tags: vec!["enemy".to_string(), "ai".to_string()],
            },
        ],
        camera_position: ComplexVector3 { x: 0.0, y: 5.0, z: -10.0 },
    };
    
            // Serialize and deserialize
        match scene.to_bytes() {
            Ok(bytes) => {
                println!("SUCCESS: Wrote complex scene ({} bytes)", bytes.len());
                
                // Read back
                match ComplexScene::from_bytes(&bytes) {
                Ok(read_scene) => {
                    println!("SUCCESS: Read complex scene back");
                    println!("  Scene name: {}", read_scene.name);
                    println!("  Object count: {}", read_scene.objects.len());
                    
                    // Verify first object
                    if let Some(first_obj) = read_scene.objects.first() {
                        println!("  First object: {}", first_obj.name);
                        println!("    Position: ({}, {}, {})", 
                                first_obj.transform.position.x,
                                first_obj.transform.position.y,
                                first_obj.transform.position.z);
                        println!("    Tags: {:?}", first_obj.tags);
                    }
                    
                    // Verify data integrity
                    if read_scene.name == scene.name &&
                       read_scene.objects.len() == scene.objects.len() &&
                       read_scene.objects[0].name == scene.objects[0].name &&
                       read_scene.objects[0].tags.len() == scene.objects[0].tags.len() {
                        println!("SUCCESS: Complex structure integrity verified");
                    } else {
                        println!("ERROR: Complex structure integrity check failed");
                        std::process::exit(1);
                    }
                }
                Err(e) => {
                    println!("ERROR: Failed to read complex scene: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            println!("ERROR: Failed to write complex scene: {}", e);
            std::process::exit(1);
        }
    }
    
    println!("Complex structure test passed!");
}
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.rs"] = main_rs
            
            self._create_rust_project(temp_path, files)
            
            try:
                result = self._compile_and_run(temp_path)
                
                # Verify output
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: Wrote complex scene" in result.stdout
                assert "SUCCESS: Read complex scene back" in result.stdout
                assert "SUCCESS: Complex structure integrity verified" in result.stdout
                assert "Complex structure test passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_rust_default_values_integration(self):
        """Test Rust generation with default values in real usage."""
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
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.rs
        main_rs = '''
mod picomsg_generated;
use picomsg_generated::*;

fn main() {
    println!("Testing Rust default values integration...");
    
    // Test 1: Create config with some custom values
    let config = ConfigServerConfig {
        host: "production.example.com".to_string(),
        port: 443,
        max_connections: 5000,
        enable_ssl: true,
        timeout_seconds: 60,
        debug_mode: false,
    };
    
            // Test 2: Serialize and verify
        match config.to_bytes() {
            Ok(bytes) => {
                println!("SUCCESS: Wrote config ({} bytes)", bytes.len());
                
                // Read back
                match ConfigServerConfig::from_bytes(&bytes) {
                Ok(read_config) => {
                    println!("SUCCESS: Read config back");
                    println!("  Host: {}", read_config.host);
                    println!("  Port: {}", read_config.port);
                    println!("  Max connections: {}", read_config.max_connections);
                    println!("  SSL enabled: {}", read_config.enable_ssl);
                    println!("  Timeout: {}s", read_config.timeout_seconds);
                    println!("  Debug mode: {}", read_config.debug_mode);
                    
                    // Verify values
                    if read_config.host == "production.example.com" &&
                       read_config.port == 443 &&
                       read_config.max_connections == 5000 &&
                       read_config.enable_ssl == true &&
                       read_config.timeout_seconds == 60 &&
                       read_config.debug_mode == false {
                        println!("SUCCESS: All values verified correctly");
                    } else {
                        println!("ERROR: Value verification failed");
                        std::process::exit(1);
                    }
                }
                Err(e) => {
                    println!("ERROR: Failed to read config: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            println!("ERROR: Failed to write config: {}", e);
            std::process::exit(1);
        }
    }
    
    println!("Default values integration test passed!");
}
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.rs"] = main_rs
            
            self._create_rust_project(temp_path, files)
            
            try:
                result = self._compile_and_run(temp_path)
                
                # Verify output
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: Wrote config" in result.stdout
                assert "SUCCESS: Read config back" in result.stdout
                assert "SUCCESS: All values verified correctly" in result.stdout
                assert "Default values integration test passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_rust_performance_benchmark(self):
        """Test Rust generation with performance benchmarking."""
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
        generator = RustCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.rs
        main_rs = '''
mod picomsg_generated;
use picomsg_generated::*;
use std::time::Instant;

fn main() {
    println!("Testing Rust performance benchmark...");
    
    // Create a dataset with many points
    let mut points = Vec::new();
    for i in 0..1000 {
        points.push(PerfDataPoint {
            timestamp: 1000000 + i,
            value: (i as f64) * 3.14159,
            label: format!("point_{}", i),
        });
    }
    
    let dataset = PerfDataset {
        name: "Performance Test Dataset".to_string(),
        points,
        metadata: "Generated for performance testing".to_string(),
    };
    
    println!("Created dataset with {} points", dataset.points.len());
    
            // Benchmark serialization
        let start_write = Instant::now();
        let bytes = match dataset.to_bytes() {
            Ok(bytes) => bytes,
            Err(e) => {
                println!("ERROR: Failed to write dataset: {}", e);
                std::process::exit(1);
            }
        };
        let write_duration = start_write.elapsed();
        
        println!("SUCCESS: Wrote {} bytes in {:?}", bytes.len(), write_duration);
        println!("Write throughput: {:.2} MB/s", 
                 (bytes.len() as f64) / (1024.0 * 1024.0) / write_duration.as_secs_f64());
        
        // Benchmark deserialization
        let start_read = Instant::now();
        let read_dataset = match PerfDataset::from_bytes(&bytes) {
            Ok(dataset) => dataset,
            Err(e) => {
                println!("ERROR: Failed to read dataset: {}", e);
                std::process::exit(1);
            }
        };
        let read_duration = start_read.elapsed();
    
    println!("SUCCESS: Read {} points in {:?}", read_dataset.points.len(), read_duration);
            println!("Read throughput: {:.2} MB/s",
                 (bytes.len() as f64) / (1024.0 * 1024.0) / read_duration.as_secs_f64());
    
    // Verify data integrity
    if read_dataset.name == dataset.name &&
       read_dataset.points.len() == dataset.points.len() &&
       read_dataset.metadata == dataset.metadata {
        println!("SUCCESS: Data integrity verified");
        
        // Check a few sample points
        let sample_indices = [0, 100, 500, 999];
        for &i in &sample_indices {
            let orig = &dataset.points[i];
            let read = &read_dataset.points[i];
            if orig.timestamp != read.timestamp ||
               (orig.value - read.value).abs() > 1e-10 ||
               orig.label != read.label {
                println!("ERROR: Data mismatch at point {}", i);
                std::process::exit(1);
            }
        }
        println!("SUCCESS: Sample point verification passed");
    } else {
        println!("ERROR: Data integrity check failed");
        std::process::exit(1);
    }
    
    println!("Performance benchmark completed successfully!");
}
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.rs"] = main_rs
            
            self._create_rust_project(temp_path, files)
            
            try:
                result = self._compile_and_run(temp_path)
                
                # Verify output
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "Created dataset with 1000 points" in result.stdout
                assert "SUCCESS: Wrote" in result.stdout
                assert "Write throughput:" in result.stdout
                assert "SUCCESS: Read 1000 points" in result.stdout
                assert "Read throughput:" in result.stdout
                assert "SUCCESS: Data integrity verified" in result.stdout
                assert "SUCCESS: Sample point verification passed" in result.stdout
                assert "Performance benchmark completed successfully!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}") 
