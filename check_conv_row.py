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
    run_ssh("SELECT id, initiator_id, target_id, status, business_context FROM core.conversations WHERE id = '8b28f3d1-494a-4a30-bb8f-6f4205691e69';")
