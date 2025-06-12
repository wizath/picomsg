"""
Template-based TypeScript code generator for PicoMsg.
"""

from typing import Dict, Any
from pathlib import Path
from .base import CodeGenerator
from .templates import TemplateEngine


class TypeScriptCodeGenerator(CodeGenerator):
    """Generate TypeScript code using Jinja2 templates."""
    
    def __init__(self, schema):
        super().__init__(schema)
        self.template_engine = TemplateEngine()
        self.type_id_counter = 1
    
    def generate(self) -> Dict[str, str]:
        """Generate TypeScript module files using templates."""
        module_name = self.get_option('module_name', 'picomsg-generated')
        
        # Prepare template context
        context = self._build_context(module_name)
        
        files = {}
        files[f"{module_name}.ts"] = self.template_engine.render(
            'typescript/module.ts.j2', context
        )
        files[f"{module_name}.d.ts"] = self._generate_declarations(context)
        files["package.json"] = self._generate_package_json(module_name)
        files["tsconfig.json"] = self._generate_tsconfig()
        files["README.md"] = self._generate_readme(module_name)
        
        return files
    
    def _build_context(self, module_name: str) -> Dict[str, Any]:
        """Build template context with all necessary data."""
        namespace_prefix = self._get_namespace_prefix()
        
        return {
            'schema': self.schema,
            'namespace': self.schema.namespace,
            'module_name': module_name,
            'namespace_prefix': namespace_prefix,
            'base_class': f'{namespace_prefix}Base' if namespace_prefix else 'PicoMsgBase',
            'error_class': f'{namespace_prefix}Error' if namespace_prefix else 'PicoMsgError',
            'const_prefix': namespace_prefix.upper() + '_' if namespace_prefix else '',
            'version': self.schema.version or 1,
            'message_type_ids': self._generate_message_type_ids(),
        }
    
    def _generate_message_type_ids(self) -> Dict[str, int]:
        """Generate type IDs for messages."""
        type_ids = {}
        for message in self.schema.messages:
            type_ids[message.name] = self.type_id_counter
            self.type_id_counter += 1
        return type_ids
    
    def _generate_declarations(self, context: Dict[str, Any]) -> str:
        """Generate TypeScript declaration file."""
        base_name = context['base_class']
        
        lines = [
            '/**',
            ' * Generated PicoMsg TypeScript type declarations',
            ' * This file is auto-generated. Do not edit manually.',
            ' */',
            '',
            'export interface PicoMsgSerializable {',
            '  toBytes(): Uint8Array;',
            '  fromBytes(data: Uint8Array): void;',
            '  toJSON(): any;',
            '  fromJSON(data: any): void;',
            '}',
            '',
            f'export declare abstract class {base_name} implements PicoMsgSerializable {{',
            '  abstract toBytes(): Uint8Array;',
            '  abstract fromBytes(data: Uint8Array): void;',
            '  abstract toJSON(): any;',
            '  abstract fromJSON(data: any): void;',
            '  toBase64(): string;',
            f'  static fromBytes<T extends {base_name}>(this: new() => T, data: Uint8Array): T;',
            f'  static fromJSON<T extends {base_name}>(this: new() => T, data: any): T;',
            f'  static fromBase64<T extends {base_name}>(this: new() => T, base64: string): T;',
            '}',
            '',
        ]
        
        # Generate enum declarations
        for enum in self.schema.enums:
            lines.extend([
                f'export declare enum {enum.name} {{',
                *[f'  {value.name} = {value.value},' for value in enum.values],
                '}',
                '',
            ])
        
        # Generate struct declarations
        for struct in self.schema.structs:
            lines.extend([
                f'export declare class {struct.name} extends {base_name} {{',
                *[f'  {field.name}: {self.template_engine._ts_type(field.type)};' for field in struct.fields],
                f'  constructor(data?: Partial<{struct.name}>);',
                '}',
                '',
            ])
        
        # Generate message declarations
        for message in self.schema.messages:
            lines.extend([
                f'export declare class {message.name} extends {base_name} {{',
                *[f'  {field.name}: {self.template_engine._ts_type(field.type)};' for field in message.fields],
                f'  constructor(data?: Partial<{message.name}>);',
                '}',
                '',
            ])
        
        return '\n'.join(lines)
    
    def _generate_package_json(self, module_name: str) -> str:
        """Generate package.json for the TypeScript module."""
        return f'''{{
  "name": "{module_name}",
  "version": "1.0.0",
  "description": "Generated PicoMsg TypeScript bindings",
  "main": "{module_name}.js",
  "types": "{module_name}.d.ts",
  "scripts": {{
    "build": "tsc",
    "test": "jest"
  }},
  "devDependencies": {{
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }},
  "keywords": ["picomsg", "serialization", "binary"],
  "license": "MIT"
}}'''
    
    def _generate_tsconfig(self) -> str:
        """Generate TypeScript configuration file."""
        return '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020", "DOM"],
    "outDir": "./dist",
    "rootDir": "./",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": [
    "*.ts"
  ],
  "exclude": [
    "node_modules",
    "dist"
  ]
}'''
    
    def _generate_readme(self, module_name: str) -> str:
        """Generate README file."""
        return f'''# Generated PicoMsg TypeScript Bindings

This directory contains auto-generated TypeScript bindings for PicoMsg schema.

## Files

- `{module_name}.ts` - Main TypeScript implementation
- `{module_name}.d.ts` - TypeScript type declarations
- `package.json` - NPM package configuration
- `tsconfig.json` - TypeScript compiler configuration

## Usage

### Installation

```bash
npm install
```

### Building

```bash
npm run build
```

### Basic Usage

```typescript
import {{ /* your types */ }} from './{module_name}';

// Create instances with type-safe constructors
const instance = new YourType({{
  field1: value1,
  field2: value2
}});

// Serialize to binary
const bytes = instance.toBytes();
console.log('Serialized bytes:', bytes);

// Deserialize from binary
const decoded = new YourType();
decoded.fromBytes(bytes);
console.log('Decoded instance:', decoded);

// JSON serialization
const json = instance.toJSON();
console.log('JSON:', JSON.stringify(json, null, 2));

// Base64 encoding
const base64 = instance.toBase64();
console.log('Base64:', base64);
```

## Type Safety

The generated TypeScript code provides full type safety:

- All fields are properly typed
- Constructors accept partial objects for easy initialization
- Serialization methods are type-safe
- Enum values are properly typed

## Features

- Binary serialization/deserialization
- JSON serialization/deserialization
- Base64 encoding/decoding
- Type-safe constructors
- Full TypeScript type definitions
- Support for all PicoMsg types:
  - Primitive types (u8, u16, u32, u64, i8, i16, i32, i64, f32, f64, bool)
  - Strings and bytes
  - Arrays and fixed arrays
  - Structs and messages
  - Enums
''' 