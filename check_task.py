import subprocess

cmd = [
    "ssh",
    "-i",
    "/home/sanjana/.ssh/linode_prod",
    "root@192.46.210.48",
    "sudo -u postgres psql -d converge_ai_db -c \"SELECT id, sender_type, turn_index, content FROM core.messages WHERE conversation_id = 'c6d24dad-061e-4178-939d-c6ab55c892f4' ORDER BY turn_index;\""
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", res.stdout)
