from core.inventory import (
    print_inventory, generate_donor_snapshot,
    manage_categories, manage_locations,
    review_flagged_scans, review_offline_queue,
    view_transfers
)
from core.auth import create_user, list_users, view_audit_log, close_session
from core.scanner import run_scanner


def superadmin_menu(session):
    while True:
        print(f"\n--- SUPERADMIN MENU --- [{session['first_name']} {session['last_name']}]")
        print("  1. View master inventory")
        print("  2. Manage users")
        print("  3. Manage categories")
        print("  4. Manage locations")
        print("  5. View session audit log")
        print("  6. Review flagged scans")
        print("  7. Review offline queue")
        print("  8. View transfer audit")
        print("  9. Start scanning session")
        print("  10. Generate donor snapshot")
        print("  11. Logout")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            print_inventory()
        elif choice == "2":
            user_mgmt_menu(session)
        elif choice == "3":
            manage_categories(session)
        elif choice == "4":
            manage_locations(session)
        elif choice == "5":
            view_audit_log(session["role"], session["building"])
        elif choice == "6":
            review_flagged_scans(session)
        elif choice == "7":
            review_offline_queue(session)
        elif choice == "8":
            view_transfers(session)
        elif choice == "9":
            run_scanner(session)
            break
        elif choice == "10":
            generate_donor_snapshot(session)
        elif choice == "11":
            close_session(session, reason="USER_LOGOUT")
            break
        else:
            print("  Invalid choice.")


def admin_menu(session):
    while True:
        print(f"\n--- ADMIN MENU --- [{session['first_name']} {session['last_name']} | Building {session['building']}]")
        print("  1. View building inventory")
        print("  2. Manage users (my building)")
        print("  3. Manage categories")
        print("  4. Manage locations")
        print("  5. View session audit log")
        print("  6. Review flagged scans")
        print("  7. Review offline queue")
        print("  8. View transfer audit")
        print("  9. Start scanning session")
        print("  10. Generate donor snapshot")
        print("  11. Logout")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            print_inventory()
        elif choice == "2":
            user_mgmt_menu(session)
        elif choice == "3":
            manage_categories(session)
        elif choice == "4":
            manage_locations(session)
        elif choice == "5":
            view_audit_log(session["role"], session["building"])
        elif choice == "6":
            review_flagged_scans(session)
        elif choice == "7":
            review_offline_queue(session)
        elif choice == "8":
            view_transfers(session)
        elif choice == "9":
            run_scanner(session)
            break
        elif choice == "10":
            generate_donor_snapshot(session)
        elif choice == "11":
            close_session(session, reason="USER_LOGOUT")
            break
        else:
            print("  Invalid choice.")


def user_mgmt_menu(session):
    while True:
        print("\n--- USER MANAGEMENT ---")
        print("  1. Create new user")
        print("  2. List users")
        print("  3. Back")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            create_user(session["role"], session["building"])
        elif choice == "2":
            list_users(session["role"], session["building"])
        elif choice == "3":
            break
        else:
            print("  Invalid choice.")