# Screenshot Converter Plugin for COVAS:NEXT

**Version:** 0.1.11  
**Author:** [The Device Null](https://github.com/TheDeviceNull)

---

## 📖 Overview

**Screenshot Converter** is a plugin for **COVAS:NEXT** that automatically converts the raw **BMP** screenshots created by *Elite Dangerous* into more convenient **PNG** or **JPG** files.

When the game triggers a **Screenshot** event, the plugin automatically:
1. Detects the BMP file saved by the game.
2. Converts it to the selected image format (PNG or JPG).
3. Renames it according to the pattern: `<systemName><yyyyMMddHHmmss>.<ext>` (system name extraction may be improved in future versions).
4. Deletes the original BMP file (to save disk space).
5. Logs the conversion result in Covas:NEXT (visible in the plugin panel).

> **Note:** The plugin no longer emits a custom event after conversion.

---

## ⚙️ Installation

1. Download the latest `.zip` release from the [Releases page](https://github.com/TheDeviceNull/ScreenshotConverterPlugin/releases).
2. Extract the contents of the `.zip` into your **Covas:NEXT plugins folder** (usually located at `C:\Users\<YourUser>\AppData\Roaming\com.covas-next.ui\plugins`).
3. Launch or restart **Covas:NEXT**.
4. Open the **Screenshot Converter** plugin settings:
   - Set the **screenshot folder** to the directory where Elite Dangerous saves screenshots.
     - Default: `%USERPROFILE%\Pictures\Frontier Developments\Elite Dangerous`
   - Select the desired **output format**: PNG or JPG.
5. Make sure **Covas:NEXT** has read and write access to the screenshot folder. On Windows, this may require confirming a Windows Defender or security popup.

---

## ⚠️ Important

- Granting read/write permissions is necessary for the plugin to convert screenshots properly.
- The plugin currently does **not announce conversions via events**; all messages are visible in the plugin panel log.
- The filename pattern may not always include the system name; this will be improved in a future version.


