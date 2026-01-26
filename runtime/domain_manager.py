import os
import uuid
import hashlib
import json
import inspect
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field, create_model
from functools import wraps

from runtime.agent_manager import AgentManager
from runtime.agent_profiler import AgentProfile

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


##################################################################
# DATA ENVELOPE
##################################################################
DomainType = TypeVar("DomainType", bound=BaseModel)

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

class DataAdapter(Generic[DomainType]):
    def __init__(self, agent_name: str, schema_class: type[DomainType]):
        self.agent_name = agent_name
        self.payload_schema = schema_class
        logger.info(f"DataAdapter initialized for domain '{agent_name}'")

    def create_envelope(
        self,
        payload:  Union[DomainType, dict],
        producer: str,
        stage: str
    ) -> DataEnvelope[DomainType]:
        logger.info(
            f"Creating DataEnvelope | domain={self.agent_name} producer={producer} stage={stage}"
        )
        logger.debug(f"Validating payload against {self.payload_schema.__name__}")

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
            created_at=datetime.utcnow(),
            payload=payload_model,   
            checksum=checksum
        )

        logger.info(
            f"DataEnvelope created | domain={envelope.domain} checksum={checksum}"
        )
        return envelope

class SchemaFactory:
    @staticmethod
    def create_class_from_json(class_name: str, json_data: Dict[str, Any]) -> Type[BaseModel]:
        """
        Dynamically creates a Pydantic model class from a dictionary.
        Infer types from the values provided.
        """
        fields = {}
        for key, value in json_data.items():
            # Infer the type (e.g., int, str, list)
            field_type = type(value)
            # If the value is a dict, recursively create a sub-model
            if isinstance(value, dict):
                sub_model = SchemaFactory.create_class_from_json(f"{key}Model", value)
                fields[key] = (sub_model, ...)
            else:
                fields[key] = (field_type, ...)

        return create_model(class_name, **fields)


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

class DataManager:
    def __init__(self, agent_manager: AgentManager):

        self.agent_manager = agent_manager

        self.domain_map: Dict[str, DataAdapter] = {}
        logger.info(f"DataManager initialized")



    def scan_and_register(self):
        logger.info("Scanning data domains for registered agents")

        agents = self.agent_manager.list_agents()

        for agent_name in agents:
            logger.info(f"Agent name: {agent_name}")
            profile = self.agent_manager.get_agent_profile(agent_name)
            data_json_schema = json.loads(profile.schema)
            logger.info(f"Agent Json Schema: {data_json_schema}")

            try:

                # Usage in your Pipeline
                DynamicModel = SchemaFactory.create_class_from_json("TriageOutput", data_json_schema)

                # Now you can validate any future output from that agent:
                validated_instance = DynamicModel(**data_json_schema)

                logger.info(f"Dynamic Model: {DynamicModel}")

                if not DynamicModel:
                    logger.warning(f"Schema class '{DynamicModel}'")
                    continue

                self.domain_map[agent_name] = DataAdapter(
                    agent_name=agent_name,
                    schema_class=DynamicModel
                )

                logger.info(f"Successfully registered data domain '{agent_name}'")

            except Exception as e:
                logger.exception(f"Failed to load data for agent '{agent_name}': {e}")


    def get_adapter(self, agent_name: str) -> DataAdapter:
        adapter = self.domain_map.get(agent_name)
        if not adapter:
            logger.error(f"DataAdapter not found for domain '{agent_name}'")
        return adapter

    def get_initial_envelope(self, agent_name: str) -> DataEnvelope:
        """
        Leverages the registered DataAdapter to create a type-safe starting envelope.
        """
        # 1. Retrieve the adapter we found during scan_and_register
        adapter = self.domain_map.get(self.agent_name)

        logger.info(f"Data Adapter for the given domain '{agent_name}': {adapter}")

        if not adapter:
            raise ValueError(f"Critical Error: Data domain '{agent_name}' is not registered.")

        # 2. Use the adapter to create the envelope.
        # Passing an empty dict {} triggers the Pydantic schema's default values.
        # Producer is 'system' because this is the mission's 'Genesis' block.
        initial_payload = adapter.payload_schema()
        initial_payload_dict = initial_payload.model_dump() # converts into a dict

        logger.info(
            f"Instantiated default payload | "
            f"type={type(initial_payload)} "
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


##################################################################
# TOOL ENVELOPE
##################################################################

class ToolEnvelope(BaseModel, Generic[DomainType]):
    id: str
    tool_name: str
    tool_version: Optional[str]
    agent_role: str
    stage: str
    intent: str 
    input: Dict[str, Any] 
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    success: bool = False


class ToolAdapter:
    def __init__(self, name: str, func: callable):
        self.name = name
        self.func = func
        logger.info(f"ToolAdapter initialized | tool={name}")

    async def execute(self, agent_role: str, stage: str, **kwargs) -> ToolEnvelope:
        logger.info(
            f"Executing tool '{self.name}' | agent={agent_role} stage={stage}"
        )
        logger.debug(f"Tool input: {kwargs}")

        start_time = datetime.utcnow().isoformat()

        try:
            output = await self.func(**kwargs)
            success = True
            error = None
            logger.info(f"Tool '{self.name}' executed successfully")

        except Exception as e:
            output = None
            success = False
            error = str(e)
            logger.exception(f"Tool '{self.name}' execution failed: {e}")

        envelope = ToolEnvelope(
            id=generate_uuid(),
            tool_name=self.name,
            agent_role=agent_role,
            stage=stage,
            intent=self.func.__doc__ or "Agent tool execution",
            input=kwargs,
            output=output,
            error=error,
            started_at=start_time,
            completed_at=datetime.utcnow().isoformat(),
            success=success
        )

        logger.info(
            f"ToolEnvelope created | tool={self.name} success={success} id={envelope.id}"
        )
        return envelope

    def get_schema(self) -> dict:
        logger.debug(f"Generating tool schema for '{self.name}'")
        schema = ToolEnvelope.model_json_schema()
        schema["title"] = self.name
        schema["description"] = self.func.__doc__ or "Atomic tool execution"
        return schema


class ToolManager:
    def __init__(self, tools_repo_path: str):
        self.repo_path = Path(tools_repo_path)
        self.tool_map: Dict[str, ToolAdapter] = {}
        logger.info(f"ToolManager initialized | repo_path={self.repo_path}")

    def scan_and_register(self):
        logger.info("Scanning tools for registration")

        for file_path in self.repo_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue

            logger.info(f"Loading tool module: {file_path.name}")

            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name, func in inspect.getmembers(module, inspect.isfunction):
                if hasattr(func, "_is_mcp_tool"):
                    self.tool_map[name] = ToolAdapter(name=name, func=func)
                    logger.info(f"Registered tool '{name}'")

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
                started_at=datetime.utcnow().isoformat()
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
                envelope.completed_at = datetime.utcnow().isoformat()

            return envelope

        return wrapper

##################################################################
# SYSTEM CONTEXT
##################################################################
class SystemContext:
    def __init__(self, domain_repo: str, agent_manager: AgentManager):
        logger.info("Initializing SystemContext")

        self.template_repo = domain_repo / "templates"
        self.data_repo     = domain_repo / "data"
        self.tools_repo    = domain_repo / "tools"      

        self.data_manager = DataManager(agent_manager)
        self.tool_manager = ToolManager(self.tools_repo)

        self.data_manager.scan_and_register()
        self.tool_manager.scan_and_register()

        logger.info("SystemContext initialization complete")

    def get_runtime_tools(self):
        logger.debug("Collecting runtime tool schemas for LLM binding")
        schemas = [adapter.get_schema() for adapter in self.tool_manager.tool_map.values()]
        logger.info(f"Exposed {len(schemas)} tools to runtime")
        return schemas
