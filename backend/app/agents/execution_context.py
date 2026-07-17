import time
from typing import List, Dict, Any, Optional

class ExecutionContext:
    """
    Maintains the temporary in-memory state of the active workflow run.
    """
    def __init__(self, goal: str, workflow_type: str, repository_id: str):
        self.goal = goal
        self.workflow_type = workflow_type
        self.repository_id = repository_id
        
        self.current_step: str = "Initializing"
        self.current_agent: str = "System"
        self.current_tool: str = "None"
        
        self.completed_steps: List[Dict[str, Any]] = []
        self.retrieved_chunks: List[Dict[str, Any]] = []
        self.tool_outputs: List[Dict[str, Any]] = []
        self.agent_outputs: List[Dict[str, Any]] = []
        self.intermediate_summaries: List[str] = []
        self.confidence_scores: List[float] = [1.0]
        
        self.logs: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.tokens_used = 0
        self.providers_used = []
        
        # Human approval management
        self.diff: Optional[str] = None
        self.affected_files: List[str] = []
        self.approval_reason: Optional[str] = None
        self.approval_status: Optional[str] = None  # approved, rejected

        # Execution Analytics metrics
        self.retry_count: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.agent_durations: Dict[str, float] = {}

        # Graph Telemetry
        self.graph_build_time: float = 0.0
        self.graph_cache_hit: bool = False
        self.graph_candidates_selected: int = 0
        self.graph_nodes: int = 0
        self.graph_edges: int = 0
        self.graph_traversal_time: float = 0.0

        # Multi-Agent Collaboration (Phase 8.6)
        self.collaboration_snapshot: Dict[str, Any] = {}
        self.collaboration_context: Dict[str, Any] = {}

        # Autonomous Reasoning (Phase 8.8) — populated by WorkflowExecutor before run
        self.reasoning_summary: Optional[Any] = None   # ReasoningSummary dataclass
        self.reasoning_metrics: Optional[Any] = None   # ReasoningMetrics dataclass
        self.reasoning_context: Optional[Any] = None   # ReasoningContext dataclass

        # Decision Engine (Phase 8.9)
        self.decision_summary: Optional[Any] = None    # DecisionSummary dataclass

        self.add_log("Workflow initialized")

    def add_log(self, message: str, level: str = "INFO"):
        self.logs.append({
            "timestamp": time.time() - self.start_time,
            "level": level,
            "message": message
        })

    def record_step_start(self, step_name: str, agent_name: str):
        self.current_step = step_name
        self.current_agent = agent_name
        self.current_tool = "None"
        self.add_log(f"Starting step '{step_name}' with Agent '{agent_name}'")

    def record_step_complete(self, step_name: str, status: str = "completed", details: str = ""):
        self.completed_steps.append({
            "step": step_name,
            "agent": self.current_agent,
            "status": status,
            "details": details,
            "timestamp": time.time() - self.start_time
        })
        self.add_log(f"Step '{step_name}' completed with status: {status}")

    def record_tool_call(self, tool_name: str, arguments: Dict[str, Any], output: str):
        self.current_tool = tool_name
        self.tool_outputs.append({
            "tool": tool_name,
            "arguments": arguments,
            "output_length": len(output),
            "timestamp": time.time() - self.start_time
        })
        self.add_log(f"Executed tool '{tool_name}'")

    def add_chunk(self, path: str, start: int, end: int, score: float):
        self.retrieved_chunks.append({
            "path": path,
            "start_line": start,
            "end_line": end,
            "score": score
        })

    def record_agent_output(self, agent_name: str, result: Dict[str, Any], confidence: float = 1.0):
        self.agent_outputs.append({
            "agent": agent_name,
            "result": result,
            "confidence": confidence,
            "timestamp": time.time() - self.start_time
        })
        self.confidence_scores.append(confidence)
        self.add_log(f"Agent '{agent_name}' output received (Confidence: {confidence:.2f})")

    def add_summary(self, summary_text: str):
        self.intermediate_summaries.append(summary_text)

    def get_average_confidence(self) -> float:
        if not self.confidence_scores:
            return 1.0
        return sum(self.confidence_scores) / len(self.confidence_scores)

    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "workflow_type": self.workflow_type,
            "repository_id": self.repository_id,
            "current_step": self.current_step,
            "current_agent": self.current_agent,
            "current_tool": self.current_tool,
            "completed_steps": self.completed_steps,
            "retrieved_chunks": self.retrieved_chunks,
            "tool_outputs": self.tool_outputs,
            "agent_outputs": self.agent_outputs,
            "intermediate_summaries": self.intermediate_summaries,
            "confidence": self.get_average_confidence(),
            "logs": self.logs,
            "duration": self.get_elapsed_time(),
            "tokens_used": self.tokens_used,
            "providers_used": list(set(self.providers_used)),
            "diff": self.diff,
            "affected_files": self.affected_files,
            "approval_status": self.approval_status,
            "analytics": {
                "retry_count": self.retry_count,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "agent_durations": self.agent_durations,
                "chunks_used_count": len(self.retrieved_chunks),
                "tools_used_count": len(self.tool_outputs)
            }
        }
