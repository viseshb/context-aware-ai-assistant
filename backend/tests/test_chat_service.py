from __future__ import annotations

import asyncio
from datetime import datetime

from app.config import settings
from app.llm.base import ChatEvent, ChatEventType, LLMProvider
from app.llm.registry import LLMRegistry
from app.mcp_layer.manager import MCPTool
from app.services.chat_service import ChatService


class RecordingProvider(LLMProvider):
    def __init__(self, supports_tools: bool = False):
        self.provider_name = "fake"
        self.model_id = "fake-model"
        self.display_name = "Fake Model"
        self.tier = "free"
        self.supports_tools = supports_tools
        self.supports_streaming = True
        self.calls: list[list[tuple[str, str]]] = []

    async def chat(self, messages, tools=None, stream=True):
        self.calls.append([(message.role, message.content) for message in messages])
        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content=f"reply {len(self.calls)}")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class ToolCallingProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "tool-model"
        self.display_name = "Tool Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name="github_get_repo_info",
                tool_args={"repo": "acme/api"},
                tool_call_id="call_repo_info",
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="Repo info ready.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class InspectingToolProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "inspect-model"
        self.display_name = "Inspect Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0
        self.last_tool_message = ""

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name="github_get_repo_info",
                tool_args={"repo": "acme/api"},
                tool_call_id="call_repo_info",
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        self.last_tool_message = next(
            message.content for message in reversed(messages) if message.role == "tool"
        )
        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="Sanitized tool result received.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class SensitiveOutputProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "sensitive-model"
        self.display_name = "Sensitive Model"
        self.tier = "free"
        self.supports_tools = False
        self.supports_streaming = True

    async def chat(self, messages, tools=None, stream=True):
        yield ChatEvent(
            type=ChatEventType.TEXT_CHUNK,
            content="GitHub token ghp_1234567890abcdefghijklmnopqrstuvwxyzAB should never be shown.",
        )
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class ToolLeakyProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "leaky-model"
        self.display_name = "Leaky Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TEXT_CHUNK,
                content=(
                    "I'll check that now. "
                    "[{'type': 'text', 'text': 'The repository name Interview-Helper "
                    "did not include an owner prefix.'}]"
                ),
            )
            yield ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name="github_get_repo_info",
                tool_args={"repo": "Interview-Helper"},
                tool_call_id="call_repo_info",
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(
            type=ChatEventType.TEXT_CHUNK,
            content="Interview-Helper uses `main` as the default branch.",
        )
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class ImplicitToolJsonProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "implicit-tool-model"
        self.display_name = "Implicit Tool Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TEXT_CHUNK,
                content='{"type":"function","name":"github_get_repo_info","parameters":{"repo":"Interview-Helper"}}',
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="Implicit tool call succeeded.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class BareJsonToolProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "bare-json-tool-model"
        self.display_name = "Bare JSON Tool Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TEXT_CHUNK,
                content='{"name":"github_get_repo_info","parameters":{"repo":"Interview-Helper"}}',
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="Bare JSON tool call succeeded.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class HallucinatedMetricsProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "hallucinated-metrics-model"
        self.display_name = "Hallucinated Metrics Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(self, messages, tools=None, stream=True):
        yield ChatEvent(
            type=ChatEventType.TEXT_CHUNK,
            content="The Interview-Helper repository has 963 commits and 0 deployment workflows.",
        )
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class FakeMCPManager:
    def __init__(self, result: str | None = None, expected_args: dict | None = None):
        self._tools = [
            MCPTool(
                name="github_get_repo_info",
                description="Get repository metadata.",
                parameters={
                    "type": "object",
                    "properties": {"repo": {"type": "string"}},
                    "required": ["repo"],
                },
                server_name="github",
            )
        ]
        self._result = result or '{"name": "acme/api", "default_branch": "main"}'
        self._expected_args = expected_args or {"repo": "acme/api"}

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        if tool_name == "github_get_repo_info":
            return "github"
        return None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        assert tool_name == "github_get_repo_info"
        assert args == self._expected_args
        return self._result


class FakeMetricsMCPManager:
    def __init__(self):
        self._tools = [
            MCPTool(
                name="github_count_commits",
                description="Count commits in a repository.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "author": {"type": "string", "default": ""},
                    },
                    "required": ["repo"],
                },
                server_name="github",
            ),
            MCPTool(
                name="github_get_repo_metrics",
                description="Get repository counts.",
                parameters={
                    "type": "object",
                    "properties": {"repo": {"type": "string"}},
                    "required": ["repo"],
                },
                server_name="github",
            ),
        ]

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        if tool_name.startswith("github_"):
            return "github"
        return None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        if tool_name == "github_count_commits":
            return '{"repo":"viseshb/Interview-Helper","author":"viseshb","branch":"","path":"","since":"","until":"","commit_count":634}'
        if tool_name == "github_get_repo_metrics":
            return '{"repo":"viseshb/Interview-Helper","default_branch":"master","counted_branch":"master","commit_count":637,"pull_request_count":8,"workflow_count":2,"deployment_workflow_count":1,"deployment_workflows":[{"name":"Deploy Backend + Frontend","path":".github/workflows/deploy.yml","state":"active"}],"warnings":{"commits":"","pull_requests":"","workflows":""}}'
        raise AssertionError(f"Unexpected tool: {tool_name}")


class FakeRepoUsageMCPManager:
    def __init__(self):
        self._tools = [
            MCPTool(
                name="github_get_repo_info",
                description="Get repository metadata.",
                parameters={
                    "type": "object",
                    "properties": {"repo": {"type": "string"}},
                    "required": ["repo"],
                },
                server_name="github",
            ),
            MCPTool(
                name="github_read_file",
                description="Read a repository file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "ref": {"type": "string", "default": ""},
                    },
                    "required": ["repo", "path"],
                },
                server_name="github",
            ),
        ]

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        if tool_name.startswith("github_"):
            return "github"
        return None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        if tool_name == "github_get_repo_info":
            return '{"name":"viseshb/Interview-Helper","default_branch":"master"}'
        if tool_name == "github_read_file":
            return (
                "# Interview Mate\n\n"
                "- **Live STT**: Speaker loopback with Deepgram Flux/Nova or AssemblyAI Universal-3 Pro\n"
                "- **Push-to-Talk**: Hold Z to record, release to transcribe + detect question + draft answer\n"
            )
        raise AssertionError(f"Unexpected tool: {tool_name}")


class FakeKimiCommitMCPManager:
    def __init__(self):
        self._tools = [
            MCPTool(
                name="github_count_commits",
                description="Count commits in a repository.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "author": {"type": "string", "default": ""},
                    },
                    "required": ["repo"],
                },
                server_name="github",
            )
        ]

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        return "github" if tool_name == "github_count_commits" else None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        assert tool_name == "github_count_commits"
        assert args == {"repo": "viseshb/Interview-Helper"}
        return '{"repo":"viseshb/Interview-Helper","author":"","branch":"","path":"","since":"","until":"","commit_count":637}'


class FakeKimiDbTablesMCPManager:
    def __init__(self):
        self._tools = [
            MCPTool(
                name="db_list_tables",
                description="List database tables.",
                parameters={"type": "object", "properties": {}, "required": []},
                server_name="postgres",
            )
        ]

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        return "postgres" if tool_name == "db_list_tables" else None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        assert tool_name == "db_list_tables"
        return '[{"schema":"public","table":"deployments","columns":9},{"schema":"public","table":"incidents","columns":11}]'


class FakeKimiWorkflowMCPManager:
    def __init__(self):
        self._tools = [
            MCPTool(
                name="github_read_file",
                description="Read repository file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "ref": {"type": "string", "default": ""},
                    },
                    "required": ["repo", "path"],
                },
                server_name="github",
            )
        ]

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        return "github" if tool_name == "github_read_file" else None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        assert tool_name == "github_read_file"
        return "name: Deploy Backend + Frontend\non:\n  push:\n    branches: [master]\n"


class FakeKimiMentionMCPManager:
    def __init__(self):
        self._tools = [
            MCPTool(
                name="github_search_code",
                description="Search repository code.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["repo", "query"],
                },
                server_name="github",
            ),
            MCPTool(
                name="github_read_file",
                description="Read repository file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "ref": {"type": "string", "default": ""},
                    },
                    "required": ["repo", "path"],
                },
                server_name="github",
            ),
        ]

    def get_all_tools(self) -> list[MCPTool]:
        return self._tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        return "github" if tool_name.startswith("github_") else None

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        if tool_name == "github_search_code":
            return "[]"
        if tool_name == "github_read_file":
            return "# README\n- AssemblyAI for audio analysis features.\n"
        raise AssertionError(f"Unexpected tool: {tool_name}")


class WeakRepoUsageProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "weak-repo-usage-model"
        self.display_name = "Weak Repo Usage Model"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(self, messages, tools=None, stream=True):
        yield ChatEvent(
            type=ChatEventType.TEXT_CHUNK,
            content="No results were found for STT or PTT models in the repository.",
        )
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class KimiWrongCommitCountProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "nvidia/kimi-k2"
        self.display_name = "Kimi K2"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name="github_count_commits",
                tool_args={"repo": "viseshb/Interview-Helper", "author": "GitHub"},
                tool_call_id="kimi_commit_count",
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="Answer: 0 commits.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class KimiNoToolProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "nvidia/kimi-k2"
        self.display_name = "Kimi K2"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True

    async def chat(self, messages, tools=None, stream=True):
        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="Here are some generic tables I remember.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class KimiWorkflowNameProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "nvidia/kimi-k2"
        self.display_name = "Kimi K2"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name="github_read_file",
                tool_args={"repo": "viseshb/Interview-Helper", "path": ".github/workflows/deploy.yml", "ref": ""},
                tool_call_id="kimi_workflow_name",
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="The workflow is called deploy.yml.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class KimiMentionMissProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "fake"
        self.model_id = "nvidia/kimi-k2"
        self.display_name = "Kimi K2"
        self.tier = "free"
        self.supports_tools = True
        self.supports_streaming = True
        self.call_count = 0

    async def chat(self, messages, tools=None, stream=True):
        self.call_count += 1
        if self.call_count == 1:
            yield ChatEvent(
                type=ChatEventType.TOOL_CALL,
                tool_name="github_search_code",
                tool_args={"repo": "viseshb/Interview-Helper", "query": "AssemblyAI"},
                tool_call_id="kimi_mention_search",
            )
            yield ChatEvent(type=ChatEventType.DONE)
            return

        yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content="AssemblyAI is not mentioned anywhere.")
        yield ChatEvent(type=ChatEventType.DONE)

    async def health_check(self) -> bool:
        return True


class RecordingUserService:
    def __init__(self):
        self.records: list[dict] = []

    async def record_chat_metric(self, **payload):
        self.records.append(payload)
        return payload


def reset_chat_state(monkeypatch):
    ChatService._conversation_history.clear()
    monkeypatch.setattr("app.services.chat_service.audit_logger.log_event", lambda *args, **kwargs: None)


def _registry_with(provider: LLMProvider) -> LLMRegistry:
    registry = LLMRegistry()
    registry.register(provider)
    return registry


def test_follow_up_history_is_reused_for_same_conversation_id(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = RecordingProvider()
    service = ChatService(_registry_with(provider))
    user = {"role": "viewer"}

    first = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="Which repo had the latest auth changes?",
        user=user,
        conversation_id="conv-1",
    ))
    second = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="What about the previous one?",
        user=user,
        conversation_id="conv-1",
    ))

    assert first["content"] == "reply 1"
    assert second["content"] == "reply 2"

    second_call = provider.calls[1]
    assert ("user", "Which repo had the latest auth changes?") in second_call
    assert ("assistant", "reply 1") in second_call
    assert ("user", "What about the previous one?") in second_call


def test_system_prompt_includes_current_year_follow_up_guidance_and_tool_context():
    service = ChatService(_registry_with(RecordingProvider()))
    prompt = service._build_system_prompt(
        user={
            "role": "member",
            "allowed_repos": ["acme/api"],
            "allowed_channels": ["eng-alerts"],
            "allowed_db_tables": ["public.events"],
        },
        tools=[
            MCPTool(
                name="github_get_repo_info",
                description="Get repository metadata.",
                parameters={
                    "type": "object",
                    "properties": {"repo": {"type": "string"}},
                    "required": ["repo"],
                },
                server_name="github",
            )
        ],
    )

    assert str(datetime.now().astimezone().year) in prompt
    assert "Current timestamp:" in prompt
    assert "multi-turn conversation" in prompt
    assert "Local server time:" in prompt
    assert "github_get_repo_info" in prompt
    assert "acme/api" in prompt
    assert "eng-alerts" in prompt
    assert "public.events" in prompt


def test_rest_chat_executes_tool_calls_and_tracks_context_sources(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = ToolCallingProvider()
    service = ChatService(_registry_with(provider), FakeMCPManager())
    user = {"role": "admin", "id": "1", "username": "tester"}

    result = asyncio.run(service.handle_rest_chat(
        model_id="tool-model",
        message="Give me repo info for acme/api",
        user=user,
        conversation_id="conv-tools",
    ))

    assert result["content"] == "Repo info ready."
    assert result["tool_calls"][0]["name"] == "github_get_repo_info"
    assert result["tool_calls"][0]["status"] == "success"
    assert result["context_sources"] == [{"type": "github", "detail": "acme/api"}]


def test_rest_chat_persists_turn_metrics_when_user_service_is_available(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = RecordingProvider()
    user_service = RecordingUserService()
    service = ChatService(_registry_with(provider), user_service=user_service)

    result = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="Show me the open issues in acme/api",
        user={"role": "admin", "id": "user-1", "username": "tester"},
        conversation_id="conv-persisted-metrics",
    ))

    assert result["content"] == "reply 1"
    assert len(user_service.records) == 1
    assert user_service.records[0]["user_id"] == "user-1"
    assert user_service.records[0]["conversation_id"] == "conv-persisted-metrics"
    assert user_service.records[0]["metrics"]["model_id"] == "fake-model"


def test_irrelevant_questions_are_refused_without_calling_provider(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = RecordingProvider()
    service = ChatService(_registry_with(provider))

    result = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="Tell me a joke about giraffes",
        user={"role": "viewer"},
        conversation_id="conv-off-topic",
    ))

    assert "outside this assistant's scope" in result["content"]
    assert provider.calls == []


def test_follow_up_without_domain_keywords_uses_relevant_history(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = RecordingProvider()
    service = ChatService(_registry_with(provider))
    user = {"role": "viewer"}

    first = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="List the open issues in acme/api",
        user=user,
        conversation_id="conv-follow-up",
    ))
    second = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="Only the open ones from last week",
        user=user,
        conversation_id="conv-follow-up",
    ))

    assert first["content"] == "reply 1"
    assert second["content"] == "reply 2"
    assert len(provider.calls) == 2


def test_first_person_count_follow_up_uses_relevant_history(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = RecordingProvider()
    service = ChatService(_registry_with(provider))
    user = {"role": "viewer"}

    first = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="how many commits in total are there in interview-helper repo?",
        user=user,
        conversation_id="conv-count-follow-up",
    ))
    second = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="and how many did i make?",
        user=user,
        conversation_id="conv-count-follow-up",
    ))

    assert first["content"] == "reply 1"
    assert second["content"] == "reply 2"
    assert len(provider.calls) == 2


def test_rest_chat_rejects_messages_that_exceed_limit(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = RecordingProvider()
    service = ChatService(_registry_with(provider))

    result = asyncio.run(service.handle_rest_chat(
        model_id="fake-model",
        message="x" * (settings.max_message_length + 1),
        user={"role": "viewer"},
        conversation_id="conv-too-long",
    ))

    assert result["code"] == "VALIDATION_ERROR"
    assert str(settings.max_message_length) in result["error"]
    assert provider.calls == []


def test_tool_results_are_redacted_before_second_model_turn(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = InspectingToolProvider()
    secret_payload = (
        '{"token":"ghp_1234567890abcdefghijklmnopqrstuvwxyzAB",'
        '"email":"alice@example.com",'
        '"dsn":"postgres://app:supersecretpassword@db.example.com/app"}'
    )
    service = ChatService(_registry_with(provider), FakeMCPManager(result=secret_payload))

    result = asyncio.run(service.handle_rest_chat(
        model_id="inspect-model",
        message="Give me repo info for acme/api",
        user={"role": "admin", "id": "1", "username": "tester"},
        conversation_id="conv-redaction-tool",
    ))

    assert result["content"] == "Sanitized tool result received."
    assert "ghp_" not in provider.last_tool_message
    assert "alice@example.com" not in provider.last_tool_message
    assert "supersecretpassword" not in provider.last_tool_message
    assert "[GITHUB_TOKEN_REDACTED]" in provider.last_tool_message
    assert "[EMAIL_REDACTED]" in provider.last_tool_message
    assert "[CONNECTION_URI_REDACTED]" in provider.last_tool_message


def test_final_model_output_is_redacted_before_return(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = SensitiveOutputProvider()
    service = ChatService(_registry_with(provider))

    result = asyncio.run(service.handle_rest_chat(
        model_id="sensitive-model",
        message="How does this assistant handle GitHub token exposure?",
        user={"role": "viewer", "id": "1", "username": "tester"},
        conversation_id="conv-redaction-final",
    ))

    assert "ghp_" not in result["content"]
    assert "[GITHUB_TOKEN_REDACTED]" in result["content"]


def test_tool_turn_does_not_leak_provisional_text_into_final_response(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = ToolLeakyProvider()
    service = ChatService(
        _registry_with(provider),
        FakeMCPManager(expected_args={"repo": "acme/Interview-Helper"}),
    )

    async def fake_normalize(tool_name: str, tool_args: dict):
        assert tool_name == "github_get_repo_info"
        return {"repo": "acme/Interview-Helper"}, None

    monkeypatch.setattr(ChatService, "_normalize_tool_args", staticmethod(fake_normalize))

    result = asyncio.run(service.handle_rest_chat(
        model_id="leaky-model",
        message="tell me about the Interview-Helper github repo",
        user={"role": "admin", "id": "1", "username": "tester"},
        conversation_id="conv-leaky-tool-turn",
    ))

    assert result["content"] == "Interview-Helper uses `main` as the default branch."
    assert "owner prefix" not in result["content"]
    assert "[{'type': 'text'" not in result["content"]


def test_json_function_text_is_promoted_to_tool_call(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = ImplicitToolJsonProvider()
    service = ChatService(
        _registry_with(provider),
        FakeMCPManager(expected_args={"repo": "acme/Interview-Helper"}),
    )

    async def fake_normalize(tool_name: str, tool_args: dict):
        assert tool_name == "github_get_repo_info"
        return {"repo": "acme/Interview-Helper"}, None

    monkeypatch.setattr(ChatService, "_normalize_tool_args", staticmethod(fake_normalize))

    result = asyncio.run(service.handle_rest_chat(
        model_id="implicit-tool-model",
        message="tell me about the Interview-Helper github repo",
        user={"role": "admin", "id": "1", "username": "tester"},
        conversation_id="conv-implicit-tool-turn",
    ))

    assert result["content"] == "Implicit tool call succeeded."
    assert result["tool_calls"][0]["name"] == "github_get_repo_info"


def test_bare_json_function_text_is_promoted_to_tool_call(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = BareJsonToolProvider()
    service = ChatService(
        _registry_with(provider),
        FakeMCPManager(expected_args={"repo": "acme/Interview-Helper"}),
    )

    async def fake_normalize(tool_name: str, tool_args: dict):
        assert tool_name == "github_get_repo_info"
        return {"repo": "acme/Interview-Helper"}, None

    monkeypatch.setattr(ChatService, "_normalize_tool_args", staticmethod(fake_normalize))

    result = asyncio.run(service.handle_rest_chat(
        model_id="bare-json-tool-model",
        message="tell me about the Interview-Helper github repo",
        user={"role": "admin", "id": "1", "username": "tester"},
        conversation_id="conv-bare-json-tool-turn",
    ))

    assert result["content"] == "Bare JSON tool call succeeded."
    assert result["tool_calls"][0]["name"] == "github_get_repo_info"


def test_first_person_commit_queries_infer_signed_in_username():
    inferred = ChatService._infer_user_tool_args(
        "github_count_commits",
        {"repo": "viseshb/Interview-Helper", "author": "k-lewis-dev"},
        {"username": "viseshb"},
        "can you tell me how many commits i made in interview-helper repo?",
    )

    assert inferred["author"] == "viseshb"


def test_first_person_commit_queries_preserve_explicit_named_author():
    inferred = ChatService._infer_user_tool_args(
        "github_count_commits",
        {"repo": "viseshb/Interview-Helper", "author": "k-lewis-dev"},
        {"username": "viseshb"},
        "can you tell me how many commits i made as k-lewis-dev in interview-helper repo?",
    )

    assert inferred["author"] == "k-lewis-dev"


def test_non_first_person_commit_queries_clear_hallucinated_author():
    inferred = ChatService._infer_user_tool_args(
        "github_count_commits",
        {"repo": "viseshb/Interview-Helper", "author": "viseshb"},
        {"username": "viseshb"},
        "can you tell me how many commits are there in interview-helper repo?",
    )

    assert "author" not in inferred


def test_live_github_count_questions_fallback_to_tools_when_model_hallucinates(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = HallucinatedMetricsProvider()
    service = ChatService(_registry_with(provider), FakeMetricsMCPManager())

    result = asyncio.run(service.handle_rest_chat(
        model_id="hallucinated-metrics-model",
        message="can you tell me how many commits, pr's, Deployment workflows are there in my repo Interview-helper?",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        conversation_id="conv-hallucinated-metrics",
    ))

    assert "637 commits" in result["content"]
    assert "1 deployment workflow" in result["content"]
    assert result["tool_calls"][0]["name"] == "github_get_repo_metrics"


def test_repo_model_usage_fallback_reads_readme_when_model_claims_no_results(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = WeakRepoUsageProvider()
    service = ChatService(_registry_with(provider), FakeRepoUsageMCPManager())
    monkeypatch.setattr(
        ChatService,
        "_normalize_tool_args",
        staticmethod(lambda tool_name, tool_args: asyncio.sleep(0, result=(tool_args, None))),
    )

    result = asyncio.run(service.handle_rest_chat(
        model_id="weak-repo-usage-model",
        message="i am not able to find the models used in interview-helper repo for stt and also for ptt?",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        conversation_id="conv-repo-usage-fallback",
    ))

    assert "Deepgram Flux/Nova" in result["content"]
    assert "AssemblyAI Universal-3 Pro" in result["content"]
    assert "PTT" in result["content"]
    assert any(tool["name"] == "github_read_file" for tool in result["tool_calls"])


def test_repo_inference_ignores_repo_for_stopword_pattern():
    inferred = ChatService._infer_repo_from_message(
        "i am not able to find the models used in interview-helper repo for stt and also for ptt?"
    )

    assert inferred == "interview-helper"


def test_kimi_db_identifier_request_recognizes_snake_case_table_prompt():
    assert ChatService._is_kimi_db_identifier_request(
        "Which service has the highest average CPU usage in system_metrics?"
    )


def test_kimi_table_listing_override_does_not_hijack_non_inventory_db_question():
    service = ChatService(_registry_with(RecordingProvider()))
    result = asyncio.run(service._format_kimi_table_listing_answer(
        message="What is the most recently updated repo in the github_repos database table?",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        context_sources=[],
        context_source_keys=set(),
        tool_calls=[],
    ))

    assert result is None


def test_kimi_commit_count_strips_fake_source_author_and_grounds_answer(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = KimiWrongCommitCountProvider()
    service = ChatService(_registry_with(provider), FakeKimiCommitMCPManager())

    monkeypatch.setattr(
        ChatService,
        "_normalize_tool_args",
        staticmethod(lambda tool_name, tool_args: asyncio.sleep(0, result=(tool_args, None))),
    )

    result = asyncio.run(service.handle_rest_chat(
        model_id="nvidia/kimi-k2",
        message="How many commits in total are there in Interview-Helper repo from GitHub?",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        conversation_id="conv-kimi-commit-grounding",
    ))

    assert "637" in result["content"]
    assert "0 commits" not in result["content"]
    assert result["tool_calls"][0]["args"] == {"repo": "viseshb/Interview-Helper"}


def test_kimi_table_listing_falls_back_to_db_tool_when_model_skips_tools(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = KimiNoToolProvider()
    service = ChatService(_registry_with(provider), FakeKimiDbTablesMCPManager())

    result = asyncio.run(service.handle_rest_chat(
        model_id="nvidia/kimi-k2",
        message="List the PostgreSQL tables available in this app.",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        conversation_id="conv-kimi-db-tables",
    ))

    assert "public.deployments" in result["content"]
    assert "public.incidents" in result["content"]
    assert any(tool["name"] == "db_list_tables" for tool in result["tool_calls"])


def test_kimi_workflow_name_is_grounded_from_workflow_file(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = KimiWorkflowNameProvider()
    service = ChatService(_registry_with(provider), FakeKimiWorkflowMCPManager())

    monkeypatch.setattr(
        ChatService,
        "_normalize_tool_args",
        staticmethod(lambda tool_name, tool_args: asyncio.sleep(0, result=(tool_args, None))),
    )

    result = asyncio.run(service.handle_rest_chat(
        model_id="nvidia/kimi-k2",
        message="What is the deployment workflow called in interview-helper repo?",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        conversation_id="conv-kimi-workflow-name",
    ))

    assert "Deploy Backend + Frontend" in result["content"]
    assert "deploy.yml" not in result["content"].split("**")[-1]


def test_kimi_repo_mention_search_falls_back_to_readme_when_code_search_is_empty(monkeypatch):
    reset_chat_state(monkeypatch)
    provider = KimiMentionMissProvider()
    service = ChatService(_registry_with(provider), FakeKimiMentionMCPManager())

    monkeypatch.setattr(
        ChatService,
        "_normalize_tool_args",
        staticmethod(lambda tool_name, tool_args: asyncio.sleep(0, result=(tool_args, None))),
    )

    result = asyncio.run(service.handle_rest_chat(
        model_id="nvidia/kimi-k2",
        message="Find where AssemblyAI is mentioned in interview-helper repo.",
        user={"role": "admin", "id": "1", "username": "viseshb"},
        conversation_id="conv-kimi-readme-mention",
    ))

    assert "README.md" in result["content"]
    assert "AssemblyAI" in result["content"]
