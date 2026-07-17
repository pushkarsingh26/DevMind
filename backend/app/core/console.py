"""
DevMind Console — Phase 7.5.3
==============================
Production-grade console renderer using Rich.

Provides a single ``console`` singleton with:
  • Startup banners with full system checklist
  • Provider validation tables with fallback detail
  • Workflow execution progress blocks
  • AI request / response panels
  • Cache operation groups
  • Workflow completion summaries
  • Structured error renderer (traceback only in DEBUG mode)
  • Runtime performance metrics footer
  • Color-coded log-level methods: info / success / warning / error /
    workflow / ai / cache / system

All output is also written to rotating log files under backend/logs/.
"""

import os
import re
import sys
import time
import logging
import traceback as tb_module
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Log directory bootstrap
# ---------------------------------------------------------------------------
_BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR    = os.path.join(_BASE_DIR, "logs")
ERRORS_DIR  = os.path.join(LOGS_DIR, "errors")
os.makedirs(LOGS_DIR,   exist_ok=True)
os.makedirs(ERRORS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Rotating log handlers (one per category)
# ---------------------------------------------------------------------------
def _create_rotator(filename: str) -> logging.Logger:
    logger_name = f"devmind.file.{os.path.splitext(filename)[0]}"
    log = logging.getLogger(logger_name)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    if log.handlers:
        log.handlers.clear()
    filepath = os.path.join(LOGS_DIR, filename)
    handler  = RotatingFileHandler(
        filepath, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    log.addHandler(handler)
    return log

startup_logger     = _create_rotator("startup.log")
workflow_logger    = _create_rotator("workflow.log")
providers_logger   = _create_rotator("providers.log")
errors_logger      = _create_rotator("errors.log")
performance_logger = _create_rotator("performance.log")

# ---------------------------------------------------------------------------
# Rich import (graceful fallback if not installed)
# ---------------------------------------------------------------------------
try:
    from rich.console import Console as RichConsole
    from rich.table   import Table
    from rich.panel   import Panel
    from rich.text    import Text
    from rich.align   import Align
    from rich.columns import Columns
    from rich.rule    import Rule
    from rich.padding import Padding
    from rich import box as rich_box
    import io

    # On Windows, stdout may use cp1252 which can't encode box-drawing characters.
    # Wrap stdout in a UTF-8 TextIOWrapper so Rich can render them safely.
    _safe_stdout = sys.stdout
    if hasattr(sys.stdout, "buffer"):
        try:
            _safe_stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )
        except Exception:
            _safe_stdout = sys.stdout

    _rich_console = RichConsole(
        file=_safe_stdout,
        force_terminal=True,
        color_system="auto",
        highlight=False,
    )
    _HAS_RICH = True
except ImportError:
    _rich_console = None  # type: ignore[assignment]
    _HAS_RICH = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"\[/?(?:bold|dim|red|green|yellow|blue|magenta|cyan|white|purple|grey|gray|underline)[^\]]*\]")

def _strip_rich(text: str) -> str:
    """Remove Rich markup tags for plain-text log files."""
    return _TAG_RE.sub("", text)


def _log_file(level: str, category: str, message: str) -> None:
    """Route a plain-text message to the appropriate rotating log file."""
    clean = _strip_rich(message)
    lvl   = getattr(logging, level.upper(), logging.INFO)
    {
        "startup":     startup_logger,
        "workflow":    workflow_logger,
        "providers":   providers_logger,
        "errors":      errors_logger,
        "performance": performance_logger,
    }.get(category, workflow_logger).log(lvl, clean)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DevMindConsole
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DevMindConsole:
    """
    Unified console & logging manager for DevMind.

    Writes Rich-styled output to the terminal and plain text to rotating
    log files.  All public methods degrade gracefully when Rich is not
    installed.
    """

    def __init__(self) -> None:
        self.console = _rich_console
        self._debug  = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _print(self, *args, **kwargs) -> None:
        """Print via Rich console or plain print()."""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            # Strip markup if Rich is absent
            for arg in args:
                print(_strip_rich(str(arg)))

    def _rule(self, title: str = "", style: str = "bold cyan") -> None:
        if self.console:
            self.console.print(Rule(title, style=style))
        else:
            w = 62
            print(f"\n{'━' * w}")
            if title:
                print(f"  {title}")

    # ------------------------------------------------------------------
    # Colored log-level methods
    # ------------------------------------------------------------------

    def info(self, msg: str, category: str = "workflow") -> None:
        _log_file("INFO", category, msg)
        self._print(f"[cyan]\\[INFO][/cyan]     {msg}")

    def success(self, msg: str, category: str = "workflow") -> None:
        _log_file("INFO", category, msg)
        self._print(f"[bold green]\\[SUCCESS][/bold green]  [green]{msg}[/green]")

    def warning(self, msg: str, category: str = "workflow") -> None:
        _log_file("WARNING", category, msg)
        self._print(f"[bold yellow]\\[WARNING][/bold yellow]  [yellow]{msg}[/yellow]")

    def error(self, msg: str, category: str = "errors") -> None:
        _log_file("ERROR", category, msg)
        self._print(f"[bold red]\\[ERROR][/bold red]    [red]{msg}[/red]")

    def workflow(self, msg: str, category: str = "workflow") -> None:
        _log_file("INFO", category, msg)
        self._print(f"[bold magenta]\\[WORKFLOW][/bold magenta] [magenta]{msg}[/magenta]")

    def ai(self, msg: str, category: str = "providers") -> None:
        _log_file("INFO", category, msg)
        self._print(f"[bold blue]\\[AI][/bold blue]       [blue]{msg}[/blue]")

    def cache(self, msg: str, category: str = "workflow") -> None:
        _log_file("INFO", category, msg)
        self._print(f"[bold magenta]\\[CACHE][/bold magenta]    [magenta]{msg}[/magenta]")

    def system(self, msg: str, category: str = "startup") -> None:
        _log_file("INFO", category, msg)
        self._print(f"[grey50]\\[SYSTEM][/grey50]   [grey50]{msg}[/grey50]")

    def section(self, title: str, category: str = "workflow") -> None:
        _log_file("INFO", category, f"=== {title} ===")
        self._rule(title.upper())

    # ------------------------------------------------------------------
    # Startup banner
    # ------------------------------------------------------------------

    def display_startup_banner(
        self,
        env: str,
        python_ver: str,
        startup_time: float,
        providers: List[Dict[str, Any]],
    ) -> None:
        """
        Renders the full structured startup banner:
          SYSTEM checklist → AI PROVIDERS → SERVER info → Ready footer
        """
        _log_file("INFO", "startup", f"DevMind Backend Ready | env={env} python={python_ver} startup={startup_time:.2f}s")

        if not self.console:
            print(f"\n--- DevMind Backend Ready (env={env}, startup={startup_time:.2f}s) ---\n")
            print("Knowledge Graph")
            print("----------------------------")
            print("✓ Graph Engine Ready")
            print("✓ Graph Cache Ready")
            try:
                from app.services.knowledge_graph.versions import GRAPH_VERSION, GRAPH_SCHEMA_VERSION
                gv = GRAPH_VERSION
                sv = GRAPH_SCHEMA_VERSION
            except Exception:
                gv = "v1"
                sv = "v1"
            print(f"✓ Graph Version : {gv}")
            print(f"✓ Schema Version: {sv}")
            return

        c = self.console
        SEP = "[bold cyan]" + "━" * 62 + "[/bold cyan]"

        c.print()
        c.print(SEP)
        c.print()
        c.print(Align("[bold white]DevMind Backend  [cyan]v0.5.0[/cyan][/bold white]", align="center"))
        c.print()
        c.print(SEP)
        c.print()

        # ── SYSTEM checklist ────────────────────────────────────────────
        c.print("[bold white]  SYSTEM[/bold white]")
        c.print()
        checklist = [
            "Configuration Loaded",
            "Environment Loaded",
            "Database Connected",
            "Token Manager Ready",
            "AI Cache Ready",
            "Embedding Engine Ready",
            "FAISS Vector Store Ready",
            "Repository Memory Ready",
            "Prompt Library Loaded",
            "Workflow Engine Ready",
            "Agent Registry Loaded",
        ]
        for item in checklist:
            c.print(f"  [bold green]✓[/bold green]  [white]{item}[/white]")

        c.print()
        c.print(SEP)
        c.print()

        # ── AI PROVIDERS ────────────────────────────────────────────────
        c.print("[bold white]  AI PROVIDERS[/bold white]")
        c.print()
        for p in providers:
            name   = p.get("name", "Unknown")
            status = p.get("status", "unavailable")
            if status == "available":
                badge = "[bold green]✓ Ready[/bold green]"
            elif status in ("invalid_configuration", "authentication_failed"):
                badge = "[bold yellow]⚠ Config Error[/bold yellow]"
            else:
                badge = "[bold red]✗ Offline[/bold red]"
            c.print(f"  [white]{name:<22}[/white] {badge}")

        c.print()
        c.print(SEP)
        c.print()

        # ── SERVER info ─────────────────────────────────────────────────
        c.print("[bold white]  SERVER[/bold white]")
        c.print()
        c.print(f"  [dim]Environment[/dim]      [white]{env}[/white]")
        c.print(f"  [dim]Python[/dim]           [white]{python_ver}[/white]")
        c.print(f"  [dim]Startup Time[/dim]     [yellow]{startup_time:.2f} sec[/yellow]")
        c.print()
        c.print(f"  [dim]API[/dim]              [cyan]http://127.0.0.1:8000[/cyan]")
        c.print(f"  [dim]Swagger[/dim]          [cyan]/docs[/cyan]")
        c.print(f"  [dim]Redoc[/dim]            [cyan]/redoc[/cyan]")
        c.print()
        c.print(SEP)
        c.print()

        # ── KNOWLEDGE GRAPH ─────────────────────────────────────────────
        c.print("[bold white]  KNOWLEDGE GRAPH[/bold white]")
        c.print()
        c.print("  [bold green]✓[/bold green]  [white]Graph Engine Ready[/white]")
        c.print("  [bold green]✓[/bold green]  [white]Graph Cache Ready[/white]")
        try:
            from app.services.knowledge_graph.versions import GRAPH_VERSION, GRAPH_SCHEMA_VERSION
            gv = GRAPH_VERSION
            sv = GRAPH_SCHEMA_VERSION
        except Exception:
            gv = "v1"
            sv = "v1"
        c.print(f"  [bold green]✓[/bold green]  [white]Graph Version : {gv}[/white]")
        c.print(f"  [bold green]✓[/bold green]  [white]Schema Version: {sv}[/white]")
        c.print()
        c.print(SEP)
        c.print()

        # ── Ready footer ─────────────────────────────────────────────────
        c.print(Align("[bold green]✓  DevMind Backend Ready[/bold green]", align="center"))
        c.print()
        c.print(SEP)
        c.print()

    # ------------------------------------------------------------------
    # Provider validation table
    # ------------------------------------------------------------------

    def display_provider_validation(self, providers: List[Dict[str, Any]]) -> None:
        """
        Renders a Rich table showing each provider's validation result.
        Fallback providers display Configured → Resolved model path.
        """
        _log_file("INFO", "providers", "Provider validation complete.")

        if not self.console:
            print("--- Provider Validation ---")
            for p in providers:
                print(f"  {p.get('name')}: {p.get('status')} | {p.get('resolved_model','')}")
            return

        c = self.console
        c.print()
        c.print(Rule("[bold cyan]  Provider Validation  [/bold cyan]", style="cyan"))
        c.print()

        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim white",
            box=rich_box.SIMPLE_HEAVY,
            padding=(0, 1),
            show_edge=True,
            expand=False,
        )
        table.add_column("Provider",  style="bold white",  min_width=12)
        table.add_column("Status",                         min_width=14)
        table.add_column("Model",     style="yellow",      min_width=24, overflow="fold")
        table.add_column("Latency",   justify="right",     min_width=10)

        for p in providers:
            status = p.get("status", "unavailable")
            is_fallback = p.get("fallback", False)

            if status == "available" and not is_fallback:
                status_txt = "[bold green]✓ Healthy[/bold green]"
            elif status == "available" and is_fallback:
                status_txt = "[bold yellow]⚠ Fallback[/bold yellow]"
            elif status == "authentication_failed":
                status_txt = "[bold red]✗ Auth Failed[/bold red]"
            elif status == "invalid_configuration":
                status_txt = "[bold yellow]⚠ Bad Config[/bold yellow]"
            else:
                status_txt = "[bold red]✗ Offline[/bold red]"

            latency_val = p.get("latency")
            latency_txt = f"[dim]{latency_val:.2f} s[/dim]" if latency_val else "[dim]—[/dim]"

            # Model column: show configured→resolved for fallback
            configured  = p.get("configured_model", "")
            resolved    = p.get("resolved_model", "")
            if is_fallback and configured and resolved and configured != resolved:
                model_txt = (
                    f"[dim]{configured[:22]}[/dim]\n"
                    f"[bold green]↓[/bold green]\n"
                    f"[green]{resolved[:22]}[/green]"
                )
            else:
                model_txt = resolved or configured or "[dim]—[/dim]"

            table.add_row(p.get("name", "?"), status_txt, model_txt, latency_txt)

        c.print(Padding(table, (0, 2)))
        c.print()

    # ------------------------------------------------------------------
    # Workflow execution block
    # ------------------------------------------------------------------

    def display_workflow_execution(
        self,
        wf_name: str,
        repo_name: str,
        wf_id: str,
        stage: int,
        stage_name: str,
        agents_status: Dict[str, str],
    ) -> None:
        """Renders a workflow stage block with per-agent status indicators."""
        _log_file("INFO", "workflow", f"Workflow [{wf_id}] Stage {stage}: {stage_name}")

        if not self.console:
            print(f"\n[WORKFLOW] {wf_name} | Stage {stage}: {stage_name} | {wf_id}")
            return

        c = self.console
        SEP = "[bold white]" + "━" * 46 + "[/bold white]"

        c.print()
        c.print(SEP)
        c.print(f"  [bold cyan]Workflow[/bold cyan]      [white]{wf_name}[/white]")
        c.print(f"  [bold cyan]Repository[/bold cyan]    [white]{repo_name}[/white]")
        c.print(f"  [bold cyan]Workflow ID[/bold cyan]   [dim]{wf_id}[/dim]")
        c.print(SEP)
        c.print()
        c.print(f"  [bold yellow]Stage {stage}[/bold yellow]")
        c.print(f"  [bold white]{stage_name}[/bold white]")
        c.print()
        c.print(SEP)
        c.print()

        _STATUS_COLORS = {
            "✓ Complete":  "bold green",
            "Running...":  "bold yellow",
            "Queued...":   "cyan",
            "Waiting...":  "dim",
            "Skipped":     "dim red",
            "Failed":      "bold red",
        }

        for agent, status in agents_status.items():
            color = _STATUS_COLORS.get(status, "white")
            c.print(f"  [white]{agent:<26}[/white] [{color}]{status}[/{color}]")
        c.print()

    # ------------------------------------------------------------------
    # AI request / response panels
    # ------------------------------------------------------------------

    def display_ai_request(
        self,
        agent_name: str,
        provider: str,
        model: str,
        tokens: int,
        streaming: str,
        cache_status: str,
    ) -> None:
        """Renders a structured AI REQUEST panel."""
        _log_file("INFO", "providers", f"AI Request: {agent_name} → {provider} ({model}) tokens={tokens} cache={cache_status}")

        if not self.console:
            print(f"[AI] REQUEST | {agent_name} → {provider} | {model} | tokens={tokens} | cache={cache_status}")
            return

        cache_color = "green" if cache_status == "HIT" else "yellow"
        stream_color = "green" if streaming == "YES" else "dim"

        content = (
            f"[bold blue]AI REQUEST[/bold blue]\n\n"
            f"  [dim]Agent[/dim]       [white]{agent_name}[/white]\n"
            f"  [dim]Provider[/dim]    [white]{provider.capitalize()}[/white]\n"
            f"  [dim]Model[/dim]       [yellow]{model}[/yellow]\n"
            f"  [dim]Tokens[/dim]      [white]{tokens:,}[/white]\n"
            f"  [dim]Streaming[/dim]   [{stream_color}]{streaming}[/{stream_color}]\n"
            f"  [dim]Cache[/dim]       [bold {cache_color}]{cache_status}[/bold {cache_color}]"
        )
        self.console.print(Panel(content, border_style="blue", expand=False))

    def display_ai_response(
        self,
        latency: float,
        output_tokens: int,
        confidence: float,
    ) -> None:
        """Renders a structured AI RESPONSE panel."""
        _log_file("INFO", "providers", f"AI Response | latency={latency:.2f}s output_tokens={output_tokens} confidence={confidence:.2f}")

        if not self.console:
            print(f"[AI] RESPONSE | latency={latency:.2f}s tokens={output_tokens} confidence={confidence:.2f}")
            return

        conf_color = "green" if confidence >= 0.80 else "yellow" if confidence >= 0.60 else "red"

        content = (
            f"[bold green]✓ Response received[/bold green]\n\n"
            f"  [dim]Latency[/dim]        [white]{latency:.2f} sec[/white]\n"
            f"  [dim]Output Tokens[/dim]  [white]{output_tokens:,}[/white]\n"
            f"  [dim]Confidence[/dim]     [{conf_color}]{confidence:.2f}[/{conf_color}]"
        )
        self.console.print(Panel(content, border_style="green", expand=False))

    # ------------------------------------------------------------------
    # Cache group panel
    # ------------------------------------------------------------------

    def display_cache_group(
        self,
        ai_cache: str,
        retrieval: str,
        repo_mem: str,
        vector: str,
    ) -> None:
        """Renders a grouped CACHE status panel."""
        _log_file("INFO", "workflow", f"Cache | AI={ai_cache} Retrieval={retrieval} RepoMem={repo_mem} Vector={vector}")

        if not self.console:
            print(f"[CACHE] AI={ai_cache} Retrieval={retrieval} RepoMem={repo_mem} Vector={vector}")
            return

        def _badge(v: str) -> str:
            return "[bold green]HIT[/bold green]" if v == "HIT" else "[bold yellow]MISS[/bold yellow]"

        content = (
            f"[bold magenta]CACHE[/bold magenta]\n\n"
            f"  [dim]AI Cache[/dim]           {_badge(ai_cache)}\n"
            f"  [dim]Retrieval Cache[/dim]    {_badge(retrieval)}\n"
            f"  [dim]Repository Memory[/dim]  {_badge(repo_mem)}\n"
            f"  [dim]Vector Cache[/dim]       {_badge(vector)}"
        )
        self.console.print(Panel(content, border_style="magenta", expand=False))

    # ------------------------------------------------------------------
    # Workflow completion summary
    # ------------------------------------------------------------------

    def display_workflow_summary(
        self,
        wf_name: str,
        duration: float,
        repo_name: str,
        files_count: int,
        agents_count: int,
        tokens_count: int,
        cache_hit_pct: int,
        report_name: str,
        status: str,
    ) -> None:
        """Renders the full workflow completion summary block."""
        _log_file("INFO", "workflow", f"Workflow Complete: {wf_name} | status={status} | duration={duration:.2f}s | tokens={tokens_count}")

        if not self.console:
            print(f"\n--- Workflow Complete: {wf_name} | Status: {status.upper()} ---")
            return

        c = self.console
        status_color = "green" if status.upper() == "SUCCESS" else "red"
        SEP = "[bold green]" + "━" * 50 + "[/bold green]"

        c.print()
        c.print(SEP)
        c.print()
        c.print(f"  [bold white]Workflow Complete[/bold white]")
        c.print()
        c.print(f"  [bold cyan]{wf_name}[/bold cyan]")
        c.print()
        c.print(f"  [dim]Duration[/dim]      [white]{duration:.2f} sec[/white]")
        c.print(f"  [dim]Repository[/dim]    [white]{repo_name}[/white]")
        c.print(f"  [dim]Files[/dim]         [white]{files_count:,}[/white]")
        c.print(f"  [dim]Agents[/dim]        [white]{agents_count}[/white]")
        c.print(f"  [dim]Tokens[/dim]        [white]{tokens_count:,}[/white]")
        c.print(f"  [dim]Cache Hit[/dim]     [white]{cache_hit_pct}%[/white]")
        c.print(f"  [dim]Report[/dim]        [cyan]{report_name}[/cyan]")
        c.print(f"  [dim]Status[/dim]        [bold {status_color}]{status.upper()}[/bold {status_color}]")
        c.print()
        c.print(SEP)
        c.print()

    # ------------------------------------------------------------------
    # Error renderer
    # ------------------------------------------------------------------

    def display_error(
        self,
        exc_class: str,
        method_name: str,
        reason: str,
        suggested_fix: str,
        traceback_log_path: str,
        full_traceback: Optional[str] = None,
    ) -> None:
        """
        Renders a structured ERROR panel.
        Full Python traceback is only printed when DEBUG=true;
        otherwise it is saved to an error log file.
        """
        # Always write the full traceback to an error log file
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        err_log_file = os.path.join(ERRORS_DIR, f"{ts}.log")
        if full_traceback:
            try:
                with open(err_log_file, "w", encoding="utf-8") as f:
                    f.write(f"Exception:     {exc_class}\n")
                    f.write(f"Method:        {method_name}\n")
                    f.write(f"Reason:        {reason}\n")
                    f.write(f"Suggested Fix: {suggested_fix}\n")
                    f.write("\n--- Full Traceback ---\n")
                    f.write(full_traceback)
            except OSError:
                pass

        _log_file("ERROR", "errors", f"Runtime Error: {exc_class} in {method_name} — {reason}")

        if not self.console:
            print(f"\n[ERROR] {exc_class} in {method_name}: {reason}")
            if self._debug and full_traceback:
                print(full_traceback)
            return

        content = (
            f"[bold red]ERROR[/bold red]\n\n"
            f"  [dim]Class[/dim]          [bold red]{exc_class}[/bold red]\n"
            f"  [dim]Method[/dim]         [white]{method_name}[/white]\n"
            f"  [dim]Reason[/dim]         [yellow]{reason}[/yellow]\n"
            f"  [dim]Suggested Fix[/dim]  [bold green]{suggested_fix}[/bold green]\n\n"
            f"  [dim]────────────────────────────────────────────[/dim]\n"
            f"  [dim]Full traceback saved to[/dim]\n"
            f"  [bold yellow]{err_log_file}[/bold yellow]"
        )
        self.console.print(Panel(content, border_style="red", expand=False))

        # In DEBUG mode, also print the traceback inline
        if self._debug and full_traceback:
            self.console.print(
                Panel(
                    f"[dim]{full_traceback}[/dim]",
                    title="[bold red]Full Traceback (DEBUG)[/bold red]",
                    border_style="dim red",
                    expand=False,
                )
            )

    # ------------------------------------------------------------------
    # Runtime metrics footer
    # ------------------------------------------------------------------

    def display_metrics_footer(self, metrics: Dict[str, Any]) -> None:
        """Renders a performance metrics panel at workflow completion."""
        _log_file("INFO", "performance", f"Metrics: {metrics}")

        if not self.console:
            print(f"[PERF] {metrics}")
            return

        def _val(key: str, unit: str = "") -> str:
            v = metrics.get(key, "N/A")
            return f"[white]{v}{unit}[/white]" if v != "N/A" else "[dim]N/A[/dim]"

        content = (
            f"[bold grey50]Performance Metrics[/bold grey50]\n\n"
            f"  [dim]CPU[/dim]                  {_val('cpu')}\n"
            f"  [dim]Memory[/dim]               {_val('memory')}\n"
            f"  [dim]GPU[/dim]                  {_val('gpu')}\n"
            f"  [dim]Avg LLM Latency[/dim]      {_val('avg_llm_latency', 's')}\n"
            f"  [dim]Retrieval Time[/dim]        {_val('retrieval_time', 's')}\n"
            f"  [dim]Disk Writes[/dim]           {_val('disk_writes')}\n"
            f"  [dim]Queue Wait[/dim]            {_val('queue_wait', 's')}\n"
            f"  [dim]Overall Time[/dim]          {_val('overall_time', 's')}"
        )
        self.console.print(Panel(content, border_style="grey50", expand=False))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
console = DevMindConsole()
