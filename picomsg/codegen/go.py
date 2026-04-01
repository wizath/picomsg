"""
Template-based Go code generator for PicoMsg.
"""

from typing import Dict
from ..schema.ast import Schema
from .base import CodeGenerator
from .templates.engine import TemplateEngine


class GoCodeGenerator(CodeGenerator):
    """Generate Go code from PicoMsg schema using templates."""

    def __init__(self, schema: Schema):
        super().__init__(schema)
        self.template_engine = TemplateEngine()

    def generate(self) -> Dict[str, str]:
        module_name = self.get_option('module_name', 'picomsg_generated')
        context = self._build_context()
        module_content = self.template_engine.render('go/module.go.j2', context)
        return {f"{module_name}.go": module_content}

    def _build_context(self) -> Dict:
        namespace_prefix = self._get_namespace_prefix()
        package_name = self.get_option('module_name', 'picomsg_generated')

        return {
            'schema': self.schema,
            'namespace_prefix': namespace_prefix,
            'package_name': package_name,
        }

    def _get_namespace_prefix(self) -> str:
        if self.schema.namespace:
            parts = self.schema.namespace.name.replace('.', '_').split('_')
            return ''.join(word.capitalize() for word in parts)
        return ''

    def _sanitize_identifier(self, name: str) -> str:
        go_keywords = {
            'break', 'case', 'chan', 'const', 'continue', 'default', 'defer',
            'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import',
            'interface', 'map', 'package', 'range', 'return', 'select', 'struct',
            'switch', 'type', 'var',
        }
        if name in go_keywords:
            return f'{name}_'
        return name
