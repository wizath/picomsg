"""
Command-line interface for PicoMsg.
"""

import click
from pathlib import Path
from typing import Optional

from .schema.parser import SchemaParser
from .codegen.c import CCodeGenerator
from .codegen.rust import RustCodeGenerator


@click.group()
@click.version_option()
def main():
    """PicoMsg - Lightweight binary serialization format."""
    pass


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
              help='Name for generated module files (Rust only)')
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
        click.echo(f"  Structs: {len(schema.structs)}")
        click.echo(f"  Messages: {len(schema.messages)}")
        
        # Show details
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
    from .schema.ast import PrimitiveType, StringType, BytesType, ArrayType, StructType
    
    if isinstance(type_obj, PrimitiveType):
        return type_obj.name
    elif isinstance(type_obj, StringType):
        return "string"
    elif isinstance(type_obj, BytesType):
        return "bytes"
    elif isinstance(type_obj, ArrayType):
        return f"[{_format_type(type_obj.element_type)}]"
    elif isinstance(type_obj, StructType):
        return type_obj.name
    else:
        return str(type_obj)


if __name__ == '__main__':
    main() 
