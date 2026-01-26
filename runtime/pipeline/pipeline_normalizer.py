# -----------------------------------------------------------------------------
# Pipeline DSL Normalizer
#
# Canonicalizes human-authored Markdown DSL into a deterministic,
# ASCII-safe, whitespace-stable representation before parsing.
#
# This is REQUIRED for correctness.
# -----------------------------------------------------------------------------

import re
import unicodedata
from typing import Iterable, List

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")

class PipelineDSLNormalizer:
    """
    Normalizes pipeline DSL lines to a canonical form so downstream
    parsers operate deterministically.
    """

    # Unicode dash variants → ASCII hyphen
    DASH_VARIANTS = r"[–—−]"

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        # Replace all Unicode whitespace with a single ASCII space
        text = re.sub(r"\s+", " ", text, flags=re.UNICODE)
        return text.strip()

    @staticmethod
    def _normalize_dashes(text: str) -> str:
        DASH_EQUIVALENTS = {
            "\u2013": "-",  # en dash
            "\u2014": "-",  # em dash
            "\u2212": "-",  # minus sign
        }
        for k, v in DASH_EQUIVALENTS.items():
            text = text.replace(k, v)
        return text

    @staticmethod
    def normalize_pipeline_text(text: str) -> str:
        text = PipelineDSLNormalizer._normalize_unicode(text)
        text = PipelineDSLNormalizer._normalize_dashes(text)
        text = PipelineDSLNormalizer._normalize_whitespace(text)
        return text

import re
from typing import Optional, Dict

class PipelineNextStageParser:
    """
    Parses normalized 'Next Stages' DSL lines into structured routing rules.
    """

    # Matches:
    #   clarification
    #   clarification if artifact_has_spec_gaps(artifact)
    #   clarification - if artifact_has_spec_gaps(artifact)
    NEXT_STAGE_PATTERN = re.compile(
        r"""
        ^
        (?P<stage>[a-zA-Z_][a-zA-Z0-9_-]*)
        (?:                        # optional conditional
            \s*-\s*                # optional dash separator
            if\s+
            (?P<condition>.+)
        |
            \s+if\s+
            (?P<condition_alt>.+)
        )?
        $
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    @staticmethod
    def parse(line: str) -> Optional[Dict[str, str]]:
        """
        Parse a single normalized DSL line.

        Returns:
            {
                "name": <stage_name>,
                "condition": <condition or None>
            }
        """
        # Strip bullet safely
        line = re.sub(r"^\s*[-*•]\s*", "", line)
        match = PipelineNextStageParser.NEXT_STAGE_PATTERN.match(line)

        if not match:
            return None

        condition = (
            match.group("condition")
            or match.group("condition_alt")
        )

        return {
            "name": match.group("stage"),
            "condition": condition.strip() if condition else None,
        }

