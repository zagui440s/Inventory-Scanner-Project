import csv
import os
import uuid
from datetime import datetime
from collections import defaultdict
from config.settings import (
    SCAN_LOG, ITEMS_FILE, ROOM_FILE, MASTER_FILE,
    SNAPSHOTS_DIR, BUILDINGS, CATEGORIES_FILE,
    FLAGGED_FILE, OFFLINE_QUEUE_FILE, LOCATIONS_FILE,
    TRANSFERS_FILE, DOCK_HALL
)
from utils.helpers import get_active_categories, get_all_active_rooms


def get_category(item_id):
    categories = get_active_categories()
    item_lower = item_id.lower()
    for cat in categories:
        if cat in item_lower:
            return cat.upper()
    return "UNKNOWN"


def register_item(item_id, category=None):
    items = set()
    with open(ITEMS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.add(row["item_id"])
    if item_id not in items:
        cat = category if category else get_category(item_id)
        with open(ITEMS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([item_id, cat])


def is_item_active(item_id):
    stock = 0
    with open(SCAN_LOG, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("qty") or not row.get("action"):
                continue
            if row["item_id"] == item_id:
                if row["action"] == "IN":
                    stock += int(row["qty"])
                elif row["action"] == "OUT":
                    stock -= int(row["qty"])
    return stock > 0


def is_item_in_transit(item_id):
    with open(TRANSFERS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["item_id"] == item_id and row["status"] == "IN_TRANSIT":
                return True
    return False


def flag_scan(item_id, category, action, qty, room, sub_room, username, reason):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(FLAGGED_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp, item_id, category, action,
            qty, room, sub_room, username, reason,
            "pending", "", ""
        ])
    print(f"\n  Item {item_id} flagged for admin review. Reason: {reason}")


def log_transfer(item_id, category, building, from_location, destination, sub_room, username):
    transfer_id = str(uuid.uuid4())[:12]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TRANSFERS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            transfer_id, timestamp, item_id, category,
            building, from_location, destination, sub_room,
            username, "IN_TRANSIT", "", ""
        ])
    return transfer_id


def confirm_transfer(item_id, room, username):
    transfers = []
    confirmed = False
    transfer_id = None
    with open(TRANSFERS_FILE, "r") as f:
        reader = csv.DictReader(f)
        transfers = list(reader)

    for t in transfers:
        if t["item_id"] == item_id and t["status"] == "IN_TRANSIT":
            t["status"] = "RECEIVED"
            t["confirmed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            t["confirmed_by"] = username
            confirmed = True
            transfer_id = t["transfer_id"]
            break

    if confirmed:
        with open(TRANSFERS_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "transfer_id", "scanned_at", "item_id", "category",
                "building", "from_location", "destination", "sub_room",
                "username", "status", "confirmed_at", "confirmed_by"
            ])
            writer.writeheader()
            writer.writerows(transfers)

    return confirmed, transfer_id


def view_transfers(session):
    print("\n--- TRANSFER AUDIT ---")
    transfers = []
    with open(TRANSFERS_FILE, "r") as f:
        reader = csv.DictReader(f)
        transfers = list(reader)

    if session["role"] == "admin":
        transfers = [t for t in transfers if t["building"] == session["building"]]

    if not transfers:
        print("  No transfers found.")
        return

    in_transit = [t for t in transfers if t["status"] == "IN_TRANSIT"]
    received = [t for t in transfers if t["status"] == "RECEIVED"]

    print(f"\n  IN TRANSIT ({len(in_transit)}):")
    print(f"  {'ITEM':<20} {'CAT':<12} {'FROM':<12} {'DESTINATION':<12} {'BY':<15} {'TIME'}")
    print(f"  {'-'*90}")
    for t in in_transit:
        dest = t["destination"] if t["destination"] else "UNKNOWN"
        print(f"  {t['item_id']:<20} {t['category']:<12} {t['from_location']:<12} {dest:<12} {t['username']:<15} {t['scanned_at']}")

    print(f"\n  RECEIVED ({len(received)}):")
    print(f"  {'ITEM':<20} {'CAT':<12} {'FROM':<12} {'DESTINATION':<12} {'CONFIRMED BY':<15} {'CONFIRMED AT'}")
    print(f"  {'-'*90}")
    for t in received:
        dest = t["destination"] if t["destination"] else "UNKNOWN"
        print(f"  {t['item_id']:<20} {t['category']:<12} {t['from_location']:<12} {dest:<12} {t['confirmed_by']:<15} {t['confirmed_at']}")


def review_flagged_scans(session):
    print("\n--- FLAGGED SCANS ---")
    flagged = []
    with open(FLAGGED_FILE, "r") as f:
        reader = csv.DictReader(f)
        flagged = list(reader)

    pending = [f for f in flagged if f["status"] == "pending"]

    if not pending:
        print("  No pending flagged scans.")
        return

    for i, scan in enumerate(pending, 1):
        print(f"\n  {i}. Item: {scan['item_id']}")
        print(f"     Category: {scan['category']}")
        print(f"     Action: {scan['action']} | Qty: {scan['qty']}")
        print(f"     Room: {scan['room']} | Sub-room: {scan.get('sub_room', 'N/A')} | User: {scan['username']}")
        print(f"     Flagged at: {scan['flagged_at']}")
        print(f"     Reason: {scan['reason']}")

        choice = input("\n  Approve (A) / Reject (R) / Skip (S): ").strip().upper()
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if choice == "A":
            with open(SCAN_LOG, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    scan["flagged_at"], scan["item_id"], scan["category"],
                    scan["action"], scan["qty"], scan["room"],
                    scan.get("sub_room", ""), scan["username"], ""
                ])
            scan["status"] = "approved"
            scan["reviewed_by"] = session["username"]
            scan["reviewed_at"] = reviewed_at
            print(f"  Approved and added to scan log.")
        elif choice == "R":
            scan["status"] = "rejected"
            scan["reviewed_by"] = session["username"]
            scan["reviewed_at"] = reviewed_at
            print(f"  Rejected.")
        else:
            print(f"  Skipped.")

    with open(FLAGGED_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "flagged_at", "item_id", "category", "action",
            "qty", "room", "sub_room", "username", "reason",
            "status", "reviewed_by", "reviewed_at"
        ])
        writer.writeheader()
        writer.writerows(flagged)

    calculate_stock()


def review_offline_queue(session):
    print("\n--- OFFLINE QUEUE ---")
    queue = []
    with open(OFFLINE_QUEUE_FILE, "r") as f:
        reader = csv.DictReader(f)
        queue = list(reader)

    pending = [q for q in queue if q.get("status", "pending") == "pending"]

    if not pending:
        print("  No pending offline scans.")
        return

    print(f"\n  {len(pending)} offline scan(s) pending review.")
    print(f"\n  {'#':<5} {'ITEM':<20} {'CAT':<12} {'ACT':<8} {'ROOM':<15} {'SUB':<8} {'USER':<15} {'TIME'}")
    print(f"  {'-'*100}")

    for i, scan in enumerate(pending, 1):
        print(f"  {i:<5} {scan['item_id']:<20} {scan['category']:<12} {scan['action']:<8} {scan['room']:<15} {scan.get('sub_room',''):<8} {scan['username']:<15} {scan['queued_at']}")

    choice = input("\n  Approve ALL (A) / Review individually (I) / Reject ALL (R): ").strip().upper()
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if choice == "A":
        with open(SCAN_LOG, "a", newline="") as f:
            writer = csv.writer(f)
            for scan in pending:
                writer.writerow([
                    scan["queued_at"], scan["item_id"], scan["category"],
                    scan["action"], scan["qty"], scan["room"],
                    scan.get("sub_room", ""), scan["username"], ""
                ])
                scan["status"] = "approved"
                scan["reviewed_by"] = session["username"]
                scan["reviewed_at"] = reviewed_at
        print(f"  All offline scans approved and merged.")

    elif choice == "I":
        for scan in pending:
            print(f"\n  Item: {scan['item_id']} | {scan['category']} | {scan['action']} | {scan['room']} | {scan.get('sub_room','')} | {scan['queued_at']}")
            ind = input("  Approve (A) / Reject (R): ").strip().upper()
            if ind == "A":
                with open(SCAN_LOG, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        scan["queued_at"], scan["item_id"], scan["category"],
                        scan["action"], scan["qty"], scan["room"],
                        scan.get("sub_room", ""), scan["username"], ""
                    ])
                scan["status"] = "approved"
                scan["reviewed_by"] = session["username"]
                scan["reviewed_at"] = reviewed_at
                print(f"  Approved.")
            else:
                scan["status"] = "rejected"
                scan["reviewed_by"] = session["username"]
                scan["reviewed_at"] = reviewed_at
                print(f"  Rejected.")

    elif choice == "R":
        for scan in pending:
            scan["status"] = "rejected"
            scan["reviewed_by"] = session["username"]
            scan["reviewed_at"] = reviewed_at
        print(f"  All offline scans rejected.")

    with open(OFFLINE_QUEUE_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "queued_at", "item_id", "category", "action",
            "qty", "room", "sub_room", "username", "status", "reviewed_by", "reviewed_at"
        ])
        writer.writeheader()
        writer.writerows(queue)

    calculate_stock()


def calculate_stock():
    categories = get_active_categories()
    all_rooms = get_all_active_rooms()
    room_data = defaultdict(lambda: defaultdict(int))
    building_data = defaultdict(lambda: defaultdict(int))
    master_data = defaultdict(int)

    with open(SCAN_LOG, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("qty") or not row.get("room") or not row.get("action"):
                continue
            if row["action"] not in ["IN", "OUT"]:
                continue
            item = row["item_id"]
            room = row["room"]
            qty = int(row["qty"])
            action = row["action"]
            category = row.get("category") or get_category(item)
            building = room.split("-")[0]

            if action == "IN":
                room_data[room][item] += qty
                building_data[building][category.upper()] += qty
                master_data[category.upper()] += qty
            elif action == "OUT":
                room_data[room][item] -= qty
                building_data[building][category.upper()] -= qty
                master_data[category.upper()] -= qty

    with open(ROOM_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["room", "item_id", "stock"])
        for room in all_rooms:
            items_in_room = room_data.get(room, {})
            if not items_in_room:
                if "Echo" not in room:
                    writer.writerow([room, "NO ITEMS", 0])
            else:
                for item, stock in items_in_room.items():
                    writer.writerow([room, item, stock])

    with open(MASTER_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category"] + [f"building_{b}" for b in BUILDINGS] + ["master_total"])
        if not master_data:
            writer.writerow(["NO ITEMS"] + [0] * len(BUILDINGS) + [0])
        else:
            for category in categories:
                cat_upper = category.upper()
                b_totals = [building_data.get(b, {}).get(cat_upper, 0) for b in BUILDINGS]
                total = master_data.get(cat_upper, 0)
                writer.writerow([cat_upper] + b_totals + [total])


def get_room_stock(item_id, room):
    stock = 0
    with open(SCAN_LOG, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("qty") or not row.get("room") or not row.get("action"):
                continue
            if row["item_id"] == item_id and row["room"] == room:
                qty = int(row["qty"])
                if row["action"] == "IN":
                    stock += qty
                elif row["action"] == "OUT":
                    stock -= qty
    return stock


def print_inventory():
    print("\n--- ROOM INVENTORY ---")
    with open(ROOM_FILE, "r") as f:
        reader = csv.DictReader(f)
        current_room = None
        for row in reader:
            if row["room"] != current_room:
                current_room = row["room"]
                print(f"\n  {current_room}")
            if row["item_id"] == "NO ITEMS":
                print(f"    *** ZERO ITEMS IN THIS ROOM — CHECK SYSTEM ***")
            else:
                print(f"    {row['item_id']:<30} stock: {row['stock']}")

    print("\n--- MASTER INVENTORY ---")
    print(f"  {'CATEGORY':<20} {'BLDG 1':>10} {'BLDG 2':>10} {'BLDG 3':>10} {'BLDG 4':>10} {'TOTAL':>10}")
    print(f"  {'-'*70}")
    with open(MASTER_FILE, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows or (len(rows) == 1 and rows[0]["category"] == "NO ITEMS"):
            print("  *** ZERO ITEMS IN MASTER — CHECK SYSTEM ***")
        else:
            for row in rows:
                print(
                    f"  {row['category']:<20}"
                    f" {row['building_1']:>10}"
                    f" {row['building_2']:>10}"
                    f" {row['building_3']:>10}"
                    f" {row['building_4']:>10}"
                    f" {row['master_total']:>10}"
                )


def manage_categories(session):
    while True:
        print("\n--- CATEGORY MANAGEMENT ---")
        categories = []
        with open(CATEGORIES_FILE, "r") as f:
            reader = csv.DictReader(f)
            categories = list(reader)

        print(f"\n  {'#':<5} {'CATEGORY':<20} {'STATUS':<12} {'CREATED BY':<20} {'CREATED AT'}")
        print(f"  {'-'*75}")
        for i, cat in enumerate(categories, 1):
            print(f"  {i:<5} {cat['category_name']:<20} {cat['status']:<12} {cat['created_by']:<20} {cat['created_at']}")

        print("\n  1. Add new category")
        print("  2. Deactivate category")
        print("  3. Activate category")
        print("  4. Back")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            name = input("  New category name: ").strip().lower()
            if not name:
                print("  Invalid name.")
                continue
            existing = [c["category_name"].lower() for c in categories]
            if name in existing:
                print("  Category already exists.")
                continue
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(CATEGORIES_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([name, "active", session["username"], timestamp])
            print(f"  Category '{name}' added and active immediately.")

        elif choice == "2":
            name = input("  Category to deactivate: ").strip().lower()
            updated = []
            found = False
            for cat in categories:
                if cat["category_name"].lower() == name:
                    cat["status"] = "inactive"
                    found = True
                updated.append(cat)
            if not found:
                print("  Category not found.")
                continue
            with open(CATEGORIES_FILE, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["category_name", "status", "created_by", "created_at"])
                writer.writeheader()
                writer.writerows(updated)
            print(f"  Category '{name}' deactivated. Historical data preserved.")

        elif choice == "3":
            name = input("  Category to activate: ").strip().lower()
            updated = []
            found = False
            for cat in categories:
                if cat["category_name"].lower() == name:
                    cat["status"] = "active"
                    found = True
                updated.append(cat)
            if not found:
                print("  Category not found.")
                continue
            with open(CATEGORIES_FILE, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["category_name", "status", "created_by", "created_at"])
                writer.writeheader()
                writer.writerows(updated)
            print(f"  Category '{name}' activated.")

        elif choice == "4":
            break


def manage_locations(session):
    while True:
        print("\n--- LOCATION MANAGEMENT ---")
        locations = []
        with open(LOCATIONS_FILE, "r") as f:
            reader = csv.DictReader(f)
            locations = list(reader)

        if session["role"] == "admin":
            display = [l for l in locations if l["building"] == session["building"]]
        else:
            display = locations

        print(f"\n  {'#':<5} {'BUILDING':<10} {'DATA HALL':<15} {'CODE':<8} {'STATUS':<12} {'CREATED BY'}")
        print(f"  {'-'*70}")
        for i, loc in enumerate(display, 1):
            print(f"  {i:<5} {loc['building']:<10} {loc['data_hall']:<15} {loc['hall_code']:<8} {loc['status']:<12} {loc['created_by']}")

        print("\n  1. Add new data hall")
        print("  2. Deactivate data hall")
        print("  3. Activate data hall")
        print("  4. Back")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            if session["role"] == "admin":
                building = session["building"]
            else:
                building = input(f"  Building (1-4): ").strip()
                if building not in ["1", "2", "3", "4"]:
                    print("  Invalid building.")
                    continue

            hall_name = input("  Data hall name: ").strip()
            if not hall_name:
                print("  Invalid name.")
                continue

            existing = [(l["building"], l["data_hall"].lower()) for l in locations]
            if (building, hall_name.lower()) in existing:
                print("  Data hall already exists in this building.")
                continue

            hall_code = input("  Hall code (single letter or DOCK): ").strip().upper()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(LOCATIONS_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([building, hall_name, hall_code, "active", session["username"], timestamp])
            print(f"  Data hall '{hall_name}' added to Building {building}.")

        elif choice == "2":
            hall_name = input("  Data hall to deactivate: ").strip().lower()
            if session["role"] == "admin":
                building = session["building"]
            else:
                building = input("  Building: ").strip()

            updated = []
            found = False
            for loc in locations:
                if loc["data_hall"].lower() == hall_name and loc["building"] == building:
                    loc["status"] = "inactive"
                    found = True
                updated.append(loc)
            if not found:
                print("  Data hall not found.")
                continue
            with open(LOCATIONS_FILE, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["building", "data_hall", "hall_code", "status", "created_by", "created_at"])
                writer.writeheader()
                writer.writerows(updated)
            print(f"  Data hall '{hall_name}' deactivated. Historical data preserved.")

        elif choice == "3":
            hall_name = input("  Data hall to activate: ").strip().lower()
            if session["role"] == "admin":
                building = session["building"]
            else:
                building = input("  Building: ").strip()

            updated = []
            found = False
            for loc in locations:
                if loc["data_hall"].lower() == hall_name and loc["building"] == building:
                    loc["status"] = "active"
                    found = True
                updated.append(loc)
            if not found:
                print("  Data hall not found.")
                continue
            with open(LOCATIONS_FILE, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["building", "data_hall", "hall_code", "status", "created_by", "created_at"])
                writer.writeheader()
                writer.writerows(updated)
            print(f"  Data hall '{hall_name}' activated.")

        elif choice == "4":
            break


def generate_donor_snapshot(session):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(SNAPSHOTS_DIR, f"snapshot_{timestamp}.csv")

    with open(MASTER_FILE, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "generated_at", "generated_by", "category",
            "building_1", "building_2", "building_3", "building_4", "master_total"
        ])
        for row in rows:
            writer.writerow([
                timestamp,
                f"{session['first_name']} {session['last_name']}",
                row["category"],
                row.get("building_1", 0),
                row.get("building_2", 0),
                row.get("building_3", 0),
                row.get("building_4", 0),
                row["master_total"]
            ])

    print(f"\n  Snapshot saved to: {filename}")