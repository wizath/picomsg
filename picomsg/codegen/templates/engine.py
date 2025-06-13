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
            template_dir = Path(__file__).parent
        
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
        
        # Additional Rust-specific filters
        self.env.filters['rust_type_with_namespace'] = self._rust_type_with_namespace
        self.env.filters['rust_read_expr'] = self._rust_read_expr
        self.env.filters['rust_write_expr'] = self._rust_write_expr
        self.env.filters['rust_enum_backing_type'] = self._rust_enum_backing_type
        self.env.filters['rust_enum_backing_read'] = self._rust_enum_backing_read
        self.env.filters['rust_enum_backing_write'] = self._rust_enum_backing_write
        
        # Additional Python-specific filters
        self.env.filters['python_default_value'] = self._python_default_value
        self.env.filters['python_struct_format'] = self._python_struct_format
        self.env.filters['python_type_size'] = self._python_type_size
        self.env.filters['python_to_dict_value'] = self._python_to_dict_value
        self.env.filters['python_to_dict_value_with_to_int'] = self._python_to_dict_value_with_to_int
        self.env.filters['python_from_dict_assignment'] = self._python_from_dict_assignment
        self.env.filters['python_enum_backing_type'] = self._python_enum_backing_type
        self.env.filters['python_enum_backing_size'] = self._python_enum_backing_size
        
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
        self.env.filters['python_enum_backing_type'] = lambda type_obj: self._python_enum_backing_type(type_obj, self._current_schema)
        self.env.filters['python_enum_backing_size'] = lambda type_obj: self._python_enum_backing_size(type_obj, self._current_schema)
        self.env.filters['python_default_value'] = lambda type_obj: self._python_default_value_with_schema(type_obj, self._current_schema)
        self.env.filters['python_default_value_with_schema'] = lambda type_obj, schema: self._python_default_value_with_schema(type_obj, schema)
        
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

    @staticmethod
    def _rust_type_with_namespace(type_obj, namespace_prefix: str) -> str:
        """Convert PicoMsg type to Rust type with namespace prefix."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            return type_obj.name  # Primitives don't need namespace
        elif isinstance(type_obj, StringType):
            return 'String'
        elif isinstance(type_obj, BytesType):
            return 'Vec<u8>'
        elif isinstance(type_obj, ArrayType):
            element_type = TemplateEngine._rust_type_with_namespace(type_obj.element_type, namespace_prefix)
            return f'Vec<{element_type}>'
        elif isinstance(type_obj, FixedArrayType):
            element_type = TemplateEngine._rust_type_with_namespace(type_obj.element_type, namespace_prefix)
            if isinstance(type_obj.element_type, PrimitiveType):
                return f'[{element_type}; {type_obj.size}]'
            else:
                return f'Vec<{element_type}>'  # Complex types use Vec
        elif isinstance(type_obj, (StructType, EnumType)):
            return f'{namespace_prefix}{type_obj.name}'
        
        return 'String'

    @staticmethod
    def _rust_read_expr(type_obj) -> str:
        """Generate Rust read expression for a primitive type."""
        from ...schema.ast import PrimitiveType
        
        if isinstance(type_obj, PrimitiveType):
            type_name = type_obj.name
            if type_name == 'bool':
                return 'reader.read_u8()? != 0'
            
            read_methods = {
                'u8': 'reader.read_u8()?',
                'i8': 'reader.read_i8()?',
                'u16': 'reader.read_u16::<LittleEndian>()?',
                'i16': 'reader.read_i16::<LittleEndian>()?',
                'u32': 'reader.read_u32::<LittleEndian>()?',
                'i32': 'reader.read_i32::<LittleEndian>()?',
                'u64': 'reader.read_u64::<LittleEndian>()?',
                'i64': 'reader.read_i64::<LittleEndian>()?',
                'f32': 'reader.read_f32::<LittleEndian>()?',
                'f64': 'reader.read_f64::<LittleEndian>()?',
            }
            return read_methods.get(type_name, 'reader.read_u8()?')
        
        return 'reader.read_u8()?'

    @staticmethod
    def _rust_write_expr(type_obj, var_name: str) -> str:
        """Generate Rust write expression for a primitive type."""
        from ...schema.ast import PrimitiveType
        
        if isinstance(type_obj, PrimitiveType):
            type_name = type_obj.name
            if type_name == 'bool':
                return f'writer.write_u8(if *{var_name} {{ 1 }} else {{ 0 }})?;'
            
            write_methods = {
                'u8': f'writer.write_u8(*{var_name})?;',
                'i8': f'writer.write_i8(*{var_name})?;',
                'u16': f'writer.write_u16::<LittleEndian>(*{var_name})?;',
                'i16': f'writer.write_i16::<LittleEndian>(*{var_name})?;',
                'u32': f'writer.write_u32::<LittleEndian>(*{var_name})?;',
                'i32': f'writer.write_i32::<LittleEndian>(*{var_name})?;',
                'u64': f'writer.write_u64::<LittleEndian>(*{var_name})?;',
                'i64': f'writer.write_i64::<LittleEndian>(*{var_name})?;',
                'f32': f'writer.write_f32::<LittleEndian>(*{var_name})?;',
                'f64': f'writer.write_f64::<LittleEndian>(*{var_name})?;',
            }
            return write_methods.get(type_name, f'writer.write_u8(*{var_name})?;')
        
        return f'writer.write_u8(*{var_name})?;'

    @staticmethod
    def _rust_enum_backing_type(type_obj) -> str:
        """Get the backing type for a Rust enum."""
        from ...schema.ast import EnumType
        
        if hasattr(type_obj, 'backing_type'):
            return type_obj.backing_type.name
        return 'u8'

    @staticmethod
    def _rust_enum_backing_read(type_obj) -> str:
        """Generate Rust read expression for an enum backing type."""
        from ...schema.ast import EnumType
        
        if hasattr(type_obj, 'backing_type'):
            backing_type = type_obj.backing_type.name
            read_methods = {
                'u8': 'reader.read_u8()?',
                'i8': 'reader.read_i8()?',
                'u16': 'reader.read_u16::<LittleEndian>()?',
                'i16': 'reader.read_i16::<LittleEndian>()?',
                'u32': 'reader.read_u32::<LittleEndian>()?',
                'i32': 'reader.read_i32::<LittleEndian>()?',
                'u64': 'reader.read_u64::<LittleEndian>()?',
                'i64': 'reader.read_i64::<LittleEndian>()?',
            }
            return read_methods.get(backing_type, 'reader.read_u8()?')
        return 'reader.read_u8()?'

    @staticmethod
    def _rust_enum_backing_write(type_obj, var_name: str) -> str:
        """Generate Rust write expression for an enum backing type."""
        from ...schema.ast import EnumType
        
        if hasattr(type_obj, 'backing_type'):
            backing_type = type_obj.backing_type.name
            write_methods = {
                'u8': f'writer.write_u8({var_name}.to_{backing_type}())?;',
                'i8': f'writer.write_i8({var_name}.to_{backing_type}())?;',
                'u16': f'writer.write_u16::<LittleEndian>({var_name}.to_{backing_type}())?;',
                'i16': f'writer.write_i16::<LittleEndian>({var_name}.to_{backing_type}())?;',
                'u32': f'writer.write_u32::<LittleEndian>({var_name}.to_{backing_type}())?;',
                'i32': f'writer.write_i32::<LittleEndian>({var_name}.to_{backing_type}())?;',
                'u64': f'writer.write_u64::<LittleEndian>({var_name}.to_{backing_type}())?;',
                'i64': f'writer.write_i64::<LittleEndian>({var_name}.to_{backing_type}())?;',
            }
            return write_methods.get(backing_type, f'writer.write_u8({var_name}.to_u8())?;')
        return f'writer.write_u8({var_name}.to_u8())?;'

    @staticmethod
    def _python_default_value(type_obj) -> str:
        """Get default value for Python type in constructor."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
                return '0'
            elif type_obj.name in ['f32', 'f64']:
                return '0.0'
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
    def _python_struct_format(type_obj) -> str:
        """Get Python struct format string for a type."""
        from ...schema.ast import PrimitiveType
        
        if isinstance(type_obj, PrimitiveType):
            format_map = {
                'u8': '<B',
                'i8': '<b',
                'u16': '<H',
                'i16': '<h',
                'u32': '<I',
                'i32': '<i',
                'u64': '<Q',
                'i64': '<q',
                'f32': '<f',
                'f64': '<d',
                'bool': '<B'
            }
            return format_map.get(type_obj.name, '<B')
        
        return '<B'

    @staticmethod
    def _python_type_size(type_obj) -> int:
        """Get size in bytes for a type."""
        from ...schema.ast import PrimitiveType
        
        if isinstance(type_obj, PrimitiveType):
            size_map = {
                'u8': 1,
                'i8': 1,
                'u16': 2,
                'i16': 2,
                'u32': 4,
                'i32': 4,
                'u64': 8,
                'i64': 8,
                'f32': 4,
                'f64': 8,
                'bool': 1
            }
            return size_map.get(type_obj.name, 1)
        
        return 1

    @staticmethod
    def _python_to_dict_value(field) -> str:
        """Generate Python expression to convert field to dict value."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        field_name = f'self._{field.name}'
        field_type = field.type
        
        if isinstance(field_type, (PrimitiveType, StringType)):
            return field_name
        elif isinstance(field_type, BytesType):
            return f'base64.b64encode({field_name}).decode("ascii")'
        elif isinstance(field_type, (ArrayType, FixedArrayType)):
            element_type = field_type.element_type
            if isinstance(element_type, (PrimitiveType, StringType)):
                return field_name
            elif isinstance(element_type, BytesType):
                return f'[base64.b64encode(item).decode("ascii") for item in {field_name}]'
            elif isinstance(element_type, StructType):
                return f'[item.to_dict() for item in {field_name}]'
            elif isinstance(element_type, EnumType):
                return f'[item.to_int() for item in {field_name}]'
        elif isinstance(field_type, StructType):
            return f'{field_name}.to_dict()'
        elif isinstance(field_type, EnumType):
            return f'{field_name}.to_int()'
        
        return field_name

    @staticmethod
    def _python_to_dict_value_with_to_int(field) -> str:
        """Generate Python expression to convert field to dict value with to_int."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        field_name = f'self._{field.name}'
        field_type = field.type
        
        if isinstance(field_type, (PrimitiveType, StringType)):
            return field_name
        elif isinstance(field_type, BytesType):
            return f'base64.b64encode({field_name}).decode("ascii")'
        elif isinstance(field_type, (ArrayType, FixedArrayType)):
            element_type = field_type.element_type
            if isinstance(element_type, (PrimitiveType, StringType)):
                return field_name
            elif isinstance(element_type, BytesType):
                return f'[base64.b64encode(item).decode("ascii") for item in {field_name}]'
            elif isinstance(element_type, StructType):
                return f'[item.to_dict() for item in {field_name}]'
            elif isinstance(element_type, EnumType):
                return f'[item.to_int() for item in {field_name}]'
        elif isinstance(field_type, StructType):
            return f'{field_name}.to_dict()'
        elif isinstance(field_type, EnumType):
            return f'{field_name}.to_int()'
        
        return field_name

    @staticmethod
    def _python_from_dict_assignment(field) -> str:
        """Generate Python assignment from dict for field."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        field_name = field.name
        field_type = field.type
        
        if isinstance(field_type, (PrimitiveType, StringType)):
            return f'instance._{field_name} = data.get("{field_name}", {TemplateEngine._python_default_value(field_type)})'
        elif isinstance(field_type, BytesType):
            return f'instance._{field_name} = base64.b64decode(data.get("{field_name}", "").encode("ascii")) if data.get("{field_name}") else b""'
        elif isinstance(field_type, (ArrayType, FixedArrayType)):
            element_type = field_type.element_type
            if isinstance(element_type, (PrimitiveType, StringType)):
                return f'instance._{field_name} = data.get("{field_name}", [])'
            elif isinstance(element_type, BytesType):
                return f'instance._{field_name} = [base64.b64decode(item.encode("ascii")) for item in data.get("{field_name}", [])]'
            elif isinstance(element_type, StructType):
                return f'instance._{field_name} = [{element_type.name}.from_dict(item) for item in data.get("{field_name}", [])]'
            elif isinstance(element_type, EnumType):
                return f'instance._{field_name} = [{element_type.name}.from_int(item) for item in data.get("{field_name}", [])]'
        elif isinstance(field_type, StructType):
            return f'instance._{field_name} = {field_type.name}.from_dict(data.get("{field_name}", {{}}))'
        elif isinstance(field_type, EnumType):
            return f'instance._{field_name} = {field_type.name}.from_int(data.get("{field_name}", 0))'
        
        return f'instance._{field_name} = data.get("{field_name}", None)'

    @staticmethod
    def _python_enum_backing_type(type_obj, schema) -> str:
        """Get the backing type for a Python enum."""
        from ...schema.ast import EnumType
        
        if isinstance(type_obj, EnumType) and schema:
            enum_def = schema.get_enum(type_obj.name)
            if enum_def:
                return TemplateEngine._python_struct_format(enum_def.backing_type)
        
        return '<B'  # Default to u8

    @staticmethod
    def _python_enum_backing_size(type_obj, schema) -> int:
        """Get the backing type size for a Python enum."""
        from ...schema.ast import EnumType
        
        if isinstance(type_obj, EnumType) and schema:
            enum_def = schema.get_enum(type_obj.name)
            if enum_def:
                return TemplateEngine._python_type_size(enum_def.backing_type)
        
        return 1  # Default to u8 size

    @staticmethod
    def _python_default_value_with_schema(type_obj, schema) -> str:
        """Get default value for Python type in constructor with schema context."""
        from ...schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
        
        if isinstance(type_obj, PrimitiveType):
            if type_obj.name in ['u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64']:
                return '0'
            elif type_obj.name in ['f32', 'f64']:
                return '0.0'
            elif type_obj.name == 'bool':
                return 'False'
        elif isinstance(type_obj, StringType):
            return '""'
        elif isinstance(type_obj, BytesType):
            return 'b""'
        elif isinstance(type_obj, ArrayType):
            return '[]'
        elif isinstance(type_obj, FixedArrayType):
            # For fixed arrays, create [default] * size
            element_default = TemplateEngine._python_default_value_with_schema(type_obj.element_type, schema)
            return f'[{element_default}] * {type_obj.size}'
        elif isinstance(type_obj, EnumType):
            # Get the first enum value as default
            if schema:
                enum_def = schema.get_enum(type_obj.name)
                if enum_def and enum_def.values:
                    # Get namespace prefix
                    namespace_prefix = ''
                    if schema.namespace:
                        parts = schema.namespace.name.split('.')
                        namespace_prefix = ''.join(part.capitalize() for part in parts)
                    enum_name = f'{namespace_prefix}{type_obj.name}' if namespace_prefix else type_obj.name
                    return f'{enum_name}.{enum_def.values[0].name}'
            return '0'
        elif isinstance(type_obj, StructType):
            # Get namespace prefix
            namespace_prefix = ''
            if schema and schema.namespace:
                parts = schema.namespace.name.split('.')
                namespace_prefix = ''.join(part.capitalize() for part in parts)
            struct_name = f'{namespace_prefix}{type_obj.name}' if namespace_prefix else type_obj.name
            return f'{struct_name}()'
        
        return 'None' 