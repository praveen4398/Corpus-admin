# main.py
import requests
import streamlit as st
from my_pages.categories_page import render_categories_page
from my_pages.records_page import render_records_page
from my_pages.users_page import render_users_page
from my_pages.contributions_page import render_contributions_page

SEND_OTP_URL = "https://backend2.swecha.org/api/v1/auth/send-otp"
VERIFY_OTP_URL = "https://backend2.swecha.org/api/v1/auth/verify-otp"


def send_otp(phone_number: str):
    return requests.post(
        SEND_OTP_URL,
        json={"phone_number": phone_number},
        headers={"accept": "application/json", "Content-Type": "application/json"},
    )


def verify_otp(phone_number: str, otp_code: str):
    return requests.post(
        VERIFY_OTP_URL,
        json={
            "phone_number": phone_number,
            "otp_code": otp_code,
            "has_given_consent": True,
        },
        headers={"accept": "application/json", "Content-Type": "application/json"},
    )


def render_login_page():
    # Page header with styling
    st.markdown(
        """
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; margin-bottom: 3rem; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">🔐 Admin Dashboard</h1>
        <p style="color: white; margin: 10px 0 0 0; font-size: 1.1rem;">Secure Login with OTP</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Create a centered login form
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                st.markdown("### 📱 Enter Your Phone Number")

                phone = st.text_input(
                    "Phone Number",
                    value=st.session_state.get("phone_number", ""),
                    placeholder="+91XXXXXXXXXX",
                    help="Enter your registered phone number",
                )

                if st.form_submit_button(
                    "📤 Send OTP", type="primary", use_container_width=True
                ):
                    if phone.strip():
                        with st.spinner("Sending OTP..."):
                            try:
                                resp = send_otp(phone.strip())
                                if resp.status_code == 200:
                                    st.success(
                                        "✅ OTP sent successfully to your phone!"
                                    )
                                    st.session_state.phone_number = phone.strip()
                                    st.session_state.otp_sent = True
                                    st.rerun()
                                else:
                                    st.error(
                                        f"❌ Failed to send OTP: {resp.json().get('detail', 'Unknown error')}"
                                    )
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                    else:
                        st.warning("⚠️ Please enter a valid phone number.")

    # OTP verification section
    if st.session_state.get("otp_sent", False):
        st.markdown("---")
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("otp_form"):
                    st.markdown("### 🔢 Enter OTP")
                    st.info(f"📱 OTP sent to: **{st.session_state.phone_number}**")

                    otp = st.text_input(
                        "OTP Code",
                        placeholder="Enter 6-digit OTP",
                        help="Enter the 6-digit OTP received on your phone",
                        max_chars=6,
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button(
                            "🔐 Verify OTP", type="primary", use_container_width=True
                        ):
                            if otp.strip() and len(otp.strip()) == 6:
                                with st.spinner("Verifying OTP..."):
                                    try:
                                        st.write(
                                            "DEBUG: Using token", st.session_state.token
                                        )
                                        resp = verify_otp(
                                            st.session_state.phone_number, otp.strip()
                                        )
                                        if resp.status_code == 200:
                                            data = resp.json()
                                            print("LOGIN RESPONSE:", data)
                                            st.write("DEBUG: Login response", data)
                                            roles = [
                                                r["name"] for r in data.get("roles", [])
                                            ]
                                            if "admin" in roles:
                                                st.success(
                                                    "🎉 Login successful! Welcome to Admin Dashboard."
                                                )
                                                st.session_state.token = data.get(
                                                    "access_token"
                                                )
                                                st.session_state.logged_in = True
                                                st.session_state.page = "users"
                                                st.session_state.user_roles = roles
                                                st.session_state.user_data = data
                                                st.session_state.user_id = data.get(
                                                    "user_id"
                                                )
                                                st.rerun()
                                            else:
                                                st.error(
                                                    "❌ Access denied. Only admin users are allowed."
                                                )
                                        else:
                                            st.error(
                                                f"❌ OTP verification failed: {resp.json().get('detail', 'Invalid OTP')}"
                                            )
                                    except Exception as e:
                                        st.error(f"❌ Server error: {e}")
                            else:
                                st.warning("⚠️ Please enter a valid 6-digit OTP.")

                    with col2:
                        if st.form_submit_button(
                            "🔄 Resend OTP", use_container_width=True
                        ):
                            st.session_state.otp_sent = False
                            st.rerun()


def render_sidebar():
    st.sidebar.markdown(
        """
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <h3 style="color: white; margin: 0; text-align: center;">🧭 Navigation</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # User info section
    if st.session_state.get("phone_number"):
        st.sidebar.markdown(f"**👤 Logged in as:** {st.session_state.phone_number}")

        # Show user roles if available
        if st.session_state.get("user_roles"):
            roles_text = ", ".join(st.session_state.user_roles)
            st.sidebar.markdown(f"**🔑 Roles:** {roles_text}")

    st.sidebar.markdown("---")

    # Navigation options
    page_options = {
        "👥 Users": "users",
        "📂 Categories": "categories",
        "📄 Records": "records",
        "📊 Contributions": "contributions",
    }

    selected_page = st.sidebar.radio(
        "Select Page",
        list(page_options.keys()),
        index=list(page_options.values()).index(st.session_state.get("page", "users")),
    )

    st.session_state.page = page_options[selected_page]

    st.sidebar.markdown("---")

    # Logout button
    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def main():
    # Configure page settings
    st.set_page_config(
        page_title="Admin Dashboard",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for better styling
    st.markdown(
        """
    <style>
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
    .stSelectbox > div > div > select {
        border-radius: 8px;
    }
    .stTextArea > div > div > textarea {
        border-radius: 8px;
    }
    .stNumberInput > div > div > input {
        border-radius: 8px;
    }
    .stCheckbox > div > div {
        border-radius: 8px;
    }
    .stDateInput > div > div > input {
        border-radius: 8px;
    }
    .stMultiselect > div > div > div {
        border-radius: 8px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Initialize session state variables only if they don't exist
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "token" not in st.session_state:
        st.session_state.token = None
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "otp_sent" not in st.session_state:
        st.session_state.otp_sent = False
    if "phone_number" not in st.session_state:
        st.session_state.phone_number = ""

    # Check if user is logged in
    if st.session_state.logged_in and st.session_state.token:
        render_sidebar()

        # Load the appropriate page
        if st.session_state.page == "users":
            render_users_page()
        elif st.session_state.page == "categories":
            render_categories_page()
        elif st.session_state.page == "records":
            render_records_page()
        elif st.session_state.page == "contributions":
            render_contributions_page()
    else:
        # User is not logged in, show login page
        render_login_page()


if __name__ == "__main__":
    main()
