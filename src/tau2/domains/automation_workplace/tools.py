import json
from typing import Optional

from tau2.data_model.message import ToolOutputWithImages
from tau2.domains.automation_workplace import automationbench_source
from tau2.domains.automation_workplace.data_model import AutomationWorkplaceDB
from tau2.domains.automation_workplace.family_registry import (
    call_tool as call_family_tool,
)
from tau2.domains.automation_workplace.family_registry import (
    check_assertion as check_family_assertion,
)
from tau2.domains.automation_workplace.family_registry import (
    tool_schema as family_tool_schema,
)
from tau2.domains.automation_workplace.family_registry import (
    tool_schemas as family_tool_schemas,
)
from tau2.domains.automation_workplace.knowledge import search_documents
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class AutomationWorkplaceTools(ToolKitBase):
    """Real-API-shaped tools backed by AutomationBench's Pydantic simulators."""

    db: AutomationWorkplaceDB

    def __init__(self, db: AutomationWorkplaceDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def api_search(self, query: str, top_k: int = 5) -> str:
        """Search the connected apps' real API schemas using BM25.

        Use this before api_fetch to discover endpoint URLs, HTTP methods,
        parameters, request bodies, and response shapes.

        Args:
            query: API-native search terms, such as "Gmail list messages" or
                "Salesforce update opportunity".
            top_k: Maximum number of schema matches to return, from 1 through 20.

        Returns:
            JSON containing ranked endpoint definitions and full URLs.
        """
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")
        return automationbench_source.api_search(query=query, top_k=top_k)

    @is_tool(ToolType.WRITE)
    def api_fetch(
        self,
        method: str,
        url: str,
        params: Optional[str] = None,
        body: Optional[str] = None,
    ) -> str:
        """Call a simulated endpoint using its real public API shape.

        Args:
            method: HTTP method: GET, POST, PUT, PATCH, or DELETE.
            url: Full endpoint URL returned by api_search.
            params: Optional query parameters encoded as a JSON object string.
            body: Optional request body encoded as a JSON object string. The
                QuickBooks query endpoint accepts its documented text query.

        Returns:
            A JSON string matching the corresponding real API response shape.
        """
        world = automationbench_source.world_state_from_dict(self.db.world)
        response = automationbench_source.api_fetch(
            world=world,
            method=method,
            url=url,
            params=params,
            body=body,
        )
        self.db.world = world.model_dump(mode="json")
        return response

    @is_tool(ToolType.THINK)
    def base64_encode(self, text: str) -> str:
        """Encode text as base64url for Gmail API message bodies.

        Args:
            text: Plaintext body or complete RFC 2822 message.

        Returns:
            Base64url-encoded text accepted by Gmail's send endpoints.
        """
        return automationbench_source.base64_encode(text)

    @is_tool(ToolType.READ)
    def knowledge_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search task-local policies, runbooks, and technical documentation.

        Technical documents may contain exact discoverable-tool names and argument
        schemas. Prefer current documents over superseded versions.

        Args:
            query: Natural-language or API-native terms describing the needed policy,
                procedure, application, or operation.
            top_k: Maximum number of full documents to return, from 1 through 10.

        Returns:
            BM25-ranked documents with IDs, version status, timestamps, and content.
        """
        if top_k < 1 or top_k > 10:
            raise ValueError("top_k must be between 1 and 10")
        return search_documents(self.db.knowledge_documents, query, top_k)

    @is_tool(ToolType.GENERIC, mutates_state=True)
    def unlock_discoverable_tool(self, discoverable_tool_name: str) -> dict:
        """Unlock an app operation whose exact name was found in the knowledge base.

        Args:
            discoverable_tool_name: Exact discoverable-tool name from current
                technical docs.

        Returns:
            The operation description and JSON argument schema.
        """
        schemas = family_tool_schemas(self.db.interactive_family)
        if discoverable_tool_name not in schemas:
            raise ValueError(f"Unknown discoverable tool: {discoverable_tool_name}")
        if discoverable_tool_name not in self.db.unlocked_tools:
            self.db.unlocked_tools.append(discoverable_tool_name)
            self.db.unlocked_tools.sort()
        return family_tool_schema(
            self.db.interactive_family,
            discoverable_tool_name,
        )

    @is_tool(ToolType.WRITE)
    def call_discoverable_tool(
        self, discoverable_tool_name: str, arguments: str = "{}"
    ) -> str:
        """Call an app operation previously unlocked from technical documentation.

        Read operations return live simulated records. Write operations mutate the
        Pydantic-backed app state and return API-shaped responses.

        Args:
            discoverable_tool_name: Exact operation name previously unlocked.
            arguments: One JSON object string matching the unlocked schema.

        Returns:
            JSON response from the simulated application.
        """
        if discoverable_tool_name not in self.db.unlocked_tools:
            raise ValueError(
                f"Tool {discoverable_tool_name!r} is locked. Find its current "
                "technical document and call unlock_discoverable_tool first."
            )
        response = call_family_tool(self.db, discoverable_tool_name, arguments)
        try:
            payload = json.loads(response)
        except (TypeError, json.JSONDecodeError):
            return response
        if isinstance(payload, dict) and payload.get("_image_paths"):
            images = payload.pop("_image_paths")
            return ToolOutputWithImages(
                content=json.dumps(payload, sort_keys=True), images=images
            )
        return response

    def assert_source_assertion(self, assertion_index: int) -> bool:
        """Evaluate one hidden source-task assertion against final state."""
        if assertion_index < 0 or assertion_index >= len(self.db.assertions):
            raise ValueError("Assertion index out of range")
        world = automationbench_source.world_state_from_dict(self.db.world)
        return automationbench_source.check_assertion(
            world,
            self.db.assertions[assertion_index],
        )

    def assert_interactive_assertion(self, assertion_index: int) -> bool:
        """Evaluate one hidden exact-state assertion for an authored task."""
        if assertion_index < 0 or assertion_index >= len(
            self.db.interactive_assertions
        ):
            raise ValueError("Interactive assertion index out of range")
        return check_family_assertion(
            self.db,
            self.db.interactive_assertions[assertion_index],
        )
