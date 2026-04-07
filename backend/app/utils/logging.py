"""Pretty, colored structured logging with rich terminal output."""
from __future__ import annotations

import logging
import sys

import structlog
from rich.console import Console
from rich.theme import Theme

from app.config import settings

# Custom theme for log levels
_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "debug": "dim",
})

_console = Console(theme=_theme, stderr=True)


def _rich_renderer(logger, name, event_dict):
    """Custom renderer that uses rich for pretty colored output."""
    level = event_dict.pop("level", "info")
    ts = event_dict.pop("timestamp", "")
    event = event_dict.pop("event", "")

    # Color the level badge
    level_colors = {
        "debug": "[dim]DBG[/dim]",
        "info": "[cyan bold]INF[/cyan bold]",
        "warning": "[yellow bold]WRN[/yellow bold]",
        "error": "[red bold]ERR[/red bold]",
        "critical": "[white on red bold]CRT[/white on red bold]",
    }
    level_badge = level_colors.get(level, f"[bold]{level.upper()[:3]}[/bold]")

    # Format timestamp (short)
    short_ts = ts[11:19] if len(ts) > 19 else ts

    # Format extra key=value pairs
    extras = ""
    if event_dict:
        parts = []
        for k, v in event_dict.items():
            if k.startswith("_"):
                continue
            parts.append(f"[dim]{k}=[/dim][white]{v}[/white]")
        extras = " " + " ".join(parts) if parts else ""

    # Color the event message based on content
    if "error" in event.lower() or "fail" in event.lower():
        event_str = f"[red]{event}[/red]"
    elif "success" in event.lower() or "ready" in event.lower() or "initialized" in event.lower():
        event_str = f"[green]{event}[/green]"
    elif "warning" in event.lower() or "missing" in event.lower():
        event_str = f"[yellow]{event}[/yellow]"
    else:
        event_str = f"[white]{event}[/white]"

    _console.print(f"[dim]{short_ts}[/dim] {level_badge} {event_str}{extras}", highlight=False)
    return ""


def setup_logging() -> None:
    """Configure structlog with pretty rich console output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            _rich_renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy uvicorn access logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
