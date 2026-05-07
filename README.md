# PresenterApp

<p align="center">
  <img src="assets/icon.png" width="140" alt="PresenterApp Logo">
</p>

<p align="center">
  <b>Professional Presentation Overlay Software for Windows</b>
</p>

<p align="center">
  Lightweight • Open-Source • Presenter Friendly
</p>

---

# Overview

PresenterApp is a professional background presentation enhancement application designed for Windows users who need lightweight and efficient on-screen presentation tools.

The application provides spotlighting, highlighting, zoom integration, and presenter overlays while running silently in the background through the Windows system tray.

PresenterApp is designed for:
- Educators
- Researchers
- Lecturers
- Students
- Technical presenters
- Content creators

---

# For Users

## Download

The latest stable version can be found in the repository **Releases** section.

### Included Downloads

#### Windows Installer (Recommended)
- `PresenterApp_Setup_v1.0.0.exe`

#### Portable Version (No Installation Required)
- `PresenterApp_Portable_v1.0.0.exe`

---

# Main Features

## 🎛️ Background Tray Application
PresenterApp runs quietly in the Windows system tray / hidden icons area without interrupting your workflow.

## 🪟 Smart Close Behavior
Pressing the window **X** button hides the dashboard instead of terminating the application.

## 🖱️ Tray Menu Controls
Right-click the tray icon to:
- Open PresenterApp
- Enable / Disable the application
- Clear / Reset overlays
- Exit PresenterApp completely

## 🖥️ Professional Dashboard Interface
Modern dashboard-style control panel with clean presentation-focused controls.

## ⚡ Enable / Disable System
Quickly enable or disable presenter features whenever needed.

## 🚀 Start Minimized to Tray
Optional startup mode that launches PresenterApp directly into the system tray.

## 🎮 Custom Presenter Key Support
Configure custom hotkeys for presenter devices and keyboards.

## 🖊️ Presentation Tools
Includes:
- Pen pointer mode
- Highlight ring mode
- Windows zoom lens integration
- Spotlight presentation mode

---

# Usage

| Action | Result |
|---|---|
| Double press presenter key | Cycle presentation modes |
| Triple press presenter key | Clear active overlays |
| `Esc` | Clear overlays |
| Press `X` on window | Hide PresenterApp to system tray |
| Tray → Exit PresenterApp completely | Fully close the application |

---

# Important Note

PresenterApp operates by temporarily intercepting selected keyboard shortcuts while presentation tools are enabled.

When the application is disabled:
- All presenter hotkeys are automatically unregistered
- Keyboard typing returns to normal behavior

This prevents conflicts during normal typing and desktop usage.

---

# Recent Improvements

## Fixes Included in This Version

- Presenter hotkeys are now fully unregistered when the application is disabled
- The letter `e` correctly returns to standard keyboard typing while PresenterApp is disabled
- Re-enabling the application automatically restores presenter controls
- Improved tray behavior and application stability
- Improved overlay clearing behavior
- Improved background-mode handling

---

# Run from Source

```bat
pip install -r requirements.txt
python main.py
