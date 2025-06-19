from datetime import datetime, timedelta

import requests
import streamlit as st

# API URLs
USERS_API_URL = "https://backend2.swecha.org/api/v1/users/"
AUTH_ME_URL = "https://backend2.swecha.org/api/v1/auth/me/"


def COMMON_HEADERS(token):
    return {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def is_authenticated(token: str) -> bool:
    """Verify if the token is valid using /auth/me."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(AUTH_ME_URL, headers=headers)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Auth check failed: {e}")
        return False


def fetch_user_by_id(token, user_id):
    """Fetch a single user by their ID."""
    try:
        headers = COMMON_HEADERS(token)
        r = requests.get(f"{USERS_API_URL}{user_id}", headers=headers)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        st.error(f"Failed to fetch user: {e}")
        return None


def fetch_all_users(token, skip=0, limit=100):
    """Fetch all users with pagination."""
    try:
        headers = COMMON_HEADERS(token)
        params = {"skip": skip, "limit": limit}
        r = requests.get(USERS_API_URL, params=params, headers=headers)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):  # Ensure the response is a list
                return data
            else:
                st.error("Unexpected response format from the server.")
                return []
        else:
            st.error(f"Failed to fetch users. Status Code: {r.status_code}")
            return []
    except Exception as e:
        st.error(f"Network error: {e}")
        return []


def create_user(token, name, email, phone, gender, dob, place, password, role_ids):
    """Create a new user."""
    data = {
        "phone": phone,
        "name": name,
        "email": email,
        "gender": gender,
        "date_of_birth": dob,
        "place": place,
        "password": password,
        "role_ids": role_ids,
        "has_given_consent": True,
    }
    try:
        headers = COMMON_HEADERS(token)
        r = requests.post(USERS_API_URL, json=data, headers=headers)
        if r.status_code == 201:
            return True, "User created successfully."
        return False, r.json().get("detail", "Error creating user.")
    except Exception as e:
        return False, f"Network error: {e}"


def update_user(
    token,
    user_id,
    name,
    email,
    gender,
    date_of_birth,
    place,
    is_active,
    has_given_consent,
):
    """Update an existing user."""
    url = f"https://backend2.swecha.org/api/v1/users/{user_id}"
    headers = COMMON_HEADERS(token)
    data = {
        "name": name,
        "email": email,
        "gender": gender,
        "date_of_birth": date_of_birth,
        "place": place,
        "is_active": is_active,
        "has_given_consent": has_given_consent,
    }
    try:
        r = requests.put(url, json=data, headers=headers)
        if r.status_code == 200:
            return True, "User updated successfully."
        return False, r.json().get("detail", "Error updating user.")
    except Exception as e:
        return False, f"Network error: {e}"


def delete_user(token, user_id):
    """Delete a user."""
    try:
        headers = COMMON_HEADERS(token)
        r = requests.delete(f"{USERS_API_URL}{user_id}", headers=headers)
        if r.status_code == 204:
            return True, "User deleted successfully."
        return False, r.json().get("detail", "Error deleting user.")
    except Exception as e:
        return False, f"Network error: {e}"


def render_update_user_form(user_id, current_user_data):
    """Render a form to update a user."""
    with st.container():
        st.markdown("### ✏️ Update User")
        st.markdown("---")

        with st.form("update_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", value=current_user_data.get("name", ""))
                email = st.text_input("Email", value=current_user_data.get("email", ""))
                gender = st.selectbox(
                    "Gender",
                    ["male", "female", "other"],
                    index=["male", "female", "other"].index(
                        current_user_data.get("gender", "male")
                    ),
                )
                date_of_birth = st.date_input(
                    "Date of Birth",
                    value=datetime.strptime(
                        current_user_data.get("date_of_birth", ""), "%Y-%m-%d"
                    )
                    if current_user_data.get("date_of_birth")
                    else datetime.today()
                    - timedelta(days=365 * 20),  # Default to 20 years ago
                ).strftime("%Y-%m-%d")

            with col2:
                place = st.text_input("Place", value=current_user_data.get("place", ""))
                is_active = st.checkbox(
                    "Is Active", value=current_user_data.get("is_active", True)
                )
                has_given_consent = st.checkbox(
                    "Has Given Consent",
                    value=current_user_data.get("has_given_consent", True),
                )

            st.markdown("---")

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.form_submit_button("✅ Update", type="primary"):
                    if not name.strip() or not email.strip():
                        st.error("Name and Email are required.")
                    else:
                        success, msg = update_user(
                            token=st.session_state.token,
                            user_id=user_id,
                            name=name.strip(),
                            email=email.strip(),
                            gender=gender,
                            date_of_birth=date_of_birth,
                            place=place.strip(),
                            is_active=is_active,
                            has_given_consent=has_given_consent,
                        )
                        if success:
                            st.success(msg)
                            del st.session_state.edit_user  # Clear edit state
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

            with col2:
                if st.form_submit_button("❌ Cancel"):
                    del st.session_state.edit_user
                    st.rerun()


def render_users_page():
    # Page header with styling
    st.markdown(
        """
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center;">👥 Users Management</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Get token from session state (no need to validate again)
    token = st.session_state.get("token")
    if not token:
        st.error("❌ No authentication token found. Please log in again.")
        return

    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["📋 View Users", "🔍 Search User", "➕ Add New User"])

    with tab1:
        st.markdown("### All Users")
        if st.button("🔄 Refresh Users", type="secondary"):
            st.rerun()

        all_users = fetch_all_users(token)
        if all_users:
            # Create a more readable table
            display_data = []
            for u in all_users:
                display_data.append(
                    {
                        "ID": u.get("id", "")[:8] + "...",
                        "Name": u.get("name", ""),
                        "Email": u.get("email", ""),
                        "Phone": u.get("phone", ""),
                        "Gender": u.get("gender", ""),
                        "Active": "✅" if u.get("is_active") else "❌",
                    }
                )
            st.dataframe(display_data, use_container_width=True)
        else:
            st.info("📭 No users found.")

    with tab2:
        st.markdown("### Search User by ID")

        col1, col2 = st.columns([3, 1])
        with col1:
            user_id = st.text_input(
                "Enter User ID",
                placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9",
            )
        with col2:
            search_clicked = st.button("🔍 Search", type="primary")

        searched_user = None
        if search_clicked:
            if user_id.strip():
                with st.spinner("Searching..."):
                    searched_user = fetch_user_by_id(token, user_id.strip())
                if not searched_user:
                    st.error("❌ User not found.")
            else:
                st.warning("⚠️ Please enter a valid User ID.")

        # Display user details if found
        if searched_user:
            st.markdown("### User Details")
            with st.container():
                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**ID:** `{searched_user.get('id', '')}`")
                    st.markdown(f"**Name:** {searched_user.get('name', '')}")
                    st.markdown(f"**Email:** {searched_user.get('email', '')}")
                    st.markdown(f"**Phone:** {searched_user.get('phone', '')}")

                with col2:
                    st.markdown(f"**Gender:** {searched_user.get('gender', '')}")
                    st.markdown(
                        f"**Date of Birth:** {searched_user.get('date_of_birth', '')}"
                    )
                    st.markdown(f"**Place:** {searched_user.get('place', '')}")
                    st.markdown(
                        f"**Active:** {'✅ Yes' if searched_user.get('is_active') else '❌ No'}"
                    )

                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✏️ Edit User", key=f"edit_{searched_user['id']}", type="primary"
                    ):
                        st.session_state.edit_user = (
                            searched_user  # Set the edit_user state
                        )
                        st.rerun()

                with col2:
                    confirm = st.checkbox("🗑️ Confirm deletion")
                    if st.button(
                        "🗑️ Delete User",
                        key=f"delete_{searched_user['id']}",
                        disabled=not confirm,
                        type="secondary",
                    ):
                        with st.spinner("Deleting..."):
                            success, msg = delete_user(token, searched_user["id"])
                        if success:
                            st.success(msg)
                            del st.session_state.edit_user  # Clear edit state if any
                            st.rerun()
                        else:
                            st.error(msg)

    with tab3:
        # Only show create form if not editing
        if not getattr(st.session_state, "edit_user", None):
            st.markdown("### Add New User")
            st.markdown("---")

            with st.form("create_user_form"):
                col1, col2 = st.columns(2)

                with col1:
                    name = st.text_input("Name *", placeholder="Enter full name")
                    email = st.text_input("Email *", placeholder="user@example.com")
                    phone = st.text_input("Phone Number *", placeholder="+91XXXXXXXXXX")
                    gender = st.selectbox("Gender", ["male", "female", "other"])

                with col2:
                    dob = st.date_input(
                        "Date of Birth",
                        value=datetime.today() - timedelta(days=365 * 20),
                    ).strftime("%Y-%m-%d")
                    place = st.text_input("Place", placeholder="City, State")
                    password = st.text_input(
                        "Password *", type="password", placeholder="Enter password"
                    )
                    role_ids = st.multiselect("Role IDs", [1, 2, 3], default=[2])

                st.markdown("---")

                if st.form_submit_button("✅ Create User", type="primary"):
                    if not all(
                        [name.strip(), email.strip(), phone.strip(), password.strip()]
                    ):
                        st.error("❌ All fields marked with * are required.")
                    else:
                        with st.spinner("Creating user..."):
                            success, msg = create_user(
                                token,
                                name.strip(),
                                email.strip(),
                                phone.strip(),
                                gender,
                                dob,
                                place.strip(),
                                password,
                                role_ids,
                            )
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {msg}")

    # Render Update User Form (if triggered) - outside tabs
    if getattr(st.session_state, "edit_user", None):
        st.markdown("---")
        render_update_user_form(
            user_id=st.session_state.edit_user["id"],
            current_user_data=st.session_state.edit_user,
        )
