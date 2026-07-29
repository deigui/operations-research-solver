import tkinter as tk

import pytest

from or_solver.ui.pages.decision import DecisionPage
from or_solver.ui.pages.lp import LPPage
from or_solver.ui.pages.network import ShortestPathPage
from or_solver.ui.pages.scheduling import SchedulingPage
from or_solver.ui.pages.transport import TransportPage


class _Controller:
    def show_home(self):
        pass

    def quit_app(self):
        pass


def _root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()
    return root


def test_transport_paste_full_table_with_headers_and_forbidden_cost():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    root.update_idletasks()

    page.body.clipboard_clear()
    page.body.clipboard_append(
        "\t销地1\t销地2\t产量\n"
        "产地1\t2\tM\t30\n"
        "产地2\t4\t5\t40\n"
        "销量\t20\t50\t\n"
    )
    event = type("E", (), {"widget": page.cost_entries[0][0]})()

    assert page._paste_from_clipboard(event, 0, 0, "cost") == "break"
    assert page.n_src.get() == 2
    assert page.n_dst.get() == 2
    assert page.cost_entries[0][0].get() == "2"
    assert page.cost_entries[0][1].get() == "M"
    assert page.supply_entries[1].get() == "40"
    assert page.demand_entries[1].get() == "50"

    root.destroy()


def test_transport_paste_space_separated_cost_matrix_resizes_without_supply_column():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    root.update_idletasks()

    page.body.clipboard_clear()
    page.body.clipboard_append("1 2 3\n4 5 6")
    event = type("E", (), {"widget": page.cost_entries[0][0]})()

    assert page._paste_from_clipboard(event, 0, 0, "cost") == "break"
    assert page.n_src.get() == 2
    assert page.n_dst.get() == 3
    assert page.cost_entries[1][2].get() == "6"
    assert page.supply_entries[0].get() == ""

    root.destroy()


def test_transport_paste_cost_rows_with_supply_column_keeps_current_destinations():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    root.update_idletasks()

    page.body.clipboard_clear()
    page.body.clipboard_append(
        "1800 1700 1550 3500\n"
        "1600 1500 1750 2500"
    )
    event = type("E", (), {"widget": page.cost_entries[0][0]})()

    assert page._paste_from_clipboard(event, 0, 0, "cost") == "break"
    assert page.n_src.get() == 2
    assert page.n_dst.get() == 3
    assert page.cost_entries[0][2].get() == "1550"
    assert page.supply_entries[0].get() == "3500"
    assert page.supply_entries[1].get() == "2500"

    root.destroy()


def test_transport_paste_single_space_separated_demand_row():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    root.update_idletasks()

    event = type("E", (), {"widget": page.demand_entries[0]})()
    page.body.clipboard_clear()
    page.body.clipboard_append("3000 1000 2000")

    assert page._paste_from_clipboard(event, 0, 0, "demand") == "break"
    assert [e.get() for e in page.demand_entries] == ["3000", "1000", "2000"]

    root.destroy()


def test_transport_paste_labeled_demand_row():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    root.update_idletasks()

    event = type("E", (), {"widget": page.demand_entries[0]})()
    page.body.clipboard_clear()
    page.body.clipboard_append("销量: 3000 1000 2000")

    assert page._paste_from_clipboard(event, 0, 0, "demand") == "break"
    assert [e.get() for e in page.demand_entries] == ["3000", "1000", "2000"]

    root.destroy()


def test_transport_supply_exceeds_adds_dummy_destination_to_visible_table():
    root = _root()
    page = TransportPage(root, _Controller(), "产大于销")
    page.n_src.set(2)
    page.n_dst.set(3)
    page._build_table()
    for i, row in enumerate(([1800, 1700, 1550], [1600, 1500, 1750])):
        for j, value in enumerate(row):
            page.cost_entries[i][j].insert(0, str(value))
    for entry, value in zip(page.supply_entries, [3500, 2500]):
        entry.insert(0, str(value))
    for entry, value in zip(page.demand_entries, [2500, 1000, 2000]):
        entry.insert(0, str(value))

    page._solve()

    assert page.n_dst.get() == 4
    assert [page.cost_entries[i][3].get() for i in range(2)] == ["0", "0"]
    assert page.demand_entries[3].get() == "500"
    assert "虚拟销地" in page.result_text.get("1.0", "end")
    assert "8800000" in page.result_text.get("1.0", "end")

    root.destroy()


def test_assignment_column_headers_are_numbered_tasks():
    root = _root()
    page = TransportPage(root, _Controller(), "指派")
    page.n_src.set(3)
    page._build_table()
    root.update_idletasks()

    labels = [
        child.cget("text")
        for child in page.cost_entries[0][0].master.winfo_children()
        if isinstance(child, tk.Label)
    ]

    assert "任务1" in labels
    assert "任务2" in labels
    assert "任务3" in labels
    assert labels.count("任务") == 0

    root.destroy()


def test_single_cell_backspace_keeps_entry_default_behavior():
    root = _root()
    page = SchedulingPage(root, _Controller())
    page._build_table()
    entry = page.need_entries[0]
    entry.insert(0, "123")
    page._sel_click(0, 1, False)

    assert page._delete_selected(type("E", (), {"widget": entry})()) is None
    assert entry.get() == "123"

    root.destroy()


def test_lp_delete_constraint_row_and_variable_column_preserves_remaining_data():
    root = _root()
    page = LPPage(root, _Controller(), "线性规划问题")
    page.n_vars.set(3)
    page.n_cons.set(2)
    page._build_table()
    page.obj_entries[0].insert(0, "1")
    page.obj_entries[1].insert(0, "2")
    page.obj_entries[2].insert(0, "3")
    page.con_entries[0][0].insert(0, "4")
    page.con_entries[1][2].insert(0, "5")
    page.rhs_entries[0].insert(0, "6")
    page.rhs_entries[1].insert(0, "7")

    page._sel_click(1, 0, False)
    page._delete_selected_row()
    assert page.n_cons.get() == 1
    assert page.con_entries[0][2].get() == "5"
    assert page.rhs_entries[0].get() == "7"

    page._sel_click(0, 1, False)
    page._delete_selected_col()
    assert page.n_vars.get() == 2
    assert [e.get() for e in page.obj_entries] == ["1", "3"]

    root.destroy()


def test_lp_insert_constraint_row_and_variable_column_preserves_remaining_data():
    root = _root()
    page = LPPage(root, _Controller(), "线性规划问题")
    page.n_vars.set(2)
    page.n_cons.set(2)
    page._build_table()
    page.obj_entries[0].insert(0, "1")
    page.obj_entries[1].insert(0, "2")
    page.con_entries[0][0].insert(0, "3")
    page.con_entries[1][1].insert(0, "4")

    page._sel_click(1, 0, False)
    page._insert_selected_row()
    assert page.n_cons.get() == 3
    assert page.con_entries[0][0].get() == "3"
    assert page.con_entries[1][0].get() == ""
    assert page.con_entries[2][1].get() == "4"

    page._sel_click(0, 0, False)
    page._insert_selected_col()
    assert page.n_vars.get() == 3
    assert [e.get() for e in page.obj_entries] == ["1", "", "2"]

    root.destroy()


def test_transport_delete_source_row_and_destination_column():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    page.cost_entries[0][0].insert(0, "1")
    page.cost_entries[1][1].insert(0, "2")
    page.supply_entries[0].insert(0, "10")
    page.supply_entries[1].insert(0, "20")
    page.demand_entries[0].insert(0, "30")
    page.demand_entries[1].insert(0, "40")

    page._sel_click(0, 0, False)
    page._delete_selected_col()
    assert page.n_dst.get() == 2
    assert page.demand_entries[0].get() == "40"

    page._sel_click(0, 0, False)
    page._delete_selected_row()
    assert page.n_src.get() == 2
    assert page.supply_entries[0].get() == "20"

    root.destroy()


def test_transport_insert_source_row_and_destination_column():
    root = _root()
    page = TransportPage(root, _Controller(), "平衡")
    page._build_table()
    page.cost_entries[0][0].insert(0, "1")
    page.cost_entries[1][1].insert(0, "2")
    page.supply_entries[1].insert(0, "20")
    page.demand_entries[1].insert(0, "40")

    page._sel_click(0, 0, False)
    page._insert_selected_row()
    assert page.n_src.get() == 4
    assert page.cost_entries[0][0].get() == "1"
    assert page.cost_entries[2][1].get() == "2"
    assert page.supply_entries[2].get() == "20"

    page._sel_click(0, 0, False)
    page._insert_selected_col()
    assert page.n_dst.get() == 4
    assert page.cost_entries[0][0].get() == "1"
    assert page.cost_entries[2][2].get() == "2"
    assert page.demand_entries[2].get() == "40"

    root.destroy()


def test_decision_delete_alternative_row_and_state_column():
    root = _root()
    page = DecisionPage(root, _Controller(), "期望值准则")
    page.mat_entries[0][0].insert(0, "1")
    page.mat_entries[1][1].insert(0, "2")
    page.prob_entries[1].delete(0, "end")
    page.prob_entries[1].insert(0, "0.5")

    page._sel_click(1, 0, False)
    page._delete_selected_row()
    assert page.n_alt.get() == 2
    assert page.mat_entries[0][1].get() == "2"

    page._sel_click(0, 1, False)
    page._delete_selected_col()
    assert page.n_state.get() == 2
    assert len(page.prob_entries) == 2

    root.destroy()


def test_decision_insert_alternative_row_and_state_column():
    root = _root()
    page = DecisionPage(root, _Controller(), "期望值准则")
    page.mat_entries[0][0].insert(0, "1")
    page.mat_entries[1][1].insert(0, "2")

    page._sel_click(1, 0, False)
    page._insert_selected_row()
    assert page.n_alt.get() == 4
    assert page.mat_entries[0][0].get() == "1"
    assert page.mat_entries[1][0].get() == ""
    assert page.mat_entries[2][1].get() == "2"

    page._sel_click(0, 0, False)
    page._insert_selected_col()
    assert page.n_state.get() == 4
    assert page.mat_entries[0][0].get() == "1"
    assert page.mat_entries[2][2].get() == "2"

    root.destroy()


def test_network_delete_node_removes_matching_row_and_column():
    root = _root()
    page = ShortestPathPage(root, _Controller())
    page._build_table()
    page.dist_entries[0][1].insert(0, "12")
    page.dist_entries[2][3].insert(0, "34")

    page._sel_click(1, 0, False)
    page._delete_selected_node()
    assert page.n_nodes.get() == 4
    assert page.dist_entries[1][2].get() == "34"

    root.destroy()


def test_network_insert_node_adds_matching_row_and_column():
    root = _root()
    page = ShortestPathPage(root, _Controller())
    page._build_table()
    page.dist_entries[0][1].insert(0, "12")
    page.dist_entries[2][3].insert(0, "34")

    page._sel_click(0, 1, False)
    page._insert_selected_node()
    assert page.n_nodes.get() == 6
    assert page.dist_entries[0][2].get() == "12"
    assert page.dist_entries[3][4].get() == "34"

    root.destroy()


def test_scheduling_delete_period_row():
    root = _root()
    page = SchedulingPage(root, _Controller())
    page._build_table()
    page.period_entries[1].delete(0, "end")
    page.period_entries[1].insert(0, "夜班")
    page.need_entries[1].insert(0, "8")

    page._sel_click(0, 0, False)
    page._delete_selected_row()
    assert page.n_periods.get() == 6
    assert page.period_entries[0].get() == "夜班"
    assert page.need_entries[0].get() == "8"

    root.destroy()


def test_scheduling_insert_period_row():
    root = _root()
    page = SchedulingPage(root, _Controller())
    page._build_table()
    page.period_entries[1].delete(0, "end")
    page.period_entries[1].insert(0, "夜班")
    page.need_entries[1].insert(0, "8")

    page._sel_click(0, 0, False)
    page._insert_selected_row()
    assert page.n_periods.get() == 8
    assert page.period_entries[1].get() == "时段2"
    assert page.period_entries[2].get() == "夜班"
    assert page.need_entries[2].get() == "8"

    root.destroy()
