# PresenterApp

A professional background presentation overlay app for Windows.

## Features

- Runs quietly in the Windows system tray / hidden icons area
- Pressing the window X hides the dashboard instead of closing the app
- Right-click the tray icon to:
  - Open PresenterApp
  - Enable / Disable the app
  - Clear / Reset overlays
  - Exit PresenterApp completely
- Dashboard-style control window
- Enable / Disable toggle
- Start minimized to tray option
- Custom presenter key option
- Pen pointer, highlight ring, Windows zoom lens, and spotlight modes

## Run

```bat
pip install -r requirements.txt
python main.py
```

## Build EXE

```bat
build_exe.bat
```

## Usage

- Double press the presenter key to cycle modes.
- Triple press the presenter key to clear all overlays.
- Press Esc to clear overlays.
- Press X on the window to keep PresenterApp running in hidden icons.
- To close completely, right-click the tray icon and choose **Exit PresenterApp completely**.


## Windows installer

1. Run `build_exe.bat` first. This creates `dist/PresenterApp.exe`.
2. Open `PresenterApp_Setup.iss` in Inno Setup.
3. Click **Compile**.
4. The installer will be created in `installer_output/`.

The app closes to the Windows hidden-icons tray when pressing X. To exit completely, right-click the tray icon and choose **Exit PresenterApp completely**.

## Fix in this version

- When PresenterApp is disabled, the presenter hotkey is completely unregistered.
- The letter `e` now returns to normal typing while the app is disabled.
- Re-enabling the app registers the hotkey again automatically.
