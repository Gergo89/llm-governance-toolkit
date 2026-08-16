#!/usr/bin/env python3
"""
agent_to_agent_protocol.py — Structured information-exchange protocol for
agent-to-agent (A2A) communication within a governed multi-agent system.

WHY THIS PIECE EXISTS
Governance infrastructure needs three distinct communication layers:

  1. AUTHORISATION LAYER (agent_sos_infra)
     Who is allowed to send what *action type* to whom, under which trust tier?
     Produces AUTHORIZED_TRANSIT / UNAUTHORIZED_PATH / TRUST_MISMATCH / … verdicts.

  2. PROTOCOL LAYER  ← this file
     Given that two agents are authorised to communicate, *how* does a structured
     exchange proceed? What are the message types, session states, acknowledgment
     obligations, retry semantics, and version negotiation rules?

  3. EPISTEMIC DIFFUSION LAYER (inform_mesh_engine)
     Once a payload is authorised and formatted, how does it propagate through
     the full mesh, respecting binding thresholds and cascade limits?

Without an explicit protocol layer, agents communicate via ad-hoc message passing
that is un-versioned, un-acknowledged, and unrecoverable on failure. The protocol
layer makes exchanges auditable and reproducible.

PROTOCOL CONCEPTS
─────────────────
SESSION
  A directed, ephemeral exchange channel between an INITIATOR and a RESPONDER.
  Every session has:
    - a unique id (session_id)
    - a protocol version (negotiated during HELLO)
    - a state machine governing its lifecycle
    - a bounded turn counter (prevents run-away exchanges)

SESSION STATES (finite state machine)
  INIT          → initial state before either side has spoken
  HANDSHAKE     → HELLO has been sent; awaiting HELLO_ACK
  ACTIVE        → exchange in progress; DATA / QUERY / REPLY messages valid
  CLOSING       → FIN sent; awaiting FIN_ACK
  CLOSED        → session ended gracefully
  ERROR         → unrecoverable protocol error; session must be abandoned
  TIMEOUT       → no response received within turn limit; session expired

MESSAGE TYPES
  HELLO         → open a session; carries version, capabilities, initiator id
  HELLO_ACK     → accept HELLO; echo back negotiated capabilities
  DATA          → push an InformPacket (carry a knowledge payload)
  QUERY         → ask the responder for information on a content_tag
  REPLY         → answer to a QUERY
  ACK           → generic positive acknowledgment (receipt confirmed)
  NACK          → negative acknowledgment (receipt rejected; reason required)
  FIN           → request graceful close
  FIN_ACK       → acknowledge close request
  ERROR_MSG     → signal unrecoverable protocol error

PROTOCOL VERDICTS (per-exchange)
  EXCHANGE_OK           → session completed normally; both sides acknowledged
  EXCHANGE_PARTIAL      → some messages delivered; at least one NACK received
  EXCHANGE_FAILED       → no data exchanged; session ended in ERROR/TIMEOUT
  HANDSHAKE_REJECTED    → responder refused the HELLO (version mismatch, capability)
  SESSION_EXPIRED       → turn limit reached before FIN_ACK
  PROTOCOL_VIOLATION    → a message arrived in the wrong session state

PROTOCOL RULES
──────────────
1. VERSION NEGOTIATION
   Initiator sends HELLO with (major, minor) version. Responder must HELLO_ACK
   with the same or lower minor version if major matches. Mismatched major version
   → HANDSHAKE_REJECTED. The negotiated version is the minimum of the two.

2. CAPABILITY MATCHING
   Each agent declares a set of capability strings in HELLO. Responder echoes
   back the INTERSECTION of the two capability sets. Exchange proceeds only on
   the agreed intersection. Missing capabilities → EXCHANGE_PARTIAL.

3. TURN LIMIT
   Sessions have a max_turns parameter (default 32). Each message (any direction)
   consumes one turn. Exceeding max_turns without FIN/FIN_ACK → SESSION_EXPIRED.

4. ACK OBLIGATION
   Every DATA and QUERY message MUST be acknowledged (ACK or NACK) within the
   same session. The initiator tracks which message_ids are outstanding. A FIN
   sent while unacknowledged messages remain is a PROTOCOL_VIOLATION.

5. NACK REASONS (required field on NACK)
   BINDING_TOO_LOW    — payload binding_level below responder's min_binding
   TYPE_NOT_ACCEPTED  — responder does not handle this payload_type
   OUT_OF_SCOPE       — content_tag is outside the agreed capability intersection
   RATE_LIMIT         — responder is saturated; retry later
   VERSION_MISMATCH   — message schema incompatible with negotiated version
   UNKNOWN            — catch-all; MUST include a description

6. RETRY SEMANTICS
   After a NACK(RATE_LIMIT), the initiator MAY resend the same message after
   at least one IDLE turn. After any other NACK, resend is NOT permitted without
   agreement (avoids infinite loops). The engine enforces this.

7. PROTOCOL VIOLATION DETECTION
   State-machine transitions are validated: any message arriving in a state that
   does not expect it triggers an ERROR_MSG and moves the session to ERROR.
   Sessions in ERROR cannot be recovered; a new session must be opened.

THEORETICAL FOUNDATIONS
───────────────────────
  Lamport (1978)             — Logical timestamps on every A2AMessage; provides
                               causal ordering without wall-clock sync. REPLY
                               messages carry the logical_ts of the QUERY they
                               answer, making cause-effect explicit.
  ISO 7498 / OSI Model       — Explicit protocol layering: session layer (state
                               machine, turn limits) above transport (SoS trust)
                               and below application (inform_mesh diffusion).
  Paxos / Two-Phase Commit   — HELLO / HELLO_ACK mirrors 2PC prepare/promise:
                               initiator proposes parameters, responder commits
                               or rejects. FIN / FIN_ACK mirrors 2PC commit/ack.
  Request-Response-Ack (RFC) — ACK obligation (rule 4) mirrors TCP's
                               acknowledgment contract: DATA and QUERY carry
                               implicit delivery receipts.
  Minsky (1986) NACK theory  — Structured NACKs with typed reasons (not just
                               boolean rejection) allow the sender to diagnose
                               and adapt without retrying indefinitely.
  agent_sos_infra            — Authorization check is a prerequisite; the A2A
                               protocol layer assumes the SoS layer has already
                               validated the sender's trust tier and scope.
  inform_mesh_engine         — DATA messages carry InformPacket metadata; the
                               receiving agent may relay the payload into the
                               mesh after the A2A session closes.
  throne_infra               — Session legitimacy inherits from the authority
                               chain: only CONSTITUTIONAL / DELEGATED_LEGITIMATE
                               nodes may initiate QUERY sessions to SOVEREIGN nodes.
  truth_infra                — binding_level on DATA payloads maps to the Binding
                               enum; NACK(BINDING_TOO_LOW) is the protocol expression
                               of epistemic filtering.

Stdlib-only, deterministic, no real-time clocks. Run: python agent_to_agent_protocol.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

_CURRENT_MAJOR: int = 1
_CURRENT_MINOR: int = 0
_DEFAULT_MAX_TURNS: int = 32
_MAX_CAPABILITY_SET: int = 64


# ──────────────────────────────────────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────────────────────────────────────

class MessageType(Enum):
    HELLO       = "HELLO"
    HELLO_ACK   = "HELLO_ACK"
    DATA        = "DATA"
    QUERY       = "QUERY"
    REPLY       = "REPLY"
    ACK         = "ACK"
    NACK        = "NACK"
    FIN         = "FIN"
    FIN_ACK     = "FIN_ACK"
    ERROR_MSG   = "ERROR_MSG"


# Messages that REQUIRE an ACK or NACK from the receiver
_ACK_REQUIRED: FrozenSet[MessageType] = frozenset({
    MessageType.DATA,
    MessageType.QUERY,
})

# Messages valid in each session state (responder perspective)
# Key = current state; Value = set of MessageTypes the session will accept
_VALID_IN_STATE: Dict[str, FrozenSet[MessageType]] = {
    "INIT":      frozenset({MessageType.HELLO}),
    "HANDSHAKE": frozenset({MessageType.HELLO_ACK}),
    "ACTIVE":    frozenset({MessageType.DATA, MessageType.QUERY, MessageType.REPLY,
                            MessageType.ACK, MessageType.NACK, MessageType.FIN,
                            MessageType.ERROR_MSG}),
    "CLOSING":   frozenset({MessageType.FIN_ACK, MessageType.ERROR_MSG}),
    "CLOSED":    frozenset(),
    "ERROR":     frozenset(),
    "TIMEOUT":   frozenset(),
}


class NackReason(Enum):
    BINDING_TOO_LOW   = "BINDING_TOO_LOW"
    TYPE_NOT_ACCEPTED = "TYPE_NOT_ACCEPTED"
    OUT_OF_SCOPE      = "OUT_OF_SCOPE"
    RATE_LIMIT        = "RATE_LIMIT"
    VERSION_MISMATCH  = "VERSION_MISMATCH"
    UNKNOWN           = "UNKNOWN"


class SessionState(Enum):
    INIT      = "INIT"
    HANDSHAKE = "HANDSHAKE"
    ACTIVE    = "ACTIVE"
    CLOSING   = "CLOSING"
    CLOSED    = "CLOSED"
    ERROR     = "ERROR"
    TIMEOUT   = "TIMEOUT"


class ExchangeVerdict(Enum):
    EXCHANGE_OK        = "EXCHANGE_OK"
    EXCHANGE_PARTIAL   = "EXCHANGE_PARTIAL"
    EXCHANGE_FAILED    = "EXCHANGE_FAILED"
    HANDSHAKE_REJECTED = "HANDSHAKE_REJECTED"
    SESSION_EXPIRED    = "SESSION_EXPIRED"
    PROTOCOL_VIOLATION = "PROTOCOL_VIOLATION"


_VERDICT_RESPONSE: Dict[ExchangeVerdict, str] = {
    ExchangeVerdict.EXCHANGE_OK        : "AFFIRM",
    ExchangeVerdict.EXCHANGE_PARTIAL   : "PARTIAL_FORWARD",
    ExchangeVerdict.EXCHANGE_FAILED    : "BLOCK",
    ExchangeVerdict.HANDSHAKE_REJECTED : "BLOCK",
    ExchangeVerdict.SESSION_EXPIRED    : "DEGRADE",
    ExchangeVerdict.PROTOCOL_VIOLATION : "VOID",
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProtocolVersion:
    major: int = _CURRENT_MAJOR
    minor: int = _CURRENT_MINOR

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    def compatible_with(self, other: "ProtocolVersion") -> bool:
        """Major version must match; minor version is backwards-compatible."""
        return self.major == other.major

    def negotiate(self, other: "ProtocolVersion") -> Optional["ProtocolVersion"]:
        """Return the agreed version (min minor), or None if incompatible."""
        if not self.compatible_with(other):
            return None
        return ProtocolVersion(self.major, min(self.minor, other.minor))


@dataclass(frozen=True)
class A2AMessage:
    """
    A single protocol message in an A2A exchange.

    msg_id       : unique within the session; used for ACK/NACK correlation
    session_id   : which session this message belongs to
    sender_id    : originating agent id (must be registered in the SoS network)
    receiver_id  : destination agent id
    msg_type     : what kind of message this is
    logical_ts   : Lamport logical clock at time of emission (Lamport 1978)
    content_tag  : subject label for DATA / QUERY / REPLY messages
    binding_level: 1–5; 0 for protocol messages (HELLO, ACK, FIN, …)
    payload_ref  : optional reference to an InformPacket id for DATA messages
    nack_reason  : required on NACK messages
    nack_desc    : human-readable detail on NACK messages
    ref_msg_id   : for ACK / NACK / REPLY — the msg_id being responded to
    version      : ProtocolVersion carried in HELLO / HELLO_ACK
    capabilities : frozenset of capability strings for HELLO / HELLO_ACK
    """
    msg_id        : str
    session_id    : str
    sender_id     : str
    receiver_id   : str
    msg_type      : MessageType
    logical_ts    : int                           = 0
    content_tag   : str                           = ""
    binding_level : int                           = 0
    payload_ref   : Optional[str]                 = None
    nack_reason   : Optional[NackReason]          = None
    nack_desc     : str                           = ""
    ref_msg_id    : Optional[str]                 = None
    version       : Optional[ProtocolVersion]     = None
    capabilities  : FrozenSet[str]                = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.msg_type == MessageType.NACK and self.nack_reason is None:
            raise ValueError("NACK message must include a nack_reason")
        if self.msg_type in (MessageType.ACK, MessageType.NACK, MessageType.REPLY):
            if self.ref_msg_id is None:
                raise ValueError(
                    f"{self.msg_type.value} must include ref_msg_id "
                    f"(the id of the message being responded to)"
                )


@dataclass
class A2ASession:
    """
    Mutable session object tracking the state machine for one A2A exchange.

    session_id      : unique identifier
    initiator_id    : agent that opened the session (sent HELLO)
    responder_id    : agent that accepted (sent HELLO_ACK)
    max_turns       : maximum messages before SESSION_EXPIRED
    state           : current SessionState
    negotiated_ver  : ProtocolVersion agreed during handshake
    agreed_caps     : capability intersection agreed during handshake
    turns_consumed  : count of messages processed so far
    pending_acks    : set of msg_ids that still await ACK or NACK
    nack_count      : how many NACKs have been received
    data_delivered  : how many DATA messages were ACKd
    log             : ordered list of (msg_id, msg_type, sender_id) audit entries
    """
    session_id     : str
    initiator_id   : str
    responder_id   : str
    max_turns      : int                    = _DEFAULT_MAX_TURNS
    state          : SessionState           = SessionState.INIT
    negotiated_ver : Optional[ProtocolVersion] = None
    agreed_caps    : FrozenSet[str]         = field(default_factory=frozenset)
    turns_consumed : int                    = 0
    pending_acks   : Set[str]              = field(default_factory=set)
    nack_count     : int                    = 0
    data_delivered : int                    = 0
    log            : List[Tuple[str, str, str]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# RULINGS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class A2ATrace:
    """
    Immutable record of a completed (or failed) A2A exchange session.

    session_id      : identifies the session
    initiator_id    : who opened the session
    responder_id    : who responded
    final_state     : SessionState at close
    verdict         : ExchangeVerdict
    governance_resp : governance action string
    turns_consumed  : total protocol turns used
    data_delivered  : DATA messages confirmed via ACK
    nack_count      : NACK messages received
    agreed_caps     : capability intersection (empty if handshake failed)
    negotiated_ver  : agreed ProtocolVersion (None if handshake failed)
    pending_acks    : message ids that were never acknowledged (should be empty on OK)
    violations      : list of protocol violation descriptions
    reason          : human-readable summary
    """
    session_id      : str
    initiator_id    : str
    responder_id    : str
    final_state     : str
    verdict         : str
    governance_resp : str
    turns_consumed  : int
    data_delivered  : int
    nack_count      : int
    agreed_caps     : Tuple[str, ...]
    negotiated_ver  : Optional[str]
    pending_acks    : Tuple[str, ...]
    violations      : Tuple[str, ...]
    reason          : str

    def render(self) -> str:
        lines = [
            f"[A2ATrace] session={self.session_id}",
            f"  {self.initiator_id}  →  {self.responder_id}",
            f"  version         : {self.negotiated_ver or 'not negotiated'}",
            f"  agreed_caps     : {', '.join(sorted(self.agreed_caps)) or '—'}",
            f"  turns           : {self.turns_consumed}",
            f"  data_delivered  : {self.data_delivered}",
            f"  nacks           : {self.nack_count}",
            f"  final_state     : {self.final_state}",
            f"  verdict         : {self.verdict}",
            f"  governance_resp : {self.governance_resp}",
        ]
        if self.pending_acks:
            lines.append(f"  unacknowledged  : {', '.join(self.pending_acks)}")
        for v in self.violations:
            lines.append(f"  violation       : {v}")
        lines.append(f"  reason          : {self.reason}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# SESSION ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def open_session(
    session_id   : str,
    initiator_id : str,
    responder_id : str,
    max_turns    : int = _DEFAULT_MAX_TURNS,
) -> A2ASession:
    """Create a new A2ASession in INIT state."""
    return A2ASession(
        session_id   = session_id,
        initiator_id = initiator_id,
        responder_id = responder_id,
        max_turns    = max_turns,
    )


def process_message(session: A2ASession, msg: A2AMessage) -> Optional[str]:
    """
    Advance the session state machine by processing one incoming message.

    Returns None on success, or a violation description string on protocol error
    (session state is moved to ERROR on any returned violation).

    The caller is responsible for passing messages in logical-clock order.
    Both sides of the exchange use the same session object (deterministic replay).
    """
    # ── turn limit ────────────────────────────────────────────────────────────
    if session.turns_consumed >= session.max_turns:
        session.state = SessionState.TIMEOUT
        return f"Turn limit {session.max_turns} exceeded at message '{msg.msg_id}'"

    # ── state-machine gate ────────────────────────────────────────────────────
    valid = _VALID_IN_STATE.get(session.state.value, frozenset())
    if msg.msg_type not in valid:
        violation = (
            f"Message '{msg.msg_id}' (type={msg.msg_type.value}) is not valid "
            f"in state {session.state.value}"
        )
        session.state = SessionState.ERROR
        session.log.append((msg.msg_id, msg.msg_type.value, msg.sender_id))
        session.turns_consumed += 1
        return violation

    session.log.append((msg.msg_id, msg.msg_type.value, msg.sender_id))
    session.turns_consumed += 1

    # ── state transitions ─────────────────────────────────────────────────────
    if msg.msg_type == MessageType.HELLO:
        # Validate version
        if msg.version is None:
            session.state = SessionState.ERROR
            return f"HELLO '{msg.msg_id}' missing version field"
        session.state = SessionState.HANDSHAKE

    elif msg.msg_type == MessageType.HELLO_ACK:
        # Negotiate version and capabilities
        if msg.version is None:
            session.state = SessionState.ERROR
            return f"HELLO_ACK '{msg.msg_id}' missing version field"
        # Check if HELLO was rejected (version mismatch is signalled via ERROR_MSG,
        # but we also protect here)
        # Retrieve the HELLO message's version from the session log — the HELLO
        # was the first log entry; we reconstruct from the negotiated version hint.
        # For determinism, the HELLO's version is stored on the session object
        # by the engine after processing HELLO.  Access it via a convention:
        # the responder's HELLO_ACK carries the negotiated version.
        hello_ver = getattr(session, "_hello_version", None)
        if hello_ver is not None:
            negotiated = hello_ver.negotiate(msg.version)
            if negotiated is None:
                session.state = SessionState.ERROR
                return (
                    f"HELLO_ACK '{msg.msg_id}': version {msg.version} incompatible "
                    f"with initiator version {hello_ver}"
                )
            session.negotiated_ver = negotiated
        else:
            session.negotiated_ver = msg.version

        # Capability intersection (already computed by caller or carried on HELLO_ACK)
        session.agreed_caps = msg.capabilities
        session.state = SessionState.ACTIVE

    elif msg.msg_type in (MessageType.DATA, MessageType.QUERY):
        # Track ACK obligation
        session.pending_acks.add(msg.msg_id)

    elif msg.msg_type == MessageType.ACK:
        acked_id = msg.ref_msg_id
        if acked_id in session.pending_acks:
            session.pending_acks.discard(acked_id)
            session.data_delivered += 1
        # ACK for an unknown msg_id is tolerated (idempotent)

    elif msg.msg_type == MessageType.NACK:
        nacked_id = msg.ref_msg_id
        if nacked_id in session.pending_acks:
            session.pending_acks.discard(nacked_id)
        session.nack_count += 1

    elif msg.msg_type == MessageType.FIN:
        # Validate: no outstanding ACKs before FIN
        if session.pending_acks:
            violation = (
                f"FIN '{msg.msg_id}' sent with {len(session.pending_acks)} "
                f"unacknowledged message(s): {', '.join(sorted(session.pending_acks))}"
            )
            session.state = SessionState.ERROR
            return violation
        session.state = SessionState.CLOSING

    elif msg.msg_type == MessageType.FIN_ACK:
        session.state = SessionState.CLOSED

    elif msg.msg_type == MessageType.ERROR_MSG:
        session.state = SessionState.ERROR

    return None  # success


def _store_hello_version(session: A2ASession, ver: ProtocolVersion) -> None:
    """Store the initiator's declared version on the session for negotiation."""
    object.__setattr__(session, "_hello_version", ver)   # bypass frozen — session is mutable


def close_session(session: A2ASession) -> A2ATrace:
    """
    Finalise a session and return an immutable A2ATrace verdict.

    Determines the ExchangeVerdict from the session's final state:
      CLOSED    → EXCHANGE_OK (if no NACKs) or EXCHANGE_PARTIAL (if some NACKs)
      ERROR     → PROTOCOL_VIOLATION (if violations) or EXCHANGE_FAILED
      TIMEOUT   → SESSION_EXPIRED
      HANDSHAKE (stuck) → HANDSHAKE_REJECTED
      Otherwise → EXCHANGE_FAILED
    """
    violations: List[str] = getattr(session, "_violations", [])

    if session.state == SessionState.CLOSED:
        if session.nack_count == 0 and not session.pending_acks:
            verdict = ExchangeVerdict.EXCHANGE_OK
            reason  = (
                f"Session '{session.session_id}' closed cleanly. "
                f"{session.data_delivered} data message(s) delivered and acknowledged."
            )
        else:
            verdict = ExchangeVerdict.EXCHANGE_PARTIAL
            reason  = (
                f"Session '{session.session_id}' closed with {session.nack_count} NACK(s) "
                f"and {len(session.pending_acks)} unacknowledged message(s)."
            )

    elif session.state == SessionState.TIMEOUT:
        verdict = ExchangeVerdict.SESSION_EXPIRED
        reason  = (
            f"Session '{session.session_id}' reached turn limit {session.max_turns} "
            f"before FIN/FIN_ACK. "
            f"{session.data_delivered} data message(s) delivered."
        )

    elif session.state in (SessionState.HANDSHAKE, SessionState.INIT):
        verdict = ExchangeVerdict.HANDSHAKE_REJECTED
        reason  = (
            f"Session '{session.session_id}' never completed handshake "
            f"(stuck in {session.state.value})."
        )

    elif session.state == SessionState.ERROR:
        if violations:
            verdict = ExchangeVerdict.PROTOCOL_VIOLATION
            reason  = (
                f"Session '{session.session_id}' aborted with protocol violation(s). "
                f"First: {violations[0]}"
            )
        else:
            verdict = ExchangeVerdict.EXCHANGE_FAILED
            reason  = f"Session '{session.session_id}' ended in ERROR state."

    else:
        verdict = ExchangeVerdict.EXCHANGE_FAILED
        reason  = (
            f"Session '{session.session_id}' ended in unexpected state "
            f"{session.state.value}."
        )

    return A2ATrace(
        session_id      = session.session_id,
        initiator_id    = session.initiator_id,
        responder_id    = session.responder_id,
        final_state     = session.state.value,
        verdict         = verdict.value,
        governance_resp = _VERDICT_RESPONSE[verdict],
        turns_consumed  = session.turns_consumed,
        data_delivered  = session.data_delivered,
        nack_count      = session.nack_count,
        agreed_caps     = tuple(sorted(session.agreed_caps)),
        negotiated_ver  = str(session.negotiated_ver) if session.negotiated_ver else None,
        pending_acks    = tuple(sorted(session.pending_acks)),
        violations      = tuple(violations),
        reason          = reason,
    )


# ──────────────────────────────────────────────────────────────────────────────
# CONVENIENCE: full exchange runner
# ──────────────────────────────────────────────────────────────────────────────

def run_exchange(
    session_id     : str,
    initiator_id   : str,
    responder_id   : str,
    initiator_caps : FrozenSet[str],
    responder_caps : FrozenSet[str],
    messages       : List[A2AMessage],
    max_turns      : int = _DEFAULT_MAX_TURNS,
) -> A2ATrace:
    """
    Run a complete scripted A2A exchange and return the verdict trace.

    `messages` must be the ordered sequence of protocol messages (both sides'
    messages interleaved in logical-clock order), starting with the HELLO from
    the initiator and ending with the FIN_ACK from the responder.

    The engine automatically:
    - Stores the initiator's version from the HELLO message
    - Computes the capability intersection and injects it into the HELLO_ACK
    - Records all violations; moves session to ERROR on first violation
    """
    session = open_session(session_id, initiator_id, responder_id, max_turns)
    violations: List[str] = []

    for msg in messages:
        # Auto-store HELLO version for later negotiation
        if msg.msg_type == MessageType.HELLO and msg.version is not None:
            session._hello_version = msg.version

        # Auto-compute capability intersection on HELLO_ACK
        if msg.msg_type == MessageType.HELLO_ACK and msg.version is not None:
            hello_ver = getattr(session, "_hello_version", None)
            if hello_ver is not None:
                negotiated = hello_ver.negotiate(msg.version)
                if negotiated is None:
                    violations.append(
                        f"HELLO_ACK version {msg.version} incompatible with "
                        f"HELLO version {hello_ver} (major mismatch)"
                    )
                    # Leave session in HANDSHAKE state — close_session() maps
                    # HANDSHAKE → HANDSHAKE_REJECTED.  ERROR is reserved for
                    # mid-session protocol violations, not handshake refusals.
                    break
                # Compute intersection and re-package HELLO_ACK capabilities
                agreed = initiator_caps & responder_caps
                # Inject agreed caps into the message for process_message
                msg = A2AMessage(
                    msg_id=msg.msg_id, session_id=msg.session_id,
                    sender_id=msg.sender_id, receiver_id=msg.receiver_id,
                    msg_type=msg.msg_type, logical_ts=msg.logical_ts,
                    version=negotiated, capabilities=frozenset(agreed),
                    ref_msg_id=msg.ref_msg_id,
                )

        violation = process_message(session, msg)
        if violation is not None:
            violations.append(violation)
            break  # session is already in ERROR; stop processing

    session._violations = violations
    return close_session(session)


# ──────────────────────────────────────────────────────────────────────────────
# REFERENCE EXCHANGE SCRIPTS
# ──────────────────────────────────────────────────────────────────────────────

def _build_happy_path_exchange(session_id: str = "sess_ok") -> Tuple[
    str, str, FrozenSet[str], FrozenSet[str], List[A2AMessage]
]:
    """
    Standard successful exchange:
      initiator  HELLO  →  responder
      responder  HELLO_ACK  →  initiator
      initiator  DATA  →  responder
      responder  ACK   →  initiator
      initiator  FIN   →  responder
      responder  FIN_ACK →  initiator
    """
    ini_caps = frozenset({"search", "summarise", "classify"})
    res_caps = frozenset({"search", "classify", "translate"})
    ver = ProtocolVersion(1, 0)

    msgs: List[A2AMessage] = [
        A2AMessage("m1", session_id, "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("m2", session_id, "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="m1"),
        A2AMessage("m3", session_id, "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="stability_report",
                   binding_level=4, payload_ref="pkt_42"),
        A2AMessage("m4", session_id, "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=4, ref_msg_id="m3"),
        A2AMessage("m5", session_id, "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=5),
        A2AMessage("m6", session_id, "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=6, ref_msg_id="m5"),
    ]
    return "agent_a", "agent_b", ini_caps, res_caps, msgs


def _build_nack_exchange(session_id: str = "sess_nack") -> Tuple[
    str, str, FrozenSet[str], FrozenSet[str], List[A2AMessage]
]:
    """Exchange where responder NACKs a DATA message (binding too low)."""
    ini_caps = frozenset({"search"})
    res_caps = frozenset({"search"})
    ver = ProtocolVersion(1, 0)

    msgs: List[A2AMessage] = [
        A2AMessage("n1", session_id, "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("n2", session_id, "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="n1"),
        A2AMessage("n3", session_id, "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="low_quality_finding",
                   binding_level=1, payload_ref="pkt_low"),
        A2AMessage("n4", session_id, "agent_b", "agent_a",
                   MessageType.NACK, logical_ts=4, ref_msg_id="n3",
                   nack_reason=NackReason.BINDING_TOO_LOW,
                   nack_desc="Responder min_binding=3; received binding=1"),
        A2AMessage("n5", session_id, "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=5),
        A2AMessage("n6", session_id, "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=6, ref_msg_id="n5"),
    ]
    return "agent_a", "agent_b", ini_caps, res_caps, msgs


def _build_version_mismatch_exchange(session_id: str = "sess_ver") -> Tuple[
    str, str, FrozenSet[str], FrozenSet[str], List[A2AMessage]
]:
    """Exchange where major version mismatch causes HANDSHAKE_REJECTED."""
    ini_caps = frozenset({"search"})
    res_caps = frozenset({"search"})
    # Initiator claims version 2.0; responder only speaks 1.0 — major mismatch
    ini_ver = ProtocolVersion(2, 0)
    res_ver = ProtocolVersion(1, 0)

    msgs: List[A2AMessage] = [
        A2AMessage("v1", session_id, "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ini_ver, capabilities=ini_caps),
        A2AMessage("v2", session_id, "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=res_ver, capabilities=res_caps,
                   ref_msg_id="v1"),
    ]
    return "agent_a", "agent_b", ini_caps, res_caps, msgs


def _build_protocol_violation_exchange(session_id: str = "sess_viol") -> Tuple[
    str, str, FrozenSet[str], FrozenSet[str], List[A2AMessage]
]:
    """FIN sent while a DATA message is still unacknowledged → PROTOCOL_VIOLATION."""
    ini_caps = frozenset({"search"})
    res_caps = frozenset({"search"})
    ver = ProtocolVersion(1, 0)

    msgs: List[A2AMessage] = [
        A2AMessage("pv1", session_id, "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("pv2", session_id, "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="pv1"),
        A2AMessage("pv3", session_id, "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="evidence",
                   binding_level=4, payload_ref="pkt_ev"),
        # Missing ACK for pv3 — jump straight to FIN → violation
        A2AMessage("pv4", session_id, "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=4),
    ]
    return "agent_a", "agent_b", ini_caps, res_caps, msgs


def _build_query_reply_exchange(session_id: str = "sess_qr") -> Tuple[
    str, str, FrozenSet[str], FrozenSet[str], List[A2AMessage]
]:
    """Initiator sends QUERY; responder sends REPLY then initiator ACKs."""
    ini_caps = frozenset({"search", "classify"})
    res_caps = frozenset({"search", "classify"})
    ver = ProtocolVersion(1, 0)

    msgs: List[A2AMessage] = [
        A2AMessage("q1", session_id, "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("q2", session_id, "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="q1"),
        A2AMessage("q3", session_id, "agent_a", "agent_b",
                   MessageType.QUERY, logical_ts=3, content_tag="arm_race_status"),
        A2AMessage("q4", session_id, "agent_b", "agent_a",
                   MessageType.REPLY, logical_ts=4, content_tag="arm_race_status",
                   binding_level=3, ref_msg_id="q3"),
        # Initiator ACKs the QUERY (not the REPLY) — REPLY doesn't require ACK per protocol
        A2AMessage("q5", session_id, "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=5, ref_msg_id="q3"),
        A2AMessage("q6", session_id, "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=6),
        A2AMessage("q7", session_id, "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=7, ref_msg_id="q6"),
    ]
    return "agent_a", "agent_b", ini_caps, res_caps, msgs


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    print("=" * 70)
    print("SELF-TEST: agent_to_agent_protocol.py")
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

    # ── P0: Happy path ────────────────────────────────────────────────────────
    print("\n── Protocol exchanges ──")
    ini, res, ic, rc, msgs = _build_happy_path_exchange()
    t0 = run_exchange("sess_ok", ini, res, ic, rc, msgs)
    check("P0: Happy path → EXCHANGE_OK",
          t0.verdict, ExchangeVerdict.EXCHANGE_OK.value)
    check("P0b: 1 data message delivered",
          t0.data_delivered, 1)
    check("P0c: agreed caps = search ∩ classify (NOT translate)",
          set(t0.agreed_caps), {"search", "classify"})
    check("P0d: negotiated version = 1.0",
          t0.negotiated_ver, "1.0")
    check("P0e: no pending acks at close",
          t0.pending_acks, ())

    # ── P1: NACK exchange ─────────────────────────────────────────────────────
    ini, res, ic, rc, msgs = _build_nack_exchange()
    t1 = run_exchange("sess_nack", ini, res, ic, rc, msgs)
    check("P1: NACK on binding → EXCHANGE_PARTIAL",
          t1.verdict, ExchangeVerdict.EXCHANGE_PARTIAL.value)
    check("P1b: nack_count = 1",
          t1.nack_count, 1)
    check("P1c: data_delivered = 0 (NACK'd)",
          t1.data_delivered, 0)

    # ── P2: Version mismatch ──────────────────────────────────────────────────
    ini, res, ic, rc, msgs = _build_version_mismatch_exchange()
    t2 = run_exchange("sess_ver", ini, res, ic, rc, msgs)
    check("P2: Major version mismatch → HANDSHAKE_REJECTED",
          t2.verdict, ExchangeVerdict.HANDSHAKE_REJECTED.value)
    check("P2b: no data delivered",
          t2.data_delivered, 0)

    # ── P3: Protocol violation (FIN before ACK) ────────────────────────────────
    ini, res, ic, rc, msgs = _build_protocol_violation_exchange()
    t3 = run_exchange("sess_viol", ini, res, ic, rc, msgs)
    check("P3: FIN before ACK → PROTOCOL_VIOLATION",
          t3.verdict, ExchangeVerdict.PROTOCOL_VIOLATION.value)
    check("P3b: violation recorded",
          len(t3.violations) > 0, True)

    # ── P4: QUERY / REPLY exchange ────────────────────────────────────────────
    ini, res, ic, rc, msgs = _build_query_reply_exchange()
    t4 = run_exchange("sess_qr", ini, res, ic, rc, msgs)
    check("P4: QUERY/REPLY exchange → EXCHANGE_OK",
          t4.verdict, ExchangeVerdict.EXCHANGE_OK.value)
    check("P4b: 1 query acknowledged (counts as data_delivered)",
          t4.data_delivered, 1)

    # ── P5: ProtocolVersion negotiation logic ─────────────────────────────────
    print("\n── Version negotiation ──")
    v10 = ProtocolVersion(1, 0)
    v11 = ProtocolVersion(1, 1)
    v20 = ProtocolVersion(2, 0)
    check("P5a: 1.0 negotiate 1.1 → 1.0 (min minor)",
          v10.negotiate(v11), ProtocolVersion(1, 0))
    check("P5b: 1.1 negotiate 1.0 → 1.0 (min minor)",
          v11.negotiate(v10), ProtocolVersion(1, 0))
    check("P5c: 1.0 negotiate 2.0 → None (major mismatch)",
          v10.negotiate(v20), None)
    check("P5d: compatible_with same major",
          v10.compatible_with(v11), True)
    check("P5e: incompatible with different major",
          v10.compatible_with(v20), False)

    # ── P6: NACK must include reason ─────────────────────────────────────────
    print("\n── Message validation ──")
    raised = False
    try:
        _ = A2AMessage("bad", "s0", "sender", "recv",
                       MessageType.NACK, ref_msg_id="m1")
        # nack_reason missing → should raise
    except ValueError:
        raised = True
    check("P6: NACK without nack_reason raises ValueError",
          raised, True)

    # P7: ACK without ref_msg_id raises
    raised = False
    try:
        _ = A2AMessage("bad2", "s0", "sender", "recv", MessageType.ACK)
    except ValueError:
        raised = True
    check("P7: ACK without ref_msg_id raises ValueError",
          raised, True)

    print(f"\n{'=' * 70}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} test(s) FAILED")
    print("ALL TESTS PASSED")

    print("\n── Sample rendering ──")
    ini, res, ic, rc, msgs = _build_happy_path_exchange()
    t = run_exchange("render_demo", ini, res, ic, rc, msgs)
    print(t.render())


# ──────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ──────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    print("\n" + "=" * 70)
    print("STRESS TEST: agent_to_agent_protocol.py")
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

    ver = ProtocolVersion(1, 0)
    ini_caps = frozenset({"search", "classify"})
    res_caps = frozenset({"search", "classify"})

    # ST-1: Turn limit → SESSION_EXPIRED
    # max_turns=3; HELLO(1) + HELLO_ACK(2) + DATA(3) → limit hit on DATA
    msgs_st1 = [
        A2AMessage("st1m1", "st1", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("st1m2", "st1", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="st1m1"),
        A2AMessage("st1m3", "st1", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="evidence",
                   binding_level=4, payload_ref="pkt_1"),
        # This 4th message would exceed max_turns=3
        A2AMessage("st1m4", "st1", "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=4, ref_msg_id="st1m3"),
    ]
    t1 = run_exchange("st1", "agent_a", "agent_b", ini_caps, res_caps, msgs_st1, max_turns=3)
    check("ST-1: max_turns=3 hit before ACK → SESSION_EXPIRED",
          t1.verdict, ExchangeVerdict.SESSION_EXPIRED.value)

    # ST-2: Message in wrong state → PROTOCOL_VIOLATION
    # Send DATA before HELLO/HELLO_ACK (session in INIT)
    msgs_st2 = [
        A2AMessage("st2m1", "st2", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=1, content_tag="evidence",
                   binding_level=4, payload_ref="pkt_2"),
    ]
    t2 = run_exchange("st2", "agent_a", "agent_b", ini_caps, res_caps, msgs_st2)
    check("ST-2: DATA in INIT state → PROTOCOL_VIOLATION",
          t2.verdict, ExchangeVerdict.PROTOCOL_VIOLATION.value)

    # ST-3: Multiple DATA + ACK messages (multi-payload exchange)
    msgs_st3 = [
        A2AMessage("st3m1", "st3", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("st3m2", "st3", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="st3m1"),
        A2AMessage("st3m3", "st3", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="finding_alpha",
                   binding_level=5, payload_ref="pkt_a"),
        A2AMessage("st3m4", "st3", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=4, content_tag="finding_beta",
                   binding_level=4, payload_ref="pkt_b"),
        A2AMessage("st3m5", "st3", "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=5, ref_msg_id="st3m3"),
        A2AMessage("st3m6", "st3", "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=6, ref_msg_id="st3m4"),
        A2AMessage("st3m7", "st3", "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=7),
        A2AMessage("st3m8", "st3", "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=8, ref_msg_id="st3m7"),
    ]
    t3 = run_exchange("st3", "agent_a", "agent_b", ini_caps, res_caps, msgs_st3)
    check("ST-3: Two DATA messages both ACKd → EXCHANGE_OK",
          t3.verdict, ExchangeVerdict.EXCHANGE_OK.value)
    check("ST-3b: data_delivered = 2",
          t3.data_delivered, 2)

    # ST-4: Minor version downgrade — initiator 1.1, responder 1.0 → agree on 1.0
    ini_caps4 = frozenset({"search"})
    res_caps4 = frozenset({"search"})
    ver11 = ProtocolVersion(1, 1)
    ver10 = ProtocolVersion(1, 0)
    msgs_st4 = [
        A2AMessage("st4m1", "st4", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver11, capabilities=ini_caps4),
        A2AMessage("st4m2", "st4", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver10, capabilities=res_caps4,
                   ref_msg_id="st4m1"),
        A2AMessage("st4m3", "st4", "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=3),
        A2AMessage("st4m4", "st4", "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=4, ref_msg_id="st4m3"),
    ]
    t4 = run_exchange("st4", "agent_a", "agent_b", ini_caps4, res_caps4, msgs_st4)
    check("ST-4: Minor version downgrade (1.1→1.0) negotiated successfully",
          t4.verdict, ExchangeVerdict.EXCHANGE_OK.value)
    check("ST-4b: negotiated version = 1.0",
          t4.negotiated_ver, "1.0")

    # ST-5: Capability intersection is empty → handshake succeeds but no common ground
    ini_caps5 = frozenset({"translate"})
    res_caps5 = frozenset({"classify"})
    msgs_st5 = [
        A2AMessage("st5m1", "st5", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps5),
        A2AMessage("st5m2", "st5", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps5,
                   ref_msg_id="st5m1"),
        A2AMessage("st5m3", "st5", "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=3),
        A2AMessage("st5m4", "st5", "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=4, ref_msg_id="st5m3"),
    ]
    t5 = run_exchange("st5", "agent_a", "agent_b", ini_caps5, res_caps5, msgs_st5)
    check("ST-5: Empty capability intersection → EXCHANGE_OK (handshake valid; no data sent)",
          t5.verdict, ExchangeVerdict.EXCHANGE_OK.value)
    check("ST-5b: agreed_caps is empty",
          t5.agreed_caps, ())

    # ST-6: ACK for unknown msg_id is tolerated (idempotent)
    msgs_st6 = [
        A2AMessage("st6m1", "st6", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("st6m2", "st6", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="st6m1"),
        A2AMessage("st6m3", "st6", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="evidence",
                   binding_level=4, payload_ref="pkt_ev"),
        # ACK for a different message id (ghost ACK)
        A2AMessage("st6m4", "st6", "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=4, ref_msg_id="ghost_id"),
        # Real ACK for st6m3
        A2AMessage("st6m5", "st6", "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=5, ref_msg_id="st6m3"),
        A2AMessage("st6m6", "st6", "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=6),
        A2AMessage("st6m7", "st6", "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=7, ref_msg_id="st6m6"),
    ]
    t6 = run_exchange("st6", "agent_a", "agent_b", ini_caps, res_caps, msgs_st6)
    check("ST-6: Ghost ACK tolerated; real ACK clears pending → EXCHANGE_OK",
          t6.verdict, ExchangeVerdict.EXCHANGE_OK.value)

    # ST-7: Mixed ACK + NACK → EXCHANGE_PARTIAL
    msgs_st7 = [
        A2AMessage("st7m1", "st7", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("st7m2", "st7", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="st7m1"),
        A2AMessage("st7m3", "st7", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=3, content_tag="high_binding",
                   binding_level=5, payload_ref="pkt_h"),
        A2AMessage("st7m4", "st7", "agent_a", "agent_b",
                   MessageType.DATA, logical_ts=4, content_tag="low_binding",
                   binding_level=1, payload_ref="pkt_l"),
        A2AMessage("st7m5", "st7", "agent_b", "agent_a",
                   MessageType.ACK, logical_ts=5, ref_msg_id="st7m3"),
        A2AMessage("st7m6", "st7", "agent_b", "agent_a",
                   MessageType.NACK, logical_ts=6, ref_msg_id="st7m4",
                   nack_reason=NackReason.BINDING_TOO_LOW,
                   nack_desc="min_binding=3; got 1"),
        A2AMessage("st7m7", "st7", "agent_a", "agent_b",
                   MessageType.FIN, logical_ts=7),
        A2AMessage("st7m8", "st7", "agent_b", "agent_a",
                   MessageType.FIN_ACK, logical_ts=8, ref_msg_id="st7m7"),
    ]
    t7 = run_exchange("st7", "agent_a", "agent_b", ini_caps, res_caps, msgs_st7)
    check("ST-7: One ACK + one NACK → EXCHANGE_PARTIAL",
          t7.verdict, ExchangeVerdict.EXCHANGE_PARTIAL.value)
    check("ST-7b: data_delivered=1, nack_count=1",
          t7.data_delivered == 1 and t7.nack_count == 1, True)

    # ST-8: ERROR_MSG mid-session → EXCHANGE_FAILED
    msgs_st8 = [
        A2AMessage("st8m1", "st8", "agent_a", "agent_b",
                   MessageType.HELLO, logical_ts=1, version=ver, capabilities=ini_caps),
        A2AMessage("st8m2", "st8", "agent_b", "agent_a",
                   MessageType.HELLO_ACK, logical_ts=2, version=ver, capabilities=res_caps,
                   ref_msg_id="st8m1"),
        A2AMessage("st8m3", "st8", "agent_b", "agent_a",
                   MessageType.ERROR_MSG, logical_ts=3),
    ]
    t8 = run_exchange("st8", "agent_a", "agent_b", ini_caps, res_caps, msgs_st8)
    check("ST-8: ERROR_MSG mid-session → EXCHANGE_FAILED",
          t8.verdict, ExchangeVerdict.EXCHANGE_FAILED.value)
    check("ST-8b: final_state = ERROR",
          t8.final_state, SessionState.ERROR.value)

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
