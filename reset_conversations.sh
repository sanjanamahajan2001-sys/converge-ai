#!/usr/bin/env bash
# Reset conversations and cooldowns on production server (192.46.210.48)
ssh -i ~/.ssh/linode_prod root@192.46.210.48 "sudo -u postgres psql -d converge_ai_db -c 'DELETE FROM core.messages; DELETE FROM core.conversations;'"
echo "Conversations and cooldowns successfully cleared on production!"
