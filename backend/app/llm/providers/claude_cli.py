"""Claude CLI provider — spawns claude as subprocess using pipe mode.

Mirrors the approach from llm_call.js:
  cmd.exe /c claude -p --output-format json --max-turns 1
  --no-session-persistence --tools "" --effort high
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import AsyncIterator

from app.config import settings
from app.llm.base import (
    ChatEvent, ChatEventType, LLMProvider, Message, ToolDefinition,
)
from app.utils.logging import get_logger

log = get_logger("llm.claude_cli")

CLI_TIMEOUT_SECONDS = 120


class ClaudeCLIProvider(LLMProvider):
    def __init__(self):
        self.provider_name = "claude-cli"
        self.model_id = "claude-cli"
        self.display_name = "Claude CLI"
        self.tier = "free"
        self.supports_tools = False  # prompt-based, no native tool calling
        self.supports_streaming = True

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        cli_path = settings.claude_cli_path or "claude"

        # Build prompt from messages
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(msg.content)
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
            elif msg.role == "tool":
                prompt_parts.append(f"Tool result ({msg.tool_name}): {msg.content}")

        # Add tool descriptions to prompt if available
        if tools:
            tool_desc = "\n".join(
                f"- {t.name}: {t.description} (params: {json.dumps(t.parameters)})"
                for t in tools
            )
            prompt_parts.insert(0,
                f"You have access to these tools:\n{tool_desc}\n"
                "To call a tool, respond with: <tool_call name=\"tool_name\">{\"arg\": \"value\"}</tool_call>"
            )

        prompt = "\n\n".join(prompt_parts)

        # Build command — matches llm_call.js approach
        # On Windows use cmd.exe /c, on Unix call directly
        if sys.platform == "win32":
            cmd = ["cmd.exe", "/c", cli_path]
        else:
            cmd = [cli_path]

        cmd.extend([
            "-p",                           # pipe mode (non-interactive)
            "--output-format", "json",      # structured output with usage stats
            "--max-turns", "1",             # single turn, no back-and-forth
            "--no-session-persistence",     # one-shot, no resume state
        ])

        log.info("claude_cli_start", cli_path=cli_path, prompt_len=len(prompt))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=CLI_TIMEOUT_SECONDS,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            if stderr:
                log.warning("claude_cli_stderr", stderr=stderr[:500])

            if not stdout:
                log.error("claude_cli_empty_output", exit_code=proc.returncode, stderr=stderr[:300])
                yield ChatEvent(
                    type=ChatEventType.ERROR,
                    error=f"Claude CLI returned no output (exit code {proc.returncode})",
                )
                return

            # Try to parse as JSON (--output-format json)
            try:
                parsed = json.loads(stdout)
                text = parsed.get("result") or parsed.get("text") or ""
                usage = parsed.get("usage", {})
                cost = parsed.get("total_cost_usd", 0)
                model_used = list(parsed.get("modelUsage", {}).keys())

                log.info(
                    "claude_cli_success",
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cost_usd=cost,
                    model=model_used[0] if model_used else "unknown",
                )

                if text:
                    yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content=text)
                else:
                    log.warning("claude_cli_no_text", keys=list(parsed.keys()))
                    yield ChatEvent(
                        type=ChatEventType.TEXT_CHUNK,
                        content=stdout,  # fallback: return raw output
                    )

            except json.JSONDecodeError:
                # CLI didn't return JSON — return raw text
                log.warning("claude_cli_non_json_output", output_len=len(stdout))
                yield ChatEvent(type=ChatEventType.TEXT_CHUNK, content=stdout)

            yield ChatEvent(type=ChatEventType.DONE)

        except asyncio.TimeoutError:
            log.error("claude_cli_timeout", timeout_s=CLI_TIMEOUT_SECONDS)
            yield ChatEvent(
                type=ChatEventType.ERROR,
                error=f"Claude CLI timed out after {CLI_TIMEOUT_SECONDS}s",
            )
        except FileNotFoundError:
            log.error("claude_cli_not_found", path=cli_path)
            yield ChatEvent(
                type=ChatEventType.ERROR,
                error=f"Claude CLI not found at '{cli_path}'. Set CLAUDE_CLI_PATH in .env",
            )
        except Exception as e:
            log.error("claude_cli_error", error=str(e), error_type=type(e).__name__)
            yield ChatEvent(type=ChatEventType.ERROR, error=f"Claude CLI error: {e}")

    async def health_check(self) -> bool:
        cli_path = settings.claude_cli_path or "claude"
        try:
            if sys.platform == "win32":
                cmd = ["cmd.exe", "/c", cli_path, "--version"]
            else:
                cmd = [cli_path, "--version"]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            ok = proc.returncode == 0
            if ok:
                log.info("claude_cli_healthy", version=stdout.decode().strip()[:50])
            else:
                log.warning("claude_cli_unhealthy", exit_code=proc.returncode)
            return ok
        except Exception as e:
            log.warning("claude_cli_health_failed", error=str(e))
            return False
