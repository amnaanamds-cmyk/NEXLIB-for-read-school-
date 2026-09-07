"""
models/book.py — Book data model matching Android/Firestore schema exactly.
"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Book:
    syncId: str = ""
    id: int = 0
    isbn: str = ""
    accNo: str = ""
    title: str = ""
    author: str = ""
    publisher: str = ""
    publisherPlace: str = ""
    publishDate: str = ""
    edition: str = ""
    pages: int = 0
    procurement: str = ""
    volume: str = ""
    price: float = 0.0
    status: str = "Available"
    isDigital: bool = False
    digitalUrl: Optional[str] = None
    category: str = "Uncategorized"
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
            "isbn": self.isbn,
            "accNo": self.accNo,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "publisherPlace": self.publisherPlace,
            "publishDate": self.publishDate,
            "edition": self.edition,
            "pages": self.pages,
            "procurement": self.procurement,
            "volume": self.volume,
            "price": self.price,
            "status": self.status,
            "isDigital": self.isDigital,
            "digitalUrl": self.digitalUrl,
            "category": self.category,
            "lastUpdated": self.lastUpdated,
            "deleted": self.deleted,
        }

    @staticmethod
    def from_dict(d: dict) -> "Book":
        return Book(
            syncId=d.get("syncId", ""),
            id=int(d.get("id", 0) or 0),
            isbn=d.get("isbn", ""),
            accNo=d.get("accNo", ""),
            title=d.get("title", ""),
            author=d.get("author", ""),
            publisher=d.get("publisher", ""),
            publisherPlace=d.get("publisherPlace", ""),
            publishDate=d.get("publishDate", ""),
            edition=d.get("edition", ""),
            pages=int(d.get("pages", 0)),
            procurement=d.get("procurement", ""),
            volume=d.get("volume", ""),
            price=float(d.get("price", 0.0)),
            status=d.get("status", "Available"),
            isDigital=bool(d.get("isDigital", False)),
            digitalUrl=d.get("digitalUrl"),
            category=d.get("category", "Uncategorized"),
            lastUpdated=int(d.get("lastUpdated", 0)),
            deleted=bool(d.get("deleted", False)),
        )
