#!/usr/bin/env python3
"""Check Google Maps Platform API key access and permissions.

Tests:
1. Maps JavaScript API (Bootstrap JS loading with key)
2. Geocoding API (Address / LatLng lookup)
3. Places API (Places text search & autocomplete)
"""

import httpx
import sys

def test_api_key(api_key: str, referer: str = None):
    print(f"=== Testing Google Maps API Key ===")
    print(f"Key: {api_key[:8]}...{api_key[-4:]}")
    if referer:
        print(f"Using HTTP Referer: {referer}")
    
    headers = {}
    if referer:
        headers["Referer"] = referer

    with httpx.Client(timeout=10.0, headers=headers) as client:
        # 1. Test Maps JavaScript API bootstrap
        print("\n--- 1. Testing Maps JavaScript API ---")
        js_url = f"https://maps.googleapis.com/maps/api/js?key={api_key}"
        resp_js = client.get(js_url)
        print(f"Maps JS Status: {resp_js.status_code}")
        if resp_js.status_code == 200:
            if "Google Maps JavaScript API error" in resp_js.text:
                print("Maps JS Error in payload:", resp_js.text[:300])
            else:
                print("✓ Maps JavaScript API: ACCESSIBLE (Script loaded successfully)")
        else:
            print(f"✗ Maps JavaScript API failed: {resp_js.status_code} {resp_js.text[:200]}")

        # 2. Test Geocoding API
        print("\n--- 2. Testing Geocoding API ---")
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address=San+Francisco&key={api_key}"
        resp_geo = client.get(geo_url)
        geo_data = resp_geo.json()
        print(f"Geocoding Status: {geo_data.get('status')}")
        if geo_data.get("status") == "OK":
            formatted_addr = geo_data['results'][0]['formatted_address']
            location = geo_data['results'][0]['geometry']['location']
            print(f"✓ Geocoding API: ACCESSIBLE. Result: {formatted_addr} -> {location}")
        else:
            print(f"✗ Geocoding API Response: {geo_data.get('status')} - {geo_data.get('error_message')}")

        # 3. Test Places API (New Text Search or Legacy)
        print("\n--- 3. Testing Places API ---")
        places_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=coffee+near+moscone+center&key={api_key}"
        resp_places = client.get(places_url)
        places_data = resp_places.json()
        print(f"Places Status: {places_data.get('status')}")
        if places_data.get("status") == "OK":
            first_place = places_data['results'][0]['name']
            first_addr = places_data['results'][0]['formatted_address']
            print(f"✓ Places API: ACCESSIBLE. Result: {first_place} ({first_addr})")
        else:
            print(f"✗ Places API Response: {places_data.get('status')} - {places_data.get('error_message')}")

if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "AIzaSyA-OpPOD5SVC_RtW5tfx_E9m3BNGqqXIwY"
    ref = sys.argv[2] if len(sys.argv) > 2 else "https://192.46.210.48/"
    test_api_key(key, referer=ref)
