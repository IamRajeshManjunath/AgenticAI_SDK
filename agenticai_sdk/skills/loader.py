"""Skills Loader — discovers and loads SKILL.md files from disk and remote sources.

Follows the Agent Skills specification (agentskills.io):
- Each skill is a directory with SKILL.md (YAML frontmatter + markdown)
- Supporting files in scripts/, references/, assets/, templates/
- Remote sources: git repos, S3 buckets, LangSmith Fleet
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
import yaml

from .models import (
    RemoteSkillSource,
    SkillFile,
    SkillFileType,
    SkillFrontmatter,
    SkillManifest,
    SkillSource,
    SkillsConfig,
)

logger = structlog.get_logger(__name__)

# Frontmatter regex - matches YAML frontmatter at start of file
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

# Skill directory classification
SUPPORTING_DIRS = {
    "scripts": SkillFileType.SCRIPT,
    "references": SkillFileType.REFERENCE,
    "assets": SkillFileType.ASSET,
    "templates": SkillFileType.TEMPLATE,
}


class SkillValidationError(Exception):
    """Raised when skill validation fails."""
    pass


class SkillsLoader:
    """Loads and validates skills from disk and remote sources."""
    
    def __init__(self, config: SkillsConfig, project_root: Optional[Path] = None):
        self.config = config
        self.project_root = project_root or Path.cwd()
        self._remote_cache: Dict[str, Path] = {}
    
    def discover_skills(self) -> List[SkillManifest]:
        """Discover all skills from local and remote sources."""
        skills: List[SkillManifest] = []
        errors: List[Tuple[str, Exception]] = []
        
        # 1. Local skills
        local_skills = self._discover_local_skills()
        skills.extend(local_skills)
        
        # 2. Remote skills
        if self.config.remote_sources:
            for remote in self.config.remote_sources:
                try:
                    remote_skills = self._sync_and_discover_remote(remote)
                    skills.extend(remote_skills)
                except Exception as exc:
                    logger.warning("remote_skill_sync_failed", source=remote.type, url=remote.url, error=str(exc))
                    errors.append((f"{remote.type}:{remote.url}", exc))
        
        if errors and self.config.validation_mode == "strict":
            raise SkillValidationError(f"Failed to load {len(errors)} skill sources: {errors}")
        
        return skills
    
    def _discover_local_skills(self) -> List[SkillManifest]:
        """Discover skills from local skills directory."""
        skills_dir = self.project_root / self.config.skills_dir
        skills: List[SkillManifest] = []
        
        if not skills_dir.exists():
            logger.info("skills_dir_not_found", path=str(skills_dir))
            return skills
        
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                logger.debug("skill_md_missing", skill_dir=entry.name)
                continue
            
            try:
                manifest = self._load_skill_from_dir(entry, SkillSource.LOCAL)
                if manifest:
                    skills.append(manifest)
            except Exception as exc:
                logger.warning("skill_load_failed", skill=entry.name, error=str(exc))
                if self.config.validation_mode == "strict":
                    raise
        
        logger.info("local_skills_discovered", count=len(skills))
        return skills
    
    def _load_skill_from_dir(self, skill_dir: Path, source: SkillSource, source_url: Optional[str] = None) -> Optional[SkillManifest]:
        """Load a single skill from a directory."""
        skill_md_path = skill_dir / "SKILL.md"
        
        if not skill_md_path.is_file():
            return None
        
        # Read and parse SKILL.md
        content = skill_md_path.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(content)
        
        # Validate frontmatter
        frontmatter_model = SkillFrontmatter(**frontmatter)
        
        # Verify name matches directory
        if frontmatter_model.name != skill_dir.name:
            raise SkillValidationError(
                f"Skill name '{frontmatter_model.name}' does not match directory '{skill_dir.name}'"
            )
        
        # Discover supporting files
        supporting_files = self._discover_supporting_files(skill_dir)
        
        # Get modification time
        modified_at = datetime.fromtimestamp(skill_md_path.stat().st_mtime)
        
        manifest = SkillManifest(
            frontmatter=frontmatter_model,
            content=body,
            path=skill_dir,
            files=supporting_files,
            modified_at=modified_at,
            source=source,
            source_url=source_url,
        )
        
        return manifest
    
    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from SKILL.md content."""
        match = FRONTMATTER_PATTERN.match(content.strip())
        if not match:
            raise SkillValidationError("SKILL.md missing required YAML frontmatter (---)")
        
        frontmatter_yaml = match.group(1)
        body = match.group(2).strip()
        
        frontmatter = yaml.safe_load(frontmatter_yaml) or {}
        return frontmatter, body
    
    def _discover_supporting_files(self, skill_dir: Path) -> List[SkillFile]:
        """Discover supporting files in standard skill subdirectories."""
        files: List[SkillFile] = []
        
        for subdir, file_type in SUPPORTING_DIRS.items():
            subdir_path = skill_dir / subdir
            if not subdir_path.is_dir():
                continue
            
            for file_path in subdir_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    rel_path = file_path.relative_to(skill_dir).as_posix()
                    size = file_path.stat().st_size
                    
                    files.append(SkillFile(
                        path=rel_path,
                        content=content,
                        type=file_type,
                        size_bytes=size,
                    ))
                except UnicodeDecodeError:
                    # Binary file - store as base64 or skip
                    logger.debug("skipping_binary_file", file=str(file_path))
        
        return files
    
    def _sync_and_discover_remote(self, remote: RemoteSkillSource) -> List[SkillManifest]:
        """Sync remote source and discover skills."""
        if remote.type == "git":
            return self._sync_git_remote(remote)
        elif remote.type == "s3":
            return self._sync_s3_remote(remote)
        elif remote.type == "fleet":
            return self._sync_fleet_remote(remote)
        else:
            logger.warning("unknown_remote_type", type=remote.type)
            return []
    
    def _sync_git_remote(self, remote: RemoteSkillSource) -> List[SkillManifest]:
        """Clone/pull git repository and discover skills."""
        try:
            import git
        except ImportError:
            logger.warning("gitpython_not_installed", required_for="git remote skills")
            return []
        
        cache_key = f"git:{remote.url}:{remote.branch}"
        repo_path = self._get_remote_cache_path(cache_key)
        
        skills_dir = repo_path / remote.path
        if not skills_dir.exists():
            logger.warning("skills_path_not_found_in_repo", path=remote.path)
            return []
        
        return self._discover_skills_in_dir(skills_dir, SkillSource.GIT, remote.url)
    
    def _sync_s3_remote(self, remote: RemoteSkillSource) -> List[SkillManifest]:
        """Download from S3 and discover skills."""
        try:
            import boto3
        except ImportError:
            logger.warning("boto3_not_installed", required_for="s3 remote skills")
            return []
        
        # S3 implementation would go here
        # For now, return empty list
        logger.warning("s3_remote_not_implemented")
        return []
    
    def _sync_fleet_remote(self, remote: RemoteSkillSource) -> List[SkillManifest]:
        """Sync from LangSmith Fleet."""
        try:
            from langsmith import Client as LangSmithClient
        except ImportError:
            logger.warning("langsmith_not_installed", required_for="fleet remote skills")
            return []
        
        # Fleet implementation would go here
        logger.warning("fleet_remote_not_implemented")
        return []
    
    def _discover_skills_in_dir(self, skills_dir: Path, source: SkillSource, source_url: Optional[str] = None) -> List[SkillManifest]:
        """Discover skills in a given directory."""
        skills: List[SkillManifest] = []
        
        if not skills_dir.exists():
            return skills
        
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                continue
            
            try:
                manifest = self._load_skill_from_dir(entry, source, source_url)
                if manifest:
                    skills.append(manifest)
            except Exception as exc:
                logger.warning("skill_load_failed", skill=entry.name, error=str(exc))
                if self.config.validation_mode == "strict":
                    raise
        
        return skills
    
    def _get_remote_cache_path(self, cache_key: str) -> Path:
        """Get cached path for remote source."""
        if cache_key in self._remote_cache:
            return self._remote_cache[cache_key]
        
        cache_dir = self.project_root / ".agenticai" / "skills_cache" / cache_key.replace(":", "_").replace("/", "_")
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._remote_cache[cache_key] = cache_dir
        return cache_dir
    
    def load_skill(self, name: str) -> Optional[SkillManifest]:
        """Load a specific skill by name."""
        # Check local first
        skill_dir = self.project_root / self.config.skills_dir / name
        manifest = self._load_skill_from_dir(skill_dir, SkillSource.LOCAL)
        if manifest:
            return manifest
        
        # Check remotes
        for remote in self.config.remote_sources:
            try:
                remote_skills = self._sync_and_discover_remote(remote)
                for skill in remote_skills:
                    if skill.name == name:
                        return skill
            except Exception:
                continue
        
        return None
    
    async def sync_remotes(self) -> List[SkillManifest]:
        """Sync all remote sources and return new skills."""
        all_skills: List[SkillManifest] = []
        
        for remote in self.config.remote_sources:
            try:
                skills = self._sync_and_discover_remote(remote)
                all_skills.extend(skills)
            except Exception as exc:
                logger.warning("remote_sync_failed", source=remote.type, error=str(exc))
        
        return all_skills
    
    def validate_skill(self, manifest: SkillManifest) -> List[str]:
        """Validate a skill against the Agent Skills spec."""
        errors: List[str] = []
        
        # Name validation
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", manifest.name):
            errors.append(f"Invalid skill name: {manifest.name}")
        
        # Description validation
        if not manifest.description or len(manifest.description) > 1024:
            errors.append("Description must be 1-1024 characters")
        
        # Directory name match
        if manifest.path.name != manifest.name:
            errors.append(f"Directory name '{manifest.path.name}' doesn't match skill name '{manifest.name}'")
        
        # Frontmatter required fields
        if not manifest.frontmatter.name or not manifest.frontmatter.description:
            errors.append("Frontmatter must contain 'name' and 'description'")
        
        return errors


def create_skills_loader(config: Optional[SkillsConfig] = None, project_root: Optional[Path] = None) -> SkillsLoader:
    """Factory function to create a SkillsLoader."""
    if config is None:
        config = SkillsConfig()
    return SkillsLoader(config, project_root)