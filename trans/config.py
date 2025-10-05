# trans/config.py
import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from dataclasses import dataclass, field, fields


@dataclass
class LLMConfig:
    """
    Configuration for Large Language Model backend settings.
    """
    # Backend provider (e.g., "openai", "aliyun")
    backend: str = "openai"
    # Model name to use for translation
    model: str = "gpt-4o-mini"
    # Environment variable name for API key
    api_key_env: str = "LLM_API_KEY"
    # Direct API key (optional, can be None if using environment variable)
    api_key: Optional[str] = None
    # Base URL for the LLM API
    base_url: str = "https://api.openai.com/v1/  "
    # Temperature parameter for generation (lower = more deterministic)
    temperature: float = 0.1
    # Top-p parameter for generation (controls diversity)
    top_p: float = 0.9
    # Maximum number of concurrent API calls
    max_concurrent: int = 15
    # Maximum number of retry attempts for failed API calls
    max_retries: int = 3


@dataclass
class TranslationConfig:
    """
    Configuration for translation-specific settings.
    """
    # Target language for translation (e.g., "Chinese", "French", "Spanish")
    target_lang: str = "Chinese"
    # Maximum chunk size for text splitting during translation
    chunk_size: int = 3800
    # Whether to use Chain-of-Thought prompting (not currently implemented)
    use_cot: bool = False
    # Whether to fix hyphen spacing issues after translation
    fix_hyphen: bool = True
    # Whether to fix command adhesion issues after translation
    fix_command_adhesion: bool = True


@dataclass
class OutputConfig:
    """
    Configuration for output-related settings.
    """
    # Directory where output files will be saved
    dir: str = "./output"
    # Whether to compile the translated LaTeX to PDF
    compile: bool = True


@dataclass
class InputConfig:
    """
    Configuration for input-related settings.
    Different fields are used depending on the operation mode.
    """
    # URL for arXiv mode (e.g., arxiv.org/abs/1234.5678)
    url: Optional[str] = None
    # File path for single file mode
    path: Optional[str] = None
    # Directory path for project mode
    dir: Optional[str] = None


@dataclass
class PromptsConfig:
    """
    Configuration for prompt templates (not currently used extensively).
    """
    # System prompt template
    system: str = "You are a professional LaTeX translator."
    # User prompt template
    user: str = "Translate to {target_lang}...{text}"


@dataclass
class AppConfig:
    """
    Main application configuration that combines all sub-configurations.
    """
    # Operation mode: "arxiv", "single", or "project"
    mode: str = "arxiv"
    # Project name for identification (optional)
    project_name: Optional[str] = None
    # Input configuration
    input: InputConfig = field(default_factory=InputConfig)
    # Output configuration
    output: OutputConfig = field(default_factory=OutputConfig)
    # Translation configuration
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    # LLM backend configuration
    llm: LLMConfig = field(default_factory=LLMConfig)
    # Prompt configuration
    prompts: PromptsConfig = field(default_factory=PromptsConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> 'AppConfig':
        """
        Load configuration from a YAML file.

        Args:
            path (Path): Path to the YAML configuration file

        Returns:
            AppConfig: Configuration object loaded from YAML
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':  # <-- Fixed: added parameter name `data`
        """
        Create AppConfig instance from a dictionary.
        This method safely handles missing or extra configuration keys.

        Args:
            data (Dict[str, Any]): Dictionary containing configuration data

        Returns:
            AppConfig: Configuration object created from the dictionary
        """
        # --- 1. Extract sub-configuration dictionaries ---
        llm_data = data.get('llm', {})
        trans_data = data.get('translation', {})
        output_data = data.get('output', {})
        input_data = data.get('input', {})
        prompts_data = data.get('prompts', {})

        # --- 2. Get valid field names for each dataclass ---
        valid_llm_fields = {f.name for f in fields(LLMConfig)}
        valid_trans_fields = {f.name for f in fields(TranslationConfig)}
        valid_output_fields = {f.name for f in fields(OutputConfig)}
        valid_input_fields = {f.name for f in fields(InputConfig)}
        valid_prompts_fields = {f.name for f in fields(PromptsConfig)}

        # --- 3. Filter dictionaries to keep only valid fields ---
        filtered_llm_data = {k: v for k, v in llm_data.items() if k in valid_llm_fields}
        filtered_trans_data = {k: v for k, v in trans_data.items() if k in valid_trans_fields}
        filtered_output_data = {k: v for k, v in output_data.items() if k in valid_output_fields}
        filtered_input_data = {k: v for k, v in input_data.items() if k in valid_input_fields}
        filtered_prompts_data = {k: v for k, v in prompts_data.items() if k in valid_prompts_fields}

        # --- 4. Safely create sub-configuration instances ---
        llm_config = LLMConfig(**filtered_llm_data)
        trans_config = TranslationConfig(**filtered_trans_data)
        output_config = OutputConfig(**filtered_output_data)
        input_config = InputConfig(**filtered_input_data)
        prompts_config = PromptsConfig(**filtered_prompts_data)

        # --- 5. Extract top-level AppConfig fields (mode, project_name) ---
        app_data = {}
        if 'mode' in data:  # <-- Fixed: complete if statement
            app_data['mode'] = data['mode']
        if 'project_name' in data:
            app_data['project_name'] = data['project_name']

        # --- 6. Create and return AppConfig instance ---
        return cls(
            **app_data,
            input=input_config,
            output=output_config,
            translation=trans_config,
            llm=llm_config,
            prompts=prompts_config
        )

    def validate(self):
        """
        Validate the configuration for correctness.
        This is an instance method that should be called after AppConfig instance creation.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate operation mode
        if self.mode not in ["arxiv", "single", "project"]:
            raise ValueError(f"Invalid mode: {self.mode}")

        # Validate arXiv mode requires URL
        if self.mode == "arxiv" and not self.input.url:
            raise ValueError("mode=arxiv requires input.url")

        # Validate single mode requires path
        if self.mode == "single" and not self.input.path:
            raise ValueError("mode=single requires input.path")

        # Validate project mode requires directory
        if self.mode == "project" and not self.input.dir:
            raise ValueError("mode=project requires input.dir")

        # Check if API key exists in environment variables
        if not self.llm.api_key and not os.environ.get(self.llm.api_key_env):
            raise ValueError(f"API key not found in environment variable: {self.llm.api_key_env}")


# Global configuration instance
_config = None


def get_config() -> AppConfig:
    """
    Get the global configuration instance.

    Returns:
        AppConfig: The global configuration instance

    Raises:
        RuntimeError: If configuration has not been loaded yet
    """
    global _config
    if _config is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    return _config


def load_config(config_path: Path):
    """
    Load configuration from a YAML file and validate it.

    Args:
        config_path (Path): Path to the configuration file to load
    """
    global _config
    # 1. Create AppConfig instance from YAML file
    _config = AppConfig.from_yaml(config_path)
    # 2. Then call the instance's validate method to check configuration validity
    _config.validate()