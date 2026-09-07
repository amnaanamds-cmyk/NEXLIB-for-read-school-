"""
models/issue_record.py — IssuedBook record matching Android/Firestore schema.
"""
import uuid
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class IssueRecord:
    syncId: str = ""
    id: int = 0
    bookId: int = 0
    bookTitle: str = ""
    bookIsbn: str = ""
    memberId: int = 0
    memberName: str = ""
    memberMemberId: str = ""
    issueDate: str = ""
    dueDate: str = ""
    returnDate: Optional[str] = None
    fine: float = 0.0
    status: str = "Issued"   # "Issued" or "Returned"
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
            "bookIsbn": self.bookIsbn,
            "memberId": self.memberId,
            "memberName": self.memberName,
            "memberMemberId": self.memberMemberId,
            "issueDate": self.issueDate,
            "dueDate": self.dueDate,
            "returnDate": self.returnDate,
            "fine": self.fine,
            "status": self.status,
            "lastUpdated": self.lastUpdated,
            "deleted": self.deleted,
        }

    @staticmethod
    def from_dict(d: dict) -> "IssueRecord":
        return IssueRecord(
            syncId=d.get("syncId", ""),
            id=int(d.get("id", 0) or 0),
            bookId=int(d.get("bookId", 0)),
            bookTitle=d.get("bookTitle", ""),
            bookIsbn=d.get("bookIsbn", ""),
            memberId=int(d.get("memberId", 0)),
            memberName=d.get("memberName", ""),
            memberMemberId=d.get("memberMemberId", ""),
            issueDate=d.get("issueDate", ""),
            dueDate=d.get("dueDate", ""),
            returnDate=d.get("returnDate"),
            fine=float(d.get("fine", 0.0)),
            status=d.get("status", "Issued"),
            lastUpdated=int(d.get("lastUpdated", 0)),
            deleted=bool(d.get("deleted", False)),
        )
