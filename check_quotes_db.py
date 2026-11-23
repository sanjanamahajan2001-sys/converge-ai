import subprocess

def run_ssh(sql: str):
    cmd = [
        "ssh", "-i", "/home/sanjana/.ssh/linode_prod", "-o", "StrictHostKeyChecking=no", "root@192.46.210.48",
        f"sudo -u postgres psql -d converge_ai_db -c \"{sql}\""
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:\n" + res.stdout)
    if res.stderr:
        print("STDERR:\n" + res.stderr)

if __name__ == "__main__":
    print("Checking quote_requests in database:")
    run_ssh("SELECT id, customer_id, title, product_name, quantity, quantity_unit, created_at FROM business.quote_requests ORDER BY created_at DESC LIMIT 5;")
    print("Checking quote_vendor_matches:")
    run_ssh("SELECT id, quote_request_id, vendor_id, status FROM business.quote_vendor_matches;")
    print("Checking conversation 8b28f3d1-494a-4a30-bb8f-6f4205691e69 context:")
    run_ssh("SELECT * FROM business.conversation_business_contexts WHERE conversation_id = '8b28f3d1-494a-4a30-bb8f-6f4205691e69';")
