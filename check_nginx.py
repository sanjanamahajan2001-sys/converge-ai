import subprocess

def run_ssh(cmd_str: str):
    cmd = [
        "ssh", "-i", "/home/sanjana/.ssh/linode_prod", "-o", "StrictHostKeyChecking=no", "root@192.46.210.48",
        cmd_str
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:\n" + res.stdout)

if __name__ == "__main__":
    run_ssh("cat /etc/nginx/sites-enabled/* | grep -E 'converge|proxy_pass|location' -A 4 -B 1")
