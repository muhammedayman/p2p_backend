# Android Implementation Guide: Secret Code Auto-Login

## Overview
This guide explains how to implement the secret code authentication flow in the Android app. After initial registration, the app saves a unique secret code and can auto-login without requiring the user to enter name, phone, and email again.

## Flow Diagram

```
First Time Registration:
1. User enters name, phone, email
2. App sends to /register/ endpoint
3. Server returns secret_code
4. App saves secret_code to local storage (SharedPreferences)
5. User verifies via SMS OTP

Subsequent Launches:
1. App checks if secret_code exists in SharedPreferences
2. If YES: Send secret_code to /login-with-code/ endpoint
3. Server verifies and returns user details
4. App skips registration form, directly shows P2P interface
5. If NO: Show registration form as before
```

## Backend Endpoints

### 1. Registration Endpoint (Modified)
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

**Response:**
```json
{
  "status": "pending_verification",
  "message": "Please send SMS '1234' to +917012710457",
  "otp_code": "1234",
  "target_number": "+917012710457",
  "secret_code": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6",
  "secret_code_message": "Save this code in your app for automatic login next time"
}
```

### 2. Auto-Login with Secret Code
**POST** `/api/login-with-code/`

**Request:**
```json
{
  "secret_code": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6"
}
```

**Response:**
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

**Error Response (401):**
```json
{
  "error": "Invalid or inactive secret code"
}
```

### 3. Verify Secret Code Validity (Optional)
**GET** `/api/verify-code/?secret_code=<code>`

**Response:**
```json
{
  "is_valid": true,
  "secret_code": "a1b2c3d4e5f6..."
}
```

## Android Implementation Steps

### Step 1: Setup SharedPreferences Helper

```kotlin
// AuthenticationManager.kt
import android.content.Context
import android.content.SharedPreferences

class AuthenticationManager(context: Context) {
    private val prefs: SharedPreferences = 
        context.getSharedPreferences("app_auth", Context.MODE_PRIVATE)
    
    companion object {
        private const val KEY_SECRET_CODE = "secret_code"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USER_NAME = "user_name"
        private const val KEY_USER_PHONE = "user_phone"
    }
    
    // Save secret code after registration
    fun saveSecretCode(secretCode: String) {
        prefs.edit()
            .putString(KEY_SECRET_CODE, secretCode)
            .apply()
    }
    
    // Retrieve saved secret code
    fun getSecretCode(): String? {
        return prefs.getString(KEY_SECRET_CODE, null)
    }
    
    // Check if user has been registered before
    fun isUserRegistered(): Boolean {
        return getSecretCode() != null
    }
    
    // Save user details (optional, for offline display)
    fun saveUserDetails(id: Int, name: String, phone: String) {
        prefs.edit()
            .putInt(KEY_USER_ID, id)
            .putString(KEY_USER_NAME, name)
            .putString(KEY_USER_PHONE, phone)
            .apply()
    }
    
    // Clear all authentication data (logout)
    fun clearAuthentication() {
        prefs.edit()
            .remove(KEY_SECRET_CODE)
            .remove(KEY_USER_ID)
            .remove(KEY_USER_NAME)
            .remove(KEY_USER_PHONE)
            .apply()
    }
}
```

### Step 2: Create API Models

```kotlin
// AuthModels.kt
import com.google.gson.annotations.SerializedName

data class RegistrationRequest(
    val name: String,
    val phone: String,
    val email: String?,
    val photo: String? = null,
    val is_photo_public: Boolean = false
)

data class RegistrationResponse(
    val status: String,
    val message: String,
    val otp_code: String,
    val target_number: String,
    val secret_code: String,
    val secret_code_message: String
)

data class LoginWithCodeRequest(
    val secret_code: String
)

data class LoginWithCodeResponse(
    val status: String,
    val user: UserDetail,
    val message: String
)

data class UserDetail(
    val id: Int,
    val name: String,
    val phone: String,
    val email: String?,
    val photo: String?,
    val is_photo_public: Boolean,
    val is_phone_verified: Boolean,
    val is_email_verified: Boolean,
    val is_online: Boolean,
    val last_seen: String?
)

data class ErrorResponse(
    val error: String
)
```

### Step 3: API Service Interface

```kotlin
// ApiService.kt
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {
    
    @POST("register/")
    suspend fun register(
        @Body request: RegistrationRequest
    ): Response<RegistrationResponse>
    
    @POST("login-with-code/")
    suspend fun loginWithSecretCode(
        @Body request: LoginWithCodeRequest
    ): Response<LoginWithCodeResponse>
    
    @GET("verify-code/")
    suspend fun verifySecretCode(
        @Query("secret_code") secretCode: String
    ): Response<VerifyCodeResponse>
}

data class VerifyCodeResponse(
    val is_valid: Boolean,
    val secret_code: String?
)
```

### Step 4: Authentication Activity Logic

```kotlin
// AuthenticationActivity.kt
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AuthenticationActivity : AppCompatActivity() {
    
    private lateinit var authManager: AuthenticationManager
    private lateinit var apiService: ApiService
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        authManager = AuthenticationManager(this)
        initializeApiService()
        
        // Check if user already has saved secret code
        if (authManager.isUserRegistered()) {
            // Try auto-login with saved secret code
            attemptAutoLogin()
        } else {
            // Show registration form
            showRegistrationForm()
        }
    }
    
    private fun initializeApiService() {
        val retrofit = Retrofit.Builder()
            .baseUrl("http://your-server-ip:8000/api/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        apiService = retrofit.create(ApiService::class.java)
    }
    
    // AUTO-LOGIN FLOW
    private fun attemptAutoLogin() {
        lifecycleScope.launch {
            val secretCode = authManager.getSecretCode()
            if (secretCode != null) {
                try {
                    val request = LoginWithCodeRequest(secretCode)
                    val response = apiService.loginWithSecretCode(request)
                    
                    if (response.isSuccessful && response.body() != null) {
                        val loginResponse = response.body()!!
                        
                        // Update user details in cache
                        authManager.saveUserDetails(
                            loginResponse.user.id,
                            loginResponse.user.name,
                            loginResponse.user.phone
                        )
                        
                        // Navigate to main app
                        startActivity(Intent(this@AuthenticationActivity, MainActivity::class.java))
                        finish()
                    } else {
                        // Code invalid or expired, show registration form
                        authManager.clearAuthentication()
                        showRegistrationForm()
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                    // Network error, but code exists - you can handle offline mode here
                    showRegistrationForm()
                }
            }
        }
    }
    
    // REGISTRATION FLOW
    private fun registerUser(name: String, phone: String, email: String?) {
        lifecycleScope.launch {
            try {
                val request = RegistrationRequest(
                    name = name,
                    phone = phone,
                    email = email
                )
                
                val response = apiService.register(request)
                
                if (response.isSuccessful && response.body() != null) {
                    val regResponse = response.body()!!
                    
                    // SAVE the secret code locally
                    authManager.saveSecretCode(regResponse.secret_code)
                    authManager.saveUserDetails(1, name, phone) // ID will be updated on next login
                    
                    // Show OTP verification screen
                    showOTPVerificationDialog(
                        regResponse.otp_code,
                        regResponse.target_number
                    )
                } else {
                    showError("Registration failed: ${response.errorBody()?.string()}")
                }
            } catch (e: Exception) {
                showError("Error: ${e.message}")
            }
        }
    }
    
    private fun showRegistrationForm() {
        setContentView(R.layout.activity_registration)
        // Setup UI bindings
        // When user submits, call registerUser()
    }
    
    private fun showOTPVerificationDialog(otpCode: String, targetNumber: String) {
        // Show dialog with instructions to SMS the code
    }
    
    private fun showError(message: String) {
        // Show error toast/dialog
    }
}
```

### Step 5: Handle Deep Links (Optional)

If your app uses deep links for sharing, you can handle secret code sharing:

```kotlin
// In AndroidManifest.xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data
        android:scheme="p2papp"
        android:host="login"
        android:pathPrefix="/code" />
</intent-filter>

// In Activity
override fun onNewIntent(intent: Intent?) {
    super.onNewIntent(intent)
    val uri = intent?.data
    if (uri != null && uri.scheme == "p2papp") {
        val secretCode = uri.getQueryParameter("code")
        if (secretCode != null) {
            authManager.saveSecretCode(secretCode)
            attemptAutoLogin()
        }
    }
}
```

## Security Best Practices

1. **Store Secret Code Securely**
   ```kotlin
   // Use EncryptedSharedPreferences instead of plain SharedPreferences
   val masterKey = MasterKey.Builder(context)
       .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
       .build()
   
   val encryptedSharedPrefs = EncryptedSharedPreferences.create(
       context,
       "secret_prefs",
       masterKey,
       EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
       EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
   )
   ```

2. **Use HTTPS**
   - Always use HTTPS endpoints in production
   - Pin SSL certificates for additional security

3. **Validate Secret Code Format**
   - Verify the format before storing (should be 48-character URL-safe string)

4. **Handle Logout Properly**
   - Clear secret code when user logs out
   - Implement timeout for auto-login

5. **Implement Refresh Token**
   - Consider adding token expiration
   - Allow secret code rotation

## Testing the Flow

### Test Case 1: First Registration
1. Launch app with no saved code
2. Enter name, phone, email
3. Receive secret code in response
4. Verify code is saved in SharedPreferences
5. Verify user can proceed after SMS verification

### Test Case 2: Subsequent Launch
1. Launch app with saved code
2. Verify auto-login happens automatically
3. Verify registration form is NOT shown
4. Verify user details are restored

### Test Case 3: Invalid Code
1. Clear SharedPreferences and manually save invalid code
2. Launch app
3. Verify registration form is shown
4. Verify error is handled gracefully

### Test Case 4: Network Error During Auto-Login
1. Turn off network
2. Launch app with saved code
3. Handle gracefully (show cached user info or registration form)

## Database Migration

Run migrations after updating models:

```bash
python manage.py makemigrations
python manage.py migrate
```

The migration will create the `authentication_codes` table automatically.

## Curl Testing Commands

```bash
# Register User
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","phone":"+919876543210","email":"john@example.com"}'

# Login with Secret Code
curl -X POST http://localhost:8000/api/login-with-code/ \
  -H "Content-Type: application/json" \
  -d '{"secret_code":"<secret_code_from_register>"}'

# Verify Code
curl -X GET "http://localhost:8000/api/verify-code/?secret_code=<secret_code>"
```

## Summary

This implementation provides:
- ✅ Unique secret code generation on registration
- ✅ Auto-login on subsequent app launches
- ✅ Skipped registration form for returning users
- ✅ Secure storage of authentication tokens
- ✅ Fallback to registration form if code is invalid
- ✅ User identification without re-entering details


start "Android Terminal" cmd /k pushd d:\projects\research\project1\android_app
start "" "C:\Program Files\Android\Android Studio\bin\studio64.exe" d:\projects\research\project1\android_app

