from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


###############################################################################
# Consensus Result
###############################################################################

@dataclass
class ConsensusResult:

    decision: Optional[str]

    agreement: bool

    confidence: float

    votes: Dict[str, str]

    reason: Optional[str] = None


###############################################################################
# Consensus Engine
###############################################################################

class ConsensusEngine:
    """
    Evaluates agreement between multiple agents.

    Supports:
        • strict agreement
        • quorum voting
        • weighted voting
        • conflict detection
    """

    def __init__(self):

        self.agent_weights: Dict[str, float] = {}

    # -------------------------------------------------------------------------
    # Register Agent Weight
    # -------------------------------------------------------------------------

    def register_weight(self, agent: str, weight: float):

        self.agent_weights[agent] = weight

        logger.info(f"Consensus weight registered: {agent}={weight}")

    # -------------------------------------------------------------------------
    # Strict Consensus
    # -------------------------------------------------------------------------

    def strict(self, votes: Dict[str, str]) -> ConsensusResult:

        logger.info("Evaluating strict consensus")

        unique = set(votes.values())

        if len(unique) == 1:

            decision = next(iter(unique))

            return ConsensusResult(
                decision=decision,
                agreement=True,
                confidence=1.0,
                votes=votes,
            )

        return ConsensusResult(
            decision=None,
            agreement=False,
            confidence=0.0,
            votes=votes,
            reason="Agent disagreement",
        )

    # -------------------------------------------------------------------------
    # Majority Consensus
    # -------------------------------------------------------------------------

    def majority(self, votes: Dict[str, str]) -> ConsensusResult:

        logger.info("Evaluating majority consensus")

        counts: Dict[str, int] = {}

        for vote in votes.values():
            counts[vote] = counts.get(vote, 0) + 1

        winner = max(counts, key=counts.get)

        total = len(votes)

        confidence = counts[winner] / total

        return ConsensusResult(
            decision=winner,
            agreement=confidence > 0.5,
            confidence=confidence,
            votes=votes,
        )

    # -------------------------------------------------------------------------
    # Weighted Consensus
    # -------------------------------------------------------------------------

    def weighted(self, votes: Dict[str, str]) -> ConsensusResult:

        logger.info("Evaluating weighted consensus")

        scores: Dict[str, float] = {}

        total_weight = 0.0

        for agent, vote in votes.items():

            weight = self.agent_weights.get(agent, 1.0)

            total_weight += weight

            scores[vote] = scores.get(vote, 0.0) + weight

        winner = max(scores, key=scores.get)

        confidence = scores[winner] / total_weight

        return ConsensusResult(
            decision=winner,
            agreement=confidence >= 0.6,
            confidence=confidence,
            votes=votes,
        )

    # -------------------------------------------------------------------------
    # Conflict Detection
    # -------------------------------------------------------------------------

    def conflict(self, votes: Dict[str, str]) -> bool:

        return len(set(votes.values())) > 1
