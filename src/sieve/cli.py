"""CLI interface for sieve."""

from pathlib import Path
from typing import Optional

import typer
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
def export(
    input: Annotated[
        Optional[Path],
        typer.Option(
            "-i", "--input",
            help="Input YAML file (single evidence packet)",
            exists=True,
            dir_okay=False,
            file_okay=True,
        ),
    ] = None,
    input_dir: Annotated[
        Optional[Path],
        typer.Option(
            "-I", "--input-dir",
            help="Input directory containing YAML evidence packets",
            exists=True,
            dir_okay=True,
            file_okay=False,
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o", "--output",
            help="Output file path",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "-O", "--output-format",
            help="Output format: rdf (turtle), xml, n3, nt, yaml",
        ),
    ] = "rdf",
):
    """Export evidence packets to various formats.

    Examples:

        # Export single file to RDF (turtle)
        sieve export -i packet.yaml -O rdf -o output.ttl

        # Export directory to RDF
        sieve export -I packets/ -O rdf -o output.ttl

        # Export to RDF/XML format
        sieve export -i packet.yaml -O xml -o output.rdf
    """
    # Validate input
    if input is None and input_dir is None:
        typer.echo("Error: Must specify either -i/--input or -I/--input-dir", err=True)
        raise typer.Exit(code=1)

    if input is not None and input_dir is not None:
        typer.echo("Error: Cannot specify both -i/--input and -I/--input-dir", err=True)
        raise typer.Exit(code=1)

    input_path = input if input is not None else input_dir
    assert input_path is not None  # guaranteed by the checks above

    # Map output format to rdflib format
    format_map = {
        "rdf": "turtle",
        "turtle": "turtle",
        "ttl": "turtle",
        "xml": "xml",
        "rdfxml": "xml",
        "n3": "n3",
        "nt": "nt",
        "ntriples": "nt",
    }

    if output_format.lower() in format_map:
        # RDF export
        from sieve.rdf_export import export_to_rdf

        rdf_format = format_map[output_format.lower()]
        result = export_to_rdf(input_path, output, format=rdf_format)

        if output:
            typer.echo(f"Exported to {output}")
        else:
            typer.echo(result)

    elif output_format.lower() == "yaml":
        # YAML export (just copy/combine)
        from sieve.rdf_export import iter_packets

        import yaml

        packets = [packet for _, packet in iter_packets(input_path)]

        if len(packets) == 1:
            yaml_str = yaml.dump(packets[0], default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            yaml_str = yaml.dump_all(packets, default_flow_style=False, allow_unicode=True, sort_keys=False)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(yaml_str)
            typer.echo(f"Exported to {output}")
        else:
            typer.echo(yaml_str)

    else:
        typer.echo(f"Error: Unknown output format '{output_format}'", err=True)
        typer.echo("Supported formats: rdf, turtle, ttl, xml, rdfxml, n3, nt, ntriples, yaml", err=True)
        raise typer.Exit(code=1)


@app.command()
def ingest(
    input_dir: Annotated[
        Path,
        typer.Option(
            "-I", "--input-dir",
            help="Input directory containing YAML files to ingest",
            exists=True,
            dir_okay=True,
            file_okay=False,
        ),
    ] = Path("inbox/"),
    db_path: Annotated[
        str,
        typer.Option(
            "--db",
            help="Path to the DuckDB database file",
        ),
    ] = "data/curation.duckdb",
):
    """Ingest YAML evidence packets into the database.

    Examples:

        # Ingest from default inbox directory
        sieve ingest

        # Ingest from specific directory
        sieve ingest -I /path/to/packets/
    """
    from sieve.db import CurationDatabase
    from sieve.ingest import ingest_directory

    db = CurationDatabase(db_path)
    stats = ingest_directory(input_dir, db)

    typer.echo(f"Ingested {stats['success']} new records")
    if stats["skipped"] > 0:
        typer.echo(f"Skipped {stats['skipped']} existing records")
    if stats["errors"] > 0:
        typer.echo(f"Errors: {stats['errors']}", err=True)
        for err in stats.get("error_details", []):
            typer.echo(f"  {err['file']}: {err['error']}", err=True)


@app.command()
def validate(
    input: Annotated[
        Optional[Path],
        typer.Option(
            "-i", "--input",
            help="Input YAML file (single evidence packet)",
            exists=True,
            dir_okay=False,
            file_okay=True,
        ),
    ] = None,
    input_dir: Annotated[
        Optional[Path],
        typer.Option(
            "-I", "--input-dir",
            help="Input directory containing YAML evidence packets",
            exists=True,
            dir_okay=True,
            file_okay=False,
        ),
    ] = None,
):
    """Validate evidence packets against the LinkML schema.

    Validates YAML evidence packets to ensure they conform to the
    curation_model.yaml LinkML schema.

    Examples:

        # Validate a single file
        sieve validate -i packet.yaml

        # Validate all files in a directory
        sieve validate -I packets/

        # Validate exported packets
        sieve validate -I exports/accepted/
    """
    from sieve.validators import validate_packets

    # Validate input
    if input is None and input_dir is None:
        typer.echo("Error: Must specify either -i/--input or -I/--input-dir", err=True)
        raise typer.Exit(code=1)

    if input is not None and input_dir is not None:
        typer.echo("Error: Cannot specify both -i/--input and -I/--input-dir", err=True)
        raise typer.Exit(code=1)

    input_path = input if input is not None else input_dir
    assert input_path is not None  # guaranteed by the checks above

    total_files, valid_files, total_errors = validate_packets(input_path)

    # Print summary
    typer.echo("\nValidation Summary:")
    typer.echo(f"  Total files:  {total_files}")
    typer.echo(f"  Valid files:  {valid_files}")
    typer.echo(f"  Total errors: {total_errors}")

    if total_errors > 0:
        raise typer.Exit(code=1)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
