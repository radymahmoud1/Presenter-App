import sys
import time
import ctypes
import threading
import json
import os
from pathlib import Path

import keyboard as kb
from PySide6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QMainWindow,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QComboBox,
    QCheckBox, QMessageBox
)
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QPainterPath, QAction, QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer, QSize, QObject, Signal

VK_LWIN = 0x5B
VK_ADD = 0x6B
VK_ESCAPE = 0x1B
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_L = 0x4C

APP_NAME = "PresenterApp"
CONFIG_FILE = Path.home() / "PresenterApp_settings.json"


def resource_path(relative_path):
    """Return correct path for development and PyInstaller EXE mode."""
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path


ICON_FILE = resource_path("assets/icon.ico")

DEFAULT_SETTINGS = {
    "enabled": True,
    "presenter_key": "e",
    "multi_press_window": 0.4,
    "start_minimized": False,
    "show_notifications": True,
    "minimize_to_tray_on_close": True,
    "close_to_tray_tip_shown": False,
}


def load_settings():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    CONFIG_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def key_down(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)


def key_up(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)


def press_win_plus():
    key_down(VK_LWIN)
    key_down(VK_ADD)
    key_up(VK_ADD)
    key_up(VK_LWIN)


def press_win_esc():
    key_down(VK_LWIN)
    key_down(VK_ESCAPE)
    key_up(VK_ESCAPE)
    key_up(VK_LWIN)


def press_ctrl_alt_l():
    key_down(VK_CONTROL)
    key_down(VK_MENU)
    key_down(VK_L)
    key_up(VK_L)
    key_up(VK_MENU)
    key_up(VK_CONTROL)


class SharedState:
    def __init__(self):
        self.enabled = True
        self.mode = "none"  # none, pen, highlight, zoom, spotlight
        self.overlays = []
        self.cursor_hidden = False
        self.windows_zoom_active = False

    def hide_cursor(self):
        if not self.cursor_hidden:
            while ctypes.windll.user32.ShowCursor(False) >= 0:
                pass
            self.cursor_hidden = True

    def show_cursor(self):
        if self.cursor_hidden:
            while ctypes.windll.user32.ShowCursor(True) < 0:
                pass
            self.cursor_hidden = False


class PresenterOverlay(QWidget):
    def __init__(self, screen, state):
        super().__init__()
        self.state = state
        self.highlight_radius = 75
        self.spotlight_radius = 150
        self.setGeometry(screen.geometry())
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_overlay)
        self.timer.start(16)

    def update_overlay(self):
        if self.state.enabled and self.state.mode in ["pen", "highlight", "spotlight"]:
            self.state.hide_cursor()
        else:
            self.state.show_cursor()
        self.update()

    def paintEvent(self, event):
        if not self.state.enabled:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        if not self.geometry().contains(global_pos):
            return

        center = local_pos

        if self.state.mode == "pen":
            painter.setPen(QPen(QColor(255, 0, 0, 230), 2))
            painter.setBrush(QColor(255, 0, 0, 230))
            painter.drawEllipse(center, 7, 7)
            painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, 12, 12)

        elif self.state.mode == "highlight":
            painter.setPen(QPen(QColor(255, 220, 0, 240), 5))
            painter.setBrush(QColor(255, 220, 0, 45))
            painter.drawEllipse(center, self.highlight_radius, self.highlight_radius)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, self.highlight_radius + 7, self.highlight_radius + 7)

        elif self.state.mode == "spotlight":
            outer_path = QPainterPath()
            outer_path.addRect(self.rect())
            clear_path = QPainterPath()
            clear_path.addEllipse(center, self.spotlight_radius, self.spotlight_radius)
            dim_path = outer_path.subtracted(clear_path)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 190))
            painter.drawPath(dim_path)


class KeyListener(QObject):
    """Handles presenter hotkeys safely.

    The keyboard package calls callbacks from a non-Qt background thread.
    Updating Qt widgets or changing overlays directly from that thread can
    crash the application. Therefore hotkey callbacks only emit a Qt signal,
    and the real action runs on the main Qt thread.
    """

    action_requested = Signal(str)

    def __init__(self, state, settings, on_status_changed=None):
        super().__init__()
        self.state = state
        self.settings = settings
        self.on_status_changed = on_status_changed
        self.e_press_count = 0
        self.last_press_time = 0
        self.timer = None
        self.registered = False
        self.action_requested.connect(self._process_action)

    @property
    def presenter_key(self):
        return self.settings.get("presenter_key", "e")

    @property
    def multi_press_window(self):
        return float(self.settings.get("multi_press_window", 0.4))

    def notify(self):
        if self.on_status_changed:
            self.on_status_changed()

    def close_windows_zoom(self):
        if self.state.windows_zoom_active:
            press_win_esc()
            self.state.windows_zoom_active = False

    def open_windows_zoom_lens(self):
        self.state.show_cursor()
        press_win_plus()
        time.sleep(0.2)
        press_ctrl_alt_l()
        self.state.windows_zoom_active = True

    def _process_action(self, action):
        """Runs on the Qt main thread."""
        if action == "cycle":
            self.cycle_mode()
        elif action == "clear":
            self.clear_all()

    def cycle_mode(self):
        if not self.state.enabled:
            return

        if self.state.mode == "none":
            self.close_windows_zoom()
            self.state.mode = "pen"
        elif self.state.mode == "pen":
            self.close_windows_zoom()
            self.state.mode = "highlight"
        elif self.state.mode == "highlight":
            self.state.mode = "zoom"
            self.open_windows_zoom_lens()
        elif self.state.mode == "zoom":
            self.close_windows_zoom()
            self.state.mode = "spotlight"
        elif self.state.mode == "spotlight":
            self.close_windows_zoom()
            self.state.mode = "pen"
        self.notify()

    def clear_all(self):
        """Disable only the active visual tool/effect; keep PresenterApp running."""
        self.close_windows_zoom()
        self.state.mode = "none"
        self.state.show_cursor()
        self.e_press_count = 0
        self.notify()

    def set_enabled(self, enabled):
        """Enable or disable PresenterApp hotkeys.

        Important behavior:
        - Enabled: the presenter key is captured/suppressed so double/triple clicks
          control the presenter tools.
        - Disabled: all keyboard hooks are removed, so the presenter key, especially
          the letter E, returns to normal typing in Windows and other apps.
        """
        enabled = bool(enabled)

        if enabled:
            self.state.enabled = True
            self.settings["enabled"] = True
            save_settings(self.settings)
            self.register_hotkeys()
        else:
            self.clear_all()
            self.state.enabled = False
            self.settings["enabled"] = False
            save_settings(self.settings)
            self.unregister_hotkeys()

        self.notify()

    def process_clicks(self):
        count = self.e_press_count
        self.e_press_count = 0

        # Triple click must only clear/close the current feature tools.
        # It must never close PresenterApp.
        if count >= 3:
            self.action_requested.emit("clear")
        elif count == 2:
            self.action_requested.emit("cycle")

    def on_presenter_key_pressed(self):
        if not self.state.enabled:
            return
        now = time.time()
        if now - self.last_press_time > self.multi_press_window:
            self.e_press_count = 0
        self.e_press_count += 1
        self.last_press_time = now
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(self.multi_press_window, self.process_clicks)
        self.timer.daemon = True
        self.timer.start()

    def unregister_hotkeys(self):
        """Remove all PresenterApp keyboard hooks and release suppressed keys."""
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        self.e_press_count = 0
        kb.unhook_all()
        self.registered = False

    def register_hotkeys(self):
        # Always clear old hooks first. This prevents duplicate hooks after
        # changing the presenter key or toggling Enable/Disable repeatedly.
        self.unregister_hotkeys()

        # When disabled, do not register a suppressing hotkey. This is what
        # allows the letter E to type normally again.
        if not self.state.enabled:
            return

        kb.add_hotkey(self.presenter_key, self.on_presenter_key_pressed, suppress=True)
        kb.add_hotkey("esc", lambda: self.action_requested.emit("clear"))
        self.registered = True

    def shutdown(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        self.clear_all()
        self.unregister_hotkeys()


class PresenterMainWindow(QMainWindow):
    def __init__(self, state, settings, listener):
        super().__init__()
        self.state = state
        self.settings = settings
        self.listener = listener
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(980, 660)
        self.setObjectName("MainWindow")
        if ICON_FILE.exists():
            self.setWindowIcon(QIcon(str(ICON_FILE)))
        self.apply_theme()

        root = QWidget()
        root.setObjectName("Root")
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(270)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(24, 28, 24, 24)
        side.setSpacing(18)

        brand_row = QHBoxLayout()
        if ICON_FILE.exists():
            logo = QLabel()
            logo.setPixmap(QIcon(str(ICON_FILE)).pixmap(52, 52))
            logo.setFixedSize(58, 58)
            logo.setAlignment(Qt.AlignCenter)
        else:
            logo = QLabel("P")
            logo.setObjectName("Logo")
            logo.setFixedSize(58, 58)
            logo.setAlignment(Qt.AlignCenter)
        brand_text = QVBoxLayout()
        brand = QLabel("PresenterApp")
        brand.setObjectName("Brand")
        brand_sub = QLabel("Smart overlay controller")
        brand_sub.setObjectName("BrandSub")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_sub)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_text)
        side.addLayout(brand_row)

        self.status_pill = QLabel()
        self.status_pill.setObjectName("StatusPill")
        self.status_pill.setAlignment(Qt.AlignCenter)
        self.status_pill.setMinimumHeight(40)
        side.addWidget(self.status_pill)

        nav_label = QLabel("TOOLS")
        nav_label.setObjectName("SectionLabel")
        side.addWidget(nav_label)
        self.nav_items = {}
        for mode, icon, desc in [
            ("pen", "●", "Laser pointer"),
            ("highlight", "◎", "Yellow ring"),
            ("zoom", "⌕", "Windows lens"),
            ("spotlight", "◉", "Focus beam"),
        ]:
            item = QLabel(f"{icon}  {mode.title()}\n<span>{desc}</span>")
            item.setObjectName("NavItem")
            item.setTextFormat(Qt.RichText)
            item.setMinimumHeight(58)
            item.setAlignment(Qt.AlignVCenter)
            self.nav_items[mode] = item
            side.addWidget(item)

        side.addStretch()
        self.mode_big_label = QLabel()
        self.mode_big_label.setObjectName("ModeBig")
        self.mode_big_label.setAlignment(Qt.AlignCenter)
        self.mode_big_label.setMinimumHeight(82)
        side.addWidget(self.mode_big_label)
        version = QLabel("v1.1  •  Tray background mode")
        version.setObjectName("TinyText")
        version.setAlignment(Qt.AlignCenter)
        side.addWidget(version)

        content = QWidget()
        content.setObjectName("Content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 26)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(26, 24, 26, 24)
        hero_layout.setSpacing(18)
        hero_text = QVBoxLayout()
        eyebrow = QLabel("PROFESSIONAL PRESENTATION CONTROL")
        eyebrow.setObjectName("Eyebrow")
        title = QLabel("Control your screen like a presenter suite")
        title.setObjectName("PageTitle")
        subtitle = QLabel("PresenterApp stays in the background and gives you pen, highlight, zoom lens, and spotlight overlays from one presenter button.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(title)
        hero_text.addWidget(subtitle)
        hero_layout.addLayout(hero_text, 1)
        hero_buttons = QVBoxLayout()
        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("PrimaryButton")
        self.toggle_btn.setMinimumSize(180, 48)
        self.toggle_btn.clicked.connect(self.toggle_enabled)
        clear_btn = QPushButton("Clear / Reset")
        clear_btn.setObjectName("GhostButton")
        clear_btn.setMinimumSize(180, 42)
        clear_btn.clicked.connect(self.listener.clear_all)
        hero_buttons.addWidget(self.toggle_btn)
        hero_buttons.addWidget(clear_btn)
        hero_buttons.addStretch()
        hero_layout.addLayout(hero_buttons)
        layout.addWidget(hero)

        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.enabled_card_value = self.make_stat_card(stats, "APP STATUS", "—", "Power")
        self.mode_card_value = self.make_stat_card(stats, "ACTIVE TOOL", "—", "Mode")
        self.key_card_value = self.make_stat_card(stats, "PRESENTER KEY", "—", "Shortcut")
        layout.addLayout(stats)

        middle = QHBoxLayout()
        middle.setSpacing(16)

        mode_card = QFrame()
        mode_card.setObjectName("Card")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(22, 20, 22, 20)
        mode_layout.setSpacing(14)
        mode_title = QLabel("Mode Workflow")
        mode_title.setObjectName("CardTitle")
        mode_layout.addWidget(mode_title)
        mode_grid = QHBoxLayout()
        mode_grid.setSpacing(10)
        self.mode_chips = {}
        for mode, icon, color in [("pen", "●", "#ef4444"), ("highlight", "◎", "#facc15"), ("zoom", "⌕", "#38bdf8"), ("spotlight", "◉", "#a78bfa")]:
            chip = QLabel(f"<b style='font-size:22px;color:{color}'>{icon}</b><br>{mode.title()}")
            chip.setObjectName("ModeChip")
            chip.setTextFormat(Qt.RichText)
            chip.setAlignment(Qt.AlignCenter)
            chip.setMinimumHeight(92)
            self.mode_chips[mode] = chip
            mode_grid.addWidget(chip)
        mode_layout.addLayout(mode_grid)
        mode_layout.addWidget(self.shortcut_row("Double press", "Move to the next visual tool in the workflow."))
        mode_layout.addWidget(self.shortcut_row("Triple press", "Clear all effects and return to normal cursor."))
        mode_layout.addWidget(self.shortcut_row("Esc", "Reset overlays and close Windows zoom lens."))
        middle.addWidget(mode_card, 2)

        settings_card = QFrame()
        settings_card.setObjectName("Card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(22, 20, 22, 20)
        settings_layout.setSpacing(14)
        settings_title = QLabel("Settings")
        settings_title.setObjectName("CardTitle")
        settings_layout.addWidget(settings_title)
        key_row = QHBoxLayout()
        key_label = QLabel("Presenter button")
        key_label.setObjectName("FieldLabel")
        self.key_combo = QComboBox()
        self.key_combo.setObjectName("Combo")
        self.key_combo.addItems(["e", "f", "q", "space", "page down", "page up"])
        self.key_combo.setCurrentText(self.settings.get("presenter_key", "e"))
        self.key_combo.currentTextChanged.connect(self.change_presenter_key)
        key_row.addWidget(key_label)
        key_row.addStretch()
        key_row.addWidget(self.key_combo)
        settings_layout.addLayout(key_row)
        self.notify_check = self.make_check("Show tray notifications", "show_notifications", self.change_notifications)
        self.start_minimized_check = self.make_check("Start minimized to tray", "start_minimized", self.change_start_minimized)
        self.close_to_tray_check = self.make_check("Pressing X hides to tray", "minimize_to_tray_on_close", self.change_close_to_tray)
        settings_layout.addWidget(self.notify_check)
        settings_layout.addWidget(self.start_minimized_check)
        settings_layout.addWidget(self.close_to_tray_check)
        settings_layout.addStretch()
        note = QLabel("Close behavior: PresenterApp remains in Windows hidden icons until you right-click the tray icon and choose Exit completely.")
        note.setObjectName("NoteBox")
        note.setWordWrap(True)
        settings_layout.addWidget(note)
        middle.addWidget(settings_card, 1)
        layout.addLayout(middle, 1)

        footer = QLabel("Tip: Use the tray icon for Enable/Disable, Clear/Reset, Open Dashboard, or Exit PresenterApp completely.")
        footer.setObjectName("FooterText")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        main.addWidget(sidebar)
        main.addWidget(content)
        self.setCentralWidget(root)
        self.refresh()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow#MainWindow { background: #08111f; }
            QWidget#Root { background: #e8eef7; }
            QFrame#Sidebar {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #111827, stop:.55 #0f172a, stop:1 #020617);
                border-right: 1px solid rgba(255,255,255,.08);
            }
            QWidget#Content { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #eef5ff, stop:1 #e2e8f0); }
            QLabel#Logo { background: #2563eb; color: white; border-radius: 18px; font-size: 30px; font-weight: 900; }
            QLabel#Brand { color: white; font-size: 22px; font-weight: 900; }
            QLabel#BrandSub { color: #94a3b8; font-size: 12px; }
            QLabel#SectionLabel, QLabel#Eyebrow { color: #64748b; font-size: 11px; font-weight: 900; letter-spacing: 1.2px; }
            QLabel#StatusPill { border-radius: 20px; color: white; font-size: 13px; font-weight: 900; padding: 9px 12px; }
            QLabel#NavItem {
                color: #e5e7eb; background: rgba(255,255,255,.055); border: 1px solid rgba(255,255,255,.09);
                border-radius: 16px; padding: 9px 14px; font-size: 15px; font-weight: 850;
            }
            QLabel#NavItem span { color: #94a3b8; font-size: 11px; font-weight: 500; }
            QLabel#ModeBig { color: white; background: rgba(37,99,235,.22); border: 1px solid rgba(96,165,250,.35); border-radius: 22px; font-size: 25px; font-weight: 950; }
            QLabel#TinyText { color: #64748b; font-size: 11px; }
            QFrame#Hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:1 #dbeafe); border: 1px solid #c7d2fe; border-radius: 26px; }
            QLabel#PageTitle { color: #0f172a; font-size: 30px; font-weight: 950; }
            QLabel#PageSubtitle { color: #475569; font-size: 14px; line-height: 1.4; }
            QFrame#Card, QFrame#StatCard { background: rgba(255,255,255,.94); border: 1px solid #d7e0ee; border-radius: 24px; }
            QLabel#CardTitle { color: #0f172a; font-size: 18px; font-weight: 900; }
            QLabel#StatIcon { color: #2563eb; background: #dbeafe; border-radius: 12px; padding: 6px 10px; font-weight: 900; }
            QLabel#StatTitle { color: #64748b; font-size: 11px; font-weight: 900; letter-spacing: 1px; }
            QLabel#StatValue { color: #0f172a; font-size: 24px; font-weight: 950; }
            QLabel#ModeChip { background: #f8fafc; border: 1px solid #dbe3ef; border-radius: 18px; color: #0f172a; font-size: 13px; font-weight: 850; padding: 10px; }
            QLabel#ShortcutKey { color: #172554; background: #dbeafe; border-radius: 11px; padding: 8px 11px; font-weight: 900; min-width: 105px; }
            QLabel#ShortcutDesc, QLabel#FieldLabel { color: #334155; font-size: 13px; font-weight: 700; }
            QLabel#NoteBox { color: #334155; background: #f1f5f9; border: 1px solid #dbe3ef; border-radius: 16px; padding: 12px; font-size: 12px; }
            QLabel#FooterText { color: #64748b; font-size: 12px; }
            QPushButton#PrimaryButton { color: white; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2563eb, stop:1 #7c3aed); border: none; border-radius: 16px; font-size: 14px; font-weight: 900; padding: 10px 18px; }
            QPushButton#PrimaryButton:hover { background: #1d4ed8; }
            QPushButton#GhostButton { color: #1e293b; background: rgba(255,255,255,.75); border: 1px solid #bfdbfe; border-radius: 14px; font-weight: 850; padding: 9px 14px; }
            QPushButton#GhostButton:hover { background: white; }
            QComboBox#Combo { min-width: 145px; padding: 9px 12px; border-radius: 12px; border: 1px solid #cbd5e1; background: white; color: #0f172a; font-weight: 800; }
            QCheckBox#Check { color: #334155; font-size: 13px; spacing: 9px; }
            QCheckBox#Check::indicator { width: 18px; height: 18px; }
        """)

    def make_stat_card(self, parent_layout, title, value, icon):
        card = QFrame()
        card.setObjectName("StatCard")
        card.setMinimumHeight(118)
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 16, 18, 16)
        top = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("StatTitle")
        icon_label = QLabel(icon)
        icon_label.setObjectName("StatIcon")
        top.addWidget(title_label)
        top.addStretch()
        top.addWidget(icon_label)
        value_label = QLabel(value)
        value_label.setObjectName("StatValue")
        box.addLayout(top)
        box.addStretch()
        box.addWidget(value_label)
        parent_layout.addWidget(card)
        return value_label

    def make_check(self, text, setting_key, callback):
        check = QCheckBox(text)
        check.setObjectName("Check")
        check.setChecked(bool(self.settings.get(setting_key, False)))
        check.stateChanged.connect(callback)
        return check

    def shortcut_row(self, key, desc):
        row = QFrame()
        row.setStyleSheet("QFrame { background: transparent; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        key_label = QLabel(key)
        key_label.setObjectName("ShortcutKey")
        desc_label = QLabel(desc)
        desc_label.setObjectName("ShortcutDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(key_label)
        layout.addWidget(desc_label, 1)
        return row

    def refresh(self):
        enabled = self.state.enabled
        mode = self.state.mode.upper()
        self.status_pill.setText("● ENABLED" if enabled else "● DISABLED")
        self.status_pill.setStyleSheet("background: #16a34a;" if enabled else "background: #dc2626;")
        self.mode_big_label.setText(mode)
        self.enabled_card_value.setText("Enabled" if enabled else "Disabled")
        self.mode_card_value.setText(mode)
        self.key_card_value.setText(self.settings.get("presenter_key", "e").upper())
        self.toggle_btn.setText("Disable App" if enabled else "Enable App")
        active = self.state.mode
        for mode_name, item in self.nav_items.items():
            if mode_name == active:
                item.setStyleSheet("background: rgba(37,99,235,.38); border: 1px solid rgba(96,165,250,.65);")
            else:
                item.setStyleSheet("")
        for mode_name, chip in self.mode_chips.items():
            if mode_name == active:
                chip.setStyleSheet("background: #eff6ff; border: 2px solid #2563eb; border-radius: 18px;")
            else:
                chip.setStyleSheet("")

    def toggle_enabled(self):
        self.listener.set_enabled(not self.state.enabled)

    def change_presenter_key(self, key):
        self.settings["presenter_key"] = key
        save_settings(self.settings)
        self.listener.register_hotkeys()
        self.refresh()

    def change_notifications(self):
        self.settings["show_notifications"] = self.notify_check.isChecked()
        save_settings(self.settings)

    def change_start_minimized(self):
        self.settings["start_minimized"] = self.start_minimized_check.isChecked()
        save_settings(self.settings)

    def change_close_to_tray(self):
        self.settings["minimize_to_tray_on_close"] = self.close_to_tray_check.isChecked()
        save_settings(self.settings)

    def closeEvent(self, event):
        if self.settings.get("minimize_to_tray_on_close", True):
            event.ignore()
            self.hide()
            if not self.settings.get("close_to_tray_tip_shown", False) and QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon_for_close_tip.showMessage(
                    APP_NAME,
                    "Still running in hidden icons. Right-click the tray icon and choose 'Exit PresenterApp completely' when you finish.",
                    QSystemTrayIcon.Information,
                    2500,
                )
                self.settings["close_to_tray_tip_shown"] = True
                save_settings(self.settings)
        else:
            event.accept()

    def attach_tray_icon(self, tray_icon):
        self.tray_icon_for_close_tip = tray_icon



class PresenterTray:
    def __init__(self, app, window, state, listener, settings):
        self.app = app
        self.window = window
        self.state = state
        self.listener = listener
        self.settings = settings

        self.tray = QSystemTrayIcon(self.make_icon(), app)
        self.menu = QMenu()
        self.show_action = QAction("Open PresenterApp")
        self.enable_action = QAction()
        self.clear_action = QAction("Clear / Reset")
        self.quit_action = QAction("Exit PresenterApp completely")

        self.show_action.triggered.connect(self.show_window)
        self.enable_action.triggered.connect(lambda: self.listener.set_enabled(not self.state.enabled))
        self.clear_action.triggered.connect(self.listener.clear_all)
        self.quit_action.triggered.connect(self.quit_app)

        self.menu.addAction(self.show_action)
        self.menu.addAction(self.enable_action)
        self.menu.addAction(self.clear_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_activated)
        self.tray.show()
        self.window.attach_tray_icon(self.tray)
        self.refresh()

    def make_icon(self):
        if ICON_FILE.exists():
            return QIcon(str(ICON_FILE))

        # Fallback generated icon if the external asset is missing.
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(37, 99, 235))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(5, 5, 54, 54, 16, 16)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(18, 17, 12, 12)
        painter.drawEllipse(35, 17, 12, 12)
        painter.setPen(QPen(QColor(255, 255, 255), 5))
        painter.drawLine(22, 42, 42, 42)
        painter.end()
        return QIcon(pixmap)

    def refresh(self):
        self.enable_action.setText("Disable" if self.state.enabled else "Enable")
        self.tray.setToolTip(f"{APP_NAME} - {'Enabled' if self.state.enabled else 'Disabled'} - Mode: {self.state.mode}\nDouble-click to open. Right-click to exit completely.")
        self.window.refresh()

    def show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def quit_app(self):
        self.listener.shutdown()
        self.tray.hide()
        self.app.quit()

    def show_message(self, title, text):
        if self.settings.get("show_notifications", True):
            self.tray.showMessage(title, text, QSystemTrayIcon.Information, 1200)


def main():
    app = QApplication(sys.argv)
    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))
    app.setQuitOnLastWindowClosed(False)

    settings = load_settings()
    state = SharedState()
    state.enabled = bool(settings.get("enabled", True))

    overlays = [PresenterOverlay(screen, state) for screen in app.screens()]
    state.overlays = overlays

    listener = KeyListener(state, settings)
    window = PresenterMainWindow(state, settings, listener)
    tray = PresenterTray(app, window, state, listener, settings)

    def status_changed():
        tray.refresh()

    listener.on_status_changed = status_changed
    listener.register_hotkeys()

    if not settings.get("start_minimized", False):
        window.show()
    tray.show_message(APP_NAME, "Running in the background.")

    try:
        sys.exit(app.exec())
    finally:
        listener.shutdown()


if __name__ == "__main__":
    main()
