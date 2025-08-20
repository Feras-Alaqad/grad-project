# Organization Search and Selection Implementation Guide

This guide explains how to implement and use the new Organization Search and Selection functionality for announcement creation.

## Overview

The implementation provides administrators with the ability to:
1. **Search for existing organizations** by name
2. **Link announcements to existing organizations** (maintaining data consistency)
3. **Use custom organization names** when the organization is not registered

## API Endpoints

### 1. Organization Search Endpoint

**Endpoint:** `GET /awn/api/organizations/search/`

**Access:** Admin users only

**Parameters:**
- `q` (required): Search query string

**Example Request:**
```bash
GET /awn/api/organizations/search/?q=university
Authorization: Bearer <admin_token>
```

**Example Response:**
```json
{
  "success": true,
  "message": "Organizations found",
  "data": [
    {
      "id": 1,
      "name": "University of Technology",
      "email": "contact@university.edu"
    },
    {
      "id": 2,
      "name": "State University",
      "email": "info@stateuni.edu"
    }
  ]
}
```

### 2. Enhanced Announcement Creation

**Endpoint:** `POST /awn/api/create-announcements/`

**New Fields:**
- `organization_id` (optional): ID of existing organization to link
- `organization_name` (optional): Custom organization name

**Important Rules:**
- Cannot specify both `organization_id` and `organization_name`
- If `organization_id` is provided, the announcement will be linked to that organization
- If `organization_name` is provided, it will be stored as text (no link)
- If neither is provided, no organization will be associated

## Usage Examples

### Option 1: Link to Existing Organization

```json
{
  "title": "Software Development Internship",
  "description": "Join our development team...",
  "start_date": "2024-01-15",
  "end_date": "2024-06-15",
  "url": "https://company.com/internship",
  "category": 1,
  "organization_id": 5
}
```

### Option 2: Use Custom Organization Name

```json
{
  "title": "Research Opportunity",
  "description": "Exciting research position...",
  "start_date": "2024-02-01",
  "end_date": "2024-08-01",
  "url": "https://research.org/opportunity",
  "category": 2,
  "organization_name": "International Research Institute"
}
```

### Option 3: No Organization

```json
{
  "title": "General Announcement",
  "description": "This is a general announcement...",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "url": "https://example.com",
  "category": 3
}
```

## Frontend Implementation Guide

### 1. Organization Search Component

Create a search component that allows administrators to search for organizations:

```javascript
// Example React component
const OrganizationSearch = ({ onSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const searchOrganizations = async (searchQuery) => {
    if (searchQuery.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `/awn/api/organizations/search/?q=${encodeURIComponent(searchQuery)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      if (data.success) {
        setResults(data.data);
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Search organizations..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          searchOrganizations(e.target.value);
        }}
      />
      {loading && <div>Searching...</div>}
      {results.map((org) => (
        <div key={org.id} onClick={() => onSelect(org)}>
          <strong>{org.name}</strong>
          <br />
          <small>{org.email}</small>
        </div>
      ))}
    </div>
  );
};
```

### 2. Announcement Form Enhancement

```javascript
const AnnouncementForm = () => {
  const [selectedOrganization, setSelectedOrganization] = useState(null);
  const [customOrgName, setCustomOrgName] = useState('');
  const [useCustomName, setUseCustomName] = useState(false);

  const handleSubmit = (formData) => {
    const announcementData = {
      ...formData,
      ...(selectedOrganization && !useCustomName 
        ? { organization_id: selectedOrganization.id }
        : { organization_name: customOrgName }
      )
    };

    // Submit announcement
    submitAnnouncement(announcementData);
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Other form fields */}
      
      <div>
        <h3>Organization</h3>
        
        <label>
          <input
            type="radio"
            checked={!useCustomName}
            onChange={() => setUseCustomName(false)}
          />
          Select existing organization
        </label>
        
        {!useCustomName && (
          <OrganizationSearch onSelect={setSelectedOrganization} />
        )}
        
        {selectedOrganization && !useCustomName && (
          <div>
            Selected: <strong>{selectedOrganization.name}</strong>
            <button onClick={() => setSelectedOrganization(null)}>Clear</button>
          </div>
        )}
        
        <label>
          <input
            type="radio"
            checked={useCustomName}
            onChange={() => setUseCustomName(true)}
          />
          Use custom organization name
        </label>
        
        {useCustomName && (
          <input
            type="text"
            placeholder="Enter organization name"
            value={customOrgName}
            onChange={(e) => setCustomOrgName(e.target.value)}
          />
        )}
      </div>
      
      <button type="submit">Create Announcement</button>
    </form>
  );
};
```

## Benefits

1. **Data Consistency**: Announcements can be properly linked to registered organizations
2. **Flexibility**: Administrators can still use custom names for unregistered organizations
3. **Better UX**: Search functionality makes it easy to find and select organizations
4. **Relationship Integrity**: Maintains proper foreign key relationships in the database
5. **Reporting**: Enables better analytics and reporting on organization-specific announcements

## Error Handling

### Common Validation Errors

1. **Both organization_id and organization_name provided:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "organization": ["Cannot specify both organization_id and organization_name. Choose one."]
  }
}
```

2. **Invalid organization_id:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "organization_id": ["Organization with this ID does not exist."]
  }
}
```

3. **Missing search query:**
```json
{
  "success": false,
  "message": "Search query parameter 'q' is required"
}
```

## Testing

Use the provided test script `test_organization_search.py` to test the functionality:

```bash
python test_organization_search.py
```

Make sure to update the admin credentials in the script before running.

## Migration Notes

No database migrations are required for this implementation as it uses existing model fields and relationships.

## Security Considerations

- Organization search is restricted to admin users only
- Input validation prevents injection attacks
- Proper authentication and authorization checks are in place
- Search results are limited to prevent performance issues