"""The `rootsy` command line: export a GEDCOM file to JSON, or summarise one."""

from __future__ import annotations

import collections
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NoReturn

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.markup import escape
from rich.table import Table

from rootsy.exceptions import RootsyError
from rootsy.parser import parse_gedcom

if TYPE_CHECKING:
    from rootsy.models import GedcomStructure

app = typer.Typer(no_args_is_help=True, add_completion=False)

console = Console()
error_console = Console(stderr=True)


GedcomFile = Annotated[
    Path,
    typer.Argument(
        exists=True,
        dir_okay=False,
        readable=True,
        help="The GEDCOM file to read.",
        show_default=False,
    ),
]


@app.callback()
def main() -> None:
    """Read a GEDCOM file into typed Python objects."""
    # Records rootsy cannot parse are logged as warnings; a command-line run is
    # where someone wants to hear about them, so give the logger a handler.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[
            RichHandler(console=error_console, show_time=False, show_path=False),
        ],
    )


@app.command()
def export(
    file: GedcomFile,
    out: Annotated[
        Path,
        typer.Option(
            "--out",
            "-o",
            dir_okay=False,
            writable=True,
            help="Where to write the JSON.",
            show_default=False,
        ),
    ],
    indent: Annotated[
        int,
        typer.Option(
            min=0,
            help="Spaces to indent the JSON by; 0 writes it on one line.",
        ),
    ] = 2,
) -> None:
    """Parse a GEDCOM file and write it out as JSON."""
    structure = _parse(file)
    text = json.dumps(
        structure.to_dict(),
        indent=indent or None,
        ensure_ascii=False,
    )

    try:
        out.write_text(f"{text}\n", encoding="utf-8")
    except OSError as error:
        _fail(f"could not write {out}: {error}")

    console.print(
        f"Wrote [bold]{escape(str(out))}[/bold]: "
        f"{_counted(len(structure.individuals), 'individual')}, "
        f"{_counted(len(structure.families), 'family', 'families')}, "
        f"{_counted(len(structure.skipped), 'record')} skipped",
    )


@app.command()
def stats(file: GedcomFile) -> None:
    """Print how much of a GEDCOM file rootsy read."""
    structure = _parse(file)

    console.print(f"[bold]{escape(str(file))}[/bold]")

    table = Table()
    table.add_column("Records")
    table.add_column("Count", justify="right")
    table.add_row("Individuals", str(len(structure.individuals)))
    table.add_row("Families", str(len(structure.families)))
    table.add_row("Sources", str(len(structure.sources)))
    table.add_row("Skipped", str(len(structure.skipped)))
    console.print(table)

    if structure.skipped:
        console.print(f"Skipped: {_skipped_by_tag(structure)}")


def _counted(count: int, singular: str, plural: str | None = None) -> str:
    """Say `1 family` or `3 families`."""
    return f"{count} {singular if count == 1 else plural or f'{singular}s'}"


def _skipped_by_tag(structure: GedcomStructure) -> str:
    """Name the level-0 tags that went unparsed, with how often each came up."""
    counts = collections.Counter(record.tag for record in structure.skipped)
    return ", ".join(f"{tag} x{count}" for tag, count in sorted(counts.items()))


def _parse(file: Path) -> GedcomStructure:
    """Parse a file, turning anything rootsy refuses into a non-zero exit."""
    try:
        return parse_gedcom(file)
    except (RootsyError, OSError, UnicodeDecodeError) as error:
        _fail(str(error))


def _fail(message: str) -> NoReturn:
    """Report a message on stderr and leave with a non-zero status."""
    error_console.print(f"[red]error:[/red] {escape(message)}")
    raise typer.Exit(code=1)
