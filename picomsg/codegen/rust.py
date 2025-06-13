"""
Template-based Rust code generator for PicoMsg.
"""

from typing import Dict
from ..schema.ast import Schema
from .base import CodeGenerator
from .templates.engine import TemplateEngine


class RustCodeGenerator(CodeGenerator):
    """Generate Rust code from PicoMsg schema using templates."""
    
    def __init__(self, schema: Schema):
        super().__init__(schema)
        self.template_engine = TemplateEngine()
    
    def generate(self) -> Dict[str, str]:
        """Generate Rust module file."""
        module_name = self.get_option('module_name', 'picomsg_generated')
        
        # Build context for template rendering
        context = self._build_context()
        
        # Render the main module
        module_content = self.template_engine.render('rust/module.rs.j2', context)
        
        files = {}
        files[f"{module_name}.rs"] = module_content
        
        return files
    
    def _build_context(self) -> Dict:
        """Build template context."""
        namespace_prefix = self._get_namespace_prefix()
        
        context = {
            'schema': self.schema,
            'namespace_prefix': namespace_prefix,
            'module_name': self.get_option('module_name', 'picomsg_generated'),
        }
        
        return context
    
    def _get_namespace_prefix(self) -> str:
        """Get namespace prefix for generated identifiers."""
        if self.schema.namespace:
            # Convert to PascalCase for Rust types
            parts = self.schema.namespace.name.replace('.', '_').split('_')
            return ''.join(word.capitalize() for word in parts)
        return ''
    
    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize an identifier for Rust."""
        # Rust keywords that need to be escaped
        rust_keywords = {
            'as', 'break', 'const', 'continue', 'crate', 'else', 'enum', 'extern',
            'false', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop', 'match',
            'mod', 'move', 'mut', 'pub', 'ref', 'return', 'self', 'Self',
            'static', 'struct', 'super', 'trait', 'true', 'type', 'unsafe',
            'use', 'where', 'while', 'async', 'await', 'dyn'
        }
        
        if name in rust_keywords:
            return f"r#{name}"
        return name 