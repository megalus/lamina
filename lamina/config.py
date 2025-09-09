from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback for older Pythons if used externally
    tomllib = None  # type: ignore[assignment]


HookCallable = Callable[..., Any]


@dataclass(frozen=True)
class HookNames:
    """Container for hook name keys used across env vars and pyproject.

    Attributes:
        pre_parse: Env or pyproject key for pre-parse hook.
        pre_execute: Env or pyproject key for pre-execute hook.
        pos_execute: Env or pyproject key for post-execute hook.
        pre_response: Env or pyproject key for pre-response hook.
    """

    pre_parse: str = "pre_parse"
    pre_execute: str = "pre_execute"
    pos_execute: str = "pos_execute"
    pre_response: str = "pre_response"


NAMES = HookNames()


def _import_from_string(path: str) -> HookCallable:
    """Import a callable from a string path.

    Supports formats "module.attr" and "module:attr".

    Args:
        path: Import path string.

    Returns:
        Imported callable.

    Raises:
        ImportError: If the path cannot be imported or is not a callable.
    """

    if ":" in path:
        module_path, attr = path.split(":", 1)
    else:
        module_path, attr = path.rsplit(".", 1)

    module = importlib.import_module(module_path)
    obj = getattr(module, attr)
    if not callable(obj):
        raise ImportError(f"Imported object '{path}' is not callable")
    return obj  # type: ignore[return-value]


def _read_pyproject_config() -> Dict[str, str]:
    """Read [tool.lamina] table from pyproject.toml.

    Returns an empty dict if file or table is missing or tomllib is not available.
    """

    # Locate project root pyproject.toml relative to this file
    # In typical installs, the file is at the package root one level up from lamina/
    root = os.path.dirname(os.path.dirname(__file__))
    pyproject_path = os.path.join(root, "pyproject.toml")

    if tomllib is None:
        return {}

    if not os.path.exists(pyproject_path):
        return {}

    try:
        with open(pyproject_path, "rb") as f:  # tomllib requires bytes
            data = tomllib.load(f)
    except Exception:
        return {}

    tool = data.get("tool") or {}
    lamina_tbl = tool.get("lamina") or {}

    # Normalize keys to strings
    return {str(k): str(v) for k, v in lamina_tbl.items() if isinstance(v, str)}


def get_hooks() -> Tuple[HookCallable, HookCallable, HookCallable, HookCallable]:
    """Resolve and return the four Lamina hooks.

    Resolution order for each hook:
    1) Environment variable (LAMINA_<HOOK_NAME_UPPER>)
    2) pyproject.toml [tool.lamina] entry
    3) Built-in placeholders in lamina.hooks

    Returns:
        Tuple of (pre_parse, pre_execute, pos_execute, pre_response) callables.
    """

    # Import placeholders lazily and safely to avoid circular imports with lamina.__init__
    import importlib as _il

    default_hooks = _il.import_module("lamina.hooks")  # type: ignore

    config = _read_pyproject_config()

    def resolve(name: str, env_var: str, default: HookCallable) -> HookCallable:
        # Env override
        env_value = os.getenv(env_var)
        if env_value:
            try:
                return _import_from_string(env_value)
            except Exception:
                # If misconfigured, fall back to default to avoid breaking runtime
                return default
        # pyproject value
        cfg_value = config.get(name)
        if cfg_value:
            try:
                return _import_from_string(cfg_value)
            except Exception:
                return default
        return default

    pre_parse = resolve(NAMES.pre_parse, "LAMINA_PRE_PARSE", default_hooks.pre_parse)
    pre_execute = resolve(
        NAMES.pre_execute, "LAMINA_PRE_EXECUTE", default_hooks.pre_execute
    )
    pos_execute = resolve(
        NAMES.pos_execute, "LAMINA_POS_EXECUTE", default_hooks.pos_execute
    )
    pre_response = resolve(
        NAMES.pre_response, "LAMINA_PRE_RESPONSE", default_hooks.pre_response
    )

    return pre_parse, pre_execute, pos_execute, pre_response
