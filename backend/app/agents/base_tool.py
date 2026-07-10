from abc import ABC, abstractmethod

class BaseTool(ABC):
    """
    Common base class interface for all specialized tools in the AI agent framework.
    """
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Runs tool operation and returns text format output context.
        """
        pass
