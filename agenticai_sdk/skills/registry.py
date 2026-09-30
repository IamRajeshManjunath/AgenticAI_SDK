"""Skills Registry — central registry for all skills with caching, hot reload, and deepagents integration."""

from __future__ import annotations

import asyncio
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import structlog
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .loader import SkillsLoader, create_skills_loader
from .models import (
    RemoteSkillSource,
    SkillManifest,
    SkillMetadata,
    SkillSource,
    SkillsConfig,
)

logger = structlog.get_logger(__name__)


class SkillChangeHandler(FileSystemEventHandler):
    """File system event handler for skill directory changes."""
    
    def __init__(self, registry: "SkillsRegistry"):
        self.registry = registry
        self._debounce: Dict[str, float] = {}
    
    def on_any_event(self, event):
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if path.name != "SKILL.md":
            return
        
        # Debounce rapid events
        now = time.time()
        key = str(path)
        if key in self._debounce and now - self._debounce[key] < 1.0:
            return
        self._debounce[key] = now
        
        skill_name = path.parent.name
        logger.info("skill_file_changed", skill=skill_name, event=event.event_type)
        
        # Schedule reload
        self.registry.schedule_reload(skill_name)


class SkillsRegistry:
    """Central registry for all skills with caching, hot reload, and deepagents integration."""
    
    def __init__(self, config: Optional[SkillsConfig] = None, project_root: Optional[Path] = None):
        self.config = config or SkillsConfig()
        self.project_root = project_root or Path.cwd()
        self.loader = create_skills_loader(self.config, self.project_root)
        
        self._skills: Dict[str, SkillManifest] = {}  # name -> manifest
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._deepagents_sources: List[str] = []
        
        self._lock = threading.RLock()
        self._reload_pending: Dict[str, bool] = {}
        self._reload_task: Optional[asyncio.Task] = None
        self._last_reload = datetime.utcnow()
        
        # File watching
        self._observer: Optional[Observer] = None
        self._handler: Optional[SkillChangeHandler] = None
        
        # Callbacks
        self._on_reload_callbacks: List[Callable[[List[SkillManifest]], Any]] = []
    
    def initialize(self) -> List[SkillManifest]:
        """Initialize registry by discovering all skills."""
        with self._lock:
            skills = self.loader.discover_skills()
            self._skills = {s.name: s for s in skills}
            self._rebuild_caches()
            self._start_watching()
            logger.info("skills_registry_initialized", count=len(skills))
            return skills
    
    def _rebuild_caches(self) -> None:
        """Rebuild metadata cache and deepagents sources."""
        self._metadata_cache = {
            name: SkillMetadata.from_manifest(manifest)
            for name, manifest in self._skills.items()
        }
        
        # Deep agents sources are paths to skill directories
        self._deepagents_sources = [
            str(manifest.path) for manifest in self._skills.values()
        ]
    
    def _start_watching(self) -> None:
        """Start file system watcher for hot reload."""
        if not self.config.watch_for_changes:
            return
        
        skills_dir = self.project_root / self.config.skills_dir
        if not skills_dir.exists():
            return
        
        self._handler = SkillChangeHandler(self)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(skills_dir), recursive=True)
        self._observer.start()
        logger.info("skills_watcher_started", path=str(skills_dir))
    
    def stop_watching(self) -> None:
        """Stop file system watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("skills_watcher_stopped")
    
    def schedule_reload(self, skill_name: str) -> None:
        """Schedule a skill for reload (debounced)."""
        self._reload_pending[skill_name] = True
        
        # Cancel existing reload task
        if self._reload_task and not self._reload_task.done():
            self._reload_task.cancel()
        
        # Schedule new reload
        self._reload_task = asyncio.create_task(self._process_reloads())
    
    async def _process_reloads(self) -> None:
        """Process pending reloads after debounce."""
        await asyncio.sleep(1.5)  # Debounce
        
        with self._lock:
            reload_names = list(self._reload_pending.keys())
            self._reload_pending.clear()
        
        if not reload_names:
            return
        
        logger.info("skills_reload_triggered", skills=reload_names)
        
        # Reload affected skills
        for name in reload_names:
            self._reload_skill(name)
        
        self._last_reload = datetime.utcnow()
        
        # Notify callbacks
        for callback in self._on_reload_callbacks:
            try:
                await callback(list(self._skills.values()))
            except Exception as exc:
                logger.error("reload_callback_failed", error=str(exc))
    
    def _reload_skill(self, name: str) -> bool:
        """Reload a single skill from disk."""
        skill_dir = self.project_root / self.config.skills_dir / name
        
        if not skill_dir.exists():
            # Skill was deleted
            if name in self._skills:
                del self._skills[name]
                logger.info("skill_removed", skill=name)
            return False
        
        try:
            manifest = self.loader.load_skill(name)
            if manifest:
                self._skills[name] = manifest
                logger.info("skill_reloaded", skill=name)
                return True
            else:
                logger.warning("skill_reload_failed_no_manifest", skill=name)
                return False
        except Exception as exc:
            logger.error("skill_reload_error", skill=name, error=str(exc))
            return False
    
    def register_reload_callback(self, callback: Callable[[List[SkillManifest]], Any]) -> None:
        """Register a callback to be called on skill reload."""
        self._on_reload_callbacks.append(callback)
    
    def get_skill(self, name: str) -> Optional[SkillManifest]:
        """Get skill manifest by name."""
        with self._lock:
            return self._skills.get(name)
    
    def get_skill_metadata(self, name: str) -> Optional[SkillMetadata]:
        """Get skill metadata (name + description only)."""
        with self._lock:
            return self._metadata_cache.get(name)
    
    def list_skills(self) -> List[SkillMetadata]:
        """List all skill metadata for system prompt."""
        with self._lock:
            return list(self._metadata_cache.values())
    
    def list_manifests(self) -> List[SkillManifest]:
        """List all skill manifests."""
        with self._lock:
            return list(self._skills.values())
    
    def get_deepagents_sources(self) -> List[str]:
        """Get skill directory paths for deepagents registration."""
        with self._lock:
            return list(self._deepagents_sources)
    
    def refresh(self) -> List[SkillManifest]:
        """Full refresh of all skills."""
        with self._lock:
            skills = self.loader.discover_skills()
            self._skills = {s.name: s for s in skills}
            self._rebuild_caches()
            self._last_reload = datetime.utcnow()
            logger.info("skills_registry_refreshed", count=len(skills))
            return skills
    
    async def sync_remotes(self) -> List[SkillManifest]:
        """Sync remote skill sources."""
        new_skills = await self.loader.sync_remotes()
        
        with self._lock:
            for skill in new_skills:
                self._skills[skill.name] = skill
            self._rebuild_caches()
        
        return new_skills
    
    def create_skill(self, name: str, frontmatter: Dict[str, Any], content: str, files: Optional[Dict[str, str]] = None) -> SkillManifest:
        """Create a new skill directory with SKILL.md and supporting files."""
        skills_dir = self.project_root / self.config.skills_dir
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        skill_dir = skills_dir / name
        if skill_dir.exists():
            raise ValueError(f"Skill '{name}' already exists")
        
        skill_dir.mkdir(parents=True)
        
        # Write SKILL.md
        skill_md = skill_dir / "SKILL.md"
        yaml_frontmatter = "---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n\n"
        skill_md.write_text(yaml_frontmatter + content, encoding="utf-8")
        
        # Write supporting files
        if files:
            for rel_path, file_content in files.items():
                file_path = skill_dir / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_content, encoding="utf-8")
        
        # Load and register
        manifest = self.loader.load_skill(name)
        if not manifest:
            raise ValueError(f"Failed to load newly created skill: {name}")
        
        with self._lock:
            self._skills[name] = manifest
            self._rebuild_caches()
        
        return manifest
    
    def update_skill(self, name: str, frontmatter: Optional[Dict[str, Any]] = None, content: Optional[str] = None, files: Optional[Dict[str, str]] = None) -> SkillManifest:
        """Update an existing skill."""
        skill_dir = self.project_root / self.config.skills_dir / name
        
        if not skill_dir.exists():
            raise ValueError(f"Skill '{name}' not found")
        
        skill_md = skill_dir / "SKILL.md"
        
        # Read existing
        existing_content = skill_md.read_text(encoding="utf-8")
        existing_frontmatter, existing_body = self.loader._parse_frontmatter(existing_content)
        
        # Merge updates
        new_frontmatter = {**existing_frontmatter, **(frontmatter or {})}
        new_content = content if content is not None else existing_body
        
        # Write SKILL.md
        yaml_frontmatter = "---\n" + "\n".join(f"{k}: {v}" for k, v in new_frontmatter.items()) + "\n---\n\n"
        skill_md.write_text(yaml_frontmatter + new_content, encoding="utf-8")
        
        # Update supporting files
        if files:
            for rel_path, file_content in files.items():
                file_path = skill_dir / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_content, encoding="utf-8")
        
        # Reload and update cache
        manifest = self.loader.load_skill(name)
        if not manifest:
            raise ValueError(f"Failed to load updated skill: {name}")
        
        with self._lock:
            self._skills[name] = manifest
            self._rebuild_caches()
        
        return manifest
    
    def delete_skill(self, name: str) -> bool:
        """Delete a skill directory."""
        skill_dir = self.project_root / self.config.skills_dir / name
        
        if not skill_dir.exists():
            return False
        
        shutil.rmtree(skill_dir)
        
        with self._lock:
            if name in self._skills:
                del self._skills[name]
            self._rebuild_caches()
        
        logger.info("skill_deleted", skill=name)
        return True
    
    def validate_skill(self, name: str) -> List[str]:
        """Validate a skill against Agent Skills spec."""
        manifest = self.get_skill(name)
        if not manifest:
            return [f"Skill '{name}' not found"]
        
        return self.loader.validate_skill(manifest)
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the skills registry."""
        return {
            "status": "healthy",
            "skills_count": len(self._skills),
            "last_reload": self._last_reload.isoformat(),
            "watching": self._observer is not None and self._observer.is_alive(),
            "skills": [{"name": m.name, "source": m.source.value, "modified": m.modified_at.isoformat()} for m in self._skills.values()],
        }


# Global registry instance
_skills_registry: Optional[SkillsRegistry] = None


def get_skills_registry(config: Optional[SkillsConfig] = None, project_root: Optional[Path] = None) -> SkillsRegistry:
    """Get or create global skills registry."""
    global _skills_registry
    if _skills_registry is None:
        _skills_registry = SkillsRegistry(config, project_root)
    return _skills_registry


def set_skills_registry(registry: SkillsRegistry) -> None:
    """Set global skills registry (for testing)."""
    global _skills_registry
    _skills_registry = registry