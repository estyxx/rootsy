import functools
import importlib
import inspect
from collections.abc import Iterator

import attrs

from rootsy.adapters import GedcomParser


@attrs.frozen
class ParserRegistry:
    """Registry of available parsers by tag."""

    _parsers: dict[str, type[GedcomParser]] = attrs.field(factory=dict, init=False)

    def register(self, parser_class: type[GedcomParser]) -> None:
        """Register a parser class."""
        self._parsers[parser_class.handles_tag] = parser_class

    def get_parser_by_tag(self, tag: str) -> GedcomParser | None:
        """Get parser instance for a tag."""
        parser_class = self._parsers.get(tag)
        return parser_class() if parser_class else None


def discover_parsers() -> Iterator[type[GedcomParser]]:
    """Discover all parser classes exported by rootsy.parsers."""
    module = importlib.import_module("rootsy.parsers")

    for _, obj in inspect.getmembers(module, inspect.isclass):
        yield obj


def _build_registry() -> ParserRegistry:
    _registry = ParserRegistry()

    for parser_class in discover_parsers():
        _registry.register(parser_class)
    return _registry


@functools.cache
def get_registry() -> ParserRegistry:
    return _build_registry()


def get_parser_for_tag(tag: str) -> GedcomParser | None:
    """Get a parser for a specific tag."""
    return get_registry().get_parser_by_tag(tag)
