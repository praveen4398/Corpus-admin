#main.py
import streamlit as st
import requests
from my_pages.users_page import render_users_page
from my_pages.categories_page import render_categories_page
from my_pages.records_page import render_records_page

SEND_OTP_URL = "https://backend2.swecha.org/api/v1/auth/send-otp"
VERIFY_OTP_URL = "https://backend2.swecha.org/api/v1/auth/verify-otp"

def send_otp(phone_number: str):
    return requests.post(SEND_OTP_URL, json={"phone_number": phone_number}, headers={
        "accept": "application/json",
        "Content-Type": "application/json"
    })

def verify_otp(phone_number: str, otp_code: str):
    return requests.post(VERIFY_OTP_URL, json={
        "phone_number": phone_number,
        "otp_code": otp_code,
        "has_given_consent": True
    }, headers={
        "accept": "application/json",
        "Content-Type": "application/json"
    })

def render_login_page():
    st.title("Login")

    phone = st.text_input("Phone Number", value=st.session_state.get("phone_number", ""))

    if st.button("Send OTP"):
        if phone.strip():
            try:
                resp = send_otp(phone)
                if resp.status_code == 200:
                    st.success("OTP sent successfully.")
                    st.session_state.phone_number = phone
                    st.session_state.otp_sent = True
                else:
                    st.error(resp.json().get("detail", "Failed to send OTP."))
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a valid phone number.")

    if st.session_state.get("otp_sent", False):
        otp = st.text_input("Enter OTP")

        if st.button("Verify OTP"):
            if otp.strip():
                try:
                    resp = verify_otp(st.session_state.phone_number, otp)
                    if resp.status_code == 200:
                        data = resp.json()
                        roles = [r["name"] for r in data.get("roles", [])]
                        if "admin" in roles:
                            st.success("Login successful!")
                            st.session_state.token = data.get("access_token")
                            st.session_state.logged_in = True
                            st.session_state.page = "users"
                            st.rerun()
                        else:
                            st.error("Access denied. Only admin users are allowed.")
                    else:
                        st.error(resp.json().get("detail", "OTP verification failed."))
                except Exception as e:
                    st.error(f"Server error: {e}")
            else:
                st.warning("Please enter the OTP.")

def render_sidebar():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Users", "Categories", "Records"])
    st.session_state.page = page.lower()

def main():
    # Initialize session state variables
    for key in ["logged_in", "token", "page", "otp_sent", "phone_number"]:
        if key not in st.session_state:
            st.session_state[key] = False if key in ["logged_in", "otp_sent"] else "login" if key == "page" else ""

    if st.session_state.logged_in:
        render_sidebar()

    # Load the appropriate page
    if st.session_state.page == "login":
        render_login_page()
    elif st.session_state.page == "users":
        render_users_page()
    elif st.session_state.page == "categories":
        render_categories_page()
    elif st.session_state.page == "records":
        render_records_page()

if __name__ == "__main__":
    main()
