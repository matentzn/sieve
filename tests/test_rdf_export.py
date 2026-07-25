"""Tests for RDF export functionality."""

from pathlib import Path

import pytest
from rdflib import OWL, RDFS, Graph, Literal, Namespace

from sieve.rdf_export import (
    expand_curie,
    export_to_rdf,
    get_obo_converter,
    iter_packets,
    load_packet,
    packet_to_rdf,
)

SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")


@pytest.fixture
def sample_packet():
    """Create a sample evidence packet."""
    return {
        "id": "http://purl.org/np/RA1234567890",
        "status": "ACCEPTED",
        "evidence_steward": "orcid:0000-0001-2345-6789",
        "confidence": 0.85,
        "assertion": {
            "subject_id": "MONDO:0005015",
            "subject_label": "diabetes mellitus",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0005151",
            "object_label": "endocrine system disorder",
        },
    }


@pytest.fixture
def converter():
    """Get the OBO converter."""
    return get_obo_converter()


def test_expand_curie_mondo(converter):
    """Test CURIE expansion for MONDO terms."""
    result = expand_curie("MONDO:0005015", converter)
    assert result is not None
    assert str(result) == "http://purl.obolibrary.org/obo/MONDO_0005015"


def test_expand_curie_orcid(converter):
    """Test CURIE expansion for ORCID."""
    result = expand_curie("orcid:0000-0001-2345-6789", converter)
    assert result is not None
    assert str(result) == "https://orcid.org/0000-0001-2345-6789"


def test_expand_curie_rdfs(converter):
    """Test CURIE expansion for rdfs:subClassOf."""
    result = expand_curie("rdfs:subClassOf", converter)
    assert result is not None
    assert str(result) == str(RDFS.subClassOf)


def test_expand_curie_uri(converter):
    """Test that full URIs are passed through."""
    uri = "http://example.org/test"
    result = expand_curie(uri, converter)
    assert result is not None
    assert str(result) == uri


def test_expand_curie_none(converter):
    """Test that None/empty returns None."""
    assert expand_curie(None, converter) is None
    assert expand_curie("", converter) is None


def test_packet_to_rdf_basic(sample_packet):
    """Test basic packet to RDF conversion."""
    graph = packet_to_rdf(sample_packet)

    # Should have exactly one axiom
    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 1

    axiom = axioms[0]

    # Check the axiom type
    assert (axiom, OWL.annotatedProperty, RDFS.subClassOf) in graph

    # Check subject and object
    subjects = list(graph.objects(axiom, OWL.annotatedSource))
    assert len(subjects) == 1
    assert "MONDO_0005015" in str(subjects[0])

    objects = list(graph.objects(axiom, OWL.annotatedTarget))
    assert len(objects) == 1
    assert "MONDO_0005151" in str(objects[0])

    # Check SEPIO reference
    sepio_refs = list(graph.objects(axiom, SEPIO["0000124"]))
    assert len(sepio_refs) == 1
    assert "RA1234567890" in str(sepio_refs[0])


def test_packet_to_rdf_with_evidence_steward(sample_packet):
    """Test that evidence steward is included in RDF."""
    graph = packet_to_rdf(sample_packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    # Check oboInOwl:source (evidence steward)
    sources = list(graph.objects(axiom, OBOINOWL.source))
    assert len(sources) == 1
    assert "0000-0001-2345-6789" in str(sources[0])


def test_packet_to_rdf_without_steward():
    """Test RDF export without evidence steward."""
    packet = {
        "id": "test-001",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    # Should not have oboInOwl:source
    sources = list(graph.objects(axiom, OBOINOWL.source))
    assert len(sources) == 0


def test_packet_to_rdf_adds_to_existing_graph(sample_packet):
    """Test that packet_to_rdf can add to an existing graph."""
    graph = Graph()

    # Add first packet
    packet1 = sample_packet.copy()
    packet1["id"] = "test-001"
    packet_to_rdf(packet1, graph)

    # Add second packet
    packet2 = {
        "id": "test-002",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0003",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0004",
        },
    }
    packet_to_rdf(packet2, graph)

    # Should have two axioms
    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 2


def test_load_packet(tmp_path):
    """Test loading a packet from a YAML file."""
    yaml_content = """
id: test-load-001
status: ACCEPTED
assertion:
  subject_id: MONDO:0001
  predicate: rdfs:subClassOf
  object_id: MONDO:0002
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    packet = load_packet(yaml_file)
    assert packet["id"] == "test-load-001"
    assert packet["assertion"]["subject_id"] == "MONDO:0001"


def test_iter_packets_single_file(tmp_path):
    """Test iterating over a single file."""
    yaml_content = """
id: test-iter-001
status: ACCEPTED
assertion:
  subject_id: MONDO:0001
  predicate: rdfs:subClassOf
  object_id: MONDO:0002
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    packets = list(iter_packets(yaml_file))
    assert len(packets) == 1
    path, packet = packets[0]
    assert packet["id"] == "test-iter-001"


def test_iter_packets_directory(tmp_path):
    """Test iterating over a directory of files."""
    for i in range(3):
        yaml_content = f"""
id: test-dir-{i:03d}
status: ACCEPTED
assertion:
  subject_id: MONDO:000{i}
  predicate: rdfs:subClassOf
  object_id: MONDO:9999
"""
        yaml_file = tmp_path / f"test_{i}.yaml"
        yaml_file.write_text(yaml_content)

    packets = list(iter_packets(tmp_path))
    assert len(packets) == 3

    ids = [p["id"] for _, p in packets]
    assert "test-dir-000" in ids
    assert "test-dir-001" in ids
    assert "test-dir-002" in ids


def test_iter_packets_nested_directory(tmp_path):
    """Test iterating over nested directories."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    # Root file
    (tmp_path / "root.yaml").write_text("""
id: root-001
status: ACCEPTED
assertion:
  subject_id: MONDO:0001
  predicate: rdfs:subClassOf
  object_id: MONDO:0002
""")

    # Nested file
    (subdir / "nested.yaml").write_text("""
id: nested-001
status: REJECTED
assertion:
  subject_id: MONDO:0003
  predicate: rdfs:subClassOf
  object_id: MONDO:0004
""")

    packets = list(iter_packets(tmp_path))
    assert len(packets) == 2

    ids = [p["id"] for _, p in packets]
    assert "root-001" in ids
    assert "nested-001" in ids


def test_export_to_rdf_single_file(tmp_path):
    """Test exporting a single file to RDF."""
    yaml_content = """
id: http://purl.org/np/RA9999
status: ACCEPTED
assertion:
  subject_id: MONDO:0001
  predicate: rdfs:subClassOf
  object_id: MONDO:0002
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    output_file = tmp_path / "output.ttl"
    result = export_to_rdf(yaml_file, output_file)

    # Check file was created
    assert output_file.exists()

    # Check content
    assert "@prefix" in result
    assert "owl:Axiom" in result
    assert "MONDO_0001" in result
    assert "MONDO_0002" in result
    assert "RA9999" in result


def test_export_to_rdf_directory(tmp_path):
    """Test exporting a directory to RDF."""
    for i in range(2):
        yaml_content = f"""
id: http://purl.org/np/RA{i:04d}
status: ACCEPTED
assertion:
  subject_id: MONDO:000{i}
  predicate: rdfs:subClassOf
  object_id: MONDO:999{i}
"""
        (tmp_path / f"test_{i}.yaml").write_text(yaml_content)

    output_file = tmp_path / "output.ttl"
    result = export_to_rdf(tmp_path, output_file)

    # Should contain both axioms
    assert "MONDO_0000" in result
    assert "MONDO_0001" in result
    assert "RA0000" in result
    assert "RA0001" in result


def test_export_to_rdf_no_output_file(tmp_path):
    """Test exporting without output file (returns string)."""
    yaml_content = """
id: test-no-output
status: ACCEPTED
assertion:
  subject_id: MONDO:0001
  predicate: rdfs:subClassOf
  object_id: MONDO:0002
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    result = export_to_rdf(yaml_file)

    # Should return turtle string
    assert "@prefix" in result
    assert "owl:Axiom" in result


def test_export_to_rdf_xml_format(tmp_path):
    """Test exporting to RDF/XML format."""
    yaml_content = """
id: test-xml
status: ACCEPTED
assertion:
  subject_id: MONDO:0001
  predicate: rdfs:subClassOf
  object_id: MONDO:0002
"""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    result = export_to_rdf(yaml_file, format="xml")

    # Should be XML format
    assert "<?xml" in result or "<rdf:RDF" in result


def test_packet_to_rdf_accepted_concordance_evidence():
    """Test that accepted concordance evidence adds additional oboInOwl:source literals."""
    packet = {
        "id": "test-concordance",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence": [
            {
                "evidence_type": "CONCORDANCE",
                "direction": "SUPPORTS",
                "rating": "ACCEPTED",
                "publication_id": "PMID:12345",
                "source_subject_id": "DOID:1234",
                "reviewer_orcid": "orcid:0000-0001-2345-6789",
            },
        ],
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    # Get all oboInOwl:source values
    sources = list(graph.objects(axiom, OBOINOWL.source))

    # Should have 3 literal sources from the concordance evidence
    literal_sources = [str(s) for s in sources if isinstance(s, Literal)]
    assert "PMID:12345" in literal_sources
    assert "DOID:1234" in literal_sources
    assert "orcid:0000-0001-2345-6789" in literal_sources


def test_packet_to_rdf_concordance_not_accepted():
    """Test that non-accepted concordance evidence doesn't add extra sources."""
    packet = {
        "id": "test-not-accepted",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence": [
            {
                "evidence_type": "CONCORDANCE",
                "direction": "SUPPORTS",
                "rating": "REJECTED",  # Not ACCEPTED
                "publication_id": "PMID:12345",
                "source_subject_id": "DOID:1234",
            },
        ],
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    # Get all oboInOwl:source values
    sources = list(graph.objects(axiom, OBOINOWL.source))

    # Should have no literal sources (only URI if evidence_steward was set)
    literal_sources = [s for s in sources if isinstance(s, Literal)]
    assert len(literal_sources) == 0


def test_packet_to_rdf_concordance_contradicts():
    """Test that CONTRADICTS concordance evidence doesn't add extra sources."""
    packet = {
        "id": "test-contradicts",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence": [
            {
                "evidence_type": "CONCORDANCE",
                "direction": "CONTRADICTS",  # Not SUPPORTS
                "rating": "ACCEPTED",
                "publication_id": "PMID:12345",
                "source_subject_id": "DOID:1234",
            },
        ],
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    sources = list(graph.objects(axiom, OBOINOWL.source))
    literal_sources = [s for s in sources if isinstance(s, Literal)]
    assert len(literal_sources) == 0


def test_packet_to_rdf_literature_evidence_adds_publication_id():
    """Test that LITERATURE evidence adds publication_id when accepted."""
    packet = {
        "id": "test-literature",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence": [
            {
                "evidence_type": "LITERATURE",
                "direction": "SUPPORTS",
                "rating": "ACCEPTED",
                "publication_id": "PMID:12345",
            },
        ],
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    sources = list(graph.objects(axiom, OBOINOWL.source))
    literal_sources = [str(s) for s in sources if isinstance(s, Literal)]
    assert "PMID:12345" in literal_sources


def test_packet_to_rdf_literature_source_subject_not_added():
    """Test that LITERATURE evidence doesn't add source_subject_id (only CONCORDANCE does)."""
    packet = {
        "id": "test-literature-no-source-subject",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence": [
            {
                "evidence_type": "LITERATURE",
                "direction": "SUPPORTS",
                "rating": "ACCEPTED",
                "source_subject_id": "DOID:1234",  # This shouldn't be added for LITERATURE
            },
        ],
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    sources = list(graph.objects(axiom, OBOINOWL.source))
    literal_sources = [str(s) for s in sources if isinstance(s, Literal)]
    assert "DOID:1234" not in literal_sources


def test_packet_to_rdf_concordance_partial_fields():
    """Test concordance evidence with only some fields present."""
    packet = {
        "id": "test-partial",
        "status": "ACCEPTED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence": [
            {
                "evidence_type": "CONCORDANCE",
                "direction": "SUPPORTS",
                "rating": "ACCEPTED",
                "source_subject_id": "DOID:5678",
                # No publication_id or reviewer_orcid
            },
        ],
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    axiom = axioms[0]

    sources = list(graph.objects(axiom, OBOINOWL.source))
    literal_sources = [str(s) for s in sources if isinstance(s, Literal)]

    # Should only have source_subject_id
    assert len(literal_sources) == 1
    assert "DOID:5678" in literal_sources


def test_packet_to_rdf_no_status_skipped(capsys):
    """Test that packets without status are skipped with a warning."""
    packet = {
        "id": "test-no-status",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }

    graph = Graph()
    result = packet_to_rdf(packet, graph)

    # Graph should be returned but empty (no axiom added)
    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 0

    # Check warning was printed
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "test-no-status" in captured.err
    assert "no status field" in captured.err


def test_packet_to_rdf_unreviewed_status_skipped(capsys):
    """Test that packets with UNREVIEWED status are skipped."""
    packet = {
        "id": "test-unreviewed",
        "status": "UNREVIEWED",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }

    graph = Graph()
    result = packet_to_rdf(packet, graph)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 0

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "UNREVIEWED" in captured.err


def test_packet_to_rdf_rejected_status():
    """Test that REJECTED packets use IAO:0000233 property."""
    packet = {
        "id": "http://purl.org/np/RA_REJECTED",
        "status": "REJECTED",
        "evidence_steward": "orcid:0000-0001-2345-6789",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 1
    axiom = axioms[0]

    # Should have IAO:0000233 (term tracker item)
    tracker_items = list(graph.objects(axiom, IAO["0000233"]))
    assert len(tracker_items) == 1
    assert "RA_REJECTED" in str(tracker_items[0])

    # Should still have evidence steward
    sources = list(graph.objects(axiom, OBOINOWL.source))
    assert len(sources) == 1


def test_packet_to_rdf_controversial_status():
    """Test that CONTROVERSIAL packets get rdfs:comment and IAO:0000233."""
    packet = {
        "id": "http://purl.org/np/RA_CONTROVERSIAL",
        "status": "CONTROVERSIAL",
        "evidence_steward": "orcid:0000-0001-2345-6789",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }

    graph = packet_to_rdf(packet)

    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 1
    axiom = axioms[0]

    # Should have rdfs:comment
    comments = list(graph.objects(axiom, RDFS.comment))
    assert len(comments) == 1
    assert "CONTROVERSIAL" in str(comments[0])

    # Should have IAO:0000233
    tracker_items = list(graph.objects(axiom, IAO["0000233"]))
    assert len(tracker_items) == 1

    # Should still have evidence steward
    sources = list(graph.objects(axiom, OBOINOWL.source))
    assert len(sources) == 1
