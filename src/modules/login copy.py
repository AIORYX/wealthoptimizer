import streamlit as st
from authlib.integrations.base_client import OAuthError
from authlib.integrations.requests_client import OAuth2Session
import os
from dotenv import load_dotenv
load_dotenv()

# Set up your OAuth configuration
CLIENT_ID = os.getenv("google_client_id")
CLIENT_SECRET = os.getenv("google_client_secret")
REDIRECT_URI = os.getenv("redirect_url")

# OAuth2 provider details for Google
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USER_INFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

# Initialize session state for user login status
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None
if "oauth_state" not in st.session_state:
    st.session_state["oauth_state"] = None

def create_oauth_session():
    return OAuth2Session(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="openid email profile"
    )

def login():
    oauth = create_oauth_session()
    google_authorization_url, state = oauth.create_authorization_url(
        AUTHORIZATION_URL,
        access_type="offline",
        prompt="consent"
    )
    
    # Save the state for verification later
    st.session_state["oauth_state"] = state

    print(f"state {st.session_state['oauth_state']}")
    
        # Display an expander as a login popup
    #with st.expander("", expanded=True):
    st.markdown(
        f"""
        <style>
            /* Style for the container */
            .login-container {{
                width: 300px;
                padding: 20px;
                border: 1px solid lightgrey;
                border-radius: 15px;
                background-color: white;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }}
            /* Style for buttons */
            .login-button {{
                width: 100%;
                padding: 10px;
                font-size: 16px;
                border: 1px solid lightgrey;
                border-radius: 10px;
                background-color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                transition: background-color 0.3s, box-shadow 0.3s;
            }}
            /* Hover effect */
            .login-button:hover {{
                background-color: #f0f0f0;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            /* Style for the logos */
            .logo {{
                width: 20px;
                height: 20px;
            }}
        </style>
        <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
            <div class="login-container">
                <h2>Welcome back</h2>
                <br>
                <a href="{google_authorization_url}" target="_self" style="text-decoration: none; display: block; margin-bottom: 10px;">
                    <button class="login-button">
                        <img src="https://lh3.googleusercontent.com/COxitqgJr1sJnIDe8-jiKhxDx1FrYbtRHKJ9z_hELisAlapwE9LUPh6fcXIfb5vwpbMl4xl9H9TRFPc5NOO8Sb3VSgIBrfRYvW6cUA" alt="Google" class="logo"/>
                        Continue with Google
                    </button>
                </a>
                <a href="your_microsoft_authorization_url" target="_self" style="text-decoration: none; display: block; margin-bottom: 10px;">
                    <button class="login-button">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/1200px-Microsoft_logo.svg.png" alt="Microsoft" class="logo"/>
                        Continue with Microsoft
                    </button>
                </a>
                <a href="your_apple_authorization_url" target="_self" style="text-decoration: none; display: block;">
                    <button class="login-button">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Apple_logo_black.svg/512px-Apple_logo_black.svg.png" alt="Apple" class="logo"/>
                        Continue with Apple
                    </button>
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    return True

def callback(code):
    # Get the query parameters using st.query_params
    if code:
        try:
            oauth = create_oauth_session()
            
            # Use Basic Authentication to pass client_id and client_secret in the Authorization header
            token = oauth.fetch_token(
                TOKEN_URL,
                code=code,  # st.query_params returns strings directly
                client_id=CLIENT_ID,  # Optional, authlib handles it via the auth header
                client_secret=CLIENT_SECRET,  # Optional, authlib handles it via the auth header
                redirect_uri=REDIRECT_URI,
                grant_type="authorization_code"
            )
            
            # Fetch user information
            resp = oauth.get(USER_INFO_URL)
            user_info = resp.json()
            # Store user information in session state
            #st.session_state["user_info"] = user_info
            
            st.toast("Login successful!")
            return user_info

            
        except OAuthError as error:
            pass
            #st.error(f"OAuth failed: {error}")
    else:
        st.error("Authorization failed or was not completed.")

def logout():
    del st.session_state['user_info']
    #st.session_state["user_info"] = None
    #st.session_state["oauth_state"] = None
    st.rerun()

