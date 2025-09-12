import importlib
import os
import tomllib
from dataclasses import dataclass
from typing import Any, Callable, Dict

HookCallable = Callable[..., Any]


def get_toml_configuration() -> Dict[str, Any]:
    """
    Reads the pyproject.toml file and returns its content as a dictionary.

    Returns:
        A dictionary containing the contents of the pyproject.toml file.
        If the file does not exist or cannot be read, an empty dictionary is returned.
    """
    try:
        with open("pyproject.toml", "rb") as f:
            all_data = tomllib.load(f)
            return all_data.get("tool", {}).get("lamina", {})
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


@dataclass
class LaminaSettings:
    settings: Dict[str, Any]

    def _get_setting(self, name: str, default: Any = None) -> Any:
        full_name = f"LAMINA_{name.upper()}"
        # First, check environment variables
        value = os.getenv(full_name, None)
        if not value:
            # Then check the settings dictionary
            value = self.settings.get(name, default)

        module_path = (
            ".".join(value.split(".")[:-1]) if ":" not in value else value.split(":")[0]
        )
        func_name = value.split(".")[-1] if ":" not in value else value.split(":")[1]
        try:
            module = importlib.import_module(module_path)
            value = getattr(module, func_name)
        except (ImportError, AttributeError) as error:
            raise ImportError(
                f"Could not import '{value}' for setting '{full_name}'"
            ) from error

        return value

    @property
    def LAMINA_PRE_PARSE_CALLBACK(self) -> HookCallable:
        return self._get_setting("pre_parse_callback", default="lamina.hooks.pre_parse")

    @property
    def LAMINA_PRE_EXECUTE_CALLBACK(self) -> HookCallable:
        return self._get_setting(
            "pre_execute_callback", default="lamina.hooks.pre_execute"
        )

    @property
    def LAMINA_POS_EXECUTE_CALLBACK(self) -> HookCallable:
        return self._get_setting(
            "pos_execute_callback", default="lamina.hooks.pos_execute"
        )

    @property
    def LAMINA_PRE_RESPONSE_CALLBACK(self) -> HookCallable:
        return self._get_setting(
            "pre_response_callback", default="lamina.hooks.pre_response"
        )


# Create a single instance of the settings class
_lamina_settings = LaminaSettings(get_toml_configuration())


def __getattr__(name: str) -> Any:
    """
    Implement PEP 562 __getattr__ to lazily load settings.

    This function is called when an attribute is not found in the module's
    global namespace. It delegates to the _lamina_settings instance.
    """
    return getattr(_lamina_settings, name)
