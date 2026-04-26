import csv
import os
from datetime import datetime
from config.settings import (
    SCAN_LOG, ITEMS_FILE, ROOM_FILE, MASTER_FILE,
    USERS_FILE, SESSIONS_FILE, CATEGORIES_FILE,
    FLAGGED_FILE, OFFLINE_QUEUE_FILE, SNAPSHOTS_DIR,
    LOCATIONS_FILE, TRANSFERS_FILE
)


def init_files():
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

    if not os.path.exists(SCAN_LOG):
        with open(SCAN_LOG, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "item_id", "category", "action", "qty", "room", "sub_room", "username", "transfer_id"])

    if not os.path.exists(ITEMS_FILE):
        with open(ITEMS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "category"])

    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "username", "first_name", "last_name", "password_hash", "role", "building"])

    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "user_id", "username", "first_name", "last_name",
                "building", "room", "sub_room", "login_time", "logout_time",
                "last_scan_time", "total_scans", "logout_reason"
            ])

    if not os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["category_name", "status", "created_by", "created_at"])

    if not os.path.exists(FLAGGED_FILE):
        with open(FLAGGED_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "flagged_at", "item_id", "category", "action",
                "qty", "room", "sub_room", "username", "reason",
                "status", "reviewed_by", "reviewed_at"
            ])

    if not os.path.exists(OFFLINE_QUEUE_FILE):
        with open(OFFLINE_QUEUE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["queued_at", "item_id", "category", "action", "qty", "room", "sub_room", "username", "status", "reviewed_by", "reviewed_at"])

    if not os.path.exists(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["building", "data_hall", "hall_code", "status", "created_by", "created_at"])

    if not os.path.exists(TRANSFERS_FILE):
        with open(TRANSFERS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "transfer_id", "scanned_at", "item_id", "category",
                "building", "from_location", "destination", "sub_room",
                "username", "status", "confirmed_at", "confirmed_by"
            ])


def get_active_categories():
    categories = []
    with open(CATEGORIES_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"].lower() == "active":
                categories.append(row["category_name"].lower())
    return categories


def get_active_locations(building):
    locations = []
    with open(LOCATIONS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["building"] == building and row["status"].lower() == "active":
                locations.append(row)
    return locations


def get_all_active_rooms():
    rooms = []
    with open(LOCATIONS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"].lower() == "active":
                room_name = f"{row['building']}-{row['data_hall']}"
                if room_name not in rooms:
                    rooms.append(room_name)
    return rooms