import json
import uuid
from typing import Dict, Any
from pathlib import Path

import asyncio
import nest_asyncio
from concurrent.futures import TimeoutError as FuturesTimeoutError

from llm.model_manager import ModelManager

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class PipelineTemplateExtractor:
    """
    Enterprise-grade extractor that converts Markdown pipeline templates
    into a machine-readable pipeline dictionary.

    Responsibilities:
    - Parse human-authored pipeline_template.md
    - Normalize stage definitions
    - Emit strict JSON-compatible Dict
    - Validate required schema fields
    """

    REQUIRED_STAGE_FIELDS = {
        "name",
        "description",
    }

    OPTIONAL_STAGE_FIELDS = {
        "allowed_agents",
        "exit_condition",
        "next_stages",
        "terminal",
    }

    def __init__(
        self,
        llm_client,
        workspace_path : str = None,
        pipeline_extractor_prompt_md: str = "pipeline_extractor.md",
    ):
        """
        llm_client must expose:
            generate(prompt: str, model: str, temperature: float) -> str
        """

        self.llm = llm_client
        self.model_info = self.llm.get_model_info()
        self.provider = self.model_info.get('provider')
        self.model_name = self.model_info.get('model_name')
        self.temperature = self.model_info.get('temperature')
        self.max_tokens = self.model_info.get('max_tokens')

        self.extractor_prompt_path = workspace_path / "templates" / pipeline_extractor_prompt_md

        logger.info(
            "Initializing PipelineTemplateExtractor | "
            f"provider={self.provider}, model={self.model_name}, temperature={self.temperature}, "
            f"max_tokens={self.max_tokens}, prompt_path={pipeline_extractor_prompt_md}"
        )

        logger.info(
            "Initializing PipelineTemplateExtractor | "
            f"workspace_path={workspace_path}, extractor_prompt_path={self.extractor_prompt_path}"
        )

        if not self.extractor_prompt_path.exists():
            logger.error(
                "Pipeline extractor prompt file not found | "
                f"path={self.extractor_prompt_path}"
            )
            raise FileNotFoundError(
                f"Pipeline extractor prompt not found: {self.extractor_prompt_path}"
            )

        logger.info(
            "PipelineTemplateExtractor initialized successfully | "
            f"prompt_loaded={self.extractor_prompt_path.resolve()}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, markdown: str) -> Dict[str, Any]:
        """
        Main entry point.
        Returns:
            {
              "stages": [ {stage_def}, ... ]
            }
        """
        trace_id = str(uuid.uuid4())

        logger.info(
            f"[PipelineTemplateExtractor:{trace_id}] "
            "Starting pipeline extraction"
        )

        logger.debug(
            f"[PipelineTemplateExtractor:{trace_id}] "
            f"Markdown length={len(markdown)} characters"
        )

        prompt = self._build_prompt(markdown, trace_id)

        raw_output = self._call_llm(prompt, trace_id)

        logger.info( "Raw Response received ... Now Parsing Json Output ... ")

        pipeline = self._parse_json(raw_output, trace_id)

        logger.info( "Validating Pipeline based on JSON schema  ... ")

        self._validate_pipeline(pipeline, trace_id)

        logger.info( "Normalizing Pipeline ... ")

        self._normalize_pipeline(pipeline, trace_id)

        logger.info(
            f"[PipelineTemplateExtractor:{trace_id}] "
            f"Extraction complete | stages={len(pipeline.get('stages', []))}"
        )

        return pipeline

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------

    def _build_prompt(self, markdown: str, trace_id: str) -> str:
        logger.debug(
            f"[PipelineTemplateExtractor:{trace_id}] "
            f"Building prompt from template: {self.extractor_prompt_path.name}"
        )

        template = self.extractor_prompt_path.read_text(encoding="utf-8")

        if "{{PIPELINE_MARKDOWN}}" not in template:
            logger.error(
                f"[PipelineTemplateExtractor:{trace_id}] "
                "Prompt template missing required {{PIPELINE_MARKDOWN}} placeholder"
            )
            raise ValueError(
                "pipeline_extractor_prompt.md must contain "
                "{{PIPELINE_MARKDOWN}} placeholder"
            )

        prompt = template.replace("{{PIPELINE_MARKDOWN}}", markdown)

        logger.debug(
            f"[PipelineTemplateExtractor:{trace_id}] "
            f"Prompt constructed | prompt_length={len(prompt)} characters"
        )

        return prompt


    # ------------------------------------------------------------------
    # LLM Invocation (Synchronous)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, trace_id: str) -> str:
        """
        Synchronous bridge for async LLM call.
        Always returns a STRING.
        """

        import asyncio
        import threading

        async def _async_generate():
            result = await self.llm.generate(
                prompt=prompt,
                persist=False,
                reflect=False
            )

            # ✅ Normalize LangChain output
            if hasattr(result, "content"):
                return result.content

            return result

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop
            return asyncio.run(_async_generate())

        # Running loop → offload to thread
        result_container = {}
        error_container = {}

        def _thread_runner():
            try:
                result_container["value"] = asyncio.run(_async_generate())
            except Exception as e:
                error_container["error"] = e

        t = threading.Thread(target=_thread_runner, daemon=True)
        t.start()
        t.join()

        if "error" in error_container:
            raise RuntimeError(
                f"[PipelineTemplateExtractor:{trace_id}] LLM invocation failed"
            ) from error_container["error"]

        return result_container["value"]




    # ------------------------------------------------------------------
    # Parsing & Validation
    # ------------------------------------------------------------------

    def _parse_json(self, raw: str, trace_id: str) -> Dict[str, Any]:
        logger.debug(
            f"[PipelineTemplateExtractor:{trace_id}] "
            "Parsing LLM output as JSON"
        )

        output = raw
        if raw.startswith("```json"):
            output = raw[len("```json"):].lstrip()

        logger.info("Do it now:")
        logger.info(output)

        try:
            parsed = json.loads(output)
            logger.info(
                f"[PipelineTemplateExtractor:{trace_id}] "
                "JSON parsing successful"
            )
            return parsed

        except json.JSONDecodeError as e:
            logger.error(
                f"[PipelineTemplateExtractor:{trace_id}] "
                "Invalid JSON returned from LLM"
            )
            raise ValueError(
                f"[PipelineTemplateExtractor:{trace_id}] "
                f"Invalid JSON from LLM: {e}\nRaw output:\n{output}"
            )

    def _validate_pipeline(self, pipeline: Dict[str, Any], trace_id: str):
        logger.info(
            f"[PipelineTemplateExtractor:{trace_id}] "
            "Validating extracted pipeline schema"
        )

        if "stages" not in pipeline or not isinstance(pipeline["stages"], list):
            logger.error(
                f"[PipelineTemplateExtractor:{trace_id}] "
                "Pipeline missing required 'stages' list"
            )
            raise ValueError(
                f"[PipelineTemplateExtractor:{trace_id}] "
                "Pipeline must contain a 'stages' list"
            )

        for idx, stage in enumerate(pipeline["stages"]):
            missing = self.REQUIRED_STAGE_FIELDS - stage.keys()
            if missing:
                logger.error(
                    f"[PipelineTemplateExtractor:{trace_id}] "
                    f"Stage[{idx}] missing required fields: {missing}"
                )
                raise ValueError(
                    f"[PipelineTemplateExtractor:{trace_id}] "
                    f"Stage[{idx}] missing required fields: {missing}"
                )

            if not isinstance(stage.get("name"), str):
                logger.error(
                    f"[PipelineTemplateExtractor:{trace_id}] "
                    f"Stage[{idx}] 'name' must be a string"
                )
                raise ValueError(
                    f"[PipelineTemplateExtractor:{trace_id}] "
                    f"Stage[{idx}] 'name' must be a string"
                )

        logger.info(
            f"[PipelineTemplateExtractor:{trace_id}] "
            f"Pipeline validation successful | stages={len(pipeline['stages'])}"
        )

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize_pipeline(self, pipeline: Dict[str, Any], trace_id: str):
        logger.info(
            f"[PipelineTemplateExtractor:{trace_id}] "
            "Normalizing pipeline structure"
        )

        for idx, stage in enumerate(pipeline["stages"]):
            stage.setdefault("allowed_agents", [])
            stage.setdefault("exit_condition", None)
            stage.setdefault("next_stages", [])
            stage.setdefault("terminal", False)

            normalized_next = []
            for ns in stage["next_stages"]:
                if isinstance(ns, str):
                    normalized_next.append({"name": ns, "condition": None})
                else:
                    normalized_next.append({
                        "name": ns.get("name"),
                        "condition": ns.get("condition"),
                    })
            stage["next_stages"] = normalized_next

            logger.debug(
                f"[PipelineTemplateExtractor:{trace_id}] "
                f"Stage[{idx}] normalized | name={stage.get('name')}"
            )

        logger.info(
            f"[PipelineTemplateExtractor:{trace_id}] "
            "Pipeline normalization complete"
        )
