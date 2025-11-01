# ScreenshotConverterPlugin.py
# Version 0.1.12 - Projection-based rewrite
# Author: The Device Null

from typing import Any, Literal
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from lib.PluginHelper import PluginHelper, PluginManifest
from lib.PluginBase import PluginBase
from lib.PluginSettingDefinitions import PluginSettings, SettingsGrid, ParagraphSetting, TextSetting, SelectSetting
from lib.Event import Event, ProjectedEvent
from lib.EventManager import Projection
from lib.Logger import log
from PIL import Image
import os
import threading
import time

# === Projection ===
class ScreenshotProjection(Projection[dict[str, Any]]):
    """Listens specifically for 'Screenshot' events from Elite Dangerous."""

    def __init__(self, plugin_ref: "ScreenshotConverterPlugin"):
        super().__init__()
        self.plugin_ref = plugin_ref

    def get_default_state(self) -> dict[str, Any]:
        return {"last": None}

    def process(self, event: Event) -> list[ProjectedEvent]:
        """
        Only handle Screenshot events. All others are ignored safely.
        """
        # Some events in Covas:NEXT don't have an 'event' attribute, or it's not a string.
        if not hasattr(event, "event"):
            return []

        # Make sure it's the right event type
        if str(event.event).lower() != "screenshot":
            return []

        # Double-check expected fields exist (Filename, etc.)
        content = getattr(event, "content", None)
        if not content or not isinstance(content, dict) or "Filename" not in content:
            # Optional: log diagnostic but don’t break Covas:NEXT
            log("debug", "[ScreenshotConverter] Ignored event: missing Filename or invalid structure")
            return []

        # Now safe to handle
        try:
            self.plugin_ref.handle_screenshot_event(event)
        except Exception as e:
            log("error", f"[ScreenshotConverter] Exception in process(): {e}")

        return []

    def get_event_types(self) -> list[str]:
        # Still register only for Screenshot events
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
    def handle_screenshot_event(self, event: Event):
        filename = event.content.get("Filename")
        if not filename:
        #    log("warn", "[ScreenshotConverter] Screenshot event missing Filename.")
            return

        if not self.plugin_helper:
            log("error", "[ScreenshotConverter] PluginHelper not ready.")
            return

        # --- Get screenshot directory from settings ---
        screenshot_path_setting = self.plugin_helper.get_plugin_setting(
            "ScreenshotConverterPlugin", "settings", "screenshot_path"
        ) or r"%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"

        screenshot_dir = Path(os.path.expandvars(screenshot_path_setting))

        # Remove ED_Pictures from filename if present
        filename = filename.replace("ED_Pictures\\", "").replace("ED_Pictures/", "")

        # Resolve full path
        if filename.startswith("\\"):
            bmp_path = screenshot_dir / filename.strip("\\")
        else:
            bmp_path = Path(filename)

        bmp_path = bmp_path.expanduser()

        log("info", f"[ScreenshotConverter] Screenshot detected: {bmp_path}")

        # Launch conversion thread
        threading.Thread(target=self._convert_screenshot, args=(bmp_path,), daemon=True).start()

    # === Conversion ===
    def _convert_screenshot(self, bmp_path: Path):
        try:
            if not bmp_path.exists():
                log("error", f"[ScreenshotConverter] File not found: {bmp_path}")
                return

            helper = self.plugin_helper
            target_format = (helper.get_plugin_setting("ScreenshotConverterPlugin", "settings", "target_format") or "png").lower()

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            system_name = bmp_path.stem.split("_")[-1] if "_" in bmp_path.stem else "System"
            new_name = f"{system_name}{timestamp}.{target_format}"
            new_path = bmp_path.parent / new_name

            # Open and save image
            with Image.open(bmp_path) as img:
                if target_format == "jpg":
                    img = img.convert("RGB")
                img.save(new_path, format=target_format.upper(), quality=90)

            # Remove original BMP
            bmp_path.unlink(missing_ok=True)

            # Log info (visible in GUI)
            log("info", f"[ScreenshotConverter] Converted {bmp_path.name} -> {new_path.name}")

        except Exception as e:
            log("error", f"[ScreenshotConverter] Conversion failed: {e}")
# End of ScreenshotConverterPlugin.py