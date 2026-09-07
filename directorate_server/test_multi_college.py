import time
import requests
import json

URL = "http://localhost:8000"

def simulate_college_push(college_id, api_key, total_books, available_books, issued_books, overdue_count, total_fines):
    headers = {
        "X-College-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "college_id": college_id,
        "total_books": total_books,
        "available_books": available_books,
        "issued_books": issued_books,
        "total_members": int(total_books * 0.4),
        "overdue_count": overdue_count,
        "total_fines": total_fines,
        "top_borrowed_books": [
            {"title": "Introduction to Algorithms", "count": 25},
            {"title": "Clean Code", "count": 18}
        ],
        "activity_summary": [
            f"Issued book to Student A",
            f"Returned book with fine Rs. {total_fines/10:.0f}"
        ]
    }
    
    try:
        response = requests.post(f"{URL}/api/sync", json=payload, headers=headers)
        print(f"[{college_id}] Push Status Code:", response.status_code)
        print(f"[{college_id}] Response JSON:", response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"[{college_id}] Error pushing data:", e)
        return False

def run_simulation():
    print("Starting simulation...")
    # Register/ensure swabi and kohat colleges exist
    # (FastAPI startup seeds default Swat and Peshawar, but let's test with them)
    
    # Swat (normal status)
    simulate_college_push(
        college_id="gdc-swat",
        api_key="key-swat-456",
        total_books=5000,
        available_books=4800,
        issued_books=200,
        overdue_count=10, # low overdue rate
        total_fines=150.0
    )
    
    # Peshawar (should trigger overdue rate and high fines warnings)
    simulate_college_push(
        college_id="gdc-peshawar",
        api_key="key-peshawar-123",
        total_books=8000,
        available_books=7000,
        issued_books=1000,
        overdue_count=350, # 35% overdue rate (>20% threshold)
        total_fines=12000.0 # >10000 threshold
    )

if __name__ == "__main__":
    run_simulation()
