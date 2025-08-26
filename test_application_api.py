#!/usr/bin/env python
"""
Comprehensive test script for Application API endpoints.
Tests the complete application workflow including creation, listing, approval/rejection.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000/api"
HEADERS = {"Content-Type": "application/json"}

# Test data
TEST_USER = {
    "username": "testuser_app",
    "email": "testuser_app@example.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User"
}

TEST_ORG = {
    "username": "testorg_app",
    "email": "testorg_app@example.com",
    "password": "TestPass123!",
    "organization_name": "Test Organization for Apps",
    "organization_type": "NGO",
    "contact_person": "John Doe",
    "phone_number": "+1234567890",
    "address": "123 Test Street",
    "description": "Test organization for application testing"
}

TEST_ADMIN = {
    "username": "admin",
    "password": "admin123"
}

def print_response(response, title):
    """Helper function to print formatted response"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'='*50}")

def signup_user(user_data, endpoint):
    """Helper function to sign up a user"""
    response = requests.post(f"{BASE_URL}/auth/signup/{endpoint}/", 
                           json=user_data, headers=HEADERS)
    return response

def login_user(username, password):
    """Helper function to login and get token"""
    login_data = {"username": username, "password": password}
    response = requests.post(f"{BASE_URL}/auth/login/", 
                           json=login_data, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get('access')
    return None

def get_auth_headers(token):
    """Helper function to get authorization headers"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

def create_test_announcement(org_token):
    """Helper function to create a test announcement"""
    announcement_data = {
        "title": "Test Announcement for Applications",
        "description": "This is a test announcement for application testing",
        "category": 1,  # Assuming category 1 exists
        "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "location": "Test Location",
        "max_participants": 50
    }
    
    response = requests.post(f"{BASE_URL}/create-announcements/",
                           json=announcement_data,
                           headers=get_auth_headers(org_token))
    return response

def main():
    print("Starting Application API Testing...")
    
    # Step 1: Sign up test users
    print("\n1. Signing up test users...")
    
    # Sign up regular user
    user_signup = signup_user(TEST_USER, "user")
    print_response(user_signup, "User Signup")
    
    # Sign up organization
    org_signup = signup_user(TEST_ORG, "organization")
    print_response(org_signup, "Organization Signup")
    
    # Step 2: Login users
    print("\n2. Logging in users...")
    
    user_token = login_user(TEST_USER["username"], TEST_USER["password"])
    org_token = login_user(TEST_ORG["username"], TEST_ORG["password"])
    admin_token = login_user(TEST_ADMIN["username"], TEST_ADMIN["password"])
    
    if not user_token:
        print("Failed to login user")
        return
    if not org_token:
        print("Failed to login organization")
        return
    if not admin_token:
        print("Failed to login admin")
        return
    
    print("All users logged in successfully!")
    
    # Step 3: Create test announcement (by organization)
    print("\n3. Creating test announcement...")
    announcement_response = create_test_announcement(org_token)
    print_response(announcement_response, "Create Announcement")
    
    if announcement_response.status_code not in [200, 201]:
        print("Failed to create announcement")
        return
    
    announcement_id = announcement_response.json().get('data', {}).get('id')
    if not announcement_id:
        print("Could not get announcement ID")
        return
    
    # Step 4: Approve announcement (by admin)
    print("\n4. Approving announcement...")
    approve_response = requests.patch(f"{BASE_URL}/announcements/{announcement_id}/approve/",
                                    headers=get_auth_headers(admin_token))
    print_response(approve_response, "Approve Announcement")
    
    # Step 5: Create application (by user)
    print("\n5. Creating application...")
    application_data = {
        "announcement": announcement_id
    }
    
    create_app_response = requests.post(f"{BASE_URL}/applications/",
                                      json=application_data,
                                      headers=get_auth_headers(user_token))
    print_response(create_app_response, "Create Application")
    
    if create_app_response.status_code not in [200, 201]:
        print("Failed to create application")
        return
    
    application_id = create_app_response.json().get('data', {}).get('id')
    
    # Step 6: Test duplicate application (should fail)
    print("\n6. Testing duplicate application (should fail)...")
    duplicate_response = requests.post(f"{BASE_URL}/applications/",
                                     json=application_data,
                                     headers=get_auth_headers(user_token))
    print_response(duplicate_response, "Duplicate Application (Should Fail)")
    
    # Step 7: List user's applications
    print("\n7. Listing user's applications...")
    user_apps_response = requests.get(f"{BASE_URL}/applications/my-applications/",
                                    headers=get_auth_headers(user_token))
    print_response(user_apps_response, "User's Applications")
    
    # Step 8: List all applications (by organization)
    print("\n8. Listing applications (organization view)...")
    org_apps_response = requests.get(f"{BASE_URL}/applications/",
                                   headers=get_auth_headers(org_token))
    print_response(org_apps_response, "Organization's Applications")
    
    # Step 9: List pending applications (by organization)
    print("\n9. Listing pending applications...")
    pending_response = requests.get(f"{BASE_URL}/applications/pending/",
                                  headers=get_auth_headers(org_token))
    print_response(pending_response, "Pending Applications")
    
    # Step 10: Get application details
    print("\n10. Getting application details...")
    if application_id:
        detail_response = requests.get(f"{BASE_URL}/applications/{application_id}/",
                                     headers=get_auth_headers(org_token))
        print_response(detail_response, "Application Details")
    
    # Step 11: Approve application (by organization)
    print("\n11. Approving application...")
    if application_id:
        approve_app_response = requests.patch(f"{BASE_URL}/applications/{application_id}/approve/",
                                            headers=get_auth_headers(org_token))
        print_response(approve_app_response, "Approve Application")
    
    # Step 12: Create another application for rejection test
    print("\n12. Creating another application for rejection test...")
    
    # First create another user
    test_user_2 = {
        "username": "testuser2_app",
        "email": "testuser2_app@example.com",
        "password": "TestPass123!",
        "first_name": "Test2",
        "last_name": "User2"
    }
    
    user2_signup = signup_user(test_user_2, "user")
    user2_token = login_user(test_user_2["username"], test_user_2["password"])
    
    if user2_token:
        create_app2_response = requests.post(f"{BASE_URL}/applications/",
                                           json=application_data,
                                           headers=get_auth_headers(user2_token))
        print_response(create_app2_response, "Create Second Application")
        
        application2_id = create_app2_response.json().get('data', {}).get('id')
        
        # Step 13: Reject application (by organization)
        print("\n13. Rejecting application...")
        if application2_id:
            reject_data = {
                "admin_notes": "Application rejected for testing purposes"
            }
            reject_response = requests.patch(f"{BASE_URL}/applications/{application2_id}/reject/",
                                           json=reject_data,
                                           headers=get_auth_headers(org_token))
            print_response(reject_response, "Reject Application")
    
    # Step 14: Admin view all applications
    print("\n14. Admin viewing all applications...")
    admin_apps_response = requests.get(f"{BASE_URL}/applications/",
                                     headers=get_auth_headers(admin_token))
    print_response(admin_apps_response, "Admin View All Applications")
    
    # Step 15: Test filtering and searching
    print("\n15. Testing filtering and searching...")
    
    # Filter by status
    filter_response = requests.get(f"{BASE_URL}/applications/?status=approved",
                                 headers=get_auth_headers(admin_token))
    print_response(filter_response, "Filter by Status (Approved)")
    
    # Search by announcement title
    search_response = requests.get(f"{BASE_URL}/applications/?search=Test Announcement",
                                 headers=get_auth_headers(admin_token))
    print_response(search_response, "Search Applications")
    
    print("\n" + "="*50)
    print("Application API Testing Completed!")
    print("="*50)

if __name__ == "__main__":
    main()