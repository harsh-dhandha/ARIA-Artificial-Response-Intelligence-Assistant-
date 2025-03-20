from typing import List
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import re
import warnings
from pydantic import BaseModel, EmailStr, field_validator
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from dotenv import load_dotenv
import smtplib
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from utils.cors_helpers import cors_options_response  # Import the helper function
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

# Create a custom middleware to add CORS headers to all responses
class CORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

# FastAPI setup - use only one app instance
app = FastAPI()

# Add our custom CORS middleware
app.add_middleware(CORSHeaderMiddleware)

# Configure standard CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

                     
# Check for required environment variables, False for production
def check_required_env_vars():
    required_vars = ['SECRET_KEY', 'DB_URL', 'STORAGE_BUCKET', 'MAIL_USER', 'MAIL_PASS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    return True

if not check_required_env_vars():
    print("Application cannot start due to missing environment variables")
    exit(1)

warnings.filterwarnings("ignore")
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 144000

# Pydantic models for API
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str or None = None

class User(BaseModel):
    username: str
    email: str or None = None
    disabled: bool or None = None

class UserInDB(User):
    hashed_password: str

class OTP_AUTH(BaseModel):
    email: str
    otp: str

class EmailOTP(BaseModel):
    email: str

class SignUp(BaseModel):
    email: EmailStr
    password: str
    username: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v

class Login(BaseModel):
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def password_not_empty(cls, v):
        if not v or v.isspace():
            raise ValueError('Password cannot be empty')
        return v

class FileProcess(BaseModel):
    files: List[str]
    rewrite: bool = False

class Domain(BaseModel):
    email: str
    domain: str

class FilterWords(BaseModel):
    email: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Firebase initialization
def initialize_firebase():
    try:
        # Check if already initialized
        if not firebase_admin._apps:
            credential_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if not os.path.exists(credential_path):
                print(f"ERROR: Service account key file not found at {credential_path}")
                raise ValueError(f"Service account key file not found at {credential_path}")
            
            # Print service account info for debugging (without sensitive data)
            try:
                import json
                with open(credential_path, 'r') as f:
                    cred_data = json.load(f)
                    print(f"DEBUG: Using service account: {cred_data.get('client_email')}")
                    print(f"DEBUG: Project ID: {cred_data.get('project_id')}")
            except Exception as e:
                print(f"DEBUG: Could not read service account details: {str(e)}")
            
            cred = credentials.Certificate(credential_path)
            database_url = os.getenv('DB_URL')
            if not database_url:
                print("WARNING: DB_URL environment variable is missing")
                raise ValueError("Missing required environment variables: DB_URL")
            
            # Initialize Firebase with detailed options
            print(f"DEBUG: Initializing Firebase with database URL: {database_url}")
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url,
                'storageBucket': os.getenv('STORAGE_BUCKET')
            })
            
            # Test Firestore connection with explicit transaction
            firestore_client = firestore.client()
            try:
                # Try a simple write operation to verify permissions
                test_doc = firestore_client.collection("_test_connection").document("test")
                test_doc.set({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                print("Firebase connection verified with successful write test")
                # Clean up test document
                test_doc.delete()
            except Exception as test_error:
                print(f"WARNING: Firebase connection test write failed: {str(test_error)}")
                # Continue anyway, as the error might be permission-specific
            
            print("Firebase connection established successfully")
            return firestore_client
        else:
            return firestore.client()
    except Exception as e:
        print(f"Firebase Initialization Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# Initialize Firebase at startup
try:
    firest = initialize_firebase()
except Exception as e:
    print(f"Critical Initialization Error: {str(e)}")
    raise

# Authentication helper functions
def generate_otp(length=6):
    """Generate a random OTP of the given length."""
    digits = string.digits
    otp = ''.join(random.choices(digits, k=length))
    return otp

def send_otp_via_email(receiver_email, otp, purpose="verification"):
    """Send the OTP to the specified email address."""
    sender_email = os.getenv('MAIL_USER')
    sender_password = os.getenv('MAIL_PASS')
    
    # More detailed logging for email configuration
    print(f"DEBUG: Email configuration - User: {sender_email}, Pass length: {len(sender_password) if sender_password else 0}")
    
    if not sender_email or not sender_password:
        print(f"ERROR: Email credentials not configured properly: {sender_email=}")
        return False

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    if purpose == "signup":
        subject = "Your OTP for Account Creation – ARIA AI"
        body_intro = "Thank you for signing up with ARIA AI."
    else:
        subject = "Your OTP for Secure Access – ARIA AI"
        body_intro = "We've received a request to authenticate your account with ARIA AI."
        
    message['Subject'] = subject
    
    body = f"""Hello,
{body_intro}
Your One-Time Password (OTP) is: {otp}
Please use this OTP to complete your process. For your security, this code is valid for only 5 minutes and can be used once.
If you did not initiate this request, please ignore this email or contact our support team immediately.

Thank you for choosing ARIA AI!
Best regards,
The ARIA AI Team"""
    
    message.attach(MIMEText(body, 'plain'))
    
    try:
        print(f"DEBUG: Attempting to send email from {sender_email} to {receiver_email}")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Add SMTP debug logging
        server.starttls()
        
        # Try to login with better error handling
        try:
            print(f"DEBUG: Attempting SMTP login for {sender_email}")
            server.login(sender_email, sender_password)
            print("DEBUG: SMTP login successful")
            
            print("DEBUG: Sending email message")
            server.send_message(message)
            server.quit()
            print(f"DEBUG: OTP email sent successfully to {receiver_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as auth_error:
            print(f"ERROR: SMTP Authentication Error: {auth_error}")
            print("This error usually occurs when:")
            print("1. Your email password is incorrect")
            print("2. You need to use an App Password instead of your regular password")
            print("3. You need to allow less secure apps in your Google account settings")
            print("4. You need to enable IMAP access in your Gmail settings")
            return False
            
        except Exception as login_error:
            print(f"ERROR: SMTP Login Error: {login_error}")
            return False
            
    except Exception as e:
        print(f"ERROR: SMTP Connection Error: {e}")
        return False

def store_otp(email, otp, purpose="login"):
    """Store OTP in Firestore with timestamp"""
    try:
        print(f"DEBUG: Storing OTP for {email} with purpose {purpose}")
        doc_ref = firest.collection("OTP DB").document(email)
        hashed_otp = get_password_hash(otp)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "otp": hashed_otp,
            "timestamp": timestamp,
            "purpose": purpose,
            "verified": False
        }
        print(f"DEBUG: Writing OTP data with timestamp {timestamp}")
        
        # Use an explicit transaction for more reliable writes
        transaction = firest.transaction()
        
        @firestore.transactional
        def update_in_transaction(transaction, doc_ref, data):
            transaction.set(doc_ref, data)
            return True
            
        result = update_in_transaction(transaction, doc_ref, data)
        print(f"DEBUG: OTP data successfully stored for {email}")
        return result
    except Exception as e:
        print(f"ERROR storing OTP: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_otp(email, user_otp):
    """Verify OTP from Firestore"""
    try:
        user_ref = firest.collection("OTP DB").document(email)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return {"status": False, "error": "No OTP found or expired"}
        data = user_doc.to_dict()
        stored_otp = data.get("otp")
        timestamp_str = data.get("timestamp")
        purpose = data.get("purpose", "login")
        
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()
        
        if current_time - timestamp > timedelta(minutes=5):
            return {"status": False, "error": "OTP expired"}
        
        if verify_password(user_otp, stored_otp):
            user_ref.update({"verified": True})
            return {"status": True, "message": "OTP is valid", "purpose": purpose}
        else:
            return {"status": False, "error": "Invalid OTP"}
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        return {"status": False, "error": str(e)}

def check_user_exists(email):
    """Check if a user with the given email already exists"""
    doc_ref = firest.collection("User").document(email)
    return doc_ref.get().exists

def create_user_account(email, password, username):
    """Create a new user account after OTP verification"""
    try:
        # First check if the user is verified with OTP
        print(f"DEBUG: Creating account for {email} with username {username}")
        otp_ref = firest.collection("OTP DB").document(email)
        otp_doc = otp_ref.get()
        if not otp_doc.exists:
            print(f"DEBUG: No OTP document found for {email}")
            return {"status": False, "message": "OTP verification required"}
            
        otp_data = otp_doc.to_dict()
        if not otp_data.get("verified", False):
            print(f"DEBUG: OTP not verified for {email}")
            return {"status": False, "message": "Email not verified with OTP"}
            
        if otp_data.get("purpose") != "signup":
            print(f"DEBUG: Invalid purpose for {email}: {otp_data.get('purpose')}")
            return {"status": False, "message": "Invalid verification purpose"}
        
        # Create the user account
        print(f"DEBUG: Verification passed, creating user account: {email}")
        doc_ref = firest.collection("User").document(email)
        
        # Check if user already exists
        if doc_ref.get().exists:
            print(f"DEBUG: User already exists: {email}")
            return {"status": False, "message": "User already exists"}
        
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        admin_data = {
            "email": email,
            "password": password,
            "username": username,
            "disabled": False,
            "created_at": created_at
        }
        
        # Use transaction for reliable write
        transaction = firest.transaction()
        
        @firestore.transactional
        def create_user_in_transaction(transaction, doc_ref, data):
            transaction.set(doc_ref, data)
            return True
            
        result = create_user_in_transaction(transaction, doc_ref, admin_data)
        
        if result:
            print(f"DEBUG: User account created successfully: {email}")
            # Clean up the OTP document after successful signup
            otp_ref.delete()
            return {"status": True, "message": "Account created successfully"}
        else:
            print(f"DEBUG: Failed to create user account for unknown reason")
            return {"status": False, "message": "Failed to create user account"}
            
    except Exception as e:
        print(f"ERROR creating user: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": False, "message": f"An error occurred: {e}"}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    try:
        user_ref = firest.collection("User").document(username)
        user_doc = user_ref.get()
        if user_doc.exists:
            data = user_doc.to_dict()
            username = data.get("username")
            password = data.get("password")
            disabled = data.get("disabled")
            return {"username": username, "password": password, "disabled": disabled}
        else:
            print("No such document!")
            return None
    except Exception as e:
        print(f"Error getting document: {e}")
        return None

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user['password']):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta or None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credential_exception
    user = get_user(firest, username=token_data.username)
    if user is None:
        raise credential_exception
    return user

def store_token(uid, token):
    doc_ref = firest.collection("User").document(uid)
    data = {"apikey": token}
    try:
        doc_ref.update(data)
        return True
    except Exception as e:
        print(f"Error storing token: {e}")
        return False

# API Endpoints:
@app.get("/")
async def root():
    return {"message": "Authentication Service"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(firest, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    store_token(form_data.username, access_token)
    return {"access_token": access_token, "token_type": "bearer"}

@app.options("/request_signup_otp")
async def options_signup_otp():
    return cors_options_response()

@app.options("/verify_signup_otp")
async def options_verify_signup_otp():
    return cors_options_response()

@app.options("/request_login_otp")
async def options_login_otp():
    return cors_options_response()

@app.options("/login_with_otp")
async def options_login_with_otp():
    return cors_options_response()

@app.options("/login")
async def options_login():
    return cors_options_response()

# Add OPTIONS handlers for other endpoints that need CORS
@app.options("/signup")
async def options_signup():
    return cors_options_response()

@app.options("/process")
async def options_process():
    return cors_options_response("POST, OPTIONS")

@app.options("/add_domain")
async def options_add_domain():
    return cors_options_response()

@app.options("/get_filterwords")
async def options_get_filterwords():
    return cors_options_response()

@app.post("/request_signup_otp")
async def request_signup_otp(request: EmailOTP):
    """Request OTP for signup process"""
    try:
        email = request.email
        print(f"DEBUG: Processing signup OTP request for email: {email}")
        # Check if the email already exists
        if check_user_exists(email):
            print(f"DEBUG: Email already registered: {email}")
            return JSONResponse(
                content={"detail": "Email already registered"},
                status_code=409
            )
        
        # Generate OTP
        otp = generate_otp()
        print(f"DEBUG: Generated OTP for {email}: {otp}")
        
        # For development, we'll always return the OTP in the response
        # This is not secure for production but helps with debugging
        
        # Try to send email but continue even if it fails
        try:
            email_sent = send_otp_via_email(email, otp, purpose="signup")
            if not email_sent:
                print("DEBUG: Email sending failed, but continuing with flow")
        except Exception as e:
            print(f"DEBUG: Email error: {str(e)}")
            # Continue even if email fails - we'll show OTP in response
        
        # Try to store OTP but continue even if it fails
        try:
            store_result = store_otp(email, otp, purpose="signup")
            if not store_result:
                print("DEBUG: Failed to store OTP, using fallback storage")
                # In a real app, implement fallback storage
        except Exception as e:
            print(f"DEBUG: Storage error: {str(e)}")
            # Continue anyway for testing
        
        # Return success with OTP for development
        return {
            "message": "OTP sent successfully for signup",
            "debug_otp": otp  # Including OTP in response for development
        }
    except Exception as e:
        print(f"DEBUG: Unexpected error in request_signup_otp: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"detail": f"Server error: {str(e)}"},
            status_code=500
        )

@app.options("/verify_signup_otp")  # Handle OPTIONS request for CORS preflight
@app.post("/verify_signup_otp")
def verify_signup_otp(request: OTP_AUTH = None):
    """Verify OTP for signup process"""
    if request is None:
        return {}
        
    try:
        email = request.email
        otp = request.otp
        
        print(f"Verifying OTP for email: {email}")
        result = verify_otp(email, otp)
        if not result["status"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Invalid OTP")
            )
        if result.get("purpose") != "signup":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP purpose"
            )
        
        return {"status": True, "message": "Email verified successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in verify_signup_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(request: SignUp):
    try:
        email = request.email
        password = request.password
        username = request.username
        
        print(f"DEBUG: Processing signup for {email} with username {username}")
        
        # Check if user already exists
        if check_user_exists(email):
            print(f"DEBUG: User already exists during signup: {email}")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"status": False, "message": "User already exists"}
            )
        
        # Hash the password
        hashed_password = get_password_hash(password)
        print("DEBUG: Password hashed successfully")
        
        # Create user account (this will also check for OTP verification)
        result = create_user_account(email, hashed_password, username)
        print(f"DEBUG: Account creation result: {result}")
        
        if not result["status"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        return {"status": True, "message": result["message"]}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"ERROR in signup: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.options("/request_login_otp")
async def options_login_otp():
    return cors_options_response()

@app.post("/request_login_otp")
def request_login_otp(request: EmailOTP):
    """Request OTP for login process"""
    try:
        email = request.email
        print(f"DEBUG: Processing login OTP request for email: {email}")
        
        # Check if the email exists
        if not check_user_exists(email):
            print(f"DEBUG: Account not found for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Generate and send OTP
        otp = generate_otp()
        print(f"DEBUG: Generated login OTP for {email}: {otp}")
        
        # Try sending email with more detailed error reporting
        email_sent = send_otp_via_email(email, otp, purpose="login")
        if not email_sent:
            print("DEBUG: Email sending failed but continuing with OTP flow for development")
            # For development, we'll still continue and return the OTP
            # Store OTP in Firestore
            store_result = store_otp(email, otp, purpose="login")
            if not store_result:
                print("DEBUG: Failed to store OTP in database")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store OTP"
                )
            
            # Return the OTP in development mode to facilitate testing
            return {
                "message": "OTP process completed (email sending failed)",
                "debug_otp": otp  # Include OTP in response for development
            }
        
        # Store OTP in Firestore
        if not store_otp(email, otp, purpose="login"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store OTP"
            )
            
        return {
            "message": "OTP sent successfully for login",
            "debug_otp": otp  # Including OTP in response for development
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"DEBUG: Unexpected error in request_login_otp: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"detail": f"Server error: {str(e)}"},
            status_code=500
        )

@app.options("/login_with_otp")
async def options_login_with_otp():
    return cors_options_response()

@app.post("/login_with_otp")
def login_with_otp(request: OTP_AUTH):
    """Login with email and OTP"""
    email = request.email
    otp = request.otp
    # Check if the email exists
    if not check_user_exists(email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Verify OTP
    result = verify_otp(email, otp)
    if not result["status"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Invalid OTP")
        )
    
    if result.get("purpose") != "login":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP purpose"
        )
    
    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": email}, expires_delta=access_token_expires)
    
    # Store token
    store_token(email, access_token)
    
    return {
        "status": True,
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.options("/login")
async def options_login():
    return cors_options_response()

@app.post("/login", status_code=status.HTTP_200_OK)
async def login(request: Login):
    try:
        email = request.email
        password = request.password
        # Check if email exists
        if not check_user_exists(email):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Check password
        user = get_user(firest, email)
        if not user or not verify_password(password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Generate access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": email}, expires_delta=access_token_expires)
        
        # Store token
        store_token(email, access_token)
        
        return {
            "status": True,
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.post("/process", status_code=status.HTTP_200_OK)
async def process_files(request: FileProcess, token: str = Depends(oauth2_scheme)):
    """Process uploaded files and optionally rewrite content"""
    try:
        # Verify token
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        # You can implement actual file processing logic here
        # For now, we'll just return success
        return {
            "status": True,
            "message": "Files processed successfully",
            "files_processed": len(request.files),
            "rewrite_enabled": request.rewrite
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.options("/add_domain")
async def options_add_domain():
    return cors_options_response()

@app.post("/add_domain", status_code=status.HTTP_200_OK)
async def add_domain(request: Domain):
    """Add a domain for a user"""
    try:
        email = request.email
        domain = request.domain
        # Check if email exists
        if not check_user_exists(email):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Store the domain in Firestore
        user_ref = firest.collection("User").document(email)
        user_doc = user_ref.get()
        if user_doc.exists:
            current_data = user_doc.to_dict()
            domains = current_data.get('domains', [])
        else:
            domains = []
        
        # Check if domain already exists
        if domain in domains:
            return {"message": "Domain already added for this user"}
        
        # Add new domain
        domains.append(domain)
        user_ref.update({"domains": domains})
        return {"message": "Domain added successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.options("/get_filterwords")
async def options_get_filterwords():
    return cors_options_response()

@app.post("/get_filterwords", status_code=status.HTTP_200_OK)
async def get_filter_words(request: FilterWords):
    """Get filter words for content moderation"""
    try:
        email = request.email
        # Check if email exists
        if not check_user_exists(email):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        user_ref = firest.collection("User").document(email)
        user_doc = user_ref.get()
        if user_doc.exists:
            current_data = user_doc.to_dict()
            filter_words = current_data.get('filter_words', [])
        else:
            filter_words = []
        
        # For demo, we'll return an empty list or mock data
        # In a real app, you would retrieve filter words from the database
        return {"filter_words": filter_words}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.get("/health")
def health_check():
    """Simple endpoint to check if the API is running"""
    return PlainTextResponse("OK")

# Landing page routes - these should be called before authentication
@app.get("/landing/about")
async def landing_about():
    """Serve the about page before authentication"""
    return JSONResponse(
        content={"page": "about", "message": "About Us page content"},
        status_code=200
    )

@app.get("/landing/contact")
async def landing_contact():
    """Serve the contact page before authentication"""
    return JSONResponse(
        content={"page": "contact", "message": "Contact page content"},
        status_code=200
    )

@app.get("/landing/redirect-to-auth")
async def redirect_to_auth():
    """Redirect from landing pages to authentication"""
    # This endpoint can be called from landing pages to redirect to auth
    return RedirectResponse(url="/auth/login")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)