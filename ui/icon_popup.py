import sys
import math
import keyboard
import threading
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QObject,
    Signal,
    Property,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
)
from PySide6.QtGui import QCursor, QColor, QPainter, QBrush


class AnimatedHoverButton(QPushButton):
    """Button that handles its own hover transition via QPropertyAnimation"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.hover_anim = None
        self._color = QColor("white")

        # Setup opacity effect for the staggering fade-in
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.update_style()

    @Property(QColor)
    def color(self):  # type: ignore
        return self._color

    @color.setter
    def color(self, val):
        self._color = val
        self.update_style()

    def update_style(self):
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self._color.name()};
                border-radius: 25px;
                font-size: 14px;
                font-weight: bold;
                color: black;
                border: none;
            }}
            QPushButton:pressed {{
                background-color: #1f618d;
                color: white;
            }}
        """
        )

    def enterEvent(self, event):
        self.hover_anim = QPropertyAnimation(self, b"color")
        self.hover_anim.setDuration(200)
        self.hover_anim.setEndValue(QColor("gray"))
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim = QPropertyAnimation(self, b"color")
        self.hover_anim.setDuration(200)
        self.hover_anim.setEndValue(QColor("white"))
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.start()
        super().leaveEvent(event)


class ButtonCircle(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.num_buttons = 8
        self.radius = 100
        self.button_size = 50

        window_size = self.radius * 2 + self.button_size + 20
        self.resize(window_size, window_size)

        self.buttons = []
        self.target_geometries = []
        self.animations = []

        self.create_buttons()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # type: ignore
        painter.setPen(Qt.NoPen)  # type: ignore
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))

    def create_buttons(self):
        for i in range(self.num_buttons):
            angle = (2 * math.pi * i) / self.num_buttons - math.pi / 2
            btn_x = self.radius * math.cos(angle)
            btn_y = self.radius * math.sin(angle)

            center = self.width() // 2
            x = int(center + btn_x - self.button_size // 2)
            y = int(center + btn_y - self.button_size // 2)

            btn = AnimatedHoverButton(f"{i + 1}", self)
            btn.setGeometry(x, y, self.button_size, self.button_size)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            btn.clicked.connect(lambda checked, n=i + 1: self.button_clicked(n))

            self.buttons.append(btn)
            self.target_geometries.append(
                QRect(x, y, self.button_size, self.button_size)
            )

    def animate_entry(self):
        """Staggered pop-out with position and opacity animation"""
        self.animations.clear()

        center_rect = QRect(
            self.width() // 2 - self.button_size // 2,
            self.height() // 2 - self.button_size // 2,
            self.button_size,
            self.button_size,
        )

        stagger_delay = 40  # ms between button starts

        for i, btn in enumerate(self.buttons):
            # 1. Reset Position and Opacity
            btn.setGeometry(center_rect)
            btn.opacity_effect.setOpacity(0.0)

            # 2. Geometry Animation (Fly out)
            pos_anim = QPropertyAnimation(btn, b"geometry")
            pos_anim.setDuration(450)
            pos_anim.setStartValue(center_rect)
            pos_anim.setEndValue(self.target_geometries[i])
            pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)

            # 3. Opacity Animation (Fade in)
            fade_anim = QPropertyAnimation(btn.opacity_effect, b"opacity")
            fade_anim.setDuration(300)
            fade_anim.setStartValue(0.0)
            fade_anim.setEndValue(1.0)

            self.animations.extend([pos_anim, fade_anim])

            # Start both animations with a delay
            QTimer.singleShot(i * stagger_delay, pos_anim.start)
            QTimer.singleShot(i * stagger_delay, fade_anim.start)

    def button_clicked(self, button_num):
        self.hide()

    def show_at_cursor(self):
        try:
            cursor_pos = QCursor.pos()
            window_center = QPoint(self.width() // 2, self.height() // 2)
            self.move(cursor_pos - window_center)

            # Show window and trigger staggered animations
            self.show()
            self.animate_entry()

            self.setFocus()
            self.activateWindow()
            self.raise_()
        except Exception as e:
            print(f"Error in show_at_cursor: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()


class SignalEmitter(QObject):
    toggle_signal = Signal()
    quit_signal = Signal()


class ButtonCircleApp:
    def __init__(self):
        self.hotkey_thread = None
        self.app = QApplication(sys.argv)
        self.window = ButtonCircle()
        self.is_running = True
        self.signal_emitter = SignalEmitter()

        self.signal_emitter.toggle_signal.connect(self._toggle_window_impl)
        self.signal_emitter.quit_signal.connect(self._quit_app_impl)

        self.setup_hotkeys()

    def setup_hotkeys(self):
        def hotkey_listener():
            try:
                keyboard.add_hotkey("ctrl+space", self.toggle_window, suppress=False)
                keyboard.add_hotkey("ctrl+q", self.quit_app, suppress=False)
                while self.is_running:
                    keyboard.read_event(suppress=False)
            except Exception as e:
                print(f"Hotkey Error: {e}")

        self.hotkey_thread = threading.Thread(target=hotkey_listener, daemon=True)
        self.hotkey_thread.start()

    def toggle_window(self):
        self.signal_emitter.toggle_signal.emit()

    def _toggle_window_impl(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.window.show_at_cursor()

    def quit_app(self):
        self.signal_emitter.quit_signal.emit()

    def _quit_app_impl(self):
        self.is_running = False
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = ButtonCircleApp()
    app.run()
