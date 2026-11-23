import requests
import urllib3
urllib3.disable_warnings()

BASE_URL = "https://192.46.210.48/converge-api/v1"
users = ["sanjanamaahi", "maahi", "vikram", "aarav", "rohit"]

for u in users:
    s = requests.Session()
    s.headers["X-Requested-With"] = "XMLHttpRequest"
    resp = s.post(f"{BASE_URL}/auth/login", json={"identifier": u, "password": "Sanju@2001"}, verify=False)
    login_data = resp.json()
    user_id = login_data.get("user_id")
    print(f"\nUser: {u} (ID: {user_id})")

    # Get business profile
    prof_resp = s.get(f"{BASE_URL}/business/profile/me", verify=False)
    if prof_resp.status_code == 200:
        p = prof_resp.json()
        print(f"  Company: {p.get('company_name')} | HQ: {p.get('hq_city')}")
        print(f"  Roles: Buyer={p.get('is_buyer')}, Supp={p.get('is_supplier')}, Vend={p.get('is_vendor')}, Dist={p.get('is_distributor')}, Part={p.get('is_partner')}")
        offerings = p.get("offerings", [])
        for o in offerings:
            print(f"    - Offering {o.get('id')}: {o.get('custom_product_title')} | Prod: {o.get('product_code')} | Serv: {o.get('service_code')} | Cap: {o.get('declared_monthly_capacity')} {o.get('capacity_unit')}")
    else:
        print(f"  Profile error: {prof_resp.status_code} {prof_resp.text}")
