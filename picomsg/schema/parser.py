"""
Schema parser for PicoMsg .pico files.
"""

from typing import List, Optional, Union
from pathlib import Path

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from .ast import (
    Schema, Namespace, Enum, EnumValue, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, UserType, StructType, EnumType
)


# Grammar for PicoMsg schema language
PICOMSG_GRAMMAR = r"""
    start: item*

    item: include_decl
        | namespace_decl
        | version_decl
        | enum_decl
        | struct_decl
        | message_decl

    include_decl: "include" STRING ";"
    namespace_decl: "namespace" QUALIFIED_NAME ";"
    version_decl: "version" NUMBER ";"

    enum_decl: "enum" NAME ":" primitive_type "{" enum_value_decl* "}"
    enum_value_decl: NAME ["=" (NUMBER | HEX_NUMBER)] ","?

    struct_decl: "struct" NAME "{" field_decl* "}"
    message_decl: "message" NAME "{" field_decl* "}"

    field_decl: NAME ":" type ["=" default_value] ";"
    
    default_value: NUMBER
                 | HEX_NUMBER
                 | NEGATIVE_NUMBER
                 | FLOAT
                 | NEGATIVE_FLOAT
                 | STRING
                 | BOOL_TRUE
                 | BOOL_FALSE
                 | NULL

    type: primitive_type
        | string_type
        | bytes_type
        | array_type
        | fixed_array_type
        | user_type

    primitive_type: U8 | U16 | U32 | U64
                  | I8 | I16 | I32 | I64
                  | F32 | F64
                  | BOOL
    
    U8: "u8"
    U16: "u16"
    U32: "u32"
    U64: "u64"
    I8: "i8"
    I16: "i16"
    I32: "i32"
    I64: "i64"
    F32: "f32"
    F64: "f64"
    BOOL: "bool"

    string_type: "string"
    bytes_type: "bytes"
    array_type: "[" type "]"
    fixed_array_type: "[" type ":" NUMBER "]"
    user_type: NAME

    QUALIFIED_NAME: NAME ("." NAME)*
    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /[0-9]+/
    HEX_NUMBER: /0x[0-9a-fA-F]+/
    NEGATIVE_NUMBER: /-[0-9]+/
    FLOAT: /[0-9]+\.[0-9]+/
    NEGATIVE_FLOAT: /-[0-9]+\.[0-9]+/
    STRING: /"([^"\\]|\\.)*"/
    BOOL_TRUE: "true"
    BOOL_FALSE: "false"
    NULL: "null"

    %import common.WS
    %import common.CPP_COMMENT
    %import common.C_COMMENT
    %ignore WS
    %ignore CPP_COMMENT
    %ignore C_COMMENT
"""


class SchemaTransformer(Transformer):
    """Transform parsed Lark tree into PicoMsg AST."""

    @v_args(inline=True)
    def start(self, *items):
        namespace = None
        version = None
        enums = []
        structs = []
        messages = []
        includes = []
        
        for item in items:
            if isinstance(item, str) and item.startswith('include:'):
                includes.append(item[8:])  # Remove 'include:' prefix
            elif isinstance(item, Namespace):
                if namespace is not None:
                    raise ValueError("Multiple namespace declarations not allowed")
                namespace = item
            elif isinstance(item, int):  # Version number
                if version is not None:
                    raise ValueError("Multiple version declarations not allowed")
                version = item
            elif isinstance(item, Enum):
                enums.append(item)
            elif isinstance(item, Struct):
                structs.append(item)
            elif isinstance(item, Message):
                messages.append(item)
        
        return Schema(namespace=namespace, enums=enums, structs=structs, messages=messages, version=version, includes=includes)

    @v_args(inline=True)
    def item(self, content):
        return content

    @v_args(inline=True)
    def type(self, type_content):
        return type_content

    @v_args(inline=True)
    def include_decl(self, path):
        # Strip quotes from path string if present
        path_str = str(path)
        if path_str.startswith('"') and path_str.endswith('"'):
            path_str = path_str[1:-1]
        return f'include:{path_str}'

    @v_args(inline=True)
    def namespace_decl(self, name):
        return Namespace(name=str(name))

    @v_args(inline=True)
    def version_decl(self, version):
        return int(version)

    @v_args(inline=True)
    def enum_decl(self, name, backing_type, *values):
        return Enum(name=str(name), backing_type=backing_type, values=list(values))

    @v_args(inline=True)
    def enum_value_decl(self, name, value=None):
        return EnumValue(name=str(name), value=int(value) if value is not None else None)

    @v_args(inline=True)
    def struct_decl(self, name, *fields):
        return Struct(name=str(name), fields=list(fields))

    @v_args(inline=True)
    def message_decl(self, name, *fields):
        return Message(name=str(name), fields=list(fields))

    def field_decl(self, children):
        """Handle field declaration with optional default value."""
        name, type_ = children[0], children[1]
        
        # Check if we have an explicit default value (including explicit null)
        if len(children) > 2 and children[2] is not None:
            default_value = children[2]
            
            # Convert ExplicitNull back to None but mark as having explicit default
            if hasattr(default_value, '__class__') and default_value.__class__.__name__ == 'ExplicitNull':
                default_value = None
            
            field = Field(name=str(name), type=type_, default_value=default_value)
            field._has_explicit_default = True
            # Validate the default value after setting the flag
            field._validate_default_value()
            return field
        else:
            # No default value specified
            return Field(name=str(name), type=type_)

    @v_args(inline=True)
    def primitive_type(self, type_token):
        return PrimitiveType(name=str(type_token))

    @v_args(inline=True)
    def string_type(self):
        return StringType()

    @v_args(inline=True)
    def bytes_type(self):
        return BytesType()

    @v_args(inline=True)
    def array_type(self, element_type):
        return ArrayType(element_type=element_type)

    @v_args(inline=True)
    def fixed_array_type(self, element_type, size):
        return FixedArrayType(element_type=element_type, size=int(size))

    @v_args(inline=True)
    def user_type(self, name):
        # Return a generic user type that will be resolved during validation
        return UserType(name=str(name))
    
    @v_args(inline=True)
    def default_value(self, value):
        return value
    
    def NUMBER(self, token):
        return int(token)
    
    def HEX_NUMBER(self, token):
        return int(token, 16)
    
    def NEGATIVE_NUMBER(self, token):
        return int(token)
    
    def FLOAT(self, token):
        return float(token)
    
    def NEGATIVE_FLOAT(self, token):
        return float(token)
    
    def STRING(self, token):
        # Remove quotes and handle escape sequences
        return str(token)[1:-1].encode().decode('unicode_escape')
    
    def BOOL_TRUE(self, token):
        return True
    
    def BOOL_FALSE(self, token):
        return False
    
    def NULL(self, token):
        # Use a special marker to distinguish explicit null from missing default
        class ExplicitNull:
            def __repr__(self):
                return "ExplicitNull()"
        return ExplicitNull()


class SchemaParser:
    """Parser for PicoMsg schema files."""
    
    def __init__(self):
        self._parser = Lark(PICOMSG_GRAMMAR, parser='lalr')
        self._transformer = SchemaTransformer()
    
    def parse_string(self, schema_text: str) -> Schema:
        """Parse schema from string."""
        try:
            tree = self._parser.parse(schema_text)
            schema = self._transformer.transform(tree)
            self._validate_schema(schema)
            return schema
        except LarkError as e:
            raise ValueError(f"Parse error: {e}") from e
    
    def parse_file(self, file_path: Union[str, Path]) -> Schema:
        """Parse schema from file with include resolution."""
        return self._parse_file_with_includes(file_path, set())
    
    def _parse_file_with_includes(self, file_path: Union[str, Path], visited: set) -> Schema:
        """Parse schema from file and recursively resolve includes."""
        path = Path(file_path).resolve()
        
        if str(path) in visited:
            raise ValueError(f"Circular dependency detected: {path}")
        
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")
        
        visited.add(str(path))
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the current file without validation first
            try:
                tree = self._parser.parse(content)
                schema = self._transformer.transform(tree)
            except LarkError as e:
                raise ValueError(f"Parse error: {e}") from e
            
            # Process includes
            if schema.includes:
                for include_path in schema.includes:
                    # Resolve include path relative to current file
                    if not Path(include_path).is_absolute():
                        include_path = path.parent / include_path
                    
                    # Parse included file
                    included_schema = self._parse_file_with_includes(include_path, visited.copy())
                    
                    # Merge included schema into current schema
                    schema = self._merge_schemas(schema, included_schema)
            
            # Validate merged schema
            self._validate_schema(schema)
            
            visited.remove(str(path))
            return schema
            
        except Exception as e:
            visited.discard(str(path))
            raise ValueError(f"Error reading schema file {path}: {e}") from e
    
    def _merge_schemas(self, main_schema: Schema, included_schema: Schema) -> Schema:
        """Merge an included schema into the main schema."""
        # Check for naming conflicts
        main_names = set()
        for enum in main_schema.enums:
            main_names.add(enum.name)
        for struct in main_schema.structs:
            main_names.add(struct.name)
        for message in main_schema.messages:
            main_names.add(message.name)
        
        included_names = set()
        for enum in included_schema.enums:
            if enum.name in main_names:
                raise ValueError(f"Type name conflict: '{enum.name}' already defined")
            included_names.add(enum.name)
        for struct in included_schema.structs:
            if struct.name in main_names or struct.name in included_names:
                raise ValueError(f"Type name conflict: '{struct.name}' already defined")
            included_names.add(struct.name)
        for message in included_schema.messages:
            if message.name in main_names or message.name in included_names:
                raise ValueError(f"Type name conflict: '{message.name}' already defined")
            included_names.add(message.name)
        
        # Create merged schema
        return Schema(
            namespace=main_schema.namespace,  # Keep main namespace
            enums=main_schema.enums + included_schema.enums,
            structs=main_schema.structs + included_schema.structs,
            messages=main_schema.messages + included_schema.messages,
            version=main_schema.version,  # Keep main version
            includes=main_schema.includes  # Keep original includes list
        )
    
    def _validate_schema(self, schema: Schema) -> None:
        """Validate the parsed schema for semantic correctness."""
        # Check that all type references are valid
        defined_types = set()
        
        # Collect all defined type names
        for enum in schema.enums:
            defined_types.add(enum.name)
        for struct in schema.structs:
            defined_types.add(struct.name)
        for message in schema.messages:
            defined_types.add(message.name)
        
        # Check all type references and resolve UserTypes
        all_definitions = schema.structs + schema.messages
        for definition in all_definitions:
            self._validate_and_resolve_type_references(definition.fields, schema)
    
    def _validate_and_resolve_type_references(self, fields: List[Field], schema: Schema) -> None:
        """Validate and resolve all type references in fields."""
        for field in fields:
            field.type = self._resolve_type_reference(field.type, schema)
    
    def _resolve_type_reference(self, type_: Type, schema: Schema) -> Type:
        """Resolve a type reference, converting UserType to StructType or EnumType."""
        if isinstance(type_, UserType):
            # Check if it's an enum
            if schema.get_enum(type_.name):
                return EnumType(name=type_.name)
            # Check if it's a struct
            elif schema.get_struct(type_.name):
                return StructType(name=type_.name)
            # Check if it's a message
            elif schema.get_message(type_.name):
                return StructType(name=type_.name)  # Messages are treated like structs for typing
            else:
                raise ValueError(f"Undefined type: {type_.name}")
        elif isinstance(type_, ArrayType):
            type_.element_type = self._resolve_type_reference(type_.element_type, schema)
            return type_
        elif isinstance(type_, FixedArrayType):
            type_.element_type = self._resolve_type_reference(type_.element_type, schema)
            return type_
        else:
            return type_
    
    def _validate_type_references(self, fields: List[Field], defined_types: set) -> None:
        """Validate that all type references in fields are valid."""
        for field in fields:
            self._validate_type_reference(field.type, defined_types)
    
    def _validate_type_reference(self, type_: Type, defined_types: set) -> None:
        """Validate a single type reference."""
        if isinstance(type_, (StructType, EnumType)):
            if type_.name not in defined_types:
                raise ValueError(f"Undefined type: {type_.name}")
        elif isinstance(type_, ArrayType):
            self._validate_type_reference(type_.element_type, defined_types)
        elif isinstance(type_, FixedArrayType):
            self._validate_type_reference(type_.element_type, defined_types) 
