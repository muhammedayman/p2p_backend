# Backend Changes Summary - Secret Code Authentication

## Files Modified

### 1. core_app/models.py
**Changes:**
- Added imports: `import secrets`, `import json`
- Added new model: `AuthenticationCode`
  - Stores unique secret codes generated during registration
  - Contains user data (name, phone, email) in JSON field
  - Tracks creation time and last usage
  - Includes static method `generate_code()` for creating unique tokens

**Database Table:** `authentication_codes`

### 2. core_app/views.py
**Changes:**
- Added import: `from .models import AuthenticationCode`
- **Modified RegisterView**: 
  - Now generates and returns `secret_code` in response
  - Creates AuthenticationCode record during registration
  - Returns both OTP code and secret code to client
  
- **Added LoginWithSecretCodeView** (new endpoint):
  - POST `/api/login-with-code/`
  - Accepts secret code and verifies it
  - Returns user details on successful verification
  - Updates last_used timestamp and last_seen
  - Returns 401 if code is invalid or inactive
  
- **Added VerifySecretCodeView** (new endpoint):
  - GET `/api/verify-code/?secret_code=<code>`
  - Checks if secret code exists and is active
  - Used for pre-login validation

### 3. core_app/serializers.py
**Changes:**
- Added new serializer: `AuthenticationCodeSerializer`
  - Serializes authentication code with user details
  - Returns user info from stored JSON data
  
- Added new serializer: `UserDetailSerializer`
  - Returns full user details after authentication
  - Includes online status calculation

### 4. core_app/urls.py
**Changes:**
- Added imports for new views: `LoginWithSecretCodeView`, `VerifySecretCodeView`
- Added two new URL patterns:
  - `path('login-with-code/', LoginWithSecretCodeView.as_view())`
  - `path('verify-code/', VerifySecretCodeView.as_view())`

## API Endpoints

### Register (Modified)
**POST** `/api/register/`

**Request:**
```json
{
  "name": "John Doe",
  "phone": "+919876543210",
  "email": "john@example.com",
  "photo": "base64_or_url",
  "is_photo_public": false
}
```

**Response (NEW - includes secret_code):**
```json
{
  "status": "pending_verification",
  "message": "Please send SMS '1234' to +917012710457",
  "otp_code": "1234",
  "target_number": "+917012710457",
  "secret_code": "a1b2c3d4e5f6g7h8...",
  "secret_code_message": "Save this code in your app for automatic login next time"
}
```

### Login with Secret Code (NEW)
**POST** `/api/login-with-code/`

**Request:**
```json
{
  "secret_code": "a1b2c3d4e5f6g7h8..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "user": {
    "id": 1,
    "name": "John Doe",
    "phone": "+919876543210",
    "email": "john@example.com",
    "photo": "base64_or_url",
    "is_photo_public": false,
    "is_phone_verified": true,
    "is_email_verified": false,
    "is_online": false
  },
  "message": "Welcome back, John Doe!"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": "Invalid or inactive secret code"
}
```

### Verify Secret Code (NEW)
**GET** `/api/verify-code/?secret_code=<code>`

**Response:**
```json
{
  "is_valid": true,
  "secret_code": "a1b2c3d4e5f6..."
}
```

## Database Migration

A migration file was automatically created:
- **0002_authenticationcode.py** - Creates the authentication_codes table

To apply the migration:
```bash
python manage.py migrate
```

## Authentication Flow

### First Time Registration:
1. User submits name, phone, email
2. Server creates ProfileUser record
3. Server generates unique `secret_code` using `secrets.token_urlsafe(48)`
4. Server returns both `otp_code` (for SMS) and `secret_code`
5. App saves `secret_code` to local storage (SharedPreferences)
6. User verifies phone via SMS OTP

### Returning User (Auto-Login):
1. App launches and checks if `secret_code` exists locally
2. If found, app sends it to `/api/login-with-code/`
3. Server verifies the code exists and is active
4. Server returns user details
5. App skips registration form entirely
6. User is immediately logged in

## Security Features

1. **Unique tokens:** Uses `secrets.token_urlsafe()` for cryptographically secure random generation
2. **Server validation:** Code is verified on backend before granting access
3. **Active flag:** Codes can be deactivated (e.g., logout, password change)
4. **Usage tracking:** `last_used` timestamp to detect suspicious patterns
5. **One-to-One relationship:** Each user has only one active code
6. **JSON storage:** User data stored with the code for offline use if needed

## Backward Compatibility

- Existing endpoints are unchanged
- Existing users can still use phone/email login methods
- New endpoints are additions, not replacements
- Old registrations can generate codes on next login

## Testing

### Manual Testing with Curl

```bash
# 1. Register user
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","phone":"+919876543210","email":"john@example.com"}'

# Response contains "secret_code": "xxx"

# 2. Auto-login with the secret code
curl -X POST http://localhost:8000/api/login-with-code/ \
  -H "Content-Type: application/json" \
  -d '{"secret_code":"<secret_code_from_step_1>"}'

# 3. Verify code validity
curl -X GET "http://localhost:8000/api/verify-code/?secret_code=<secret_code>"
```

## Documentation

Two comprehensive guides have been created:

1. **ANDROID_SECRET_CODE_IMPLEMENTATION.md**
   - Complete Android/Kotlin implementation guide
   - SharedPreferences and EncryptedSharedPreferences examples
   - Full activity lifecycle with auto-login logic
   - Security best practices
   - Test scenarios

2. **DAPHNE_TROUBLESHOOTING.md**
   - Solutions for service startup errors
   - Migration and dependency checks
   - Direct daphne testing
   - Service restart procedures

## Migration Steps on Production

1. SSH to server
2. Activate virtual environment
3. Run `python manage.py migrate`
4. Restart daphne service: `sudo systemctl restart p2p_project.service`
5. Test with curl commands above

## Notes

- The `secret_code` is 48 characters long (URL-safe base64)
- Each registration overwrites the previous code for that user (OneToOneField)
- The code does not expire automatically (implement logout to clear)
- User data is stored as JSON for potential offline-first scenarios
- Both OTP and secret code are returned, allowing multiple auth methods

ssh scp root@46.62.195.191:/etc/nginx/sites-available/nginx_p2p.conf .