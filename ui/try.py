from PySide6.QtWidgets import QApplication
import sys
import os
from folder_popup import FileLauncher

# Example Usage
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Dict with your file/folder names and absolute paths
    my_files = {
        "Documents": os.path.expanduser("~/Documents"),
        "Scripts": os.path.abspath("../"),
        "Config": "C:/Windows/System32/drivers/etc/hosts" if sys.platform == "win32" else "/etc/hosts",
        "The Hobbit: The Fellowship": "D:/Entertainment/movies/The Hobbit The Battle of the Five Armies 2014.mp4"
    }
    
    launcher = FileLauncher(my_files)
    
    # Center the launcher on the screen
    screen_geo = app.primaryScreen().geometry()
    launcher.move(
        (screen_geo.width() - launcher.width()) // 2,
        (screen_geo.height() - launcher.height()) // 2
    )
    
    launcher.show_animated()
    sys.exit(app.exec())
    