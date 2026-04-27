"""Plugin Loader - Auto-loads all plugins from the plugins folder.

Drop any *_plugin.py file into the plugins/ directory and it will
be automatically discovered and loaded. No editing main.py ever.
"""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.plugins.loader")

PLUGINS_DIR = Path(__file__).parent


class PluginBase:
    """Base class for all Jiro AI plugins.

    Create a new plugin:
    1. Create a file named your_thing_plugin.py in plugins/
    2. Create a class that inherits from PluginBase
    3. Set name, description, triggers
    4. Implement execute()
    5. Done! It loads automatically.
    """

    name: str = "unnamed"
    description: str = ""
    triggers: list[str] = []
    version: str = "1.0.0"
    requires_api_keys: list[str] = []

    def __init__(self, config: dict, ai_engine=None):
        self.config = config
        self.ai_engine = ai_engine
        self.enabled = True

    async def execute(self, command: str, context: Optional[dict] = None) -> str:
        raise NotImplementedError

    def matches(self, text: str) -> bool:
        return any(t.lower() in text.lower() for t in self.triggers)

    def get_info(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "triggers": self.triggers, "version": self.version,
            "enabled": self.enabled, "requires_api_keys": self.requires_api_keys,
        }


class PluginLoader:
    """Discovers and loads plugins dynamically."""

    def __init__(self, config: dict, ai_engine=None, self_fixer=None):
        self._config = config
        self._ai_engine = ai_engine
        self._self_fixer = self_fixer
        self.plugins: dict[str, PluginBase] = {}

    def load_all(self) -> dict[str, PluginBase]:
        """Discover and load all *_plugin.py files."""
        for path in PLUGINS_DIR.glob("*_plugin.py"):
            if path.name.startswith("_"):
                continue
            self._load_one(path)
        logger.info("Loaded %d plugins", len(self.plugins))
        return self.plugins

    def _load_one(self, path: Path) -> Optional[PluginBase]:
        try:
            spec = importlib.util.spec_from_file_location(f"plugins.{path.stem}", path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (inspect.isclass(attr) and issubclass(attr, PluginBase)
                        and attr is not PluginBase):
                    instance = attr(self._config, self._ai_engine)
                    self.plugins[instance.name] = instance
                    logger.info("Loaded plugin: %s v%s", instance.name, instance.version)
                    return instance
        except Exception as e:
            logger.error("Plugin load error '%s': %s", path.name, e)
            if self._self_fixer:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._self_fixer.fix_plugin(path, e))
                    else:
                        loop.run_until_complete(self._self_fixer.fix_plugin(path, e))
                except Exception:
                    pass
        return None

    def reload_all(self) -> dict[str, PluginBase]:
        self.plugins.clear()
        return self.load_all()

    def find_match(self, text: str) -> Optional[PluginBase]:
        for p in self.plugins.values():
            if p.enabled and p.matches(text):
                return p
        return None

    def get(self, name: str) -> Optional[PluginBase]:
        return self.plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [p.get_info() for p in self.plugins.values()]
