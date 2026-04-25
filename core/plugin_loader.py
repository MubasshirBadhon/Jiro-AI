"""Dynamic Plugin Loader for Jiro AI.

Automatically discovers and loads plugins from the plugins/ directory.
No need to edit main.py when adding new plugins - just drop a .py file
into the plugins/ folder and it will be loaded automatically.
"""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.plugin_loader")

PLUGINS_DIR = Path(__file__).parent.parent / "plugins"


class PluginBase:
    """Base class for all Jiro AI plugins.

    All plugins must inherit from this class and implement:
    - name: str - Plugin display name
    - description: str - What the plugin does
    - triggers: list[str] - Keywords/phrases that activate this plugin
    - execute(command, context) - Main execution method
    """

    name: str = "unnamed_plugin"
    description: str = "No description"
    triggers: list[str] = []
    version: str = "1.0.0"
    requires_api_keys: list[str] = []

    def __init__(self, config_manager, ai_engine=None):
        self.config = config_manager
        self.ai_engine = ai_engine
        self.enabled = True

    async def execute(self, command: str, context: Optional[dict] = None) -> str:
        """Execute the plugin's main functionality."""
        raise NotImplementedError("Plugins must implement execute()")

    def matches(self, text: str) -> bool:
        """Check if user input matches this plugin's triggers."""
        text_lower = text.lower()
        return any(trigger.lower() in text_lower for trigger in self.triggers)

    def get_info(self) -> dict:
        """Return plugin information."""
        return {
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "version": self.version,
            "enabled": self.enabled,
            "requires_api_keys": self.requires_api_keys,
        }


class PluginLoader:
    """Dynamically loads and manages plugins from the plugins/ directory."""

    def __init__(self, config_manager, ai_engine=None, plugins_dir: Optional[Path] = None):
        self.config = config_manager
        self.ai_engine = ai_engine
        self.plugins_dir = plugins_dir or PLUGINS_DIR
        self.plugins: dict[str, PluginBase] = {}
        self._watchers = []

    def discover_plugins(self) -> list[str]:
        """Discover all plugin files in the plugins directory."""
        if not self.plugins_dir.exists():
            logger.warning("Plugins directory not found: %s", self.plugins_dir)
            return []

        plugin_files = []
        for path in self.plugins_dir.glob("*_plugin.py"):
            if path.name.startswith("_"):
                continue
            plugin_files.append(path.stem)

        logger.info("Discovered %d plugin files: %s", len(plugin_files), plugin_files)
        return plugin_files

    def load_plugin(self, module_name: str) -> Optional[PluginBase]:
        """Load a single plugin by module name."""
        try:
            module_path = self.plugins_dir / f"{module_name}.py"
            if not module_path.exists():
                logger.error("Plugin file not found: %s", module_path)
                return None

            spec = importlib.util.spec_from_file_location(
                f"plugins.{module_name}", module_path
            )
            if spec is None or spec.loader is None:
                logger.error("Failed to create spec for: %s", module_name)
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    inspect.isclass(attr)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin_instance = attr(self.config, self.ai_engine)
                    self.plugins[plugin_instance.name] = plugin_instance
                    logger.info(
                        "Loaded plugin: %s v%s",
                        plugin_instance.name,
                        plugin_instance.version,
                    )
                    return plugin_instance

            logger.warning("No PluginBase subclass found in: %s", module_name)
            return None

        except Exception as e:
            logger.error("Failed to load plugin '%s': %s", module_name, e)
            return None

    def load_all(self) -> dict[str, PluginBase]:
        """Load all discovered plugins."""
        plugin_modules = self.discover_plugins()
        for module_name in plugin_modules:
            self.load_plugin(module_name)
        logger.info("Loaded %d plugins total", len(self.plugins))
        return self.plugins

    def reload_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Reload a specific plugin (hot-reload)."""
        for mod_name, plugin in list(self.plugins.items()):
            if plugin.name == plugin_name:
                del self.plugins[plugin_name]
                break

        module_files = self.discover_plugins()
        for mod_name in module_files:
            loaded = self.load_plugin(mod_name)
            if loaded and loaded.name == plugin_name:
                return loaded
        return None

    def reload_all(self) -> dict[str, PluginBase]:
        """Reload all plugins."""
        self.plugins.clear()
        return self.load_all()

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a plugin by name."""
        return self.plugins.get(name)

    def find_matching_plugin(self, text: str) -> Optional[PluginBase]:
        """Find a plugin that matches the given input text."""
        for plugin in self.plugins.values():
            if plugin.enabled and plugin.matches(text):
                return plugin
        return None

    async def execute_plugin(self, plugin_name: str, command: str,
                             context: Optional[dict] = None) -> str:
        """Execute a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return f"Plugin '{plugin_name}' not found."
        if not plugin.enabled:
            return f"Plugin '{plugin_name}' is disabled."

        try:
            return await plugin.execute(command, context)
        except Exception as e:
            logger.error("Plugin '%s' execution failed: %s", plugin_name, e)
            return f"Plugin error: {e}"

    def list_plugins(self) -> list[dict]:
        """List all loaded plugins and their info."""
        return [plugin.get_info() for plugin in self.plugins.values()]

    def enable_plugin(self, name: str) -> bool:
        plugin = self.get_plugin(name)
        if plugin:
            plugin.enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        plugin = self.get_plugin(name)
        if plugin:
            plugin.enabled = False
            return True
        return False
