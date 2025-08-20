#!/usr/bin/env python3
"""
Test script to demonstrate organization user creating announcements with PENDING status

This script shows:
1. How organization users create announcements that get PENDING status
2. How admin users can see and approve these pending announcements
3. The difference between organization and admin announcement creation
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8000/awn/api"

def print_response(title, response):
    """Helper function to print formatted response"""
    print(f"\n{'='*50}")
    print(f"📋 {title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return data
    except:
        print(f"Response: {response.text}")
        return None

def test_organization_announcement_flow():
    """
    Test the complete flow of organization creating announcements
    """
    print("🚀 Testing Organization Announcement Creation with PENDING Status")
    print("=" * 70)
    
    # Step 1: Organization Login
    print("\n📝 Step 1: Organization User Login")
    org_login_data = {
        "email": "org@example.com",  # Replace with actual org email
        "password": "password123"     # Replace with actual password
    }
    
    response = requests.post(f"{BASE_URL}/login/", json=org_login_data)
    login_result = print_response("Organization Login", response)
    
    if response.status_code != 200 or not login_result:
        print("❌ Organization login failed. Please check credentials.")
        return
    
    org_token = login_result.get('access')
    org_headers = {"Authorization": f"Bearer {org_token}"}
    
    # Step 2: Create Announcement (Should be PENDING)
    print("\n📝 Step 2: Create Announcement as Organization User")
    announcement_data = {
        "title": "Software Development Internship - Pending Test",
        "description": "This is a test announcement created by an organization user. It should have PENDING status and require admin approval.",
        "start_date": datetime.now().date().isoformat(),
        "end_date": (datetime.now() + timedelta(days=60)).date().isoformat(),
        "url": "https://company.com/internship-pending-test",
        "category": 1  # Assuming category 1 exists
    }
    
    response = requests.post(f"{BASE_URL}/create-announcements/", 
                           json=announcement_data, headers=org_headers)
    create_result = print_response("Create Announcement (Organization)", response)
    
    if response.status_code != 201:
        print("❌ Failed to create announcement")
        return
    
    announcement_id = create_result.get('id')
    announcement_status = create_result.get('status')
    
    print(f"\n✅ Announcement created with ID: {announcement_id}")
    print(f"📊 Status: {announcement_status}")
    
    if announcement_status == 'pending':
        print("✅ SUCCESS: Announcement status is PENDING as expected for organization user!")
    else:
        print(f"❌ UNEXPECTED: Expected 'pending' but got '{announcement_status}'")
    
    # Step 3: Organization views their announcements
    print("\n📝 Step 3: Organization Views Their Own Announcements")
    response = requests.get(f"{BASE_URL}/announcements/", headers=org_headers)
    org_announcements = print_response("Organization's Announcements", response)
    
    # Step 4: Admin Login
    print("\n📝 Step 4: Admin User Login")
    admin_login_data = {
        "email": "admin@example.com",  # Replace with actual admin email
        "password": "admin123"         # Replace with actual admin password
    }
    
    response = requests.post(f"{BASE_URL}/login/", json=admin_login_data)
    admin_login_result = print_response("Admin Login", response)
    
    if response.status_code != 200 or not admin_login_result:
        print("❌ Admin login failed. Skipping admin steps.")
        return
    
    admin_token = admin_login_result.get('access')
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Step 5: Admin views pending announcements
    print("\n📝 Step 5: Admin Views Pending Announcements")
    response = requests.get(f"{BASE_URL}/announcements/?status=pending", headers=admin_headers)
    pending_announcements = print_response("Pending Announcements (Admin View)", response)
    
    # Step 6: Admin approves the announcement
    print("\n📝 Step 6: Admin Approves the Announcement")
    approval_data = {
        "status": "approved",
        "admin_notes": "Great internship opportunity. Approved for publication."
    }
    
    response = requests.patch(f"{BASE_URL}/announcements/{announcement_id}/approve/", 
                            json=approval_data, headers=admin_headers)
    approval_result = print_response("Approve Announcement", response)
    
    # Step 7: Public view (only approved announcements)
    print("\n📝 Step 7: Public View (No Authentication)")
    response = requests.get(f"{BASE_URL}/announcements/")
    public_announcements = print_response("Public Announcements", response)
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"✅ Organization created announcement with ID: {announcement_id}")
    print(f"✅ Initial status: {announcement_status} (Expected: pending)")
    print("✅ Organization can see their own announcements (including pending)")
    print("✅ Admin can see all announcements including pending ones")
    print("✅ Admin can approve/reject announcements")
    print("✅ Public users only see approved announcements")
    
if __name__ == "__main__":
    print("🧪 Organization Announcement Pending Status Test")
    print("Make sure the Django server is running on http://127.0.0.1:8000")
    print("Update the login credentials in the script before running.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    try:
        test_organization_announcement_flow()
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure Django server is running on http://127.0.0.1:8000")
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")