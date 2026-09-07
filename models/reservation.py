"""
models/reservation.py — Reservation and staff User data models.
"""
import uuid
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Reservation:
    syncId: str = ""
    id: int = 0
    bookId: int = 0
    bookTitle: str = ""
    memberId: int = 0
    memberName: str = ""
    reservedDate: str = ""
    status: str = "Pending"   # "Pending" or "Fulfilled"
    notifiedDate: Optional[str] = None
    lastUpdated: int = 0
    deleted: bool = False

    def __post_init__(self):
        if not self.syncId:
            self.syncId = str(uuid.uuid4())
        if not self.lastUpdated:
            self.lastUpdated = int(time.time() * 1000)

    def to_dict(self) -> dict:
        return {
            "syncId": self.syncId,
            "bookId": self.bookId,
            "bookTitle": self.bookTitle,
            "memberId": self.memberId,
            "memberName": self.memberName,
            "reservedDate": self.reservedDate,
            "status": self.status,
            "notifiedDate": self.notifiedDate,
            "lastUpdated": self.lastUpdated,
            "deleted": self.deleted,
        }

    @staticmethod
    def from_dict(d: dict) -> "Reservation":
        return Reservation(
            syncId=d.get("syncId", ""),
            bookId=int(d.get("bookId", 0)),
            bookTitle=d.get("bookTitle", ""),
            memberId=int(d.get("memberId", 0)),
            memberName=d.get("memberName", ""),
            reservedDate=d.get("reservedDate", ""),
            status=d.get("status", "Pending"),
            notifiedDate=d.get("notifiedDate"),
            lastUpdated=int(d.get("lastUpdated", 0)),
            deleted=bool(d.get("deleted", False)),
        )


@dataclass
class User:
    uid: str = ""
    email: str = ""
    name: str = ""
    role: str = "admin"   # "admin" or "librarian"

    @staticmethod
    def from_dict(d: dict) -> "User":
        return User(
            uid=d.get("uid", ""),
            email=d.get("email", ""),
            name=d.get("name", ""),
            role=d.get("role", "admin"),
        )
