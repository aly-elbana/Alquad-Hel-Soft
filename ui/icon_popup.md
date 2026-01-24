# Icon Popup API:

## 1. Architectural Overview
The application is structured into three primary components:
1. AnimatedHoverButton: A specialized QPushButton that handles its own visual states and animations.
2. ButtonCircle: The main UI container that manages the circular layout, the dark translucent background, and the entry/exit logic.
3. ButtonCircleApp: The logic controller that handles global hotkeys via a background thread and manages the application lifecycle.

<hr>

## 2. Component Details

### A. AnimatedHoverButton (Custom Widget)
This class extends `QPushButton` to overcome the limitations of Qt Style Sheets (QSS), specifically the lack of support for the `transition` property.

- **Color Transition**: Uses a `Property(QColor)` to allow `QPropertyAnimation` to interpolate between white and gray during hover events.

- **Opacity Handling**: Incorporates a `QGraphicsOpacityEffect`. This is essential because standard widgets do not have an inherent `opacity` property that can be animated directly.

- **Events**:

  - `enterEvent`: Triggers a 200ms animation to the hover color (gray).

  - `leaveEvent`: Triggers a 200ms animation back to the base color (white).

### B. ButtonCircle (Main Window)
A frameless, translucent QWidget that serves as the canvas for the radial menu.

- **Window Management**:

    - `WindowStaysOnTopHint`: Ensures the menu is never hidden behind other apps.

    - `FramelessWindowHint`: Removes standard OS window borders.

    - `WA_TranslucentBackground`: Allows for the semi-transparent circular aesthetic.

- Mathematical Layout: Buttons are positioned using polar-to-cartesian conversion:
$$x = \text{radius} \cdot \cos(\theta)$$
$$y = \text{radius} \cdot \sin(\theta)$$
- The "Pop-Out" Animation:
  - Staggering: Each button's animation start time is offset by an index-based delay ($index \cdot 40ms$).
  - Easing: Uses QEasingCurve.Type.OutBack, which creates a professional "overshoot" effect where buttons fly slightly past their target and settle back.

### C. ButtonCircleApp (Controller)
Manages the integration between the OS-level hotkeys and the Qt Main Thread.

- Multithreading: The `keyboard` library blocks execution, so it is run in a separate `daemon` thread.
- Thread Safety: Since Qt UI elements cannot be modified from a non-GUI thread, a `SignalEmitter` (QObject) is used to communicate between the hotkey listener and the main window.

<hr>

## 3. Configuration & Constants
You can customize the look and feel by modifying these variables within the `ButtonCircle.__init__`:

| Variable        | Description                           | Default Value |
|-----------------|---------------------------------------|---------------|
| `num_buttons`   | Total buttons in the circle           | 8             |
| `radius`        | Distance from center to button center | 100px         |
| `button_size`   | Width/Height of each button           | 50px          |
| `stagger_delay` | Delay between each button "popping"   | 40ms          |
| `window_size`   | Total canvas area (calculated)        | ~270px        |

<hr>

## 4. Usage & Controls

| Action           | Command               |
|------------------|-----------------------|
| Show/Hide Menu   | Ctrl + Space          |
| Close Menu       | Escape (when focused) |
| Select Option    | Left Click            |
| Exit Application | Ctrl + Q              |

<hr>

## 5. Known Limitations
- Focus Requirement: For the Escape key to hide the window, the window must have active focus.
- OS Transparency: On some Linux distributions without a compositor (like Compton or Picom), the `WA_TranslucentBackground` attribute may render as a solid black block.