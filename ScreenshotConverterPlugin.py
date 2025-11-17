# ScreenshotConverterPlugin.py
# Version 1.5.0 - Using side effects as recommended by developers
# Author: The Device Null

from typing import Any
from datetime import datetime
from pathlib import Path
from lib.PluginHelper import PluginHelper
from lib.PluginBase import PluginBase, PluginManifest
from lib.PluginSettingDefinitions import (
    PluginSettings, SettingsGrid, ParagraphSetting, TextSetting, SelectSetting
)
from lib.Event import Event, GameEvent
from lib.Projections import Location
from lib.Logger import log
from PIL import Image
import os
import threading
import traceback


class ScreenshotConverterPlugin(PluginBase):
    """Converts Elite Dangerous BMP screenshots to PNG/JPG when a Screenshot event occurs."""

    def __init__(self, plugin_manifest: PluginManifest):
        try:
            super().__init__(plugin_manifest)
            self.plugin_helper: PluginHelper | None = None
            log("info", f"[ScreenshotConverter] Plugin initialized with manifest: {plugin_manifest.name} v{plugin_manifest.version}")
            
            # Track processed screenshots to avoid duplicates
            self.processed_screenshots = set()

            self.settings_config = PluginSettings(
                key="ScreenshotConverterPlugin",
                label="Screenshot Converter",
                icon="image",
                grids=[
                    SettingsGrid(
                        key="info",
                        label="Information",
                        fields=[ParagraphSetting(
                            key="desc",
                            label="Description",
                            type="paragraph",
                            readonly=True,
                            content="Automatically converts Elite Dangerous BMP screenshots into PNG or JPG when the Screenshot event is detected."
                        )]
                    ),
                    SettingsGrid(
                        key="settings",
                        label="Conversion Settings",
                        fields=[
                            ParagraphSetting(
                                key="screenshot_path_desc",
                                label="Screenshot folder",
                                type="paragraph",
                                readonly=True,
                                content="Set the directory where Elite Dangerous saves screenshots."
                            ),
                            TextSetting(
                                key="screenshot_path",
                                label="Screenshot folder",
                                type="text",
                                default_value=r"%USERPROFILE%\\Pictures\\Frontier Developments\\Elite Dangerous"
                            ),
                            SelectSetting(
                                key="target_format",
                                label="Output format",
                                type="select",
                                default_value="png",
                                select_options=[
                                    {"key": "png", "label": "PNG", "value": "png"},
                                    {"key": "jpg", "label": "JPG", "value": "jpg"}
                                ]
                            )
                        ]
                    )
                ]
            )
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error in __init__: {e}\n{traceback.format_exc()}")

    def on_plugin_helper_ready(self, helper: PluginHelper):
        """Called when the plugin helper is ready."""
        try:
            self.plugin_helper = helper
            
            # Register a side effect to handle game events
            helper.register_sideeffect(self.handle_game_event)
            
            log("info", "[ScreenshotConverter] Plugin loaded and waiting for Screenshot events.")
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error in on_plugin_helper_ready: {e}\n{traceback.format_exc()}")

    def handle_game_event(self, event: Event, context: dict[str, Any]):
        """Handle game events, specifically looking for Screenshot events"""
        try:
            # Check if it's a GameEvent
            if not isinstance(event, GameEvent):
                return
                
            # Check if it has content with an event field
            if not hasattr(event, "content") or not isinstance(event.content, dict):
                return
                
            # Check if it's a Screenshot event
            if event.content.get("event") != "Screenshot":
                return
                
            log("info", f"[ScreenshotConverter] Screenshot event detected: {event.content}")
            
            # Process in a separate thread to avoid blocking
            threading.Thread(
                target=self.process_screenshot,
                args=(event,),
                daemon=True
            ).start()
            
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error in handle_game_event: {e}\n{traceback.format_exc()}")

    def process_screenshot(self, event: GameEvent):
        """Process a screenshot event in a separate thread"""
        try:
            filename = event.content.get("Filename")
            if not filename:
                log("warn", "[ScreenshotConverter] Screenshot event missing Filename.")
                return

            if not self.plugin_helper:
                log("error", "[ScreenshotConverter] PluginHelper not ready.")
                return

            # Check if we've already processed this screenshot
            if filename in self.processed_screenshots:
                log("debug", f"[ScreenshotConverter] Already processed: {filename}")
                return
                
            self.processed_screenshots.add(filename)
            log("info", f"[ScreenshotConverter] Processing screenshot: {filename}")

            # Get screenshot directory from settings
            screenshot_path_setting = (
                self.plugin_helper.get_plugin_setting("ScreenshotConverterPlugin", "settings", "screenshot_path")
                or r"%USERPROFILE%\\Pictures\\Frontier Developments\\Elite Dangerous"
            )
            screenshot_dir = Path(os.path.expandvars(screenshot_path_setting))
            
            # Resolve the actual path to the BMP file
            bmp_path = Path(os.path.expandvars(filename)).expanduser().resolve()
            if "ED_Pictures" in str(bmp_path):
                relative_name = str(bmp_path).split("ED_Pictures")[-1].lstrip("\\/")
                bmp_path = Path(screenshot_dir) / relative_name
            bmp_path = bmp_path.expanduser().resolve()
            
            log("info", f"[ScreenshotConverter] Resolved path: {bmp_path}")

            # Validate the file
            if not bmp_path.exists():
                log("debug", f"[ScreenshotConverter] File not found: {bmp_path}")
                return
                
            if bmp_path.stat().st_mtime < (datetime.now().timestamp() - 300):
                log("debug", f"[ScreenshotConverter] Ignored stale screenshot: {bmp_path}")
                return

            # Get current star system
            current_system = self.get_current_star_system()
            
            # Convert the screenshot
            self.convert_screenshot(bmp_path, current_system)
            
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error processing screenshot: {e}\n{traceback.format_exc()}")

    def get_current_star_system(self) -> str:
        """Reads the current system name from the Location projection."""
        try:
            if not self.plugin_helper:
                return "Unknown"
                
            location_projection = self.plugin_helper.get_projection(Location)
            if location_projection and hasattr(location_projection, "state"):
                return location_projection.state.get("StarSystem", "Unknown")
            return "Unknown"
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error getting current system: {e}")
            return "Unknown"

    def convert_screenshot(self, bmp_path: Path, current_system: str):
        """Converts the screenshot to PNG/JPG and emits conversion log."""
        try:
            if not self.plugin_helper:
                return

            if not bmp_path.exists():
                msg = f"Screenshot file not found: {bmp_path}"
                log("error", f"[ScreenshotConverter] {msg}")
                return

            target_format = (
                self.plugin_helper.get_plugin_setting("ScreenshotConverterPlugin", "settings", "target_format") or "png"
            ).lower()

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            system_name = bmp_path.stem.split("_")[-1] if "_" in bmp_path.stem else "System"
            safe_system_name = current_system.replace(" ", "_")
            new_name = f"{safe_system_name}_{system_name}-{timestamp}.{target_format}"
            new_path = bmp_path.parent / new_name

            with Image.open(bmp_path) as img:
                if target_format == "jpg":
                    img = img.convert("RGB")
                img.save(new_path, format=target_format.upper(), quality=90)

            bmp_path.unlink(missing_ok=True)
            log("info", f"[ScreenshotConverter] Converted {bmp_path.name} -> {new_path.name}")

        except Exception as e:
            msg = f"Screenshot conversion failed: {e}"
            log("error", f"[ScreenshotConverter] {msg}\n{traceback.format_exc()}")