# CNC Door Wizard

A PySide6 desktop application for generating CNC G-code files for **door manufacturing**. Select hinge, lock, and barrel profiles, configure door dimensions, then generate customized right/left G-code files through an automatic variable replacement pipeline.

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.0%2B-green)

## Preview

![CNC Door Milling Preview](preview/cnc%20door%20milling.gif)

## Features

- **Profiles** — create reusable hinge, lock, and barrel *types* (a G-code template with variable placeholders) and *profiles* (named instances with specific values for those placeholders)
- **Door setup** — configure door dimensions, up to 10 hinges, and lock/barrel positions, each manual or auto-calculated; live visual preview as you edit
- **Spreadsheet import** — pull dimensions and positions from an existing spreadsheet, or create one from a template and edit it in-app
- **G-code editor** — LinuxCNC-aware syntax highlighting, template variable highlighting, and inline error detection with a built-in $-variable reference
- **Two-pass generation** — profile G-codes are resolved first, then embedded into the right/left door templates to produce the final output files
- **Projects** — save/load full projects and profile sets so you can pick up where you left off

## Installation

### Prerequisites

- Python 3.8 or higher

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/maro7tigre/cnc_doors_milling
   cd cnc_doors_milling
   ```

1. Create a virtual environment (recommended):

   ```bash
   python -m venv .venv

   # On Windows
   .venv\Scripts\activate

   # On Linux/Mac
   source .venv/bin/activate
   ```

1. Install dependencies:

   ```bash
   pip install PySide6
   ```

1. Run the application:

   ```bash
   python main.py
   ```

## Usage

### Workflow

1. **Profile Selection tab**
   - Create hinge, lock, and barrel types with G-code templates and variable definitions
   - Create profiles under each type with specific values
   - Select one active profile per component category — at least one is required before the Door Setup tab enables

1. **Door Setup tab**
   - Enter door dimensions manually, or import them from a spreadsheet
   - Enable/disable hinges and configure lock/barrel positions (manual or auto)
   - Choose left/right orientation
   - Edit the right and left G-code templates, embedding component G-code with `{$hinges_gcode}`, `{$lock_gcode}`, `{$barrel_gcode}`

1. **Generate Files tab**
   - Review the processed right/left G-code output
   - Edit directly if needed — a sync indicator flags stale output
   - Export both files to `~/CNC/Output/` (or a custom directory)

### Variable System

Templates use two kinds of placeholders:

- **`{L1}`, `{L2:default}`, `{feed_rate:1000}`** — resolved from whichever profile is active for that component. These live inside a type's template; the placeholders you write there define the input fields shown when creating a profile of that type.
- **`{$door_height}`, `{$lock_x_position}`, ...** — door-wide values set once in the Door Setup tab and shared across every template. `{$hinges_gcode}`, `{$lock_gcode}`, `{$barrel_gcode}` are a special case: they embed the resolved G-code of the active hinge/lock/barrel profile.

Click the **`?`** button in the G-code editor for the full list of available `$` variables.

### Example Templates

`examples/linuxcnc/` contains a working set of starter templates for a LinuxCNC-based door router, showing how types, profiles, and `{$...}` / `{L1:default}` placeholders fit together in practice.

> [!WARNING]
> These are a starting point, not a plug-and-play solution — they were written for one specific machine (tool numbers, spindle selects, feeds, work offsets, axis directions). Read through them, adapt them to your own machine, and confirm the resulting toolpath before it touches material.

### Parameter Preview Images

Drop an image into `parameter_images/`, named after a `$variable` (e.g. `door_height.png`). When that field is focused in the Door Setup tab, the app shows the matching image as a preview.

## Project Structure

```text
cnc_doors_milling/
├── main.py
├── theme_manager.py
│
├── examples/linuxcnc/      # Starter G-code templates (see Usage above)
├── parameter_images/       # Context-sensitive parameter preview images
├── profiles/               # Saved profile sets and profile/type images
├── projects/               # Full project saves ($ variables + generated G-codes)
├── preview/                # App screenshots / demo media
├── themes/                 # dark / light / purple theme definitions
│
└── ui/
    ├── main_window.py      # App root: event handling, gcode pipeline, save/load
    ├── profile/            # Profile Selection tab
    ├── door/                # Door Setup tab (dimensions, hinges, lock, barrel, live preview)
    ├── generate/            # Generate Files tab
    ├── gcode_ide/           # LinuxCNC-aware G-code editor
    ├── dialogs/             # Profile/type editors, $variable reference, spreadsheet picker, etc.
    └── widgets/             # Shared/themed UI components
```

Output files are exported to `~/CNC/Output/` by default.

## License

This project is licensed under the GNU General Public License v3.0.

## Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython/) — Qt for Python
- Adapted from [cnc_frames_milling](https://github.com/maro7tigre/cnc_frames_milling)
- Developed with [Claude](https://claude.ai) (Anthropic) — some parts vibe-coded and experimented with to see what sticks, other parts precisely directed with specific instructions and close supervision over changes

---

**Note**: Always verify generated G-code before running on actual CNC equipment. The authors are not responsible for any damage resulting from the use of generated code.
