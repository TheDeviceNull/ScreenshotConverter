# ScreenshotConverter

**Version 1.0.7 "Mostly Harmless, Definitely Working"**

ScreenshotConverter is a plugin for **Covas:NEXT** that automatically converts **Elite Dangerous** BMP screenshots into PNG or JPG format.  
It runs quietly in the background, listening for screenshot events, and performs conversions instantly without interrupting your gameplay.

---

## ✨ Features

- Automatic conversion of BMP screenshots to **PNG** or **JPG**.  
- Runs in **background threads** — no blocking or stuttering in Covas:NEXT or the game.  
- **Configurable screenshot path** (supports custom or default Elite Dangerous folder).  
- **Smart filenames** including timestamp and current star system.  
- Fully **compatible with Covas:NEXT event system**.  
- **Robust logging** for conversion success, errors, and diagnostics.  

---

## ⚙️ Installation (Windows)

1. Download the latest release ZIP from the [Releases page](https://github.com/TheDeviceNull/ScreenshotConverter/releases).  
2. **Unzip** the folder `ScreenshotConverter` directly into:  

`%APPDATA%\com.covas-next.ui\plugins`

(You can paste this path into File Explorer’s address bar to open it quickly.)
3. After extraction, you should have:

`%APPDATA%\com.covas-next.ui\plugins\ScreenshotConverter\`

4. Launch **Covas:NEXT**.  
5. Open the **Plugin Settings** panel → locate **Screenshot Converter** → verify or configure:  
- *Screenshot folder* (usually `Pictures\Frontier Developments\Elite Dangerous`)  
- *Output format* (PNG or JPG)

✅ That’s it — the plugin will automatically start converting screenshots as soon as Covas:NEXT receives a `Screenshot` event.

---

## 🕹️ Usage

- Take a screenshot in **Elite Dangerous** (default key: `F10` for BMP, `Alt+F10` for high-res).  
- The plugin automatically detects the event via Covas:NEXT.  
- The BMP file is converted to the selected format (PNG/JPG) and saved in the same folder.  
- The original BMP is safely deleted after successful conversion.  
- Conversion logs appear in the Covas:NEXT console and log files.  

---

## ⚙️ Configuration

| Setting | Description |
|----------|-------------|
| **Screenshot folder** | Path where Elite Dangerous stores screenshots. |
| **Output format** | Choose between PNG and JPG output. |

---

## ⚠️ Important Notes

- Ensure that **Covas:NEXT** has **read/write access** to the Elite Dangerous screenshot folder.  
- Windows Defender or similar security tools may prompt for permission — allow it so conversions can complete.  
- High-resolution screenshots may take a few seconds to convert depending on your system speed.  

---

## 🧩 Changelog

### **1.0.7 “Mostly Harmless, Definitely Working” (2025-11-08)**
- Fixed: replaced invalid `get_event_manager()` calls with `_event_manager`.  
- Fixed: conversion event propagation now works correctly.  
- Improved: better error handling and cleaner logging.  
- Verified: full compatibility with Covas:NEXT November 2025 builds.  

### **1.0.0 “SnapDragon” (2025-11-01)**
- First stable major release.  
- Added threaded background conversion.  
- Implemented configurable format and directory settings.  
- Improved logging and filename structure.  

### **Pre-release 0.1.11**
- Initial automatic BMP → PNG/JPG conversion prototype.  
- Basic settings UI.  
- Early testing version.  

---

## 📜 License

MIT License — see [`LICENSE`](LICENSE) for details.
