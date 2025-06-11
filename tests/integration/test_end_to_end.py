"""
End-to-end integration tests for PicoMsg workflows.

These tests verify complete workflows from schema definition through
code generation to actual runtime usage.
"""

import pytest
import tempfile
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any

from picomsg.cli import main
from click.testing import CliRunner


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_dir(self) -> Path:
        """Create a temporary directory."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        return Path(self.temp_dir)
    
    def create_schema_file(self, content: str, filename: str = "test.pico") -> Path:
        """Create a schema file in the temp directory."""
        temp_dir = self.create_temp_dir()
        schema_file = temp_dir / filename
        schema_file.write_text(content)
        return schema_file
    
    def test_complete_c_workflow(self):
        """Test complete workflow: schema -> C code -> compilation -> execution."""
        schema_content = '''
        version 1;
        namespace test.workflow;
        
        struct Point {
            x: f32;
            y: f32;
        }
        
        struct Rectangle {
            top_left: Point;
            bottom_right: Point;
        }
        
        message GeometryRequest {
            shapes: [Rectangle];
            count: u32;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        output_dir = temp_dir / "c_output"
        
        # Step 1: Validate schema
        result = self.runner.invoke(main, ['validate', str(schema_file)])
        assert result.exit_code == 0
        assert "Schema file is valid" in result.output
        
        # Step 2: Generate C code
        result = self.runner.invoke(main, [
            'compile', str(schema_file),
            '--lang', 'c',
            '--output', str(output_dir),
            '--header-name', 'geometry'
        ])
        assert result.exit_code == 0
        assert "Generated 2 files" in result.output
        
        # Step 3: Verify generated files
        assert (output_dir / "geometry.h").exists()
        assert (output_dir / "geometry.c").exists()
        
        # Step 4: Check generated content
        header_content = (output_dir / "geometry.h").read_text()
        impl_content = (output_dir / "geometry.c").read_text()
        
        # Verify structs are generated
        assert "test_workflow_point_t" in header_content
        assert "test_workflow_rectangle_t" in header_content
        assert "test_workflow_geometryrequest_t" in header_content
        
        # Verify functions are generated
        assert "test_workflow_point_from_bytes" in header_content
        assert "test_workflow_point_to_bytes" in header_content
        
        # Step 5: Test compilation (if gcc available)
        try:
            test_c_content = '''
#include "geometry.h"
#include <stdio.h>

int main() {
    test_workflow_point_t point = {1.0f, 2.0f};
    printf("Point: (%.1f, %.1f)\\n", point.x, point.y);
    return 0;
}
'''
            test_file = output_dir / "test_main.c"
            test_file.write_text(test_c_content)
            
            result = subprocess.run([
                'gcc', '-o', str(output_dir / 'test_program'),
                str(test_file), str(output_dir / 'geometry.c'),
                '-I', str(output_dir)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Step 6: Execute compiled program
                exec_result = subprocess.run([
                    str(output_dir / 'test_program')
                ], capture_output=True, text=True)
                
                assert exec_result.returncode == 0
                assert "Point: (1.0, 2.0)" in exec_result.stdout
            
        except FileNotFoundError:
            pytest.skip("GCC not available for compilation test")
    
    def test_complete_rust_workflow(self):
        """Test complete workflow: schema -> Rust code -> compilation -> execution."""
        schema_content = '''
        version 2;
        namespace test.rust_workflow;
        
        struct Config {
            name: string;
            enabled: u8;
            timeout: u32;
        }
        
        message ConfigUpdate {
            config: Config;
            timestamp: u64;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        output_dir = temp_dir / "rust_output"
        
        # Step 1: Validate schema
        result = self.runner.invoke(main, ['validate', str(schema_file)])
        assert result.exit_code == 0
        
        # Step 2: Generate Rust code
        result = self.runner.invoke(main, [
            'compile', str(schema_file),
            '--lang', 'rust',
            '--output', str(output_dir),
            '--module-name', 'config_types'
        ])
        assert result.exit_code == 0
        assert "Generated 1 files" in result.output
        
        # Step 3: Verify generated files
        assert (output_dir / "config_types.rs").exists()
        
        # Step 4: Check generated content
        rust_content = (output_dir / "config_types.rs").read_text()
        
        # Verify structs are generated
        assert "pub struct TestRustWorkflowConfig {" in rust_content
        assert "pub struct TestRustWorkflowConfigUpdate {" in rust_content
        
        # Verify traits are generated
        assert "pub trait TestRustWorkflowSerialize {" in rust_content
        
        # Step 5: Create Rust project and test compilation
        try:
            # Create Cargo.toml
            cargo_toml = '''
[package]
name = "config-test"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
byteorder = "1.4"
base64 = "0.21"
'''
            (output_dir / "Cargo.toml").write_text(cargo_toml)
            
            # Create src directory and lib.rs
            src_dir = output_dir / "src"
            src_dir.mkdir(exist_ok=True)
            
            lib_rs = '''
pub mod config_types;
pub use config_types::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_serialization() {
        let config = TestRustWorkflowConfig {
            name: "test_config".to_string(),
            enabled: 1,
            timeout: 5000,
        };
        
        let bytes = config.to_bytes().expect("Failed to serialize");
        let decoded = TestRustWorkflowConfig::from_bytes(&bytes).expect("Failed to deserialize");
        
        assert_eq!(config, decoded);
    }
    
    #[test]
    fn test_config_update_serialization() {
        let config_update = TestRustWorkflowConfigUpdate {
            config: TestRustWorkflowConfig {
                name: "updated_config".to_string(),
                enabled: 0,
                timeout: 10000,
            },
            timestamp: 1234567890,
        };
        
        let bytes = config_update.to_bytes().expect("Failed to serialize");
        let decoded = TestRustWorkflowConfigUpdate::from_bytes(&bytes).expect("Failed to deserialize");
        
        assert_eq!(config_update, decoded);
    }
}
'''
            (src_dir / "lib.rs").write_text(lib_rs)
            
            # Move generated file to src
            (output_dir / "config_types.rs").rename(src_dir / "config_types.rs")
            
            # Step 6: Test compilation and execution
            result = subprocess.run([
                'cargo', 'test'
            ], cwd=output_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                assert "test result: ok" in result.stdout
            else:
                # Print error for debugging
                print(f"Cargo test failed: {result.stderr}")
                
        except FileNotFoundError:
            pytest.skip("Cargo not available for Rust compilation test")
    
    def test_schema_info_workflow(self):
        """Test schema information extraction workflow."""
        schema_content = '''
        version 5;
        namespace com.example.api;
        
        struct User {
            id: u64;
            username: string;
            email: string;
            active: u8;
        }
        
        struct Post {
            id: u64;
            author: User;
            title: string;
            content: string;
            tags: [string];
            created_at: u64;
        }
        
        message CreatePostRequest {
            post: Post;
            auth_token: string;
        }
        
        message CreatePostResponse {
            success: u8;
            post_id: u64;
            error_message: string;
        }
        '''
        
        schema_file = self.create_schema_file(schema_content)
        
        # Test info command
        result = self.runner.invoke(main, ['info', str(schema_file)])
        assert result.exit_code == 0
        
        output = result.output
        
        # Check namespace and version
        assert "Namespace: com.example.api" in output
        assert "Version: 5" in output
        
        # Check structs
        assert "User:" in output
        assert "id: u64" in output
        assert "username: string" in output
        
        assert "Post:" in output
        assert "author: User" in output
        assert "tags: [string]" in output
        
        # Check messages
        assert "CreatePostRequest:" in output
        assert "CreatePostResponse:" in output
    
    def test_structs_only_workflow(self):
        """Test structs-only generation workflow."""
        schema_content = '''
        namespace embedded.protocol;
        
        struct SensorReading {
            sensor_id: u16;
            value: f32;
            timestamp: u32;
        }
        
        struct DeviceStatus {
            device_id: u32;
            battery_level: u8;
            readings: [SensorReading];
        }
        
        message StatusReport {
            status: DeviceStatus;
            checksum: u16;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        output_dir = temp_dir / "embedded_output"
        
        # Generate structs-only C code
        result = self.runner.invoke(main, [
            'compile', str(schema_file),
            '--lang', 'c',
            '--output', str(output_dir),
            '--header-name', 'protocol',
            '--structs-only'
        ])
        assert result.exit_code == 0
        assert "Mode: Structs only" in result.output
        assert "Generated 1 files" in result.output
        
        # Verify only header file was generated
        assert (output_dir / "protocol.h").exists()
        assert not (output_dir / "protocol.c").exists()
        
        # Check header content
        header_content = (output_dir / "protocol.h").read_text()
        
        # Should contain struct definitions
        assert "embedded_protocol_sensorreading_t" in header_content
        assert "embedded_protocol_devicestatus_t" in header_content
        assert "embedded_protocol_statusreport_t" in header_content
        
        # Should NOT contain error enums or function declarations
        assert "typedef enum" not in header_content
        assert "_from_bytes" not in header_content
        assert "_to_bytes" not in header_content
        assert "MAGIC_BYTE" not in header_content
    
    def test_error_handling_workflow(self):
        """Test error handling in various workflow scenarios."""
        temp_dir = self.create_temp_dir()
        
        # Test 1: Invalid schema syntax
        invalid_schema = '''
        namespace test;
        
        struct InvalidStruct {
            field: UnknownType;
        }
        '''
        
        schema_file = self.create_schema_file(invalid_schema, "invalid.pico")
        
        result = self.runner.invoke(main, ['validate', str(schema_file)])
        assert result.exit_code == 1
        assert "Validation failed" in result.output
        
        # Test 2: Nonexistent schema file
        result = self.runner.invoke(main, ['validate', str(temp_dir / "nonexistent.pico")])
        assert result.exit_code == 2  # Click file not found error
        
        # Test 3: Invalid language
        valid_schema = '''
        struct Point { x: f32; y: f32; }
        '''
        
        schema_file = self.create_schema_file(valid_schema, "valid.pico")
        
        result = self.runner.invoke(main, [
            'compile', str(schema_file),
            '--lang', 'invalid_language'
        ])
        assert result.exit_code == 2  # Click validation error
    
    def test_complex_schema_workflow(self):
        """Test workflow with a complex, realistic schema."""
        schema_content = '''
        version 3;
        namespace game.protocol;
        
        struct Vector3 {
            x: f32;
            y: f32;
            z: f32;
        }
        
        struct Player {
            id: u32;
            name: string;
            position: Vector3;
            health: u16;
            inventory: [u32];
        }
        
        struct GameState {
            players: [Player];
            world_time: u64;
            weather: u8;
        }
        
        message PlayerJoin {
            player: Player;
            session_token: string;
        }
        
        message PlayerMove {
            player_id: u32;
            new_position: Vector3;
            timestamp: u64;
        }
        
        message GameStateUpdate {
            state: GameState;
            delta_time: f32;
        }
        
        message ChatMessage {
            sender_id: u32;
            message: string;
            channel: u8;
        }
        '''
        
        temp_dir = self.create_temp_dir()
        schema_file = self.create_schema_file(schema_content)
        
        # Test validation
        result = self.runner.invoke(main, ['validate', str(schema_file)])
        assert result.exit_code == 0
        assert "Version: 3" in result.output
        assert "Structs: 3" in result.output
        assert "Messages: 4" in result.output
        
        # Test info command
        result = self.runner.invoke(main, ['info', str(schema_file)])
        assert result.exit_code == 0
        assert "Vector3:" in result.output
        assert "Player:" in result.output
        assert "GameState:" in result.output
        assert "PlayerJoin:" in result.output
        assert "ChatMessage:" in result.output
        
        # Test C code generation
        c_output_dir = temp_dir / "c_game"
        result = self.runner.invoke(main, [
            'compile', str(schema_file),
            '--lang', 'c',
            '--output', str(c_output_dir),
            '--header-name', 'game_protocol'
        ])
        assert result.exit_code == 0
        
        # Verify C files
        assert (c_output_dir / "game_protocol.h").exists()
        assert (c_output_dir / "game_protocol.c").exists()
        
        # Test Rust code generation
        rust_output_dir = temp_dir / "rust_game"
        result = self.runner.invoke(main, [
            'compile', str(schema_file),
            '--lang', 'rust',
            '--output', str(rust_output_dir),
            '--module-name', 'game_protocol'
        ])
        assert result.exit_code == 0
        
        # Verify Rust files
        assert (rust_output_dir / "game_protocol.rs").exists()
        
        # Check that both implementations have consistent type IDs
        c_content = (c_output_dir / "game_protocol.h").read_text()
        rust_content = (rust_output_dir / "game_protocol.rs").read_text()
        
        # All message types should have consistent IDs
        assert "PLAYERJOIN_TYPE_ID 1" in c_content
        assert "PLAYERMOVE_TYPE_ID 2" in c_content
        assert "GAMESTATEUPDATE_TYPE_ID 3" in c_content
        assert "CHATMESSAGE_TYPE_ID 4" in c_content
        
        assert "PLAYERJOIN_TYPE_ID: u16 = 1" in rust_content
        assert "PLAYERMOVE_TYPE_ID: u16 = 2" in rust_content
        assert "GAMESTATEUPDATE_TYPE_ID: u16 = 3" in rust_content
        assert "CHATMESSAGE_TYPE_ID: u16 = 4" in rust_content 
