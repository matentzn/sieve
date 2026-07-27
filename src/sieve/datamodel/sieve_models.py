from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "None"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )

    @model_serializer(mode='wrap', when_used='unless-none')
    def treat_empty_lists_as_none(
            self, handler: SerializerFunctionWrapHandler,
            info: SerializationInfo) -> dict[str, Any]:
        if info.exclude_none:
            _instance = self.model_copy()
            for field, field_info in type(_instance).model_fields.items():
                if getattr(_instance, field) == [] and not(
                        field_info.is_required()):
                    setattr(_instance, field, None)
        else:
            _instance = self
        return handler(_instance, info)



class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'sieve',
     'default_range': 'string',
     'description': 'A model for evidence-based curation of semantic assertions\n'
                    '(ontology axioms, knowledge graph triples, etc.).\n'
                    '\n'
                    'Core concept: An EvidencePacket bundles a statement with '
                    'evidence\n'
                    'supporting or disputing it, plus curation workflow status.\n'
                    '\n'
                    'Evidence model aligned with SEPIO (Scientific Evidence and '
                    'Provenance\n'
                    'Information Ontology).',
     'id': 'https://w3id.org/sieve',
     'imports': ['linkml:types', 'sepio_classes'],
     'license': 'Apache Software License 2.0',
     'name': 'sieve',
     'prefixes': {'DOID': {'prefix_prefix': 'DOID',
                           'prefix_reference': 'http://purl.obolibrary.org/obo/DOID_'},
                  'MONDO': {'prefix_prefix': 'MONDO',
                            'prefix_reference': 'http://purl.obolibrary.org/obo/MONDO_'},
                  'PMID': {'prefix_prefix': 'PMID',
                           'prefix_reference': 'http://www.ncbi.nlm.nih.gov/pubmed/'},
                  'eco': {'prefix_prefix': 'eco',
                          'prefix_reference': 'http://purl.obolibrary.org/obo/ECO_'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'obo': {'prefix_prefix': 'obo',
                          'prefix_reference': 'http://purl.obolibrary.org/obo/'},
                  'orcid': {'prefix_prefix': 'orcid',
                            'prefix_reference': 'https://orcid.org/'},
                  'owl': {'prefix_prefix': 'owl',
                          'prefix_reference': 'http://www.w3.org/2002/07/owl#'},
                  'rdfs': {'prefix_prefix': 'rdfs',
                           'prefix_reference': 'http://www.w3.org/2000/01/rdf-schema#'},
                  'sepio': {'prefix_prefix': 'sepio',
                            'prefix_reference': 'https://w3id.org/sepio/'},
                  'sieve': {'prefix_prefix': 'sieve',
                            'prefix_reference': 'https://w3id.org/sieve/'}},
     'see_also': ['https://github.com/monarch-initiative/sieve',
                  'https://sepio-framework.github.io/sepio-linkml'],
     'source_file': 'schema/sieve.yaml',
     'title': 'Sieve - Evidence Packets for Assertion Curation'} )

class CurationStatus(str, Enum):
    """
    Workflow status of the curation.
    """
    UNREVIEWED = "UNREVIEWED"
    """
    Not yet reviewed.
    """
    ACCEPTED = "ACCEPTED"
    """
    Accepted as valid.
    """
    REJECTED = "REJECTED"
    """
    Rejected as invalid.
    """
    CONTROVERSIAL = "CONTROVERSIAL"
    """
    Conflicting evidence, needs discussion.
    """


class DecisionType(str, Enum):
    """
    A curator's decision on an assertion.
    """
    ACCEPT = "ACCEPT"
    """
    Accept the assertion.
    """
    REJECT = "REJECT"
    """
    Reject the assertion.
    """
    CONTROVERSIAL = "CONTROVERSIAL"
    """
    Mark as controversial for further discussion.
    """


class EvidenceDirection(str, Enum):
    """
    Direction of evidence support.
    """
    supports = "supports"
    """
    Evidence supports the statement.
    """
    disputes = "disputes"
    """
    Evidence disputes the statement.
    """
    neutral = "neutral"
    """
    Evidence is neutral.
    """


class EvidenceStrength(str, Enum):
    """
    Qualitative strength of evidence.
    """
    strong = "strong"
    """
    Strong evidence.
    """
    moderate = "moderate"
    """
    Moderate evidence.
    """
    weak = "weak"
    """
    Weak evidence.
    """


class EvidenceItemType(str, Enum):
    """
    Type of evidence item.
    """
    DataItem = "DataItem"
    """
    Individual data point.
    """
    Document = "Document"
    """
    Publication or document.
    """
    StudyResult = "StudyResult"
    """
    Result from a study.
    """
    ConcordanceItem = "ConcordanceItem"
    """
    Cross-source concordance.
    """
    ComputationalResult = "ComputationalResult"
    """
    Computational analysis result.
    """
    AgentContribution = "AgentContribution"
    """
    Human or organizational contribution.
    """


class TrustLevel(str, Enum):
    """
    Level of trust/authority assigned to a contributor. Key dimension for evidence scoring.
    """
    community = "community"
    """
    General community member with unknown credentials.
    """
    domain_expert = "domain_expert"
    """
    Trusted community member with established reputation.
    """
    curator = "curator"
    """
    Official curator with domain expertise and curation training.
    """
    authority = "authority"
    """
    Authoritative source (e.g., official organization, standards body).
    """


class ContributionChannel(str, Enum):
    """
    How a contribution was communicated or submitted. Affects traceability and reliability scoring.
    """
    issue_tracker = "issue_tracker"
    """
    Public issue tracker (GitHub, GitLab, etc.). High traceability.
    """
    personal_communication = "personal_communication"
    """
    Private/personal communication (email, conversation). Low traceability.
    """
    direct_submission = "direct_submission"
    """
    Formal direct submission to the project. Highest traceability.
    """
    public_forum = "public_forum"
    """
    Public mailing list or forum. Medium-high traceability.
    """


class ContributionType(str, Enum):
    """
    The nature/type of a contribution. Affects evidence weight based on commitment level.
    """
    suggestion = "suggestion"
    """
    A suggestion or proposal without formal commitment. Lowest weight.
    """
    review = "review"
    """
    A review or assessment of existing content. Medium weight.
    """
    decision = "decision"
    """
    A formal decision or determination. High weight.
    """
    provision = "provision"
    """
    Direct provision of content from an authoritative source. Highest weight.
    """



class Entity(ConfiguredBaseModel):
    """
    Anything that exists, has existed, or will exist. Root class of the SEPIO core information model.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class InformationEntity(Entity):
    """
    An abstract (non-physical) entity that is about something - representing the underlying information content conveyed by physical or digital artifacts.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Statement(InformationEntity):
    """
    A claim of purported truth as made by a particular agent. Statements may put forth a proposition as true, or provide a nuanced assessment of confidence or evidence supporting a proposition.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    statementText: Optional[str] = Field(default=None, description="""A natural-language expression of what a Statement asserts to be true.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Draft'} })
    proposition: Optional[Proposition] = Field(default=None, description="""A possible fact that the Statement assesses or puts forth as true.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Informative'} })
    subject: Optional[str] = Field(default=None, description="""The Entity or concept about which the Statement is made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Draft'} })
    predicate: Optional[Coding] = Field(default=None, description="""The relationship declared to hold between the subject and the object of the Statement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Draft'} })
    object: Optional[str] = Field(default=None, description="""An Entity or concept that is related to the subject of a Statement via its predicate.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Draft'} })
    qualifier: Optional[list[Qualifier]] = Field(default=[], description="""An additional piece of information that extends or refines the meaning of a Statement's core subject-predicate-object triple.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Informative'} })
    direction: Optional[str] = Field(default=None, description="""Whether the Statement supports, disputes, or is neutral w.r.t. the validity of its Proposition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidenceSynthesis'], 'status': 'Draft'} })
    strength: Optional[str] = Field(default=None, description="""The strength of a Proposition's assessment in the direction indicated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Draft'} })
    score: Optional[float] = Field(default=None, description="""A quantitative score indicating the strength of a Proposition's validity assessment.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidenceSynthesis'], 'status': 'Draft'} })
    hasEvidenceLines: Optional[list[EvidenceLine]] = Field(default=[], description="""Evidence-based arguments that support or dispute the validity of the Statement's proposition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidencePacket'], 'status': 'Draft'} })
    hasEvidence: Optional[list[InformationEntity]] = Field(default=[], description="""A piece of information that contributes to an argument for or against the Statement's proposition. Shortcut bypassing EvidenceLine.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Informative'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class EvidenceLine(InformationEntity):
    """
    An independent, evidence-based argument that may support or refute the validity of a specific proposition, based on interpretation of one or more pieces of information as evidence.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    hasEvidenceItems: Optional[list[InformationEntity]] = Field(default=[], description="""Individual pieces of information evaluated as evidence in building this argument.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    directionOfEvidenceProvided: Optional[str] = Field(default=None, description="""The direction of support toward its target Proposition (supports, disputes, neutral).""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    strengthOfEvidenceProvided: Optional[str] = Field(default=None, description="""The qualitative strength of support for or against its target Proposition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    scoreOfEvidenceProvided: Optional[float] = Field(default=None, description="""A quantitative score indicating the strength of support.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Document(InformationEntity):
    """
    A collection of information in text-based or graphic human-readable form, intended to be read and understood together as a whole.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    subtype: Optional[Coding] = Field(default=None, description="""A specific type of document (e.g. publication, patent, report).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Draft'} })
    title: Optional[str] = Field(default=None, description="""The official title given to the document by its authors.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document']} })
    urls: Optional[list[str]] = Field(default=[], description="""URLs from which the Document content can be retrieved.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document'], 'status': 'Draft'} })
    pmid: Optional[str] = Field(default=None, description="""A PubMed unique identifier for the document.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document'], 'status': 'Draft'} })
    doi: Optional[str] = Field(default=None, description="""A Digital Object Identifier for the document.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document'], 'status': 'Draft'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class DataItem(InformationEntity):
    """
    An Information Entity representing an individual piece of data, generated or acquired through methods which reliably produce truthful information.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Informative'})

    subtype: Optional[Coding] = Field(default=None, description="""A specific type of data the DataItem represents.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    value: str = Field(default=..., description="""The value of the data item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score'],
         'status': 'Informative'} })
    unit: Optional[Coding] = Field(default=None, description="""A unit of measure for the value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem'], 'status': 'Informative'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class StudyResult(InformationEntity):
    """
    A collection of data items from a single study that pertain to a particular subject or experimental unit, along with optional provenance information.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    focus: Optional[str] = Field(default=None, description="""A specific subject or experimental unit the data is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyResult']} })
    dataItems: Optional[list[DataItem]] = Field(default=[], description="""Data items included in the StudyResult.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyResult'], 'status': 'Informative'} })
    sourceDataSet: Optional[list[DataSet]] = Field(default=[], description="""A larger DataSet from which this content was derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyResult'], 'status': 'Draft'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class DataSet(InformationEntity):
    """
    A collection of related data items organized together in a common format.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    subtype: Optional[Coding] = Field(default=None, description="""A specific type of data set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    version: Optional[str] = Field(default=None, description="""The version of the DataSet.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataSet'], 'status': 'Informative'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Activity(Entity):
    """
    An action or set of actions performed by an agent, occurring over a period of time.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Informative'})

    subtype: Optional[Coding] = Field(default=None, description="""A specific type of activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    date: Optional[str] = Field(default=None, description="""The date that the Activity was completed (ISO 8601 string).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity', 'AgentContribution'], 'status': 'Draft'} })
    performedBy: Optional[list[Agent]] = Field(default=[], description="""An Agent who participated in executing the Activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Contribution(Activity):
    """
    An action or actions taken by a particular agent in the creation, modification, assessment, or deprecation of some entity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    contributor: Optional[Agent] = Field(default=None, description="""The Agent that made the contribution.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Contribution', 'AgentContribution'], 'status': 'Draft'} })
    activityType: Optional[list[Coding]] = Field(default=[], description="""The specific type of activity performed or role played by an agent in making the contribution.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Contribution'], 'status': 'Draft'} })
    subtype: Optional[Coding] = Field(default=None, description="""A specific type of activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    date: Optional[str] = Field(default=None, description="""The date that the Activity was completed (ISO 8601 string).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity', 'AgentContribution'], 'status': 'Draft'} })
    performedBy: Optional[list[Agent]] = Field(default=[], description="""An Agent who participated in executing the Activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Agent(Entity):
    """
    An autonomous actor (person, organization, or software agent) that bears some form of responsibility for an activity or entity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    subtype: Optional[str] = Field(default=None, description="""A specific type of agent (person, organization, software).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Draft'} })
    name: Optional[str] = Field(default=None, description="""The given name of the Agent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent', 'Qualifier', 'Extension', 'Characteristic'],
         'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Proposition(Entity):
    """
    An abstract entity representing a possible fact that is either true or false.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Informative'})

    propositionText: Optional[str] = Field(default=None, description="""A natural-language expression of the Proposition's meaning.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Proposition'], 'status': 'Informative'} })
    subject: str = Field(default=..., description="""The Entity or concept about which the Proposition is made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Informative'} })
    predicate: Optional[Coding] = Field(default=None, description="""The relationship declared to hold between subject and object.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Informative'} })
    object: Optional[str] = Field(default=None, description="""An Entity or concept related to the subject via the predicate.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Informative'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class Utility(ConfiguredBaseModel):
    """
    Abstract organizational class grouping classes that act as complex datatypes in the model.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model'})

    pass


class Coding(Utility):
    """
    A structured representation of a code for a defined concept in a terminology or code system.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model'})

    code: Optional[str] = Field(default=None, description="""A symbol uniquely identifying the concept (CURIE format preferred).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Coding']} })
    label: Optional[str] = Field(default=None, description="""The human-readable name for the coded concept.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding']} })
    system: Optional[str] = Field(default=None, description="""The terminology/code system that defined the code.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Coding']} })
    systemVersion: Optional[str] = Field(default=None, description="""Version of the terminology or code system.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Coding', 'Expression']} })


class Qualifier(Utility):
    """
    A key-value object capturing additional information that extends or refines the meaning of a Statement's subject-predicate-object triple.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Informative'})

    name: str = Field(default=..., description="""The type of qualifying information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent', 'Qualifier', 'Extension', 'Characteristic'],
         'status': 'Informative'} })
    value: str = Field(default=..., description="""The value of the qualifier.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score'],
         'status': 'Informative'} })


class Expression(Utility):
    """
    A label representing a systematic expression for an entity, generated by formal nomenclatures.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model'})

    value: str = Field(default=..., description="""A free-text rendering of the expression.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score']} })
    systemURL: Optional[str] = Field(default=None, description="""A URL for the nomenclature system.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    systemVersion: Optional[str] = Field(default=None, description="""The version of the nomenclature system.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Coding', 'Expression']} })


class Extension(Utility):
    """
    A data structure that allows custom attributes to be defined for an Entity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model'})

    extensionDescription: Optional[str] = Field(default=None, description="""Description of the extension element's intended meaning and use.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Extension']} })
    name: str = Field(default=..., description="""A name for the Extension.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent', 'Qualifier', 'Extension', 'Characteristic']} })
    value: str = Field(default=..., description="""The value of the Extension.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score']} })


class RecordMetadata(Utility):
    """
    Provenance metadata about a serialized data record or object in a dataset.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    recordIdentifier: Optional[str] = Field(default=None, description="""The identifier of the record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RecordMetadata'], 'status': 'Draft'} })
    recordVersion: Optional[str] = Field(default=None, description="""The version number of the record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RecordMetadata'], 'status': 'Draft'} })
    derivedFromRecord: Optional[list[str]] = Field(default=[], description="""Another data record from which this was derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RecordMetadata'], 'status': 'Draft'} })
    dateRecordCreated: Optional[str] = Field(default=None, description="""The date the record was initially created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RecordMetadata'], 'status': 'Draft'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Contributions made by an agent to the creation or management of this record.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })


class Characteristic(Utility):
    """
    A name-value pair describing a trait or role of an individual member of a StudyGroup.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    name: str = Field(default=..., description="""The type of trait or role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent', 'Qualifier', 'Extension', 'Characteristic'],
         'status': 'Draft'} })
    values: list[str] = Field(default=..., description="""The specific value(s) of the trait.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Characteristic'], 'status': 'Draft'} })


class StudyGroup(Entity):
    """
    A collection of individuals or specimens selected for analysis based on shared characteristics.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sepio-model', 'status': 'Draft'})

    memberCount: Optional[int] = Field(default=None, description="""Total number of members in the StudyGroup.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyGroup'], 'status': 'Informative'} })
    isSubsetOf: Optional[list[StudyGroup]] = Field(default=[], description="""A larger StudyGroup of which this is a subset.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyGroup'], 'status': 'Draft'} })
    characteristics: Optional[list[Characteristic]] = Field(default=[], description="""Features shared by all members.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyGroup'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class EvidencePacket(ConfiguredBaseModel):
    """
    A bundle containing a statement (assertion) along with evidence lines supporting or disputing it, and curation workflow status.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve', 'tree_root': True})

    id: str = Field(default=..., description="""Unique identifier for this evidence packet.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision']} })
    statement: SieveStatement = Field(default=..., description="""The statement/assertion being curated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidencePacket']} })
    status: CurationStatus = Field(default=CurationStatus.UNREVIEWED, description="""Current curation workflow status.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidencePacket'], 'ifabsent': 'string(UNREVIEWED)'} })
    hasEvidenceLines: Optional[list[SieveEvidenceLine]] = Field(default=[], description="""Evidence lines supporting or disputing the statement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidencePacket']} })
    evidence_synthesis: Optional[EvidenceSynthesis] = Field(default=None, description="""Synthesis of the evidence with reasoning.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidencePacket']} })
    curated_by: Optional[CurationActivity] = Field(default=None, description="""The curation activity that reviewed/approved this packet.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidencePacket']} })
    created: Optional[date] = Field(default=None, description="""When this packet was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidencePacket']} })
    updated: Optional[date] = Field(default=None, description="""When this packet was last updated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidencePacket']} })


class SieveStatement(Statement):
    """
    Sieve extension of SEPIO Statement. A subject-predicate-object assertion being curated. Inherits subject, predicate (Coding), object, statementText, and evidence-linking attributes from SEPIO Statement. Adds human-readable labels for subject and object. Evidence lines are kept on the EvidencePacket container, not nested here.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    subjectLabel: Optional[str] = Field(default=None, description="""Human-readable label for the subject.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveStatement']} })
    objectLabel: Optional[str] = Field(default=None, description="""Human-readable label for the object.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveStatement']} })
    statementText: Optional[str] = Field(default=None, description="""A natural-language expression of what a Statement asserts to be true.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Draft'} })
    proposition: Optional[Proposition] = Field(default=None, description="""A possible fact that the Statement assesses or puts forth as true.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Informative'} })
    subject: Optional[str] = Field(default=None, description="""The Entity or concept about which the Statement is made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Draft'} })
    predicate: Optional[Coding] = Field(default=None, description="""The relationship declared to hold between the subject and the object of the Statement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Draft'} })
    object: Optional[str] = Field(default=None, description="""An Entity or concept that is related to the subject of a Statement via its predicate.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'Proposition'], 'status': 'Draft'} })
    qualifier: Optional[list[Qualifier]] = Field(default=[], description="""An additional piece of information that extends or refines the meaning of a Statement's core subject-predicate-object triple.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Informative'} })
    direction: Optional[str] = Field(default=None, description="""Whether the Statement supports, disputes, or is neutral w.r.t. the validity of its Proposition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidenceSynthesis'], 'status': 'Draft'} })
    strength: Optional[str] = Field(default=None, description="""The strength of a Proposition's assessment in the direction indicated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Draft'} })
    score: Optional[float] = Field(default=None, description="""A quantitative score indicating the strength of a Proposition's validity assessment.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidenceSynthesis'], 'status': 'Draft'} })
    hasEvidenceLines: Optional[list[EvidenceLine]] = Field(default=[], description="""Evidence-based arguments that support or dispute the validity of the Statement's proposition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidencePacket'], 'status': 'Draft'} })
    hasEvidence: Optional[list[InformationEntity]] = Field(default=[], description="""A piece of information that contributes to an argument for or against the Statement's proposition. Shortcut bypassing EvidenceLine.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement'], 'status': 'Informative'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class SieveEvidenceLine(EvidenceLine):
    """
    Sieve extension of SEPIO EvidenceLine. Inherits all SEPIO EvidenceLine attributes. Can contain any InformationEntity as evidence items, including Sieve-specific types like ConcordanceItem.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    hasEvidenceItems: Optional[list[InformationEntity]] = Field(default=[], description="""Individual pieces of information evaluated as evidence in building this argument.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    directionOfEvidenceProvided: Optional[str] = Field(default=None, description="""The direction of support toward its target Proposition (supports, disputes, neutral).""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    strengthOfEvidenceProvided: Optional[str] = Field(default=None, description="""The qualitative strength of support for or against its target Proposition.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    scoreOfEvidenceProvided: Optional[float] = Field(default=None, description="""A quantitative score indicating the strength of support.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceLine'], 'status': 'Draft'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class CuratedEvidence(ConfiguredBaseModel):
    """
    Curation-workflow slots grafted onto every Sieve evidence item: a steward's per-item verdict and an explicit ECO hook. (sieve-specific; not SEPIO)
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve', 'mixin': True})

    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })


class SieveEvidenceItem(InformationEntity):
    """
    Base class for Sieve-specific evidence items. Extends SEPIO InformationEntity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    evidenceItemType: Optional[EvidenceItemType] = Field(default=None, description="""Type of evidence item (for polymorphism).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveEvidenceItem']} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class SieveDataItem(CuratedEvidence, DataItem):
    """
    Sieve extension of SEPIO DataItem.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve', 'mixins': ['CuratedEvidence']})

    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    subtype: Optional[Coding] = Field(default=None, description="""A specific type of data the DataItem represents.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    value: str = Field(default=..., description="""The value of the data item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score'],
         'status': 'Informative'} })
    unit: Optional[Coding] = Field(default=None, description="""A unit of measure for the value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem'], 'status': 'Informative'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class SieveDocument(CuratedEvidence, Document):
    """
    Sieve extension of SEPIO Document. Adds quote fields.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve', 'mixins': ['CuratedEvidence']})

    quote: Optional[str] = Field(default=None, description="""Relevant quote from the document.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveDocument']} })
    quoteLocation: Optional[str] = Field(default=None, description="""Location of quote (page, section, figure).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveDocument']} })
    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    subtype: Optional[Coding] = Field(default=None, description="""A specific type of document (e.g. publication, patent, report).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Draft'} })
    title: Optional[str] = Field(default=None, description="""The official title given to the document by its authors.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document']} })
    urls: Optional[list[str]] = Field(default=[], description="""URLs from which the Document content can be retrieved.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document'], 'status': 'Draft'} })
    pmid: Optional[str] = Field(default=None, description="""A PubMed unique identifier for the document.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document'], 'status': 'Draft'} })
    doi: Optional[str] = Field(default=None, description="""A Digital Object Identifier for the document.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document'], 'status': 'Draft'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class SieveStudyResult(CuratedEvidence, StudyResult):
    """
    Sieve extension of SEPIO StudyResult.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve', 'mixins': ['CuratedEvidence']})

    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    focus: Optional[str] = Field(default=None, description="""A specific subject or experimental unit the data is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyResult']} })
    dataItems: Optional[list[DataItem]] = Field(default=[], description="""Data items included in the StudyResult.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyResult'], 'status': 'Informative'} })
    sourceDataSet: Optional[list[DataSet]] = Field(default=[], description="""A larger DataSet from which this content was derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StudyResult'], 'status': 'Draft'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class ConcordanceItem(SieveEvidenceItem, CuratedEvidence):
    """
    Evidence from concordance with another knowledge source (ontology, database, terminology). The concordant source contains a statement that aligns with the statement being curated.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'comments': ["Use inherited 'sources' to reference the concordant knowledge "
                      'source.',
                      "Use inherited 'derivedFrom' if linking to a formal "
                      'InformationEntity.',
                      'The sourceSubject/Predicate/Object fields capture the '
                      'concordant assertion.'],
         'from_schema': 'https://w3id.org/sieve',
         'mixins': ['CuratedEvidence']})

    sourceName: Optional[str] = Field(default=None, description="""Human-readable name of the concordant source (e.g., \"Disease Ontology\"). Convenience field; formal source can be in inherited 'sources'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourceId: Optional[str] = Field(default=None, description="""Identifier of the concordant source (e.g., database ID, ontology IRI).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourceVersion: Optional[str] = Field(default=None, description="""Version/release of the concordant source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourceSubject: Optional[str] = Field(default=None, description="""Subject of the concordant assertion in the source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourceSubjectLabel: Optional[str] = Field(default=None, description="""Human-readable label of the subject in the source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourcePredicate: Optional[str] = Field(default=None, description="""Predicate/relationship in the concordant assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourcePredicateLabel: Optional[str] = Field(default=None, description="""Human-readable label of the predicate in the source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourceObject: Optional[str] = Field(default=None, description="""Object of the concordant assertion in the source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    sourceObjectLabel: Optional[str] = Field(default=None, description="""Human-readable label of the object in the source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    mappingJustification: Optional[str] = Field(default=None, description="""How entities were mapped between sources (e.g., semapv:LexicalMatching, semapv:ManualMappingCuration). Uses SSSOM mapping justification vocabulary.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    mappingSet: Optional[str] = Field(default=None, description="""SSSOM mapping-set URI the concordance was drawn from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConcordanceItem']} })
    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    evidenceItemType: Optional[EvidenceItemType] = Field(default=None, description="""Type of evidence item (for polymorphism).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveEvidenceItem']} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class ComputationalResult(CuratedEvidence, DataItem):
    """
    Evidence from a computational method or algorithm. Extends SEPIO DataItem. The computed score/result is stored in inherited 'value'. Method details can be referenced via inherited 'specifiedBy' or the convenience attributes below.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'comments': ["Use inherited 'value' for the primary result (e.g., confidence "
                      'score).',
                      "Use inherited 'subtype' (Coding) to categorize the computation "
                      'type.',
                      "Use inherited 'specifiedBy' to reference formal method "
                      'specifications.'],
         'from_schema': 'https://w3id.org/sieve',
         'mixins': ['CuratedEvidence']})

    methodName: Optional[str] = Field(default=None, description="""Human-readable name of the computational method. Convenience field; formal method can be in inherited 'specifiedBy'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ComputationalResult']} })
    methodId: Optional[str] = Field(default=None, description="""Identifier for the method (e.g., OBI term). Convenience field; formal method can be in inherited 'specifiedBy'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ComputationalResult']} })
    parameters: Optional[str] = Field(default=None, description="""Method parameters (as JSON string or key=value format).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ComputationalResult']} })
    softwareVersion: Optional[str] = Field(default=None, description="""Version of software/tool used.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ComputationalResult']} })
    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    subtype: Optional[Coding] = Field(default=None, description="""A specific type of data the DataItem represents.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    value: str = Field(default=..., description="""The value of the data item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score'],
         'status': 'Informative'} })
    unit: Optional[Coding] = Field(default=None, description="""A unit of measure for the value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem'], 'status': 'Informative'} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class AgentContribution(SieveEvidenceItem, CuratedEvidence):
    """
    Evidence from any human or organizational contribution. Captures orthogonal dimensions for scoring: who contributed (trust level), how they contributed (channel), and what type of contribution. Replaces the narrower ExpertStatement class.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve', 'mixins': ['CuratedEvidence']})

    contributor: Optional[Agent] = Field(default=None, description="""The agent (person or organization) who made the contribution.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Contribution', 'AgentContribution']} })
    trustLevel: Optional[TrustLevel] = Field(default=None, description="""Level of trust/authority assigned to the contributor. Key dimension for evidence scoring.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentContribution']} })
    channel: Optional[ContributionChannel] = Field(default=None, description="""How the contribution was communicated/submitted. Affects traceability and reliability scoring.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentContribution']} })
    contributionType: Optional[ContributionType] = Field(default=None, description="""The nature of the contribution (suggestion, review, decision, etc.). Affects evidence weight.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentContribution']} })
    reference: Optional[str] = Field(default=None, description="""URL or identifier for traceability (issue tracker link, email thread, submission ID, etc.).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentContribution']} })
    content: Optional[str] = Field(default=None, description="""The actual content of the contribution (what they said/provided).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentContribution']} })
    date: Optional[str] = Field(default=None, description="""When the contribution was made (ISO 8601 string).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity', 'AgentContribution']} })
    rating: Optional[CurationStatus] = Field(default=None, description="""The evidence steward's verdict on this individual evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_code: Optional[str] = Field(default=None, description="""Evidence & Conclusion Ontology (ECO) term for this evidence item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    eco_label: Optional[str] = Field(default=None, description="""Human-readable label of the ECO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CuratedEvidence']} })
    evidenceItemType: Optional[EvidenceItemType] = Field(default=None, description="""Type of evidence item (for polymorphism).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SieveEvidenceItem']} })
    isAbout: Optional[list[str]] = Field(default=[], description="""An entity or concept that the information entity describes/is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Informative'} })
    contributions: Optional[list[Contribution]] = Field(default=[], description="""Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity', 'RecordMetadata'], 'status': 'Draft'} })
    dateAuthored: Optional[str] = Field(default=None, description="""When the information content was generated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    specifiedBy: Optional[list[str]] = Field(default=[], description="""A specification that describes all or part of the process that led to creation of the Information Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    derivedFrom: Optional[list[InformationEntity]] = Field(default=[], description="""Another Information Entity from which this one is derived.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    reportedIn: Optional[list[str]] = Field(default=[], description="""A document in which the Information Entity is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    sources: Optional[list[str]] = Field(default=[], description="""A document or other information resource in which the information entity, or evidence supporting it, is reported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    recordMetadata: Optional[RecordMetadata] = Field(default=None, description="""Provenance metadata about a specific concrete record of information.""", json_schema_extra = { "linkml_meta": {'domain_of': ['InformationEntity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class CurationActivity(Contribution):
    """
    Sieve extension of SEPIO Contribution. Represents work done by an agent (human curator or AI) in the curation process.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    timestamp: Optional[datetime ] = Field(default=None, description="""When the activity was performed (datetime precision). Use inherited 'date' for date-only precision.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationActivity']} })
    used: Optional[list[str]] = Field(default=[], description="""Inputs used by this activity (e.g., prompt versions, tools). Simplified alternative to SEPIO Activity.input for string-typed inputs.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationActivity']} })
    pull_request: Optional[str] = Field(default=None, description="""GitHub pull request URL associated with this activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationActivity']} })
    issue: Optional[str] = Field(default=None, description="""GitHub issue URL associated with this activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationActivity']} })
    created_with: Optional[str] = Field(default=None, description="""Tool or software used (e.g., a Protégé URI).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationActivity']} })
    contributor: Optional[Agent] = Field(default=None, description="""The Agent that made the contribution.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Contribution', 'AgentContribution'], 'status': 'Draft'} })
    activityType: Optional[list[Coding]] = Field(default=[], description="""The specific type of activity performed or role played by an agent in making the contribution.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Contribution'], 'status': 'Draft'} })
    subtype: Optional[Coding] = Field(default=None, description="""A specific type of activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Document', 'DataItem', 'DataSet', 'Activity', 'Agent'],
         'status': 'Informative'} })
    date: Optional[str] = Field(default=None, description="""The date that the Activity was completed (ISO 8601 string).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity', 'AgentContribution'], 'status': 'Draft'} })
    performedBy: Optional[list[Agent]] = Field(default=[], description="""An Agent who participated in executing the Activity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Activity'], 'status': 'Draft'} })
    id: str = Field(default=..., description="""The logical identifier of the entity in the system of record, e.g. a UUID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision'],
         'status': 'Draft'} })
    identifiers: Optional[list[str]] = Field(default=[], description="""Globally-unique business identifiers or accession numbers for the entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Informative'} })
    type: str = Field(default=..., description="""The name of the class that is instantiated by a data object representing the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    label: Optional[str] = Field(default=None, description="""A primary name for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Coding'], 'status': 'Draft'} })
    alternativeLabels: Optional[list[str]] = Field(default=[], description="""Alternative name(s) for the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })
    description: Optional[str] = Field(default=None, description="""A free text description of the Entity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score'], 'status': 'Draft'} })
    extensions: Optional[list[Extension]] = Field(default=[], description="""A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity'], 'status': 'Draft'} })


class CurationDecision(ConfiguredBaseModel):
    """
    A curator's decision on an EvidencePacket. One row per decision, preserving history (richer than a single curated_by activity). Sieve-specific.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EvidencePacket', 'CurationDecision']} })
    packet_id: str = Field(default=..., description="""Reference to the EvidencePacket.id this decision applies to.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })
    curator: str = Field(default=..., description="""ORCID of the deciding curator.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })
    curator_name: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })
    decision: DecisionType = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })
    rationale: Optional[str] = Field(default=None, description="""Explanation for the decision (required for rejections).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })
    certainty: Optional[float] = Field(default=None, description="""Curator's confidence in this decision (0-1).""", ge=0, le=1, json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })
    decided_at: datetime  = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['CurationDecision']} })


class Score(ConfiguredBaseModel):
    """
    A score with value and description. Extensible for documenting weights, formulas, and aggregation methods.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    value: float = Field(default=..., description="""The numeric score value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DataItem', 'Qualifier', 'Expression', 'Extension', 'Score']} })
    description: Optional[str] = Field(default=None, description="""Explanation of how the score was computed.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'Score']} })


class EvidenceSynthesis(ConfiguredBaseModel):
    """
    Synthesis of evidence with reasoning and overall assessment.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/sieve'})

    summary: str = Field(default=..., description="""Textual summary explaining the conclusion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceSynthesis']} })
    score: Optional[Score] = Field(default=None, description="""Aggregated score from the evidence.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidenceSynthesis']} })
    direction: Optional[EvidenceDirection] = Field(default=None, description="""Overall direction - supports or disputes.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'EvidenceSynthesis']} })
    cited_evidence: Optional[list[str]] = Field(default=[], description="""IDs of evidence lines cited in the synthesis.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceSynthesis']} })
    generated_by: Optional[CurationActivity] = Field(default=None, description="""The activity that generated this synthesis.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EvidenceSynthesis']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Entity.model_rebuild()
InformationEntity.model_rebuild()
Statement.model_rebuild()
EvidenceLine.model_rebuild()
Document.model_rebuild()
DataItem.model_rebuild()
StudyResult.model_rebuild()
DataSet.model_rebuild()
Activity.model_rebuild()
Contribution.model_rebuild()
Agent.model_rebuild()
Proposition.model_rebuild()
Utility.model_rebuild()
Coding.model_rebuild()
Qualifier.model_rebuild()
Expression.model_rebuild()
Extension.model_rebuild()
RecordMetadata.model_rebuild()
Characteristic.model_rebuild()
StudyGroup.model_rebuild()
EvidencePacket.model_rebuild()
SieveStatement.model_rebuild()
SieveEvidenceLine.model_rebuild()
CuratedEvidence.model_rebuild()
SieveEvidenceItem.model_rebuild()
SieveDataItem.model_rebuild()
SieveDocument.model_rebuild()
SieveStudyResult.model_rebuild()
ConcordanceItem.model_rebuild()
ComputationalResult.model_rebuild()
AgentContribution.model_rebuild()
CurationActivity.model_rebuild()
CurationDecision.model_rebuild()
Score.model_rebuild()
EvidenceSynthesis.model_rebuild()
