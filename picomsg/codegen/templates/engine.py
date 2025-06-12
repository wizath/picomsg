"""
Template engine for PicoMsg code generation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateEngine:
    """Template engine for generating code from Jinja2 templates."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize the template engine.
        
        Args:
            template_dir: Directory containing templates. If None, uses default.
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / 'templates'
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add custom filters
        self.env.filters['snake_case'] = self._snake_case
        self.env.filters['camel_case'] = self._camel_case
        self.env.filters['pascal_case'] = self._pascal_case
        self.env.filters['upper_snake_case'] = self._upper_snake_case
        self.env.filters['sanitize_identifier'] = self._sanitize_identifier
        
        # PicoMsg-specific filters
        self.env.filters['ts_type'] = self._ts_type
        self.env.filters['ts_default'] = self._ts_default
        self.env.filters['py_type'] = self._py_type
        self.env.filters['py_default'] = self._py_default
        self.env.filters['rust_type'] = self._rust_type
        self.env.filters['rust_default'] = self._rust_default
        
        # Schema-aware filters (these need to be set per render call)
        self._current_schema = None
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Variables to pass to the template
            
        Returns:
            Rendered template content
        """
        # Set current schema for schema-aware filters
        self._current_schema = context.get('schema')
        
        # Add schema-aware filters
        self.env.filters['ts_default_with_schema'] = lambda type_obj: self._ts_default(type_obj, self._current_schema)
        
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string with the given context.
        
        Args:
            template_string: Template content as string
            context: Variables to pass to the template
            
        Returns:
            Rendered template content
        """
        template = self.env.from_string(template_string)
        return template.render(**context)
    
    @staticmethod
    def _snake_case(name: str) -> str:
        """Convert name to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    @staticmethod
    def _camel_case(name: str) -> str:
        """Convert name to camelCase."""
        components = name.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    @staticmethod
    def _pascal_case(name: str) -> str:
        """Convert name to PascalCase."""
        return ''.join(word.capitalize() for word in name.split('_'))
    
    @staticmethod
    def _upper_snake_case(name: str) -> str:
        """Convert name to UPPER_SNAKE_CASE."""
        return TemplateEngine._snake_case(name).upper()
    
    @staticmethod
    def _sanitize_identifier(name: str, language: str = 'python') -> str:
        """Sanitize identifier for target language."""
        reserved_words = {
            'python': {'class', 'def', 'if', 'else', 'for', 'while', 'import', 'from', 'as', 'try', 'except', 'finally', 'with', 'lambda', 'global', 'nonlocal'},
            'rust': {'fn', 'let', 'mut', 'const', 'static', 'if', 'else', 'match', 'for', 'while', 'loop', 'break', 'continue', 'return', 'struct', 'enum', 'impl', 'trait', 'mod', 'pub', 'use', 'crate', 'super', 'self', 'Self'},
            'typescript': {'class', 'interface', 'type', 'enum', 'namespace', 'module', 'export', 'import', 'function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'try', 'catch', 'finally', 'throw', 'return'},
            'c': {'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while'}
        }
        
        if name in reserved_words.get(language, set()):
            return f'{name}_'
        return name
    
    @staticmethod
    def _ts_type(type_obj) -> str:
        """Convert PicoMsg type to TypeScript type."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64', 'f32', 'f64']:
                return 'number'
            elif type_obj.name == 'bool':
                return 'boolean'
        elif isinstance(type_obj, StringType):
            return 'string'
        elif isinstance(type_obj, BytesType):
            return 'Uint8Array'
        elif isinstance(type_obj, (ArrayType, FixedArrayType)):
            element_type = TemplateEngine._ts_type(type_obj.element_type)
            return f'{element_type}[]'
        elif isinstance(type_obj, (StructType, EnumType)):
            return type_obj.name
        
        return 'any'
    
    @staticmethod
    def _ts_default(type_obj, schema=None) -> str:
        """Get default value for TypeScript type."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64', 'f32', 'f64']:
                return '0'
            elif type_obj.name == 'bool':
                return 'false'
        elif isinstance(type_obj, StringType):
            return '""'
        elif isinstance(type_obj, BytesType):
            return 'new Uint8Array(0)'
        elif isinstance(type_obj, (ArrayType, FixedArrayType)):
            return '[]'
        elif isinstance(type_obj, EnumType):
            # For enums, use the first enum value if available
            if schema:
                for enum in schema.enums:
                    if enum.name == type_obj.name and enum.values:
                        return f'{type_obj.name}.{enum.values[0].name}'
            return '0'
        elif isinstance(type_obj, StructType):
            return f'new {type_obj.name}()'
        
        return 'null'
    
    @staticmethod
    def _py_type(type_obj) -> str:
        """Convert PicoMsg type to Python type hint."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
                return 'int'
            elif type_obj.name in ['f32', 'f64']:
                return 'float'
            elif type_obj.name == 'bool':
                return 'bool'
        elif isinstance(type_obj, StringType):
            return 'str'
        elif isinstance(type_obj, BytesType):
            return 'bytes'
        elif isinstance(type_obj, (ArrayType, FixedArrayType)):
            element_type = TemplateEngine._py_type(type_obj.element_type)
            return f'List[{element_type}]'
        elif isinstance(type_obj, (StructType, EnumType)):
            return type_obj.name
        
        return 'Any'
    
    @staticmethod
    def _py_default(type_obj) -> str:
        """Get default value for Python type."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64', 'f32', 'f64']:
                return '0'
            elif type_obj.name == 'bool':
                return 'False'
        elif isinstance(type_obj, StringType):
            return '""'
        elif isinstance(type_obj, BytesType):
            return 'b""'
        elif isinstance(type_obj, (ArrayType, FixedArrayType)):
            return '[]'
        elif isinstance(type_obj, EnumType):
            return '0'
        elif isinstance(type_obj, StructType):
            return f'{type_obj.name}()'
        
        return 'None'
    
    @staticmethod
    def _rust_type(type_obj) -> str:
        """Convert PicoMsg type to Rust type."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            return type_obj.name  # Rust types match PicoMsg primitive names
        elif isinstance(type_obj, StringType):
            return 'String'
        elif isinstance(type_obj, BytesType):
            return 'Vec<u8>'
        elif isinstance(type_obj, ArrayType):
            element_type = TemplateEngine._rust_type(type_obj.element_type)
            return f'Vec<{element_type}>'
        elif isinstance(type_obj, FixedArrayType):
            element_type = TemplateEngine._rust_type(type_obj.element_type)
            return f'[{element_type}; {type_obj.size}]'
        elif isinstance(type_obj, (StructType, EnumType)):
            return type_obj.name
        
        return 'String'
    
    @staticmethod
    def _rust_default(type_obj) -> str:
        """Get default value for Rust type."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
                return '0'
            elif type_obj.name in ['f32', 'f64']:
                return '0.0'
            elif type_obj.name == 'bool':
                return 'false'
        elif isinstance(type_obj, StringType):
            return 'String::new()'
        elif isinstance(type_obj, BytesType):
            return 'Vec::new()'
        elif isinstance(type_obj, ArrayType):
            return 'Vec::new()'
        elif isinstance(type_obj, FixedArrayType):
            element_default = TemplateEngine._rust_default(type_obj.element_type)
            return f'[{element_default}; {type_obj.size}]'
        elif isinstance(type_obj, (StructType, EnumType)):
            return f'{type_obj.name}::default()'
        
        return 'Default::default()' 