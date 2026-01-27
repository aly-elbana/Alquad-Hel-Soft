import sys
import platform
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor

# Pynput is always imported as a fallback/helper
from pynput.keyboard import Controller, Key

# Try to import keyboard lib
try:
    import keyboard as kb_lib

    HAS_KEYBOARD_LIB = True
except ImportError:
    HAS_KEYBOARD_LIB = False

# Try to import win32 for the focus fix
if platform.system() == "Windows":
    try:
        import win32gui
        import win32con

        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False


class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        # Handle the "&" character for display (Qt uses & for shortcuts)
        display_text = text.replace("&", "&&") if "&" in text else text
        super().__init__(display_text, parent)
        self.raw_text = text
        self.setMinimumHeight(55)
        # Prevent the button itself from stealing focus
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def update_style(self):
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #222222; padding-top: 2px; }
        """
        )


class ModifierButton(ModernButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.toggled.connect(self._on_toggle)
        # Modifiers (Ctrl/Shift) should NOT auto-repeat
        self.setAutoRepeat(False)

    def _on_toggle(self, checked):
        if checked:
            self.setStyleSheet(
                "QPushButton { background-color: #0078D4; color: white; border-radius: 8px; font-weight: bold; border: 1px solid #005A9E; }"
            )
        else:
            self.update_style()

    def is_active(self):
        return self.isChecked()

    def reset(self):
        self.setChecked(False)


class DragHandle(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setStyleSheet(
            "background: #222; border-top-left-radius: 15px; border-top-right-radius: 15px;"
        )
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()


class VirtualKeyboard(QWidget):
    def __init__(self):
        super().__init__()
        self.keyboard_controller = Controller()
        self.modifiers = {}
        self.layout_mode = "letters"
        self.language = "EN"

        self.layouts = {
            "EN_letters": [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "Back"],
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", "Enter"],
                ["Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "Exit"],
                ["?123", "Lang", "Ctrl", "Alt", "Space"],
            ],
            "AR_letters": [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "Back"],
                ["ض", "ص", "ث", "ق", "ف", "غ", "ع", "ه", "خ", "ح", "ج", "د"],
                [
                    "Caps",
                    "ش",
                    "س",
                    "ي",
                    "ب",
                    "ل",
                    "ا",
                    "ت",
                    "ن",
                    "م",
                    "ك",
                    "ط",
                    "Enter",
                ],
                ["Shift", "ئ", "ء", "ؤ", "ر", "لا", "ى", "ة", "و", "ز", "ظ", "Exit"],
                ["?123", "Lang", "Ctrl", "Alt", "Space"],
            ],
            "symbols": [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "Back"],
                ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"],
                ["+", "-", "=", "_", "[", "]", "{", "}", "\\", "|", "Enter"],
                ["<", ">", "?", "/", ";", ":", "'", '"', "~", "`", "Exit"],
                ["ABC", "Lang", "Ctrl", "Alt", "Space"],
            ],
        }

        # Setup Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setup_ui()
        self.slide_anim = QPropertyAnimation(self, b"pos")

    def showEvent(self, event):
        super().showEvent(event)
        # Apply the Windows-specific fix to prevent focus stealing
        self.set_no_activate_flag()

    def set_no_activate_flag(self):
        if HAS_WIN32:
            try:
                hwnd = int(self.winId())
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                # WS_EX_NOACTIVATE (0x08000000) prevents the window from becoming active on click
                new_style = (
                    ex_style | win32con.WS_EX_NOACTIVATE | win32con.WS_EX_TOPMOST
                )
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
            except Exception:
                pass

    def setup_ui(self):
        self.setFixedSize(1050, 420)
        self.main_layout = QVBoxLayout(self)
        self.container = QFrame()
        self.container.setStyleSheet(
            "background-color: #1e1e1e; border-radius: 15px; border: 1px solid #333;"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(5, 0, 5, 15)

        self.refresh_keyboard()
        self.main_layout.addWidget(self.container)

    def refresh_keyboard(self):
        self.setUpdatesEnabled(False)
        self.modifiers.clear()

        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()  # type: ignore
            elif item.layout():
                self.clear_sub_layout(item.layout())

        self.container_layout.addWidget(DragHandle())

        if self.layout_mode == "symbols":
            current_rows = self.layouts["symbols"]
        else:
            current_rows = self.layouts[f"{self.language}_letters"]

        for row in current_rows:
            row_layout = QHBoxLayout()
            row_layout.addStretch()
            for key in row:
                if key in ["Shift", "Ctrl", "Alt", "Caps"]:
                    btn = ModifierButton(key)
                    self.modifiers[key] = btn
                else:
                    btn = ModernButton(key)
                    # Enable Auto-Repeat only for normal keys (letters, backspace, etc)
                    if key not in ["Exit", "Lang", "?123", "ABC"]:
                        btn.setAutoRepeat(True)
                        btn.setAutoRepeatDelay(400)
                        btn.setAutoRepeatInterval(50)

                # Special widths
                if key == "Lang":
                    btn.setText("AR" if self.language == "EN" else "EN")

                if key == "Space":
                    btn.setMinimumWidth(400)
                elif key in [
                    "Back",
                    "Enter",
                    "Shift",
                    "Exit",
                    "Caps",
                    "?123",
                    "ABC",
                    "Lang",
                ]:
                    btn.setMinimumWidth(85)
                else:
                    btn.setFixedSize(65, 55)

                btn.clicked.connect(lambda chk=False, k=key: self.handle_keypress(k))
                row_layout.addWidget(btn)
            row_layout.addStretch()
            self.container_layout.addLayout(row_layout)

        self.setUpdatesEnabled(True)
        self.update()

    def clear_sub_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def handle_keypress(self, key_label):
        if key_label == "Exit":
            self.close()
            sys.exit()

        if key_label in ["Shift", "Ctrl", "Alt", "Caps"]:
            return

        if key_label == "?123":
            self.layout_mode = "symbols"
            self.refresh_keyboard()
            return
        if key_label == "ABC":
            self.layout_mode = "letters"
            self.refresh_keyboard()
            return
        if key_label == "Lang":
            self.language = "AR" if self.language == "EN" else "EN"
            self.refresh_keyboard()
            return

        # --- KEY MAPPING ---
        # Map UI Labels to proper internal names
        key_map = {"Back": "backspace", "Enter": "\n", "Space": " "}
        target_key = key_map.get(key_label, key_label)

        # Handle Case (Upper/Lower) for single letters
        if (
            self.language == "EN"
            and self.layout_mode == "letters"
            and len(target_key) == 1  # type: ignore
        ):
            is_caps = (
                self.modifiers.get("Caps").is_active()  # type: ignore
                if "Caps" in self.modifiers
                else False
            )
            is_shift = (
                self.modifiers.get("Shift").is_active()  # type: ignore
                if "Shift" in self.modifiers
                else False
            )

            if is_caps != is_shift:
                target_key = target_key.upper()  # type: ignore
            else:
                target_key = target_key.lower()  # type: ignore

        self._send_key(target_key)

    def _send_key(self, key_to_send):
        """
        Sends the key event.
        - key_to_send: "a", "A", "backspace", "enter", "space", etc.
        """

        # 1. Identify Modifiers
        active_mods = []
        if self.modifiers.get("Ctrl") and self.modifiers.get("Ctrl").is_active():  # type: ignore
            active_mods.append("ctrl")
        if self.modifiers.get("Alt") and self.modifiers.get("Alt").is_active():  # type: ignore
            active_mods.append("alt")
        if self.modifiers.get("Shift") and self.modifiers.get("Shift").is_active():  # type: ignore
            active_mods.append("shift")

        # 2. Try using the 'keyboard' library (Preferred for Windows)
        if HAS_KEYBOARD_LIB:
            try:
                # LIST OF KEYS THAT MUST BE 'PRESSED' (Commands), NOT 'WRITTEN' (Text)
                command_keys = [
                    "backspace",
                    "enter",
                    "space",
                    "tab",
                    "esc",
                    "delete",
                    "up",
                    "down",
                    "left",
                    "right",
                ]

                if active_mods:
                    # Case A: Modifiers are active (e.g., Ctrl+C, Ctrl+Backspace)
                    combo = "+".join(active_mods) + "+" + key_to_send
                    kb_lib.send(combo)

                elif key_to_send.lower() in command_keys:
                    # Case B: It is a command key (e.g., Backspace)
                    # Use press_and_release to ensure it acts as a keystroke, not text
                    kb_lib.press_and_release(key_to_send)

                else:
                    # Case C: It is a normal character (e.g., 'a', '1', 'ش')
                    # Use write so it handles Unicode/Arabic correctly
                    kb_lib.write(key_to_send)

            except Exception:
                # If keyboard lib fails, fallback
                self._send_via_pynput(key_to_send, active_mods)
        else:
            # 3. Fallback to 'pynput' (Linux/Mac or if keyboard lib missing)
            self._send_via_pynput(key_to_send, active_mods)

        # 4. Reset Sticky Keys (except Caps)
        for name in ["Shift", "Ctrl", "Alt"]:
            btn = self.modifiers.get(name)
            if btn and btn.is_active():
                btn.reset()

    def _send_via_pynput(self, key_str, active_mods):
        # Press modifiers
        for mod in active_mods:
            if hasattr(Key, mod):
                self.keyboard_controller.press(getattr(Key, mod))

        # Press Key
        # Check if the string matches a Pynput Key attribute (e.g. "backspace" -> Key.backspace)
        # Note: Pynput attributes are usually lowercase
        if hasattr(Key, key_str.lower()):
            self.keyboard_controller.tap(getattr(Key, key_str.lower()))
        else:
            self.keyboard_controller.type(key_str)

        # Release modifiers
        for mod in active_mods:
            if hasattr(Key, mod):
                self.keyboard_controller.release(getattr(Key, mod))

    def show_animated(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y_end = screen.height() - self.height() - 50
        self.move(x, screen.height() + 10)
        self.show()

        self.slide_anim.setTargetObject(self)
        self.slide_anim.setPropertyName(b"pos")
        self.slide_anim.setDuration(500)
        self.slide_anim.setStartValue(QPoint(x, screen.height() + 10))
        self.slide_anim.setEndValue(QPoint(x, y_end))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kb = VirtualKeyboard()
    QTimer.singleShot(100, kb.show_animated)
    sys.exit(app.exec())

"""

"""
