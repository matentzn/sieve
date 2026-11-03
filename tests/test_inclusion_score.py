"""The reference inclusion score S (D-063, amended by D-069)."""

import copy
import math
from pathlib import Path

import pytest

from sieve.inclusion_score import competition_weight, s_from_l, score_packet
from tests.profile_support import load_yaml

DATA = Path(__file__).parent / "data" / "profile" / "valid"


@pytest.fixture
def lecd() -> dict:
    return load_yaml(DATA / "c003_lecd_multi_item_lines.yaml")


@pytest.fixture
def mds() -> dict:
    return load_yaml(DATA / "c003_mds_competing_claim.yaml")


def _line(breakdown, line_id):
    return next(c for c in breakdown.lines if c.line_id == line_id)


def test_s_is_tanh_of_half_l():
    assert s_from_l(0.0) == 0.0
    assert s_from_l(2.2) == pytest.approx(math.tanh(1.1))


def test_d069_worked_example():
    """D-069: MDS, own L = 2.2, competitor L = 1.4 -> L' = 0.58, S = 0.28."""
    w = competition_weight([1.4])
    assert w == pytest.approx(1.62, abs=0.005)
    assert s_from_l(2.2 - w) == pytest.approx(0.28, abs=0.005)


def test_no_competitor_changes_nothing():
    assert competition_weight([]) == 0.0


def test_lecd_breakdown(lecd):
    """The LECD statement, line by line (rule sieve:rule/synonym-v1.1 in the snapshot)."""
    b = score_packet(lecd)
    concordance = _line(b, "sieve:el/lecd-concordance")
    label = _line(b, "sieve:el/lecd-label-match")
    synthesis = _line(b, "sieve:el/lecd-synthesis")
    assert concordance.state == "counted"
    assert concordance.q == pytest.approx(0.9)  # best-rated source among its items (OMIM)
    assert concordance.w == pytest.approx(0.765)
    assert label.state == "same cluster"  # it rests on the OMIM record too
    assert synthesis.state == "counted"
    assert synthesis.q == pytest.approx(0.7)  # the AI agent's trust, not a source rating
    assert synthesis.w == pytest.approx(0.504)
    assert b.l0 == pytest.approx(0.5)
    assert b.l_evidence == pytest.approx(0.5 + 2.0 * (0.765 + 0.504))
    assert b.s == pytest.approx(math.tanh(b.l_evidence / 2))
    assert round(b.s, 2) == 0.91
    assert b.band == "strong"


def test_stacking_replace_inputs(lecd):
    """With stackedLines REPLACE_INPUTS the synthesis stands for the lines it read."""
    rule = lecd["referenceSnapshot"]["aggregationRules"][0]
    rule["stackedLines"] = "REPLACE_INPUTS"
    b = score_packet(lecd)
    assert _line(b, "sieve:el/lecd-concordance").state == "replaced by higher-order line"
    assert b.l_evidence == pytest.approx(0.5 + 2.0 * 0.504)


def test_judgement_capped_by_what_it_read(lecd):
    """D-063 Q5: a judgement line cannot be stronger than the lines it rests on."""
    lecd["statement"]["hasEvidenceLines"][2]["scoreOfEvidenceProvided"] = 1.0
    synthesis = _line(score_packet(lecd), "sieve:el/lecd-synthesis")
    assert synthesis.s == pytest.approx(0.85)


def test_invalidated_and_low_confidence_lines_do_not_count(lecd):
    lines = lecd["statement"]["hasEvidenceLines"]
    lines[0]["validity"] = "INVALIDATED"
    lines[2]["confidence"] = 0.2
    b = score_packet(lecd)
    assert _line(b, "sieve:el/lecd-concordance").state == "invalidated"
    assert _line(b, "sieve:el/lecd-synthesis").state == "below confidence floor"


def test_disputing_line_lowers_s(lecd):
    before = score_packet(lecd).s
    lecd["statement"]["hasEvidenceLines"][2]["directionOfEvidenceProvided"] = "disputes"
    assert score_packet(lecd).s < before


def test_competing_claim_line(mds):
    """D-069: one refuting line, weight ln(1 + sum e^L_j), outside k."""
    b = score_packet(mds)
    assert b.competition == pytest.approx(math.log(1 + math.exp(1.4)))
    assert b.l_final == pytest.approx(b.l_evidence - b.competition)
    assert b.s == pytest.approx(math.tanh(b.l_final / 2))
    without = copy.deepcopy(mds)
    without["statement"]["hasEvidenceLines"] = [
        line for line in without["statement"]["hasEvidenceLines"] if line["id"] != "sieve:el/mds-competing"
    ]
    assert score_packet(without).s > b.s


def test_unknown_human_gets_the_default_prior(lecd):
    act = lecd["statement"]["hasEvidenceLines"][2]["contributions"][0]
    act.update(contributor="sieve:agent/unknown-human", methodType="EXPERT_JUDGEMENT")
    lecd["referenceSnapshot"]["agents"].append(
        {"id": "sieve:agent/unknown-human", "type": "SieveAgent", "subtype": "person", "identityKnown": False}
    )
    synthesis = _line(score_packet(lecd), "sieve:el/lecd-synthesis")
    assert synthesis.q == pytest.approx(0.5)  # rule.defaultQuality
