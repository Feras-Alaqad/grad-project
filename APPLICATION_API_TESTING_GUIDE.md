# Application API Testing Guide

This guide explains how to test the Application API endpoints that manage the relationship between users and announcements.

## Overview

The Application API provides endpoints for:
- Creating applications to announcements
- Listing applications (with different views for users, organizations, and admins)
- Approving/rejecting applications
- Managing application status

## Prerequisites

1. **Server Running**: Ensure your Django server is running on `http://localhost:8000`
2. **Test Data**: You'll need:
   - A regular user account
   - An organization account
   - An admin account
   - At least one approved announcement

## API Endpoints

### Base URL: `http://localhost:8000/api`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/applications/` | List applications | Authenticated |
| POST | `/applications/` | Create application | Authenticated |
| GET | `/applications/{id}/` | Get application details | Authenticated |
| PUT/PATCH | `/applications/{id}/` | Update application | Admin/Org only |
| DELETE | `/applications/{id}/` | Delete application | User/Admin only |
| GET | `/applications/my-applications/` | User's applications | User only |
| GET | `/applications/pending/` | Pending applications | Admin/Org only |
| PATCH | `/applications/{id}/approve/` | Approve application | Admin/Org only |
| PATCH | `/applications/{id}/reject/` | Reject application | Admin/Org only |

## Testing Steps

### Step 1: Setup Test Accounts

#### 1.1 Create Regular User
```http
POST /api/auth/signup/user/
Content-Type: application/json

{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "TestPass123!",
  "first_name": "Test",
  "last_name": "User"
}
```

#### 1.2 Create Organization
```http
POST /api/auth/signup/organization/
Content-Type: application/json

{
  "username": "testorg",
  "email": "testorg@example.com",
  "password": "TestPass123!",
  "organization_name": "Test Organization",
  "organization_type": "NGO",
  "contact_person": "John Doe",
  "phone_number": "+1234567890",
  "address": "123 Test Street",
  "description": "Test organization"
}
```

### Step 2: Login and Get Tokens

#### 2.1 Login User
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "testuser",
  "password": "TestPass123!"
}
```

#### 2.2 Login Organization
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "testorg",
  "password": "TestPass123!"
}
```

#### 2.3 Login Admin
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Save the `access` tokens from responses for authorization headers.**

### Step 3: Create and Approve Announcement

#### 3.1 Create Announcement (Organization)
```http
POST /api/create-announcements/
Authorization: Bearer {org_token}
Content-Type: application/json

{
  "title": "Test Announcement",
  "description": "Test announcement for applications",
  "category": 1,
  "start_date": "2024-02-01",
  "end_date": "2024-02-28",
  "location": "Test Location",
  "max_participants": 50
}
```

#### 3.2 Approve Announcement (Admin)
```http
PATCH /api/announcements/{announcement_id}/approve/
Authorization: Bearer {admin_token}
Content-Type: application/json
```

### Step 4: Test Application Creation

#### 4.1 Create Application (User)
```http
POST /api/applications/
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "announcement": {announcement_id}
}
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Application created successfully",
  "data": {
    "id": 1,
    "announcement": {announcement_id},
    "status": "pending",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
}
```

#### 4.2 Test Duplicate Application (Should Fail)
```http
POST /api/applications/
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "announcement": {announcement_id}
}
```

**Expected Response:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "non_field_errors": ["You have already applied to this announcement."]
  }
}
```

### Step 5: Test Application Listing

#### 5.1 User's Applications
```http
GET /api/applications/my-applications/
Authorization: Bearer {user_token}
```

#### 5.2 Organization's Applications
```http
GET /api/applications/
Authorization: Bearer {org_token}
```

#### 5.3 Admin View All Applications
```http
GET /api/applications/
Authorization: Bearer {admin_token}
```

#### 5.4 Pending Applications
```http
GET /api/applications/pending/
Authorization: Bearer {org_token}
```

### Step 6: Test Application Management

#### 6.1 Get Application Details
```http
GET /api/applications/{application_id}/
Authorization: Bearer {org_token}
```

#### 6.2 Approve Application
```http
PATCH /api/applications/{application_id}/approve/
Authorization: Bearer {org_token}
Content-Type: application/json
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Application approved successfully",
  "data": {
    "id": 1,
    "status": "approved",
    "announcement": {
      "id": 1,
      "title": "Test Announcement"
    },
    "user": {
      "id": 1,
      "username": "testuser"
    }
  }
}
```

#### 6.3 Reject Application
```http
PATCH /api/applications/{application_id}/reject/
Authorization: Bearer {org_token}
Content-Type: application/json

{
  "admin_notes": "Application rejected due to insufficient qualifications"
}
```

### Step 7: Test Filtering and Searching

#### 7.1 Filter by Status
```http
GET /api/applications/?status=approved
Authorization: Bearer {admin_token}
```

#### 7.2 Filter by Organization
```http
GET /api/applications/?announcement__organization={org_id}
Authorization: Bearer {admin_token}
```

#### 7.3 Search Applications
```http
GET /api/applications/?search=Test Announcement
Authorization: Bearer {admin_token}
```

#### 7.4 Order by Date
```http
GET /api/applications/?ordering=-created_at
Authorization: Bearer {admin_token}
```

## Testing with Postman

### Setting Up Postman Collection

1. **Create Environment Variables:**
   - `base_url`: `http://localhost:8000/api`
   - `user_token`: (set after login)
   - `org_token`: (set after login)
   - `admin_token`: (set after login)
   - `announcement_id`: (set after creating announcement)
   - `application_id`: (set after creating application)

2. **Authorization Setup:**
   - Use Bearer Token type
   - Token: `{{user_token}}` (or appropriate token variable)

3. **Test Scripts:**
   Add to login requests to save tokens:
   ```javascript
   if (pm.response.code === 200) {
       const response = pm.response.json();
       pm.environment.set("user_token", response.access);
   }
   ```

## Expected Behaviors

### Permission Matrix

| Action | Regular User | Organization | Admin |
|--------|-------------|-------------|-------|
| Create Application | ✅ (own) | ❌ | ❌ |
| View Own Applications | ✅ | ❌ | ✅ (all) |
| View Org Applications | ❌ | ✅ (own org) | ✅ (all) |
| Approve/Reject | ❌ | ✅ (own org) | ✅ (all) |
| Delete Application | ✅ (own) | ❌ | ✅ (all) |
| Update Application Status | ❌ | ✅ (own org) | ✅ (all) |

### Status Flow

1. **PENDING** → User creates application
2. **APPROVED** → Organization/Admin approves
3. **REJECTED** → Organization/Admin rejects

### Validation Rules

- Users can only apply to **approved** announcements
- Users cannot apply to the same announcement twice
- Applications automatically start with **PENDING** status
- Only announcement owners and admins can approve/reject
- Users can only delete their own applications

## Common Test Scenarios

### Positive Tests
- ✅ User creates application to approved announcement
- ✅ Organization approves application
- ✅ Admin views all applications
- ✅ User views own applications
- ✅ Filtering and searching works

### Negative Tests
- ❌ User applies to same announcement twice
- ❌ User applies to pending/rejected announcement
- ❌ User tries to approve application
- ❌ Organization tries to approve other org's application
- ❌ Unauthenticated access

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check authentication token and permissions
2. **400 Bad Request**: Validate request payload format
3. **404 Not Found**: Ensure announcement/application exists
4. **500 Server Error**: Check server logs for database issues

### Debug Tips

1. Check Django admin panel for data verification
2. Use Django shell for direct model queries
3. Enable DEBUG=True for detailed error messages
4. Check server logs for permission errors

This comprehensive testing approach ensures all Application API functionality works correctly across different user roles and scenarios.