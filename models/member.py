"""
models/member.py — Member/Student data model matching Android/Firestore schema exactly.
PIN is stored as plain text, matching the Android SQLDelight implementation.
"""
import uuid
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Member:
    syncId: str = ""
    id: int = 0
    memberId: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    department: str = ""
    memberType: str = "Student"
    joinDate: str = ""
    expiryDate: str = ""
    booksIssued: int = 0
    fatherName: str = ""
    className: str = ""
    classNo: str = ""
    address: str = ""
    photoUri: Optional[str] = None
    designation: str = ""
    bps: str = ""
    pin: str = ""           # Stored as plain text — matches Android
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
            "memberId": self.memberId,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "department": self.department,
            "memberType": self.memberType,
            "joinDate": self.joinDate,
            "expiryDate": self.expiryDate,
            "booksIssued": self.booksIssued,
            "fatherName": self.fatherName,
            "className": self.className,
            "classNo": self.classNo,
            "address": self.address,
            "photoUri": self.photoUri,
            "designation": self.designation,
            "bps": self.bps,
            "pin": self.pin,
            "lastUpdated": self.lastUpdated,
            "deleted": self.deleted,
        }

    @staticmethod
    def from_dict(d: dict) -> "Member":
        return Member(
            syncId=d.get("syncId", ""),
            memberId=d.get("memberId", ""),
            name=d.get("name", ""),
            email=d.get("email", ""),
            phone=d.get("phone", ""),
            department=d.get("department", ""),
            memberType=d.get("memberType", "Student"),
            joinDate=d.get("joinDate", ""),
            expiryDate=d.get("expiryDate", ""),
            booksIssued=int(d.get("booksIssued", 0)),
            fatherName=d.get("fatherName", ""),
            className=d.get("className", ""),
            classNo=d.get("classNo", ""),
            address=d.get("address", ""),
            photoUri=d.get("photoUri"),
            designation=d.get("designation", ""),
            bps=d.get("bps", ""),
            pin=d.get("pin", ""),
            lastUpdated=int(d.get("lastUpdated", 0)),
            deleted=bool(d.get("deleted", False)),
        )
