import sys
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
from pynput.keyboard import Controller, Key


class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        display_text = text.replace("&", "&&") if "&" in text else text
        super().__init__(display_text, parent)
        self.raw_text = text
        self.setMinimumHeight(55)
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

    def _on_toggle(self, checked):
        if checked:
            self.setStyleSheet(
                "QPushButton { background-color: #0078D4; color: white; border-radius: 8px; font-weight: bold; border: 1px solid #005A9E; }"
            )
        else:
            self.update_style()

    def is_active(self):
        try:
            return self.isChecked()
        except RuntimeError:
            return False

    def reset(self):
        try:
            self.setChecked(False)
        except RuntimeError:
            pass


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
        self.layout_mode = "letters"  # letters or symbols
        self.language = "EN"  # EN or AR

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
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self.clear_sub_layout(item.layout())

        self.container_layout.addWidget(DragHandle())

        # Determine which layout to load
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

                # Dynamic text for the language toggle button
                if key == "Lang":
                    btn.setText("AR" if self.language == "EN" else "EN")

                # Sizing
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
                item.widget().setParent(None)
                item.widget().deleteLater()

    def handle_keypress(self, key_label):
        if key_label == "Exit":
            self.close()
            return

        # Toggle between Symbols and Letters
        if key_label == "?123":
            self.layout_mode = "symbols"
            self.refresh_keyboard()
            return
        if key_label == "ABC":
            self.layout_mode = "letters"
            self.refresh_keyboard()
            return

        # Toggle Language
        if key_label == "Lang":
            self.language = "AR" if self.language == "EN" else "EN"
            self.refresh_keyboard()
            return

        if key_label in ["Shift", "Ctrl", "Alt", "Caps"]:
            return

        key_map = {"Back": Key.backspace, "Enter": Key.enter, "Space": Key.space}
        target_key = key_map.get(key_label, key_label)

        # Capitalization logic for English letters
        if (
            self.language == "EN"
            and self.layout_mode == "letters"
            and isinstance(target_key, str)
            and len(target_key) == 1
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
            target_key = (
                target_key.upper() if (is_caps != is_shift) else target_key.lower()
            )

        self._type(target_key)

    def _type(self, key_obj):
        active_mods = []
        for name, key_type in [
            ("Shift", Key.shift),
            ("Ctrl", Key.ctrl),
            ("Alt", Key.alt),
        ]:
            btn = self.modifiers.get(name)
            if btn and btn.is_active():
                active_mods.append(key_type)

        for m in active_mods:
            self.keyboard_controller.press(m)

        # pynput handles strings (like Arabic chars) via tap
        self.keyboard_controller.tap(key_obj)

        for m in active_mods:
            self.keyboard_controller.release(m)

        for name in ["Shift", "Ctrl", "Alt"]:
            btn = self.modifiers.get(name)
            if btn:
                btn.reset()

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


"""type testing:
#$^&`~
"""
