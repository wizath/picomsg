"""
End-to-end integration tests for TypeScript code generation.
These tests generate TypeScript code, compile it, and verify the output.
"""

import tempfile
import subprocess
import sys
import json
import shutil
from pathlib import Path
import pytest
from picomsg.schema.parser import SchemaParser
from picomsg.codegen.typescript import TypeScriptCodeGenerator


def node_available():
    """Check if Node.js and npm are available."""
    try:
        node_result = subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        npm_result = subprocess.run(["npm", "--version"], capture_output=True, timeout=5)
        return node_result.returncode == 0 and npm_result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def typescript_available():
    """Check if TypeScript compiler is available globally or can be installed."""
    try:
        # Try global tsc first
        result = subprocess.run(["tsc", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # TypeScript will be installed locally via npm
        return True


pytestmark = pytest.mark.skipif(not node_available(), reason="Node.js/npm not available")


class TestTypeScriptEndToEnd:
    """End-to-end tests for TypeScript code generation and compilation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SchemaParser()
    
    def _create_typescript_project(self, temp_path: Path, files: dict, project_name: str = "test_project"):
        """Create a TypeScript project structure with generated files."""
        # Create package.json if not provided
        if "package.json" not in files:
            package_json = {
                "name": project_name,
                "version": "1.0.0",
                "description": "Test project for PicoMsg TypeScript generation",
                "main": "dist/main.js",
                "scripts": {
                    "build": "tsc",
                    "test": "node dist/main.js"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            files["package.json"] = json.dumps(package_json, indent=2)
        
        # Create tsconfig.json if not provided
        if "tsconfig.json" not in files:
            tsconfig = {
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "commonjs",
                    "lib": ["ES2020", "DOM"],
                    "outDir": "./dist",
                    "rootDir": "./",
                    "strict": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                    "declaration": True,
                    "sourceMap": True
                },
                "include": ["*.ts"],
                "exclude": ["node_modules", "dist"]
            }
            files["tsconfig.json"] = json.dumps(tsconfig, indent=2)
        
        # Write all files
        for filename, content in files.items():
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                f.write(content)
    
    def _install_and_compile(self, temp_path: Path, timeout: int = 120) -> subprocess.CompletedProcess:
        """Install dependencies, compile TypeScript, and run the project."""
        # Install dependencies
        install_result = subprocess.run(
            ["npm", "install"], cwd=temp_path,
            capture_output=True, text=True, timeout=timeout
        )
        
        if install_result.returncode != 0:
            raise subprocess.CalledProcessError(
                install_result.returncode,
                ["npm", "install"],
                output=install_result.stdout,
                stderr=install_result.stderr
            )
        
        # Compile TypeScript
        compile_result = subprocess.run(
            ["npm", "run", "build"], cwd=temp_path,
            capture_output=True, text=True, timeout=60
        )
        
        if compile_result.returncode != 0:
            raise subprocess.CalledProcessError(
                compile_result.returncode,
                ["npm", "run", "build"],
                output=compile_result.stdout,
                stderr=compile_result.stderr
            )
        
        # Run the test
        run_result = subprocess.run(
            ["npm", "run", "test"], cwd=temp_path,
            capture_output=True, text=True, timeout=30
        )
        
        return run_result
    
    def test_basic_typescript_binary_generation(self):
        """Test basic TypeScript binary format generation and usage."""
        schema_text = """
        namespace game;
        
        message Player {
            id: u32;
            name: string;
            health: u32;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = TypeScriptCodeGenerator(schema)
        files = generator.generate()
        
        # Create test main.ts
        main_ts = '''
import { Player } from './picomsg-generated';

console.log("Testing basic TypeScript binary generation...");

// Create a player
const player = new Player({
    id: 12345,
    name: "TestPlayer",
    health: 100
});

console.log("Created player:", player.toJSON());

// Serialize to bytes
const bytes = player.toBytes();
console.log(`SUCCESS: Wrote ${bytes.length} bytes`);

// Deserialize back
const readPlayer = new Player();
readPlayer.fromBytes(bytes);

console.log("SUCCESS: Read player back");
console.log("  ID:", readPlayer.id);
console.log("  Name:", readPlayer.name);
console.log("  Health:", readPlayer.health);

// Verify data integrity
if (readPlayer.id === player.id &&
    readPlayer.name === player.name &&
    readPlayer.health === player.health) {
    console.log("SUCCESS: Data integrity verified");
} else {
    console.log("ERROR: Data integrity check failed");
    process.exit(1);
}

// Test JSON serialization
const jsonData = player.toJSON();
const playerFromJson = new Player();
playerFromJson.fromJSON(jsonData);

if (playerFromJson.id === player.id &&
    playerFromJson.name === player.name &&
    playerFromJson.health === player.health) {
    console.log("SUCCESS: JSON serialization verified");
} else {
    console.log("ERROR: JSON serialization check failed");
    process.exit(1);
}

// Test Base64 encoding
const base64 = player.toBase64();
console.log("Base64 encoded:", base64);

const playerFromBase64 = Player.fromBase64(base64);
if (playerFromBase64.id === player.id &&
    playerFromBase64.name === player.name &&
    playerFromBase64.health === player.health) {
    console.log("SUCCESS: Base64 encoding verified");
} else {
    console.log("ERROR: Base64 encoding check failed");
    process.exit(1);
}

console.log("All tests passed!");
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.ts"] = main_ts
            
            # Override the generated package.json with our test-specific one
            test_package_json = {
                "name": "test_project",
                "version": "1.0.0",
                "description": "Test project for PicoMsg TypeScript generation",
                "main": "dist/main.js",
                "scripts": {
                    "build": "tsc",
                    "test": "node dist/main.js"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            files["package.json"] = json.dumps(test_package_json, indent=2)
            
            self._create_typescript_project(temp_path, files)
            
            try:
                result = self._install_and_compile(temp_path)
                
                # Verify output
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: Wrote" in result.stdout
                assert "SUCCESS: Read player back" in result.stdout
                assert "SUCCESS: Data integrity verified" in result.stdout
                assert "SUCCESS: JSON serialization verified" in result.stdout
                assert "SUCCESS: Base64 encoding verified" in result.stdout
                assert "All tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_typescript_complex_structures(self):
        """Test TypeScript generation with complex nested structures and arrays."""
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
        generator = TypeScriptCodeGenerator(schema)
        files = generator.generate()
        
        main_ts = '''
import { Scene, GameObject, Transform, Vector3 } from './picomsg-generated';

console.log("Testing complex TypeScript structures...");

// Create complex nested structure
const scene = new Scene({
    name: "TestScene",
    camera_position: new Vector3({ x: 0.0, y: 5.0, z: -10.0 }),
    objects: [
        new GameObject({
            id: 1,
            name: "Player",
            transform: new Transform({
                position: new Vector3({ x: 0.0, y: 1.0, z: 0.0 }),
                rotation: new Vector3({ x: 0.0, y: 45.0, z: 0.0 }),
                scale: new Vector3({ x: 1.0, y: 1.0, z: 1.0 })
            }),
            tags: ["player", "controllable"]
        }),
        new GameObject({
            id: 2,
            name: "Enemy",
            transform: new Transform({
                position: new Vector3({ x: 10.0, y: 0.0, z: 5.0 }),
                rotation: new Vector3({ x: 0.0, y: 180.0, z: 0.0 }),
                scale: new Vector3({ x: 1.2, y: 1.2, z: 1.2 })
            }),
            tags: ["enemy", "ai"]
        })
    ]
});

console.log("Created scene:", JSON.stringify(scene.toJSON(), null, 2));

// Test serialization
const bytes = scene.toBytes();
console.log(`SUCCESS: Wrote complex scene (${bytes.length} bytes)`);

// Test deserialization
const readScene = new Scene();
readScene.fromBytes(bytes);

console.log("SUCCESS: Read complex scene back");
console.log("  Scene name:", readScene.name);
console.log("  Object count:", readScene.objects.length);

// Verify first object
if (readScene.objects.length > 0) {
    const firstObj = readScene.objects[0];
    console.log("  First object:", firstObj.name);
    console.log(`    Position: (${firstObj.transform.position.x}, ${firstObj.transform.position.y}, ${firstObj.transform.position.z})`);
    console.log("    Tags:", firstObj.tags);
}

// Verify data integrity
let success = true;
if (readScene.name !== scene.name) {
    console.log("ERROR: Scene name mismatch");
    success = false;
}
if (readScene.objects.length !== scene.objects.length) {
    console.log("ERROR: Object count mismatch");
    success = false;
}
if (readScene.objects.length > 0 && readScene.objects[0].name !== scene.objects[0].name) {
    console.log("ERROR: First object name mismatch");
    success = false;
}
if (readScene.objects.length > 0 && readScene.objects[0].tags.length !== scene.objects[0].tags.length) {
    console.log("ERROR: First object tags length mismatch");
    success = false;
}

if (success) {
    console.log("SUCCESS: Complex structure integrity verified");
} else {
    console.log("ERROR: Complex structure integrity check failed");
    process.exit(1);
}

console.log("Complex structure test passed!");
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.ts"] = main_ts
            
            # Override the generated package.json with our test-specific one
            test_package_json = {
                "name": "test_project",
                "version": "1.0.0",
                "description": "Test project for PicoMsg TypeScript generation",
                "main": "dist/main.js",
                "scripts": {
                    "build": "tsc",
                    "test": "node dist/main.js"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            files["package.json"] = json.dumps(test_package_json, indent=2)
            
            self._create_typescript_project(temp_path, files)
            
            try:
                result = self._install_and_compile(temp_path)
                
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: Wrote complex scene" in result.stdout
                assert "SUCCESS: Read complex scene back" in result.stdout
                assert "SUCCESS: Complex structure integrity verified" in result.stdout
                assert "Complex structure test passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_typescript_static_factory_methods(self):
        """Test TypeScript static factory methods."""
        schema_text = """
        namespace test;
        
        struct Config {
            name: string;
            value: u32;
            enabled: bool;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = TypeScriptCodeGenerator(schema)
        files = generator.generate()
        
        main_ts = '''
import { Config } from './picomsg-generated';

console.log("Testing TypeScript static factory methods...");

// Test fromJSON static method
const config1 = Config.fromJSON({
    name: "test_config",
    value: 42,
    enabled: true
});

console.log("Created from JSON:", config1.toJSON());

// Test fromBytes static method
const bytes = config1.toBytes();
const config2 = Config.fromBytes(bytes);

console.log("Created from bytes:", config2.toJSON());

// Test fromBase64 static method
const base64 = config1.toBase64();
const config3 = Config.fromBase64(base64);

console.log("Created from Base64:", config3.toJSON());

// Verify all are identical
if (config1.name === config2.name && config2.name === config3.name &&
    config1.value === config2.value && config2.value === config3.value &&
    config1.enabled === config2.enabled && config2.enabled === config3.enabled) {
    console.log("SUCCESS: All static factory methods work correctly");
} else {
    console.log("ERROR: Static factory methods failed");
    process.exit(1);
}

console.log("All tests passed!");
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.ts"] = main_ts
            
            # Override the generated package.json with our test-specific one
            test_package_json = {
                "name": "test_project",
                "version": "1.0.0",
                "description": "Test project for PicoMsg TypeScript generation",
                "main": "dist/main.js",
                "scripts": {
                    "build": "tsc",
                    "test": "node dist/main.js"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            files["package.json"] = json.dumps(test_package_json, indent=2)
            
            self._create_typescript_project(temp_path, files)
            
            try:
                result = self._install_and_compile(temp_path)
                
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: All static factory methods work correctly" in result.stdout
                assert "All tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_typescript_type_safety(self):
        """Test TypeScript type safety and compilation errors."""
        schema_text = """
        namespace types;
        
        struct TypedData {
            id: u32;
            name: string;
            active: bool;
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = TypeScriptCodeGenerator(schema)
        files = generator.generate()
        
        # This should compile successfully
        main_ts = '''
import { TypedData } from './picomsg-generated';

console.log("Testing TypeScript type safety...");

// Valid usage - should compile
const data: TypedData = new TypedData({
    id: 123,
    name: "test",
    active: true
});

// Type-safe access
const id: number = data.id;
const name: string = data.name;
const active: boolean = data.active;

console.log("Type-safe access works:", { id, name, active });

// Partial constructor should work
const partial = new TypedData({ name: "partial" });
console.log("Partial constructor works:", partial.toJSON());

// Static methods should be type-safe
const fromJson: TypedData = TypedData.fromJSON({ id: 456, name: "json", active: false });
console.log("Type-safe static method works:", fromJson.toJSON());

console.log("SUCCESS: TypeScript type safety verified");
console.log("All tests passed!");
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.ts"] = main_ts
            
            # Override the generated package.json with our test-specific one
            test_package_json = {
                "name": "test_project",
                "version": "1.0.0",
                "description": "Test project for PicoMsg TypeScript generation",
                "main": "dist/main.js",
                "scripts": {
                    "build": "tsc",
                    "test": "node dist/main.js"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            files["package.json"] = json.dumps(test_package_json, indent=2)
            
            self._create_typescript_project(temp_path, files)
            
            try:
                result = self._install_and_compile(temp_path)
                
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "SUCCESS: TypeScript type safety verified" in result.stdout
                assert "All tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}")
    
    def test_typescript_performance_benchmark(self):
        """Test TypeScript performance with large data sets."""
        schema_text = """
        namespace perf;
        
        struct DataPoint {
            timestamp: u64;
            value: f64;
            label: string;
        }
        
        message Dataset {
            name: string;
            points: [DataPoint:100];
        }
        """
        
        schema = self.parser.parse_string(schema_text)
        generator = TypeScriptCodeGenerator(schema)
        files = generator.generate()
        
        main_ts = '''
import { Dataset, DataPoint } from './picomsg-generated';

console.log("Testing TypeScript performance...");

// Create large dataset
const points: DataPoint[] = [];
for (let i = 0; i < 100; i++) {
    points.push(new DataPoint({
        timestamp: Date.now() + i,
        value: Math.random() * 1000,
        label: `point_${i}`
    }));
}

const dataset = new Dataset({
    name: "performance_test",
    points: points
});

console.log(`Created dataset with ${points.length} points`);

// Benchmark serialization
const startTime = Date.now();
const iterations = 1000;

for (let i = 0; i < iterations; i++) {
    const bytes = dataset.toBytes();
    const decoded = new Dataset();
    decoded.fromBytes(bytes);
}

const endTime = Date.now();
const totalTime = endTime - startTime;
const avgTime = totalTime / iterations;

console.log(`Performance test completed:`);
console.log(`  Iterations: ${iterations}`);
console.log(`  Total time: ${totalTime}ms`);
console.log(`  Average time per iteration: ${avgTime.toFixed(3)}ms`);

if (avgTime < 10) {  // Should be fast enough
    console.log("SUCCESS: Performance benchmark passed");
} else {
    console.log("WARNING: Performance might be suboptimal");
}

console.log("All tests passed!");
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files["main.ts"] = main_ts
            
            # Override the generated package.json with our test-specific one
            test_package_json = {
                "name": "test_project",
                "version": "1.0.0",
                "description": "Test project for PicoMsg TypeScript generation",
                "main": "dist/main.js",
                "scripts": {
                    "build": "tsc",
                    "test": "node dist/main.js"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            files["package.json"] = json.dumps(test_package_json, indent=2)
            
            self._create_typescript_project(temp_path, files)
            
            try:
                result = self._install_and_compile(temp_path)
                
                assert result.returncode == 0, f"Program failed:\n{result.stdout}\n{result.stderr}"
                assert "Performance test completed:" in result.stdout
                assert "All tests passed!" in result.stdout
                
            except subprocess.CalledProcessError as e:
                pytest.fail(f"Compilation failed:\nSTDOUT: {e.output}\nSTDERR: {e.stderr}") 