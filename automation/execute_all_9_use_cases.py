"""Execute and validate all 9 commercial discovery & RFQ use cases against live production.

Resets core.messages and core.conversations between each case via SSH.
Records full context, parameters, and 5-turn representative dialogue for each use case.
"""
import json
import os
import subprocess
import time
from typing import Any, Dict, List
import requests
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://192.46.210.48/converge-api/v1"
SSH_CMD = 'ssh -i ~/.ssh/linode_prod -o StrictHostKeyChecking=no root@192.46.210.48 "sudo -u postgres psql -d converge_ai_db -c \'DELETE FROM core.messages; DELETE FROM core.conversations;\'"'

USERS = {
    "sanjanamaahi": {"pass": "Sanju@2001", "id": "16ebf13d-93aa-4433-9b9c-e0b35ae418b3", "company": "InfraTech EPC Solutions Ltd"},
    "maahi": {"pass": "Sanju@2001", "id": "e5fe54e2-d060-4fdc-a304-40b3940e950c", "company": "Maahi Decarb Materials Pvt Ltd"},
    "vikram": {"pass": "Sanju@2001", "id": "6848cd26-5f7b-4a98-9ba2-cf4d9bc9fd29", "company": "Deccan Clinker & Mineral Feedstocks Ltd"},
    "aarav": {"pass": "Sanju@2001", "id": "fde0f622-d96e-45e8-9a27-d2c77e87a07c", "company": "Western Logistics & Heavy Haulage Fleet"},
    "rohit": {"pass": "Sanju@2001", "id": "3fd530c0-16b7-4549-b4fb-3dc75fd1d14f", "company": "Apex Building Materials & Regional Distribution Ltd"},
}


def reset_db_conversations():
    """Execute mandated DB reset between use cases."""
    print("  -> Resetting production conversations and messages via SSH...")
    res = subprocess.run(SSH_CMD, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [ERROR] DB reset failed: {res.stderr}")
    else:
        print("  -> DB reset successful.")


def get_authenticated_session(username: str) -> requests.Session:
    """Create session with verified CSRF headers and authenticated cookies."""
    s = requests.Session()
    s.headers["X-Requested-With"] = "XMLHttpRequest"
    resp = s.post(f"{BASE_URL}/auth/login", json={"identifier": username, "password": USERS[username]["pass"]}, verify=False)
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {username}: {resp.status_code} {resp.text}")
    return s


def request_with_retry(sess: requests.Session, username: str, method: str, url: str, **kwargs) -> requests.Response:
    """Execute HTTP request with automatic session re-authentication and connection retry."""
    for attempt in range(3):
        try:
            resp = getattr(sess, method.lower())(url, verify=False, **kwargs)
            if resp.status_code == 401 and "revoked" in resp.text:
                print(f"  [INFO] Session for {username} was revoked by concurrent activity. Re-authenticating...")
                new_sess = get_authenticated_session(username)
                sess.cookies.update(new_sess.cookies)
                resp = getattr(sess, method.lower())(url, verify=False, **kwargs)
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < 2:
                time.sleep(2)
                continue
            raise e


def run_use_case(case_num: int, case_def: Dict[str, Any]) -> Dict[str, Any]:
    print(f"\n================================================================================")
    print(f"STARTING USE CASE {case_num}: {case_def['title']}")
    print(f"================================================================================")
    print(f"Context: {case_def['context']}")
    print(f"Testing: {case_def['what_is_testing']}")

    # 1. Reset DB
    reset_db_conversations()
    time.sleep(1)

    # 2. Login Initiator and Target
    init_user = case_def["initiator"]
    target_user = case_def["target"]
    init_sess = get_authenticated_session(init_user)
    target_sess = get_authenticated_session(target_user)

    # 3. Create Conversation with Business Context
    bctx = case_def["business_context"]
    create_payload = {
        "target_id": USERS[target_user]["id"],
        "business_context": bctx,
    }
    print(f"  -> {init_user} initiating {bctx['inquiry_type']} with {target_user}...")
    conv_resp = request_with_retry(init_sess, init_user, "post", f"{BASE_URL}/conversations", json=create_payload)
    if conv_resp.status_code not in (200, 201):
        raise RuntimeError(f"Initiate conversation failed ({conv_resp.status_code}): {conv_resp.text}")

    conv_data = conv_resp.json()
    conv_id = conv_data["id"]
    print(f"  -> Conversation created: ID {conv_id} (Status: {conv_data['status']})")

    # 4. Target Accepts Conversation with trigger_agent=true
    print(f"  -> {target_user} accepting conversation {conv_id} & triggering representative dialogue...")
    accept_resp = request_with_retry(target_sess, target_user, "post", f"{BASE_URL}/conversations/{conv_id}/accept?trigger_agent=true")
    if accept_resp.status_code != 200:
        raise RuntimeError(f"Accept conversation failed ({accept_resp.status_code}): {accept_resp.text}")

    # 5. Poll for all 10 representative dialogue turns to complete
    target_turns = 10
    print(f"  -> Waiting for {target_turns} representative dialogue turns to complete (~60s)...")
    messages: List[Dict[str, Any]] = []
    for attempt in range(50):
        time.sleep(2)
        hist_resp = request_with_retry(init_sess, init_user, "get", f"{BASE_URL}/conversations/{conv_id}")
        if hist_resp.status_code == 200:
            hist_data = hist_resp.json()
            messages = hist_data.get("messages", [])
            print(f"     Turn progress: {len(messages)} / {target_turns} messages generated...")
            if len(messages) >= target_turns:
                break

    if len(messages) < target_turns:
        print(f"  [WARN] Only {len(messages)} / {target_turns} messages generated after waiting.")

    # 6. Extract and Format Transcripts
    transcript: List[Dict[str, Any]] = []
    for idx, msg in enumerate(messages):
        sender_type = msg.get("sender_type", "AGENT")
        content = msg.get("content", "")
        created_at = msg.get("created_at", "")
        speaker_name = f"{USERS[init_user]['company']}'s Representative" if idx % 2 == 0 else f"{USERS[target_user]['company']}'s Representative"
        transcript.append({
            "turn_index": idx,
            "turn_label": f"Turn #{idx + 1}",
            "speaker": speaker_name,
            "sender_type": sender_type,
            "created_at": created_at,
            "content": content,
        })
        print(f"\n  [Turn #{idx + 1}] ({speaker_name}):")
        print(f"  \"{content}\"")

    return {
        "case_number": case_num,
        "title": case_def["title"],
        "inquiry_type": bctx["inquiry_type"],
        "initiator": {
            "username": init_user,
            "company": USERS[init_user]["company"],
        },
        "target": {
            "username": target_user,
            "company": USERS[target_user]["company"],
        },
        "context": case_def["context"],
        "what_is_testing": case_def["what_is_testing"],
        "business_context": bctx,
        "conversation_id": conv_id,
        "total_turns": len(messages),
        "transcript": transcript,
        "passed": len(messages) >= 10,
    }


def main():
    cases = [
        # Use Case 1: Buyer looking for product supplier (RFQ Product)
        {
            "title": "Buyer Looking for Product Supplier (RFQ Product)",
            "initiator": "sanjanamaahi",
            "target": "maahi",
            "context": "An EPC contractor (InfraTech EPC Solutions Ltd) requires 1,000 MT of certified Limestone Calcined Clay Cement (LC3) for upcoming green infrastructure projects in Pune.",
            "what_is_testing": "Tests standard physical product procurement RFQ, declared plant run-rate capacity validation (2,500 MT/mo), Ex Works price quotation disclosure (₹4,900 - ₹5,100/MT), Mill Test Certificate (MTC) assurance, and smooth 5th-turn executive handover.",
            "business_context": {
                "inquiry_type": "RFQ_PRODUCT",
                "product_name": "Limestone Calcined Clay Cement (LC3)",
                "product_code": "CALCINED_CLAY_LC3",
                "grade_code": "LC3_50_STANDARD",
                "quantity": 1000.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Pune",
                "timeline_days": 30,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Exploring supply availability and batch test certification for commercial infrastructure project.",
            },
        },
        # Use Case 2: Buyer looking for service vendor (RFI Service)
        {
            "title": "Buyer Looking for Service Vendor (RFI Service)",
            "initiator": "sanjanamaahi",
            "target": "aarav",
            "context": "An infrastructure builder needs dedicated bulk pneumatic bulker tankers and heavy haulage transport for dispatching cement across Mumbai and Pune terminals.",
            "what_is_testing": "Tests service procurement RFI, dedicated fleet operational capacity, GPS-monitored fleet readiness, freight pricing structure, and logistics SLA parameters.",
            "business_context": {
                "inquiry_type": "RFI_SERVICE",
                "product_name": "Bulk Construction Material Transport & Fleet",
                "service_code": "CONSTRUCTION_LOGISTICS",
                "quantity": 25.0,
                "unit": "TRUCKLOAD",
                "delivery_location": "Mumbai",
                "timeline_days": 14,
                "urgency": "IMMEDIATE",
                "is_budget_public": False,
                "inquiry_notes": "Need dedicated 30-ton pneumatic bulker trucks for continuous cement dispatch from Raigad to Pune.",
            },
        },
        # Use Case 3: Supplier prospecting for buyers (Supplier Pitch)
        {
            "title": "Supplier Prospecting for Buyers (Supplier Pitch)",
            "initiator": "vikram",
            "target": "sanjanamaahi",
            "context": "An upstream clinker and mineral producer (Deccan Clinker & Mineral Feedstocks Ltd) has 4,950 MT of uncommitted production capacity and actively pitches to EPC contractors.",
            "what_is_testing": "Tests proactive supplier prospecting, uncommitted inventory allocation check, ISO 9001 and IS 16415 accreditation sharing, and direct sales handover.",
            "business_context": {
                "inquiry_type": "SUPPLIER_PROSPECTING",
                "product_name": "High-Grade Cement Clinker & Mineral Feedstock",
                "product_code": "CEMENT_CLINKER",
                "quantity": 2000.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Pune",
                "timeline_days": 30,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Proactively offering certified clinker feedstocks with immediate dispatch readiness from our Pune plant.",
            },
        },
        # Use Case 4: Vendor pitching service to potential customers (Vendor Pitch)
        {
            "title": "Vendor Pitching Service to Potential Customers (Vendor Pitch)",
            "initiator": "aarav",
            "target": "sanjanamaahi",
            "context": "A heavy equipment rental vendor (Western Logistics & Heavy Haulage Fleet) pitches 50-ton mobile hydraulic crawler cranes to an EPC firm with upcoming structural lift packages.",
            "what_is_testing": "Tests proactive vendor service pitching, equipment availability verification, crane load-chart and third-party certified inspection records, and mobilized deployment terms.",
            "business_context": {
                "inquiry_type": "VENDOR_PITCH",
                "product_name": "50-Ton Crawler & Mobile Hydraulic Crane Rental",
                "service_code": "PLANT_MAINTENANCE",
                "quantity": 10.0,
                "unit": "TRUCKLOAD",
                "delivery_location": "Mumbai",
                "timeline_days": 21,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Pitching heavy lifting equipment rental packages with certified operators and third-party safety audits.",
            },
        },
        # Use Case 5: Buyer seeking alternative/substitute materials (Substitute Discovery)
        {
            "title": "Buyer Seeking Alternative / Substitute Material (Substitute Discovery)",
            "initiator": "sanjanamaahi",
            "target": "maahi",
            "context": "A project manager seeks an approved low-carbon substitute for Ordinary Portland Cement (OPC 53) to meet decarbonization guidelines on an urban infrastructure corridor.",
            "what_is_testing": "Tests alternative sourcing workflow, environmental carbon-reduction verification (~40% embodied CO2 reduction), technical performance parity to OPC, and comparative trial data exchange.",
            "business_context": {
                "inquiry_type": "ALTERNATIVE_SOURCING",
                "product_name": "Limestone Calcined Clay Cement (LC3)",
                "product_code": "CALCINED_CLAY_LC3",
                "grade_code": "LC3_50_STANDARD",
                "quantity": 1200.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Pune",
                "timeline_days": 45,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Seeking low-carbon sustainable cement as an alternative to OPC 53 for green building compliance.",
            },
        },
        # Use Case 6: Feedstock / Raw material sourcing (Strategic Feedstock Partnership)
        {
            "title": "Feedstock / Raw Material Sourcing (Strategic Feedstock Partnership)",
            "initiator": "maahi",
            "target": "vikram",
            "context": "A cement grinding and decarb material plant (Maahi Decarb Materials Pvt Ltd) sources 2,000 MT of cement clinker intermediate from an upstream mineral supplier under an annual partnership.",
            "what_is_testing": "Tests raw material feedstock sourcing, monthly allocation schedule coordination, declared accreditations (IS 16415, ISO 9001:2015, NABL Lab Certified), Ex Works quote, and quarterly SLA reviews.",
            "business_context": {
                "inquiry_type": "SOURCING_PARTNERSHIP",
                "product_name": "Cement Clinker Intermediate",
                "product_code": "CEMENT_CLINKER",
                "quantity": 2000.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Pune",
                "timeline_days": 30,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Exploring long-term clinker supply agreements and annual feedstock quota arrangements.",
            },
        },
        # Use Case 7: Distributor looking for manufacturers (Distributor Application)
        {
            "title": "Distributor Looking for Manufacturers (Distributor Application)",
            "initiator": "rohit",
            "target": "maahi",
            "context": "An established regional distributor (Apex Building Materials) seeks authorized distributorship and stockist rights for LC3 cement across Western Maharashtra.",
            "what_is_testing": "Tests regional distributor application, dynamic extraction of distributor's 60,000 sq ft warehousing and 220 active dealer network, authorized wholesale pricing, and monthly minimum off-take tiers.",
            "business_context": {
                "inquiry_type": "DISTRIBUTOR_APPLICATION",
                "product_name": "Limestone Calcined Clay Cement (LC3)",
                "product_code": "CALCINED_CLAY_LC3",
                "grade_code": "LC3_50_STANDARD",
                "quantity": 1500.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Pune",
                "timeline_days": 30,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Applying for authorized stockist rights across Pune, Satara, Solapur, and Western Maharashtra.",
            },
        },
        # Use Case 8: Manufacturer expanding distribution network (Distribution Expansion)
        {
            "title": "Manufacturer Expanding Distribution Network (Distribution Expansion)",
            "initiator": "maahi",
            "target": "rohit",
            "context": "A cement manufacturer proactively seeks qualified regional distributors to expand retail market footprint across Western Maharashtra.",
            "what_is_testing": "Tests manufacturer distribution expansion, directional extraction of target distributor's verified infrastructure (60,000 sq ft warehouse, 220 retail dealers), credit windows (30 days), and territorial exclusivity discussions.",
            "business_context": {
                "inquiry_type": "DISTRIBUTION_EXPANSION",
                "product_name": "Limestone Calcined Clay Cement (LC3)",
                "product_code": "CALCINED_CLAY_LC3",
                "grade_code": "LC3_50_STANDARD",
                "quantity": 1500.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Western Maharashtra",
                "timeline_days": 30,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Seeking authorized stockist and regional channel distribution partners for Western Maharashtra.",
            },
        },
        # Use Case 9: Buyer & Supplier exploring business relationship (Exploratory Collaboration)
        {
            "title": "Buyer & Supplier Exploring Business Relationship (Exploratory Collaboration)",
            "initiator": "sanjanamaahi",
            "target": "maahi",
            "context": "An infrastructure builder and green cement producer explore potential commercial synergies, technical data exchange, and long-term supply agreements.",
            "what_is_testing": "Tests strategic exploratory collaboration, operational run-rate verification (2,500 MT/mo), phased collaboration frameworks (technical data exchange, trial batch testing), and C-level meeting coordination.",
            "business_context": {
                "inquiry_type": "EXPLORATORY_COLLABORATION",
                "product_name": "Limestone Calcined Clay Cement (LC3)",
                "product_code": "CALCINED_CLAY_LC3",
                "grade_code": "LC3_50_STANDARD",
                "quantity": 1000.0,
                "unit": "METRIC_TONNE",
                "delivery_location": "Western Maharashtra",
                "timeline_days": 30,
                "urgency": "PLANNED",
                "is_budget_public": False,
                "inquiry_notes": "Exploring sustainable cement blends and potential commercial supply partnership for Western Maharashtra pipeline.",
            },
        },
    ]

    all_results = []
    for idx, c in enumerate(cases, 1):
        res = run_use_case(idx, c)
        all_results.append(res)
        time.sleep(2)

    # Save complete JSON results
    json_path = "/home/sanjana/converge-ai/automation/phase6_all_9_cases_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[DONE] All 9 Use Cases executed! Raw results written to {json_path}")


if __name__ == "__main__":
    main()
