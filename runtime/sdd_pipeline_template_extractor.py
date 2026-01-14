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
        pipeline_extractor_prompt_md: str = "sdd_pipeline_extractor.md",
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

        self.extractor_prompt_path = workspace_path / "templates" / pipeline_extractor_prompt_md

        logger.info(
            "Initializing PipelineTemplateExtractor | "
            f"provider={self.provider}, model={self.model_name}, temperature={self.temperature}, prompt_path={pipeline_extractor_prompt_md}"
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
        pipeline = self._parse_json(raw_output, trace_id)

        self._validate_pipeline(pipeline, trace_id)
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
    # LLM Invocation
    # ------------------------------------------------------------------

    '''
    def _call_llm(self, prompt: str, trace_id: str, timeout: float = 50.0) -> str:
        """
        Synchronous wrapper for async LLM call.
        Handles running event loop if one exists.
        """
        async def _async_call():
            # Pass model_name and temperature as kwargs, depending on your ModelManager API
            return await self.llm.generate(
                prompt=prompt,
            )

        try:
            loop = asyncio.get_running_loop()
            # Already in an event loop → schedule coroutine and block
            future = asyncio.run_coroutine_threadsafe(_async_call(), loop)
            return future.result(timeout)
        except RuntimeError:
            # No loop → safe to run normally
            return asyncio.run(asyncio.wait_for(_async_call(), timeout))
    '''

    # ------------------------------------------------------------------
    # LLM Invocation (Synchronous)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, trace_id: str, timeout: float = 0.0) -> str:
        """
        Synchronous wrapper for async LLM call.
        Handles running loop and respects timeout using Future.result().
        """
        import nest_asyncio
        import asyncio
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        async def _async_generate():
            return await self.llm.generate(
                prompt=prompt,
                persist=False,
                reflect=False
            )

        try:
            # Check if an event loop is running
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # Already in a loop → use nest_asyncio and run as Future
                nest_asyncio.apply()
                future = asyncio.run_coroutine_threadsafe(_async_generate(), loop)
                try:
                    return future.result(timeout)
                except FuturesTimeoutError:
                    raise TimeoutError(
                        f"[PipelineTemplateExtractor:{trace_id}] "
                        f"LLM generation timed out after {timeout} seconds"
                    )
        except RuntimeError:
            # No loop → safe to run normally
            return asyncio.run(_async_generate())


    # ------------------------------------------------------------------
    # Parsing & Validation
    # ------------------------------------------------------------------

    def _parse_json(self, raw: str, trace_id: str) -> Dict[str, Any]:
        logger.debug(
            f"[PipelineTemplateExtractor:{trace_id}] "
            "Parsing LLM output as JSON"
        )

        try:
            parsed = json.loads(raw)
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
                f"Invalid JSON from LLM: {e}\nRaw output:\n{raw}"
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
