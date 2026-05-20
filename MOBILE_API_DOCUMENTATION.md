# Church POS Mobile API Documentation

## Overview

This API provides endpoints for the Flutter POS mobile app to interact with the church management system. The API supports authentication, member management, payment processing, and offline synchronization.

## Base URL

```
http://localhost:8000/tithe/api/v1/
```

## Authentication

### Login with POS PIN

```http
POST /tithe/api/auth/login/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password",
  "pos_pin": "1234"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "roles": "admin"
  }
}
```

### Refresh Token

```http
POST /tithe/api/auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## API Endpoints

### 1. Dashboard Statistics

Get daily statistics and summary data for the POS dashboard.

```http
GET /tithe/api/v1/dashboard/stats/
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "today": {
      "total_amount": 150000.50,
      "payment_count": 25,
      "cash_amount": 100000.00,
      "bank_amount": 50000.50,
      "unique_payers": 20
    },
    "week": {
      "total_amount": 750000.00,
      "payment_count": 120
    },
    "stats": {
      "total_members": 500,
      "average_payment": 6000.02
    },
    "recent_payments": [...],
    "top_contributors": [...]
  }
}
```

### 2. Member Search

Search for members by name, code, or phone number.

```http
GET /tithe/api/v1/members/lookup/?search=john
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "id": 123,
      "name": "John Doe",
      "code": "001PT",
      "telephone": "+255123456789",
      "location": "Dar es Salaam",
      "community_name": "St. Peter's Community"
    }
  ]
}
```

### 3. Submit Payment

Create a new tithe payment and generate receipt.

```http
POST /tithe/api/v1/payments/submit/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "member_id": 123,
  "amount": 10000.00,
  "payment_method": "cash",
  "auto_print": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment submitted successfully",
  "payment": {
    "id": 456,
    "date": "2024-01-15T10:30:00Z",
    "member_name": "John Doe",
    "amount": "10000.00",
    "payment_method_display": "Cash"
  },
  "receipt": {
    "id": 789,
    "receipt_number": "TITH-20240115-0001",
    "member_name": "John Doe",
    "payment_amount": "10000.00"
  }
}
```

### 4. Recent Payments

Get the last 10 payments for dashboard display.

```http
GET /tithe/api/v1/payments/recent/
Authorization: Bearer {access_token}
```

### 5. Payment Details

Get full details of a specific payment including receipt.

```http
GET /tithe/api/v1/payments/{payment_id}/
Authorization: Bearer {access_token}
```

### 6. POS Settings

Get configuration settings for the mobile app.

```http
GET /tithe/api/v1/settings/pos/
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "church": {
      "name": "Christ The King Parish",
      "address": "123 Church Street",
      "phone": "+255123456789",
      "email": "church@example.com"
    },
    "pos": {
      "auto_generate_receipt": true,
      "auto_print_receipt": false,
      "default_payment_method": "cash",
      "receipt_width": 32,
      "currency_symbol": "Tsh",
      "decimal_places": 2
    },
    "app": {
      "app_version": "1.0.0",
      "api_version": "v1",
      "supported_languages": ["en", "sw"],
      "default_language": "en",
      "search_min_length": 3,
      "max_payment_amount": 1000000.0,
      "min_payment_amount": 100.0
    },
    "user": {
      "username": "admin",
      "role": "admin",
      "permissions": {
        "can_submit_payments": true,
        "can_print_receipts": true,
        "can_view_reports": true,
        "can_manage_members": true
      }
    },
    "features": {
      "offline_mode": true,
      "qr_scanning": true,
      "bluetooth_printing": true,
      "push_notifications": true
    }
  }
}
```

### 7. Bulk Member Sync

Sync member data for offline support with pagination and incremental updates.

```http
GET /tithe/api/v1/sync/members/?page=1&limit=100&since=2024-01-01T00:00:00Z
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 100, max: 500)
- `since`: ISO datetime for incremental sync (optional)
- `community`: Filter by community ID (optional)

**Response:**
```json
{
  "success": true,
  "data": {
    "members": [...],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "total_count": 500,
      "has_next": true,
      "has_previous": false
    },
    "sync_info": {
      "latest_timestamp": "2024-01-15T10:30:00Z",
      "items_in_sync": 100,
      "filters_applied": {
        "since": "2024-01-01T00:00:00Z",
        "community": null
      }
    }
  }
}
```

### 8. Device Registration

Register mobile device for push notifications and tracking.

```http
POST /tithe/api/v1/device/register/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "device_id": "unique_device_id_123",
  "device_type": "android",
  "push_token": "firebase_push_token",
  "device_name": "Samsung Galaxy S21",
  "app_version": "1.0.0"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device registered successfully",
  "device_id": "unique_device_id_123",
  "is_new": true
}
```

### 9. Offline Operations Sync

Sync operations performed while offline.

```http
POST /tithe/api/v1/sync/offline/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "device_id": "unique_device_id_123",
  "operations": [
    {
      "operation_type": "create_payment",
      "data": {
        "member_id": 123,
        "amount": 10000.00,
        "payment_method": "cash"
      },
      "client_timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Sync completed: 1/1 operations processed",
  "sync_id": 456,
  "results": [
    {
      "success": true,
      "operation_type": "create_payment",
      "payment_id": 789
    }
  ]
}
```

### 10. Print Receipt

Mark a receipt as printed after successful printing.

```http
POST /tithe/api/v1/receipts/{receipt_id}/print/
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Receipt marked as printed",
  "receipt_number": "TITH-20240115-0001"
}
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error message",
  "details": {
    "field_name": ["Validation error details"]
  }
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## Authentication Headers

All protected endpoints require:

```
Authorization: Bearer {access_token}
```

## Rate Limiting

- Search endpoints: 100 requests per minute
- Payment endpoints: 50 requests per minute
- Sync endpoints: 20 requests per minute

## Data Formats

### Date/Time
All datetime fields use ISO 8601 format: `2024-01-15T10:30:00Z`

### Currency
All amounts use decimal format with 2 places: `10000.50`

### Phone Numbers
Use international format with country code: `+255123456789`

## Testing

Use the provided Postman collection or test with curl:

```bash
# Test login
curl -X POST http://localhost:8000/tithe/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password","pos_pin":"1234"}'

# Test member search
curl -X GET "http://localhost:8000/tithe/api/v1/members/lookup/?search=john" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Offline Support

The API supports offline operations through:

1. **Bulk Sync**: Download member data for offline use
2. **Operation Queue**: Store operations performed offline
3. **Conflict Resolution**: Handle data conflicts when syncing
4. **Incremental Updates**: Only sync changed data

## Security Notes

- All endpoints require authentication
- POS PIN validation for login
- Role-based permissions
- HTTPS recommended for production
- Input validation and sanitization
- SQL injection protection through Django ORM

## Mobile App Integration

For Flutter integration:

1. Use `dio` or `http` package for API calls
2. Implement JWT token refresh logic
3. Store tokens securely using `flutter_secure_storage`
4. Handle offline scenarios with local database
5. Implement retry logic for failed requests
6. Use proper error handling and user feedback

## Support

For API issues or questions, contact the development team or check the Django admin for detailed logs.
