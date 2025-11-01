# Screenshot Converter Plugin for COVAS:NEXT

**Version:** 0.1.0  
**Author:** [The Device Null](https://github.com/TheDeviceNull)

---

## 📖 Overview

**Screenshot Converter** is a plugin for **COVAS:NEXT** that automatically converts the raw **BMP** screenshots created by *Elite Dangerous* into more convenient **PNG** or **JPG** files.

When the game triggers a **Screenshot** event, the plugin automatically:
1. Detects the latest BMP file saved by the game.
2. Converts it to the selected image format (PNG or JPG).
3. Renames it according to the pattern: <systemName><yyyyMMddHHmmss>.<ext>
4. Deletes the original BMP file (to save disk space).
5. Emits a `ScreenshotConvertedEvent` to notify the system and other plugins.

