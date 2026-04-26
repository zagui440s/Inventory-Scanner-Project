import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "donor_snapshots")

SCAN_LOG = os.path.join(DATA_DIR, "scan_log.csv")
ITEMS_FILE = os.path.join(DATA_DIR, "items.csv")
ROOM_FILE = os.path.join(DATA_DIR, "room_inventory.csv")
MASTER_FILE = os.path.join(DATA_DIR, "master_inventory.csv")
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
SESSIONS_FILE = os.path.join(DATA_DIR, "user_sessions.csv")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.csv")
FLAGGED_FILE = os.path.join(DATA_DIR, "flagged_scans.csv")
OFFLINE_QUEUE_FILE = os.path.join(DATA_DIR, "offline_queue.csv")
LOCATIONS_FILE = os.path.join(DATA_DIR, "locations.csv")
TRANSFERS_FILE = os.path.join(DATA_DIR, "transfers.csv")

BUILDINGS = ["1", "2", "3", "4"]

INACTIVITY_WARNING = 25 * 60
INACTIVITY_TIMEOUT = 30 * 60
DUPLICATE_WINDOW = 4

LOCK_ENABLED = True

DOCK_HALL = "Echo"
DOCK_CODE = "DOCK"

FIXED_SUBROOMS = ["103", "127", "BH"]