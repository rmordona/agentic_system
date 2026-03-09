from core.paths import REFINER_TEMPLATE, load_template

import json
from typing import Dict, Any, Optional

from runtime.engine.state.state_schema import StateSchema
from llm.model_manager import ModelManager
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")

# -----------------------------------------------------------------------------
# AgentIntentRefiner
# -----------------------------------------------------------------------------
# Control-plane supervisor responsible for refining user intent into a structured,
# domain-agnostic format suitable for multi-agent orchestration.
#
# Responsibilities:
# -----------------
# 1. Determine user input to refine (human feedback > original_intent)
# 2. Produce a normalized_intent string for general reference
# 3. Produce a structured_intent JSON with keys:
#      - task: high-level action
#      - raw_intent: original text
#      - workspace: target capability/domain assistant
#      - entities: domain-specific key/value pairs
#      - parameters: domain-specific optional metadata
#      - metrics: optional quantitative indicators
#      - priority: optional, e.g., "high", "normal"
# 4. Detect missing required entities for downstream governance
# 5. Return updates for the StateSchema
# -----------------------------------------------------------------------------

class AgentIntentRefiner:
    def __init__(self, llm: ModelManager):
        self.llm = llm

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentIntentRefiner is being called                             ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"State at entry: {state}")

        if state.human_response:
            logger.info("I got a new response.")

        try:
            # -----------------------------------------------------------------
            # 1. Determine input to refine
            # -----------------------------------------------------------------
            user_input: Optional[str] = state.human_response or state.original_intent
            if not user_input:
                logger.warning("No user input found. Skipping intent refinement.")
                return {}

            # -----------------------------------------------------------------
            # 2. Skip if structured_intent already exists
            # -----------------------------------------------------------------
            if state.structured_intent:
                logger.info("Structured intent already exists. Skipping refinement.")
                return {}

            # -----------------------------------------------------------------
            # 3. Build LLM prompt for domain-agnostic structured intent
            # -----------------------------------------------------------------
            system_prompt = ModelManager.hydrate( load_template(REFINER_TEMPLATE), {
                "user_input" : user_input
            })

            # -----------------------------------------------------------------
            # 4. Call LLM to refine intent
            # -----------------------------------------------------------------
            logger.info(f"Calling LLM to refine user intent: {user_input}")
            response = await self.llm.ainvoke(system_prompt)
            raw_output = getattr(response, "content", str(response))

            logger.info(f"Raw LLM output: {raw_output}")

            # -----------------------------------------------------------------
            # 5. Parse JSON safely
            # -----------------------------------------------------------------
            structured_intent = self._safe_json_parse(raw_output)

            # -----------------------------------------------------------------
            # 6. Fallback if parsing fails
            # -----------------------------------------------------------------
            if structured_intent is None:
                logger.warning("Intent JSON parsing failed. Using fallback.")
                structured_intent = {
                    "intent_type" : "unknown",
                    "task": "unknown",
                    "raw_intent": user_input,
                    "workspace": "general_assistant",
                    "entities": {},
                    "parameters": {},
                    "metrics": [],
                    "priority": "normal"
                }

            # -----------------------------------------------------------------
            # 7. Detect missing required entities
            # -----------------------------------------------------------------
            missing_entities = []
            entities = structured_intent.get("entities", {})
            if not entities:
                missing_entities.append("entities")

            clarification_needed = bool(missing_entities)
            clarification_question = (
                f"Could you provide the missing information for: {', '.join(missing_entities)}?"
                if missing_entities else None
            )

            logger.info(f"Normalized intent: {user_input.strip()}")
            logger.info(f"Structured intent: {structured_intent}")

            # -----------------------------------------------------------------
            # 8. Return updates to state
            # -----------------------------------------------------------------
            intent_type = structured_intent.get("intent_type")
            reason = structured_intent.get("reason")
            message = structured_intent.get("response")

            if intent_type == "unknown":
                return {
                    "human_response": None,
                    "hitl_required": True,
                    "hitl_type": "intent_clarification",
                    "hitl_prompt": "I couldn't understand your request. Could you please rephrase what you'd like to do?",
                    "hitl_resume_node": "refiner"
                }
            elif intent_type == "conversation":
                return {
                    "human_response": None,
                    "hitl_required": True,
                    "hitl_type": "intent_conversation",
                    "hitl_prompt": message,
                    "hitl_resume_node": "refiner"
                }

            return {
                "human_response": None,
                "hitl_required": False,
                "normalized_intent": user_input.strip(),
                "structured_intent": structured_intent,
                "clarification_needed": clarification_needed,
                "clarification_question": clarification_question
            }

        except Exception as e:
            logger.exception("AgentIntentRefiner failed")
            return {
                "human_response": None,
                "hitl_required": False,
                "structured_intent": None,
                "clarification_needed": False,
                "clarification_question": None,
                "refiner_error": str(e)
            }

    # -------------------------------------------------------------------------
    # Safe JSON parser from raw LLM output
    # -------------------------------------------------------------------------
    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        try:
            if not isinstance(text, str):
                text = str(text)

            text = text.strip()

            # remove markdown code blocks
            if text.startswith("```"):
                text = text.replace("```json", "").replace("```", "").strip()

            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1 or end < start:
                return None

            json_str = text[start:end+1]

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Attempted JSON string: {text}")
            return None

    def route_after_refining(self, state: StateSchema):
        if state.hitl_required:
            return "Route_To_HITL"
        if state.session_is_new or state.context_switch:
            return "Route_To_Classifier"
        return "Route_To_Governance"  # skip classifier mid-session