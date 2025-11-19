import datetime
import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

from caseconverter import camelcase, kebabcase, titlecase
from pydantic import BaseModel, RootModel

from lamina import conf
from lamina.openapi.markdown import markdown_to_html
from lamina.openapi.types import ParameterObject


def extract_schema_info(
    model: Type[BaseModel | RootModel],
) -> Tuple[str, Dict[str, Any]]:
    """Return the JSON Schema reference name and full schema for a Pydantic model."""
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    name = schema.get("title") or model.__name__
    return name, schema


@dataclass
class ViewData:
    """Helper structure to hold collected Pydantic models.

    Attributes:
        request: Optional type for request body.
        response: Optional type for response body.
        params: Optional type for query parameters.
    """

    request: Optional[Type[BaseModel | RootModel]]
    response: Optional[Type[BaseModel | RootModel]]
    params: Optional[Type[BaseModel | RootModel]]
    import_path: Optional[str]
    path: Optional[str] = None
    methods: Optional[List[str]] = None
    extra_responses: Dict[int, Any] = None
    view_docstring: Optional[str] = None
    tags: Optional[List[str]] = None
    file_last_update: Optional[datetime] = None
    accept_media_type: str | None = None
    produce_media_type: str | None = None

    def extract_extras(self) -> Dict[str, Any]:
        """Merge json_schema_extra from provided models."""
        extra_info: Dict[str, Any] = {}
        for m in (self.request, self.response, self.params):
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
                extra_info[key] = value
        return extra_info

    def resolve_schemas(self):
        schemas: Dict[str, Any] = {}
        for m in (self.request, self.response, self.params):
            if m is None:
                continue
            name, schema = extract_schema_info(m)
            schemas[name] = schema

        # Also include schemas declared in custom responses
        for _code, cfg in self.extra_responses.items():
            schema_model = cfg.get("schema") if isinstance(cfg, dict) else None
            if schema_model is not None:
                name, schema_def = extract_schema_info(schema_model)
                schemas[name] = schema_def
        return schemas

    def get_methods(self):
        # Methods resolution
        wrapper_methods = self.methods
        extras = self.extract_extras()

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
        return methods_list

    def _parse_docstring(self) -> Tuple[str | None, str | None]:
        """Parse view docstring into a summary and a description.

        Returns:
            A tuple of (summary, description). If no docstring is provided,
            both values will be None to avoid injecting empty fields in the
            top-level info object.
        """
        if not self.view_docstring:
            return None, None

        doc = inspect.cleandoc(self.view_docstring)
        lines = doc.splitlines()

        # Remove leading empty lines
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            return None, None

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

        description = markdown_to_html(
            "\n".join(desc_lines).strip(), self.file_last_update
        )
        return summary, description

    def get_summary(self):
        extras = self.extract_extras()
        default_name = titlecase(self.get_path().replace("/", ""))
        return self._parse_docstring()[0] or extras.get("summary") or default_name

    def get_description(self):
        extras = self.extract_extras()
        return self._parse_docstring()[1] or extras.get("description") or ""

    def get_path(self):
        # Check for path in view first
        path = None
        if self.path:
            path = self.path
        if not path:
            # Example: foo.bar.handler
            import_parts = self.import_path.split(".")
            index = None
            match conf.LAMINA_USE_OBJECT_NAME:
                case "package":
                    index = -3
                case "module":
                    index = -2
                case "function":
                    index = -1
                case _:
                    raise ValueError(
                        "Invalid value for LAMINA_USE_OBJECT_NAME. "
                        "Expected one of: package, module, function."
                    )
            path = import_parts[index if len(import_parts) >= abs(index) else index + 1]
            path = kebabcase(path)
        return f"/{path}" if not path.startswith("/") else path

    def get_operation_id(self):
        extras = self.extract_extras()
        fallback_name = camelcase(self.get_path().replace("/", ""))
        return extras.get("operationId", fallback_name)

    def get_parameters(self) -> List[ParameterObject]:
        """Convert a Pydantic model into OpenAPI query parameters."""
        params: List[ParameterObject] = []
        if self.params is None:
            return params

        # Only handle BaseModel subclasses for parameters
        if inspect.isclass(self.params) and issubclass(self.params, BaseModel):
            for name, field in self.params.model_fields.items():
                annotation = field.annotation
                # Minimal type mapping
                t: str = "string"
                if annotation in (int, float):
                    t = "number" if annotation is float else "integer"
                elif annotation is bool:
                    t = "boolean"

                required_fields = self.params.model_json_schema().get("required") or []
                is_required = name in required_fields or field.alias in required_fields
                desc = field.description or ""
                params.append(
                    ParameterObject(
                        **{
                            "name": field.alias or name,
                            "in": "query",
                            "required": is_required,
                            "schema": {"type": t},
                            "description": desc,
                        }
                    )
                )
        return params

    @staticmethod
    def get_model_schema(
        model: Optional[Type[BaseModel | RootModel]],
    ) -> Optional[dict]:
        if model is None:
            return None
        name, _ = extract_schema_info(model)
        return {
            "application/json": {"schema": {"$ref": f"#/components/schemas/{name}"}}
        }

    def get_tags(self) -> List[str]:
        extras = self.extract_extras()
        tags = self.tags or extras.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        return tags
