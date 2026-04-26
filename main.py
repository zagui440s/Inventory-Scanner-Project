from utils.helpers import init_files
from core.inventory import calculate_stock, print_inventory
from core.auth import login
from core.menus import superadmin_menu, admin_menu
from core.scanner import run_scanner


def main():
    init_files()
    calculate_stock()

    session = login()
    if not session:
        print("Login failed. Exiting.")
        return

    role = session["role"]

    if role == "superadmin":
        superadmin_menu(session)
    elif role == "admin":
        admin_menu(session)
    elif role == "worker":
        run_scanner(session)


if __name__ == "__main__":
    main()