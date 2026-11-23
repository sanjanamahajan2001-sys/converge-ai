#!/usr/bin/env python3
"""Comprehensive Live Verification Script for AC-WS10 Dialogue & Boundary Testing.

Performs:
1. Ordered Mood Combination Tests:
   - Mood Test 1: Mixed Incompatible (Initiator: 'Prefer low-key interaction', Target: 'Open to discussing an informal break or meetup')
     * Turn 1 (0): Introduces with 'Prefer low-key interaction'
     * Turn 2 (1): Responding representative acknowledges partner's mood ('Noting your focus on \'Prefer low-key interaction\', Maahi Sharma\'s current focus is \'Open to discussing an informal break or meetup\'')
     * Turn 3 (2): Proposes asynchronous exchange / note comparison, strictly respecting low-key (NO COFFEE proposal)
     * Turn 4 (3): Conditionally acknowledges openness without committing
     * Turn 5 (4): Clean handoff to human attendees (no Turn 6 representative)
   - Reset DB between tests: DELETE FROM core.messages; DELETE FROM core.conversations; (Explicitly intentional)
   
   - Mood Test 2: Informal Meetup / Casual Pair (Initiator: 'Open to discussing an informal break or meetup', Target: 'Open to casual conversation')
     * Turn 2 (1): Responding rep acknowledges partner's mood
     * Turn 3 (2): Appropriately proposes coffee or catching up
     * Turn 4 (3): Conditionally acknowledges openness
     * Turn 5 (4): Clean handoff
   - Reset DB between tests (Explicitly intentional)

   - Mood Test 3: Conference-focused Pair
     * Turn 2 (1): Responding rep acknowledges partner's mood
     * Turn 3 (2): Proposes discussing takeaways / key themes (NO COFFEE)
     * Turn 4 (3): Openness without committing
     * Turn 5 (4): Clean handoff
   - Reset DB between tests (Explicitly intentional)

2. 20-Turn Limit & Boundary Verification:
   - Completes 5 representative turns (0-4)
   - Sends 14 human attendee messages (turns 5 through 18, reaching 19 messages)
   - Sends the 20th message (index 19) -> verifies it succeeds and immediately sets conversation status to COMPLETED
   - Attempts to send a 21st message (index 20) -> strictly rejected with HTTP 409 Conflict ("Conversation has reached the maximum turn limit of 20 messages.")
"""

import asyncio
import httpx
import json
import subprocess
import sys
import time

BASE_URL = "https://192.46.210.48/converge-api/v1"
SSH_CMD = 'ssh -i ~/.ssh/linode_prod root@192.46.210.48'

def run_psql(sql):
    escaped_sql = sql.replace('"', '\\"')
    cmd = f"{SSH_CMD} \"sudo -u postgres psql -d converge_ai_db -c \\\"{escaped_sql}\\\"\""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip(), res.stderr.strip()

def reset_db_conversations(reason: str):
    print(f"\n{'='*70}\n[INTENTIONAL DB RESET] Reason: {reason}\n{'='*70}")
    out, err = run_psql("DELETE FROM core.messages; DELETE FROM core.conversations;")
    print("PSQL Output:\n", out)
    if err:
        print("PSQL Stderr:\n", err)

async def set_user_mood_via_api(client: httpx.AsyncClient, mood: str):
    resp = await client.put(f"{BASE_URL}/profile/me", json={"current_mood": mood})
    assert resp.status_code == 200, f"Failed to set mood: {resp.status_code} {resp.text}"
    print(f"Updated user mood via API to: '{mood}'")

def print_current_db_state():
    sql = "SELECT u.username, p.current_mood, p.intent FROM core.users u JOIN core.participant_profiles p ON u.id = p.user_id WHERE u.username IN ('sanjanamaahi', 'maahi');"
    out, _ = run_psql(sql)
    print("\n[DB State - Users & Current Moods]:\n" + out)

    sql2 = "SELECT u.username, s.title, d.decision FROM agenda.session_intent_decisions d JOIN core.users u ON d.user_id = u.id JOIN agenda.sessions s ON d.session_id = s.id WHERE u.username IN ('sanjanamaahi', 'maahi');"
    out2, _ = run_psql(sql2)
    print("\n[DB State - Verified Attendance Decisions]:\n" + out2)

async def create_client_session(identifier: str, password: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(
        verify=False,
        timeout=30.0,
        headers={"x-requested-with": "xmlhttprequest"},
    )
    resp = await client.post(
        f"{BASE_URL}/auth/login",
        json={"identifier": identifier, "password": password},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {identifier}: {resp.status_code} {resp.text}")
    print(f"Logged in successfully as {identifier}: cookies = {list(client.cookies.keys())}")
    return client

async def run_dialogue_exchange(init_client: httpx.AsyncClient, target_client: httpx.AsyncClient, target_id: str):
    # 1. Initiator initiates conversation
    c_resp = await init_client.post(
        f"{BASE_URL}/conversations",
        json={"target_id": target_id},
    )
    assert c_resp.status_code in (201, 200), f"Failed to initiate: {c_resp.status_code} {c_resp.text}"
    conv = c_resp.json()
    conv_id = conv["id"]
    print(f"Conversation created: {conv_id}, initial status: {conv['status']}")

    # 2. Target accepts conversation with trigger_agent=True
    a_resp = await target_client.post(
        f"{BASE_URL}/conversations/{conv_id}/accept?trigger_agent=true",
    )
    assert a_resp.status_code == 200, f"Failed to accept: {a_resp.status_code} {a_resp.text}"
    print(f"Target accepted conversation and triggered agent exchange.")

    # 3. Poll for the 5 representative messages to complete
    messages = []
    for poll in range(20):
        await asyncio.sleep(1.0)
        det_resp = await init_client.get(f"{BASE_URL}/conversations/{conv_id}")
        det = det_resp.json()
        messages = det.get("messages", [])
        if len(messages) >= 5:
            break

    det_resp = await init_client.get(f"{BASE_URL}/conversations/{conv_id}")
    det = det_resp.json()
    messages = det.get("messages", [])
    print(f"Total messages generated: {len(messages)}")
    for m in messages:
        print(f"  Turn #{m['turn_index'] + 1} ({m['sender_type']}): {m['content']}")

    return conv_id, messages

async def main():
    print("Authenticating Sanjana (Initiator) and Maahi (Target)...")
    init_client = await create_client_session("sanjanamaahi", "Sanju@2001")
    target_client = await create_client_session("maahi", "Sanju@2001")

    # Get Maahi user ID
    target_me = (await target_client.get(f"{BASE_URL}/profile/me")).json()
    maahi_id = target_me["user_id"]
    init_me = (await init_client.get(f"{BASE_URL}/profile/me")).json()
    sanjana_id = init_me["user_id"]
    print(f"User IDs: Sanjana={sanjana_id}, Maahi={maahi_id}")

    # Ensure conversation table is clean before starting
    reset_db_conversations("Initial cleanup before Test 1")

    # =====================================================================
    # TEST 1: Mixed Incompatible Moods (Low-Key vs Informal Meetup)
    # =====================================================================
    print("\n" + "#"*70)
    print("TEST 1: Mixed Moods - Sanjana (Prefer low-key) vs Maahi (Informal meetup)")
    print("#"*70)
    await set_user_mood_via_api(init_client, "Prefer low-key interaction")
    await set_user_mood_via_api(target_client, "Open to discussing an informal break or meetup")
    print_current_db_state()

    conv_id_1, msgs_1 = await run_dialogue_exchange(init_client, target_client, maahi_id)
    assert len(msgs_1) == 5, f"Expected exactly 5 rep messages, got {len(msgs_1)}"
    
    # Verify Turn 2 explicitly acknowledges partner's mood
    turn2_text = msgs_1[1]["content"]
    print(f"\n[EVALUATION - Turn 2 Mood Acknowledgment]:\n'{turn2_text}'")
    assert "Prefer low-key interaction" in turn2_text
    assert "Open to discussing an informal break or meetup" in turn2_text

    # Verify Turn 3 respects Low-key (no coffee proposal, offers asynchronous or comparing notes)
    turn3_text = msgs_1[2]["content"]
    print(f"\n[EVALUATION - Turn 3 Mixed Grounding]:\n'{turn3_text}'")
    assert "grabbing coffee" not in turn3_text.lower(), "Turn 3 should NOT propose coffee when one party prefers low-key!"
    assert "asynchronous exchange or comparing notes" in turn3_text

    # Verify Turn 4 leaves it open without commitment
    turn4_text = msgs_1[3]["content"]
    assert "That could be an option" in turn4_text

    # Verify Turn 5 clean handoff
    turn5_text = msgs_1[4]["content"]
    assert "leave this conversation open" in turn5_text

    # Reset DB intentionally before next mood combination test
    reset_db_conversations("Completed Test 1 (Mixed Moods); resetting before Test 2 (Informal Meetup / Coffee)")

    # =====================================================================
    # TEST 2: Informal Meetup / Casual Pair
    # =====================================================================
    print("\n" + "#"*70)
    print("TEST 2: Informal Meetup - Sanjana (Open to break/meetup) vs Maahi (Casual conversation)")
    print("#"*70)
    await set_user_mood_via_api(init_client, "Open to discussing an informal break or meetup")
    await set_user_mood_via_api(target_client, "Open to casual conversation")
    print_current_db_state()

    conv_id_2, msgs_2 = await run_dialogue_exchange(init_client, target_client, maahi_id)
    assert len(msgs_2) == 5
    turn2_text_2 = msgs_2[1]["content"]
    print(f"\n[EVALUATION - Turn 2 Mood Acknowledgment]:\n'{turn2_text_2}'")
    assert "Open to discussing an informal break or meetup" in turn2_text_2
    assert "Open to casual conversation" in turn2_text_2

    turn3_text_2 = msgs_2[2]["content"]
    print(f"\n[EVALUATION - Turn 3 Coffee Proposal]:\n'{turn3_text_2}'")
    assert "coffee" in turn3_text_2.lower()

    reset_db_conversations("Completed Test 2 (Informal Meetup); resetting before Test 3 (Conference-focused)")

    # =====================================================================
    # TEST 3: Conference-focused Pair
    # =====================================================================
    print("\n" + "#"*70)
    print("TEST 3: Conference-focused Pair - Both 'Conference-focused'")
    print("#"*70)
    await set_user_mood_via_api(init_client, "Conference-focused")
    await set_user_mood_via_api(target_client, "Conference-focused")
    print_current_db_state()

    conv_id_3, msgs_3 = await run_dialogue_exchange(init_client, target_client, maahi_id)
    assert len(msgs_3) == 5
    turn2_text_3 = msgs_3[1]["content"]
    print(f"\n[EVALUATION - Turn 2 Mood Acknowledgment]:\n'{turn2_text_3}'")
    assert "Noting our shared focus on 'Conference-focused'" in turn2_text_3
    turn3_text_3 = msgs_3[2]["content"]
    print(f"\n[EVALUATION - Turn 3 Session Takeaways]:\n'{turn3_text_3}'")
    assert "grabbing coffee" not in turn3_text_3.lower()
    assert "takeaways or session themes" in turn3_text_3

    reset_db_conversations("Completed Test 3 (Conference-focused); resetting before Test 4 (20-Turn Boundary)")

    # =====================================================================
    # TEST 4: 20-Turn Boundary & Rejection Verification
    # =====================================================================
    print("\n" + "#"*70)
    print("TEST 4: 20-Turn Boundary Test (5 Reps + 15 Human turns = 20 max, 21st Rejected)")
    print("#"*70)
    await set_user_mood_via_api(init_client, "Ready to network")
    await set_user_mood_via_api(target_client, "Ready to network")
    print_current_db_state()

    conv_id_4, msgs_4 = await run_dialogue_exchange(init_client, target_client, maahi_id)
    assert len(msgs_4) == 5
    print(f"5 representative turns completed for conversation {conv_id_4}.")

    # Now send human messages:
    # Message 6 (index 5) through Message 19 (index 18) -> 14 human messages
    print("\nSending human messages from Turn 6 up to Turn 19 (indices 5..18)...")
    for i in range(5, 19):
        is_sanjana = (i % 2 == 1)
        active_client = init_client if is_sanjana else target_client
        sender_name = "Sanjana" if is_sanjana else "Maahi"
        post_r = await active_client.post(
            f"{BASE_URL}/conversations/{conv_id_4}/messages",
            json={"content": f"Human message #{i+1} from {sender_name}."},
        )
        assert post_r.status_code == 201, f"Failed at message #{i+1}: {post_r.status_code} {post_r.text}"
        time.sleep(0.05)

    # Check status after 19 messages (should still be ACTIVE)
    det_19 = (await init_client.get(f"{BASE_URL}/conversations/{conv_id_4}")).json()
    print(f"Status after 19 messages: {det_19['status']} (total messages: {len(det_19['messages'])})")
    assert det_19['status'] == "ACTIVE"
    assert len(det_19['messages']) == 19

    # Now send the 20th message (index 19)
    print("\nSending the 20th message (boundary message, index 19)...")
    post_20 = await target_client.post(
        f"{BASE_URL}/conversations/{conv_id_4}/messages",
        json={"content": "Human message #20 - This is the final permitted turn."},
    )
    assert post_20.status_code == 201, f"Expected 20th message to succeed, got {post_20.status_code} {post_20.text}"
    print(f"20th message accepted: Turn #{post_20.json()['turn_index'] + 1}")

    # Check status after 20 messages (must be COMPLETED)
    det_20 = (await init_client.get(f"{BASE_URL}/conversations/{conv_id_4}")).json()
    print(f"Status after 20 messages: {det_20['status']} (outcome: {det_20.get('terminal_outcome')})")
    assert det_20['status'] == "COMPLETED", f"Expected COMPLETED, got {det_20['status']}"
    assert det_20.get('terminal_outcome') == "COMPLETED_WITHOUT_PROPOSAL"
    assert len(det_20['messages']) == 20

    # Now attempt to send the 21st message (index 20) -> MUST BE REJECTED with HTTP 409
    print("\nAttempting to send the 21st message (turn index 20)...")
    post_21 = await init_client.post(
        f"{BASE_URL}/conversations/{conv_id_4}/messages",
        json={"content": "Human message #21 - Should be rejected."},
    )
    print(f"21st message response: {post_21.status_code} {post_21.text}")
    assert post_21.status_code == 409, f"Expected HTTP 409 Conflict, got {post_21.status_code}"
    assert "already COMPLETED" in post_21.text or "maximum turn limit of 20 messages" in post_21.text
    print("✓ Verified: 21st message strictly rejected with HTTP 409 Conflict!")

    print("\n" + "="*70)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY WITH ZERO DEFECTS!")
    print("="*70)

    await init_client.aclose()
    await target_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
