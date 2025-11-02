# ScreenshotConverterPlugin.py
# Version 1.0.1-hotfix - compatible manifest usage, safe event handling
# Author: The Device Null

from typing import Any
from datetime import datetime
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

# === Projection ===
class ScreenshotProjection(Projection[dict[str, Any]]):
    """Receives 'Screenshot' events from Elite Dangerous and forwards relevant ones."""

    def __init__(self, plugin_ref: "ScreenshotConverterPlugin"):
        # don't pass unexpected args to super; framework will handle Projection internals
        super().__init__()
        self.plugin_ref = plugin_ref

    def get_default_state(self) -> dict[str, Any]:
        return {"last": None}

    def process(self, event: Event) -> list[ProjectedEvent]:
        """
        Soft/robust filtering:
        - Only invoke handler when event.content is a dict and contains 'Filename'.
        - Ignore anything else silently to avoid startup spam and exceptions.
        """
        try:
            content = getattr(event, "content", None)
            if content and isinstance(content, dict) and "Filename" in content:
                # Safe: content is a dict and has Filename
                self.plugin_ref.handle_screenshot_event(event)
        except Exception as e:
            # log but never raise to keep Covas stable
            log("error", f"[ScreenshotConverter] Unexpected error in projection.process(): {e}")
        return []

    def get_event_types(self) -> list[str]:
        # Keep the projection registered; framework may match events by name.
        # Using the same "Screenshot" string used previously by the working plugin.
        return ["Screenshot"]


# === Main Plugin ===
class ScreenshotConverterPlugin(PluginBase):
    """Converts Elite Dangerous BMP screenshots to PNG/JPG when a Screenshot event occurs."""

    def __init__(self, plugin_manifest: PluginManifest):
        # plugin_manifest is provided by Covas; don't try to construct it here
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
        # Safely extract content and Filename
        content = getattr(event, "content", None)

        # If content is not a dict, ignore silently (prevents 'str'.get errors)
        if not isinstance(content, dict):
            return

        filename = content.get("Filename")
        if not filename:
            # silent ignore for events without Filename (avoids startup spam)
            return

        if not self.plugin_helper:
            log("error", "[ScreenshotConverter] PluginHelper not ready.")
            return

        # --- Get screenshot directory from settings ---
        screenshot_path_setting = self.plugin_helper.get_plugin_setting(
            "ScreenshotConverterPlugin", "settings", "screenshot_path"
        ) or r"%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"

        screenshot_dir = Path(os.path.expandvars(screenshot_path_setting))

        # Normalize filename removing ED_Pictures prefix if present
        filename = filename.replace("ED_Pictures\\", "").replace("ED_Pictures/", "")

        # Resolve full path: if path is absolute, use it; otherwise join with configured folder
        if filename.startswith("\\") or filename.startswith("/") or (len(filename) > 1 and filename[1] == ':'):
            bmp_path = Path(filename)
        else:
            bmp_path = screenshot_dir / filename

        bmp_path = bmp_path.expanduser().resolve()

        log("info", f"[ScreenshotConverter] Screenshot detected: {bmp_path}")

        # Launch conversion thread
        threading.Thread(target=self._convert_screenshot, args=(bmp_path,), daemon=True).start()

    # === Conversion ===
    def _convert_screenshot(self, bmp_path: Path):
        try:
            # Wait briefly up to ~0.5s for the game/FS to flush file (helps avoid transient not-found)
            for _ in range(5):
                if bmp_path.exists():
                    break
                threading.Event().wait(0.1)

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

            # Remove original BMP only if the output exists
            if new_path.exists():
                try:
                    bmp_path.unlink(missing_ok=True)
                except Exception as e:
                    log("warning", f"[ScreenshotConverter] Could not remove original BMP: {e}")

                log("info", f"[ScreenshotConverter] Converted {bmp_path.name} -> {new_path.name}")
            else:
                log("error", f"[ScreenshotConverter] Conversion completed but output missing: {new_path}")

        except Exception as e:
            log("error", f"[ScreenshotConverter] Conversion failed: {e}")
