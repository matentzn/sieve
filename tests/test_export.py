"""Tests for RDF export functionality."""

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

from sieve.export import create_owl_axiom_annotation, expand_curie

# Namespaces used in tests
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
ORCID = Namespace("https://orcid.org/")


def test_expand_curie_mondo():
    """Test CURIE expansion for MONDO IDs."""
    assert expand_curie("MONDO:0000005") == "http://purl.obolibrary.org/obo/MONDO_0000005"


def test_expand_curie_orcid():
    """Test CURIE expansion for ORCID IDs."""
    assert expand_curie("orcid:0000-0002-5002-8648") == "https://orcid.org/0000-0002-5002-8648"


def test_expand_curie_rdfs():
    """Test CURIE expansion for rdfs predicates."""
    assert expand_curie("rdfs:subClassOf") == "http://www.w3.org/2000/01/rdf-schema#subClassOf"


def test_expand_curie_already_uri():
    """Test that full URIs are returned unchanged."""
    uri = "http://example.org/test"
    assert expand_curie(uri) == uri


def test_create_owl_axiom_annotation_basic():
    """Test creating a basic OWL axiom annotation."""
    g = Graph()
    subject = URIRef("http://purl.obolibrary.org/obo/MONDO_0000005")
    predicate = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    obj = URIRef("http://purl.obolibrary.org/obo/MONDO_0100118")

    axiom = create_owl_axiom_annotation(g, subject, predicate, obj)

    # Check axiom type
    assert (axiom, RDF.type, OWL.Axiom) in g

    # Check annotated triple components
    assert (axiom, OWL.annotatedSource, subject) in g
    assert (axiom, OWL.annotatedProperty, predicate) in g
    assert (axiom, OWL.annotatedTarget, obj) in g


def test_create_owl_axiom_annotation_with_curator():
    """Test OWL axiom annotation with curator ORCID."""
    g = Graph()
    subject = URIRef("http://purl.obolibrary.org/obo/MONDO_0000005")
    predicate = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    obj = URIRef("http://purl.obolibrary.org/obo/MONDO_0100118")

    axiom = create_owl_axiom_annotation(
        g, subject, predicate, obj,
        curator_orcid="0000-0002-5002-8648"
    )

    # Check oboInOwl:source points to ORCID
    curator_uri = ORCID["0000-0002-5002-8648"]
    assert (axiom, OBOINOWL.source, curator_uri) in g


def test_create_owl_axiom_annotation_with_orcid_prefix():
    """Test that orcid: prefix is handled correctly."""
    g = Graph()
    subject = URIRef("http://purl.obolibrary.org/obo/MONDO_0000005")
    predicate = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    obj = URIRef("http://purl.obolibrary.org/obo/MONDO_0100118")

    axiom = create_owl_axiom_annotation(
        g, subject, predicate, obj,
        curator_orcid="orcid:0000-0002-5002-8648"
    )

    # Check oboInOwl:source points to ORCID (prefix stripped)
    curator_uri = ORCID["0000-0002-5002-8648"]
    assert (axiom, OBOINOWL.source, curator_uri) in g


def test_create_owl_axiom_annotation_with_evidence():
    """Test OWL axiom annotation with evidence reference."""
    g = Graph()
    subject = URIRef("http://purl.obolibrary.org/obo/MONDO_0000005")
    predicate = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    obj = URIRef("http://purl.obolibrary.org/obo/MONDO_0100118")
    evidence_uri = "https://evidence.monarchinitiative.org/record-123"

    axiom = create_owl_axiom_annotation(
        g, subject, predicate, obj,
        evidence_id=evidence_uri
    )

    # Check SEPIO:0000124 (has_evidence) points to evidence
    assert (axiom, SEPIO["0000124"], URIRef(evidence_uri)) in g


def test_create_owl_axiom_annotation_full():
    """Test OWL axiom annotation with all fields."""
    g = Graph()
    subject = URIRef("http://purl.obolibrary.org/obo/MONDO_0000005")
    predicate = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    obj = URIRef("http://purl.obolibrary.org/obo/MONDO_0100118")

    axiom = create_owl_axiom_annotation(
        g, subject, predicate, obj,
        curator_orcid="0000-0002-5002-8648",
        evidence_id="https://evidence.monarchinitiative.org/record-123"
    )

    # Verify the graph is valid RDF by serializing to turtle
    turtle_output = g.serialize(format="turtle")
    assert "owl:Axiom" in turtle_output
    assert "owl:annotatedSource" in turtle_output
    assert "owl:annotatedProperty" in turtle_output
    assert "owl:annotatedTarget" in turtle_output

    # Verify it can also be serialized to RDF/XML
    xml_output = g.serialize(format="xml")
    assert "Axiom" in xml_output


def test_owl_axiom_roundtrip():
    """Test that exported RDF can be parsed back."""
    g = Graph()
    subject = URIRef("http://purl.obolibrary.org/obo/MONDO_0000005")
    predicate = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    obj = URIRef("http://purl.obolibrary.org/obo/MONDO_0100118")

    # Add axiom annotation (no direct triple needed)
    create_owl_axiom_annotation(
        g, subject, predicate, obj,
        curator_orcid="0000-0002-5002-8648",
        evidence_id="https://evidence.monarchinitiative.org/record-123"
    )

    # Serialize and parse back
    turtle = g.serialize(format="turtle")
    g2 = Graph()
    g2.parse(data=turtle, format="turtle")

    # Check we have an axiom
    axioms = list(g2.subjects(RDF.type, OWL.Axiom))
    assert len(axioms) == 1

    # Check the axiom has the correct annotated components
    axiom = axioms[0]
    assert (axiom, OWL.annotatedSource, subject) in g2
    assert (axiom, OWL.annotatedProperty, predicate) in g2
    assert (axiom, OWL.annotatedTarget, obj) in g2
