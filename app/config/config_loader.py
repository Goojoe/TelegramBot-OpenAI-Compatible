"""
Configuration loader for managing YAML config files and environment variables.
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ConfigLoader:
    """
    Handles loading and parsing configuration from YAML files and environment variables.
    """

    def __init__(self, config_path: str = "configs/bot_config.yaml"):
        """
        Initialize the config loader.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dict containing configuration values
        """
        if not self.config_path.exists():
            return {}

        with open(self.config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)

        # Process environment variable references in config
        return self._process_env_vars(config)

    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process environment variable references in the config.

        Args:
            config: The configuration dictionary

        Returns:
            Processed configuration with environment variables replaced
        """
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # Extract environment variable name
            env_var = config[2:-1]
            return os.environ.get(env_var, "")
        else:
            return config

    def get_api_endpoint(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """
        Get API endpoint configuration by name.

        Args:
            endpoint_name: Name of the API endpoint

        Returns:
            API endpoint configuration or None if not found
        """
        endpoints = self.config.get("api_endpoints", {})
        return endpoints.get(endpoint_name)

    def get_command_config(self, command_name: str) -> Optional[Dict[str, Any]]:
        """
        Get command configuration by name.

        Args:
            command_name: Name of the command (including the / prefix)

        Returns:
            Command configuration or None if not found
        """
        commands = self.config.get("commands", {})
        return commands.get(command_name)

    def get_all_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all command configurations.

        Returns:
            Dictionary of command configurations
        """
        return self.config.get("commands", {})
