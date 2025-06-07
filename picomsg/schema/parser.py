"""
Schema parser for PicoMsg .pico files.
"""

from typing import List, Optional, Union
from pathlib import Path

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from .ast import (
    Schema, Namespace, Struct, Message, Field, Type,
    PrimitiveType, StringType, BytesType, ArrayType, StructType
)


# Grammar for PicoMsg schema language
PICOMSG_GRAMMAR = r"""
    start: item*

    item: namespace_decl
        | struct_decl
        | message_decl

    namespace_decl: "namespace" QUALIFIED_NAME ";"

    struct_decl: "struct" NAME "{" field_decl* "}"
    message_decl: "message" NAME "{" field_decl* "}"

    field_decl: NAME ":" type ";"

    type: primitive_type
        | string_type
        | bytes_type
        | array_type
        | struct_type

    primitive_type: U8 | U16 | U32 | U64
                  | I8 | I16 | I32 | I64
                  | F32 | F64
    
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

    string_type: "string"
    bytes_type: "bytes"
    array_type: "[" type "]"
    struct_type: NAME

    QUALIFIED_NAME: NAME ("." NAME)*
    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/

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
        structs = []
        messages = []
        
        for item in items:
            if isinstance(item, Namespace):
                if namespace is not None:
                    raise ValueError("Multiple namespace declarations not allowed")
                namespace = item
            elif isinstance(item, Struct):
                structs.append(item)
            elif isinstance(item, Message):
                messages.append(item)
        
        return Schema(namespace=namespace, structs=structs, messages=messages)

    @v_args(inline=True)
    def item(self, content):
        return content

    @v_args(inline=True)
    def type(self, type_content):
        return type_content

    @v_args(inline=True)
    def namespace_decl(self, name):
        return Namespace(name=str(name))

    @v_args(inline=True)
    def struct_decl(self, name, *fields):
        return Struct(name=str(name), fields=list(fields))

    @v_args(inline=True)
    def message_decl(self, name, *fields):
        return Message(name=str(name), fields=list(fields))

    @v_args(inline=True)
    def field_decl(self, name, type_):
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
    def struct_type(self, name):
        return StructType(name=str(name))


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
        """Parse schema from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_string(content)
        except Exception as e:
            raise ValueError(f"Error reading schema file {path}: {e}") from e
    
    def _validate_schema(self, schema: Schema) -> None:
        """Validate the parsed schema for semantic correctness."""
        # Check that all struct type references are valid
        defined_types = set()
        
        # Collect all defined type names
        for struct in schema.structs:
            defined_types.add(struct.name)
        for message in schema.messages:
            defined_types.add(message.name)
        
        # Check all type references
        all_definitions = schema.structs + schema.messages
        for definition in all_definitions:
            self._validate_type_references(definition.fields, defined_types)
    
    def _validate_type_references(self, fields: List[Field], defined_types: set) -> None:
        """Validate that all type references in fields are valid."""
        for field in fields:
            self._validate_type_reference(field.type, defined_types)
    
    def _validate_type_reference(self, type_: Type, defined_types: set) -> None:
        """Validate a single type reference."""
        if isinstance(type_, StructType):
            if type_.name not in defined_types:
                raise ValueError(f"Undefined type: {type_.name}")
        elif isinstance(type_, ArrayType):
            self._validate_type_reference(type_.element_type, defined_types) 
