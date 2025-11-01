# Screenshot Converter Plugin for COVAS:NEXT

**Version:** 0.1.9  
**Author:** [The Device Null](https://github.com/TheDeviceNull)

---

## 📖 Overview

**Screenshot Converter** is a plugin for **COVAS:NEXT** that automatically converts the raw **BMP** screenshots created by *Elite Dangerous* into more convenient **PNG** or **JPG** files.

When the game triggers a **Screenshot** event, the plugin automatically:
1. Detects the latest BMP file saved by the game.
2. Converts it to the selected image format (PNG or JPG).
3. Renames it according to the pattern: <systemName><yyyyMMddHHmmss>.<ext> <-- TODO
4. Deletes the original BMP file (to save disk space).
5. Emits a `ScreenshotConvertedEvent` to notify the system and other plugins.

## ⚠️ Important

Make sure that Covas:NEXT has read and write access to your Elite Dangerous screenshot folder.
On Windows, Windows Defender or other security features may block access and show a popup.
Granting permissions is necessary for the plugin to convert screenshots properly.

