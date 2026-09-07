import requests, json

BASE = 'http://127.0.0.1:8000'

# Login as Directorate Admin
r = requests.post(f'{BASE}/api/auth/login', json={'email':'director@gdc.edu','password':'director123'})
data = r.json()
token = data['access_token']
H = {'Authorization': f'Bearer {token}'}

print('=== LOGIN OK ===')
print(json.dumps(data['user'], indent=2))

# Aggregated stats
agg = requests.get(f'{BASE}/api/aggregate', headers=H).json()
print()
print('=== AGGREGATE (ALL COLLEGES COMBINED) ===')
print(json.dumps(agg, indent=2))

# Per-college drill-down: Swat
swat = requests.get(f'{BASE}/api/colleges/gdc-swat/stats', headers=H).json()
print()
print('=== GDC SWAT DRILL-DOWN ===')
print('  total_books:', swat['snapshot']['total_books'])
print('  overdue_count:', swat['snapshot']['overdue_count'])
print('  total_fines:', swat['snapshot']['total_fines'])

# Per-college drill-down: Peshawar
pesh = requests.get(f'{BASE}/api/colleges/gdc-peshawar/stats', headers=H).json()
print()
print('=== GDC PESHAWAR DRILL-DOWN ===')
print('  total_books:', pesh['snapshot']['total_books'])
print('  overdue_count:', pesh['snapshot']['overdue_count'])
print('  total_fines:', pesh['snapshot']['total_fines'])

# Verify separation: Peshawar has 8000 books, Swat has 5000 — must NOT be mixed
assert swat['snapshot']['total_books'] == 5000, 'Swat data mismatch!'
assert pesh['snapshot']['total_books'] == 8000, 'Peshawar data mismatch!'
assert agg['total_books'] == 13000, f"Aggregate total mismatch! Got {agg['total_books']}"
assert agg['college_count'] == 2, 'Wrong college count in aggregate!'
print()
print('=== ALL ASSERTIONS PASSED - DATA CORRECTLY SEPARATED AND AGGREGATED ===')

# Alerts
alerts_resp = requests.get(f'{BASE}/api/alerts', headers=H).json()
print()
print(f'=== ACTIVE ALERTS ({len(alerts_resp)}) ===')
for a in alerts_resp:
    sev = a['severity'].upper()
    cname = a['college_name']
    msg = a['message']
    print(f'  [{sev}] {cname}: {msg}')

# Comparison ranking
cmp = requests.get(f'{BASE}/api/comparison', headers=H).json()
print()
print('=== COLLEGE COMPARISON / RANKING ===')
for c in cmp:
    print(f"  {c['name']}: books={c['total_books']}, overdue={c['overdue_count']}, fines={c['total_fines']}")
