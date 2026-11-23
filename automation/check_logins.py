import requests
import urllib3
urllib3.disable_warnings()

BASE_URL = "https://192.46.210.48/converge-api/v1"
users = ["sanjanamaahi", "maahi", "vikram", "aarav", "rohit"]

for u in users:
    resp = requests.post(f"{BASE_URL}/auth/login", json={"identifier": u, "password": "Sanju@2001"}, verify=False)
    print(f"User: {u} -> Status: {resp.status_code}")
