import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type, TypedDict

from pydantic import BaseModel, RootModel

from lamina.main import LAMINA_REGISTRY


class ServerObject(TypedDict, total=False):
    url: str
    description: str


class InfoObject(TypedDict, total=False):
    title: str
    version: str
    description: str
    termsOfService: str


class RequestBodyObject(TypedDict, total=False):
    content: Dict[str, Any]
    required: bool
    description: str


class ResponseObject(TypedDict, total=False):
    description: str | Any | None
    content: Dict[str, Any]


class ParameterObject(TypedDict, total=False):
    name: str
    in_: str
    required: bool
    schema: Dict[str, Any]
    description: str


class OperationObject(TypedDict, total=False):
    summary: str | Any | None
    description: str
    tags: List[str]
    operationId: str
    parameters: List[ParameterObject]
    requestBody: RequestBodyObject
    responses: Dict[str, ResponseObject]


class ComponentsObject(TypedDict, total=False):
    schemas: Dict[str, Any]
    securitySchemes: Dict[str, Any]


class OpenAPIObject(TypedDict, total=False):
    openapi: str
    info: InfoObject
    servers: List[ServerObject]
    security: List[Dict[str, List[str]]]
    paths: Dict[str, Dict[str, OperationObject]]
    components: ComponentsObject


@dataclass
class _CollectedSchemas:
    """Helper structure to hold collected Pydantic models.

    Attributes:
        request: Optional type for request body.
        response: Optional type for response body.
        params: Optional type for query parameters.
    """

    request: Optional[Type[BaseModel | RootModel]]
    response: Optional[Type[BaseModel | RootModel]]
    params: Optional[Type[BaseModel | RootModel]]


def _model_schema_ref(model: Type[BaseModel | RootModel]) -> Tuple[str, Dict[str, Any]]:
    """Return the JSON Schema reference name and full schema for a Pydantic model."""
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    name = schema.get("title") or model.__name__
    return name, schema


def _extract_extras(models: _CollectedSchemas) -> Dict[str, Any]:
    """Merge json_schema_extra from provided models.

    Later models override earlier ones."""
    merged: Dict[str, Any] = {}
    for m in (models.request, models.response, models.params):
        if m is None:
            continue
        schema = m.model_json_schema()
        # json_schema_extra lands as top-level unknown keys in Pydantic v2
        for key, value in schema.items():
            if key in {
                "$defs",
                "properties",
                "type",
                "title",
                "required",
                "$ref",
                "$schema",
            }:
                continue
            merged[key] = value
    return merged


def _build_parameters(
    model: Optional[Type[BaseModel | RootModel]],
) -> List[ParameterObject]:
    """Convert a Pydantic model into OpenAPI query parameters."""
    params: List[ParameterObject] = []
    if model is None:
        return params

    # Only handle BaseModel subclasses for parameters
    if inspect.isclass(model) and issubclass(model, BaseModel):
        for name, field in model.model_fields.items():
            annotation = field.annotation
            # Minimal type mapping
            t: str = "string"
            if annotation in (int, float):
                t = "number" if annotation is float else "integer"
            elif annotation is bool:
                t = "boolean"

            required = name in (model.model_json_schema().get("required") or [])
            desc = field.description or ""
            params.append(
                ParameterObject(
                    **{
                        "name": name,
                        "in": "query",
                        "required": bool(required),
                        "schema": {"type": t},
                        "description": desc,
                    }
                )
            )
    return params


def _content_for_model(
    model: Optional[Type[BaseModel | RootModel]],
) -> Optional[dict]:
    if model is None:
        return None
    name, _ = _model_schema_ref(model)
    return {"application/json": {"schema": {"$ref": f"#/components/schemas/{name}"}}}


def _parse_docstring(doc: Optional[str]) -> tuple[str, str]:
    """Parse a docstring into summary and description.

    The summary is the first non-empty line. The description is the block of text
    after the first line up to the section that begins with common headings like
    Args:, Arguments:, Parameters:, Returns:, Return:, Raises:, or Examples:.
    """
    if not doc:
        return "", ""
    lines = [ln.rstrip() for ln in doc.strip().splitlines()]
    # Remove leading empty lines
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return "", ""
    summary = lines[0].strip()
    rest = lines[1:]
    stop_tokens = {
        "args:",
        "arguments:",
        "parameters:",
        "returns:",
        "return:",
        "raises:",
        "examples:",
    }
    desc_lines: list[str] = []
    for ln in rest:
        if ln.strip().lower() in stop_tokens:
            break
        desc_lines.append(ln)
    description = "\n".join(desc_lines).strip()
    return summary, description


def _titleize_func_name(name: str) -> str:
    """Convert snake_case or kebab-case function name into Title Case words."""
    cleaned = name.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in cleaned.split())


def get_openapi_spec(
    *,
    title: str = "Lamina API",
    version: str = "1.0.0",
    description: str | None = None,
    servers: Optional[List[str]] = None,
    host: Optional[str] = None,
    base_path: str | None = "/",
    security_schemes: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
) -> OpenAPIObject:
    """Generate an OpenAPI 3.1 specification from all lamina-decorated handlers.

    The generator inspects all registered lamina handlers and uses the json_schema_extra
    provided in the Pydantic models (schema_in, schema_out, params_in) to determine
    operation-level metadata like path, method, summary, tags, and operationId.

    Args:
        title: API title.
        version: API version.
        description: API description.
        servers: Optional list of server URLs.
                    If omitted, will be built from host+base_path.
        host: Convenience hostname to build server URL.
        base_path: Convenience base path to build server URL (default "/").
        security_schemes: Optional security schemes to include in components.
                          If omitted, defaults to API Key in Authorization header.
        security: Optional global security requirements.
                  If omitted, defaults to requiring the default API Key scheme.

    Returns:
        An OpenAPIObject dict ready to be serialized as JSON.
    """

    paths: Dict[str, Dict[str, OperationObject]] = {}
    components: Dict[str, Any] = {}

    # Build servers list
    server_objs: List[ServerObject] = []
    if servers:
        server_objs = [{"url": s} for s in servers]
    elif host:
        bp = base_path or "/"
        url = f"https://{host}{bp}"
        server_objs = [{"url": url}]

    # Iterate over registered handlers
    for wrapper in LAMINA_REGISTRY:
        schema_in: Optional[Type[BaseModel | RootModel]] = getattr(
            wrapper, "schema_in", None
        )
        schema_out: Optional[Type[BaseModel | RootModel]] = getattr(
            wrapper, "schema_out", None
        )
        params_in: Optional[Type[BaseModel | RootModel]] = getattr(
            wrapper, "params_in", None
        )

        # Ignore minimal handlers without any schemas to keep behavior consistent
        if schema_in is None and schema_out is None and params_in is None:
            continue

        models = _CollectedSchemas(
            request=schema_in, response=schema_out, params=params_in
        )
        extras = _extract_extras(models)

        # Resolve path: decorator arg > extras > default from function name
        wrapper_path = getattr(wrapper, "path", None)
        default_name = (
            getattr(wrapper, "__name__", "operation").replace("_", "-").lower()
        )
        default_path = f"/{default_name}"
        path: str = wrapper_path or extras.get("path") or default_path

        # Determine methods: decorator `methods`
        # > extras["method" or "methods"] > default ["post"]
        wrapper_methods = getattr(wrapper, "methods", None)
        methods_list: list[str] = []
        if wrapper_methods:
            methods_list = [m.lower() for m in wrapper_methods]
        else:
            m_from_extra = (
                extras.get("methods")
                or extras.get("method")
                or extras.get("http_method")
            )
            if isinstance(m_from_extra, str):
                methods_list = [m_from_extra.lower()]
            elif isinstance(m_from_extra, (list, tuple)):
                methods_list = [str(m).lower() for m in m_from_extra]
            else:
                methods_list = ["post"]

        # Collect schemas in components
        for m in (schema_in, schema_out, params_in):
            if m is None:
                continue
            name, schema = _model_schema_ref(m)
            components[name] = schema

        # Build shared operation parts
        parameters = _build_parameters(params_in)
        request_body_content = _content_for_model(schema_in)
        responses: Dict[str, ResponseObject] = {}

        # Use 200 (default)
        response_content = _content_for_model(schema_out)
        responses["200"] = ResponseObject(
            **{
                "description": extras.get(
                    "response_description", "Successful Response"
                ),
                "content": response_content
                or {"application/json": {"schema": {"type": "string"}}},
            }
        )

        # Add default error responses from lamina error handling
        responses["400"] = {"description": "Bad Request"}
        responses["500"] = {"description": "Internal Server Error"}

        # Merge custom responses from decorator
        # (e.g., {404: {"schema": Model, "description": "..."}})
        custom_responses = getattr(wrapper, "responses", {}) or {}
        for status_code, cfg in custom_responses.items():
            # Accept int or str codes; normalize to string
            code_str = str(status_code)
            schema_model = cfg.get("schema") if isinstance(cfg, dict) else None
            desc = cfg.get("description") if isinstance(cfg, dict) else None
            content = None
            if schema_model is not None:
                name, schema_def = _model_schema_ref(schema_model)
                components[name] = schema_def
                content = {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{name}"}
                    }
                }
            response_obj: ResponseObject = {"description": desc or "Response"}
            if content:
                response_obj["content"] = content
            responses[code_str] = response_obj

        # Summary and description: docstring > extras > defaults
        doc_summary, doc_description = _parse_docstring(
            getattr(wrapper, "__doc__", None)
        )
        if doc_summary:
            summary_val = doc_summary
            description_val = doc_description
        else:
            summary_val = extras.get("summary") or _titleize_func_name(
                getattr(wrapper, "__name__", "operation")
            )
            description_val = extras.get("description", "")

        # Build operation object template
        base_op: OperationObject = {
            "summary": summary_val,
            "description": description_val,
            "tags": extras.get("tags", []) or [],
            "operationId": extras.get(
                "operationId", getattr(wrapper, "__name__", "operation")
            ),
            "parameters": parameters,
            "responses": responses,
        }
        if request_body_content:
            base_op["requestBody"] = RequestBodyObject(
                **{"content": request_body_content, "required": True}
            )

        if path not in paths:
            paths[path] = {}
        for method in methods_list:
            paths[path][method] = base_op

    # Sort paths alphabetically by key to ensure deterministic ordering
    sorted_paths: Dict[str, Dict[str, OperationObject]] = {}
    for p in sorted(paths.keys()):
        sorted_paths[p] = paths[p]

    # Default security: API Key in Authorization header
    if security_schemes is None:
        security_schemes = {
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
        }
    if security is None:
        security = [{"ApiKeyAuth": []}]

    return {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
            **({"description": description} if description else {}),
        },
        "servers": server_objs,
        "security": security,
        "paths": sorted_paths,
        "components": {"schemas": components, "securitySchemes": security_schemes},
    }
