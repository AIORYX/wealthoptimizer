import streamlit as st
from authlib.integrations.base_client import OAuthError
from authlib.integrations.requests_client import OAuth2Session
import os
from dotenv import load_dotenv
load_dotenv()

def login_popup():
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
                <h2>Welcome back!</h2>
                <a href="#" target="_self" style="text-decoration: none; display: block; margin-bottom: 10px;">
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

def login():
    if not st.experimental_user.is_logged_in:
        with st.container():
            st.login()

        #login_popup()
        #if st.button()
        #st.login()
        #if st.button("Log in with Microsoft"):
        #     st.login("microsoft")

    
    else:
        with st.sidebar:
            
            st.markdown(f"#### Welcome back {st.experimental_user.given_name}!") 
            col1, col2, col3 = st.columns([1, 1, 4]) 
            with col1:
                st.image(st.experimental_user.picture, width=70)
            with col2:
                if  st.experimental_user.is_logged_in:
                    if st.button(":material/logout:"):
                        st.logout()
            st.divider()
   