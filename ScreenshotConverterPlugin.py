# ScreenshotConverterPlugin.py
# Version 1.0.5 - Added current star system name to filename
# Version 1.0.6 - Added error event for missing files
# Author: The Device Null

from typing import Any
from datetime import datetime
from pathlib import Path
from lib.PluginHelper import PluginHelper, PluginManifest
from lib.PluginBase import PluginBase
from lib.PluginSettingDefinitions import (
    PluginSettings, SettingsGrid, ParagraphSetting, TextSetting, SelectSetting
)
from lib.Event import Event, ProjectedEvent
from lib.EventManager import Projection
from lib.Logger import log
from lib.Projections import Location  # Import the Location projection
from PIL import Image
import os
import threading


# === Projection ===
class ScreenshotProjection(Projection[dict[str, Any]]):
    """Receives 'Screenshot' events from Elite Dangerous."""
    def __init__(self, plugin_ref: "ScreenshotConverterPlugin"):
        super().__init__()
        self.plugin_ref = plugin_ref

    def get_default_state(self) -> dict[str, Any]:
        return {"last": None}

    def process(self, event: Event) -> list[ProjectedEvent]:
        # Only act on real Screenshot events with structured content
        if not hasattr(event, "content") or not isinstance(event.content, dict):
            return []
        if event.content.get("event") != "Screenshot":
            return []
        try:
            return self.plugin_ref.handle_screenshot_event(event)
        except Exception as e:
            log("error", f"[ScreenshotConverter] Exception in process(): {e}")
        return []

    def get_event_types(self) -> list[str]:
        return ["Screenshot"]


# === Main Plugin ===
class ScreenshotConverterPlugin(PluginBase):
    """Converts Elite Dangerous BMP screenshots to PNG/JPG when a Screenshot event occurs."""

    def __init__(self, plugin_manifest: PluginManifest):
        super().__init__(plugin_manifest)
        self.plugin_helper: PluginHelper | None = None

        # --- Settings ---
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
                            content="Set the directory where Elite Dangerous saves screenshots. The plugin will use this path to locate BMP files."
                        ),
                        TextSetting(
                            key="screenshot_path",
                            label="Screenshot folder",
                            type="text",
                            default_value=r"%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"
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

    # === Lifecycle ===
    def on_plugin_helper_ready(self, helper: PluginHelper):
        self.plugin_helper = helper
        log("info", "[ScreenshotConverter] Plugin loaded and waiting for Screenshot events.")

    def register_projections(self, helper: PluginHelper):
        helper.register_projection(ScreenshotProjection(self))

    # === Event Handling ===
    def handle_screenshot_event(self, event: Event) -> list[ProjectedEvent]:
        projected_events: list[ProjectedEvent] = []
        filename = event.content.get("Filename") if hasattr(event, "content") else None
        
        if not filename:
            log("warn", "[ScreenshotConverter] Screenshot event missing Filename.")
            projected_events.append(ProjectedEvent({
                "event": "ScreenshotError", 
                "message": "Screenshot event missing Filename"
            }))
            return projected_events

        if not self.plugin_helper:
            log("error", "[ScreenshotConverter] PluginHelper not ready.")
            projected_events.append(ProjectedEvent({
                "event": "ScreenshotError", 
                "message": "Plugin helper not ready"
            }))
            return projected_events

        # --- Get screenshot directory from settings ---
        screenshot_path_setting = self.plugin_helper.get_plugin_setting(
            "ScreenshotConverterPlugin", "settings", "screenshot_path"
        ) or r"%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"

        screenshot_dir = Path(os.path.expandvars(screenshot_path_setting))

        # --- Resolve correct screenshot path ---
        raw_filename = os.path.expandvars(filename)
        bmp_path = Path(raw_filename)

        # Replace "ED_Pictures" alias with the configured screenshot directory
        if "ED_Pictures" in raw_filename:
            relative_name = raw_filename.split("ED_Pictures")[-1].lstrip("\\/")
            bmp_path = Path(screenshot_dir) / relative_name

        # Normalize the path
        bmp_path = bmp_path.expanduser().resolve()

        log("info", f"[ScreenshotConverter] Screenshot detected: {bmp_path}")

        # Check if file exists before starting conversion
        if not bmp_path.exists():
            error_message = f"Screenshot file not found: {bmp_path}"
            log("error", f"[ScreenshotConverter] {error_message}")
            projected_events.append(ProjectedEvent({
                "event": "ScreenshotError", 
                "message": error_message
            }))
            return projected_events

        # Get current star system from Location projection
        current_system = self._get_current_star_system()

        # Launch conversion thread
        threading.Thread(target=self._convert_screenshot, 
                         args=(bmp_path, current_system, event), 
                         daemon=True).start()
        
        return projected_events

    # === Get Current Star System ===
    def _get_current_star_system(self) -> str:
        """Get the current star system name from the Location projection."""
        try:
            if self.plugin_helper:
                event_manager = self.plugin_helper.get_event_manager()
                location_projection = event_manager.get_projection(Location)
                if location_projection:
                    return location_projection.state.get("StarSystem", "Unknown")
            return "Unknown"
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error getting current system: {e}")
            return "Unknown"

    # === Conversion ===
    def _convert_screenshot(self, bmp_path: Path, current_system: str, original_event: Event):
        try:
            if not bmp_path.exists():
                error_message = f"Screenshot file not found: {bmp_path}"
                log("error", f"[ScreenshotConverter] {error_message}")
                
                # Create error event
                if self.plugin_helper:
                    error_event = ProjectedEvent({
                        "event": "ScreenshotError", 
                        "message": error_message
                    })
                    self.plugin_helper.get_event_manager().add_projected_event(error_event, original_event)
                return

            helper = self.plugin_helper
            target_format = (
                helper.get_plugin_setting("ScreenshotConverterPlugin", "settings", "target_format")
                or "png"
            ).lower()

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            system_name = bmp_path.stem.split("_")[-1] if "_" in bmp_path.stem else "System"
            
            # Create new filename with current system at the beginning
            safe_system_name = current_system.replace(" ", "_")
            new_name = f"{safe_system_name}_{system_name}-{timestamp}.{target_format}"
            new_path = bmp_path.parent / new_name

            # Open and save image
            from PIL import Image
            with Image.open(bmp_path) as img:
                if target_format == "jpg":
                    img = img.convert("RGB")
                img.save(new_path, format=target_format.upper(), quality=90)

            # Remove original BMP
            bmp_path.unlink(missing_ok=True)

            log("info", f"[ScreenshotConverter] Converted {bmp_path.name} -> {new_path.name}")
            
            # Create success event
            if self.plugin_helper:
                success_event = ProjectedEvent({
                    "event": "ScreenshotConverted", 
                    "originalPath": str(bmp_path),
                    "newPath": str(new_path),
                    "system": current_system
                })
                self.plugin_helper.get_event_manager().add_projected_event(success_event, original_event)

        except Exception as e:
            error_message = f"Screenshot conversion failed: {e}"
            log("error", f"[ScreenshotConverter] {error_message}")
            
            # Create error event
            if self.plugin_helper:
                error_event = ProjectedEvent({
                    "event": "ScreenshotError", 
                    "message": error_message,
                    "path": str(bmp_path)
                })
                self.plugin_helper.get_event_manager().add_projected_event(error_event, original_event)
# --- END OF FILE ---