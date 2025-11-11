# ScreenshotConverterPlugin.py
# Version 1.0.11 - Full Covas:NEXT compliance and stable Event handling - <3 Rude <3
# Author: The Device Null (revised by GPT-5)

from typing import Any
from datetime import datetime
from pathlib import Path
from lib.PluginHelper import PluginHelper, PluginManifest
from lib.PluginBase import PluginBase
from lib.PluginSettingDefinitions import (
    PluginSettings, SettingsGrid, ParagraphSetting, TextSetting, SelectSetting
)
from lib.Event import Event
from lib.EventManager import Projection
from lib.Projections import Location
from lib.Logger import log
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

    def process(self, event: Event) -> list[Any]:
        """Intercepts Screenshot events and passes them to the plugin."""
        if not hasattr(event, "content") or not isinstance(event.content, dict):
            return []
        if event.content.get("event") != "Screenshot":
            return []
        try:
            self.plugin_ref.handle_screenshot_event(event)
        except Exception as e:
            log("error", f"[ScreenshotConverter] Exception in process(): {e}")
        return []

    def get_event_types(self) -> list[str]:
        return ["Screenshot"]


# === Plugin ===
class ScreenshotConverterPlugin(PluginBase):
    """Converts Elite Dangerous BMP screenshots to PNG/JPG when a Screenshot event occurs."""

    def __init__(self, plugin_manifest: PluginManifest):
        super().__init__(plugin_manifest)
        self.plugin_helper: PluginHelper | None = None

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

    def on_plugin_helper_ready(self, helper: PluginHelper):
        """Called when the plugin helper is ready."""
        self.plugin_helper = helper
        log("info", "[ScreenshotConverter] Plugin loaded and waiting for Screenshot events.")

    def register_projections(self, helper: PluginHelper):
        """Registers the Screenshot projection."""
        helper.register_projection(ScreenshotProjection(self))

    # === Main handler ===
    def handle_screenshot_event(self, event: Event):
        """Triggered by ScreenshotProjection when a Screenshot event occurs."""
        filename = event.content.get("Filename") if hasattr(event, "content") else None
        if not filename:
            log("warn", "[ScreenshotConverter] Screenshot event missing Filename.")
            return

        if not self.plugin_helper:
            log("error", "[ScreenshotConverter] PluginHelper not ready.")
            return

        screenshot_path_setting = (
            self.plugin_helper.get_plugin_setting("ScreenshotConverterPlugin", "settings", "screenshot_path")
            or r"%USERPROFILE%\\Pictures\\Frontier Developments\\Elite Dangerous"
        )
        screenshot_dir = Path(os.path.expandvars(screenshot_path_setting))
        bmp_path = Path(os.path.expandvars(filename)).expanduser().resolve()

        if "ED_Pictures" in str(bmp_path):
            relative_name = str(bmp_path).split("ED_Pictures")[-1].lstrip("\\/")
            bmp_path = Path(screenshot_dir) / relative_name

        bmp_path = bmp_path.expanduser().resolve()

        # Ignore stale or already-removed screenshots
        if not bmp_path.exists():
            log("debug", f"[ScreenshotConverter] Ignored missing file (likely old): {bmp_path}")
            return
        # Ignore if older than 5 minutes
        if bmp_path.stat().st_mtime < (datetime.now().timestamp() - 300):
            log("debug", f"[ScreenshotConverter] Ignored stale screenshot: {bmp_path}")
            return

        log("info", f"[ScreenshotConverter] Screenshot detected: {bmp_path}")

        current_system = self._get_current_star_system()
        threading.Thread(
            target=self._convert_screenshot,
            args=(bmp_path, current_system),
            daemon=True
        ).start()

    def _get_current_star_system(self) -> str:
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

    def _convert_screenshot(self, bmp_path: Path, current_system: str):
        """Converts the screenshot to PNG/JPG and emits conversion log."""
        try:
            helper = self.plugin_helper
            if not helper:
                return

            if not bmp_path.exists():
                msg = f"Screenshot file not found: {bmp_path}"
                log("error", f"[ScreenshotConverter] {msg}")
                return

            target_format = (
                helper.get_plugin_setting("ScreenshotConverterPlugin", "settings", "target_format") or "png"
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
            log("error", f"[ScreenshotConverter] {msg}")

