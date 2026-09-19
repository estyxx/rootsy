import functools
import importlib
import inspect
from typing import TYPE_CHECKING, TypeGuard

import attrs

from rootsy.adapters import GedcomParser, GedcomRecord

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

# Every parser reaches the registry as a parser of some record; which record
# it builds is known to its caller, not to the registry.
type AnyParser = GedcomParser[GedcomRecord]


@attrs.frozen
class ParserRegistry:
    """Registry of available parsers, by tag and by full tag path."""

    _parsers: dict[str, type[AnyParser]] = attrs.field(factory=dict, init=False)
    _parsers_by_path: dict[tuple[str, ...], type[AnyParser]] = attrs.field(
        factory=dict,
        init=False,
    )

    def register(self, parser_class: type[AnyParser]) -> None:
        """Register a parser class, under its tag path when it claims one."""
        if path := getattr(parser_class, "handles_path", None):
            self._parsers_by_path[tuple(path)] = parser_class
        else:
            self._parsers[parser_class.handles_tag] = parser_class

    def get_parser_by_tag(self, tag: str) -> AnyParser | None:
        """Get parser instance for a tag."""
        parser_class = self._parsers.get(tag)
        return parser_class() if parser_class else None

    def get_parser_by_path(self, path: Sequence[str]) -> AnyParser | None:
        """Get parser instance for a tag path, falling back to its last tag."""
        if not path:
            return None
        if parser_class := self._parsers_by_path.get(tuple(path)):
            return parser_class()
        return self.get_parser_by_tag(path[-1])


def _is_parser(obj: type[object]) -> TypeGuard[type[AnyParser]]:
    """Whether a class `rootsy.parsers` exports is a parser at all."""
    return hasattr(obj, "handles_tag")


def discover_parsers() -> Iterator[type[AnyParser]]:
    """Discover all parser classes exported by rootsy.parsers."""
    module = importlib.import_module("rootsy.parsers")

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if _is_parser(obj):
            yield obj


def _build_registry() -> ParserRegistry:
    _registry = ParserRegistry()

    for parser_class in discover_parsers():
        _registry.register(parser_class)
    return _registry


@functools.cache
def get_registry() -> ParserRegistry:
    return _build_registry()


def get_parser_for_tag(tag: str) -> AnyParser | None:
    """Get a parser for a specific tag."""
    return get_registry().get_parser_by_tag(tag)


def get_parser_for_path(path: Sequence[str]) -> AnyParser | None:
    """Get a parser for a full tag path, such as `("HEAD", "SOUR")`."""
    return get_registry().get_parser_by_path(path)
