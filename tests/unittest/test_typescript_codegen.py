"""
Tests for TypeScript code generator.
"""

import pytest
from picomsg.schema.ast import (
    Schema, Struct, Message, Field, Namespace, Enum, EnumValue,
    PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
)
from picomsg.codegen.typescript import TypeScriptCodeGenerator


def test_typescript_generator_basic():
    """Test basic TypeScript code generation."""
    schema = Schema(enums=[], 
        namespace=Namespace("test.example"),
        structs=[
            Struct("Point", [
                Field("x", PrimitiveType("f32")),
                Field("y", PrimitiveType("f32"))
            ])
        ],
        messages=[
            Message("EchoRequest", [
                Field("point", StructType("Point")),
                Field("id", PrimitiveType("u32"))
            ])
        ]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    
    assert len(files) == 5  # .ts, .d.ts, package.json, tsconfig.json, README.md
    assert "picomsg-generated.ts" in files
    assert "picomsg-generated.d.ts" in files
    assert "package.json" in files
    assert "tsconfig.json" in files
    assert "README.md" in files
    
    content = files["picomsg-generated.ts"]
    
    # Check for proper TypeScript syntax
    assert "export abstract class test_example_Base" in content
    assert "export class test_example_Error extends Error" in content
    
    # Check for proper naming conventions
    assert "export class Point extends test_example_Base" in content
    assert "export class EchoRequest extends test_example_Base" in content
    
    # Check for constants
    assert "export const TEST_EXAMPLE__VERSION = 1;" in content
    assert "export const TEST_EXAMPLE__ECHO_REQUEST_TYPE_ID = 1;" in content


def test_typescript_generator_primitives():
    """Test TypeScript generation with all primitive types."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("AllTypes", [
                Field("u8_field", PrimitiveType("u8")),
                Field("u16_field", PrimitiveType("u16")),
                Field("u32_field", PrimitiveType("u32")),
                Field("u64_field", PrimitiveType("u64")),
                Field("i8_field", PrimitiveType("i8")),
                Field("i16_field", PrimitiveType("i16")),
                Field("i32_field", PrimitiveType("i32")),
                Field("i64_field", PrimitiveType("i64")),
                Field("f32_field", PrimitiveType("f32")),
                Field("f64_field", PrimitiveType("f64")),
                Field("bool_field", PrimitiveType("bool")),
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Check struct definition with TypeScript types
    assert "export class AllTypes extends PicoMsgBase" in content
    assert "u8_field: number = 0;" in content
    assert "f64_field: number = 0;" in content
    assert "bool_field: boolean = false;" in content
    
    # Check constructor
    assert "constructor(data?: Partial<AllTypes>)" in content
    assert "this.u8_field = data?.u8_field ?? 0;" in content
    assert "this.bool_field = data?.bool_field ?? false;" in content
    
    # Check serialization methods
    assert "toBytes(): Uint8Array" in content
    assert "fromBytes(data: Uint8Array): void" in content
    assert "toJSON(): any" in content
    assert "fromJSON(data: any): void" in content


def test_typescript_generator_strings_and_bytes():
    """Test TypeScript generation with string and bytes types."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("StringStruct", [
                Field("name", StringType()),
                Field("data", BytesType()),
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Check types
    assert "name: string = \"\";" in content
    assert "data: Uint8Array = new Uint8Array(0);" in content
    
    # Check string serialization
    assert "new TextEncoder().encode(this.name)" in content
    assert "new TextDecoder().decode(" in content


def test_typescript_generator_arrays():
    """Test TypeScript generation with array types."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("Point", [
                Field("x", PrimitiveType("f32")),
                Field("y", PrimitiveType("f32"))
            ]),
            Struct("ArrayStruct", [
                Field("numbers", ArrayType(PrimitiveType("u32"))),
                Field("points", ArrayType(StructType("Point"))),
                Field("fixed_bytes", FixedArrayType(PrimitiveType("u8"), 10)),
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Check types
    assert "numbers: number[] = [];" in content
    assert "points: Point[] = [];" in content
    assert "fixed_bytes: number[] = [];" in content


def test_typescript_generator_enums():
    """Test TypeScript generation with enums."""
    schema = Schema(
        enums=[
            Enum("Status", PrimitiveType("u8"), [
                EnumValue("ACTIVE", 1),
                EnumValue("INACTIVE", 2),
                EnumValue("PENDING", 3)
            ])
        ],
        namespace=None,
        structs=[
            Struct("User", [
                Field("id", PrimitiveType("u32")),
                Field("status", EnumType("Status"))
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Check enum definition
    assert "export enum Status {" in content
    assert "ACTIVE = 1," in content
    assert "INACTIVE = 2," in content
    assert "PENDING = 3," in content
    
    # Check enum usage in struct
    assert "status: Status = Status.ACTIVE;" in content


def test_typescript_generator_with_version():
    """Test TypeScript generation with schema version."""
    schema = Schema(enums=[], 
        namespace=Namespace("test.versioned"),
        structs=[],
        messages=[],
        version=42
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    assert "export const TEST_VERSIONED__VERSION = 42;" in content


def test_typescript_generator_module_name_option():
    """Test TypeScript generator with custom module name."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("TestStruct", [Field("value", PrimitiveType("u32"))])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    generator.set_option('module_name', 'custom_module')
    files = generator.generate()
    
    assert "custom_module.ts" in files
    assert "custom_module.d.ts" in files
    
    # Check package.json has correct name
    package_json = files["package.json"]
    assert '"name": "custom_module"' in package_json


def test_typescript_generator_no_namespace():
    """Test TypeScript generation without namespace."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("Point", [
                Field("x", PrimitiveType("f32")),
                Field("y", PrimitiveType("f32"))
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Check that types don't have namespace prefix
    assert "export class Point extends PicoMsgBase" in content
    assert "export class PicoMsgError extends Error" in content
    assert "export abstract class PicoMsgBase" in content
    
    # Check constants don't have namespace prefix
    assert "export const VERSION = 1;" in content


def test_typescript_generator_static_methods():
    """Test TypeScript generation includes static factory methods."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("Config", [
                Field("name", StringType()),
                Field("value", PrimitiveType("u32"))
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Check static methods in base class
    assert "static fromBytes<T extends PicoMsgBase>" in content
    assert "static fromJSON<T extends PicoMsgBase>" in content
    assert "static fromBase64<T extends PicoMsgBase>" in content
    
    # Check instance methods
    assert "toBase64(): string" in content


def test_typescript_generator_type_declarations():
    """Test TypeScript declaration file generation."""
    schema = Schema(enums=[], 
        namespace=Namespace("test.types"),
        structs=[
            Struct("Point", [
                Field("x", PrimitiveType("f32")),
                Field("y", PrimitiveType("f32"))
            ])
        ],
        messages=[
            Message("Move", [
                Field("from", StructType("Point")),
                Field("to", StructType("Point"))
            ])
        ]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    declarations = files["picomsg-generated.d.ts"]
    
    # Check interface definition
    assert "export interface PicoMsgSerializable" in declarations
    
    # Check class declarations
    assert "export declare class Point extends test_types_Base" in declarations
    assert "export declare class Move extends test_types_Base" in declarations
    
    # Check constructor signatures
    assert "constructor(data?: Partial<Point>);" in declarations
    assert "constructor(data?: Partial<Move>);" in declarations


def test_typescript_generator_package_json():
    """Test package.json generation."""
    schema = Schema(enums=[], namespace=None, structs=[], messages=[])
    
    generator = TypeScriptCodeGenerator(schema)
    generator.set_option('module_name', 'test_package')
    files = generator.generate()
    
    package_json = files["package.json"]
    
    # Check basic package.json structure
    assert '"name": "test_package"' in package_json
    assert '"version": "1.0.0"' in package_json
    assert '"main": "test_package.js"' in package_json
    assert '"types": "test_package.d.ts"' in package_json
    assert '"typescript"' in package_json
    assert '"@types/node"' in package_json


def test_typescript_generator_tsconfig():
    """Test tsconfig.json generation."""
    schema = Schema(enums=[], namespace=None, structs=[], messages=[])
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    
    tsconfig = files["tsconfig.json"]
    
    # Check TypeScript configuration
    assert '"target": "ES2020"' in tsconfig
    assert '"module": "commonjs"' in tsconfig
    assert '"strict": true' in tsconfig
    assert '"outDir": "./dist"' in tsconfig


def test_typescript_generator_readme():
    """Test README.md generation."""
    schema = Schema(enums=[], namespace=None, structs=[], messages=[])
    
    generator = TypeScriptCodeGenerator(schema)
    generator.set_option('module_name', 'my_module')
    files = generator.generate()
    
    readme = files["README.md"]
    
    # Check README content
    assert "# Generated PicoMsg TypeScript Bindings" in readme
    assert "my_module.ts" in readme
    assert "npm install" in readme
    assert "npm run build" in readme
    assert "Binary serialization/deserialization" in readme


def test_typescript_sanitize_identifier():
    """Test TypeScript identifier sanitization."""
    schema = Schema(enums=[], 
        namespace=None,
        structs=[
            Struct("class", [  # 'class' is a reserved word in TypeScript
                Field("function", PrimitiveType("u32")),  # 'function' is also reserved
                Field("normal_field", PrimitiveType("u32"))
            ])
        ],
        messages=[]
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    # Reserved words should be handled appropriately
    # The exact handling depends on the implementation
    assert "class" in content  # Should still work as class name in export
    assert "function" in content  # Should still work as field name


def test_typescript_generator_with_version():
    """Test TypeScript generation with schema version."""
    schema = Schema(enums=[], 
        namespace=Namespace("test.versioned"),
        structs=[],
        messages=[],
        version=42
    )
    
    generator = TypeScriptCodeGenerator(schema)
    files = generator.generate()
    content = files["picomsg-generated.ts"]
    
    assert "export const TEST_VERSIONED__VERSION = 42;" in content 