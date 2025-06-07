"""
Base code generator class for PicoMsg.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path

from ..schema.ast import Schema


class CodeGenerator(ABC):
    """Base class for all code generators."""
    
    def __init__(self, schema: Schema):
        self.schema = schema
        self.options: Dict[str, Any] = {}
    
    def set_option(self, key: str, value: Any) -> None:
        """Set a generator option."""
        self.options[key] = value
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get a generator option."""
        return self.options.get(key, default)
    
    @abstractmethod
    def generate(self) -> Dict[str, str]:
        """
        Generate code for the schema.
        
        Returns:
            Dictionary mapping file names to file contents
        """
        pass
    
    def write_files(self, output_dir: Path) -> None:
        """Write generated files to the output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files = self.generate()
        for filename, content in files.items():
            file_path = output_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for generated identifiers."""
        if self.schema.namespace:
            return self.schema.namespace.name.replace('.', '_') + '_'
        return ''
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize an identifier for the target language."""
        # Default implementation - override in subclasses
        return name 
