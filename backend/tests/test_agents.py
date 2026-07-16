import os
import json
import pytest
import shutil
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

import app.db.base
from app.models.repository import Repository
from app.agents.execution_context import ExecutionContext
from app.agents.execution_report import ExecutionReport
from app.agents.tool_registry import ToolRegistry
from app.agents.base_agent import BaseAgent
from app.agents.planner_agent import PlannerAgent, ExecutionPlanSchema, PlanStepSchema
from app.agents.security_agent import SecurityAgent
from app.agents.refactor_agent import RefactorAgent, RefactorAgentSchema
from app.agents.summary_agent import SummaryAgent, SummaryAgentSchema
from app.db.session import SessionLocal

@pytest.fixture
def mock_db():
    session = MagicMock(spec=Session)
    return session

@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

# 1. Execution Context Tests
def test_execution_context_lifecycle():
    context = ExecutionContext("Upgrade security", "Security Audit", "repo_123")
    
    assert context.goal == "Upgrade security"
    assert context.workflow_type == "Security Audit"
    assert context.repository_id == "repo_123"
    assert len(context.logs) == 1
    
    # Step tracking
    context.record_step_start("Find Files", "Repository Agent")
    assert context.current_step == "Find Files"
    assert context.current_agent == "Repository Agent"
    
    context.record_step_complete("Find Files", "completed", "Found 2 files")
    assert len(context.completed_steps) == 1
    assert context.completed_steps[0]["step"] == "Find Files"
    assert context.completed_steps[0]["status"] == "completed"
    
    # Log telemetry
    context.record_tool_call("file_reader", {"path": "auth.py"}, "code content")
    assert len(context.tool_outputs) == 1
    assert context.tool_outputs[0]["tool"] == "file_reader"
    
    context.add_log("A test warning", "WARNING")
    assert len(context.logs) == 5
    
    data = context.to_dict()
    assert data["goal"] == "Upgrade security"
    assert data["confidence"] == 1.0

# 2. Tool Registry Tests
def test_tool_registry_operations(mock_db, temp_workspace):
    # Setup mock files in workspace
    auth_file = os.path.join(temp_workspace, "auth.py")
    with open(auth_file, "w", encoding="utf-8") as f:
        f.write("def verify_jwt(token):\n    return jwt.decode(token)\n")
        
    pkg_file = os.path.join(temp_workspace, "package.json")
    with open(pkg_file, "w", encoding="utf-8") as f:
        f.write('{"dependencies": {"express": "^4.18.2"}}')

    registry = ToolRegistry(temp_workspace, "repo_123", mock_db)
    
    # File Reader
    res_file = registry.execute_tool("file_reader", {"path": "auth.py"})
    assert "verify_jwt" in res_file
    assert "1: def verify_jwt(token):" in res_file
    
    # Dependency Analyzer
    res_deps = registry.execute_tool("dependency_analyzer", {})
    assert "express" in res_deps
    
    # Config Reader
    res_cfg = registry.execute_tool("config_reader", {"path": "package.json"})
    assert "express" in res_cfg

# 3. Agent Tests with Mocks
@pytest.mark.anyio
async def test_planner_agent():
    planner = PlannerAgent()
    mock_plan = ExecutionPlanSchema(
        plan=[
            PlanStepSchema(
                name="Map files",
                agent="Repository Agent",
                description="Find auth modules",
                expected_output="File paths list"
            )
        ],
        rationale="Simple query needs quick discovery",
        confidence=0.9
    )
    
    with patch.object(BaseAgent, "call_llm", AsyncMock(return_value=(mock_plan, {"total_tokens": 100, "provider": "google"}))):
        plan, telemetry = await planner.plan_goal("Find all security systems", {})
        assert plan.confidence == 0.9
        assert len(plan.plan) == 1
        assert plan.plan[0].agent == "Repository Agent"
        assert telemetry["total_tokens"] == 100

@pytest.mark.anyio
async def test_security_agent():
    agent = SecurityAgent()
    from app.agents.security_agent import SecurityAgentSchema, VulnerabilitySchema
    mock_out = SecurityAgentSchema(
        vulnerabilities=[
            VulnerabilitySchema(
                severity="High",
                description="Missing JWT verification",
                file="auth.py",
                line=2
            )
        ],
        security_score=40,
        recommendations=["Add jwt.verify() checks"],
        confidence=0.95
    )
    
    with patch.object(BaseAgent, "call_llm", AsyncMock(return_value=(mock_out, {"total_tokens": 150}))):
        res, telemetry = await agent.analyze_step("Verify auth security", "Scan JWT logic", "def verify_jwt(token):\n    pass")
        assert res.security_score == 40
        assert len(res.vulnerabilities) == 1
        assert res.vulnerabilities[0].severity == "High"

# 4. Workflow Executor Approval Flow Test
@pytest.mark.anyio
async def test_executor_approval_flow():
    from app.services.workflow_executor import WorkflowExecutor
    
    # Create a minimal mock executor
    executor = WorkflowExecutor(
        workflow_id="wf_test_approval",
        repository_id="repo_123",
        goal="Verify auth",
        workflow_type="Security Audit",
        on_event_cb=lambda *args: None,
        on_finished_cb=lambda *args: None
    )
    
    # Set context diff and affected files
    executor.context.diff = "--- old\n+++ new\n"
    executor.context.affected_files = ["auth.py"]
    executor._status = "waiting_approval"
    
    # We trigger approval in 50ms asynchronously to test unblocking
    async def trigger_approval_delayed():
        await asyncio.sleep(0.05)
        executor.submit_approval(approved=True, reason="Looks clean")
        
    asyncio.create_task(trigger_approval_delayed())
    
    # Block on event wait (as executor thread would do)
    await executor._approval_event.wait()
    
    assert executor.context.approval_status == "approved"
    assert executor.context.approval_reason == "Looks clean"

# 5. Registry and templates dynamic configuration tests
def test_agent_registry_resolution():
    from app.agents.agent_registry import agent_registry
    from app.agents.planner_agent import PlannerAgent
    planner_class = agent_registry.get_agent_class("Planner Agent")
    assert planner_class == PlannerAgent
    planner_instance = agent_registry.get_agent("Planner Agent")
    assert isinstance(planner_instance, PlannerAgent)

def test_workflow_templates_dynamic_loading():
    from app.agents.workflow_templates import WORKFLOW_TEMPLATES
    assert isinstance(WORKFLOW_TEMPLATES, dict)
    assert "Security Audit" in WORKFLOW_TEMPLATES
    assert len(WORKFLOW_TEMPLATES["Security Audit"]) == 4

# 6. Database Repository Memory persistence tests
def test_repository_memory_persistence():
    from app.models.memory import RepositoryMemoryORM
    memory = RepositoryMemoryORM(
        repository_id="repo_123",
        memory_key="Security Audit",
        content="JWT Signature Bypass vulnerability patched."
    )
    assert memory.repository_id == "repo_123"
    assert memory.memory_key == "Security Audit"
    assert memory.content == "JWT Signature Bypass vulnerability patched."

# 7. Conforming Tool Registry operations tests
def test_expanded_tool_registry_conformance(mock_db, temp_workspace):
    from app.agents.tool_registry import ToolRegistry
    registry = ToolRegistry(temp_workspace, "repo_123", mock_db)
    
    # Verify all tools exist and conform
    for tool_key, tool_instance in registry.tools.items():
        from app.agents.base_tool import BaseTool
        assert isinstance(tool_instance, BaseTool)

    # Test RepoStatsTool
    stats_tool = registry.tools["repo_stats"]
    stats_out = stats_tool.execute()
    assert "workspace_path" in stats_out
    
    # Test DirectoryReaderTool
    dir_tool = registry.tools["directory_reader"]
    dir_out = dir_tool.execute()
    assert "Contents of directory" in dir_out

# 8. Execution Analytics telemetry tests
def test_execution_analytics_telemetry():
    context = ExecutionContext("Optimize codebase", "Performance Audit", "repo_123")
    context.retry_count = 3
    context.cache_hits = 5
    context.cache_misses = 2
    context.agent_durations["Performance Agent"] = 1.24
    
    data = context.to_dict()
    assert "analytics" in data
    assert data["analytics"]["retry_count"] == 3
    assert data["analytics"]["cache_hits"] == 5
    assert data["analytics"]["cache_misses"] == 2
    assert data["analytics"]["agent_durations"]["Performance Agent"] == 1.24
