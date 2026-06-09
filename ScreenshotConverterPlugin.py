# ScreenshotConverter.py
# Version 3.0.0
# Converts Elite Dangerous BMP screenshots to PNG or JPG.
# Filename format: <StarSystem>_<HiRes|Normal>_<YYYYMMDDHHmmSS>.<ext>
# Author: The Device Null

import os
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from PIL import Image

from lib.Event import Event
from lib.Logger import log
from lib.PluginBase import PluginBase, PluginManifest
from lib.PluginHelper import PluginHelper
from lib.PluginSettingDefinitions import (
    PluginSettings, SettingsGrid, ParagraphSetting, TextSetting, SelectSetting
)


class ScreenshotConverterPlugin(PluginBase):
    """
    Converts Elite Dangerous BMP screenshots to PNG or JPG.
    Triggered by the Screenshot journal event.
    System name is read from the Location projection state passed
    to the sideeffect callback — no private API access required.
    """

    # ------------------------------------------------------------------
    # Settings UI
    # ------------------------------------------------------------------
    settings_config = PluginSettings(
        key="ScreenshotConverterPlugin",
        label="Screenshot Converter",
        icon="image",
        grids=[
            SettingsGrid(
                key="info",
                label="Information",
                fields=[
                    ParagraphSetting(
                        key="desc",
                        label="Description",
                        type="paragraph",
                        readonly=True,
                        content=(
                            "Automatically converts Elite Dangerous BMP screenshots "
                            "to PNG or JPG. Filename: <System>_<Res>_<Timestamp>.<ext>"
                        )
                    )
                ]
            ),
            SettingsGrid(
                key="settings",
                label="Conversion Settings",
                fields=[
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
                            {"key": "jpg", "label": "JPG", "value": "jpg"},
                        ]
                    )
                ]
            )
        ]
    )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, plugin_manifest: PluginManifest):
        super().__init__(plugin_manifest)
        log("info", "[ScreenshotConverter] Plugin instantiated")

    def on_chat_start(self, helper: PluginHelper):
        """Register sideeffect. All setup that needs PluginHelper goes here."""
        helper.register_sideeffect(self._handle_event)
        log("info", "[ScreenshotConverter] Ready — watching for Screenshot events")

    def on_chat_stop(self, helper: PluginHelper):
        """Nothing to clean up."""
        pass

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_event(self, event: Event, projected_states: Dict[str, Any]):
        """
        Sideeffect callback. Receives every event and the full projection
        state dict. We filter for Screenshot events only.

        projected_states keys are projection class names (strings).
        The Location projection exposes its state under "Location".
        """
        try:
            if not hasattr(event, "content") or not isinstance(event.content, dict):
                return
            if event.content.get("event") != "Screenshot":
                return

            # LocationState is a dataclass with a direct .StarSystem attribute
            location = projected_states.get("Location")
            star_system = "Unknown"
            if location is not None:
                star_system = getattr(location, "StarSystem", None) or "Unknown"

            # Run conversion off the main thread
            thread = threading.Thread(
                target=self._convert,
                args=(event, star_system),
                daemon=True
            )
            thread.start()

        except Exception:
            log("error", f"[ScreenshotConverter] _handle_event error:\n{traceback.format_exc()}")

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _convert(self, event: Event, star_system: str):
        """Convert the BMP file and delete the original."""
        try:
            filename = event.content.get("Filename")
            if not filename:
                log("error", "[ScreenshotConverter] Screenshot event missing Filename field")
                return

            # Resolve settings (self.settings is populated by the framework)
            screenshot_path_setting = self.settings.get(
                "screenshot_path",
                r"%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"
            )
            target_format = self.settings.get("target_format", "png").lower()

            screenshot_dir = os.path.expandvars(screenshot_path_setting)
            raw_filename = os.path.expandvars(filename)
            bmp_path = Path(raw_filename)

            # Journal sometimes stores a path relative to ED_Pictures
            if "ED_Pictures" in raw_filename:
                relative_name = raw_filename.split("ED_Pictures")[-1].lstrip("\\/")
                bmp_path = Path(screenshot_dir) / relative_name

            bmp_path = bmp_path.expanduser().resolve()

            if not bmp_path.exists():
                log("error", f"[ScreenshotConverter] File not found: {bmp_path}")
                return

            # Build output filename: <System>_<Res>_<Timestamp>.<ext>
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            system_slug = star_system.replace(" ", "_")
            is_hires = "HighResScreenShot" in bmp_path.stem
            res_tag = "HiRes" if is_hires else "Normal"
            new_name = f"{system_slug}_{res_tag}_{timestamp}.{target_format}"
            new_path = bmp_path.parent / new_name

            # Convert
            with Image.open(bmp_path) as img:
                if target_format == "jpg":
                    img = img.convert("RGB")  # strip alpha for JPEG
                img.save(new_path, format=target_format.upper(), quality=95)

            # Delete original BMP
            bmp_path.unlink(missing_ok=True)

            log("info", f"[ScreenshotConverter] {bmp_path.name} → {new_name}")

        except Exception:
            log("error", f"[ScreenshotConverter] Conversion error:\n{traceback.format_exc()}")