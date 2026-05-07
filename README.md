# PresenterApp

<p align="center">
  <img width="500" height="500" alt="icon" src="https://github.com/user-attachments/assets/db309f9c-5a06-46c2-a90a-b9e3b40527dd" />
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

The latest stable version can be found in the repository **[Releases](https://github.com/radymahmoud1/Presenter-App/releases/tag/V1.0.0_Initial_Release)** section.

### Included Downloads

#### Windows Installer (Recommended)
- `PresenterApp_Setup_v1.0.0.exe`

#### Portable Version (No Installation Required)
- `Portable_PresenterApp_v1.0.0.exe`

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

## Run from Source (For Developers)

```bat
pip install -r requirements.txt
python main.py
```

## Build EXE

```bat
build_exe.bat
```

## Open Source Windows Installer

1. Run `build_exe.bat` first. This creates `dist/PresenterApp.exe`.
2. Open `PresenterApp_Setup.iss` in Inno Setup.
3. Click **Compile**.
4. The installer will be created in `installer_output/`.

## Python Version

PresenterApp is recommended to run with:

```text
Python 3.10+
```

Tested environment:
- Python 3.10.20
- Windows 10 / Windows 11

## Requirements for Building the Installer (in detail)

To build the Windows installer for PresenterApp, the following tools are required:

### 1. Python

Recommended version:

```text
Python 3.10+
```

Tested environment:
- Python 3.10.20
- Windows 10 / Windows 11

---

### 2. Required Python Packages

Install dependencies using:

```bat
pip install -r requirements.txt
```

---

### 3. PyInstaller

Used to generate the executable file.

Install using:

```bat
pip install pyinstaller
```

---

### 4. Inno Setup

Used to build the Windows installer.

Download:
- https://jrsoftware.org/isinfo.php

---

## Build Process

### Step 1 — Build EXE

```bat
build_exe.bat
```

This creates:

```text
dist/PresenterApp.exe
```

---

### Step 2 — Build Installer

1. Open:
   ```text
   PresenterApp_Setup.iss
   ```

2. Using:
   - Inno Setup

3. Click:
   - **Compile**

4. The installer will be generated inside:

```text
installer_output/
```
