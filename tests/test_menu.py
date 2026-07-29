from or_solver.ui.pages.menu import MenuPage
from or_solver.app import App


def test_all_menu_items_are_implemented():
    all_items = set().union(*MenuPage.MENU.values())

    assert MenuPage.IMPLEMENTED == all_items


def test_all_implemented_menu_items_have_page_factories():
    app = App.__new__(App)
    all_items = set().union(*MenuPage.MENU.values())

    missing = [item for item in sorted(all_items) if app._solver_page(item, object(), object()) is None]

    assert missing == []
