# PySide6 Animated File Launcher
A sleek, glassmorphism-inspired "launcher" interface for PySide6. This class creates a frameless, translucent popup that displays system icons for specific files or folders and launches them with a smooth "pop-up" animation.

## 🚀 Features
- Dynamic System Icons: Automatically fetches the correct OS icon for any file or folder path.
- Modern Animations: Uses QEasingCurve to provide a springy, high-end feel.
- Auto-Dismiss: The window automatically fades out and closes if you click anywhere else on the screen.
- Translucent UI: A frosted-glass effect with a soft drop shadow.
<hr>

## 🛠 Installation
To run this launcher, you need Python 3.x and the PySide6 library.

```bash
pip install PySide6
```
<hr>

## 📖 How to Use
Simply import the FileLauncher class and pass it a dictionary where:

- Key: The display name you want shown under the icon.
- Value: The absolute path to the file or folder.

### Basic Example
```python
import sys
from PySide6.QtWidgets import QApplication
from folder_popup import FileLauncher # Assuming your file is named folder_popup.py

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Define the files/folders you want to display
    my_files = {
        "Projects": "C:/Users/Source/Repos",
        "Notes": "D:/Documents/Daily_Notes.txt",
        "Downloads": "C:/Users/Downloads"
    }
    
    # Initialize and show
    launcher = FileLauncher(my_files)
    launcher.show_animated()
    
    sys.exit(app.exec())
```
<hr>

## 🏗 Component Structure
The launcher is built using a nested widget hierarchy to ensure animations and shadows render correctly on a translucent background.

| Method            | Description                                                                        |
|-------------------|------------------------------------------------------------------------------------|
| `__init__(files)` | Sets up the frameless window, translucency, and builds the UI from the dict.       |
| `show_animated()` | Centers the widget on the primary screen and triggers the fade/slide-up animation. |
| `hide_animated()` | Triggers a fade-out animation and closes the application gracefully.               |
| `changeEvent()`   | Monitors window focus to trigger dismissal when the user clicks away.              |

<hr>

## 🎨 Customization
You can easily adjust the visual style within the `__init__` method's stylesheet section:

- Transparency: Adjust the `rgba` alpha value (currently `225`) in the `#Container` style.
- Rounding: Change the `border-radius` (currently `24px`) for sharper or rounder corners.
- Animation Speed: Modify the `.setDuration()` values (in milliseconds) inside `show_animated`.

<hr>

&nbsp; &nbsp;Note: This class uses `Qt.Tool`, which prevents the window from appearing in the OS taskbar while it is open, keeping your workspace clean.