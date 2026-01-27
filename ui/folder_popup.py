from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QFileIconProvider,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QSize,
    QUrl,
    QFileInfo,
    QEvent,
)
from PySide6.QtGui import QDesktopServices, QColor, QGuiApplication
from PySide6.QtWidgets import QApplication
import sys


class FileLauncher(QWidget):
    def __init__(self, files: dict):
        super().__init__()
        self.slide_in = None
        self.fade_in = None
        self.fade_out = None
        self.files = files
        self._is_closing = False  # Prevent redundant animation triggers

        # 1. Window Configuration
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)  # type: ignore
        self.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore

        # 2. UI Layout Setup
        self.main_layout = QVBoxLayout(self)
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(
            """
            #Container {
                background-color: rgba(25, 25, 25, 225);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 45);
            }
        """
        )

        self.content_layout = QHBoxLayout(self.container)
        self.content_layout.setContentsMargins(30, 25, 30, 25)
        self.content_layout.setSpacing(20)
        self.main_layout.addWidget(self.container)

        # 3. Populate Items
        icon_provider = QFileIconProvider()
        for name, path in self.files.items():
            item_widget = self._create_item(name, path, icon_provider)
            self.content_layout.addWidget(item_widget)

        # 4. Visual Polish (Shadow)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

    def _create_item(self, name, path, provider):
        item_container = QWidget()
        item_layout = QVBoxLayout(item_container)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(8)

        file_info = QFileInfo(path)
        icon = provider.icon(file_info)

        btn = QPushButton()
        btn.setIcon(icon)
        btn.setIconSize(QSize(54, 54))
        btn.setFixedSize(70, 70)
        btn.setCursor(Qt.PointingHandCursor)  # type: ignore
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                border-radius: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
            }
        """
        )
        btn.clicked.connect(lambda: self._launch(path))

        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)  # type: ignore
        label.setFixedWidth(85)
        label.setWordWrap(True)
        label.setStyleSheet("color: #E0E0E0; font-size: 12px; font-weight: 500;")

        item_layout.addWidget(btn, alignment=Qt.AlignCenter)  # type: ignore
        item_layout.addWidget(label, alignment=Qt.AlignCenter)  # type: ignore

        return item_container

    def _launch(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        self.hide_animated()

    def center_on_screen(self):
        self.adjustSize()
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def show_animated(self):
        """Standard show with fade and pop-up effect."""
        self.center_on_screen()
        self.show()
        self.activateWindow()  # Ensure it takes focus to detect later dismissal

        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.OutCubic)  # type: ignore

        self.slide_in = QPropertyAnimation(self, b"pos")
        self.slide_in.setDuration(400)
        self.slide_in.setStartValue(self.pos() + QPoint(0, 40))
        self.slide_in.setEndValue(self.pos())
        self.slide_in.setEasingCurve(QEasingCurve.OutBack)  # type: ignore

        self.fade_in.start()
        self.slide_in.start()

    def hide_animated(self):
        """Fades out and closes the widget."""
        if self._is_closing:
            return
        self._is_closing = True

        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(200)
        self.fade_out.setStartValue(self.windowOpacity())
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.close)
        self.fade_out.start()

    def changeEvent(self, event: QEvent):
        """Detects when the window loses focus to dismiss it."""
        if event.type() == QEvent.ActivationChange:  # type: ignore
            if not self.isActiveWindow():
                self.hide_animated()
                sys.exit(0)
        super().changeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    my_files = {
        "CV (2025)": "D:/Certificates/CV (2025).pdf",
        "The Hobbit: The Fellowship": "D:/Entertainment/movies/The Hobbit The Battle of the Five Armies 2014.mp4",
    }

    launcher = FileLauncher(my_files)

    screen_geo = app.primaryScreen().geometry()
    launcher.move(
        (screen_geo.width() - launcher.width()) // 2,
        (screen_geo.height() - launcher.height()) // 2,
    )

    launcher.show_animated()
    sys.exit(app.exec())
