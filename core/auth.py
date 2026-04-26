import csv
import uuid
import bcrypt
from datetime import datetime
from config.settings import USERS_FILE, SESSIONS_FILE, BUILDINGS


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def get_user(username):
    with open(USERS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["username"].lower() == username.lower():
                return row
    return None


def create_user(created_by_role, created_by_building):
    print("\n--- CREATE NEW USER ---")
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    username = input("Username: ").strip()

    if get_user(username):
        print("Username already exists.")
        return

    password = input("Password: ").strip()
    password_hash = hash_password(password)

    print("Roles: worker, admin, superadmin")
    role = input("Role: ").strip().lower()
    if role not in ["worker", "admin", "superadmin"]:
        print("Invalid role.")
        return

    if created_by_role == "admin":
        building = created_by_building
    else:
        building = input(f"Building ({'/'.join(BUILDINGS)}): ").strip()
        if building not in BUILDINGS:
            print("Invalid building.")
            return

    user_id = str(uuid.uuid4())[:8]

    with open(USERS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([user_id, username, first_name, last_name, password_hash, role, building])

    print(f"User {first_name} {last_name} ({username}) created successfully.")


def list_users(role, building):
    print("\n--- USER LIST ---")
    with open(USERS_FILE, "r") as f:
        reader = csv.DictReader(f)
        users = list(reader)

    if role == "admin":
        users = [u for u in users if u["building"] == building]

    if not users:
        print("  No users found.")
        return

    print(f"  {'USERNAME':<20} {'NAME':<25} {'ROLE':<15} {'BUILDING':<10}")
    print(f"  {'-'*70}")
    for u in users:
        name = f"{u['first_name']} {u['last_name']}"
        print(f"  {u['username']:<20} {name:<25} {u['role']:<15} {u['building']:<10}")


def login():
    print("\n--- INVENTORY SYSTEM LOGIN ---")
    max_attempts = 10

    for attempt in range(1, max_attempts + 1):
        username = input("Username: ").strip()
        password = input("Password: ").strip()

        user = get_user(username)
        if not user or not check_password(password, user["password_hash"]):
            remaining = max_attempts - attempt
            if remaining == 0:
                print("Maximum login attempts reached. Exiting.")
                return None
            print(f"Invalid username or password. {remaining} attempt(s) remaining.")
            continue

        building = input(f"Building (1-4): ").strip()
        if building not in BUILDINGS:
            print("Invalid building.")
            continue

        session_id = str(uuid.uuid4())[:12]
        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        session = {
            "session_id": session_id,
            "user_id": user["user_id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "role": user["role"],
            "building": building,
            "room": None,
            "login_time": login_time,
            "logout_time": None,
            "last_scan_time": None,
            "total_scans": 0,
            "logout_reason": None
        }

        print(f"\nWelcome, {user['first_name']} {user['last_name']}! Logged in to Building {building}.")
        return session

    return None


def lock_session(session):
    print("\n  Session locked. Enter password to resume.")
    for attempt in range(1, 4):
        password = input("  Password: ").strip()
        user = get_user(session["username"])
        if check_password(password, user["password_hash"]):
            print("  Session resumed.")
            return True
        remaining = 3 - attempt
        if remaining > 0:
            print(f"  Incorrect password. {remaining} attempt(s) remaining.")
    print("  Too many failed attempts. Logging out.")
    return False


def close_session(session, reason="USER_LOGOUT"):
    session["logout_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session["logout_reason"] = reason

    with open(SESSIONS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            session["session_id"],
            session["user_id"],
            session["username"],
            session["first_name"],
            session["last_name"],
            session["building"],
            session["room"],
            session["login_time"],
            session["logout_time"],
            session["last_scan_time"],
            session["total_scans"],
            session["logout_reason"]
        ])

    print(f"\nLogged out. Session saved. Goodbye, {session['first_name']}.")


def view_audit_log(role, building):
    print("\n--- SESSION AUDIT LOG ---")
    with open(SESSIONS_FILE, "r") as f:
        reader = csv.DictReader(f)
        sessions = list(reader)

    if role == "admin":
        sessions = [s for s in sessions if s["building"] == building]

    if not sessions:
        print("  No sessions found.")
        return

    print(f"  {'USERNAME':<20} {'NAME':<25} {'BUILDING':<10} {'LOGIN':<22} {'LOGOUT':<22} {'SCANS':<8} {'REASON'}")
    print(f"  {'-'*120}")
    for s in sessions:
        name = f"{s['first_name']} {s['last_name']}"
        print(f"  {s['username']:<20} {name:<25} {s['building']:<10} {s['login_time']:<22} {s['logout_time']:<22} {s['total_scans']:<8} {s['logout_reason']}")