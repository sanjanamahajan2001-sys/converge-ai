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
    run_ssh("""sudo -u postgres psql -d converge_ai_db -c "SELECT c.id, u1.username as initiator, u2.username as target, c.status FROM core.conversations c JOIN core.users u1 ON c.initiator_id = u1.id JOIN core.users u2 ON c.target_id = u2.id;" """)
