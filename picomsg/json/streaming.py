"""
Streaming JSON parser for PicoMsg.

This module provides streaming JSON parsing capabilities for handling
large JSON messages without loading everything into memory at once.
"""

import json
import io
from typing import Dict, Any, Optional, Union, Iterator, Callable, BinaryIO, TextIO
from pathlib import Path

from . import JSONStreamingError, SchemaAwareJSONConverter
from ..schema.ast import Schema


class StreamingJSONParser:
    """
    Streaming JSON parser for large PicoMsg JSON files.
    
    This parser can handle:
    - Large JSON files that don't fit in memory
    - JSON arrays with many objects
    - Incremental validation during parsing
    - Memory-efficient processing
    """
    
    def __init__(self, converter: Optional[SchemaAwareJSONConverter] = None):
        """
        Initialize streaming parser.
        
        Args:
            converter: Optional schema-aware converter for validation
        """
        self.converter = converter
        self._buffer_size = 8192  # 8KB buffer
    
    def parse_json_array_stream(self, 
                               stream: Union[TextIO, BinaryIO], 
                               type_name: Optional[str] = None,
                               validate: bool = True) -> Iterator[Dict[str, Any]]:
        """
        Parse a JSON array stream, yielding one object at a time.
        
        Args:
            stream: Input stream containing JSON array
            type_name: Optional type name for validation
            validate: Whether to validate each object
            
        Yields:
            Individual JSON objects from the array
        """
        if isinstance(stream, BinaryIO):
            # Convert binary stream to text
            stream = io.TextIOWrapper(stream, encoding='utf-8')
        
        # Read the opening bracket
        char = self._read_next_char(stream)
        if char != '[':
            raise JSONStreamingError(f"Expected '[' at start of array, got '{char}'")
        
        # Skip whitespace
        self._skip_whitespace(stream)
        
        # Check for empty array
        char = self._peek_next_char(stream)
        if char == ']':
            stream.read(1)  # Consume the ']'
            return
        
        # Parse objects one by one
        first_object = True
        while True:
            # Skip comma if not first object
            if not first_object:
                char = self._read_next_char(stream)
                if char == ']':
                    break  # End of array
                elif char != ',':
                    raise JSONStreamingError(f"Expected ',' or ']', got '{char}'")
                self._skip_whitespace(stream)
            
            # Parse next object
            try:
                obj_str = self._read_json_object(stream)
                obj = json.loads(obj_str)
                
                # Validate if requested
                if validate and self.converter and type_name:
                    self.converter.validate_json(obj, type_name)
                
                yield obj
                
            except json.JSONDecodeError as e:
                raise JSONStreamingError(f"Invalid JSON object: {e}")
            except Exception as e:
                raise JSONStreamingError(f"Error parsing object: {e}")
            
            first_object = False
            self._skip_whitespace(stream)
    
    def parse_json_lines_stream(self,
                               stream: Union[TextIO, BinaryIO],
                               type_name: Optional[str] = None,
                               validate: bool = True) -> Iterator[Dict[str, Any]]:
        """
        Parse a JSON Lines stream (one JSON object per line).
        
        Args:
            stream: Input stream containing JSON Lines
            type_name: Optional type name for validation
            validate: Whether to validate each object
            
        Yields:
            Individual JSON objects from each line
        """
        if isinstance(stream, BinaryIO):
            stream = io.TextIOWrapper(stream, encoding='utf-8')
        
        line_number = 0
        for line in stream:
            line_number += 1
            line = line.strip()
            
            if not line:
                continue  # Skip empty lines
            
            try:
                obj = json.loads(line)
                
                # Validate if requested
                if validate and self.converter and type_name:
                    self.converter.validate_json(obj, type_name)
                
                yield obj
                
            except json.JSONDecodeError as e:
                raise JSONStreamingError(f"Invalid JSON on line {line_number}: {e}")
            except Exception as e:
                raise JSONStreamingError(f"Error parsing line {line_number}: {e}")
    
    def _read_next_char(self, stream: TextIO) -> str:
        """Read the next character from stream."""
        char = stream.read(1)
        if not char:
            raise JSONStreamingError("Unexpected end of stream")
        return char
    
    def _peek_next_char(self, stream: TextIO) -> str:
        """Peek at the next character without consuming it."""
        pos = stream.tell()
        char = stream.read(1)
        stream.seek(pos)
        if not char:
            raise JSONStreamingError("Unexpected end of stream")
        return char
    
    def _skip_whitespace(self, stream: TextIO) -> None:
        """Skip whitespace characters."""
        while True:
            pos = stream.tell()
            char = stream.read(1)
            if not char or char not in ' \t\n\r':
                stream.seek(pos)
                break
    
    def _read_json_object(self, stream: TextIO) -> str:
        """Read a complete JSON object from the stream."""
        # This is a simplified JSON object reader
        # In a production implementation, you might want to use a proper JSON streaming parser
        
        brace_count = 0
        in_string = False
        escape_next = False
        obj_chars = []
        
        while True:
            char = self._read_next_char(stream)
            obj_chars.append(char)
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
        
        return ''.join(obj_chars)


class StreamingJSONWriter:
    """
    Streaming JSON writer for large PicoMsg JSON output.
    
    This writer can:
    - Write large JSON arrays without loading everything into memory
    - Validate objects during writing
    - Format output with proper indentation
    """
    
    def __init__(self, 
                 stream: Union[TextIO, BinaryIO],
                 converter: Optional[SchemaAwareJSONConverter] = None,
                 indent: Optional[int] = None):
        """
        Initialize streaming writer.
        
        Args:
            stream: Output stream for JSON
            converter: Optional schema-aware converter for validation
            indent: Optional indentation level
        """
        if isinstance(stream, BinaryIO):
            self.stream = io.TextIOWrapper(stream, encoding='utf-8')
        else:
            self.stream = stream
        
        self.converter = converter
        self.indent = indent
        self._first_object = True
        self._array_started = False
    
    def start_array(self) -> None:
        """Start writing a JSON array."""
        if self._array_started:
            raise JSONStreamingError("Array already started")
        
        self.stream.write('[')
        if self.indent is not None:
            self.stream.write('\n')
        
        self._array_started = True
        self._first_object = True
    
    def write_object(self, obj: Dict[str, Any], type_name: Optional[str] = None) -> None:
        """
        Write a JSON object to the stream.
        
        Args:
            obj: JSON object to write
            type_name: Optional type name for validation
        """
        if not self._array_started:
            raise JSONStreamingError("Must call start_array() first")
        
        # Validate if converter is available
        if self.converter and type_name:
            self.converter.validate_json(obj, type_name)
        
        # Write comma separator if not first object
        if not self._first_object:
            self.stream.write(',')
            if self.indent is not None:
                self.stream.write('\n')
        
        # Write the object
        if self.indent is not None:
            # Pretty-printed output
            obj_str = json.dumps(obj, indent=self.indent)
            # Indent each line
            lines = obj_str.split('\n')
            indented_lines = [' ' * self.indent + line if line.strip() else line for line in lines]
            self.stream.write('\n'.join(indented_lines))
        else:
            # Compact output
            obj_str = json.dumps(obj, separators=(',', ':'))
            self.stream.write(obj_str)
        
        self._first_object = False
    
    def end_array(self) -> None:
        """End the JSON array."""
        if not self._array_started:
            raise JSONStreamingError("Array not started")
        
        if self.indent is not None:
            self.stream.write('\n')
        
        self.stream.write(']')
        self._array_started = False
    
    def write_json_lines(self, objects: Iterator[Dict[str, Any]], 
                        type_name: Optional[str] = None) -> None:
        """
        Write objects as JSON Lines format (one JSON object per line).
        
        Args:
            objects: Iterator of JSON objects
            type_name: Optional type name for validation
        """
        for obj in objects:
            # Validate if converter is available
            if self.converter and type_name:
                self.converter.validate_json(obj, type_name)
            
            obj_str = json.dumps(obj, separators=(',', ':'))
            self.stream.write(obj_str)
            self.stream.write('\n')
    
    def flush(self) -> None:
        """Flush the output stream."""
        self.stream.flush()
    
    def close(self) -> None:
        """Close the output stream."""
        if hasattr(self.stream, 'close'):
            self.stream.close()


# Convenience functions for streaming operations
def stream_validate_json_array(file_path: Union[str, Path],
                              type_name: str,
                              schema_file: Union[str, Path]) -> bool:
    """
    Stream-validate a large JSON array file.
    
    Args:
        file_path: Path to JSON array file
        type_name: Type name for validation
        schema_file: Path to schema file
        
    Returns:
        True if all objects are valid
    """
    from . import create_converter
    
    converter = create_converter(schema_file)
    parser = StreamingJSONParser(converter)
    
    try:
        with open(file_path, 'r') as f:
            for obj in parser.parse_json_array_stream(f, type_name, validate=True):
                pass  # Just validate, don't process
        return True
    except JSONStreamingError:
        return False


def stream_convert_json_lines_to_array(input_file: Union[str, Path],
                                      output_file: Union[str, Path],
                                      type_name: Optional[str] = None,
                                      schema_file: Optional[Union[str, Path]] = None,
                                      indent: Optional[int] = 2) -> None:
    """
    Convert JSON Lines file to JSON array format.
    
    Args:
        input_file: Input JSON Lines file
        output_file: Output JSON array file
        type_name: Optional type name for validation
        schema_file: Optional schema file for validation
        indent: Optional indentation for output
    """
    converter = None
    if schema_file:
        from . import create_converter
        converter = create_converter(schema_file)
    
    parser = StreamingJSONParser(converter)
    
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        writer = StreamingJSONWriter(outfile, converter, indent)
        writer.start_array()
        
        for obj in parser.parse_json_lines_stream(infile, type_name, validate=bool(converter)):
            writer.write_object(obj, type_name)
        
        writer.end_array()


def stream_convert_json_array_to_lines(input_file: Union[str, Path],
                                      output_file: Union[str, Path],
                                      type_name: Optional[str] = None,
                                      schema_file: Optional[Union[str, Path]] = None) -> None:
    """
    Convert JSON array file to JSON Lines format.
    
    Args:
        input_file: Input JSON array file
        output_file: Output JSON Lines file
        type_name: Optional type name for validation
        schema_file: Optional schema file for validation
    """
    converter = None
    if schema_file:
        from . import create_converter
        converter = create_converter(schema_file)
    
    parser = StreamingJSONParser(converter)
    
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        writer = StreamingJSONWriter(outfile, converter)
        
        objects = parser.parse_json_array_stream(infile, type_name, validate=bool(converter))
        writer.write_json_lines(objects, type_name) 
