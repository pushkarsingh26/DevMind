from typing import Dict, Type
import importlib

class AgentRegistry:
    """
    Registry for dynamic loading of autonomous specialized agents.
    Decouples the execution engine from concrete agent implementations.
    """
    def __init__(self):
        # Map agent registered name to its module import path and class name
        self._registry: Dict[str, Dict[str, str]] = {
            "Planner Agent": {
                "module": "app.agents.planner_agent",
                "class": "PlannerAgent"
            },
            "Repository Agent": {
                "module": "app.agents.repository_agent",
                "class": "RepositoryAgent"
            },
            "Review Agent": {
                "module": "app.agents.review_agent",
                "class": "ReviewAgent"
            },
            "Security Agent": {
                "module": "app.agents.security_agent",
                "class": "SecurityAgent"
            },
            "Performance Agent": {
                "module": "app.agents.performance_agent",
                "class": "PerformanceAgent"
            },
            "Testing Agent": {
                "module": "app.agents.testing_agent",
                "class": "TestingAgent"
            },
            "Documentation Agent": {
                "module": "app.agents.documentation_agent",
                "class": "DocumentationAgent"
            },
            "Refactor Agent": {
                "module": "app.agents.refactor_agent",
                "class": "RefactorAgent"
            },
            "Summary Agent": {
                "module": "app.agents.summary_agent",
                "class": "SummaryAgent"
            }
        }
        # In-memory instance cache for memoization
        self._instances = {}

    def register(self, name: str, module_path: str, class_name: str):
        """
        Dynamically registers a new agent definition.
        """
        self._registry[name] = {
            "module": module_path,
            "class": class_name
        }

    def get_agent_class(self, name: str) -> Type:
        """
        Loads the agent module dynamically and returns the agent class.
        """
        if name not in self._registry:
            raise KeyError(f"Agent '{name}' is not registered in AgentRegistry.")
        
        info = self._registry[name]
        module = importlib.import_module(info["module"])
        return getattr(module, info["class"])

    def get_agent(self, name: str):
        """
        Instantiates and returns a single agent instance.
        """
        if name not in self._instances:
            cls = self.get_agent_class(name)
            self._instances[name] = cls()
        return self._instances[name]

# Global singleton instance
agent_registry = AgentRegistry()
