"""Skill Executor — executes skill scripts in isolated subprocess with virtual environment.

Provides secure, isolated execution of skill scripts via subprocess with
virtual environment. Implements JSON stdin/stdout protocol for communication.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import venv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from agenticai_sdk.skills.models import SkillManifest, SkillResult, SkillContext

logger = structlog.get_logger(__name__)


@dataclass
class SkillExecutorConfig:
    """Configuration for skill executor."""
    # Venv cache directory
    venv_cache_dir: Path = field(default_factory=lambda: Path.cwd() / ".agenticai" / "skill_venvs")
    # Default timeout in seconds
    default_timeout: int = 300
    # Default memory limit in MB
    default_memory_mb: int = 512
    # Default CPU limit (cores)
    default_cpu_cores: float = 1.0
    # Network access enabled by default
    network_enabled: bool = False
    # Enable docker mode if available
    use_docker: bool = False


class SkillExecutor:
    """Executes skill scripts in isolated subprocess with virtual environment."""
    
    def __init__(self, config: Optional[SkillExecutorConfig] = None):
        self.config = config or SkillExecutorConfig()
        self._venv_cache: Dict[str, Any] = {}
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """Ensure venv cache directory exists."""
        self.config.venv_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _compute_requirements_hash(self, requirements: List[str]) -> str:
        """Compute hash of requirements for venv caching."""
        req_str = "\n".join(sorted(requirements))
        return hashlib.sha256(req_str.encode()).hexdigest()[:16]
    
    async def _get_or_create_venv(self, skill: SkillManifest) -> Path:
        """Get or create virtual environment for skill."""
        requirements_list = self._parse_requirements(skill)
        req_hash = self._compute_requirements_hash(requirements_list)
        
        venv_name = f"{skill.name}-{req_hash}"
        venv_path = self.config.venv_cache_dir / venv_name
        
        # Check if venv exists and is valid
        if venv_path.exists() and (venv_path / "pyvenv.cfg").exists():
            logger.debug("venv_cache_hit", skill=skill.name, venv=str(venv_path))
            return venv_path
        
        # Create new venv
        logger.info("venv_creating", skill=skill.name, venv=str(venv_path))
        venv_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create virtual environment
            await self._create_venv(venv_path)
            
            # Install requirements
            if requirements_list:
                await self._install_requirements(venv_path, requirements_list)
            
            logger.info("venv_created", skill=skill.name, venv=str(venv_path))
            return venv_path
            
        except Exception as e:
            # Cleanup on failure
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            raise
    
    def _parse_requirements(self, skill: SkillManifest) -> List[str]:
        """Parse requirements from skill manifest."""
        requirements = []
        
        # Check for requirements.txt in scripts/
        req_file = skill.path / "scripts" / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)
            return requirements
        
        # Check compatibility field for requirements
        compat = skill.frontmatter.compatibility or ""
        if compat:
            # Try to parse as requirements
            for line in compat.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and any(c in line for c in "=<>~"):
                    requirements.append(line)
        
        return requirements
    
    async def _create_venv(self, venv_path: Path) -> None:
        """Create virtual environment."""
        # Use venv module to create environment
        venv.create(venv_path, with_pip=True)
        logger.debug("venv_created", path=str(venv_path))
    
    async def _install_requirements(self, venv_path: Path, requirements: List[str]) -> None:
        """Install requirements in virtual environment."""
        pip = venv_path / "bin" / "pip"
        if sys.platform == "win32":
            pip = venv_path / "Scripts" / "pip.exe"
        
        # Upgrade pip first
        await self._run_subprocess([str(pip), "install", "--upgrade", "pip"], cwd=venv_path.parent)
        
        # Install requirements
        for req in requirements:
            await self._run_subprocess([str(pip), "install", req], cwd=venv_path.parent)
    
    async def _run_subprocess(self, cmd: List[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run subprocess with timeout."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise asyncio.TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
    
    async def execute(
        self,
        skill: SkillManifest,
        script_name: str,
        params: Dict[str, Any],
        context: SkillContext,
        sandbox_mode: Optional[str] = None,
    ) -> SkillResult:
        """Execute a skill script in isolated environment."""
        mode = sandbox_mode or skill.frontmatter.sandbox or self.config.use_docker
        
        if mode == "docker":
            return await self._execute_docker(skill, script_name, params, context)
        else:
            return await self._execute_subprocess(skill, script_name, params, context)
    
    async def _execute_subprocess(
        self,
        skill: SkillManifest,
        script_name: str,
        params: Dict[str, Any],
        context: SkillContext,
    ) -> SkillResult:
        """Execute skill via subprocess with venv."""
        # Find script
        script_path = skill.path / "scripts" / script_name
        if not script_path.exists():
            return SkillResult(
                success=False,
                error=f"Script not found: {script_name}",
            )
        
        # Get or create venv
        venv_path = await self._get_or_create_venv(skill)
        python_bin = venv_path / "bin" / "python"
        if sys.platform == "win32":
            python_bin = venv_path / "Scripts" / "python.exe"
        
        # Prepare input JSON
        input_data = {
            "protocol_version": "0.3.0",
            "task_id": f"exec_{uuid.uuid4().hex[:8]}",
            "inputs": params,
            "context": context.model_dump(),
        }
        
        # Execute script
        start_time = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                str(python_bin),
                str(script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(skill.path),
                env={**os.environ, "PYTHONPATH": str(skill.path)},
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=json.dumps(input_data).encode()),
                timeout=skill.frontmatter.timeout_seconds or 300,
            )
            
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            
            if proc.returncode != 0:
                return SkillResult(
                    success=False,
                    error=stderr.decode() if stderr else "Script execution failed",
                    execution_time_ms=elapsed_ms,
                )
            
            # Parse output JSON
            try:
                output = json.loads(stdout.decode())
                return SkillResult(
                    success=output.get("success", False),
                    data=output.get("data"),
                    error=output.get("error"),
                    metadata=output.get("metadata", {}),
                    execution_time_ms=elapsed_ms,
                    tokens_used=output.get("tokens_used", 0),
                    cost=output.get("cost", 0.0),
                )
            except json.JSONDecodeError:
                return SkillResult(
                    success=False,
                    error=f"Invalid JSON output: {stdout.decode()[:500]}",
                    execution_time_ms=elapsed_ms,
                )
                
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"Script execution timed out",
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
    
    async def _execute_docker(
        self,
        skill: SkillManifest,
        script_name: str,
        params: Dict[str, Any],
        context: SkillContext,
    ) -> SkillResult:
        """Execute skill in Docker container."""
        # Check if Docker is available
        if not shutil.which("docker"):
            return SkillResult(
                success=False,
                error="Docker not available",
            )
        
        # Build Docker image if needed
        image_name = f"agenticai-skill-{skill.name}:latest"
        dockerfile = skill.path / "Dockerfile"
        
        if not dockerfile.exists():
            # Create default Dockerfile
            dockerfile_content = self._generate_dockerfile(skill)
            dockerfile.write_text(dockerfile_content)
        
        # Build image
        try:
            await self._run_subprocess([
                "docker", "build", "-t", image_name, "-f", str(dockerfile), str(skill.path)
            ])
        except Exception as e:
            return SkillResult(success=False, error=f"Docker build failed: {e}")
        
        # Prepare input
        input_data = {
            "protocol_version": "0.3.0",
            "task_id": f"exec_{uuid.uuid4().hex[:8]}",
            "inputs": params,
            "context": context.model_dump(),
        }
        
        # Run container
        start_time = time.perf_counter()
        try:
            # Get script path relative to skill root
            script_rel = skill.path / "scripts" / script_name
            if not script_rel.exists():
                return SkillResult(success=False, error=f"Script not found: {script_name}")
            
            # Run container
            cmd = [
                "docker", "run", "--rm",
                "--network", "none" if not self.config.network_enabled else "bridge",
                "--memory", f"{self.config.default_memory_mb}m",
                "--cpus", str(self.config.default_cpu_cores),
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m",
                "-v", f"{skill.path}:/skill:ro",
                "-i",
                image_name,
                "python", f"/skill/scripts/{script_name}",
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=json.dumps(input_data).encode()),
                timeout=300,
            )
            
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            
            if proc.returncode != 0:
                return SkillResult(
                    success=False,
                    error=stderr.decode() if stderr else "Docker execution failed",
                    execution_time_ms=elapsed_ms,
                )
            
            try:
                output = json.loads(stdout.decode())
                return SkillResult(
                    success=output.get("success", False),
                    data=output.get("data"),
                    error=output.get("error"),
                    metadata=output.get("metadata", {}),
                    execution_time_ms=elapsed_ms,
                    tokens_used=output.get("tokens_used", 0),
                    cost=output.get("cost", 0.0),
                )
            except json.JSONDecodeError:
                return SkillResult(
                    success=False,
                    error=f"Invalid JSON output: {stdout.decode()[:500]}",
                    execution_time_ms=elapsed_ms,
                )
                
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error="Execution timed out",
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
    
    def _generate_dockerfile(self, skill: SkillManifest) -> str:
        """Generate Dockerfile for skill."""
        requirements = self._parse_requirements(skill)
        
        dockerfile = f"""FROM python:3.12-slim

WORKDIR /skill

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy skill files
COPY . /skill

# Install Python dependencies
"""
        if requirements:
            dockerfile += "COPY scripts/requirements.txt /tmp/requirements.txt\n"
            dockerfile += "RUN pip install --no-cache-dir -r /tmp/requirements.txt\n"
        
        dockerfile += """
# Create non-root user
RUN useradd -m -u 1000 skilluser
USER skilluser

# Default command
CMD ["python", "-c", "import sys; print('Skill container ready')]
"""
        return dockerfile


# Factory function
def create_skill_executor(config: Optional[SkillExecutorConfig] = None) -> "SkillExecutor":
    """Factory function to create a SkillExecutor."""
    return SkillExecutor(config)