############################################################
#                   AGENTIC SYSTEM ARCHITECTURE           #
#                                                          #
# This diagram illustrates how multi-domain agentic       #
# systems operate using Artifacts, Predicates, and Skills.#
# Domains provide raw data; predicates translate it into  #
# boolean/state checks; the Artifact stores state; Skills #
# operate on the Artifact; the Agent evaluates and acts.  #
############################################################
#
#          ┌────────────────────────────┐
#          │        DOMAIN LOGIC        │
#          │  (raw data, APIs, services)│
#          │                            │
#          │  - Market data             │
#          │  - Order book / trades     │
#          │  - External signals        │
#          └─────────────┬──────────────┘
#                        │
#                        │ Domain provides
#                        ▼
#          ┌──────────────────────────────────────┐
#          │       PREDICATES                     │
#          │  (boolean / yes-no checks)           │
#          │                                      │
#          │ Examples:                            │
#          │  is_market_open(ctx)                 │
#          │  is_bullish(ctx)                     │
#          │  order_is_terminal(ctx)              │
#          │  risk_metrics_within_guardrails(ctx) │
#          └─────────────┬────────────────────────┘
#                        │ Evaluated
#                        ▼
#          ┌────────────────────────────┐
#          │        ARTIFACT            │
#          │  (state + domain values)   │
#          │                            │
#          │ Fields:                    │
#          │  market_open               │
#          │  trade_permission          │
#          │  risk_index                │
#          │  key_drivers               │
#          │  order_status              │
#          └─────────────┬──────────────┘
#                        │ Used by
#                        ▼
#          ┌────────────────────────────┐
#          │          SKILLS            │
#          │ (operations / instructions │
#          │   on the Artifact)         │
#          │                            │
#          │ - Analyze Artifact state   │
#          │ - Plan next tasks          │
#          │ - Trigger HITL if needed   │
#          └─────────────┬──────────────┘
#                        │ Executes
#                        ▼
#          ┌────────────────────────────┐
#          │         AGENTIC SYSTEM     │
#          │  (domain-agnostic)         │
#          │                            │
#          │ - Receives predicates      │
#          │ - Evaluates conditions     │
#          │ - Chooses next skill/action│
#          │ - Updates artifact         │
#          └────────────────────────────┘
############################################################


import os
import uuid
import hashlib
import json
import inspect
import importlib.util
import asyncio
import yaml
from jsonschema import validate, ValidationError

from pathlib import Path
from datetime import datetime, UTC
from typing import Any, TypedDict, Dict, Optional, List, Generic, TypeVar, get_args, get_origin, Union
from typing_extensions import Literal

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, create_model
from pydantic_core import PydanticUndefined
from functools import wraps

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from runtime.artifact_factory import ArtifactSchema

from runtime.agent_manager import AgentManager
from runtime.agent_profiler import AgentOutput

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


def generate_checksum(payload: dict) -> str:
    logger.debug("Generating checksum for payload")
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    logger.debug(f"Checksum generated: {checksum}")
    return checksum


def generate_uuid() -> str:
    uid = str(uuid.uuid4())
    logger.debug(f"Generated UUID: {uid}")
    return uid


DomainType = TypeVar("DomainType", bound=BaseModel)

##################################################################
# Schema Factory
##################################################################
NODEFAULT = "<NODEFAULT>"

class SchemaFactory:

    @staticmethod
    def create_class_from_json(
        class_name: str,
        schema: Dict[str, Any],
        definitions: Dict[str, Any] | None = None
    ) -> Type:
        # Capture root definitions if not provided
        if definitions is None:
            definitions = schema.get("definitions", {})

        if schema.get("type") != "object":
            raise ValueError(
                f"Top-level schema must be an object, got {schema.get('type')}"
            )

        fields = {}
        required = set(schema.get("required", []))

        for prop_name, prop_schema in schema.get("properties", {}).items():
            field_type, default = SchemaFactory._infer_field(
                prop_schema,
                definitions,
                prop_name
            )
            fields[prop_name] = (
                field_type,
                ... if prop_name in required else default
            )

        return create_model(class_name, **fields)

    @staticmethod
    def _infer_field(
        schema: Dict[str, Any],
        definitions: Dict[str, Any],
        prop_name: str
    ):
        # --- Resolve $ref ---
        if "$ref" in schema:
            ref_key = schema["$ref"].split("/")[-1]
            actual_schema = definitions.get(ref_key)
            if not actual_schema:
                raise ValueError(f"Definition {ref_key} not found in schema")
            # Pass definitions forward recursively
            return SchemaFactory._infer_field(actual_schema, definitions, prop_name)

        schema_type = schema.get("type")

        # --- Standard types ---
        if schema_type == "string":
            if "enum" in schema:
                enum_values = list(schema["enum"])
                return Literal[tuple(enum_values)], None
            return str, None

        if schema_type == "integer":
            return int, None
        if schema_type == "number":
            return float, None
        if schema_type == "boolean":
            return bool, None

        # --- Array ---
        if schema_type == "array":
            item_schema = schema.get("items", {})
            return List[SchemaFactory._infer_field(item_schema, definitions, prop_name)[0]], None

        # --- Object ---
        if schema_type == "object":
            # Pass definitions recursively for nested objects
            return SchemaFactory.create_class_from_json(f"{prop_name.title()}Model", schema, definitions), None

        raise ValueError(f"Unsupported schema type: {schema_type}")





# --------------------------------------------------------------------------------------------------
# AgentContext: dynamic, per-turn ownership: control, data, stage, artifacts, and history.
# --------------------------------------------------------------------------------------------------

@dataclass
class AgentContext:
        agent_name: str        # identity of the agent in this turn
        stage: str             # current stage
        # ------------------------------------------------------------------
        # Control Plane (required, immutable intent)
        # ------------------------------------------------------------------
        control_raw: ArtifactSchema = None # artifact.md / plan / contract

        # ------------------------------------------------------------------
        # Data Plane (append-only, domain governed)
        # ------------------------------------------------------------------
        data_raw:  DataEnvelope[DomainType]  = None # Field(default_factory=DataEnvelope)

        # ------------------------------------------------------------------
        # Tool Plane (append-only execution records)
        # ------------------------------------------------------------------
        tool_raw: List[ToolEnvelope[DomainType]] = Field(default_factory=list)
        # ------------------------------------------------------------------
        timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
        result_summary: str | None = None          # optional result / status

##################################################################
# DATA ENVELOPE
##################################################################


class DataEnvelope(BaseModel, Generic[DomainType]):
    agent: str
    type: str
    version: str
    producer: str
    stage: str
    created_at: datetime
    payload: DomainType
    checksum: Optional[str]
    references: List[str] = []

class DataBridge:
    def __init__(self, agent_md_content: str):
        self.raw_schema = self._extract_json_from_md(agent_md_content)
        self.validator_class = SchemaFactory.create_class_from_json("AgentContract", self.raw_schema)

    def validate_and_save(self, agent_response_string: str, db_session):
        # 1. Convert string to JSON
        data_dict = json.loads(agent_response_string)
        
        # 2. Automatically validate against the Dynamic Class
        validated_data = self.validator_class(**data_dict)
        
        # 3. Map to Database (Generic Upsert)
        # This part interacts with your SQLAlchemy/SQLModel
        return db_session.merge(validated_data.dict())

class DataAdapter(Generic[DomainType]):
    def __init__(self, 
                agent_name: str, 
                schema_class: type[DomainType]):
        self.agent_name = agent_name
        self.payload_schema = schema_class
        logger.info(f"DataAdapter initialized for agent '{agent_name}'")

    def create_envelope(
        self,
        payload:  Union[DomainType, dict],
        producer: str,
        stage: str
    ) -> DataEnvelope[DomainType]:
        logger.info(
            f"Creating DataEnvelope | domain={self.agent_name} producer={producer} stage={stage}"
        )
        logger.debug(f"Validating payload against {self.payload_schema}")

        # 1. Validate + materialize typed payload
        #    If payload is already a Pydantic model, use it directly
        if isinstance(payload, self.payload_schema):
            payload_model = payload
        else:
            payload_model: DomainType = self.payload_schema(**payload)

        checksum = generate_checksum(payload_model.model_dump())

        # 2. Create typed envelope
        envelope = DataEnvelope[DomainType](
            agent=self.agent_name,
            type=self.payload_schema.__name__.lower(),
            version="1.0",
            producer=producer,
            stage=stage,
            created_at=datetime.now(UTC),
            payload=payload_model,   
            checksum=checksum
        )

        logger.info(
            f"DataEnvelope created | domain={envelope.agent} checksum={checksum}"
        )
        return envelope

class DataManager:
    def __init__(self, agent_manager: AgentManager):

        self.agent_manager = agent_manager

        self.domain_map: Dict[str, DataAdapter] = {}
        logger.info(f"DataManager initialized")

    def scan_and_register_schema(self):
        logger.info("Scanning schema domains for registered agents")

        agents = self.agent_manager.list_agents()

        for agent_name in agents:
            logger.info(f"Agent name: {agent_name}")
            profile = self.agent_manager.get_agent_profile(agent_name)
            logger.info(f"Agent Profile: name={profile.name}, role={profile.role}")
            logger.info(f"Agent Input Schema: {profile.input_schema}")

            schema = {
                "type": "object",
                "required": ["input", "output"],
                "properties": {
                    "input": profile.input_schema,
                    "output": profile.output_schema,
                },
                "definitions": {
                    **profile.input_schema.get("definitions", {}),
                    **profile.output_schema.get("definitions", {}),
                },
                "additionalProperties": False,
            }

            definitions = profile.input_schema.get("definitions", {})  # <-- extract definitions here

            logger.info(f"Definition exists: {definitions}")

            try:

                # 1. Usage in your Pipeline
                DynamicAgentSchema: Type[DomainType] = SchemaFactory.create_class_from_json(f"{agent_name}Schema", schema, schema.get("definitions, {})"))

                logger.info(f"Dynamic Agent Model: {DynamicAgentSchema}")

                if not DynamicAgentSchema:
                    logger.warning(f"Schema class '{DynamicAgentSchema}'")
                    continue

                self.domain_map[agent_name] = DataAdapter(
                    agent_name=agent_name,
                    schema_class=DynamicAgentSchema # This is a schema class [type(DomainType)]
                )

                logger.info(f"Successfully registered data schema for '{agent_name}'")

            except Exception as e:
                logger.exception(f"Failed to load data for agent '{agent_name}': {e}")


    def get_default_for_type(self, field_type: Any) -> Any:
        origin = get_origin(field_type)

        # 1. Lists
        if origin is list:
            return []

        # 2. Nested Pydantic models (THIS fixes input/output)
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return self.instantiate_with_defaults(field_type)

        # 3. Literals
        if origin is Literal:
            args = getattr(field_type, "__args__", [])
            return args[0] if args else NODEFAULT

        # 4. Primitives
        if field_type is str:
            return NODEFAULT
        if field_type is int:
            return 0
        if field_type is float:
            return 0.0
        if field_type is bool:
            return False
        if field_type is dict:
            return {}

        # 5. Fallback
        return NODEFAULT


    def get_adapter(self, agent_name: str) -> DataAdapter:
        adapter = self.domain_map.get(agent_name)
        if not adapter:
            logger.error(f"DataAdapter not found for agent '{agent_name}'")
        return adapter

    def get_initial_envelope(self, agent_name: str) -> DataEnvelope:
        """
        Leverages the registered DataAdapter to create a type-safe starting envelope.
        """
        # 1. Retrieve the adapter we found during scan_and_register
        adapter = self.domain_map.get(agent_name)

        logger.info(f"Data Adapter for the given agent '{agent_name}': {adapter}")

        if not adapter:
            raise ValueError(f"Critical Error: Data agent '{agent_name}' is not registered.")

        # 2. Use the adapter to create the envelope.
        # Passing an empty dict {} triggers the Pydantic schema's default values.
        # Producer is 'system' because this is the mission's 'Genesis' block.
        instantiated_schema = self.instantiate_with_defaults(adapter.payload_schema)
        initial_payload_dict = instantiated_schema.model_dump() # converts into a dict

        logger.info(
            f"Instantiated default payload | "
            f"type={type(instantiated_schema)} "
            f"values={initial_payload_dict}"
        )

        try:
            initial_envelope = adapter.create_envelope(
                payload=initial_payload_dict, 
                producer="system/genesis", 
                stage="init"
            )
            return initial_envelope
        except ValueError as e:
            logger.error(f"Critical Error: Data domain '{agent_name}' schema, {e}")


    def instantiate_with_defaults(self, model_class: Type[DomainType]) -> DomainType:
        payload = {}

        for name, field_info in model_class.model_fields.items():
            field_type = field_info.annotation

            # REQUIRED fields must NEVER be None
            payload[name] = self.get_default_for_type(field_type)

        return model_class(**payload)





##################################################################
# TOOL ENVELOPE
##################################################################

class ToolCall(TypedDict):
    agent: str
    tool: str
    args: Dict[str, Any]
    result: Any

class ToolEnvelope(BaseModel, Generic[DomainType]):
    id: str
    tool_name: str
    tool_version: Optional[str]
    agent_role: str
    stage: str
    intent: str 
    input: Dict[str, Any] 
    output: Optional[Dict[AgentOutput, Any]] = None
    error: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None
    success: bool = False


class ToolAdapter:
    def __init__(self, name: str, description: str, schema: dict, tool_file: Path, mcp_caller: callable):
        self.name = name
        self.description = description
        self.parameters = schema  # The MCP inputSchema (e.g., ticker, qty)
        self.tool_file = tool_file
        self.mcp_caller = mcp_caller # The logic to run the MCP command
        
        logger.info(f"ToolAdapter initialized | tool={name}")

    def get_schema(self) -> dict:
        """
        Returns the OpenAI-compatible schema so the LLM knows HOW to call the tool.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    async def execute(self, agent_role: str, stage: str, intent: str, **kwargs) -> ToolEnvelope:
        logger.info(f"Executing tool '{self.name}' | agent={agent_role} stage={stage}")
        start_time = datetime.now(UTC).isoformat()

        try:
            # 1. Call the tool
            raw_result = await self.mcp_caller(kwargs) # Note: we pass kwargs here
            
            # 2. Extract the data (Cleaning for the LLM)
            # We look for 'text' blocks first, then 'data' or 'structured_content'
            if hasattr(raw_result, 'content'):
                output = "\n".join([c.text for c in raw_result.content if hasattr(c, 'text')])
            else:
                output = str(raw_result)

            success = True
            error = None
        except Exception as e:
            output = None
            success = False
            error = str(e)
            logger.exception(f"Tool '{self.name}' execution failed: {e}")

        return ToolEnvelope(
            id=generate_uuid(),
            tool_name=self.name,
            agent_role=agent_role,
            stage=stage,
            intent=intent or self.description,
            input=kwargs,
            output=output, # Now this is a clean string/object
            error=error,
            started_at=start_time,
            completed_at=datetime.now(UTC).isoformat(),
            success=success
        )


class ToolManager:
    def __init__(self, agent_manager: AgentManager):

        self.agent_manager = agent_manager

        self.tool_map: Dict[str, ToolAdapter] = {}
        logger.info(f"ToolManager initialized")

        # This keeps the connections alive
        self._session_cache: Dict[Path, ClientSession] = {}
        self._exit_stack: Dict[Path, AsyncExitStack] = {}

    async def scan_and_register_tools(self, workspace_path: Path) -> None:
        self.tools_dir = workspace_path / "tools" / "mcp"

        logger.info(f"Scanning for agents tools {self.tools_dir}")

        if not self.tools_dir.exists() or not self.tools_dir.is_dir():
            raise ValueError(f"Invalid agent base path: {self.tools_dir}")

        for tool_file in self.tools_dir.iterdir():
            if tool_file.suffix != ".py": # Avoid temp files or __pycache__
                continue

            try:
                logger.info(f"Reading tools from {tool_file}")
                # Registry is the list of dicts we just got working
                registry = await self.extract_tools_via_protocol(tool_file)

                for tool_data in registry:
                    # Create the adapter
                    adapter = ToolAdapter(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        schema=tool_data["arguments"],
                        tool_file=tool_file,
                        mcp_caller=self.call_mcp_tool
                    )
                    
                    # Register in the map
                    self.tool_map[adapter.name] = adapter
                    
                logger.info(f"Successfully registered {len(registry)} tools from {tool_file.name}")

            except Exception as e:
                logger.error(f"Failed to register tools from {tool_file.name}: {e}", exc_info=True)

        logger.info(f"Agent scan complete. Total registered tools: {len(self.tool_map)}")

    async def extract_tools_via_protocol(self, tool_file: Path) -> list[dict]:
        import sys
        import subprocess

        # Using sys.executable ensures we use the exact same Python environment
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(tool_file.absolute())],
            env=None
        )

        registry = []
        try:
            # Short timeout - it should be near-instant
            async with asyncio.timeout(5):
                # stderr=subprocess.DEVNULL is the default; 
                # changing to None can sometimes help see output in the main console
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        response = await session.list_tools()
                        for tool in response.tools:
                            registry.append({
                                "name": tool.name,
                                "description": tool.description or "",
                                "arguments": tool.inputSchema # Capture this for later!
                            })
        except Exception as e:
            # LOG THE CRASH DETAIL
            logger.error(f"Handshake failed for {tool_file.name}.")
            logger.error(f"Error Detail: {repr(e)}")
            
            # PRO-TIP: Try to run it once manually via subprocess to catch the traceback
            result = subprocess.run(
                [sys.executable, str(tool_file)], 
                capture_output=True, 
                text=True, 
                timeout=2
            )
            if result.stderr:
                logger.error(f"Captured Traceback from {tool_file.name}:\n{result.stderr}")
            
        return registry

    async def call_mcp_tool(self, tool_file: Path, tool_name: str, args: dict):
        """
        The bridge logic. Now with session persistence to keep 
        the 'Agnostic OS' snappy.
        """
        # 1. Check if we already have a live session for this file
        if tool_file in self._session_cache:
            session = self._session_cache[tool_file]
            result = await session.call_tool(tool_name, arguments=args)
            return result.content

        # 2. If not, spin it up (Your original logic)
        logger.info(f"Starting persistent session for {tool_file.name}")
        
        # We use AsyncExitStack to keep the 'async with' contexts alive
        stack = AsyncExitStack()
        self._exit_stack[tool_file] = stack

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(tool_file.absolute())],
            env=None
        )

        # Entering the contexts
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))
        
        await session.initialize()
        self._session_cache[tool_file] = session

        # 3. Call the tool
        result = await session.call_tool(tool_name, arguments=args)
        return result.content

    async def shutdown(self):
        """Cleanly close all MCP processes at engine stop."""
        for path, stack in self._exit_stack.items():
            logger.info(f"Closing MCP server: {path.name}")
            await stack.aclose()
        self._session_cache.clear()
        self._exit_stack.clear()

    def get_llm_tool_definitions(self):
        """
        Converts the internal MCP registry into standard LLM tool format.
        """
        llm_tools = []
        for tool in self.all_discovered_tools: # your registry list
            llm_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["arguments"] # Rename 'arguments' to 'parameters'
                }
            })
        return llm_tools

    def list_available_tools(self):
        keys = self.tool_map.keys()
        result = ", ".join(keys)
        return result


    def auto_envelope_wrapper(func, agent_role: str, stage: str):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(
                f"Auto-enveloped tool execution | tool={func.__name__} stage={stage}"
            )

            envelope = ToolEnvelope(
                id=str(uuid.uuid4()),
                tool_name=func.__name__,
                agent_role=agent_role,
                stage=stage,
                intent=func.__doc__ or "Executing atomic tool",
                input=kwargs,
                started_at=datetime.now(UTC).isoformat()
            )

            try:
                result = await func(*args, **kwargs)
                envelope.output = result
                envelope.success = True
                logger.info(f"Tool '{func.__name__}' completed successfully")

            except Exception as e:
                envelope.error = str(e)
                envelope.success = False
                logger.exception(f"Tool '{func.__name__}' failed: {e}")

            finally:
                envelope.completed_at = datetime.now(UTC).isoformat()

            return envelope

        return wrapper

    def get_initial_envelope(self, agent_name: str) -> ToolEnvelope:
        """
        Leverages the registered DataAdapter to create a type-safe starting envelope.
        """
        # 1. Retrieve the adapter we found during scan_and_register
        adapter = self.tool_map.get(agent_name)


##################################################################
# SYSTEM CONTEXT
##################################################################

class SystemContext:
    def __init__(self, template_repo: str, workspace_path: str, agent_manager: AgentManager):
        # Only setup synchronous variables here
        self.template_repo = Path(template_repo)
        self.workspace_path = Path(workspace_path)
        self.agent_manager = agent_manager
        self.data_manager = DataManager(agent_manager)
        self.tool_manager = ToolManager(agent_manager)

    @classmethod
    async def create(cls, template_repo: str, workspace_path: str, agent_manager: AgentManager):
        """
        The proper way to instantiate SystemContext asynchronously.
        """
        logger.info("Initializing SystemContext via Async Factory")
        instance = cls(template_repo, workspace_path, agent_manager)
        
        # 1. Sync registration
        instance.data_manager.scan_and_register_schema()
        
        # 2. Async registration (now we can safely await)
        await instance.tool_manager.scan_and_register_tools(instance.workspace_path)
        
        logger.info("SystemContext initialization complete")
        return instance

    def get_runtime_tools(self):
        logger.debug("Collecting runtime tool schemas for LLM binding")
        schemas = [adapter.get_schema() for adapter in self.tool_manager.tool_map.values()]
        logger.info(f"Exposed {len(schemas)} tools to runtime")
        return schemas

