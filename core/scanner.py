import csv
import threading
import time
import uuid
from datetime import datetime
from config.settings import (
    SCAN_LOG, INACTIVITY_WARNING, INACTIVITY_TIMEOUT,
    DUPLICATE_WINDOW, LOCK_ENABLED, OFFLINE_QUEUE_FILE,
    DOCK_HALL, FIXED_SUBROOMS
)
from utils.helpers import get_active_categories, get_active_locations
from core.inventory import (
    register_item, calculate_stock, get_room_stock,
    print_inventory, flag_scan, is_item_active,
    log_transfer, confirm_transfer
)
from core.auth import close_session, lock_session


def select_data_hall(building):
    locations = get_active_locations(building)
    if not locations:
        print("  No active data halls found for this building.")
        return None, None

    print(f"\n  Select Data Hall:")
    for i, loc in enumerate(locations, 1):
        print(f"  {i}. {loc['data_hall']}")
    choice = input("  Choice: ").strip()
    try:
        selected = locations[int(choice) - 1]
        return selected["data_hall"], selected["hall_code"]
    except:
        print("  Invalid choice.")
        return None, None


def select_sub_room(hall_code):
    if hall_code == "DOCK":
        print(f"\n  Enter destination (optional):")
        print(f"  1. Unknown / Skip")
        print(f"  2. Enter destination sub-room")
        choice = input("  Choice: ").strip()
        if choice == "2":
            dest = input("  Destination (e.g. A103): ").strip().upper()
            if dest and len(dest) >= 2 and dest[0].isalpha():
                return dest
        return ""

    print(f"\n  Select Sub-room:")
    options = [f"{hall_code}{sr}" for sr in FIXED_SUBROOMS]
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print(f"  {len(options) + 1}. Other")
    print(f"  {len(options) + 2}. None / Skip")

    choice = input("  Choice: ").strip()
    try:
        idx = int(choice) - 1
        if idx < len(options):
            return options[idx]
        elif idx == len(options):
            custom = input(f"  Enter sub-room (must start with {hall_code}): ").strip().upper()
            if custom.startswith(hall_code):
                return custom
            else:
                print(f"  Invalid sub-room. Must start with {hall_code}.")
                return ""
        else:
            return ""
    except:
        return ""


def select_category():
    categories = get_active_categories()
    print("\n  What are you scanning today?")
    for i, cat in enumerate(categories, 1):
        print(f"  {i}. {cat.upper()}")
    print(f"  {len(categories) + 1}. Mixed (ask per scan)")
    choice = input("  Choice: ").strip()
    try:
        idx = int(choice) - 1
        if idx == len(categories):
            return "MIXED"
        return categories[idx].upper()
    except:
        print("  Invalid choice, defaulting to MIXED.")
        return "MIXED"


def run_scanner(session):
    print(f"\n--- SELECT DATA HALL ---")
    data_hall, hall_code = select_data_hall(session["building"])
    if not data_hall:
        return

    is_dock = data_hall == DOCK_HALL

    sub_room = select_sub_room(hall_code)
    session["room"] = f"{session['building']}-{data_hall}"
    session["sub_room"] = sub_room

    session_category = select_category()

    inactivity_timer = [None]
    warning_timer = [None]
    timed_out = [False]
    last_scanned = {}
    offline_mode = [False]

    def do_timeout():
        timed_out[0] = True
        print(f"\n\n  You have been logged out due to 30 minutes of inactivity.")
        close_session(session, reason="INACTIVITY_TIMEOUT")

    def do_warning():
        print(f"\n\n  Warning: You will be logged out in 5 minutes due to inactivity.")
        warning_timer[0] = None

    def reset_timer():
        if inactivity_timer[0]:
            inactivity_timer[0].cancel()
        if warning_timer[0]:
            warning_timer[0].cancel()
        w = threading.Timer(INACTIVITY_WARNING, do_warning)
        t = threading.Timer(INACTIVITY_TIMEOUT, do_timeout)
        w.daemon = True
        t.daemon = True
        w.start()
        t.start()
        warning_timer[0] = w
        inactivity_timer[0] = t

    def cancel_timers():
        if inactivity_timer[0]:
            inactivity_timer[0].cancel()
        if warning_timer[0]:
            warning_timer[0].cancel()

    reset_timer()

    while True:
        if timed_out[0]:
            break

        mode_label = "OFFLINE" if offline_mode[0] else "ONLINE"
        sub_label = f" | Sub-room: {sub_room}" if sub_room else ""
        dock_label = " | DOCK MODE" if is_dock else ""
        print(f"\n--- INVENTORY SCAN --- [{session['first_name']} | Bldg {session['building']} | {data_hall}{sub_label}{dock_label} | {mode_label}]")
        print(f"  Category: {session_category}")
        print(f"  Commands: ROOM, SUBROOM, CATEGORY, LOCK, OFFLINE, ONLINE, EXIT")
        if is_dock:
            print(f"  Dock mode — items will be logged as IN_TRANSIT only")

        item = input("\nScan Item: ").strip()

        if timed_out[0]:
            break

        if item.lower() == "exit":
            cancel_timers()
            close_session(session, reason="USER_LOGOUT")
            break

        if item.upper() == "LOCK":
            if LOCK_ENABLED:
                cancel_timers()
                resumed = lock_session(session)
                if not resumed:
                    close_session(session, reason="LOCK_FAILED")
                    break
                reset_timer()
            else:
                print("  Lock is disabled.")
            continue

        if item.upper() == "OFFLINE":
            offline_mode[0] = True
            print("  Switched to OFFLINE mode. Scans will be queued for admin approval.")
            reset_timer()
            continue

        if item.upper() == "ONLINE":
            offline_mode[0] = False
            print("  Switched to ONLINE mode.")
            reset_timer()
            continue

        if item.upper() == "ROOM":
            data_hall, hall_code = select_data_hall(session["building"])
            if data_hall:
                is_dock = data_hall == DOCK_HALL
                sub_room = select_sub_room(hall_code)
                session["room"] = f"{session['building']}-{data_hall}"
                session["sub_room"] = sub_room
                print(f"  Location changed to {data_hall} {sub_room}")
            reset_timer()
            continue

        if item.upper() == "SUBROOM":
            sub_room = select_sub_room(hall_code)
            session["sub_room"] = sub_room
            print(f"  Sub-room changed to {sub_room if sub_room else 'None'}")
            reset_timer()
            continue

        if item.upper() == "CATEGORY":
            session_category = select_category()
            reset_timer()
            continue

        # 4 second duplicate check
        now = time.time()
        if item in last_scanned:
            elapsed = now - last_scanned[item]
            if elapsed < DUPLICATE_WINDOW:
                print(f"  Duplicate scan detected within {DUPLICATE_WINDOW} seconds. Ignored.")
                reset_timer()
                continue
        last_scanned[item] = now

        if session_category == "MIXED":
            categories = get_active_categories()
            print("  Select category for this item:")
            for i, cat in enumerate(categories, 1):
                print(f"  {i}. {cat.upper()}")
            choice = input("  Choice: ").strip()
            try:
                item_category = categories[int(choice) - 1].upper()
            except:
                print("  Invalid choice.")
                reset_timer()
                continue
        else:
            item_category = session_category

        room = f"{session['building']}-{data_hall}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---- DOCK MODE — no IN/OUT prompt, no scan_log write ----
        if is_dock:
            register_item(item, item_category)
            transfer_id = log_transfer(
                item, item_category, session["building"],
                "Echo", sub_room, sub_room, session["username"]
            )
            if offline_mode[0]:
                with open(OFFLINE_QUEUE_FILE, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, item, item_category, "TRANSIT", 1, room, sub_room, session["username"], "pending", "", ""])
                print(f"  Queued (offline): TRANSIT {item} ({item_category}) → {sub_room if sub_room else 'UNKNOWN'}")
            else:
                session["last_scan_time"] = timestamp
                session["total_scans"] += 1
                print(f"\n  Transfer logged: {item} ({item_category}) → {sub_room if sub_room else 'UNKNOWN'} | Status: IN_TRANSIT")
            reset_timer()
            continue

        # ---- ROOM MODE — normal IN/OUT flow ----
        action = input("IN / OUT: ").strip().upper()
        if action not in ["IN", "OUT"]:
            print("  Invalid action.")
            reset_timer()
            continue

        qty = 1

        # duplicate serial check only for IN scans in room mode
        if action == "IN" and is_item_active(item):
            # check if its an incoming transfer first
            confirmed, transfer_id = confirm_transfer(item, room, session["username"])
            if confirmed:
                print(f"  Transfer confirmed. Item received at {room} {sub_room}")
                with open(SCAN_LOG, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, item, item_category, "IN", qty, room, sub_room, session["username"], transfer_id])
                session["last_scan_time"] = timestamp
                session["total_scans"] += 1
                calculate_stock()
                print_inventory()
                print(f"\n  Logged IN {item} ({item_category}) | {room} {sub_room}")
                reset_timer()
                continue
            else:
                flag_scan(item, item_category, action, qty, room, sub_room, session["username"], "DUPLICATE_SERIAL")
                reset_timer()
                continue

        register_item(item, item_category)

        if action == "OUT":
            current = get_room_stock(item, room)
            if qty > current:
                print(f"  Not enough stock in {room}. Current: {current}")
                reset_timer()
                continue

        transfer_id = ""
        if action == "IN":
            confirmed, transfer_id = confirm_transfer(item, room, session["username"])
            if confirmed:
                print(f"  Transfer confirmed. Item received at {room} {sub_room}")
            transfer_id = transfer_id or ""

        if offline_mode[0]:
            with open(OFFLINE_QUEUE_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, item, item_category, action, qty, room, sub_room, session["username"], "pending", "", ""])
            print(f"  Queued (offline): {action} {item} ({item_category}) in {room} {sub_room}")
        else:
            with open(SCAN_LOG, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, item, item_category, action, qty, room, sub_room, session["username"], transfer_id])
            session["last_scan_time"] = timestamp
            session["total_scans"] += 1
            calculate_stock()
            print_inventory()
            print(f"\n  Logged {action} {item} ({item_category}) | {room} {sub_room}")

        reset_timer()