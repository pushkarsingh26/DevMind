import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import app.db.base
from app.main import app
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.job import AnalysisJobORM
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service
from app.services.retrieval_service import retrieval_service
from app.services.context_builder import context_builder
from app.services.rag_service import rag_service
from app.services.chunk_service import CodeChunk

client = TestClient(app)

def test_embedding_service_dimensions():
    """
    Verifies that EmbeddingService generates correct 384-dimensional vectors.
    """
    texts = ["def hello(): print('hello')", "class A: pass"]
    embeddings = embedding_service.generate_embeddings(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384
    assert embedding_service.get_model_name() == "BAAI/bge-small-en-v1.5"
    assert embedding_service.get_embedding_dimension() == 384

def test_vector_store_save_load_search():
    """
    Verifies VectorStoreService index creation, loading, search, mapping, and deletion.
    """
    repo_id = f"test_repo_{uuid.uuid4().hex[:6]}"
    dimension = 384
    vectors = [[0.1] * dimension, [0.9] * dimension]
    embedding_ids = ["emb_1", "emb_2"]
    
    # Save vector store
    vector_store_service.save_vector_store(repo_id, dimension, vectors, embedding_ids)
    
    assert vector_store_service.index_exists(repo_id) is True
    
    # Search
    query = [0.95] * dimension
    results = vector_store_service.search(repo_id, query, k=2)
    
    assert len(results) == 2
    assert results[0][0] == "emb_2"  # More similar to [0.9]*384
    assert results[1][0] == "emb_1"
    
    # Delete
    vector_store_service.delete_vector_store(repo_id)
    assert vector_store_service.index_exists(repo_id) is False

def test_rag_and_retrieval_integration():
    """
    Runs end-to-end DB model registration, indexing via RAGService, 
    and semantic retrieval via RetrievalService and ContextBuilder.
    """
    db = SessionLocal()
    repo_id = f"repo_int_{uuid.uuid4().hex[:6]}"
    job_id = f"job_int_{uuid.uuid4().hex[:6]}"
    
    try:
        # Create Repository and Job in DB
        repo = Repository(
            id=repo_id,
            name="integration-test",
            owner="owner",
            source="source-url",
            status="INDEXING"
        )
        job = AnalysisJobORM(
            id=job_id,
            repository_id=repo_id,
            task_type="review",
            status="running"
        )
        db.add(repo)
        db.add(job)
        db.commit()
        
        # Define mock chunk
        chunks = [
            CodeChunk(
                id="c1",
                path="math.py",
                language=".py",
                start_line=1,
                end_line=5,
                content="def add(a, b):\n    return a + b\n",
                job_id=job_id
            ),
            CodeChunk(
                id="c2",
                path="string.py",
                language=".py",
                start_line=1,
                end_line=5,
                content="def concat(s1, s2):\n    return s1 + s2\n",
                job_id=job_id
            )
        ]
        
        # 1. RAG Indexing
        rag_service.index_repository(db, repo_id, job_id, chunks)
        
        # Refresh repo status
        db.refresh(repo)
        assert repo.status == "READY"
        
        # Verify DB entries
        db_chunks = db.query(Chunk).filter(Chunk.repository_id == repo_id).all()
        assert len(db_chunks) == 2
        
        db_embeddings = db.query(Embedding).filter(Embedding.repository_id == repo_id).all()
        assert len(db_embeddings) == 2
        assert db_embeddings[0].embedding_dimension == 384
        assert db_embeddings[0].embedding_model == "BAAI/bge-small-en-v1.5"
        
        # Verify FAISS exists
        assert vector_store_service.index_exists(repo_id) is True
        
        # 2. Semantic retrieval
        retrieved_pairs = retrieval_service.retrieve_chunks(db, repo_id, "sum numbers or add", top_k=1)
        assert len(retrieved_pairs) == 1
        matched_chunk, score = retrieved_pairs[0]
        assert matched_chunk.path == "math.py"
        assert "add" in matched_chunk.content
        
        # 3. ContextBuilder
        context = context_builder.build_context(retrieved_pairs)
        assert len(context) == 1
        assert context[0]["path"] == "math.py"
        assert context[0]["score"] == score
        assert context[0]["start_line"] == 1
        assert context[0]["end_line"] == 5
        assert "add" in context[0]["content"]

    finally:
        # Clean up database and vector files
        vector_store_service.delete_vector_store(repo_id)
        db.query(Embedding).filter(Embedding.repository_id == repo_id).delete()
        db.query(Chunk).filter(Chunk.repository_id == repo_id).delete()
        db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).delete()
        db.query(Repository).filter(Repository.id == repo_id).delete()
        db.commit()
        db.close()

def test_api_endpoints():
    """
    Tests GET /repositories, GET /repositories/{id}, DELETE /repositories/{id}, and POST /retrieve.
    """
    db = SessionLocal()
    repo_id = f"repo_api_{uuid.uuid4().hex[:6]}"
    job_id = f"job_api_{uuid.uuid4().hex[:6]}"
    
    try:
        # 1. Setup mock data
        repo = Repository(
            id=repo_id,
            name="api-test",
            owner="test-owner",
            source="http://github.com/test-owner/api-test",
            framework="FastAPI",
            language="Python",
            repository_hash="hash123",
            status="INDEXING"
        )
        job = AnalysisJobORM(
            id=job_id,
            repository_id=repo_id,
            task_type="review",
            status="running"
        )
        db.add(repo)
        db.add(job)
        db.commit()
        
        chunks = [
            CodeChunk(
                id="c1",
                path="app.py",
                language=".py",
                start_line=1,
                end_line=3,
                content="print('Hello API')",
                job_id=job_id
            )
        ]
        
        rag_service.index_repository(db, repo_id, job_id, chunks)
        
        # 2. Test GET /repositories
        response = client.get("/repositories")
        assert response.status_code == 200
        repos = response.json()
        assert len(repos) >= 1
        assert any(r["id"] == repo_id for r in repos)
        
        # 3. Test GET /repositories/{id}
        response = client.get(f"/repositories/{repo_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == repo_id
        assert data["framework"] == "FastAPI"
        assert data["status"] == "READY"
        
        # Test GET /repositories/non-existent
        response = client.get("/repositories/non-existent-repo")
        assert response.status_code == 404
        
        # 4. Test POST /retrieve
        payload = {
            "repository_id": repo_id,
            "query": "hello api printing print",
            "top_k": 5
        }
        response = client.post("/retrieve", json=payload)
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["path"] == "app.py"
        assert result["results"][0]["start_line"] == 1
        assert "Hello API" in result["results"][0]["content"]
        
        # 5. Test DELETE /repositories/{id}
        response = client.delete(f"/repositories/{repo_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify repository deleted from DB and vector store
        db.expire_all()
        repo_db = db.query(Repository).filter(Repository.id == repo_id).first()
        assert repo_db is None
        assert vector_store_service.index_exists(repo_id) is False
        
        # Verify cascade deletes worked
        chunks_db = db.query(Chunk).filter(Chunk.repository_id == repo_id).all()
        assert len(chunks_db) == 0
        embeddings_db = db.query(Embedding).filter(Embedding.repository_id == repo_id).all()
        assert len(embeddings_db) == 0

    finally:
        # Cleanup in case of failure
        vector_store_service.delete_vector_store(repo_id)
        db.query(Embedding).filter(Embedding.repository_id == repo_id).delete()
        db.query(Chunk).filter(Chunk.repository_id == repo_id).delete()
        db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).delete()
        repo_db = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo_db:
            db.delete(repo_db)
        db.commit()
        db.close()


def test_task_propagation_and_branching():
    """
    Verifies that the markdown serialization branches on task objective types.
    """
    from app.services.job_service import job_service
    
    mock_result = {
        "repository": {
            "name": "test-repo",
            "owner": "test-owner",
            "default_branch": "main"
        },
        "metadata": {
            "primary_language": "Python",
            "framework": "FastAPI",
            "package_managers": ["pip"],
            "tests_present": True,
            "docker_support": True,
            "github_actions": False,
            "cicd": False,
            "license": "MIT",
            "dependencies": {"fastapi": "0.100.0"}
        },
        "statistics": {
            "total_files": 12,
            "total_directories": 3,
            "extensions": {".py": 10},
            "largest_files": [{"path": "main.py", "size": 1024}]
        },
        "chunks": [{"id": "c1", "path": "main.py", "content": "print('hello')"}]
    }
    
    # Test EXPLAIN report
    explain_report = job_service._serialize_json_to_markdown(mock_result, task_type="explain")
    assert "Architecture Explanation" in explain_report
    assert "EXPLAIN" in explain_report
    assert "High-Level Architecture" in explain_report
    
    # Test TESTS report
    tests_report = job_service._serialize_json_to_markdown(mock_result, task_type="tests")
    assert "Test Generation Recommendations" in tests_report
    assert "TESTS" in tests_report
    assert "Test Suite Coverage Status" in tests_report
    
    # Test BUGS report
    bugs_report = job_service._serialize_json_to_markdown(mock_result, task_type="bugs")
    assert "Bug Finder Report" in bugs_report
    assert "BUGS" in bugs_report
    assert "Hotspots & Logic Defects" in bugs_report
    
    # Test REVIEW report (default)
    review_report = job_service._serialize_json_to_markdown(mock_result, task_type="review")
    assert "DevMind Real-Time Workspace Scan" in review_report
    assert "SUCCESS" in review_report
    assert "Codebase Architecture Summary" in review_report


def test_task_aware_progress_stages():
    """
    Verifies that the progress stages mapped by PipelineService represent actual backend processing stages.
    """
    from app.services.pipeline_service import pipeline_service
    from app.core.config import settings
    
    # We will simulate the notify_progress internal behavior using a mock callback
    notified_stages = []
    def callback(prog, stage):
        notified_stages.append((prog, stage))
        
    for task in ["review", "explain", "tests", "bugs"]:
        job_id = f"test_stages_{task}_{uuid.uuid4().hex[:6]}"
        test_temp_dir = os.path.abspath(os.path.join(str(settings.WORKSPACE_ROOT), job_id))
        os.makedirs(test_temp_dir, exist_ok=True)
        with open(os.path.join(test_temp_dir, "hello.py"), "w") as f:
            f.write("print('hello')")
            
        try:
            pipeline_service.run_pipeline(
                job_id=job_id,
                source_path_or_url="hello.zip",
                is_zip=True,
                task_type=task,
                progress_callback=callback
            )
        except Exception:
            pass
        finally:
            import shutil
            if os.path.exists(test_temp_dir):
                shutil.rmtree(test_temp_dir, ignore_errors=True)
                
        assert len(notified_stages) > 0
        # Find the stage names for different progress values
        stage_names_15 = [name for prog, name in notified_stages if prog == 15]
        stage_names_35 = [name for prog, name in notified_stages if prog == 35]
        stage_names_60 = [name for prog, name in notified_stages if prog == 60]
        stage_names_85 = [name for prog, name in notified_stages if prog == 85]

        assert len(stage_names_15) > 0
        assert "Planner" in stage_names_15[0]
        
        # Depending on whether there was a cache hit or miss, other stages might exist
        if len(stage_names_35) > 0:
            assert "Retriever" in stage_names_35[0]
        if len(stage_names_60) > 0:
            assert "Reviewer" in stage_names_60[0]
        if len(stage_names_85) > 0:
            assert "Critic" in stage_names_85[0]

        notified_stages.clear()



def test_repository_stats_persistence_and_reuse():
    """
    Verifies that repository stats are successfully persisted in the database
    and restored exactly during cache reuse.
    """
    from app.services.pipeline_service import pipeline_service
    from app.core.config import settings
    db = SessionLocal()
    repo_id = f"repo_stats_{uuid.uuid4().hex[:6]}"
    job_id = f"job_stats_reuse"
    
    # Create the workspace directory to satisfy the path check
    test_temp_dir = os.path.abspath(os.path.join(str(settings.WORKSPACE_ROOT), job_id))
    os.makedirs(test_temp_dir, exist_ok=True)
    with open(os.path.join(test_temp_dir, "hello.py"), "w") as f:
        f.write("print('hello')")
        
    try:
        # Calculate repo hash of this temp workspace so it matches what we record in Repository
        repo_hash = pipeline_service._compute_repo_hash(test_temp_dir, is_zip=True)
        
        # Clean up any leftover repository with source hello.zip to prevent contamination
        db.query(Repository).filter(Repository.source == "hello.zip").delete()
        db.commit()

        # Create a ready Repository in DB with stats columns set
        repo = Repository(
            id=repo_id,
            name="stats-repo",
            owner="test-owner",
            source="hello.zip",
            framework="FastAPI",
            language="Python",
            repository_hash=repo_hash,
            status="READY",
            default_branch="develop",
            readme_present=True,
            license="MIT",
            docker_support=True,
            github_actions=True,
            cicd=True,
            tests_present=True,
            total_files=42,
            directories=8,
            extensions={".py": 30, ".json": 12},
            largest_files=[{"path": "main.py", "size": 999}],
            dependencies={"fastapi": "0.100.0"},
            package_managers=["pip"]
        )
        db.add(repo)
        db.commit()
        
        # Call run_pipeline which should hit the cache reuse block
        result = pipeline_service.run_pipeline(
            job_id=job_id,
            source_path_or_url="hello.zip",
            is_zip=True,
            task_type="explain"
        )
        
        # Assert returned statistics match the database record instead of being 0
        assert result["metadata"]["total_files"] == 42
        assert result["metadata"]["directories"] == 8
        assert result["metadata"]["primary_language"] == "Python"
        assert result["metadata"]["framework"] == "FastAPI"
        assert result["metadata"]["package_managers"] == ["pip"]
        assert result["metadata"]["dependencies"] == {"fastapi": "0.100.0"}
        assert result["metadata"]["extensions"] == {".py": 30, ".json": 12}
        assert result["metadata"]["largest_files"] == [{"path": "main.py", "size": 999}]
        assert result["metadata"]["default_branch"] == "develop"
        assert result["metadata"]["readme_present"] is True
        assert result["metadata"]["license"] == "MIT"
        assert result["metadata"]["docker_support"] is True
        assert result["metadata"]["github_actions"] is True
        assert result["metadata"]["cicd"] is True
        assert result["metadata"]["tests_present"] is True
        
        assert result["statistics"]["total_files"] == 42
        assert result["statistics"]["total_directories"] == 8

        
    finally:
        import shutil
        if os.path.exists(test_temp_dir):
            shutil.rmtree(test_temp_dir, ignore_errors=True)
        db.query(AnalysisJobORM).filter(AnalysisJobORM.repository_id == repo_id).delete()
        db.query(Repository).filter(Repository.id == repo_id).delete()
        db.commit()
        db.close()


def test_cache_clone_bypass_and_traceability(monkeypatch):
    """
    Verifies that cache hit pre-clone checks bypass clone_repository completely,
    and the generated report contains traceability mapping (## Retrieved Context).
    """
    from app.services.pipeline_service import pipeline_service
    from app.services.job_service import job_service
    from app.services.repository_service import repository_service
    
    db = SessionLocal()
    repo_id = f"repo_bypass_{uuid.uuid4().hex[:6]}"
    job_id = f"job_bypass_test"
    target_url = "https://github.com/fake/repo"
    fake_hash = "fake_commit_hash_123456"

    # Mock remote commit hash lookup to return our fake hash
    monkeypatch.setattr(pipeline_service, "_get_remote_commit_hash", lambda url: fake_hash)

    # Mock clone_repository to fail if called, ensuring it is bypassed
    def mock_clone(url, j_id):
        raise Exception("clone_repository should have been bypassed!")
    monkeypatch.setattr(repository_service, "clone_repository", mock_clone)

    try:
        # Prevent test pollution by purging prior mock repositories with the same source
        db.query(Chunk).filter(Chunk.repository_id.like("repo_bypass_%")).delete(synchronize_session=False)
        db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).delete(synchronize_session=False)
        db.query(Repository).filter(Repository.source == target_url).delete(synchronize_session=False)
        db.commit()

        # Pre-populate READY Repository in DB
        repo = Repository(
            id=repo_id,

            name="bypass-repo",
            owner="fake-owner",
            source=target_url,
            framework="FastAPI",
            language="Python",
            repository_hash=fake_hash,
            status="READY",
            total_files=5,
            directories=1,
            extensions={".py": 5},
            largest_files=[{"path": "main.py", "size": 100}],
            dependencies={"fastapi": "0.100.0"},
            package_managers=["pip"]
        )
        db.add(repo)
        db.commit()

        # Pre-populate AnalysisJobORM to satisfy chunks foreign key constraint
        job_record = AnalysisJobORM(
            id=job_id,
            repository_id=repo_id,
            task_type="review",
            status="completed",
            progress=100,
            current_stage="Analysis completed successfully"
        )
        db.add(job_record)
        db.commit()

        # Add a chunk for traceability checks

        chunk = Chunk(
            id=f"{repo_id}:main.py-chunk-0",
            repository_id=repo_id,
            analysis_job_id=job_id,
            path="main.py",
            language=".py",
            chunk_index=0,
            start_line=1,
            end_line=10,
            content="print('hello')"
        )
        db.add(chunk)
        db.commit()

        # Call run_pipeline which should hit cache and bypass clone
        result = pipeline_service.run_pipeline(
            job_id=job_id,
            source_path_or_url=target_url,
            is_zip=False,
            task_type="review"
        )

        assert result["repository"]["name"] == "bypass-repo"
        assert result["metadata"]["primary_language"] == "Python"

        # Verify that generating report contains Retrieved Context section
        report = job_service._serialize_json_to_markdown(result, task_type="review")
        assert "## Retrieved Context" in report
        assert "main.py" in report
        assert "L1-L10" in report

    finally:
        db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).delete()
        db.query(Chunk).filter(Chunk.repository_id == repo_id).delete()
        db.query(Repository).filter(Repository.id == repo_id).delete()
        db.commit()
        db.close()

