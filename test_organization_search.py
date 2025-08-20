#!/usr/bin/env python
"""
Test script to demonstrate the new Organization Search and Selection functionality.
This script shows how administrators can:
1. Search for existing organizations
2. Create announcements linked to existing organizations
3. Create announcements with custom organization names
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8000/awn/api"
ADMIN_CREDENTIALS = {
    "email": "admin@example.com",  # Replace with actual admin credentials
    "password": "admin123"  # Replace with actual admin password
}

def get_admin_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/auth/login/", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        return response.json()["access"]
    else:
        print(f"Failed to login: {response.text}")
        return None

def search_organizations(token, query):
    """Search for organizations by name"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/organizations/search/", 
                          params={"q": query}, headers=headers)
    return response.json()

def create_announcement_with_existing_org(token, org_id):
    """Create announcement linked to existing organization"""
    headers = {"Authorization": f"Bearer {token}"}
    
    announcement_data = {
        "title": "Test Announcement with Existing Organization",
        "description": "This announcement is linked to an existing organization.",
        "start_date": datetime.now().date().isoformat(),
        "end_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
        "url": "https://example.com/announcement",
        "category": 1,  # Assuming category with ID 1 exists
        "organization_id": org_id  # Link to existing organization
    }
    
    response = requests.post(f"{BASE_URL}/create-announcements/", 
                           json=announcement_data, headers=headers)
    return response.json()

def create_announcement_with_custom_name(token, custom_name):
    """Create announcement with custom organization name"""
    headers = {"Authorization": f"Bearer {token}"}
    
    announcement_data = {
        "title": "Test Announcement with Custom Organization Name",
        "description": "This announcement uses a custom organization name.",
        "start_date": datetime.now().date().isoformat(),
        "end_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
        "url": "https://example.com/announcement2",
        "category": 1,  # Assuming category with ID 1 exists
        "organization_name": custom_name  # Custom organization name
    }
    
    response = requests.post(f"{BASE_URL}/create-announcements/", 
                           json=announcement_data, headers=headers)
    return response.json()

def main():
    """Main test function"""
    print("=== Organization Search and Selection Test ===")
    
    # Get admin token
    print("\n1. Getting admin authentication token...")
    token = get_admin_token()
    if not token:
        print("Failed to get admin token. Please check credentials.")
        return
    print("✓ Admin token obtained successfully")
    
    # Test organization search
    print("\n2. Testing organization search...")
    search_query = "test"  # Search for organizations containing "test"
    search_results = search_organizations(token, search_query)
    print(f"Search results for '{search_query}':")
    print(json.dumps(search_results, indent=2))
    
    # Test creating announcement with existing organization (if any found)
    if search_results.get('success') and search_results.get('data'):
        print("\n3. Testing announcement creation with existing organization...")
        first_org = search_results['data'][0]
        org_id = first_org['id']
        print(f"Using organization: {first_org['name']} (ID: {org_id})")
        
        result = create_announcement_with_existing_org(token, org_id)
        print("Result:")
        print(json.dumps(result, indent=2))
    else:
        print("\n3. No organizations found for testing existing organization link.")
    
    # Test creating announcement with custom organization name
    print("\n4. Testing announcement creation with custom organization name...")
    custom_name = "Custom Organization Name for Testing"
    result = create_announcement_with_custom_name(token, custom_name)
    print(f"Using custom organization name: {custom_name}")
    print("Result:")
    print(json.dumps(result, indent=2))
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    main()