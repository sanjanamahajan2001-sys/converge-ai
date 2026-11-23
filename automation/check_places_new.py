#!/usr/bin/env python3
import httpx
import sys

def test_places_new(api_key: str, referer: str = None):
    print(f"\n--- Testing Places API (New) Text Search ---")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    if referer:
        headers["Referer"] = referer

    url = "https://places.googleapis.com/v1/places:searchText"
    body = {"textQuery": "Moscone Center San Francisco"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=headers, json=body)
        print("Status code:", resp.status_code)
        print("Response:", resp.text[:400])

if __name__ == "__main__":
    key = "AIzaSyA-OpPOD5SVC_RtW5tfx_E9m3BNGqqXIwY"
    ref = "https://192.46.210.48/"
    test_places_new(key, ref)
