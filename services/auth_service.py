"""
services/auth_service.py
Firebase Authentication using REST API (firebase-admin doesn't support client auth).
Roles are stored in Firestore users collection.
"Remember Me" uses Windows Credential Manager via keyring.
"""
import json
import time
import requests
import keyring
from typing import Optional, Tuple

import config
from models.reservation import User


KEYRING_SERVICE = config.KEYRING_SERVICE_NAME
KEYRING_USER = "refresh_token"
SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={}"
REFRESH_URL = "https://securetoken.googleapis.com/v1/token?key={}"


class AuthService:
    def __init__(self, firebase_service):
        self.fb = firebase_service
        self._current_user: Optional[User] = None
        self._id_token: Optional[str] = None
        self._token_expiry: float = 0

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        return self._current_user is not None

    @property
    def is_director(self) -> bool:
        return self._current_user is not None and self._current_user.role == "director"

    @property
    def is_admin_or_librarian(self) -> bool:
        return self._current_user is not None and self._current_user.role in ("admin", "librarian")

    @property
    def role(self) -> str:
        return self._current_user.role if self._current_user else ""

    @property
    def is_directorate_admin(self) -> bool:
        return self._current_user is not None and self._current_user.role in ("directorate_admin",)

    @property 
    def is_college_admin(self) -> bool:
        """College Admin = old 'director' or 'admin' roles."""
        return self._current_user is not None and self._current_user.role in (
            "college_admin", "director", "admin"
        )

    @property
    def is_librarian(self) -> bool:
        return self._current_user is not None and self._current_user.role in (
            "librarian", "admin", "college_admin", "director"
        )

    def can_manage_books(self) -> bool:
        return self.role in ("admin", "college_admin", "director", "librarian")

    def can_manage_members(self) -> bool:
        return self.role in ("admin", "college_admin", "director", "librarian")

    def can_access_settings(self) -> bool:
        return self.role in ("admin", "college_admin", "director")

    def can_view_reports(self) -> bool:
        return self.role in ("admin", "college_admin", "director", "directorate_admin")

    def can_view_directorate_dashboard(self) -> bool:
        return self.role in ("director", "college_admin", "directorate_admin")

    # ── Sign In ───────────────────────────────────────────────────────────────
    def sign_in(self, email: str, password: str,
                remember_me: bool = False) -> Tuple[bool, str]:
        """Sign in with email/password. Returns (success, error_msg)."""
        # Fallback Local Accounts for Offline Testing / Mock Mode
        if self.fb.mock_mode or not config.FIREBASE_WEB_API_KEY or config.FIREBASE_WEB_API_KEY == "your-firebase-web-api-key":
            if email == "admin@gdc.edu" and password == "admin":
                self._current_user = User(uid="local-admin", email=email, name="Local Admin", role="admin")
                return True, ""
            elif email == "director@gdc.edu" and password == "director":
                self._current_user = User(uid="local-director", email=email, name="Local Director", role="director")
                return True, ""
            elif email == "librarian@gdc.edu" and password == "librarian":
                self._current_user = User(uid="local-librarian", email=email, name="Local Librarian", role="librarian")
                return True, ""
            return False, "Offline Mode: Use admin@gdc.edu / admin, director@gdc.edu / director, or librarian@gdc.edu / librarian."

        try:
            resp = requests.post(
                SIGN_IN_URL.format(config.FIREBASE_WEB_API_KEY),
                json={"email": email, "password": password, "returnSecureToken": True},
                timeout=10,
            )
            data = resp.json()
            if "error" in data:
                return False, data["error"].get("message", "Login failed")

            self._id_token = data["idToken"]
            self._token_expiry = time.time() + int(data.get("expiresIn", 3600))
            uid = data["localId"]
            refresh_token = data.get("refreshToken", "")

            # Fetch role from Firestore users collection
            if self.fb.db:
                user_doc = self.fb.db.collection("users").document(uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data["uid"] = uid
                    self._current_user = User.from_dict(user_data)
                else:
                    self._current_user = User(uid=uid, email=email, role="admin")
            else:
                self._current_user = User(uid=uid, email=email, role="admin")

            # Store refresh token securely if "remember me"
            if remember_me and refresh_token:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USER, refresh_token)
            elif not remember_me:
                try:
                    keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
                except Exception:
                    pass

            return True, ""

        except requests.exceptions.ConnectionError:
            return False, "No internet connection. Check your network."
        except Exception as e:
            return False, str(e)

    # ── Remember Me Restore ────────────────────────────────────────────────────
    def try_restore_session(self) -> bool:
        """Try to restore session from saved refresh token (Windows Credential Manager)."""
        try:
            refresh_token = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
            if not refresh_token or not config.FIREBASE_WEB_API_KEY:
                return False

            resp = requests.post(
                REFRESH_URL.format(config.FIREBASE_WEB_API_KEY),
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=10,
            )
            data = resp.json()
            if "error" in data or "id_token" not in data:
                return False

            self._id_token = data["id_token"]
            self._token_expiry = time.time() + int(data.get("expires_in", 3600))
            uid = data.get("user_id", "")

            if self.fb.db:
                user_doc = self.fb.db.collection("users").document(uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data["uid"] = uid
                    self._current_user = User.from_dict(user_data)
                    return True
            else:
                # In mock mode, if we reach here we can't really restore a "real" session role
                # but we shouldn't crash.
                return False
            return False
        except Exception:
            return False

    # ── Sign Out ──────────────────────────────────────────────────────────────
    def sign_out(self):
        self._current_user = None
        self._id_token = None
        self._token_expiry = 0

    # ── Clear Saved Credentials ───────────────────────────────────────────────
    def clear_saved_credentials(self):
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        except Exception:
            pass
