import os
from typing import List, Dict
from pydantic import BaseModel, Field
from app.core.logger import logger

class CodeChunk(BaseModel):
    id: str = Field(..., description="Unique chunk ID")
    path: str = Field(..., description="Relative file path within repository")
    language: str = Field(..., description="Language/extension of file")
    start_line: int = Field(..., description="Line index (1-based) where chunk begins")
    end_line: int = Field(..., description="Line index (1-based) where chunk ends")
    content: str = Field(..., description="The chunk text contents")
    job_id: str = Field(..., description="The parent job ID tracking this analysis run")

class ChunkService:
    def __init__(self):
        # Dictionary storing job_id -> List[CodeChunk]
        self._store: Dict[str, List[CodeChunk]] = {}
        
        # Extensions to process
        self.supported_extensions = {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".java",
            ".go", ".rs", ".cpp", ".c", ".cs", ".md",
            ".json", ".yaml", ".yml"
        }

    def chunk_repository(self, local_path: str, job_id: str) -> List[CodeChunk]:
        """
        Walks local repository path, reads supported code files, chunks them, and stores in-memory.
        """
        logger.info(f"Chunking files in repository: {local_path} for job {job_id}")
        chunks: List[CodeChunk] = []

        if not os.path.exists(local_path):
            logger.warn(f"Cannot chunk repository. Path does not exist: {local_path}")
            return []

        for root, dirs, files in os.walk(local_path):
            # Exclude folders
            dirs[:] = [d for d in dirs if d not in {
                ".git", "node_modules", "venv", ".venv", "dist", "build", "coverage", "__pycache__"
            }]

            for file in files:
                _, ext = os.path.splitext(file.lower())
                if ext not in self.supported_extensions:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, local_path)
                
                # Chunk individual file
                file_chunks = self._chunk_file(full_path, rel_path, ext, job_id)
                chunks.extend(file_chunks)

        # Store chunks in-memory
        self._store[job_id] = chunks
        logger.info(f"Chunked repository: created {len(chunks)} chunks for job {job_id}")
        return chunks

    def get_chunks(self, job_id: str) -> List[CodeChunk]:
        """
        Retrieves in-memory chunks for a specific job_id.
        """
        return self._store.get(job_id, [])

    def delete_chunks(self, job_id: str):
        """
        Cleans up chunks from memory.
        """
        if job_id in self._store:
            del self._store[job_id]
            logger.info(f"Cleaned up in-memory chunks for job: {job_id}")

    def _chunk_file(self, full_path: str, rel_path: str, extension: str, job_id: str) -> List[CodeChunk]:
        file_chunks: List[CodeChunk] = []
        
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read file {full_path} for chunking: {e}")
            return []

        current_line_num = 1
        buffer_lines = []
        buffer_chars = 0
        chunk_idx = 0
        start_line = 1

        for line in lines:
            line_len = len(line)
            
            # Handle extremely long lines (>1000 chars)
            if line_len > 1000:
                if buffer_lines:
                    file_chunks.append(
                        self._create_chunk(buffer_lines, rel_path, extension, chunk_idx, start_line, current_line_num - 1, job_id)
                    )
                    chunk_idx += 1
                    buffer_lines = []
                    buffer_chars = 0

                start = 0
                while start < line_len:
                    end = start + 800
                    sub_content = line[start:end]
                    file_chunks.append(
                        CodeChunk(
                            id=f"{rel_path}-large-{chunk_idx}",
                            path=rel_path,
                            language=extension,
                            start_line=current_line_num,
                            end_line=current_line_num,
                            content=sub_content,
                            job_id=job_id
                        )
                    )
                    chunk_idx += 1
                    start = end
                current_line_num += 1
                continue

            if buffer_chars == 0:
                start_line = current_line_num

            # Check if adding this line violates the chunk target boundaries
            if buffer_chars + line_len > 1000 and buffer_chars >= 500:
                file_chunks.append(
                    self._create_chunk(buffer_lines, rel_path, extension, chunk_idx, start_line, current_line_num - 1, job_id)
                )
                chunk_idx += 1
                buffer_lines = [line]
                buffer_chars = line_len
                start_line = current_line_num
                current_line_num += 1
            else:
                buffer_lines.append(line)
                buffer_chars += line_len
                current_line_num += 1

        # Flush final remaining lines
        if buffer_lines:
            file_chunks.append(
                self._create_chunk(buffer_lines, rel_path, extension, chunk_idx, start_line, current_line_num - 1, job_id)
            )

        return file_chunks

    def _create_chunk(self, lines: List[str], rel_path: str, ext: str, index: int, start: int, end: int, job_id: str) -> CodeChunk:
        content = "".join(lines)
        return CodeChunk(
            id=f"{rel_path}-chunk-{index}",
            path=rel_path,
            language=ext,
            start_line=start,
            end_line=end,
            content=content,
            job_id=job_id
        )

chunk_service = ChunkService()
