# CNC Door Wizard

A PySide6 desktop application for generating CNC G-code files for **door manufacturing**. Configure door dimensions, select hinge, lock, and barrel profiles, then generate customized right/left G-code files through an automatic two-pass variable replacement pipeline.

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.0%2B-green)

## Preview

![CNC Door Milling Preview](preview/cnc%20door%20milling.gif)

## Features

### Profile Management

- Create and manage reusable hinge, lock, and barrel profiles
- **Type-based organization**: each component has types (G-code template + L-variable definitions) and profiles (named instances with specific values)
- Define custom G-code templates with L-variable and custom-variable placeholders
- Visual profile selection with image previews and aspect-ratio-preserving scaling
- Built-in profile editor dialog with type selector, variable editor, and image picker
- Save/load portable profile sets — image paths stored relative to the profiles directory

### Door Setup

- Interactive door dimension setup (height, width, depth)
- Support for up to 10 independently activatable hinges, each with manual or auto X position
- Configure lock position (X/Z) and barrel position (X/Y) — manual or auto-calculated
- Automatic calculation of optimal component positions:
  - `hinge_x_auto` → hinge X positions distributed along door height (special-cased spacing for 1-4 hinges, even spacing for 5-10)
  - `lock_x_auto` → `door_height / 2`, `lock_z_auto` → `door_depth / 2`
  - `barrel_x_auto` follows `lock_x_position`, `barrel_y_auto` keeps/defaults the barrel Y position
  - Shared hinge Z position (`hinge_z_position`) is always set manually — no auto flag
- Support for left/right door orientations
- Real-time visual preview of door component layout
- Draggable component order widget
- **Spreadsheet import**: browse to an existing `.xlsx`/`.ods`/`.csv`/`.xls`/`.xlsm` file or create a fresh one from a built-in template (`door_height`, `door_width`, `door_depth`, `side`), pick a row from a merged/de-duplicated card list, and apply it directly to the matching `$variables`
  - Auto-created spreadsheets open immediately in an in-app spreadsheet editor (add/remove columns, drag rows/columns, per-row context menu, dedicated G/D dropdown for the `side` column)
  - Importing a value automatically disables the corresponding `*_auto` flag when one exists (e.g. importing `lock_x_position` clears `lock_x_auto` so it isn't silently overwritten by auto-calculation)
  - Auto-created spreadsheets are bundled into the project folder on save and restored on load

### G-code Editor (LinuxCNC-Aware IDE)

- **Full LinuxCNC syntax highlighting** with semantically distinct colors per code group:
  - G-codes: rapid (G0), linear (G1), arc (G2/G3), canned cycles, tool compensation, coordinate systems, modal codes
  - M-codes: stop/end, spindle, coolant, tool change, I/O, overrides, save/restore, subprogram, user M-codes
  - All 9 axes: X Y Z A B C U V W, plus arc offsets I J K and words F S T D H P Q N
  - LinuxCNC parameters: `#5`, `#<name>`, `#[expr]`
  - O-words: `o100 sub`, `call`, `if`, `while`, `repeat`, etc.
  - Math functions: `ABS`, `SIN`, `SQRT`, `EXISTS`, `ATAN`, `LN` … (cyan-teal)
  - Keyword operators: `AND`, `OR`, `MOD`, `EQ`, `LT` … (yellow)
  - Both comment styles: `(…)` and `;`
- **Template variable highlighting**: `{VAR:default}` in orange, valid `{$variable}` in green, unknown `{$variable}` in red with error background
- **Line number gutter** with red highlight for error lines; click a flagged line number to show the error tooltip
- **Current-line highlight** and **all-occurrences highlight** (select any word to see all matches)
- **`?` help button** — opens a $-variable reference dialog; click any variable to insert it at the cursor
- Auto-extraction of `{L1:default}` template variables from editor content

### G-code Generation (Two-Pass Pipeline)

1. **Pass 1** — profile G-codes (hinge, lock, barrel) are processed and injected as dollar variables: `{$hinges_gcode}`, `{$lock_gcode}`, `{$barrel_gcode}`
1. **Pass 2** — right/left door G-code templates are processed using the complete `$variable` set, including the embedded sub-G-codes from Pass 1
1. Automatic variable replacement in templates (L-variables, custom variables, $ variables)
1. Output: exactly **two files** — `right_gcode` and `left_gcode`
1. Sync-status highlighting shows when generated files are out of date relative to current settings
1. Edit output files directly in the IDE before saving to disk

### Variable System

There are two separate substitution namespaces, resolved in two different places:

- **L-variables and custom variables** live inside a **type**'s G-code template (`{L1}`, `{L2:default}`, `{feed rate:1000}`...). Whichever placeholders you type into a type's template become that type's parameter list. When you create a **profile** under that type, the app scans the template for these placeholders and gives you one input field per placeholder (pre-filled with its `:default`, if any). Each activated hinge/lock/barrel uses whichever profile is currently selected for its category, and every `{L1}` / `{feed rate:1000}` occurrence in that type's template is replaced with the value stored on that profile. L-variables (`L1`, `L2`, ...) and custom variables (any name you choose) work identically — the only difference is L-variables are meant for the component's core dimensions and custom variables for anything else (feeds, offsets, tool counts...).
- **Dollar variables** (`{$door_height}`, `{$lock_x_position}`, ...) are door-wide, not tied to any profile — one shared value per door, set in the Door Setup tab, available to every template.

| Type | Syntax | Resolved from | Description |
| --- | --- | --- | --- |
| L-variables | `{L1}`, `{L2:default}` | The active profile's stored value | Component dimension slots defined by the type's template |
| Custom variables | `{var_name:default}` | The active profile's stored value | User-named parameters defined by the type's template |
| Dollar variables | `{$door_height}` | Door Setup tab | System variables shared by every template (door dims, positions, orientation…) |
| Sub-G-code embed | `{$hinges_gcode}` | Pass 1 output | A special dollar variable: the selected hinge/lock/barrel profile's G-code, after its own L/custom variables have already been resolved |

### Project Management

- Save/load complete projects (all `$variables` + generated G-codes) as `.json`
- Auto-created import spreadsheets are copied into the project folder and referenced from the project file on save
- Auto-save current profile set on every change (`profiles/current.json`)
- Save/load named profile set snapshots independently of projects
- Window geometry and tab state persisted between sessions

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
   - Create hinge, lock, and barrel types with G-code templates and L-variable definitions
   - Create profiles under each type with specific L-variable and custom-variable values
   - Select one active profile per component category
   - At least one profile must be selected before the Door Setup tab enables

1. **Door Setup tab**
   - Enter door dimensions (height, width, depth) manually, or import them from a spreadsheet (Browse an existing file or Create a new one, then Pick Row)
   - Enable/disable individual hinges and set their X positions (or use auto-distribution)
   - Configure lock and barrel positions — manual or auto-calculated
   - Choose left/right orientation
   - Edit the right and left G-code templates in the IDE; embed component G-code blocks via `{$hinges_gcode}`, `{$lock_gcode}`, `{$barrel_gcode}`

1. **Generate Files tab**
   - Review the processed right/left G-code output with full syntax highlighting
   - Edit directly if needed; sync indicator shows stale state
   - Export both files to `~/CNC/Output/` (or a custom directory)

### Key Dollar Variables

```text
door_height, door_width, door_depth
machine_x_offset, machine_y_offset, machine_z_offset
hinge_z_position, hinge_x_auto
hinge{1-10}_active, hinge{1-10}_x_position
lock_active, lock_x_position, lock_x_auto, lock_z_position, lock_z_auto
barrel_active, barrel_x_position, barrel_x_auto, barrel_y_position, barrel_y_auto
orientation
hinges_gcode, lock_gcode, barrel_gcode   <- injected by Pass 1, embed with {$...}
```

## Example G-code Templates (LinuxCNC)

`examples/linuxcnc/` contains a working set of starter templates for a LinuxCNC-based door router, meant as a reference for how the type/profile G-code and the `{$...}`/`{L1:default}` placeholders fit together in practice:

```text
examples/linuxcnc/
├── Right Door G-Code.gcode   # top-level template — repeat/if block over hinge, lock, barrel order + tool-change subroutines
├── Left Door G-Code.gcode    # mirrored version (opposite X sign)
├── Hinge_concealed.gcode     # hinge type template
├── Hinge_entrance.gcode      # hinge type template (alternate style)
├── Lock_normal.gcode         # lock type template
└── images/                   # matching profile preview thumbnails
```

> [!WARNING]
> These files are shared purely as a starting point, not a plug-and-play solution. They were written for one specific machine and encode choices that are almost certainly wrong for yours: tool numbers (`T21`, `T22`, `T1`), spindle motor selects (`M3/M5 $0`, `$1`, `$2`), spindle speeds, feed rates, work offset (`G55`), and axis-sign/travel assumptions. Read through every line, cross-check it against your own tool table, spindle wiring, and machine limits, and confirm the resulting toolpath (dry run / air cut) before it ever touches material. You are responsible for verifying and adapting this code for your own machine — see the note at the bottom of this README.

## parameter_images — Context-Sensitive Parameter Previews

Drop image files into the `parameter_images/` directory named after any `$variable`.
When a parameter field in the Door Setup tab receives focus, the app automatically looks
up `parameter_images/<variable_name>.png` (or `.jpg` / `.jpeg`) and displays it in the
preview panel. If no image exists for that variable the panel shows "No preview".

```text
parameter_images/
├── door_height.png         # shown when the door height field is focused
├── door_width.png
├── door_depth.png
├── hinge1_x_position.png
├── lock_x_position.png
├── lock_z_position.png
├── barrel_x_position.png
├── barrel_y_position.png
└── <any_dollar_variable>.png   # add more to cover any $ variable
```

## Directory Structure

```text
cnc_doors_milling/
├── main.py
├── theme_manager.py
│
├── examples/
│   └── linuxcnc/           # Starter G-code templates for LinuxCNC (see below — adapt before use)
│
├── parameter_images/       # Context-sensitive parameter preview images (see above)
│
├── profiles/
│   ├── current.json        # Auto-saved active profile set (updated on every change)
│   ├── saved/              # Named profile set snapshots saved by the user
│   └── images/             # Profile and type preview images
│
├── projects/               # Full project saves ($ variables + generated G-codes)
│
├── preview/                # App screenshots / demo media
│
├── themes/
│   ├── dark/               # dark_colors.json, dark_theme.qss, control_styles.json, graph_styles.json
│   ├── light/              # light_colors.json, light_theme.qss, ...
│   └── purple/             # purple_colors.json, purple_theme.qss, ... (default)
│
└── ui/
    ├── main_window.py          # App root: EventManager, gcode pipeline, save/load
    ├── profile/
    │   ├── profile_tab.py      # Profile Selection tab
    │   └── widgets/
    │       ├── profile_grid.py     # Grid of profile cards per component category
    │       ├── profile_item.py     # Single profile card with image preview
    │       ├── type_item.py        # Single type card
    │       └── type_selector.py    # Type picker used inside the profile editor
    ├── door/
    │   ├── setup_tab.py        # Door Setup tab (dimensions, hinges, lock, barrel)
    │   └── widgets/
    │       ├── frame_preview.py    # Real-time door layout visual preview
    │       ├── order_widget.py     # Draggable component order widget
    │       └── draggable_list.py   # Generic draggable list base
    ├── generate/
    │   ├── generate_tab.py     # Generate Files tab
    │   └── widgets/
    │       └── generated_file_item.py  # Right/left G-code output panels with sync status
    ├── gcode_ide/
    │   └── gcode_editor.py     # LinuxCNC-aware editor (syntax highlight, line numbers, help btn)
    ├── dialogs/
    │   ├── profile_editor.py       # New/edit profile dialog
    │   ├── type_editor.py          # New/edit type dialog (G-code template + L-variable defs)
    │   ├── gcode_dialog.py         # Standalone G-code viewer/editor dialog
    │   ├── dollar_variables_dialog.py  # $ variable reference dialog (click to insert)
    │   ├── preview_dialog.py       # Full-size image preview dialog
    │   └── spreadsheet_picker_dialog.py  # Pick/edit rows from an imported spreadsheet
    └── widgets/
        ├── themed_widgets.py           # Themed buttons, labels, inputs, splitters
        ├── simple_widgets.py           # ClickableLabel, ScaledPreviewLabel, ErrorLineEdit
        ├── variable_editor.py          # L-variable editor table
        ├── custom_editor.py            # Custom-variable editor
        └── dollar_variable_widgets.py  # $ variable display/edit widgets
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
