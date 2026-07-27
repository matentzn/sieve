"""CLI interface for sieve."""

from pathlib import Path
from typing import Optional

import typer
import yaml
from typing_extensions import Annotated

app = typer.Typer(
    help="sieve: Scientific Evidence Evaluation & Verification Environment",
    no_args_is_help=True,
)


@app.command()
def run():
    """Run the Sieve web application."""
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/sieve/app.py"])


@app.command()
def ingest(
    input_dir: Annotated[
        Path,
        typer.Option(
            "-I", "--input-dir",
            help="Directory of YAML EvidencePackets to ingest",
            exists=True,
            dir_okay=True,
            file_okay=False,
        ),
    ] = Path("inbox/"),
    db_path: Annotated[
        str,
        typer.Option("--db", help="Path to the DuckDB database file"),
    ] = "data/sieve.duckdb",
):
    """Ingest YAML EvidencePackets into the database.

    Examples:

        sieve ingest -I inbox/examples/
    """
    from sieve.packet_ingest import ingest_packet_directory
    from sieve.store import PacketStore

    store = PacketStore(db_path)
    stats = ingest_packet_directory(input_dir, store)
    typer.echo(f"Ingested {stats['success']} of {stats['files']} packets")
    if stats["errors"]:
        typer.echo(f"Errors: {stats['errors']}", err=True)
        for err in stats["error_details"]:
            typer.echo(f"  {err['file']}: {err['error']}", err=True)


@app.command()
def export(
    input: Annotated[
        Optional[Path],
        typer.Option(
            "-i", "--input",
            help="Input YAML file (single EvidencePacket)",
            exists=True, dir_okay=False, file_okay=True,
        ),
    ] = None,
    input_dir: Annotated[
        Optional[Path],
        typer.Option(
            "-I", "--input-dir",
            help="Directory of YAML EvidencePackets",
            exists=True, dir_okay=True, file_okay=False,
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("-o", "--output", help="Output file path"),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("-O", "--output-format", help="rdf (turtle), xml, n3, nt, yaml"),
    ] = "rdf",
):
    """Export EvidencePackets to RDF or YAML.

    Examples:

        sieve export -I exports/accepted/ -O rdf -o accepted.ttl
    """
    from sieve.datamodel.loaders import load_packet
    from sieve.packet_export import export_packets_to_rdf, export_packets_to_yaml

    if input is None and input_dir is None:
        typer.echo("Error: specify either -i/--input or -I/--input-dir", err=True)
        raise typer.Exit(code=1)

    if input is not None:
        paths = [input]
    else:
        assert input_dir is not None
        paths = sorted(input_dir.glob("**/*.yaml")) + sorted(input_dir.glob("**/*.yml"))
    packets = [load_packet(p) for p in paths]

    rdf_formats = {"rdf": "turtle", "turtle": "turtle", "ttl": "turtle",
                   "xml": "xml", "rdfxml": "xml", "n3": "n3", "nt": "nt", "ntriples": "nt"}
    fmt = output_format.lower()
    if fmt in rdf_formats:
        result = export_packets_to_rdf(packets, output, format=rdf_formats[fmt])
        typer.echo(f"Exported to {output}" if output else result)
    elif fmt == "yaml":
        if output is None:
            typer.echo("Error: -o/--output is required for YAML export", err=True)
            raise typer.Exit(code=1)
        export_packets_to_yaml(packets, output)
        typer.echo(f"Exported to {output}")
    else:
        typer.echo(f"Error: unknown output format '{output_format}'", err=True)
        raise typer.Exit(code=1)


@app.command()
def validate(
    input: Annotated[
        Optional[Path],
        typer.Option(
            "-i", "--input",
            help="Input YAML file (single EvidencePacket)",
            exists=True, dir_okay=False, file_okay=True,
        ),
    ] = None,
    input_dir: Annotated[
        Optional[Path],
        typer.Option(
            "-I", "--input-dir",
            help="Directory of YAML EvidencePackets",
            exists=True, dir_okay=True, file_okay=False,
        ),
    ] = None,
):
    """Validate EvidencePackets against the SIEVE schema.

    Examples:

        sieve validate -I inbox/examples/
    """
    from sieve.packet_ingest import validate_packet_dict

    if input is None and input_dir is None:
        typer.echo("Error: specify either -i/--input or -I/--input-dir", err=True)
        raise typer.Exit(code=1)

    if input is not None:
        paths = [input]
    else:
        assert input_dir is not None
        paths = sorted(input_dir.glob("**/*.yaml")) + sorted(input_dir.glob("**/*.yml"))

    total_errors = 0
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        results = validate_packet_dict(data)
        status = "OK" if not results else f"{len(results)} error(s)"
        typer.echo(f"  {path}: {status}")
        total_errors += len(results)

    typer.echo(f"\nValidated {len(paths)} file(s); {total_errors} total error(s)")
    if total_errors:
        raise typer.Exit(code=1)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
