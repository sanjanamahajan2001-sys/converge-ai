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
    print("=== Quote Requests ===")
    run_ssh("SELECT r.id, r.title, r.customer_id, u.username as customer_user, r.created_at FROM business.quote_requests r JOIN core.users u ON r.customer_id = u.id ORDER BY r.created_at DESC LIMIT 5;")
    print("=== Quote Vendor Matches ===")
    run_ssh("SELECT m.id, m.quote_request_id, m.vendor_id, u.username as vendor_user, m.status, m.match_score FROM business.quote_vendor_matches m JOIN core.users u ON m.vendor_id = u.id ORDER BY m.created_at DESC LIMIT 5;")
