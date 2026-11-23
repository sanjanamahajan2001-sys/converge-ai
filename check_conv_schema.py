import subprocess

def run_ssh(sql: str):
    cmd = [
        "ssh", "-i", "/home/sanjana/.ssh/linode_prod", "-o", "StrictHostKeyChecking=no", "root@192.46.210.48",
        f"sudo -u postgres psql -d converge_ai_db -c \"{sql}\""
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:\n" + res.stdout)

if __name__ == "__main__":
    run_ssh("\d core.conversations")
