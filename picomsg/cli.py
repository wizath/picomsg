"""
Command-line interface for PicoMsg.
"""

import click
from pathlib import Path
from typing import Optional

from .schema.parser import SchemaParser
from .codegen.c import CCodeGenerator
from .codegen.rust import RustCodeGenerator
from .codegen.python import PythonCodeGenerator
from .json.cli_integration import add_json_commands


@click.group()
@click.version_option()
def main():
    """PicoMsg - Lightweight binary serialization format."""
    pass


# Add JSON commands as a subgroup
@main.group()
def json():
    """JSON conversion and validation commands."""
    pass


@json.command('validate')
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
@click.argument('json_file', type=click.Path(exists=True, path_type=Path))
@click.argument('type_name')
@click.option('--streaming', is_flag=True, help='Use streaming validation for large JSON arrays')
def json_validate(schema_file: Path, json_file: Path, type_name: str, streaming: bool):
    """Validate JSON data against a PicoMsg schema."""
    try:
        from .json import validate_json_file
        from .json.streaming import stream_validate_json_array
        
        if streaming:
            result = stream_validate_json_array(json_file, type_name, schema_file)
            if result:
                click.echo(f"✓ JSON array validation passed for type '{type_name}'")
            else:
                click.echo(f"✗ JSON array validation failed for type '{type_name}'")
                raise click.ClickException("Validation failed")
        else:
            result = validate_json_file(json_file, type_name, schema_file)
            if result:
                click.echo(f"✓ JSON validation passed for type '{type_name}'")
            else:
                click.echo(f"✗ JSON validation failed for type '{type_name}'")
                raise click.ClickException("Validation failed")
    
    except Exception as e:
        raise click.ClickException(f"Error: {e}")


@json.command('pretty')
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
@click.argument('json_file', type=click.Path(exists=True, path_type=Path))
@click.argument('type_name')
@click.option('-o', '--output', type=click.Path(path_type=Path), help='Output file (default: stdout)')
@click.option('--indent', type=int, default=2, help='Indentation level (default: 2)')
def json_pretty(schema_file: Path, json_file: Path, type_name: str, output: Optional[Path], indent: int):
    """Pretty-print JSON with schema annotations."""
    try:
        from .json import pretty_print_json_file
        
        formatted = pretty_print_json_file(json_file, type_name, schema_file, output)
        
        if not output:
            click.echo(formatted)
        else:
            click.echo(f"✓ Pretty-printed JSON written to {output}")
    
    except Exception as e:
        raise click.ClickException(f"Error: {e}")


@json.command('convert')
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--from-format', type=click.Choice(['array', 'lines']), default='array', help='Input format')
@click.option('--to-format', type=click.Choice(['array', 'lines']), default='lines', help='Output format')
@click.option('--schema', type=click.Path(exists=True, path_type=Path), help='Optional schema file for validation')
@click.option('--type', 'type_name', help='Schema type name (required if --schema is provided)')
@click.option('--no-validate', is_flag=True, help='Skip validation during conversion')
@click.option('--pretty', is_flag=True, help='Pretty-print output (only for array format)')
def json_convert(input_file: Path, output_file: Path, from_format: str, to_format: str, 
                schema: Optional[Path], type_name: Optional[str], no_validate: bool, pretty: bool):
    """Convert between JSON formats (array ↔ lines)."""
    try:
        from .json.streaming import stream_convert_json_lines_to_array, stream_convert_json_array_to_lines
        
        if from_format == 'lines' and to_format == 'array':
            stream_convert_json_lines_to_array(
                input_file, output_file, type_name if schema else None,
                schema if schema else None, 2 if pretty else None
            )
        elif from_format == 'array' and to_format == 'lines':
            stream_convert_json_array_to_lines(
                input_file, output_file, type_name if schema else None,
                schema if schema else None
            )
        else:
            raise click.ClickException(f"Conversion from {from_format} to {to_format} not supported")
        
        click.echo(f"✓ Converted {input_file} from {from_format} to {to_format} format")
        click.echo(f"  Output written to {output_file}")
    
    except Exception as e:
        raise click.ClickException(f"Error: {e}")


@json.command('codegen')
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
@click.option('--lang', type=click.Choice(['rust', 'python']), required=True, help='Target language')
@click.option('-o', '--output', type=click.Path(path_type=Path), required=True, help='Output file or directory')
@click.option('--module-name', default='picomsg_types', help='Module name')
@click.option('--package-name', help='Package name for Rust (default: derived from module-name)')
def json_codegen(schema_file: Path, lang: str, output: Path, module_name: str, package_name: Optional[str]):
    """Generate enhanced code with JSON support."""
    try:
        if lang == 'rust':
            from .json.rust_integration import enhance_rust_json_support, generate_rust_json_cargo_toml
            
            enhance_rust_json_support(schema_file, output, module_name)
            
            if output.is_dir():
                pkg_name = package_name or module_name.replace('_', '-')
                generate_rust_json_cargo_toml(output, pkg_name)
                click.echo(f"✓ Enhanced Rust code with JSON support generated in {output}")
                click.echo(f"  - Generated {output / 'lib.rs'}")
                click.echo(f"  - Generated {output / 'Cargo.toml'}")
            else:
                click.echo(f"✓ Enhanced Rust code with JSON support generated: {output}")
        
        elif lang == 'python':
            from .json.python_integration import enhance_python_json_support
            
            enhance_python_json_support(schema_file, output, module_name)
            click.echo(f"✓ Enhanced Python code with JSON support generated: {output}")
    
    except Exception as e:
        raise click.ClickException(f"Error generating enhanced code: {e}")


@json.command('info')
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
@click.option('--format', type=click.Choice(['text', 'json']), default='text', help='Output format')
def json_info(schema_file: Path, format: str):
    """Show JSON schema information."""
    try:
        import json as json_module
        
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        # Collect schema information
        info = {
            'schema_file': str(schema_file),
            'enums': [],
            'structs': [],
            'messages': [],
            'total_types': len(schema.enums) + len(schema.structs) + len(schema.messages)
        }
        
        for enum in schema.enums:
            enum_info = {
                'name': enum.name,
                'backing_type': enum.backing_type.name,
                'values': [{'name': value.name, 'value': value.value} for value in enum.values]
            }
            info['enums'].append(enum_info)
        
        for struct in schema.structs:
            struct_info = {
                'name': struct.name,
                'fields': [{'name': field.name, 'type': str(field.type)} for field in struct.fields]
            }
            info['structs'].append(struct_info)
        
        for message in schema.messages:
            message_info = {
                'name': message.name,
                'fields': [{'name': field.name, 'type': str(field.type)} for field in message.fields]
            }
            info['messages'].append(message_info)
        
        if format == 'json':
            click.echo(json_module.dumps(info, indent=2))
        else:
            click.echo(f"Schema: {schema_file}")
            click.echo(f"Total types: {info['total_types']}")
            click.echo()
            
            if info['enums']:
                click.echo("Enums:")
                for enum in info['enums']:
                    click.echo(f"  {enum['name']} : {enum['backing_type']}")
                    for value in enum['values']:
                        click.echo(f"    {value['name']} = {value['value']}")
                click.echo()
            
            if info['structs']:
                click.echo("Structs:")
                for struct in info['structs']:
                    click.echo(f"  {struct['name']}")
                    for field in struct['fields']:
                        click.echo(f"    {field['name']}: {field['type']}")
                click.echo()
            
            if info['messages']:
                click.echo("Messages:")
                for message in info['messages']:
                    click.echo(f"  {message['name']}")
                    for field in message['fields']:
                        click.echo(f"    {field['name']}: {field['type']}")
    
    except Exception as e:
        raise click.ClickException(f"Error reading schema: {e}")


@main.command()
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
@click.option('--lang', '-l', 
              type=click.Choice(['c', 'rust', 'python', 'javascript']),
              default='c',
              help='Target language for code generation')
@click.option('--output', '-o',
              type=click.Path(path_type=Path),
              default=Path('generated'),
              help='Output directory for generated files')
@click.option('--header-name',
              default='picomsg_generated',
              help='Name for generated header files (C only)')
@click.option('--module-name',
              default='picomsg_generated',
              help='Name for generated module files (Rust/Python)')
@click.option('--structs-only',
              is_flag=True,
              help='Generate only struct definitions without error enums and serialization functions (C only)')
def compile(schema_file: Path, lang: str, output: Path, header_name: str, module_name: str, structs_only: bool):
    """Compile a PicoMsg schema file to target language bindings."""
    try:
        # Parse schema
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        click.echo(f"Parsed schema: {schema_file}")
        if schema.namespace:
            click.echo(f"Namespace: {schema.namespace.name}")
        click.echo(f"Enums: {len(schema.enums)}")
        click.echo(f"Structs: {len(schema.structs)}")
        click.echo(f"Messages: {len(schema.messages)}")
        
        # Generate code
        if lang == 'c':
            generator = CCodeGenerator(schema)
            generator.set_option('header_name', header_name)
            generator.set_option('structs_only', structs_only)
            
            if structs_only:
                click.echo("Mode: Structs only (no error enums or serialization functions)")
        elif lang == 'rust':
            generator = RustCodeGenerator(schema)
            generator.set_option('module_name', module_name)
            click.echo(f"Generating Rust code with module name: {module_name}")
        elif lang == 'python':
            generator = PythonCodeGenerator(schema)
            generator.set_option('module_name', module_name)
            click.echo(f"Generating Python code with module name: {module_name}")
        else:
            raise click.ClickException(f"Language '{lang}' not yet implemented")
        
        # Write files
        generator.write_files(output)
        
        files = generator.generate()
        click.echo(f"\nGenerated {len(files)} files in {output}:")
        for filename in files.keys():
            click.echo(f"  - {filename}")
        
    except Exception as e:
        raise click.ClickException(f"Error: {e}")


@main.command()
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
def validate(schema_file: Path):
    """Validate a PicoMsg schema file."""
    try:
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        click.echo(f"✓ Schema file is valid: {schema_file}")
        if schema.namespace:
            click.echo(f"  Namespace: {schema.namespace.name}")
        if schema.version is not None:
            click.echo(f"  Version: {schema.version}")
        click.echo(f"  Enums: {len(schema.enums)}")
        click.echo(f"  Structs: {len(schema.structs)}")
        click.echo(f"  Messages: {len(schema.messages)}")
        
        # Show details
        if schema.enums:
            click.echo("\n  Enum definitions:")
            for enum in schema.enums:
                click.echo(f"    - {enum.name} : {enum.backing_type.name} ({len(enum.values)} values)")
        
        if schema.structs:
            click.echo("\n  Struct definitions:")
            for struct in schema.structs:
                click.echo(f"    - {struct.name} ({len(struct.fields)} fields)")
        
        if schema.messages:
            click.echo("\n  Message definitions:")
            for message in schema.messages:
                click.echo(f"    - {message.name} ({len(message.fields)} fields)")
        
    except Exception as e:
        raise click.ClickException(f"Validation failed: {e}")


@main.command()
@click.argument('schema_file', type=click.Path(exists=True, path_type=Path))
def info(schema_file: Path):
    """Show detailed information about a PicoMsg schema."""
    try:
        parser = SchemaParser()
        schema = parser.parse_file(schema_file)
        
        click.echo(f"Schema: {schema_file}")
        click.echo("=" * 50)
        
        if schema.namespace:
            click.echo(f"Namespace: {schema.namespace.name}")
        
        if schema.version is not None:
            click.echo(f"Version: {schema.version}")
        
        if schema.namespace or schema.version is not None:
            click.echo()
        
        if schema.enums:
            click.echo("Enums:")
            for enum in schema.enums:
                click.echo(f"  {enum.name} : {enum.backing_type.name}:")
                for value in enum.values:
                    click.echo(f"    {value.name} = {value.value}")
                click.echo()
        
        if schema.structs:
            click.echo("Structs:")
            for struct in schema.structs:
                click.echo(f"  {struct.name}:")
                for field in struct.fields:
                    click.echo(f"    {field.name}: {_format_type(field.type)}")
                click.echo()
        
        if schema.messages:
            click.echo("Messages:")
            for message in schema.messages:
                click.echo(f"  {message.name}:")
                for field in message.fields:
                    click.echo(f"    {field.name}: {_format_type(field.type)}")
                click.echo()
        
    except Exception as e:
        raise click.ClickException(f"Error: {e}")


def _format_type(type_obj) -> str:
    """Format a type object for display."""
    from .schema.ast import PrimitiveType, StringType, BytesType, ArrayType, FixedArrayType, StructType, EnumType
    
    if isinstance(type_obj, PrimitiveType):
        return type_obj.name
    elif isinstance(type_obj, StringType):
        return "string"
    elif isinstance(type_obj, BytesType):
        return "bytes"
    elif isinstance(type_obj, ArrayType):
        return f"[{_format_type(type_obj.element_type)}]"
    elif isinstance(type_obj, FixedArrayType):
        return f"[{_format_type(type_obj.element_type)}:{type_obj.size}]"
    elif isinstance(type_obj, (StructType, EnumType)):
        return type_obj.name
    else:
        return str(type_obj)


if __name__ == '__main__':
    main() 
