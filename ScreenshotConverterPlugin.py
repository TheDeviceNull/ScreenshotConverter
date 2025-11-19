# ScreenshotConverterPlugin.py
# Version 2.0.0 - Converts Elite Dangerous screenshots from BMP to PNG/JPG - New Covas:NEXT Plugin System
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
from lib.PluginHelper import PluginHelper, PluginEvent
from lib.PluginSettingDefinitions import (
    PluginSettings, SettingsGrid, ParagraphSetting, TextSetting, SelectSetting
)
from lib.Projections import Location


class ScreenshotConverterPlugin(PluginBase):
    """
    Plugin that converts Elite Dangerous BMP screenshots to PNG or JPG format.
    Automatically triggered when a Screenshot event is detected.
    """

    def __init__(self, plugin_manifest: PluginManifest):
        super().__init__(plugin_manifest)
        self.plugin_helper = None
        log("info", "[ScreenshotConverter] Plugin initialized")
        
        # Define plugin settings
        self.settings_config = PluginSettings(
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
                            content="Automatically converts Elite Dangerous BMP screenshots to PNG or JPG format."
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
                                {"key": "jpg", "label": "JPG", "value": "jpg"}
                            ]
                        )
                    ]
                )
            ]
        )
        
        # Default settings
        self.default_screenshot_path = r"%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous"
        self.default_target_format = "png"

    def on_plugin_helper_ready(self, helper: PluginHelper):
        """Called when the plugin helper is ready"""
        try:
            self.plugin_helper = helper
            
            # Register a side effect to handle Screenshot events
            helper.register_sideeffect(self.handle_event)
            
            # Register events for user notifications
            helper.register_event(
                "ScreenshotConverted",
                lambda event: True if event.plugin_event_name == "ScreenshotConverted" else False,
                lambda event: f"Screenshot converted to {event.content.get('format')}: {event.content.get('filename')}"
            )
            
            # Register a direct handler for Screenshot events as an alternative approach
            self.register_direct_handlers(helper)
            
            log("info", "[ScreenshotConverter] Plugin loaded and ready to convert screenshots")
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error in on_plugin_helper_ready: {e}")
            log("error", f"[ScreenshotConverter] Traceback: {traceback.format_exc()}")

    def register_direct_handlers(self, helper: PluginHelper):
        """Register direct handlers for events as an alternative approach"""
        try:
            # Alternative approach: register a projection directly
            class DirectScreenshotProjection:
                def __init__(self, plugin):
                    self.plugin = plugin
                
                def get_default_state(self):
                    return {"last": None}
                
                def process(self, event):
                    if hasattr(event, "content") and isinstance(event.content, dict):
                        if event.content.get("event") == "Screenshot":
                            self.plugin.convert_screenshot(event)
                    return []
                
                def get_event_types(self):
                    return ["Screenshot"]
            
            helper.register_projection(DirectScreenshotProjection(self))
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error registering direct handlers: {e}")

    def on_chat_start(self, helper: PluginHelper):
        """Called when chat starts"""
        if not self.plugin_helper:
            self.plugin_helper = helper
            helper.register_sideeffect(self.handle_event)

    def handle_event(self, event: Event, context: Dict[str, Any]):
        """Handle incoming events and check for Screenshot events"""
        try:           
            if not hasattr(event, "content"):
                return
                
            if not isinstance(event.content, dict):
                return
                
            event_type = event.content.get("event")
            log("debug", f"[ScreenshotConverter] Event type: {event_type}")
            
            if event_type != "Screenshot":
                return
                
            log("debug", f"[ScreenshotConverter] Screenshot event detected: {event.content}")
            
            # Process screenshot in a separate thread to avoid blocking
            thread = threading.Thread(
                target=self.convert_screenshot,
                args=(event,),
                daemon=True
            )
            log("info", "[ScreenshotConverter] Starting screenshot conversion thread")
            thread.start()
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error in handle_event: {e}")
            log("error", f"[ScreenshotConverter] Traceback: {traceback.format_exc()}")

    def get_setting(self, key, default_value):
        """Get a setting value from the plugin settings"""
        try:
            # Try to access settings from the plugin's settings attribute
            if hasattr(self, 'settings') and isinstance(self.settings, dict):
                # Check if the key exists in settings
                if key in self.settings:
                    return self.settings.get(key, default_value)
            
            # If we get here, return the default value
            return default_value
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error getting setting {key}: {e}")
            return default_value

    def convert_screenshot(self, event: Event):
        """Convert a screenshot from BMP to PNG/JPG"""
        try:          
            if not self.plugin_helper:
                log("error", "[ScreenshotConverter] Plugin helper not available")
                return
                
            # Get the filename from the event
            filename = event.content.get("Filename")           
            if not filename:
                log("error", "[ScreenshotConverter] Screenshot event missing Filename")
                return
                
            # Get settings using our custom method
            screenshot_path_setting = self.get_setting("screenshot_path", self.default_screenshot_path)
            target_format = self.get_setting("target_format", self.default_target_format)
            
            log("info", f"[ScreenshotConverter] Settings - Path: {screenshot_path_setting}, Format: {target_format}")
            
            # Expand environment variables in paths
            screenshot_dir = os.path.expandvars(screenshot_path_setting)
            
            # Handle different filename formats
            raw_filename = os.path.expandvars(filename)
            bmp_path = Path(raw_filename)
            
            # Handle relative paths in the event
            if "ED_Pictures" in raw_filename:
                relative_name = raw_filename.split("ED_Pictures")[-1].lstrip("\\/")
                bmp_path = Path(screenshot_dir) / relative_name
                
            bmp_path = bmp_path.expanduser().resolve()
            
           
            # Check if file exists
            if not bmp_path.exists():
                log("error", f"[ScreenshotConverter] Screenshot file not found: {bmp_path}")
                return
                
            # Get current star system for filename
            current_system = self.get_current_system()
            
            # Create new filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            system_name = current_system.replace(" ", "_")
            original_name = bmp_path.stem
            
            new_name = f"{system_name}_{original_name}_{timestamp}.{target_format}"
            new_path = bmp_path.parent / new_name
            
            
            # Convert the image
            with Image.open(bmp_path) as img:
                if target_format.lower() == "jpg":
                    img = img.convert("RGB")  # Remove alpha channel for JPG
                img.save(new_path, format=target_format.upper(), quality=95)
                
            # Delete original BMP file
            bmp_path.unlink(missing_ok=True)
            
            log("info", f"[ScreenshotConverter] Converted {bmp_path.name} to {new_path.name}")
            
            # Notify about successful conversion
            if self.plugin_helper:
                success_event = PluginEvent("ScreenshotConverted", {
                    "filename": str(new_path),
                    "original": str(bmp_path),
                    "system": current_system,
                    "format": target_format.upper()
                })
                self.plugin_helper.dispatch_event(success_event)
                
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error converting screenshot: {e}")
            log("error", f"[ScreenshotConverter] Traceback: {traceback.format_exc()}")
            
            # Notify about conversion error
            if self.plugin_helper:
                error_event = PluginEvent("ScreenshotError", {
                    "message": str(e),
                    "filename": str(bmp_path) if 'bmp_path' in locals() else "unknown"
                })
                self.plugin_helper.dispatch_event(error_event)

    def get_current_system(self) -> str:
        """Get the current star system name from Location projection"""
        try:
            if self.plugin_helper:
                # Get the Location projection from the event manager
                location_projection = self.plugin_helper._event_manager.get_projection(Location)
                if location_projection and "StarSystem" in location_projection.state:
                    return location_projection.state["StarSystem"]
            return "Unknown"
        except Exception as e:
            log("error", f"[ScreenshotConverter] Error getting current system: {e}")
            return "Unknown"