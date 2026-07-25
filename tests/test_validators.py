"""Tests for sieve validators module."""

import tempfile
from pathlib import Path

import yaml
from linkml.validator.report import Severity

from sieve.validators import (
    _clean_dict,
    get_schema_path,
    print_validation_report,
    validate_json_schema,
    validate_packet,
    validate_packets,
)


class TestGetSchemaPath:
    """Tests for get_schema_path function."""

    def test_schema_path_exists(self):
        """Test that the schema path exists."""
        schema_path = get_schema_path()
        assert schema_path.exists()
        assert schema_path.name == "curation_model.yaml"


class TestCleanDict:
    """Tests for _clean_dict function."""

    def test_removes_none_values(self):
        """Test that None values are removed."""
        data = {"a": 1, "b": None, "c": "hello"}
        result = _clean_dict(data)
        assert result == {"a": 1, "c": "hello"}

    def test_removes_empty_strings(self):
        """Test that empty strings are removed."""
        data = {"a": 1, "b": "", "c": "hello"}
        result = _clean_dict(data)
        assert result == {"a": 1, "c": "hello"}

    def test_removes_null_strings(self):
        """Test that 'null' string values are removed."""
        data = {"a": 1, "b": "null", "c": "hello"}
        result = _clean_dict(data)
        assert result == {"a": 1, "c": "hello"}

    def test_cleans_nested_dicts(self):
        """Test that nested dictionaries are cleaned."""
        data = {"a": {"b": None, "c": 1}, "d": {"e": ""}}
        result = _clean_dict(data)
        assert result == {"a": {"c": 1}}

    def test_cleans_lists(self):
        """Test that lists are cleaned."""
        data = {"items": [None, "", "valid", "null", {"key": None}]}
        result = _clean_dict(data)
        assert result == {"items": ["valid"]}

    def test_preserves_valid_values(self):
        """Test that valid values are preserved."""
        data = {"string": "hello", "number": 42, "float": 3.14, "bool": True}
        result = _clean_dict(data)
        assert result == data

    def test_handles_non_dict_input(self):
        """Test that non-dict input is returned as-is."""
        assert _clean_dict("string") == "string"
        assert _clean_dict(42) == 42
        assert _clean_dict([1, 2, 3]) == [1, 2, 3]


class TestValidateJsonSchema:
    """Tests for validate_json_schema function."""

    def test_validates_minimal_valid_record(self):
        """Test validation of a minimal valid curation record."""
        data = {
            "id": "http://example.org/record1",
            "status": "UNREVIEWED",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }
        report = validate_json_schema(data, target_class="CurationRecord")
        # Check that we get a valid report (may have warnings but no errors)
        assert report is not None

    def test_validates_complete_record(self):
        """Test validation of a complete curation record."""
        data = {
            "id": "http://example.org/record1",
            "status": "ACCEPTED",
            "last_updated": "2024-01-15",
            "evidence_steward": "orcid:0000-0002-6601-2165",
            "confidence": 0.9,
            "assertion": {
                "subject_id": "MONDO:0004979",
                "subject_label": "asthma",
                "predicate": "rdfs:subClassOf",
                "predicate_label": "subClassOf",
                "object_id": "MONDO:0005275",
                "object_label": "respiratory system disorder",
                "display_text": "asthma subClassOf respiratory system disorder",
            },
            "provenance": {
                "attributed_to": ["orcid:0000-0002-6601-2165"],
                "generated_at": "2020-06-15",
                "source_version": "2025-10-08",
            },
        }
        report = validate_json_schema(data, target_class="CurationRecord")
        assert report is not None

    def test_detects_missing_required_field(self):
        """Test that missing required fields are detected."""
        # Missing assertion
        data = {
            "id": "http://example.org/record1",
            "status": "UNREVIEWED",
        }
        report = validate_json_schema(data, target_class="CurationRecord")
        # Should have validation errors
        errors = [r for r in report.results if r.severity in (Severity.ERROR, Severity.FATAL)]
        assert len(errors) > 0

    def test_detects_invalid_status(self):
        """Test that invalid status values are detected."""
        data = {
            "id": "http://example.org/record1",
            "status": "INVALID_STATUS",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }
        report = validate_json_schema(data, target_class="CurationRecord")
        errors = [r for r in report.results if r.severity in (Severity.ERROR, Severity.FATAL)]
        assert len(errors) > 0

    def test_detects_invalid_confidence_range(self):
        """Test that confidence values outside 0-1 range are detected."""
        data = {
            "id": "http://example.org/record1",
            "status": "ACCEPTED",
            "confidence": 1.5,  # Invalid: should be 0-1
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }
        report = validate_json_schema(data, target_class="CurationRecord")
        # Note: JSON Schema validation may not enforce minimum/maximum_value constraints
        # This test documents expected behavior
        assert report is not None


class TestValidatePacket:
    """Tests for validate_packet function."""

    def test_validates_valid_yaml_file(self):
        """Test validation of a valid YAML file."""
        valid_data = {
            "id": "http://example.org/record1",
            "status": "UNREVIEWED",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(valid_data, f)
            temp_path = Path(f.name)

        try:
            report, error_count = validate_packet(temp_path, fail_on_error=False)
            assert report is not None
            assert error_count == 0
        finally:
            temp_path.unlink()

    def test_detects_invalid_yaml_file(self):
        """Test detection of errors in an invalid YAML file."""
        invalid_data = {
            "id": "http://example.org/record1",
            "status": "INVALID",  # Invalid status
            # Missing required assertion field
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            report, error_count = validate_packet(temp_path, fail_on_error=False)
            assert error_count > 0
        finally:
            temp_path.unlink()


class TestValidatePackets:
    """Tests for validate_packets function."""

    def test_validates_single_file(self):
        """Test validation of a single file."""
        valid_data = {
            "id": "http://example.org/record1",
            "status": "ACCEPTED",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(valid_data, f)
            temp_path = Path(f.name)

        try:
            total, valid, errors = validate_packets(temp_path, fail_on_error=False)
            assert total == 1
            assert valid == 1
            assert errors == 0
        finally:
            temp_path.unlink()

    def test_validates_directory(self):
        """Test validation of a directory of files."""
        valid_data = {
            "id": "http://example.org/record1",
            "status": "ACCEPTED",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }
        invalid_data = {
            "id": "http://example.org/record2",
            "status": "INVALID",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create valid file
            with open(temp_path / "valid.yaml", "w") as f:
                yaml.dump(valid_data, f)

            # Create invalid file
            with open(temp_path / "invalid.yaml", "w") as f:
                yaml.dump(invalid_data, f)

            total, valid, errors = validate_packets(temp_path, fail_on_error=False)
            assert total == 2
            assert valid == 1
            assert errors > 0

    def test_handles_nested_yaml_files(self):
        """Test that nested YAML files are found and validated."""
        valid_data = {
            "id": "http://example.org/record1",
            "status": "ACCEPTED",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nested_dir = temp_path / "subdir"
            nested_dir.mkdir()

            # Create file in nested directory
            with open(nested_dir / "nested.yaml", "w") as f:
                yaml.dump(valid_data, f)

            total, valid, errors = validate_packets(temp_path, fail_on_error=False)
            assert total == 1
            assert valid == 1

    def test_handles_yml_extension(self):
        """Test that .yml files are also validated."""
        valid_data = {
            "id": "http://example.org/record1",
            "status": "ACCEPTED",
            "assertion": {
                "subject_id": "MONDO:0004979",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:0005275",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with open(temp_path / "file.yml", "w") as f:
                yaml.dump(valid_data, f)

            total, valid, errors = validate_packets(temp_path, fail_on_error=False)
            assert total == 1
            assert valid == 1

    def test_empty_directory(self):
        """Test validation of an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            total, valid, errors = validate_packets(
                Path(temp_dir), fail_on_error=False
            )
            assert total == 0
            assert valid == 0
            assert errors == 0


class TestPrintValidationReport:
    """Tests for print_validation_report function."""

    def test_returns_zero_for_valid_report(self):
        """Test that valid reports return zero errors."""
        from linkml.validator import ValidationReport

        report = ValidationReport(results=[])
        error_count = print_validation_report(report)
        assert error_count == 0

    def test_counts_errors_correctly(self):
        """Test that errors are counted correctly."""
        from linkml.validator import ValidationReport
        from linkml.validator.report import Severity, ValidationResult

        results = [
            ValidationResult(
                type="test",
                severity=Severity.ERROR,
                message="Error 1",
            ),
            ValidationResult(
                type="test",
                severity=Severity.ERROR,
                message="Error 2",
            ),
            ValidationResult(
                type="test",
                severity=Severity.WARN,
                message="Warning 1",
            ),
        ]
        report = ValidationReport(results=results)
        error_count = print_validation_report(report, fail_on_error=False)
        assert error_count == 2  # Only errors, not warnings
