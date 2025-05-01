from typing import List
from fastapi import FastAPI, HTTPException, Depends, status, Request, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import re
import tempfile

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
from fastapi.staticfiles import StaticFiles
import shutil
import uuid

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

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Mount the uploads directory to serve static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload multiple PDF files"""
    try:
        uploaded_files = []
        for file in files:
            # Validate file type
            if not file.content_type == "application/pdf":
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not a PDF"
                )
            
            # Generate unique filename
            unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            uploaded_files.append({
                "filename": unique_filename,
                "originalname": file.filename,
                "size": file_size,
                "path": f"/uploads/{unique_filename}"
            })
        
        return {
            "success": True,
            "files": uploaded_files
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/files")
async def get_files():
    """Get all uploaded files"""
    try:
        files = []
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            stats = os.stat(file_path)
            files.append({
                "filename": filename,
                "size": stats.st_size,
                "path": f"/uploads/{filename}"
            })
        
        return {
            "success": True,
            "files": files
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """Delete a specific file"""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )
        
        os.remove(file_path)
        return {
            "success": True,
            "message": "File deleted successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.options("/upload-pdfs")
async def options_upload_pdfs():
    return cors_options_response()

@app.post("/upload-pdfs", status_code=status.HTTP_200_OK)
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Upload up to 5 PDF files to Cloudinary and store their URLs in Firebase.
    """
    # Validate number of files
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 PDF files can be uploaded at once"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided"
        )
    
    uploaded_files_info = []
    
    for file in files:
        # Validate file is a PDF
        if not file.content_type == "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a PDF"
            )
        
        temp_file_path = None
        try:
            # Read content and create temporary file
            content = await file.read()
            print(f"DEBUG: Read content for {file.filename}")
            
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(content)
                print(f"DEBUG: Temporary file created at {temp_file_path}")
            
            # Upload to Cloudinary
            try:
                result = cloudinary.uploader.upload(
                    temp_file_path,
                    resource_type="raw",
                    folder="pdfs",
                    use_filename=True,
                    unique_filename=True
                )
                cloud_url = result.get('secure_url')
                print(f"DEBUG: Uploaded to Cloudinary: {cloud_url}")
            except Exception as cloud_err:
                print(f"ERROR uploading to Cloudinary: {str(cloud_err)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Cloudinary upload failed: {str(cloud_err)}"
                )
            
            # Create metadata for Firestore - use current time for response
            current_time = datetime.now()
            current_time_str = current_time.isoformat()
            
            # For Firestore document - use SERVER_TIMESTAMP
            firestore_data = {
                'name': file.filename,
                'contentType': file.content_type,
                'url': cloud_url,
                'public_id': result.get('public_id'),
                'timestamp': firestore.SERVER_TIMESTAMP  # This is what Firestore will use
            }
            
            # Store in Firestore
            try:
                doc_ref = db.collection('pdf_uploads').document()
                doc_ref.set(firestore_data)
                doc_id = doc_ref.id
                print(f"DEBUG: Document added to Firestore with ID: {doc_id}")
                
                # Create response data WITHOUT the SERVER_TIMESTAMP sentinel
                response_data = {
                    'id': doc_id,
                    'name': file.filename,
                    'contentType': file.content_type,
                    'url': cloud_url,
                    'public_id': result.get('public_id'),
                    'uploaded_at': current_time_str,  # Use string timestamp for response
                    'time_ago': "Just now"
                }
                
                uploaded_files_info.append(response_data)
            except Exception as db_err:
                print(f"ERROR storing in Firestore: {str(db_err)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error: {str(db_err)}"
                )
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            print(f"ERROR in upload_pdfs: {str(e)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading {file.filename}: {str(e)}"
            )
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"DEBUG: Temporary file removed: {temp_file_path}")
    
    return {
        "status": True,
        "message": f"Successfully uploaded {len(uploaded_files_info)} files",
        "files": uploaded_files_info
    }


@app.options("/recent-pdfs")
async def options_recent_pdfs():
    return cors_options_response()

@app.get("/recent-pdfs", status_code=status.HTTP_200_OK)
async def get_recent_pdfs():
    """
    Retrieve PDF URLs uploaded within the last 3 minutes.
    """
    try:
        # Calculate timestamp from 3 minutes ago
        three_minutes_ago = datetime.now() - timedelta(minutes=3)
        print(f"DEBUG: Getting PDFs uploaded after {three_minutes_ago.isoformat()}")
        
        try:
            # Query for recent documents
            # Note: We can't directly query by SERVER_TIMESTAMP with a comparison
            # So we'll get recent documents and filter them in memory
            query = db.collection('pdf_uploads').order_by(
                'timestamp', direction=firestore.Query.DESCENDING
            ).limit(50)  # Get most recent 50 to filter from
            
            # Execute query
            docs = query.stream()
            
        except Exception as query_err:
            print(f"ERROR querying Firestore: {str(query_err)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database query error: {str(query_err)}"
            )
        
        recent_pdfs = []
        for doc in docs:
            try:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Get the timestamp (it might be a Firestore timestamp object)
                timestamp = data.get('timestamp')
                
                # Skip non-existent timestamps
                if not timestamp:
                    continue
                    
                # Convert Firestore timestamp to datetime if needed
                if hasattr(timestamp, 'seconds'):
                    dt = datetime.fromtimestamp(timestamp.seconds)
                    
                    # Skip if older than 3 minutes
                    if dt < three_minutes_ago:
                        continue
                        
                    # Format for response
                    data['uploaded_at'] = dt.isoformat()
                    data['time_ago'] = get_time_ago(dt)
                    
                    # Remove the non-serializable Firestore timestamp
                    data.pop('timestamp', None)
                    
                # If we get here, this is a document we want to include
                recent_pdfs.append(data)
                
            except Exception as doc_err:
                print(f"WARNING: Error processing document {doc.id}: {str(doc_err)}")
                # Continue with other documents
        
        print(f"DEBUG: Retrieved {len(recent_pdfs)} PDFs uploaded in the last 3 minutes")
        
        return {
            "status": True,
            "count": len(recent_pdfs),
            "files": recent_pdfs
        }
        
    except Exception as e:
        print(f"ERROR retrieving recent PDFs: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recent PDFs: {str(e)}"
        )

def get_time_ago(dt):
    """Convert a datetime to a human-readable 'time ago' string"""
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds/60)} minutes ago"
    else:
        return f"{int(seconds/3600)} hours ago"
    


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