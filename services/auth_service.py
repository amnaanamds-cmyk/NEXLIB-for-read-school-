"""
services/auth_service.py
Fully local authentication. Staff accounts (username + password) are stored
in the local SQLite database, hashed with PBKDF2-HMAC-SHA256. No network
calls, no cloud accounts — everything works fully offline.
"""
import hashlib
import os
import binascii
import time
from typing import Optional, Tuple

from models.reservation import User

PBKDF2_ITERATIONS = 200_000


class AuthService:
    def __init__(self, db_helper):
        self.db = db_helper
        self._current_user: Optional[User] = None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        return self._current_user is not None

    @property
    def role(self) -> str:
        return self._current_user.role if self._current_user else ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_librarian(self) -> bool:
        return self.role in ("admin", "librarian")

    def can_manage_books(self) -> bool:
        return self.role in ("admin", "librarian")

    def can_manage_members(self) -> bool:
        return self.role in ("admin", "librarian")

    def can_access_settings(self) -> bool:
        return self.role == "admin"

    def can_view_reports(self) -> bool:
        return self.role in ("admin", "librarian")

    def can_manage_staff(self) -> bool:
        return self.role == "admin"

    # ── Password Hashing ─────────────────────────────────────────────────────
    @staticmethod
    def _hash_password(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
        """Returns (salt_hex, hash_hex)."""
        salt = binascii.unhexlify(salt_hex) if salt_hex else os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return binascii.hexlify(salt).decode(), binascii.hexlify(pwd_hash).decode()

    # ── Account Setup ────────────────────────────────────────────────────────
    def has_any_accounts(self) -> bool:
        return self.db.count_users() > 0

    def create_account(self, username: str, password: str, name: str, role: str) -> Tuple[bool, str]:
        username = username.strip().lower()
        if not username or not password:
            return False, "Username and password are required."
        if len(password) < 4:
            return False, "Password must be at least 4 characters."
        if self.db.get_user_by_username(username):
            return False, "That username is already taken."
        salt_hex, hash_hex = self._hash_password(password)
        self.db.create_user(username, hash_hex, salt_hex, name.strip() or username, role)
        return True, ""

    def change_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        if len(new_password) < 4:
            return False, "Password must be at least 4 characters."
        salt_hex, hash_hex = self._hash_password(new_password)
        self.db.update_user_password(user_id, hash_hex, salt_hex)
        return True, ""

    # ── Sign In / Out ─────────────────────────────────────────────────────────
    def sign_in(self, username: str, password: str) -> Tuple[bool, str]:
        username = username.strip().lower()
        row = self.db.get_user_by_username(username)
        if not row:
            return False, "Invalid username or password."
        _, hash_hex = self._hash_password(password, row["salt"])
        if hash_hex != row["password_hash"]:
            return False, "Invalid username or password."

        self._current_user = User(
            uid=str(row["id"]), email=row["username"],
            name=row["name"] or row["username"], role=row["role"],
        )
        return True, ""

    def sign_out(self):
        self._current_user = None
