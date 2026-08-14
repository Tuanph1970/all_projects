#!/usr/bin/env python3
"""
Quick test script to verify cart system is working after fix
"""

import requests
import json

BASE_URL = "http://localhost:8002/api/v1"

def test_cart_system():
    print("=" * 80)
    print("CART SYSTEM FIX VERIFICATION TEST")
    print("=" * 80)

    # Step 1: Register a test user
    print("\n1. Registering test user...")
    register_data = {
        "email": f"carttest@example.com",
        "username": "carttest_user",
        "password": "Test123!@#",
        "full_name": "Cart Test User",
        "phone_number": "+1234567890",
        "role": "customer"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code in [200, 201]:
        print("✓ User registered successfully")
    else:
        print(f"✗ Registration failed: {response.status_code}")
        print(response.text)
        return False

    # Step 2: Login
    print("\n2. Logging in...")
    login_data = {
        "username": "carttest_user",
        "password": "Test123!@#"
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        print("✓ Login successful")
    else:
        print(f"✗ Login failed: {response.status_code}")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Test GET cart (this was causing 500 error)
    print("\n3. Testing GET cart endpoint (was causing 500 error)...")
    response = requests.get(f"{BASE_URL}/cart/", headers=headers)
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        print("✓ GET cart endpoint working!")
        cart_data = response.json()
        print(f"   Cart ID: {cart_data['id']}")
        print(f"   Items: {len(cart_data['items'])}")
        print(f"   Item count: {cart_data['summary']['item_count']}")
    else:
        print(f"✗ GET cart failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    # Step 4: Test cart count
    print("\n4. Testing cart count endpoint...")
    response = requests.get(f"{BASE_URL}/cart/count", headers=headers)
    if response.status_code == 200:
        print("✓ Cart count endpoint working!")
        print(f"   {response.json()}")
    else:
        print(f"✗ Cart count failed: {response.status_code}")

    print("\n" + "=" * 80)
    print("CART SYSTEM FIX VERIFICATION: SUCCESS")
    print("=" * 80)
    return True

if __name__ == "__main__":
    try:
        test_cart_system()
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
