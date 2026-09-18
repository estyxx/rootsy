Guidance for AI agents working in this repository. Read it fully before touching code.

## What this is

Rootsy is a typed, pythonic GEDCOM parser. It turns a `.ged` file into
immutable `attrs` models (`Individual`, `Family`, `Header`, …) collected in a
`GedcomStructure`, which can be serialised to plain JSON for consumers such as
the beltrami.family website.

Goals, in priority order:

1. **Correctness against the spec.** GEDCOM 5.5.1 today; GEDCOM 7.0 is the
   next target. Both specifications are the source of truth, not other
   parsers and not what one exporter happens to emit.
2. **Full typing.** Every model field has a precise type; no `dict[str, Any]`
   leaks out of the public API.
3. **Readable, boring code.** One record type per module, one parser per
   record type, no cleverness.

## Stack and commands

Python 3.13+, `attrs`, `uv` for environments, `ruff` for lint and format,
`pytest` for tests. `mypy --strict` should be added and kept green.

```sh
uv sync                        # create/refresh the venv with dev deps
uv run pytest                  # run tests
uv run ruff check . --fix      # lint
uv run ruff format .           # format
uv run mypy rootsy             # type-check (once configured)
```

Run all four before declaring a task finished.

## Repository layout

```
rootsy/
  reader.py        GedcomReader: file → GedcomLine → groups of lines per level-0 record
  types.py         GedcomLine (level, xref, tag, value) and ParsingContext (tag path)
  adapters.py      GedcomRecord base class; GedcomParser protocol; ParserNotFoundError
  registry.py      discovers parser classes in rootsy.parsers and maps tag → parser
  parser.py        parse_gedcom(path) → GedcomStructure  (the public entry point)
  models/          one attrs model per record/structure (individual, family, header,
                   address, event, multimedia, …) plus GedcomStructure
  parsers/         one parser per record/structure, same names as models/
tests/             pytest; fixtures are small inline GEDCOM snippets
```

Flow: `GedcomReader.line_groups()` yields each level-0 record with its
substructure as a list of `GedcomLine`. `parse_gedcom` looks up a parser by
the record's tag in the registry, calls `parser.parse(lines, context)`, and
stores the resulting model in `GedcomStructure`.

## Conventions

### Models

- `@attrs.frozen(slots=True, kw_only=True)`, subclassing `GedcomRecord`, with
  `tag: ClassVar[str]` set to the GEDCOM tag.
- Field names are the spec's meaning in `snake_case` (`given_name`, not
  `givn`). Add a comment with the GEDCOM tag when the mapping is not obvious.
- Optional scalar fields default to `None`; list fields use
  `attrs.field(factory=list)`. Never use mutable defaults.
- Dates are not `datetime`. GEDCOM dates carry qualifiers (`ABT`, `BEF`,
  `AFT`, `BET … AND …`, `EST`, `CAL`), calendars, and partial precision
  (`1890`, `MAR 1890`). Model them as a dedicated `GedcomDate` type with the
  original string preserved; only offer a `datetime`/`date` conversion when the
  value is exact.
- Cross-references (`@I1@`) stay as strings on models. Resolution happens on
  `GedcomStructure`, not inside records.

### Parsers

- Implement the `GedcomParser` protocol: `handles_tag` class var and
  `parse(lines, context) -> tuple[Model, lines_consumed]`.
- A parser owns exactly the lines of its structure: stop when a line's level
  is `<=` the structure's starting level. Delegate every nested structure
  (`ADDR`, `BIRT`, `DEAT`, `SOUR` citation, …) to that structure's parser and
  advance `i` by the consumed count. Do not inline the child's tags.
- Never silently `pass` on a tag the spec defines for that structure. Either
  parse it, or record it in an `unparsed: list[GedcomLine]` field so nothing is
  lost. Vendor extension tags (`_UID`, `_PRIM`, …) go to the same place.
- Use `match line.tag:` as the existing parsers do. Keep each `case` to one or
  two lines; anything longer becomes a helper.
- Use `context.path` for tags that mean different things in different places
  (e.g. `VERS` under `GEDC` vs under `SOUR`), as `HeaderParser` already does.

### Style

- `ruff` with `select = ["ALL"]` and the ignore list in `pyproject.toml`. Do
  not add ignores to make a warning go away; fix the code or justify the ignore
  in a comment.
- Type hints on every function, including tests. PEP 695 generics
  (`class GedcomParser[Result: GedcomRecord]`) are fine.
- Docstrings on public classes and functions: one summary line, then detail
  only if it adds something the signature does not say.
- No I/O in models or parsers. Only `reader.py` touches files.
- Exceptions: subclass a `RootsyError` base; raise with a message that
  includes the line number when possible.

### Tests

- One test module per parser: `tests/parsers/test_individual.py` and so on.
- Build inputs from small inline GEDCOM strings via a shared helper that
  returns `list[GedcomLine]`; assert on the model, not on dicts.
- Cover: happy path, missing optional tags, unknown tags, nested structures,
  and at least one real-world quirk per exporter you support (MyHeritage
  exports currently drive this project).
- Spec conformance: keep a `tests/fixtures/` folder with the official sample
  files (e.g. the FamilySearch GEDCOM 7 `maximal70.ged` and `minimal70.ged`)
  and a test that parses each without error.

## GEDCOM notes that matter here

- 5.5.1 and 7.0 differ materially: 7.0 is UTF-8 only, removes `CONC`, changes
  the `HEAD` structure (`GEDC.VERS 7.0`, `SCHMA` for extensions), tightens
  xref syntax, and redefines several event and name substructures. Detect the
  version from the header and dispatch to version-aware parsers rather than
  sprinkling `if version == …` through one parser.
- `FAMC` on an `INDI` = family the person is a child of. `FAMS` = family the
  person is a spouse/partner in. Both must be captured; they are different
  fields.
- `NAME` values are `Given /Surname/ Suffix`. Empty parts are legal. When
  `GIVN`/`SURN` substructures are absent, derive them from the slashed form.
- `BIRT`, `DEAT`, `MARR`, `DIV`, `RESI` and the other events share one
  structure (`DATE`, `PLAC`, `SOUR`, `NOTE`, …). Parse them with a single
  event-detail parser and attach the event type from the tag.
- MyHeritage exports include level-0 `SOUR`, `NOTE`, `OBJE`, `SUBM` and
  `REPO` records. Every level-0 tag must have a parser or be explicitly
  skipped with a logged warning; an unknown tag must not crash `parse_gedcom`.
- Line parsing: `GedcomLine.from_string` uses `split(maxsplit=2)`. That is
  correct for `level [xref] tag [value]` only when the value is the last token;
  verify it against lines like `0 @N1@ NOTE some text` and fix if needed.

## Known gaps (as of September 2026)

- `IndividualParser`: `BIRT`, `DEAT`, `RESI`, `FAMS` are ignored; `FAMC` is
  stored in `families`; `parents` is never populated; `name` keeps the raw
  slashed string.
- `FamilyParser`: `MARR`, `DIV` and their events are ignored.
- `parse_gedcom` calls `.parse` on the registry result without checking for
  `None`, so any unhandled level-0 tag raises `AttributeError`.
- `HeaderParser.parse_date` uses `strptime("%d %b %Y")`, which rejects
  qualified or partial GEDCOM dates.
- `HeaderSourceParser` registers `SOUR`, so top-level source records are
  mis-parsed as the header's source.
- No CLI, no `[build-system]` in `pyproject.toml`, no mypy, no CI.

## Roadmap (in order)

1. `GedcomDate` type and a shared event-detail parser; wire `BIRT`/`DEAT`
   into `Individual` and `MARR`/`DIV` into `Family`; capture `FAMS`/`FAMC`
   correctly; expose `given_name`/`surname` always.
2. Make `parse_gedcom` resilient: registry miss → warning + skip; add
   `unparsed` capture on every model.
3. Version detection and GEDCOM 7.0 support with the official sample files as
   conformance tests.
4. `rootsy export file.ged --out file.json` CLI (Typer or argparse) and a
   `[build-system]` so the package installs cleanly; publish to PyPI.
5. mypy strict, GitHub Actions CI (ruff, mypy, pytest on 3.13).

When adding support for a new tag, work spec-first: find it in the
specification, add the field to the model, add the `case` to the parser, add a
test with a snippet from the spec. Do not reverse-engineer from a single
exporter's output.
