"""Validators for evidence packets using LinkML schema."""

import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from linkml.validator import ValidationReport, Validator
from linkml.validator.plugins import JsonschemaValidationPlugin
from linkml.validator.report import Severity

# Path to the schema file
SCHEMA_PATH = Path(__file__).parent.parent.parent / "schema" / "curation_model.yaml"


def get_schema_path() -> Path:
    """Get the path to the LinkML schema file.

    Returns:
        Path to the curation_model.yaml schema file
    """
    if SCHEMA_PATH.exists():
        return SCHEMA_PATH
    # Fallback for installed package
    import importlib.resources

    try:
        resource = importlib.resources.files("sieve").joinpath(
            "../schema/curation_model.yaml"
        )
        with importlib.resources.as_file(resource) as p:
            return Path(p)
    except (TypeError, FileNotFoundError):
        raise FileNotFoundError(
            f"Schema file not found at {SCHEMA_PATH}. "
            "Please ensure the schema/curation_model.yaml file exists."
        )


def _clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove key-value pairs where value is None, "null", or empty string.

    This is needed because LinkML validator may complain about null values.

    Args:
        d: The dictionary to clean

    Returns:
        A cleaned dictionary with unwanted values removed
    """
    if not isinstance(d, dict):
        return d

    cleaned_dict: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            cleaned_value = _clean_dict(v)
            if cleaned_value:
                cleaned_dict[k] = cleaned_value
        elif isinstance(v, list):
            cleaned_list = [
                _clean_dict(item) if isinstance(item, dict) else item for item in v
            ]
            cleaned_list = [
                item for item in cleaned_list if item not in [None, "", "null", {}]
            ]
            if cleaned_list:
                cleaned_dict[k] = cleaned_list
        elif v not in [None, "", "null"]:
            cleaned_dict[k] = v

    return cleaned_dict


def print_validation_report(
    report: ValidationReport, file_path: Path | None = None, fail_on_error: bool = True
) -> int:
    """Print validation results from a LinkML ValidationReport.

    Args:
        report: The LinkML validation report
        file_path: Optional path to the file being validated (for error messages)
        fail_on_error: If True, return non-zero exit code on errors

    Returns:
        Number of validation errors found
    """
    error_count = 0
    file_info = f" ({file_path})" if file_path else ""

    if not report.results:
        logging.info(f"Validation passed{file_info}")
        return 0

    for result in report.results:
        if result.severity in (Severity.FATAL, Severity.ERROR):
            error_count += 1
            print(f"ERROR{file_info}: {result.message}", file=sys.stderr)
        elif result.severity == Severity.WARN:
            print(f"WARNING{file_info}: {result.message}", file=sys.stderr)
        elif result.severity == Severity.INFO:
            logging.info(f"INFO{file_info}: {result.message}")

    return error_count


def validate_json_schema(
    data: dict[str, Any],
    target_class: str = "CurationRecord",
    fail_on_error: bool = True,
) -> ValidationReport:
    """Validate a dictionary against the LinkML JSON Schema.

    Args:
        data: The dictionary to validate
        target_class: The LinkML class to validate against
        fail_on_error: If True, raise exception on validation errors

    Returns:
        LinkML ValidationReport with validation results
    """
    schema_path = get_schema_path()

    validator = Validator(
        schema=str(schema_path),
        validation_plugins=[JsonschemaValidationPlugin(closed=False)],
    )

    # Clean the data to remove null values
    cleaned_data = _clean_dict(data)

    report = validator.validate(cleaned_data, target_class)
    return report


def validate_packet(
    packet_path: Path,
    fail_on_error: bool = True,
) -> tuple[ValidationReport, int]:
    """Validate a single evidence packet YAML file.

    Args:
        packet_path: Path to the YAML file
        fail_on_error: If True, print errors to stderr

    Returns:
        Tuple of (ValidationReport, error_count)
    """
    with open(packet_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    report = validate_json_schema(data, target_class="CurationRecord")
    error_count = print_validation_report(
        report, file_path=packet_path, fail_on_error=fail_on_error
    )

    return report, error_count


def validate_packets(
    input_path: Path,
    fail_on_error: bool = True,
) -> tuple[int, int, int]:
    """Validate one or more evidence packet YAML files.

    Args:
        input_path: Path to a YAML file or directory containing YAML files
        fail_on_error: If True, print errors to stderr

    Returns:
        Tuple of (total_files, valid_files, total_errors)
    """
    input_path = Path(input_path)
    total_files = 0
    valid_files = 0
    total_errors = 0

    if input_path.is_file():
        files = [input_path]
    else:
        files = list(input_path.glob("**/*.yaml")) + list(input_path.glob("**/*.yml"))

    for file_path in sorted(files):
        total_files += 1
        try:
            _, error_count = validate_packet(file_path, fail_on_error=fail_on_error)
            total_errors += error_count
            if error_count == 0:
                valid_files += 1
        except Exception as e:
            total_errors += 1
            print(f"ERROR ({file_path}): Failed to parse: {e}", file=sys.stderr)

    return total_files, valid_files, total_errors
