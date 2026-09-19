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

Python 3.14+, `attrs`, `uv` for environments, `ruff` for lint and format,
`pytest` for tests, `mypy` in strict mode, `typer` and `rich` for the CLI.

```sh
uv sync                        # create/refresh the venv with dev deps
uv run pytest                  # run tests
uv run ruff check . --fix      # lint
uv run ruff format .           # format
uv run mypy                    # type-check rootsy and tests, strictly
```

Run all four before declaring a task finished. GitHub Actions runs the same
four on Python 3.14 for every push and pull request.

## Repository layout

```
rootsy/
  reader.py        GedcomReader: file → GedcomLine → groups of lines per level-0 record
  types.py         GedcomLine (level, xref, tag, value, line number) and ParsingContext
  lines.py         helpers over a sequence of GedcomLine (substructure span, CONC/CONT)
  exceptions.py    RootsyError and every error rootsy raises
  adapters.py      GedcomRecord base class (with `unparsed`); GedcomParser protocol
  registry.py      discovers parser classes in rootsy.parsers, maps tag/tag path → parser
  parser.py        parse_gedcom(path) → GedcomStructure  (the public entry point)
  anonymise.py     anonymise(structure) → a GedcomStructure that names nobody
  coverage.py      coverage(structure) → the tags left in `unparsed`, counted
  cli.py           `rootsy export`, `stats` and `coverage`, the `rootsy` command
  models/          one attrs model per record/structure (individual, family, header,
                   address, event, multimedia, …) plus GedcomStructure
  parsers/         one parser per record/structure, same names as models/
tests/             pytest; fixtures are small inline GEDCOM snippets
```

Flow: `GedcomReader.line_groups()` yields each level-0 record with its
substructure as a list of `GedcomLine`. `parse_gedcom` looks up a parser by
the record's tag in the registry, calls `parser.parse(lines, context)`, and
stores the resulting model in `GedcomStructure`. A level-0 tag with no parser
is logged with its line number and kept as a `SkippedRecord` on the structure,
never raised.

A tag that means different things in different places is registered by its full
tag path instead: `HeaderSourceParser` claims `("HEAD", "SOUR")`, so a level-0
`SOUR` reaches `SourceRecordParser`. Look a parser up with
`get_parser_for_path(context.path)`, which falls back to the last tag.

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
  (`1890`, `MAR 1890`). Use `GedcomDate` (`rootsy/models/date.py`): it keeps
  the original string in `raw`, never raises on input it cannot read, and
  `to_date()` returns a `datetime.date` only when the value is an exact day.
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
- `anonymise.py` rebuilds every model explicitly rather than evolving it, so a
  field added to a model without a line there comes out empty instead of
  leaking. Add the field to `_Anonymiser` in the same change as the parser.
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

## Commits and pull requests

Keep it short. No walls of text.

### Commits

- Write a summary line, and preferably nothing else.
- The summary is imperative, capitalised, 70 characters or fewer, with no full stop and no `feat:` or `fix:` prefix. It should complete "If merged, this commit will...". Example: `Show birth and death years on tree nodes`.
- Add a body only when the reason isn't obvious from the summary. Then one or two short sentences on why, not what.

### Pull request descriptions

- Start with "In this PR" and say what changed and why, in one to three sentences.
- If there are several distinct changes, add at most three short bullets.
- No headings, no test plan, no file-by-file list, no filler.

Example: "In this PR we parse birth and death events on individuals, so the tree can show years under each name."

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
- Line parsing: `GedcomLine.from_string` matches `level [xref] tag [value]`
  with the value running to the end of the line, so `0 @N1@ NOTE some text` and
  `1 EMAIL a@b.com` both come out right. Lines carry the `line_number` they were
  read from, for error messages; it is left out of equality.

## Known gaps (as of September 2026)

- `EventParser` and `IndividualParser` keep `SOUR` citations as raw lines;
  there is no citation model yet. `1 MARR Y` parses as an event, but the `Y`
  itself is dropped.
- Level-0 `SUBM`, `REPO` and `NOTE` records have no parser, so they are logged
  and skipped.
- `HeaderParser` is where the unparsed tags now are: `GEDC`, `FILE`, the
  contact details beside `CORP`, and the exporter's own header tags.
- `GedcomStructure` keeps the header, individuals, families, sources and the
  level-0 records it skipped. A level-0 `OBJE` record has nowhere to go yet,
  though an `OBJE` inline on an `INDI` becomes `Individual.media`.
- There is no version detection: `HeaderParser` reads `GEDC.VERS` but every
  record is then parsed the same way whatever the version says.
- The package is not on PyPI yet, though it now builds with hatchling.

## Roadmap (in order)

1. Version detection and GEDCOM 7.0 support with the official sample files as
   conformance tests.
2. Parsers for the level-0 records that are still skipped (`NOTE`, `SUBM`,
   `REPO`) and a model for source citations.
3. Publish to PyPI.

When adding support for a new tag, work spec-first: find it in the
specification, add the field to the model, add the `case` to the parser, add a
test with a snippet from the spec. Do not reverse-engineer from a single
exporter's output.
