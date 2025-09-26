from typing import Any, Dict, List, Optional

from loguru import logger

from lamina.main import LAMINA_REGISTRY
from lamina.openapi.generator import SwaggerGenerator
from lamina.openapi.types import (
    OpenAPIContactObject,
    OpenAPIExternalDocumentationObject,
    OpenAPILicenseObject,
    OpenAPIObject,
    OpenAPIServerObject,
)
from lamina.openapi.view_data import ViewData


def get_openapi_spec(
    *,
    title: str = "Lamina API",
    version: str = "1.0.0",
    summary: str | None = None,
    description: str | None = None,
    servers: Optional[List[OpenAPIServerObject]] = None,
    host: Optional[str] = None,
    base_path: str = "/",
    security_schemes: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
    contact: Optional[OpenAPIContactObject] = None,
    terms_of_service: str | None = None,
    license_info: Optional[OpenAPILicenseObject] = None,
    external_docs: Optional[OpenAPIExternalDocumentationObject] = None,
) -> OpenAPIObject:
    """Generate an OpenAPI 3.1 specification from all lamina-decorated handlers."""

    view_data = []
    for wrapper in LAMINA_REGISTRY:

        payload = {
            "request": getattr(wrapper, "schema_in", None),
            "response": getattr(wrapper, "schema_out", None),
            "params": getattr(wrapper, "params_in", None),
            "methods": getattr(wrapper, "methods", None),
            "tags": getattr(wrapper, "tags", None),
            "extra_responses": getattr(wrapper, "responses", {}) or {},
            "view_docstring": getattr(wrapper, "__doc__", None),
            "import_path": getattr(wrapper, "import_path", None),
            "path": getattr(wrapper, "path", None),
        }

        if (
            payload["request"] is None
            and payload["response"] is None
            and payload["params"] is None
        ):
            logger.warning(
                f"Skipping handler with no schemas: {payload['import_path']}"
            )
            continue

        view = ViewData(**payload)
        view_data.append(view)

    # Sort List based on path
    view_data.sort(key=lambda v: v.get_path())

    gen = SwaggerGenerator(view_data=view_data)

    return gen.generate(
        title=title,
        version=version,
        host=host,
        base_path=base_path,
        servers=servers,
        summary=summary,
        description=description,
        contact=contact,
        license_info=license_info,
        terms_of_service=terms_of_service,
        security_schemes=security_schemes,
        security=security,
        external_docs=external_docs,
    )
