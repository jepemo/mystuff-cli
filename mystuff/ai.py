"""Provider-aware agent command resolution shared by MyStuff workflows."""

from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class AgentRunnerError(RuntimeError):
    """Raised when an external agent cannot complete a task."""


@dataclass(frozen=True)
class AgentSettings:
    provider: str
    command: List[str]
    model: Optional[str] = None
    profile: Optional[str] = None
    reasoning_effort: Optional[str] = None


def load_mystuff_config(mystuff_dir: Path) -> Dict[str, Any]:
    config_path = mystuff_dir / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise AgentRunnerError(f"Could not load {config_path}: {exc}") from exc
    if not isinstance(config, dict):
        raise AgentRunnerError(f"Expected a mapping in {config_path}")
    return config


def _command_list(value: Any) -> List[str]:
    if value is None:
        return ["codex"]
    if isinstance(value, str):
        return shlex.split(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise AgentRunnerError("Agent command must be a string or a list of strings")


def resolve_agent_settings(
    task: str,
    mystuff_dir: Path,
    *,
    command_override: Optional[str] = None,
) -> AgentSettings:
    config = load_mystuff_config(mystuff_dir)
    ai_config = config.get("ai") or {}
    if not isinstance(ai_config, dict):
        raise AgentRunnerError("config.yaml field 'ai' must be a mapping")

    tasks = ai_config.get("tasks") or {}
    task_config = tasks.get(task) or {}
    if not isinstance(task_config, dict):
        raise AgentRunnerError(f"AI task configuration for {task!r} must be a mapping")

    provider = str(
        task_config.get("provider") or ai_config.get("default_provider") or "codex"
    )
    providers = ai_config.get("providers") or {}
    provider_config = providers.get(provider) or {}
    if not isinstance(provider_config, dict):
        raise AgentRunnerError(f"AI provider configuration for {provider!r} is invalid")

    if provider != "codex":
        raise AgentRunnerError(
            f"AI provider {provider!r} is configured but not implemented; "
            "currently supported: codex"
        )

    if command_override:
        command = _command_list(command_override)
    else:
        command = _command_list(provider_config.get("command"))
    if not command:
        raise AgentRunnerError("Agent command cannot be empty")

    model = task_config.get("model", provider_config.get("model"))
    profile = task_config.get("profile", provider_config.get("profile"))
    reasoning_effort = task_config.get(
        "reasoning_effort", provider_config.get("reasoning_effort")
    )
    return AgentSettings(
        provider=provider,
        command=command,
        model=str(model) if model else None,
        profile=str(profile) if profile else None,
        reasoning_effort=str(reasoning_effort) if reasoning_effort else None,
    )


def build_codex_exec_command(
    settings: AgentSettings,
    prompt: str,
    *,
    cwd: Path,
    output_schema: Optional[Path] = None,
    output_path: Optional[Path] = None,
    read_only: bool = False,
    ephemeral: bool = False,
) -> List[str]:
    command = list(settings.command) + ["exec"]
    if settings.model:
        command.extend(["--model", settings.model])
    if settings.profile:
        command.extend(["--profile", settings.profile])
    if settings.reasoning_effort:
        command.extend(
            ["--config", f'model_reasoning_effort="{settings.reasoning_effort}"']
        )
    if read_only:
        command.extend(["--sandbox", "read-only"])
    if ephemeral:
        command.append("--ephemeral")
    command.extend(["--cd", str(cwd)])
    if output_schema:
        command.extend(["--output-schema", str(output_schema)])
    if output_path:
        command.extend(["--output-last-message", str(output_path)])
    command.append(prompt)
    return command


def run_structured_agent(
    task: str,
    prompt: str,
    schema: Dict[str, Any],
    *,
    mystuff_dir: Path,
    command_override: Optional[str] = None,
) -> Dict[str, Any]:
    settings = resolve_agent_settings(
        task, mystuff_dir, command_override=command_override
    )
    with tempfile.TemporaryDirectory(prefix="mystuff-agent-") as temp_dir:
        temp = Path(temp_dir)
        schema_path = temp / "schema.json"
        output_path = temp / "result.json"
        schema_path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        command = build_codex_exec_command(
            settings,
            prompt,
            cwd=mystuff_dir,
            output_schema=schema_path,
            output_path=output_path,
            read_only=True,
            ephemeral=True,
        )
        error_path = temp / "agent.stderr.log"
        try:
            with open(error_path, "w", encoding="utf-8") as error_handle:
                result = subprocess.run(
                    command,
                    cwd=mystuff_dir,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=error_handle,
                )
        except FileNotFoundError as exc:
            raise AgentRunnerError(f"Agent command not found: {command[0]}") from exc
        if result.returncode:
            details = error_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            raise AgentRunnerError(
                f"Agent command failed with exit code {result.returncode}"
                + (f":\n{details}" if details else "")
            )

        if not output_path.exists():
            raise AgentRunnerError("Agent did not produce a structured result")
        try:
            value = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentRunnerError(f"Agent returned invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise AgentRunnerError("Agent result must be a JSON object")
        return value
