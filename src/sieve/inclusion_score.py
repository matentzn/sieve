"""Reference implementation of the inclusion score S (D-063, amended by D-069).

Every parameter comes from the packet itself: the AggregationRule for the statement's
claim type, frozen in the packet's ``reference_snapshot``. Nothing is read from outside
the packet, so the same packet version always scores the same.

Per valid evidence line i::

    w_i = d_i * s_i * q_i * c_i
    d   direction (+1 supports, -1 disputes)
    s   score_of_evidence_provided; a judgement line is capped at the strongest line it rests on (Q5)
    q   prior: for a judgement line (expert, panel, LLM) the interpreter's trust as of the act;
        otherwise the best quality rating, valid at the act date, of the line's sources (Q2)
    c   confidence (data quality); below the rule's floor the line is excluded (Q1)

Only the strongest line per independence cluster counts (D-046). Then::

    L  = L0[channel] + k * sum(w)          (Q3, Q4)
    L' = L - ln(1 + sum_j e^(L_j))         (D-069 competing-claim line, outside k)
    S  = tanh(L' / 2)

How a higher-order line and its inputs count is the rule's ``stacked_lines`` policy:
CAP_AND_ADD (both count, the higher-order line capped) or REPLACE_INPUTS.
"""

import math
from dataclasses import dataclass, field
from typing import Any

JUDGEMENT_METHODS = {"EXPERT_JUDGEMENT", "CONSENSUS_PANEL", "LLM_JUDGEMENT"}
ITEM_LISTS = (
    "external_records",
    "prior_claims",
    "text_passages",
    "publications",
    "web_pages",
    "guidelines",
    "computational_scores",
)
DIRECTION = {"supports": 1, "disputes": -1}


@dataclass
class LineContribution:
    """How one evidence line entered the score."""

    line_id: str
    state: str
    d: int = 0
    s: float = 0.0
    q: float = 0.0
    c: float = 1.0
    w: float = 0.0
    cluster: str = ""


@dataclass
class ScoreBreakdown:
    """S and every step that produced it."""

    rule_id: str
    l0: float
    k: float
    lines: list[LineContribution] = field(default_factory=list)
    sum_w: float = 0.0
    l_evidence: float = 0.0
    competition: float = 0.0
    l_final: float = 0.0
    s: float = 0.0
    band: str | None = None


def s_from_l(l_value: float) -> float:
    """S = tanh(L / 2) = 2 P(true) - 1.

    >>> round(s_from_l(0.58), 2)
    0.28
    """
    return math.tanh(l_value / 2)


def competition_weight(competitor_log_odds: list[float]) -> float:
    """D-069: weight of the one competing-claim line, ln(1 + sum_j e^(L_j)).

    >>> round(competition_weight([1.4]), 2)
    1.62
    >>> competition_weight([])
    0.0
    """
    if not competitor_log_odds:
        return 0.0
    return math.log1p(sum(math.exp(lj) for lj in competitor_log_odds))


def band_for(s: float, bands: list[str]) -> str | None:
    """First band whose condition S satisfies, e.g. ``["strong >= 0.8", "weak < 0.4"]``.

    >>> band_for(0.9, ["strong >= 0.8", "moderate >= 0.4", "weak < 0.4"])
    'strong'
    >>> band_for(0.1, ["strong >= 0.8", "moderate >= 0.4", "weak < 0.4"])
    'weak'
    """
    for band in bands:
        name, op, cut = band.split()
        if (op == ">=" and s >= float(cut)) or (op == "<" and s < float(cut)) or (op == ">" and s > float(cut)):
            return name
    return None


def _valid_at(levels: list[dict], date: str | None, claim_type: str) -> float | None:
    """Level of the latest rating valid at ``date`` (ISO strings compare correctly)."""
    usable = [
        lv
        for lv in levels
        if lv.get("level") is not None
        and (date is None or lv["valid_from"] <= date)
        and (not lv.get("scope") or claim_type in lv["scope"])
    ]
    if not usable:
        return None
    return float(max(usable, key=lambda lv: lv["valid_from"])["level"])


def _rule_for(packet: dict) -> dict:
    claim_type = packet["statement"]["type"]
    rules = [r for r in packet["reference_snapshot"].get("aggregation_rules") or [] if r.get("claim_type") == claim_type]
    if len(rules) != 1:
        raise ValueError(f"expected exactly one AggregationRule for {claim_type} in the snapshot, found {len(rules)}")
    return rules[0]


def score_packet(packet: dict[str, Any]) -> ScoreBreakdown:
    """Compute S for one self-contained EvidencePacket (as loaded from YAML / JSON)."""
    statement = packet["statement"]
    claim_type = statement["type"]
    snapshot = packet["reference_snapshot"]
    rule = _rule_for(packet)
    default_q = float(rule.get("default_quality", 0.5))
    floor = float(rule.get("confidence_floor", 0.0))
    policy = rule.get("stacked_lines", "CAP_AND_ADD")
    priors = {p["channel"]: float(p["log_odds"]) for p in rule.get("claim_priors") or []}
    out = ScoreBreakdown(
        rule_id=rule["id"],
        l0=priors.get(statement.get("proposing_channel", ""), 0.0),
        k=float(rule.get("scaling_factor", 1.0)),
    )

    items = {i["id"]: i for key in ITEM_LISTS for i in packet.get(key) or []}
    agents = {a["id"]: a for a in snapshot.get("agents") or []}
    resources = {r["id"]: r for r in snapshot.get("resources") or []}
    lines = {line["id"]: line for line in statement.get("has_evidence_lines") or []}

    def act_of(line: dict) -> dict:
        return (line.get("contributions") or [{}])[0]

    def is_valid(line: dict) -> bool:
        return line.get("validity", "VALID") != "INVALIDATED"

    def sources_of(item: dict) -> list[str]:
        if item.get("resource"):
            return [item["resource"]]
        if item["type"] == "TextPassage":
            return [items[d]["resource"] for d in item.get("reported_in") or [] if d in items and items[d].get("resource")]
        return []

    def prior(line: dict, act: dict) -> float:
        date = act.get("date")
        if act.get("method_type") in JUDGEMENT_METHODS:
            if act.get("agent_trust_at_time") is not None:
                return float(act["agent_trust_at_time"])
            level = _valid_at(agents.get(act.get("contributor", ""), {}).get("trust_levels") or [], date, claim_type)
            return default_q if level is None else level
        ratings = []
        for ref in line.get("has_evidence_items") or []:
            for res in sources_of(items.get(ref, {"type": ""})):
                level = _valid_at(resources.get(res, {}).get("quality_ratings") or [], date, claim_type)
                if level is not None:
                    ratings.append(level)
        return max(ratings) if ratings else default_q

    competitors: list[float] = []
    replaced: set[str] = set()
    if policy == "REPLACE_INPUTS":
        for line in lines.values():
            if is_valid(line):
                replaced |= {ref for ref in line.get("has_evidence_items") or [] if ref in lines}

    best: dict[str, LineContribution] = {}
    for line_id, line in lines.items():
        act = act_of(line)
        contrib = LineContribution(line_id=line_id, state="counted")
        out.lines.append(contrib)
        if not is_valid(line):
            contrib.state = "invalidated"
            continue
        if act.get("method_type") == "COMPETING_CLAIM":
            competitors += [float(items[r]["own_log_odds"]) for r in line.get("has_evidence_items") or [] if r in items]
            contrib.state = "competing-claim line"
            continue
        if line_id in replaced:
            contrib.state = "replaced by higher-order line"
            continue
        contrib.c = float(line.get("confidence", 1.0))
        if contrib.c < floor or line.get("data_quality_flags"):
            contrib.state = "below confidence floor"
            continue
        if line.get("score_of_evidence_provided") is None:
            contrib.state = "no strength"
            continue
        contrib.d = DIRECTION[line["direction_of_evidence_provided"]]
        contrib.s = float(line["score_of_evidence_provided"])
        inputs = [lines[r] for r in line.get("has_evidence_items") or [] if r in lines]
        if inputs and act.get("method_type") in JUDGEMENT_METHODS:
            cap = max(float(i.get("score_of_evidence_provided") or 0.0) for i in inputs)
            contrib.s = min(contrib.s, cap)
        contrib.q = prior(line, act)
        contrib.w = contrib.d * contrib.s * contrib.q * contrib.c
        contrib.cluster = line.get("independence_cluster") or line_id
        current = best.get(contrib.cluster)
        if current is None or abs(contrib.w) > abs(current.w):
            if current is not None:
                current.state = "same cluster"
            best[contrib.cluster] = contrib
        else:
            contrib.state = "same cluster"

    out.sum_w = sum(c.w for c in best.values())
    out.l_evidence = out.l0 + out.k * out.sum_w
    out.competition = competition_weight(competitors)
    out.l_final = out.l_evidence - out.competition
    out.s = s_from_l(out.l_final)
    out.band = band_for(out.s, rule.get("strength_bands") or [])
    return out
