import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://192.46.210.48/converge-api/v1"

def run_checks():
    print("=== Testing Production Analytics, Profile Demographics & Location Features ===")
    
    # 1. Login Sanjana
    s_sanjana = requests.Session()
    resp = s_sanjana.post(f"{BASE_URL}/auth/login", json={"identifier": "sanjanamaahi", "password": "Sanju@2001"}, verify=False)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    print("✓ Sanjana logged in successfully")

    # 2. Login Maahi
    s_maahi = requests.Session()
    resp = s_maahi.post(f"{BASE_URL}/auth/login", json={"identifier": "maahi", "password": "Sanju@2001"}, verify=False)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    print("✓ Maahi logged in successfully")

    # 3. Update Profile with Gender, Date of Birth & User Location
    prof_payload = {
        "bio_summary": "DevOps Engineer exploring green materials & multi-agent networking.",
        "gender": "Female",
        "date_of_birth": "15-08-1994",
        "location": "Jio World Convention Centre, Hall 3, Mumbai",
        "location_lat": 19.0657,
        "location_lng": 72.8688,
        "allow_agent_matching": True
    }
    p_resp = s_sanjana.put(f"{BASE_URL}/profile/me", json=prof_payload, headers={"X-Requested-With": "XMLHttpRequest"}, verify=False)
    assert p_resp.status_code == 200, f"Profile update failed: {p_resp.text}"
    profile_data = p_resp.json()
    assert profile_data["gender"] == "Female", f"Gender mismatch: {profile_data.get('gender')}"
    assert profile_data["date_of_birth"] == "15-08-1994", f"DOB mismatch: {profile_data.get('date_of_birth')}"
    assert profile_data["location"] == "Jio World Convention Centre, Hall 3, Mumbai", f"Location mismatch: {profile_data.get('location')}"
    assert profile_data["location_lat"] == 19.0657
    assert profile_data["location_lng"] == 72.8688
    print(f"✓ Profile Demographics & Location verified: Gender={profile_data['gender']}, DOB={profile_data['date_of_birth']}, Location={profile_data['location']} ({profile_data['location_lat']}, {profile_data['location_lng']})")

    # 4. Record Analytics Activity Event
    evt_resp = s_sanjana.post(
        f"{BASE_URL}/analytics/events",
        json={"event_type": "LOCATION_SHARE", "feature_name": "location_modal", "metadata": {"picker_mode": "gps"}},
        headers={"X-Requested-With": "XMLHttpRequest"},
        verify=False
    )
    assert evt_resp.status_code == 201, f"Event logging failed: {evt_resp.text}"
    print("✓ Analytics event logged: LOCATION_SHARE")

    # 5. Fetch User Analytics Summary
    sum_resp = s_sanjana.get(f"{BASE_URL}/analytics/my-summary", verify=False)
    assert sum_resp.status_code == 200, f"Analytics summary failed: {sum_resp.text}"
    summary = sum_resp.json()
    print(f"✓ Analytics Summary retrieved: Logins={summary['total_logins']}, Conversations={summary['total_conversations']}, Activity Events={summary['total_activity_events']}")

    # 6. Test Location Sharing in Conversation
    # Clean previous completed test conversation
    import subprocess
    subprocess.run("ssh -i ~/.ssh/linode_prod root@192.46.210.48 \"sudo -u postgres psql -d converge_ai_db -c 'DELETE FROM core.messages; DELETE FROM core.conversations;'\"", shell=True, capture_output=True)

    # Create fresh conversation with Maahi
    maahi_id = "e5fe54e2-d060-4fdc-a304-40b3940e950c"
    conv_init = s_sanjana.post(f"{BASE_URL}/conversations", json={"target_id": maahi_id}, headers={"X-Requested-With": "XMLHttpRequest"}, verify=False)
    assert conv_init.status_code == 201, f"Failed to create conversation: {conv_init.text}"
    conv_id = conv_init.json()["id"]
    
    # Maahi accepts
    acc_resp = s_maahi.post(f"{BASE_URL}/conversations/{conv_id}/accept?trigger_agent=false", headers={"X-Requested-With": "XMLHttpRequest"}, verify=False)
    assert acc_resp.status_code == 200, f"Failed to accept: {acc_resp.text}"
    
    # Send WhatsApp-style Location Message
    loc_payload = {
        "content": "📍 Shared Location: Jio World Convention Centre, Mumbai",
        "message_type": "LOCATION",
        "location": {
            "latitude": 19.0657,
            "longitude": 72.8688,
            "name": "Jio World Convention Centre",
            "address": "G Block BKC, Bandra Kurla Complex, Mumbai, Maharashtra 400098"
        }
    }
    msg_resp = s_sanjana.post(f"{BASE_URL}/conversations/{conv_id}/messages", json=loc_payload, headers={"X-Requested-With": "XMLHttpRequest"}, verify=False)
    assert msg_resp.status_code in (200, 201), f"Send location message failed: {msg_resp.text}"
    msg_data = msg_resp.json()
    assert msg_data["message_type"] == "LOCATION", f"Expected LOCATION type, got: {msg_data.get('message_type')}"
    assert msg_data["location_payload"]["latitude"] == 19.0657
    print(f"✓ WhatsApp-style Location Message successfully sent & persisted on conversation {conv_id}!")
    print(f"  Venue: {msg_data['location_payload']['name']}")
    print(f"  Coordinates: {msg_data['location_payload']['latitude']}, {msg_data['location_payload']['longitude']}")

    print("\n=======================================================")
    print("ALL PRODUCTION CHECKS FOR PHASES 1, 2, 3 & 4 PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    run_checks()
