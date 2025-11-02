# ScreenshotConverter

**Version 1.0.0 "SnapDragon"**

ScreenshotConverter is a plugin for Covas:NEXT that automatically converts Elite Dangerous BMP screenshots into PNG or JPG format. Designed to run in the background, it seamlessly handles screenshot events without interfering with gameplay.

## Features

- Automatic conversion of BMP screenshots to PNG or JPG.
- Threaded processing to keep conversions fast and non-blocking.
- Customizable screenshot folder path.
- Timestamped filenames preserving system names.
- Compatible with Covas:NEXT event system.
- Robust logging for successful conversions and error detection.

## Installation

1. Place the `ScreenshotConverter` plugin folder in your Covas:NEXT plugins directory.
2. Start Covas:NEXT.
3. Go to the plugin settings and configure the screenshot folder and output format.

## Usage

- Take a screenshot in Elite Dangerous.
- The plugin automatically detects the screenshot event.
- The BMP file is converted to the chosen format (PNG or JPG) and saved in the same folder.
- Original BMP files are deleted after conversion to save space.
- Logs are available in Covas:NEXT for monitoring conversion status.

## Configuration

| Setting | Description |
|---------|-------------|
| Screenshot folder | Directory where Elite Dangerous saves screenshots. |
| Output format | Choose between PNG and JPG. |


## ⚠️ Important

Make sure that Covas:NEXT has read and write access to your Elite Dangerous screenshot folder.

On Windows, Windows Defender or other security features may block access and show a popup.

Granting permissions is necessary for the plugin to convert screenshots properly

## Changelog

**1.0.0 "SnapDragon"**
- Stable major release.
- Fixed event handling and startup logging issues.
- Improved filename and path handling.
- Optimized conversion threads.

**Pre-release 0.1.11**
- Initial automatic BMP to PNG/JPG conversion.
- Basic settings interface.
- Pre-release testing version.

## License

MIT License. See `LICENSE` file for details.
