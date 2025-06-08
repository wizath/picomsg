"""
CLI integration for JSON conversion system.

This module adds JSON-related commands to the PicoMsg CLI for validation,
conversion, and streaming operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Union

from . import (
    create_converter, validate_json_file, pretty_print_json_file,
    JSONConversionError, JSONValidationError, JSONStreamingError
)
from .streaming import (
    stream_validate_json_array, stream_convert_json_lines_to_array,
    stream_convert_json_array_to_lines, StreamingJSONParser, StreamingJSONWriter
)
from .rust_integration import enhance_rust_json_support, generate_rust_json_cargo_toml
from .python_integration import enhance_python_json_support


def add_json_commands(subparsers) -> None:
    """Add JSON-related commands to the CLI parser."""
    
    # JSON validation command
    json_validate_parser = subparsers.add_parser(
        'json-validate',
        help='Validate JSON data against a PicoMsg schema'
    )
    json_validate_parser.add_argument(
        'schema_file',
        type=Path,
        help='Path to the .pico schema file'
    )
    json_validate_parser.add_argument(
        'json_file',
        type=Path,
        help='Path to the JSON file to validate'
    )
    json_validate_parser.add_argument(
        'type_name',
        help='Name of the schema type to validate against'
    )
    json_validate_parser.add_argument(
        '--streaming',
        action='store_true',
        help='Use streaming validation for large JSON arrays'
    )
    json_validate_parser.set_defaults(func=cmd_json_validate)
    
    # JSON pretty-print command
    json_pretty_parser = subparsers.add_parser(
        'json-pretty',
        help='Pretty-print JSON with schema annotations'
    )
    json_pretty_parser.add_argument(
        'schema_file',
        type=Path,
        help='Path to the .pico schema file'
    )
    json_pretty_parser.add_argument(
        'json_file',
        type=Path,
        help='Path to the JSON file to format'
    )
    json_pretty_parser.add_argument(
        'type_name',
        help='Name of the schema type'
    )
    json_pretty_parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file (default: stdout)'
    )
    json_pretty_parser.add_argument(
        '--indent',
        type=int,
        default=2,
        help='Indentation level (default: 2)'
    )
    json_pretty_parser.set_defaults(func=cmd_json_pretty)
    
    # JSON conversion command
    json_convert_parser = subparsers.add_parser(
        'json-convert',
        help='Convert between JSON formats (array ↔ lines)'
    )
    json_convert_parser.add_argument(
        'input_file',
        type=Path,
        help='Input JSON file'
    )
    json_convert_parser.add_argument(
        'output_file',
        type=Path,
        help='Output JSON file'
    )
    json_convert_parser.add_argument(
        '--from-format',
        choices=['array', 'lines'],
        default='array',
        help='Input format (default: array)'
    )
    json_convert_parser.add_argument(
        '--to-format',
        choices=['array', 'lines'],
        default='lines',
        help='Output format (default: lines)'
    )
    json_convert_parser.add_argument(
        '--schema',
        type=Path,
        help='Optional schema file for validation'
    )
    json_convert_parser.add_argument(
        '--type',
        help='Schema type name (required if --schema is provided)'
    )
    json_convert_parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip validation during conversion'
    )
    json_convert_parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print output (only for array format)'
    )
    json_convert_parser.set_defaults(func=cmd_json_convert)
    
    # Enhanced code generation command
    json_codegen_parser = subparsers.add_parser(
        'json-codegen',
        help='Generate enhanced code with JSON support'
    )
    json_codegen_parser.add_argument(
        'schema_file',
        type=Path,
        help='Path to the .pico schema file'
    )
    json_codegen_parser.add_argument(
        '--lang',
        choices=['rust', 'python'],
        required=True,
        help='Target language for enhanced JSON support'
    )
    json_codegen_parser.add_argument(
        '-o', '--output',
        type=Path,
        required=True,
        help='Output file or directory'
    )
    json_codegen_parser.add_argument(
        '--module-name',
        default='picomsg_types',
        help='Module name (default: picomsg_types)'
    )
    json_codegen_parser.add_argument(
        '--package-name',
        help='Package name for Rust (default: derived from module-name)'
    )
    json_codegen_parser.set_defaults(func=cmd_json_codegen)
    
    # JSON schema info command
    json_info_parser = subparsers.add_parser(
        'json-info',
        help='Show JSON schema information'
    )
    json_info_parser.add_argument(
        'schema_file',
        type=Path,
        help='Path to the .pico schema file'
    )
    json_info_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    json_info_parser.set_defaults(func=cmd_json_info)


def cmd_json_validate(args) -> int:
    """Handle json-validate command."""
    try:
        if args.streaming:
            # Use streaming validation
            result = stream_validate_json_array(args.json_file, args.type_name, args.schema_file)
            if result:
                print(f"✓ JSON array validation passed for type '{args.type_name}'")
                return 0
            else:
                print(f"✗ JSON array validation failed for type '{args.type_name}'")
                return 1
        else:
            # Use regular validation
            result = validate_json_file(args.json_file, args.type_name, args.schema_file)
            if result:
                print(f"✓ JSON validation passed for type '{args.type_name}'")
                return 0
            else:
                print(f"✗ JSON validation failed for type '{args.type_name}'")
                return 1
    
    except (JSONValidationError, JSONConversionError, JSONStreamingError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_json_pretty(args) -> int:
    """Handle json-pretty command."""
    try:
        formatted = pretty_print_json_file(
            args.json_file, 
            args.type_name, 
            args.schema_file,
            args.output
        )
        
        if not args.output:
            print(formatted)
        else:
            print(f"✓ Pretty-printed JSON written to {args.output}")
        
        return 0
    
    except (JSONValidationError, JSONConversionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_json_convert(args) -> int:
    """Handle json-convert command."""
    try:
        validate = not args.no_validate
        
        if args.from_format == 'lines' and args.to_format == 'array':
            # JSON Lines to Array
            stream_convert_json_lines_to_array(
                args.input_file,
                args.output_file,
                args.type if args.schema else None,
                args.schema if args.schema else None,
                2 if args.pretty else None
            )
        elif args.from_format == 'array' and args.to_format == 'lines':
            # JSON Array to Lines
            stream_convert_json_array_to_lines(
                args.input_file,
                args.output_file,
                args.type if args.schema else None,
                args.schema if args.schema else None
            )
        else:
            print(f"Error: Conversion from {args.from_format} to {args.to_format} not supported", file=sys.stderr)
            return 1
        
        print(f"✓ Converted {args.input_file} from {args.from_format} to {args.to_format} format")
        print(f"  Output written to {args.output_file}")
        
        return 0
    
    except (JSONValidationError, JSONConversionError, JSONStreamingError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_json_codegen(args) -> int:
    """Handle json-codegen command."""
    try:
        if args.lang == 'rust':
            # Generate enhanced Rust code
            enhance_rust_json_support(args.schema_file, args.output, args.module_name)
            
            # Generate Cargo.toml if output is a directory
            if args.output.is_dir():
                package_name = args.package_name or args.module_name.replace('_', '-')
                generate_rust_json_cargo_toml(args.output, package_name)
                print(f"✓ Enhanced Rust code with JSON support generated in {args.output}")
                print(f"  - Generated {args.output / 'lib.rs'}")
                print(f"  - Generated {args.output / 'Cargo.toml'}")
            else:
                print(f"✓ Enhanced Rust code with JSON support generated: {args.output}")
        
        elif args.lang == 'python':
            # Generate enhanced Python code
            enhance_python_json_support(args.schema_file, args.output, args.module_name)
            print(f"✓ Enhanced Python code with JSON support generated: {args.output}")
        
        return 0
    
    except Exception as e:
        print(f"Error generating enhanced code: {e}", file=sys.stderr)
        return 1


def cmd_json_info(args) -> int:
    """Handle json-info command."""
    try:
        from ..schema.parser import SchemaParser
        
        parser = SchemaParser()
        schema = parser.parse_file(args.schema_file)
        
        # Collect schema information
        info = {
            'schema_file': str(args.schema_file),
            'structs': [],
            'messages': [],
            'total_types': len(schema.structs) + len(schema.messages)
        }
        
        for struct in schema.structs:
            struct_info = {
                'name': struct.name,
                'fields': []
            }
            for field in struct.fields:
                field_info = {
                    'name': field.name,
                    'type': str(field.type)
                }
                struct_info['fields'].append(field_info)
            info['structs'].append(struct_info)
        
        for message in schema.messages:
            message_info = {
                'name': message.name,
                'fields': []
            }
            for field in message.fields:
                field_info = {
                    'name': field.name,
                    'type': str(field.type)
                }
                message_info['fields'].append(field_info)
            info['messages'].append(message_info)
        
        if args.format == 'json':
            print(json.dumps(info, indent=2))
        else:
            # Text format
            print(f"Schema: {args.schema_file}")
            print(f"Total types: {info['total_types']}")
            print()
            
            if info['structs']:
                print("Structs:")
                for struct in info['structs']:
                    print(f"  {struct['name']}")
                    for field in struct['fields']:
                        print(f"    {field['name']}: {field['type']}")
                print()
            
            if info['messages']:
                print("Messages:")
                for message in info['messages']:
                    print(f"  {message['name']}")
                    for field in message['fields']:
                        print(f"    {field['name']}: {field['type']}")
        
        return 0
    
    except Exception as e:
        print(f"Error reading schema: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for JSON CLI commands."""
    parser = argparse.ArgumentParser(
        description='PicoMsg JSON Conversion System',
        prog='picomsg-json'
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available JSON commands'
    )
    
    add_json_commands(subparsers)
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 1
    
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main()) 
