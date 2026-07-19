from typing import Any, override

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ResponseT,
    hook_config,
)
from langchain.messages import AnyMessage
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from core.pii.handlers.base_handler import BasePIIHandler
from utils.messages import get_last_ai_message, get_last_user_message


class PIIMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Detect and handle Personally Identifiable Information (PII) in conversations."""

    def __init__(
        self,
        pii_handler: BasePIIHandler,
        anonymize_input: bool = True,
        anonymize_tool_results: bool = True,
        deanonymize_output: bool = True,
    ) -> None:
        self._pii_handler = pii_handler
        self.anonymize_input = anonymize_input
        self.anonymize_tool_results = anonymize_tool_results
        self.deanonymize_output = deanonymize_output

    @hook_config(can_jump_to=['end'])
    @override
    def before_model(
        self, state: AgentState[Any], runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        messages = state['messages']
        if not messages:
            return None

        thread_id = self._get_thread_id(runtime)
        if not thread_id:
            return None

        new_messages = list(messages)
        any_modified = False

        if self.anonymize_input:
            updated_message, last_user_idx = self._anonymize_input(messages, thread_id)
            if updated_message and last_user_idx is not None:
                new_messages[last_user_idx] = updated_message
                any_modified = True

        if self.anonymize_tool_results:
            updated_message, tool_msg_idx = self._anonymize_tool_results(
                messages, thread_id
            )
            if updated_message and tool_msg_idx is not None:
                new_messages[tool_msg_idx] = updated_message
                any_modified = True

        if any_modified:
            return {'messages': new_messages}

        return None

    @hook_config(can_jump_to=['end'])
    async def abefore_model(
        self, state: AgentState[Any], runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        return self.before_model(state, runtime)

    @override
    def after_model(
        self, state: AgentState[Any], runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        if not self.deanonymize_output:
            return None

        messages = state['messages']
        if not messages:
            return None

        thread_id = self._get_thread_id(runtime)
        if not thread_id:
            return None

        try:
            updated_message, last_ai_idx = self._deanonymize_output(messages, thread_id)
            if not updated_message or last_ai_idx is None:
                return None
        finally:
            self._clear_vault(thread_id)

        new_messages = list(messages)
        new_messages[last_ai_idx] = updated_message

        return {'messages': new_messages}

    async def aafter_model(
        self,
        state: AgentState[Any],
        runtime: Runtime[ContextT],
    ) -> dict[str, Any] | None:
        return self.after_model(state, runtime)

    def _anonymize_input(
        self, messages: list[AnyMessage], thread_id: str
    ) -> tuple[HumanMessage | None, int | None]:
        """Apply PII handling to the last user message."""
        last_user_msg, last_user_idx = get_last_user_message(messages)
        if last_user_idx is not None and last_user_msg and last_user_msg.content:
            content = str(last_user_msg.content)
            new_content = self._anonymize(content, vault_key=thread_id)
            updated_message = HumanMessage(
                content=new_content,
                id=last_user_msg.id,
                name=last_user_msg.name,
            )
            return updated_message, last_user_idx

        return None, None

    def _anonymize_tool_results(
        self, messages: list[AnyMessage], thread_id: str
    ) -> tuple[ToolMessage | None, int | None]:
        """Apply PII handling to the tool messages after the last AI message."""
        last_ai_msg, last_ai_idx = get_last_ai_message(messages)
        if last_ai_idx is not None and last_ai_msg and last_ai_msg.content:
            # Get all tool messages after the last AI message
            for i in range(last_ai_idx + 1, len(messages)):
                msg = messages[i]
                if not isinstance(msg, ToolMessage):
                    continue

                tool_msg = msg
                if not tool_msg.content:
                    continue

                content = str(tool_msg.content)
                new_content = self._anonymize(content, vault_key=thread_id)
                updated_message = ToolMessage(
                    content=new_content,
                    id=tool_msg.id,
                    name=tool_msg.name,
                    tool_call_id=tool_msg.tool_call_id,
                )
                return updated_message, i

        return None, None

    def _deanonymize_output(
        self, messages: list[AnyMessage], thread_id: str
    ) -> tuple[AIMessage | None, int | None]:
        last_ai_msg, last_ai_idx = get_last_ai_message(messages)
        if last_ai_idx is None or not last_ai_msg or not last_ai_msg.content:
            return None, None

        content = str(last_ai_msg.content)
        new_content = self._deanonymize(content, vault_key=thread_id)
        updated_message = AIMessage(
            content=new_content,
            id=last_ai_msg.id,
            name=last_ai_msg.name,
            tool_calls=last_ai_msg.tool_calls,
        )
        return updated_message, last_ai_idx

    def _anonymize(self, content: str, vault_key: str) -> str:
        """Anonymize the given content using the PII handler."""
        return self._pii_handler.anonymize(content, vault_key=vault_key)

    def _deanonymize(self, content: str, vault_key: str) -> str:
        """De-anonymize the given content using the PII handler."""
        return self._pii_handler.deanonymize(content, vault_key=vault_key)

    def _clear_vault(self, vault_key: str) -> None:
        """Clear the vault data for the given key using the PII handler."""
        self._pii_handler.clear_vault(vault_key)

    def _get_thread_id(self, runtime: Runtime[ContextT]) -> str | None:
        """Get the thread ID from the runtime execution info."""
        if not runtime.execution_info or not runtime.execution_info.thread_id:
            return None
        return runtime.execution_info.thread_id
