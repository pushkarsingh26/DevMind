import pytest
from datetime import datetime
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.services.planning.planning_engine import planning_engine
from app.services.planning.planning_storage import planning_storage
from app.services.planning.planning_models import ExecutionPlan, ExecutionStep, StepDependency


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def mock_repository(db_session):
    # Retrieve or create a test repository in the DB
    repo = db_session.query(Repository).filter(Repository.name == "test_planning_repo").first()
    if not repo:
        repo = Repository(
            id="test_planning_repo_id",
            name="test_planning_repo",
            owner="test_owner",
            source="https://github.com/test/planning",
            repository_hash="initial_hash_123",
            total_files=42,
            status="READY",
        )
        db_session.add(repo)
        db_session.commit()
        db_session.refresh(repo)
    return repo


def test_intent_detection():
    # Verify standard prompts intent classification
    intent_sec = planning_engine.detect_intent("Please run a security scan on JWT paths")
    assert intent_sec == "Security Audit"

    intent_doc = planning_engine.detect_intent("generate documentation guide index")
    assert intent_doc == "Documentation"

    intent_ref = planning_engine.detect_intent("refactor component coupling and modularity")
    assert intent_ref == "Refactoring"

    intent_perf = planning_engine.detect_intent("diagnose latency bottleneck and slow queries")
    assert intent_perf == "Performance"

    intent_test = planning_engine.detect_intent("write pytest coverage cases")
    assert intent_test == "Testing"

    intent_bug = planning_engine.detect_intent("fix bug exception in controller route")
    assert intent_bug == "Bug Fix"

    intent_arch = planning_engine.detect_intent("review SOLID architecture patterns")
    assert intent_arch == "Architecture Review"

    intent_deps = planning_engine.detect_intent("audit dependency package imports tree")
    assert intent_deps == "Dependency Analysis"

    intent_feat = planning_engine.detect_intent("implement new endpoints for authentication")
    assert intent_feat == "Feature Implementation"

    intent_gen = planning_engine.detect_intent("unrelated generic request details")
    assert intent_gen == "General Analysis"


def test_plan_score_algorithm():
    # Verify plan completeness, confidence, and success rating logic
    steps = [
        ExecutionStep("step_repo", "Repository Agent", "Title 1", "Desc 1", "repository"),
        ExecutionStep("step_summary", "Summary Agent", "Title 2", "Desc 2", "summary"),
    ]
    plan = ExecutionPlan(
        plan_id="test_plan_id",
        plan_version="v1",
        repository_hash="hash",
        generated_at=datetime.utcnow().isoformat(),
        planner_version="v1",
        plan_schema_version="v1",
        ruleset_version="v1",
        steps=steps,
        intent="Security Audit",
        risk_level="medium",
        complexity_level="low",
    )
    score = planning_engine.score_plan(plan)
    assert score["completeness"] == 1.0  # has repo + summary + base
    assert score["confidence"] == 0.9    # matches Security Audit intent
    assert score["estimated_success_probability"] == 0.90


def test_topological_sort_levels():
    # Verify topological Kahn sort levels
    steps = [
        ExecutionStep("step_repo", "Repository Agent", "T1", "D1", "repository"),
        ExecutionStep("step_sec", "Security Agent", "T2", "D2", "analysis"),
        ExecutionStep("step_deps", "Dependency Agent", "T3", "D3", "analysis"),
        ExecutionStep("step_sum", "Summary Agent", "T4", "D4", "summary"),
    ]
    deps = [
        StepDependency("step_repo", "step_sec"),
        StepDependency("step_repo", "step_deps"),
        StepDependency("step_sec", "step_sum"),
        StepDependency("step_deps", "step_sum"),
    ]

    levels = planning_engine.topological_sort(steps, deps)
    
    assert len(levels) == 3
    assert levels[0] == ["step_repo"]
    # Parallelizable level 2
    assert sorted(levels[1]) == ["step_deps", "step_sec"]
    assert levels[2] == ["step_sum"]


def test_topological_sort_cycle_detection():
    # Verify Kahn sort fails on cyclic dependencies
    steps = [
        ExecutionStep("step_a", "Repository Agent", "T1", "D1", "repository"),
        ExecutionStep("step_b", "Review Agent", "T2", "D2", "analysis"),
    ]
    deps = [
        StepDependency("step_a", "step_b"),
        StepDependency("step_b", "step_a"),
    ]

    with pytest.raises(ValueError) as exc:
        planning_engine.topological_sort(steps, deps)
    assert "Cyclic dependencies" in str(exc.value)


def test_deterministic_plan_generation(mock_repository):
    # Same inputs should produce identical steps and dependency structure
    goal = "audit security JWT routes"
    plan1 = planning_engine.generate_plan(mock_repository.id, goal)
    plan2 = planning_engine.generate_plan(mock_repository.id, goal)

    assert plan1.intent == plan2.intent
    assert len(plan1.steps) == len(plan2.steps)
    assert len(plan1.dependencies) == len(plan2.dependencies)
    
    step_ids_1 = [s.step_id for s in plan1.steps]
    step_ids_2 = [s.step_id for s in plan2.steps]
    assert step_ids_1 == step_ids_2

    dep_pairs_1 = sorted([(d.source_step_id, d.target_step_id) for d in plan1.dependencies])
    dep_pairs_2 = sorted([(d.source_step_id, d.target_step_id) for d in plan2.dependencies])
    assert dep_pairs_1 == dep_pairs_2


def test_plan_cache_saving_and_invalidation(mock_repository):
    # Clean cache first
    planning_storage.clear_cache(mock_repository.id)

    goal = "Perform a security audit scan on JWT routes"
    
    # 1. First run: cache MISS, returns generated plan
    plan = planning_engine.generate_plan(mock_repository.id, goal)
    planning_storage.save_plan(mock_repository.id, plan)

    # 2. Second run: cache HIT, reuse exact same plan ID
    cached_plan = planning_storage.validate_cache(mock_repository.id, goal, mock_repository.repository_hash)
    assert cached_plan is not None
    assert cached_plan.plan_id == plan.plan_id

    # 3. Third run: cache invalidation due to repository hash change
    different_hash_plan = planning_storage.validate_cache(mock_repository.id, goal, "new_diff_hash_999")
    assert different_hash_plan is None

    # 4. Fourth run: cache invalidation due to goal mismatch
    different_goal_plan = planning_storage.validate_cache(mock_repository.id, "document the routes", mock_repository.repository_hash)
    assert different_goal_plan is None

    # Clean up
    planning_storage.clear_cache(mock_repository.id)


def test_empty_and_large_repository_fallbacks(mock_repository, db_session):
    # Empty total_files
    mock_repository.total_files = 0
    db_session.commit()
    plan_empty = planning_engine.generate_plan(mock_repository.id, "run security audit scan")
    assert plan_empty.metrics.dependency_depth > 0

    # Large repository total_files
    mock_repository.total_files = 100000
    db_session.commit()
    plan_large = planning_engine.generate_plan(mock_repository.id, "run security audit scan")
    assert plan_large.metrics.dependency_depth > 0
