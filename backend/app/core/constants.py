from enum import Enum

class TaskType(str, Enum):
    REVIEW = "review"
    EXPLAIN = "explain"
    TESTS = "tests"
    BUGS = "bugs"

class AgentName(str, Enum):
    PLANNER = "planner"
    RETRIEVER = "retriever"
    REVIEWER = "reviewer"
    CRITIC = "critic"

class AgentStatus(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
