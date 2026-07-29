# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running and Building

```bash
# Run new modular version (src/ layout)
cd src && python -m or_solver.app      # or from project root:
python main.py

# Syntax check
python -m py_compile src/or_solver/app.py
python -m py_compile main.py

# Install dependencies
pip install scipy matplotlib pulp numpy

# Run tests (requires pytest)
pip install pytest
python -m pytest tests/

# Package as standalone exe
pip install pyinstaller
pyinstaller --onefile --windowed --name "运筹学模型求解工具" --paths src main.py
# Output: dist\运筹学模型求解工具.exe
```

## Architecture

The project has been refactored from a single monolithic file into a layered `src/` package structure.

**Entry point**: `main.py` → `src/or_solver/app.py` (`App(tk.Tk)`)

**Package layout** (`src/or_solver/`):
```
constants.py          — colors, fonts, BIG_M, xname(), SUBSCRIPTS
app.py                — App(tk.Tk): page lifecycle, open_solver(name) dispatch
core/                 — pure algorithm modules (zero tkinter dependency)
  lp_solver.py        — solve_lp(), solve_integer_lp(), simplex_steps()
  transport_solver.py — solve_transport(), solve_assignment(), parse_cost()
  decision_solver.py  — solve_maximin/maximax/regret/expected_value/hurwicz/laplace()
  network_solver.py   — dijkstra()
  scheduling_solver.py— solve_shift_schedule()
  forecast_solver.py  — moving_average(), exponential_smoothing(), linear_regression()
io/
  autosave.py         — save(name, data), load(name), save_to_path(), load_from_path()
  clipboard.py        — parse_tsv(), detect_headers(), extract_data_block()
utils/
  expr_parser.py      — normalize_expr(), parse_polynomial(), parse_lp_expr()
ui/
  mixins.py           — TableEditMixin (drag-select, Ctrl+C/X/Delete)
  widgets.py          — make_button() / make_btn alias
  charts.py           — draw_bar_chart(), embed_figure()
  pages/
    home.py           — HomePage (animated splash)
    menu.py           — MenuPage (navigation grid)
    lp.py             — LPPage (LP + integer + sensitivity + chart)
    transport.py      — TransportPage (transport/assignment + LP result table)
    decision.py       — DecisionPage (6 criteria + guide panel)
    network.py        — ShortestPathPage (Dijkstra)
    scheduling.py     — SchedulingPage (cyclic LP)
    forecast.py       — ForecastPage (moving avg / exp smoothing / regression)
```

**App controller** (`app.py`): `open_solver(name)` maps Chinese menu strings to page constructors. Each call to `_show(frame)` destroys the previous frame and packs the new one.

**TableEditMixin** (`ui/mixins.py`): Mixed into all table pages via multiple inheritance. Provides drag-select, Ctrl+C/X/Delete for multi-cell ranges. Each page must implement:
- `_entry_at(r, c)` → `tk.Entry` at logical (r,c), or None
- `_entry_default_bg(r, c)` → original background color
- `_all_entries()` → generator of `(r, c, entry)` tuples
- `_entry_frame()` → parent frame for clipboard and `winfo_containing`
- Call `_tbl_init_sel()` at table rebuild time

## Coordinate Systems by Page

**LPPage**: row 0 = objective coefficients (`obj_entries[j]`), rows 1..m = constraint rows (`con_entries[i][j]`), last column = RHS (`rhs_entries[i]`).

**TransportPage**: `(i, j)` = cost cell, `(i, n)` = supply entry for row i, `(m, j)` = demand entry for col j. Mode "指派" has no supply/demand row.

**DecisionPage**: row 0 = state probabilities, rows 1..m = payoff matrix rows.

**ShortestPathPage**: `(i, j)` = distance entry, diagonal cells are skipped.

**SchedulingPage**: col 0 = period name entries, col 1 = requirement entries.

## Key Patterns

**Table lifecycle**: Pages have a two-phase setup — header built in `__init__`, then `_build_table()` called on 确定. Rebuilding destroys and recreates all entry widgets; always call `_tbl_init_sel()` after rebuild.

**Autosave**: `io/autosave.py` saves to `autosave_<name>.json` at project root. LPPage auto-saves on solve; SchedulingPage saves on solve. Load via 恢复历史 button.

**Core result dataclasses**: All solver functions return `@dataclass` results (`LPResult`, `TransportResult`, etc.) with no tkinter dependency. UI pages import from `core/` and display results.

**Transport solver**: Auto-balances supply/demand by adding a dummy row or column of zeros. Costs support "M"/"m" as big-M (1e7) for forbidden routes via `parse_cost()`.

**LP sensitivity analysis**: `solve_lp()` returns `c_lower/c_upper/c_diff` (objective coefficient ranges via basis matrix method) and `b_lower/b_upper` (RHS ranges via binary search perturbation).

**Clipboard paste** (`_paste_from_clipboard` in TransportPage): Parses TSV from clipboard. If pasted block covers full table (start at 0,0) and dimensions differ, auto-resizes by updating spinboxes and calling `_build_table()`. Detects and strips Excel-style row/column headers.

**Matplotlib charts**: Embedded using `FigureCanvasTkAgg`. Charts are recreated on each solve by destroying chart_frame children. 2-variable LP shows feasible region; n>2 shows sensitivity range bars.
