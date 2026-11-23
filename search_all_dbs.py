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
    script = """
    for db in $(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE NOT datistemplate AND datname != 'postgres';"); do
        echo "=== Checking DB: $db ==="
        sudo -u postgres psql -d "$db" -c "\\dt *.*" | grep -i "conversation"
        sudo -u postgres psql -d "$db" -t -c "SELECT id FROM core.conversations WHERE id::text LIKE '8b28f3d1%';" 2>/dev/null || true
    done
    """
    run_ssh(f"bash -c '{script}'")
