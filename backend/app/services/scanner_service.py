import os
import json
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.logger import logger

class FileInfo(BaseModel):
    path: str = Field(..., description="Relative file path")
    size: int = Field(..., description="File size in bytes")

class RepositoryMetadata(BaseModel):
    repository_name: str = Field(..., description="The name of the repository folder")
    repository_owner: str = Field("Unknown", description="Owner of the repository")
    default_branch: str = Field("Unknown", description="Default checkout branch")
    primary_language: str = Field("Unknown", description="Determined primary language based on file counts")
    framework: str = Field("None", description="Guessed project framework")
    package_managers: List[str] = Field(default_factory=list, description="Detected package managers")
    readme_present: bool = Field(False, description="Whether a README file is present")
    license: str = Field("None", description="Detected LICENSE type")
    docker_support: bool = Field(False, description="Whether Docker configs are present")
    github_actions: bool = Field(False, description="Whether GitHub Actions are present")
    cicd: bool = Field(False, description="Whether any CI/CD pipeline config exists")
    tests_present: bool = Field(False, description="Whether tests folder is present")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Parsed dependency names and versions")
    total_files: int = Field(0, description="Total number of code/text files")
    directories: int = Field(0, description="Total number of folders")
    extensions: Dict[str, int] = Field(default_factory=dict, description="Counts of file extensions")
    largest_files: List[FileInfo] = Field(default_factory=list, description="Top 5 largest files in the repository")

class ScannerService:
    def __init__(self):
        self.exclude_dirs = {
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "dist",
            "build",
            "coverage",
            "__pycache__",
            ".pytest_cache",
            "cache"
        }
        
        self.lang_exts = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "JavaScript (React)",
            ".ts": "TypeScript",
            ".tsx": "TypeScript (React)",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".sh": "Shell Script"
        }

    def scan_repository(self, local_path: str, repo_url: Optional[str] = None, branch: Optional[str] = None) -> RepositoryMetadata:
        """
        Recursively scans a local folder and returns structured RepositoryMetadata.
        """
        logger.info(f"Scanning repository path: {local_path}")
        
        repo_name = os.path.basename(local_path.rstrip("/\\"))
        if not repo_name or repo_name == local_path or repo_name.startswith("job_"):
            # Try to infer name from URL if name is generic job UUID
            if repo_url:
                repo_name = repo_url.split("/")[-1].replace(".git", "")
            else:
                repo_name = "analyzed_repo"

        # Determine Owner
        repository_owner = "Unknown"
        if repo_url:
            match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
            if match:
                repository_owner = match.group(1)

        default_branch = branch if branch else "Unknown"

        file_count = 0
        dir_count = 0
        ext_counts: Dict[str, int] = {}
        readme_present = False
        docker_support = False
        github_actions = False
        cicd = False
        tests_present = False
        package_managers: List[str] = []
        dependencies: Dict[str, str] = {}
        extensions: Dict[str, int] = {}
        all_file_infos: List[FileInfo] = []
        framework = "None"

        # Walk workspace
        for root, dirs, files in os.walk(local_path):
            # Prune directories in place
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            dir_count += len(dirs)

            # Check for tests folder
            for d in dirs:
                if d.lower() in ("test", "tests", "__tests__"):
                    tests_present = True

            # Check for GitHub Actions workflows folder
            if ".github" in root and "workflows" in root:
                github_actions = True
                cicd = True

            for file in files:
                file_count += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, local_path)
                _, ext = os.path.splitext(file.lower())
                
                # File extension counts
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1

                # Language extensions count
                if ext in self.lang_exts:
                    lang = self.lang_exts[ext]
                    ext_counts[lang] = ext_counts.get(lang, 0) + 1

                # Save file size metadata
                try:
                    size = os.path.getsize(file_path)
                    all_file_infos.append(FileInfo(path=rel_path, size=size))
                except Exception:
                    pass

                # README check
                if file.lower() in ("readme.md", "readme.txt", "readme"):
                    readme_present = True

                # Dockerfile check
                if file.lower() == "dockerfile" or file.lower().startswith("dockerfile."):
                    docker_support = True

                # Other CI/CD checks
                if file.lower() in (".gitlab-ci.yml", "travis.yml", "circleci.yml", "jenkinsfile"):
                    cicd = True

                # Package managers check
                if file.lower() == "package.json":
                    package_managers.append("npm/yarn")
                    self._parse_package_json(file_path, dependencies)
                elif file.lower() == "requirements.txt":
                    package_managers.append("pip")
                    self._parse_requirements_txt(file_path, dependencies)
                elif file.lower() == "cargo.toml":
                    package_managers.append("cargo")
                elif file.lower() == "go.mod":
                    package_managers.append("go mod")
                elif file.lower() == "pom.xml":
                    package_managers.append("maven")

        # Determine Primary Language
        primary_language = "Unknown"
        if ext_counts:
            primary_language = max(ext_counts, key=ext_counts.get) # type: ignore

        # Determine Framework
        framework = self._guess_framework(package_managers, dependencies, ext_counts)

        # Detect License
        license_type = self._detect_license(local_path)

        # Select Top 5 Largest Files
        all_file_infos.sort(key=lambda x: x.size, reverse=True)
        largest_files = all_file_infos[:5]

        return RepositoryMetadata(
            repository_name=repo_name,
            repository_owner=repository_owner,
            default_branch=default_branch,
            primary_language=primary_language,
            framework=framework,
            package_managers=package_managers,
            readme_present=readme_present,
            license=license_type,
            docker_support=docker_support,
            github_actions=github_actions,
            cicd=cicd,
            tests_present=tests_present,
            dependencies=dependencies,
            total_files=file_count,
            directories=dir_count,
            extensions=extensions,
            largest_files=largest_files
        )

    def _detect_license(self, path: str) -> str:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path) and item.lower() in ("license", "license.txt", "license.md", "copying"):
                try:
                    with open(item_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read(1000)
                    if "MIT" in text:
                        return "MIT"
                    elif "Apache" in text:
                        return "Apache 2.0"
                    elif "GNU" in text or "GPL" in text:
                        return "GPL"
                    elif "BSD" in text:
                        return "BSD"
                    elif "Mozilla" in text or "MPL" in text:
                        return "MPL"
                    else:
                        return "Custom License"
                except Exception:
                    return "Custom License"
        return "None"

    def _parse_package_json(self, file_path: str, dependencies: Dict[str, str]):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Combine dependencies and devDependencies
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            
            for k, v in {**deps, **dev_deps}.items():
                if len(dependencies) < 20: # Limit length
                    dependencies[k] = str(v)
        except Exception as e:
            logger.warn(f"Failed to parse package.json dependencies: {e}")

    def _parse_requirements_txt(self, file_path: str, dependencies: Dict[str, str]):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"==|>=|<=|~=", line)
                dep_name = parts[0].strip()
                dep_ver = parts[1].strip() if len(parts) > 1 else "latest"
                if len(dependencies) < 20:
                    dependencies[dep_name] = dep_ver
        except Exception as e:
            logger.warn(f"Failed to parse requirements.txt dependencies: {e}")

    def _guess_framework(self, package_managers: List[str], dependencies: Dict[str, str], lang_counts: Dict[str, int]) -> str:
        if "npm/yarn" in package_managers:
            if "next" in dependencies:
                return "Next.js"
            if "react" in dependencies:
                return "React"
            if "vue" in dependencies:
                return "Vue"
            if "@nestjs/core" in dependencies:
                return "NestJS"
            if "express" in dependencies:
                return "Express"

        if "pip" in package_managers:
            if "django" in dependencies or "Django" in dependencies:
                return "Django"
            if "fastapi" in dependencies or "FastAPI" in dependencies:
                return "FastAPI"
            if "flask" in dependencies or "Flask" in dependencies:
                return "Flask"

        return "None"

scanner_service = ScannerService()
