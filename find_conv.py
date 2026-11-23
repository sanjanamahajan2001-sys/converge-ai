import subprocess

def run_ssh(cmd_str: str):
    cmd = [
        "ssh", "-i", "/home/sanjana/.ssh/linode_prod", "-o", "StrictHostKeyChecking=no", "root@192.46.210.48",
        cmd_str
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:\n" + res.stdout)
    if res.stderr:
        print("STDERR:\n" + res.stderr)

if __name__ == "__main__":
    run_ssh("""sudo -u postgres psql -d converge_ai_db -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('core', 'business', 'agenda', 'public');" """)
    run_ssh("""sudo -u postgres psql -d converge_ai_db -c "SELECT count(*) FROM core.conversations;" """)
    run_ssh("""sudo -u postgres psql -d converge_ai_db -c "SELECT id FROM core.conversations WHERE id::text LIKE '%8b28f3d1%';" """)
