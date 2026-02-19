import yaml
import os
from pathlib import Path

from app.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")

class ConfigApiManager:
    def __init__(self, config_path: str = "config_api.yaml"):

        parent = Path(__file__).parent
        self.config_path = parent / 'config' / config_path
        self.credentials = self._load_config()

        logger.info(f"Path: {__file__}")

    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path} {__file__}")
            
        with open(self.config_path, 'r') as file:
            try:
                # safe_load converts YAML into a standard Python dictionary
                config = yaml.safe_load(file)
                return config.get('alpaca', {})
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file: {e}")
                return {}

    @property
    def api_key(self) -> str:
        return self.credentials.get('api_key')

    @property
    def api_secret(self) -> str:
        return self.credentials.get('api_secret')