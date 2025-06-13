"""
Template-based Python code generator for PicoMsg.
"""

from typing import Dict
from ..schema.ast import Schema
from .base import CodeGenerator
from .templates.engine import TemplateEngine


class PythonCodeGenerator(CodeGenerator):
    """Generate Python code from PicoMsg schema using templates."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
        self.engine = TemplateEngine()
    
    def generate(self) -> Dict[str, str]:
        """Generate Python module file."""
        module_name = self.get_option('module_name', 'picomsg_generated')
        
        # Build template context
        context = {
            'schema': self.schema,
            'namespace_prefix': self._get_namespace_prefix(),
            'module_name': module_name,
        }
        
        # Generate the module
        module_content = self.engine.render('python/module.py.j2', context)
        
        return {f"{module_name}.py": module_content}
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for class names."""
        if not self.schema.namespace:
            return ''
        
        # Convert namespace to PascalCase prefix
        parts = self.schema.namespace.name.split('.')
        return ''.join(part.capitalize() for part in parts)
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize identifier for Python."""
        python_keywords = {
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
            'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'not', 'or', 'pass', 'print', 'raise', 'return', 'try', 'while', 'with',
            'yield', 'None', 'True', 'False'
        }
        
        if name in python_keywords:
            return f'{name}_'
        return name 