#!/usr/bin/env python3
"""
xcom_mesh_adapter.py — Governance adapter connecting X.com (Twitter/X) as an
external information source node in the LLM governance mesh.

WHY THIS PIECE EXISTS
The governance mesh (inform_mesh_engine) assumes that information enters through
its anchor node. But real governance systems must consume signals from external,
uncontrolled sources — social media platforms, news feeds, public APIs — whose
epistemic quality is heterogeneous and unverified.

X.com is the canonical example:
  - A post from an anonymous account about a geopolitical event → UNVERIFIABLE (binding=1)
  - A post from a verified journalist quoting an official source → INFERRED (binding=2)
  - An official account announcement from a known institution → ESTIMATED (binding=3)
  - No X.com signal ever reaches SOLVE (4) or EXACT (5) without independent verification

The adapter solves two problems:

  1. SIGNAL CLASSIFICATION — map X.com post metadata to a XComSignalClass:
       NEWS        — factual claim about an observable event
       ANNOUNCEMENT — declarative statement from an identified actor
       OPINION      — evaluative or predictive claim
       RUMOUR       — unverified propagation without primary source

  2. BINDING GOVERNANCE — each (signal_class, source_quality) pair has a hard cap
     on binding_level. No adapter configuration can push an X.com signal above
     ESTIMATED (3) without human-in-the-loop verification. This enforces the
     epistemic principle that social media is always an indirect evidence source.

GOVERNANCE ARCHITECTURE
                                   ┌─────────────────────┐
  X.com API / firehose ──────────► │  XComRelayNode       │  binding ≤ 3
                                   │  (min_binding=1)      │  type = FINDING only
                                   └───────────┬──────────┘
                                               │  FINDING
                                   ┌───────────▼──────────┐
                                   │  xcom_evaluator       │  human or
                                   │  (MeshNode, core)     │  high-trust agent
                                   └───────────────────────┘

The relay node CANNOT emit RULING, ALERT, CORRECTION, or RETRACTION — those are
reserved for the governance core. An X.com post can trigger a FINDING that the
core then elevates to a RULING via its own audit path.

SIGNAL CLASSIFICATION RULES
  Binding cap by signal class:
    RUMOUR       → 1  (UNVERIFIABLE)
    OPINION      → 2  (INFERRED)     — even from verified accounts
    NEWS         → 2  (INFERRED)     — unverified account
    NEWS         → 3  (ESTIMATED)    — verified account WITH cited primary source
    ANNOUNCEMENT → 3  (ESTIMATED)    — verified official account

  Modifier: engagement_factor (likes + reposts / threshold) — does NOT raise
  binding; high engagement increases confidence in signal reach, not truth value.
  This prevents "viral = true" reasoning.

BINDING LEVELS (truth_infra convention)
  5 EXACT        — logically entailed or directly measured
  4 SOLVE        — computationally verified model output
  3 ESTIMATED    — calibrated statistical inference
  2 INFERRED     — reasoned from indirect evidence
  1 UNVERIFIABLE — cannot be checked

THEORETICAL FOUNDATIONS
  Mercier & Sperber (2017) — The Enigma of Reason: social proof (engagement)
                              does not raise epistemic binding. Virality tracks
                              coherence with prior belief, not truth value.
                              The adapter enforces this: engagement_factor
                              is informational metadata, never a binding booster.
  Habermas (1984)          — Communicative action theory: discourse validity
                              claims (truth, normative rightness, sincerity) each
                              require a different type of warrant. ANNOUNCEMENT
                              carries a sincerity claim (actor committed); NEWS
                              carries a truth claim (event occurred). The signal
                              class captures this distinction.
  Luhmann (1996)           — Reality of the Mass Media: media selections amplify
                              deviation from normal expectation, not average facts.
                              High-engagement X.com posts are selected for
                              unusualness, not ground truth. Governance systems
                              must compensate for this selection bias.
  Shannon (1948)           — Noisy channel: X.com is a high-entropy, low signal-
                              to-noise channel. Binding caps are the governance
                              analogue of error-correcting codes: they limit how
                              far corrupted signals propagate before verification.
  truth_infra              — Binding levels 1–5 directly imported. The adapter
                              never assigns 4 or 5 without a human or verifier node.
  inform_mesh_engine       — InformPacket is the output format. The relay node
                              is a standard MeshNode insertable into any MeshNetwork.
  agent_sos_infra          — The relay node's trust tier in a SoS network would be
                              OBSERVED (1): external, observable, unverified.
  anti_war_infra           — Richardson instability analogy: viral disinformation
                              loops on X.com mirror arms-race dynamics. The binding
                              cap is the governance brake (kl > αβ condition).

Stdlib-only, deterministic, no real-time clocks. Run: python xcom_mesh_adapter.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Tuple

# ── Imports from sibling modules (informational — not executed at import time) ──
# from inform_mesh_engine import (
#     InformPacket, MeshNode, MeshEdge, MeshNetwork, PayloadType, inform, audit_mesh
# )
# We re-define the minimal surface we need so xcom_mesh_adapter.py is runnable
# standalone, but the real production usage imports from inform_mesh_engine directly.

from inform_mesh_engine import (
    InformPacket,
    MeshEdge,
    MeshNetwork,
    MeshNode,
    PayloadType,
    audit_mesh,
    inform,
)


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

_BINDING_MAX_XCOM: int = 3    # hard ceiling for any X.com-sourced packet
_BINDING_MIN:      int = 1
_RELAY_NODE_ID:    str = "xcom_relay"


# ──────────────────────────────────────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────────────────────────────────────

class XComSignalClass(Enum):
    """
    Epistemic category of an X.com post.

    NEWS         — factual claim about an observable external event
    ANNOUNCEMENT — declarative statement by an identified, acknowledged actor
    OPINION      — evaluative, predictive, or normative claim
    RUMOUR       — unverified propagation; no identifiable primary source
    """
    NEWS         = "NEWS"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    OPINION      = "OPINION"
    RUMOUR       = "RUMOUR"


class SourceQuality(Enum):
    """
    Quality tier of the X.com post author.

    ANONYMOUS       — no verified identity
    IDENTIFIED      — real name or handle traceable to a person, not verified by platform
    PLATFORM_VERIFIED — blue-check or organization badge on X.com
    INSTITUTIONAL   — official account of a known institution (government, press, NGO)
    """
    ANONYMOUS          = 0
    IDENTIFIED         = 1
    PLATFORM_VERIFIED  = 2
    INSTITUTIONAL      = 3


class AdapterVerdict(Enum):
    """Result of attempting to convert an X.com post into a governance packet."""
    ACCEPTED       = "ACCEPTED"       # packet produced; binding assigned
    CAPPED         = "CAPPED"         # binding reduced to enforce governance ceiling
    REJECTED       = "REJECTED"       # post does not meet minimum adapter requirements
    QUARANTINED    = "QUARANTINED"    # post flagged as likely manipulation / coordinated
    UNCLASSIFIABLE = "UNCLASSIFIABLE" # cannot assign a signal class; dropped


_VERDICT_RESPONSE: Dict[AdapterVerdict, str] = {
    AdapterVerdict.ACCEPTED      : "FORWARD",
    AdapterVerdict.CAPPED        : "DEGRADE",
    AdapterVerdict.REJECTED      : "BLOCK",
    AdapterVerdict.QUARANTINED   : "VOID",
    AdapterVerdict.UNCLASSIFIABLE: "BLOCK",
}

# Binding cap table: (signal_class, source_quality) → max binding_level
_BINDING_CAP: Dict[Tuple[XComSignalClass, SourceQuality], int] = {
    (XComSignalClass.RUMOUR,       SourceQuality.ANONYMOUS)         : 1,
    (XComSignalClass.RUMOUR,       SourceQuality.IDENTIFIED)        : 1,
    (XComSignalClass.RUMOUR,       SourceQuality.PLATFORM_VERIFIED) : 1,
    (XComSignalClass.RUMOUR,       SourceQuality.INSTITUTIONAL)     : 1,
    (XComSignalClass.OPINION,      SourceQuality.ANONYMOUS)         : 1,
    (XComSignalClass.OPINION,      SourceQuality.IDENTIFIED)        : 1,
    (XComSignalClass.OPINION,      SourceQuality.PLATFORM_VERIFIED) : 2,
    (XComSignalClass.OPINION,      SourceQuality.INSTITUTIONAL)     : 2,
    (XComSignalClass.NEWS,         SourceQuality.ANONYMOUS)         : 1,
    (XComSignalClass.NEWS,         SourceQuality.IDENTIFIED)        : 2,
    (XComSignalClass.NEWS,         SourceQuality.PLATFORM_VERIFIED) : 2,
    (XComSignalClass.NEWS,         SourceQuality.INSTITUTIONAL)     : 3,
    (XComSignalClass.ANNOUNCEMENT, SourceQuality.ANONYMOUS)         : 1,
    (XComSignalClass.ANNOUNCEMENT, SourceQuality.IDENTIFIED)        : 2,
    (XComSignalClass.ANNOUNCEMENT, SourceQuality.PLATFORM_VERIFIED) : 2,
    (XComSignalClass.ANNOUNCEMENT, SourceQuality.INSTITUTIONAL)     : 3,
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class XComPost:
    """
    Minimal governance-relevant representation of an X.com post.

    post_id          : platform post identifier
    author_id        : platform author identifier
    content_tag      : governance content label (assigned by ingestion pipeline,
                       not from the post itself — prevents injection)
    signal_class     : epistemic category (NEWS / ANNOUNCEMENT / OPINION / RUMOUR)
    source_quality   : author quality tier
    has_primary_ref  : True if post cites a verifiable primary source (URL, doc)
    engagement_score : normalised 0.0–1.0 (reach / platform_max); informational only
    is_reply_chain   : True if the post is part of a reply thread (reduces independence)
    coordinated_flag : True if platform or prior analysis flagged as coordinated behaviour
    logical_ts       : Lamport clock at ingestion
    """
    post_id          : str
    author_id        : str
    content_tag      : str
    signal_class     : XComSignalClass
    source_quality   : SourceQuality
    has_primary_ref  : bool  = False
    engagement_score : float = 0.0
    is_reply_chain   : bool  = False
    coordinated_flag : bool  = False
    logical_ts       : int   = 0

    def __post_init__(self) -> None:
        if not (0.0 <= self.engagement_score <= 1.0):
            raise ValueError(
                f"engagement_score must be 0.0–1.0; got {self.engagement_score}"
            )


@dataclass(frozen=True)
class XComAdapterConfig:
    """
    Governance configuration for the X.com adapter.

    min_source_quality     : posts from authors below this tier are REJECTED
    require_primary_ref_for: signal classes that MUST cite a primary source;
                             absence downgrades to RUMOUR
    quarantine_coordinated : if True, coordinated_flag posts are QUARANTINED
    logical_ts_offset      : added to post.logical_ts on output packets
    packet_id_prefix       : prepended to post_id to form InformPacket id
    """
    min_source_quality      : SourceQuality               = SourceQuality.ANONYMOUS
    require_primary_ref_for : FrozenSet[XComSignalClass]  = field(
        default_factory=lambda: frozenset({XComSignalClass.NEWS})
    )
    quarantine_coordinated  : bool                        = True
    logical_ts_offset       : int                         = 0
    packet_id_prefix        : str                         = "xcom_"


@dataclass(frozen=True)
class XComAdapterTrace:
    """
    Audit record for a single post-to-packet conversion attempt.

    post_id          : source post identifier
    verdict          : what the adapter decided
    governance_resp  : governance action string
    signal_class     : class assigned (may differ from post if downgraded)
    source_quality   : source quality used
    raw_binding      : binding level before cap enforcement
    final_binding    : binding level after cap (may equal raw_binding)
    was_capped       : True if cap reduced binding
    packet_id        : InformPacket id produced (None if not ACCEPTED/CAPPED)
    reason           : human-readable explanation
    """
    post_id         : str
    verdict         : str
    governance_resp : str
    signal_class    : str
    source_quality  : str
    raw_binding     : int
    final_binding   : int
    was_capped      : bool
    packet_id       : Optional[str]
    reason          : str

    def render(self) -> str:
        lines = [
            f"[XComAdapterTrace] post={self.post_id}",
            f"  signal_class    : {self.signal_class}",
            f"  source_quality  : {self.source_quality}",
            f"  binding         : {self.raw_binding}"
            + (f" → {self.final_binding} (capped)" if self.was_capped else ""),
            f"  verdict         : {self.verdict}",
            f"  governance_resp : {self.governance_resp}",
        ]
        if self.packet_id:
            lines.append(f"  packet_id       : {self.packet_id}")
        lines.append(f"  reason          : {self.reason}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# ADAPTER CORE
# ──────────────────────────────────────────────────────────────────────────────

def ingest_xcom_post(
    post   : XComPost,
    config : XComAdapterConfig,
) -> Tuple[Optional[InformPacket], XComAdapterTrace]:
    """
    Convert an XComPost into an InformPacket under the adapter's governance rules.

    Returns (packet, trace). If the post is rejected/quarantined/unclassifiable,
    packet is None.

    Governance checks (priority order):
      1. QUARANTINED  — coordinated_flag AND config.quarantine_coordinated
      2. REJECTED     — author below min_source_quality
      3. Signal class downgrade — if NEWS/ANNOUNCEMENT lacks required primary ref
      4. Binding cap assignment from (signal_class, source_quality) table
      5. Global ceiling enforcement (_BINDING_MAX_XCOM = 3)
      6. ACCEPTED or CAPPED verdict
    """
    effective_class = post.signal_class

    # ── 1. Coordinated behaviour quarantine ──────────────────────────────────
    if post.coordinated_flag and config.quarantine_coordinated:
        return None, XComAdapterTrace(
            post_id=post.post_id, verdict=AdapterVerdict.QUARANTINED.value,
            governance_resp=_VERDICT_RESPONSE[AdapterVerdict.QUARANTINED],
            signal_class=effective_class.value,
            source_quality=post.source_quality.value,
            raw_binding=0, final_binding=0, was_capped=False, packet_id=None,
            reason=(
                f"Post '{post.post_id}' flagged as coordinated behaviour. "
                f"Quarantined per adapter config."
            ),
        )

    # ── 2. Source quality gate ────────────────────────────────────────────────
    if post.source_quality.value < config.min_source_quality.value:
        return None, XComAdapterTrace(
            post_id=post.post_id, verdict=AdapterVerdict.REJECTED.value,
            governance_resp=_VERDICT_RESPONSE[AdapterVerdict.REJECTED],
            signal_class=effective_class.value,
            source_quality=post.source_quality.value,
            raw_binding=0, final_binding=0, was_capped=False, packet_id=None,
            reason=(
                f"Author source quality '{post.source_quality.value}' is below "
                f"minimum required '{config.min_source_quality.value}'."
            ),
        )

    # ── 3. Primary reference requirement (downgrade if missing) ──────────────
    downgraded = False
    if (
        effective_class in config.require_primary_ref_for
        and not post.has_primary_ref
    ):
        effective_class = XComSignalClass.RUMOUR
        downgraded = True

    # ── 4. Binding cap from (class, quality) table ───────────────────────────
    cap = _BINDING_CAP.get(
        (effective_class, post.source_quality),
        1,  # safe default
    )

    # ── 5. Global X.com ceiling ───────────────────────────────────────────────
    cap = min(cap, _BINDING_MAX_XCOM)

    # Note: engagement_score does NOT affect binding (Mercier & Sperber: virality ≠ truth)

    # Raw binding = cap (X.com posts carry no pre-assigned binding;
    # the cap IS the assigned level)
    raw_binding   = cap
    final_binding = cap
    was_capped    = False  # cap was applied during classification, not after

    # Check if a "requested" higher binding was reduced — here binding is always
    # assigned from scratch, but we flag if the class was downgraded
    if downgraded:
        was_capped = True
        cap_reason = (
            f"Post '{post.post_id}' classified as {post.signal_class.value} "
            f"but no primary reference found — downgraded to RUMOUR; "
            f"binding capped at {final_binding}."
        )
        verdict = AdapterVerdict.CAPPED
    else:
        cap_reason = (
            f"Post '{post.post_id}' accepted as {effective_class.value} "
            f"from {post.source_quality.value} source; binding={final_binding}."
        )
        verdict = AdapterVerdict.ACCEPTED

    packet_id = f"{config.packet_id_prefix}{post.post_id}"
    packet = InformPacket(
        id            = packet_id,
        source_id     = _RELAY_NODE_ID,
        content_tag   = post.content_tag,
        payload_type  = PayloadType.FINDING,   # X.com → always FINDING; never RULING
        binding_level = final_binding,
        ttl           = 4,                      # short TTL: external signals age quickly
        logical_ts    = post.logical_ts + config.logical_ts_offset,
    )

    return packet, XComAdapterTrace(
        post_id=post.post_id, verdict=verdict.value,
        governance_resp=_VERDICT_RESPONSE[verdict],
        signal_class=effective_class.value,
        source_quality=post.source_quality.value,
        raw_binding=raw_binding, final_binding=final_binding,
        was_capped=was_capped, packet_id=packet_id,
        reason=cap_reason,
    )


# ──────────────────────────────────────────────────────────────────────────────
# MESH INTEGRATION
# ──────────────────────────────────────────────────────────────────────────────

def build_xcom_relay_node() -> MeshNode:
    """
    Return a pre-configured MeshNode for the X.com relay point.

    Properties:
    - Accepts only FINDING (X.com cannot originate RULING, ALERT, etc.)
    - min_binding=1 (accepts all adapted signals; core mesh filters downstream)
    - standalone=False (requires connection to core mesh to be meaningful)
    """
    return MeshNode(
        id            = _RELAY_NODE_ID,
        name          = "X.com Signal Relay",
        min_binding   = 1,
        accepted_types= frozenset({PayloadType.FINDING}),
        standalone    = False,
    )


def extend_mesh_with_xcom(
    base_mesh      : MeshNetwork,
    xcom_targets   : List[str],
    permitted_types: Optional[FrozenSet[PayloadType]] = None,
) -> MeshNetwork:
    """
    Add the X.com relay node to an existing MeshNetwork.

    `xcom_targets` : list of node ids in base_mesh that should receive X.com
                     FINDING signals. These must already exist in base_mesh.
    `permitted_types` : types allowed on xcom_relay → target edges.
                        Defaults to {FINDING} (the only type X.com can source).

    Returns a new MeshNetwork (frozen; base_mesh is not mutated).
    """
    if permitted_types is None:
        permitted_types = frozenset({PayloadType.FINDING})

    relay = build_xcom_relay_node()
    new_nodes = tuple(list(base_mesh.nodes) + [relay])

    new_edges = list(base_mesh.edges)
    for target_id in xcom_targets:
        new_edges.append(
            MeshEdge(
                source_id       = _RELAY_NODE_ID,
                target_id       = target_id,
                permitted_types = permitted_types & frozenset({PayloadType.FINDING}),
            )
        )

    return MeshNetwork(
        name      = f"{base_mesh.name}+xcom",
        nodes     = new_nodes,
        edges     = tuple(new_edges),
        anchor_id = base_mesh.anchor_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# REFERENCE MESH WITH X.COM
# ──────────────────────────────────────────────────────────────────────────────

def _build_xcom_governance_mesh() -> MeshNetwork:
    """
    A governance mesh with X.com relay integrated:

      xcom_relay  →  xcom_evaluator  →  anchor  →  reporter
                                         ↓
                                       alert_relay  (ALERT only)

    The anchor is authoritative. xcom_evaluator is a FINDING-only node that
    filters raw X.com signals before they reach the governance anchor.
    """
    ALL = frozenset(PayloadType)

    anchor = MeshNode(
        id="anchor", name="Governance Anchor",
        # Accepts only FINDING from xcom_evaluator. The anchor generates
        # RULING/ALERT/CORRECTION/RETRACTION for downstream nodes but does
        # not RECEIVE those types from within this mesh — declaring ALL would
        # create coverage gaps (no incoming edge delivers them).
        min_binding=2,
        accepted_types=frozenset({PayloadType.FINDING}),
        standalone=True,
    )
    xcom_eval = MeshNode(
        id="xcom_evaluator", name="X.com Signal Evaluator",
        min_binding=1, accepted_types=frozenset({PayloadType.FINDING}),
        standalone=False,
    )
    reporter = MeshNode(
        id="reporter", name="Reporting Module",
        min_binding=2, accepted_types=frozenset({PayloadType.FINDING, PayloadType.ALERT,
                                                  PayloadType.RULING}),
        standalone=True,
    )
    alert_relay = MeshNode(
        id="alert_relay", name="Alert Relay",
        min_binding=5, accepted_types=frozenset({PayloadType.ALERT}),
        standalone=False,
    )
    relay = build_xcom_relay_node()

    edges = (
        MeshEdge("xcom_relay",     "xcom_evaluator", frozenset({PayloadType.FINDING})),
        MeshEdge("xcom_evaluator", "anchor",          frozenset({PayloadType.FINDING})),
        MeshEdge("anchor",         "reporter",        frozenset({PayloadType.FINDING,
                                                                   PayloadType.RULING,
                                                                   PayloadType.ALERT})),
        MeshEdge("anchor",         "alert_relay",     frozenset({PayloadType.ALERT})),
    )

    # anchor_id = "xcom_relay": information originates at the relay (external source)
    # and flows downstream through xcom_evaluator → anchor → reporter.
    # In inform_mesh_engine partition detection starts from anchor_id via forward BFS;
    # using xcom_relay ensures all downstream nodes are reachable.
    return MeshNetwork(
        name      = "xcom_governance_mesh",
        nodes     = (relay, xcom_eval, anchor, reporter, alert_relay),
        edges     = edges,
        anchor_id = "xcom_relay",
    )


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    print("=" * 70)
    print("SELF-TEST: xcom_mesh_adapter.py")
    print("=" * 70)

    passed = total = 0

    def check(label: str, got, expected):
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {got}")
        passed += ok
        total  += 1

    cfg = XComAdapterConfig()

    print("\n── Signal classification & binding ──")

    # X0: Institutional NEWS with primary ref → binding=3 (ESTIMATED)
    p0 = XComPost("x0", "bbc_official", "ceasefire_agreement",
                  XComSignalClass.NEWS, SourceQuality.INSTITUTIONAL,
                  has_primary_ref=True)
    pkt0, tr0 = ingest_xcom_post(p0, cfg)
    check("X0: INSTITUTIONAL NEWS + primary ref → binding=3",
          tr0.final_binding, 3)
    check("X0b: verdict=ACCEPTED",
          tr0.verdict, AdapterVerdict.ACCEPTED.value)
    check("X0c: packet produced",
          pkt0 is not None, True)
    check("X0d: payload_type=FINDING",
          pkt0.payload_type.name if pkt0 else None, PayloadType.FINDING.name)

    # X1: PLATFORM_VERIFIED NEWS without primary ref → downgraded to RUMOUR → binding=1
    p1 = XComPost("x1", "journalist_v", "ceasefire_claim",
                  XComSignalClass.NEWS, SourceQuality.PLATFORM_VERIFIED,
                  has_primary_ref=False)
    pkt1, tr1 = ingest_xcom_post(p1, cfg)
    check("X1: PLATFORM_VERIFIED NEWS, no primary ref → RUMOUR → binding=1",
          tr1.final_binding, 1)
    check("X1b: verdict=CAPPED (downgraded)",
          tr1.verdict, AdapterVerdict.CAPPED.value)
    check("X1c: signal_class downgraded to RUMOUR",
          tr1.signal_class, XComSignalClass.RUMOUR.value)

    # X2: ANONYMOUS post → REJECTED (default min_source_quality=ANONYMOUS, should still pass)
    # Test with config requiring IDENTIFIED minimum
    strict_cfg = XComAdapterConfig(min_source_quality=SourceQuality.IDENTIFIED)
    p2 = XComPost("x2", "anon_123", "event_report",
                  XComSignalClass.NEWS, SourceQuality.ANONYMOUS)
    pkt2, tr2 = ingest_xcom_post(p2, strict_cfg)
    check("X2: ANONYMOUS source below IDENTIFIED minimum → REJECTED",
          tr2.verdict, AdapterVerdict.REJECTED.value)
    check("X2b: no packet produced",
          pkt2 is None, True)

    # X3: Coordinated flag → QUARANTINED
    p3 = XComPost("x3", "bot_farm_7", "viral_claim",
                  XComSignalClass.NEWS, SourceQuality.PLATFORM_VERIFIED,
                  coordinated_flag=True)
    pkt3, tr3 = ingest_xcom_post(p3, cfg)
    check("X3: coordinated_flag → QUARANTINED",
          tr3.verdict, AdapterVerdict.QUARANTINED.value)
    check("X3b: no packet produced",
          pkt3 is None, True)

    # X4: OPINION from PLATFORM_VERIFIED → binding=2 (cap)
    p4 = XComPost("x4", "analyst_v", "market_prediction",
                  XComSignalClass.OPINION, SourceQuality.PLATFORM_VERIFIED,
                  has_primary_ref=True)
    pkt4, tr4 = ingest_xcom_post(p4, cfg)
    check("X4: PLATFORM_VERIFIED OPINION → binding=2 (hard cap for opinion)",
          tr4.final_binding, 2)

    # X5: engagement_score does NOT raise binding (Mercier & Sperber)
    # High engagement RUMOUR should still be binding=1
    p5 = XComPost("x5", "viral_user", "breaking_claim",
                  XComSignalClass.RUMOUR, SourceQuality.PLATFORM_VERIFIED,
                  engagement_score=0.99)
    pkt5, tr5 = ingest_xcom_post(p5, cfg)
    check("X5: High engagement RUMOUR still binding=1 (virality ≠ truth)",
          tr5.final_binding, 1)

    # X6: Global ceiling enforced — nothing above 3
    p6 = XComPost("x6", "inst_acc", "verified_announcement",
                  XComSignalClass.ANNOUNCEMENT, SourceQuality.INSTITUTIONAL,
                  has_primary_ref=True)
    pkt6, tr6 = ingest_xcom_post(p6, cfg)
    check("X6: INSTITUTIONAL ANNOUNCEMENT capped at 3 (global X.com ceiling)",
          tr6.final_binding <= _BINDING_MAX_XCOM, True)

    # X7: packet source_id is always xcom_relay
    check("X7: packet source_id = xcom_relay",
          pkt6.source_id if pkt6 else None, _RELAY_NODE_ID)

    # X8: packet TTL = 4 (short TTL for external signals)
    check("X8: packet TTL = 4",
          pkt6.ttl if pkt6 else None, 4)

    print("\n── Mesh integration ──")

    # A0: Governance mesh coherent with xcom relay
    mesh = _build_xcom_governance_mesh()
    ruling = audit_mesh(mesh)
    check("A0: xcom_governance_mesh → MESH_COHERENT",
          ruling.verdict, "MESH_COHERENT")

    # A1: X.com packet propagates through relay → evaluator → anchor → reporter
    pkt_a1 = InformPacket("inf_a1", "xcom_relay", "ceasefire_signal",
                          PayloadType.FINDING, 2, 4)
    trace = inform(pkt_a1, mesh)
    check("A1: FINDING binding=2 from xcom_relay reaches xcom_evaluator",
          "xcom_evaluator" in trace.delivered_to, True)
    check("A1b: FINDING binding=2 reaches anchor (min_binding=2)",
          "anchor" in trace.delivered_to, True)
    check("A1c: FINDING reaches reporter",
          "reporter" in trace.delivered_to, True)

    # A2: binding=1 blocked at anchor (min_binding=2) → PARTIAL or NO_RECIPIENTS
    pkt_a2 = InformPacket("inf_a2", "xcom_relay", "low_quality_signal",
                          PayloadType.FINDING, 1, 4)
    trace2 = inform(pkt_a2, mesh)
    check("A2: FINDING binding=1 blocked at anchor (min=2)",
          "anchor" not in trace2.delivered_to, True)

    # A3: extend_mesh_with_xcom adds relay edges correctly
    base_nodes = (
        MeshNode("base_anchor", "Anchor", 1, frozenset(PayloadType), True),
        MeshNode("base_worker", "Worker", 1, frozenset({PayloadType.FINDING}), True),
    )
    base_edges = (
        MeshEdge("base_anchor", "base_worker", frozenset({PayloadType.FINDING})),
    )
    base_mesh = MeshNetwork("base", base_nodes, base_edges, "base_anchor")
    extended = extend_mesh_with_xcom(base_mesh, ["base_worker"])
    check("A3: extended mesh has xcom_relay node",
          any(n.id == _RELAY_NODE_ID for n in extended.nodes), True)
    check("A3b: extended mesh has xcom_relay→base_worker edge",
          any(e.source_id == _RELAY_NODE_ID and e.target_id == "base_worker"
              for e in extended.edges), True)
    # A3c: xcom_relay is an external SOURCE — by design it is not reachable from
    # the base governance anchor (information flows TO the anchor, not from it).
    # PARTITION_DETECTED is the correct and expected verdict: xcom_relay sits
    # outside the base anchor's governance downstream. Mesh designers who want
    # the relay inside the authority chain must route a governance feedback edge
    # (e.g. anchor→xcom_relay for CORRECTION / RETRACTION).
    check("A3c: xcom_relay correctly PARTITION_DETECTED from base governance anchor",
          audit_mesh(extended).verdict, "PARTITION_DETECTED")

    print(f"\n{'=' * 70}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} test(s) FAILED")
    print("ALL TESTS PASSED")

    print("\n── Sample renderings ──")
    print(tr0.render())
    print()
    print(tr1.render())
    print()
    print(ruling.render())


# ──────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ──────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    print("\n" + "=" * 70)
    print("STRESS TEST: xcom_mesh_adapter.py")
    print("=" * 70)

    passed = total = 0

    def check(label: str, got, expected):
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {got}")
        passed += ok
        total  += 1

    cfg = XComAdapterConfig()

    # ST-1: Full binding cap table — verify every (class, quality) pair
    expected_caps = [
        (XComSignalClass.RUMOUR,       SourceQuality.ANONYMOUS,         1),
        (XComSignalClass.RUMOUR,       SourceQuality.IDENTIFIED,        1),
        (XComSignalClass.RUMOUR,       SourceQuality.PLATFORM_VERIFIED, 1),
        (XComSignalClass.RUMOUR,       SourceQuality.INSTITUTIONAL,     1),
        (XComSignalClass.OPINION,      SourceQuality.ANONYMOUS,         1),
        (XComSignalClass.OPINION,      SourceQuality.IDENTIFIED,        1),
        (XComSignalClass.OPINION,      SourceQuality.PLATFORM_VERIFIED, 2),
        (XComSignalClass.OPINION,      SourceQuality.INSTITUTIONAL,     2),
        (XComSignalClass.NEWS,         SourceQuality.ANONYMOUS,         1),
        (XComSignalClass.NEWS,         SourceQuality.IDENTIFIED,        2),
        (XComSignalClass.NEWS,         SourceQuality.PLATFORM_VERIFIED, 2),
        (XComSignalClass.NEWS,         SourceQuality.INSTITUTIONAL,     3),
        (XComSignalClass.ANNOUNCEMENT, SourceQuality.ANONYMOUS,         1),
        (XComSignalClass.ANNOUNCEMENT, SourceQuality.IDENTIFIED,        2),
        (XComSignalClass.ANNOUNCEMENT, SourceQuality.PLATFORM_VERIFIED, 2),
        (XComSignalClass.ANNOUNCEMENT, SourceQuality.INSTITUTIONAL,     3),
    ]
    for sig_class, src_q, expected_binding in expected_caps:
        post = XComPost(
            f"st1_{sig_class.value}_{src_q.value}",
            "test_author", "event",
            sig_class, src_q,
            has_primary_ref=True,  # give best possible conditions
        )
        _, trace = ingest_xcom_post(post, cfg)
        check(
            f"ST-1 cap({sig_class.value}, {src_q.value}) = {expected_binding}",
            trace.final_binding, expected_binding,
        )

    # ST-2: coordinated=False does NOT quarantine even if flag would trigger
    p_st2 = XComPost("st2", "bot_maybe", "news_event",
                     XComSignalClass.NEWS, SourceQuality.INSTITUTIONAL,
                     coordinated_flag=False, has_primary_ref=True)
    _, tr_st2 = ingest_xcom_post(p_st2, cfg)
    check("ST-2: coordinated_flag=False → NOT quarantined",
          tr_st2.verdict, AdapterVerdict.ACCEPTED.value)

    # ST-3: quarantine_coordinated=False in config → coordinated posts are NOT quarantined
    permissive_cfg = XComAdapterConfig(quarantine_coordinated=False)
    p_st3 = XComPost("st3", "suspect_actor", "influence_op",
                     XComSignalClass.NEWS, SourceQuality.PLATFORM_VERIFIED,
                     coordinated_flag=True, has_primary_ref=True)
    _, tr_st3 = ingest_xcom_post(p_st3, permissive_cfg)
    check("ST-3: quarantine_coordinated=False → coordinated post accepted (binding=2)",
          tr_st3.verdict in {AdapterVerdict.ACCEPTED.value, AdapterVerdict.CAPPED.value},
          True)

    # ST-4: logical_ts_offset correctly applied
    p_st4 = XComPost("st4", "author", "event_st4",
                     XComSignalClass.ANNOUNCEMENT, SourceQuality.INSTITUTIONAL,
                     logical_ts=10)
    offset_cfg = XComAdapterConfig(logical_ts_offset=100)
    pkt_st4, _ = ingest_xcom_post(p_st4, offset_cfg)
    check("ST-4: logical_ts_offset=100 + post.logical_ts=10 → packet.logical_ts=110",
          pkt_st4.logical_ts if pkt_st4 else None, 110)

    # ST-5: packet_id_prefix applied correctly
    p_st5 = XComPost("abc123", "author", "content_st5",
                     XComSignalClass.NEWS, SourceQuality.INSTITUTIONAL,
                     has_primary_ref=True)
    prefix_cfg = XComAdapterConfig(packet_id_prefix="gov_xcom_")
    pkt_st5, tr_st5 = ingest_xcom_post(p_st5, prefix_cfg)
    check("ST-5: packet_id = prefix + post_id",
          tr_st5.packet_id, "gov_xcom_abc123")

    # ST-6: engagement_score boundary validation
    raised = False
    try:
        _ = XComPost("bad_eng", "a", "tag",
                     XComSignalClass.NEWS, SourceQuality.IDENTIFIED,
                     engagement_score=1.5)
    except ValueError:
        raised = True
    check("ST-6: engagement_score > 1.0 raises ValueError",
          raised, True)

    # ST-7: reply chain does not change binding (structural metadata, not epistemic)
    p_reply = XComPost("st7r", "journalist_v", "thread_context",
                       XComSignalClass.NEWS, SourceQuality.PLATFORM_VERIFIED,
                       has_primary_ref=True, is_reply_chain=True)
    p_direct = XComPost("st7d", "journalist_v", "direct_post",
                        XComSignalClass.NEWS, SourceQuality.PLATFORM_VERIFIED,
                        has_primary_ref=True, is_reply_chain=False)
    _, tr_reply  = ingest_xcom_post(p_reply, cfg)
    _, tr_direct = ingest_xcom_post(p_direct, cfg)
    check("ST-7: is_reply_chain does not change binding (structural only)",
          tr_reply.final_binding == tr_direct.final_binding, True)

    # ST-8: extend_mesh_with_xcom preserves anchor_id
    base_nodes2 = (
        MeshNode("root", "Root", 1, frozenset(PayloadType), True),
        MeshNode("leaf", "Leaf", 1, frozenset({PayloadType.FINDING}), True),
    )
    base_mesh2 = MeshNetwork(
        "base2", base_nodes2,
        (MeshEdge("root", "leaf", frozenset({PayloadType.FINDING})),),
        "root",
    )
    ext2 = extend_mesh_with_xcom(base_mesh2, ["leaf"])
    check("ST-8: extend_mesh_with_xcom preserves anchor_id",
          ext2.anchor_id, "root")
    check("ST-8b: extended mesh name gets +xcom suffix",
          ext2.name, "base2+xcom")

    # ST-9: X.com packet payload_type is always FINDING — cannot be RULING
    p_st9 = XComPost("st9", "inst_acc", "policy_announcement",
                     XComSignalClass.ANNOUNCEMENT, SourceQuality.INSTITUTIONAL,
                     has_primary_ref=True)
    pkt_st9, _ = ingest_xcom_post(p_st9, cfg)
    check("ST-9: X.com packet always FINDING — never RULING",
          pkt_st9.payload_type if pkt_st9 else None, PayloadType.FINDING)

    # ST-10: require_primary_ref_for=empty set means no downgrade for NEWS
    no_req_cfg = XComAdapterConfig(require_primary_ref_for=frozenset())
    p_st10 = XComPost("st10", "journalist_v", "unref_news",
                      XComSignalClass.NEWS, SourceQuality.PLATFORM_VERIFIED,
                      has_primary_ref=False)
    _, tr_st10 = ingest_xcom_post(p_st10, no_req_cfg)
    check("ST-10: require_primary_ref_for=∅ → NEWS without ref not downgraded",
          tr_st10.signal_class, XComSignalClass.NEWS.value)
    check("ST-10b: binding=2 (PLATFORM_VERIFIED NEWS)",
          tr_st10.final_binding, 2)

    print(f"\n{'=' * 70}")
    print(f"Stress result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} stress test(s) FAILED")
    print("ALL STRESS TESTS PASSED")


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    _stress_test()
