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

    def _get_namespace_prefix_capitalized(self) -> str:
        """Get namespace prefix with PascalCase for TypeScript."""
        if not self.schema.namespace:
            return ''

        parts = self.schema.namespace.name.split('.')
        prefix = ''.join(part.capitalize() for part in parts)
        return prefix if prefix else ''
    
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
        
        return files
    
    def _build_context(self, module_name: str) -> Dict[str, Any]:
        """Build template context with all necessary data."""
        namespace_prefix = self._get_namespace_prefix_capitalized()

        return {
            'schema': self.schema,
            'namespace': self.schema.namespace,
            'module_name': module_name,
            'namespace_prefix': namespace_prefix,
            'base_class': f'{namespace_prefix}Base' if namespace_prefix else 'PicoMsgBase',
            'error_class': f'{namespace_prefix}Error' if namespace_prefix else 'PicoMsgError',
            'const_prefix': namespace_prefix.rstrip('_').upper() + '_' if namespace_prefix else '',
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
        namespace_prefix = context['namespace_prefix']
        for enum in self.schema.enums:
            lines.extend([
                f'export declare enum {namespace_prefix}{enum.name} {{',
                *[f'  {value.name} = {value.value},' for value in enum.values],
                '}',
                '',
            ])

        # Generate struct declarations
        for struct in self.schema.structs:
            lines.extend([
                f'export declare class {namespace_prefix}{struct.name} extends {base_name} {{',
                *[f'  {field.name}: {self.template_engine._ts_type(field.type)};' for field in struct.fields],
                f'  constructor(data?: Partial<{namespace_prefix}{struct.name}>);',
                '}',
                '',
            ])

        # Generate message declarations
        for message in self.schema.messages:
            lines.extend([
                f'export declare class {namespace_prefix}{message.name} extends {base_name} {{',
                *[f'  {field.name}: {self.template_engine._ts_type(field.type)};' for field in message.fields],
                f'  constructor(data?: Partial<{namespace_prefix}{message.name}>);',
                '}',
                '',
            ])
        
        return '\n'.join(lines)
    
 