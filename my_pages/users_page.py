import streamlit as st
import requests
from datetime import datetime, timedelta

# API URLs
USERS_API_URL = "https://backend2.swecha.org/api/v1/users/" 
AUTH_ME_URL = "https://backend2.swecha.org/api/v1/auth/me/" 

def COMMON_HEADERS(token):
    return {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

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
        "has_given_consent": True
    }
    try:
        headers = COMMON_HEADERS(token)
        r = requests.post(USERS_API_URL, json=data, headers=headers)
        if r.status_code == 201:
            return True, "User created successfully."
        return False, r.json().get("detail", "Error creating user.")
    except Exception as e:
        return False, f"Network error: {e}"

def update_user(token, user_id, name, email, gender, date_of_birth, place, is_active, has_given_consent):
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
        "has_given_consent": has_given_consent
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
    st.subheader("Update User")

    # Pre-fill form fields with current user data
    name = st.text_input("Name", value=current_user_data.get("name", ""))
    email = st.text_input("Email", value=current_user_data.get("email", ""))
    gender = st.selectbox(
        "Gender",
        ["male", "female", "other"],
        index=["male", "female", "other"].index(current_user_data.get("gender", "male"))
    )
    date_of_birth = st.date_input(
        "Date of Birth",
        value=datetime.strptime(current_user_data.get("date_of_birth", ""), "%Y-%m-%d")
        if current_user_data.get("date_of_birth")
        else datetime.today() - timedelta(days=365 * 20)  # Default to 20 years ago
    ).strftime("%Y-%m-%d")
    place = st.text_input("Place", value=current_user_data.get("place", ""))
    is_active = st.checkbox("Is Active", value=current_user_data.get("is_active", True))
    has_given_consent = st.checkbox("Has Given Consent", value=current_user_data.get("has_given_consent", True))

    if st.form_submit_button("Update"):
        success, msg = update_user(
            token=st.session_state.token,
            user_id=user_id,
            name=name,
            email=email,
            gender=gender,
            date_of_birth=date_of_birth,
            place=place,
            is_active=is_active,
            has_given_consent=has_given_consent
        )
        if success:
            st.success(msg)
            del st.session_state.edit_user  # Clear edit state
            st.rerun()
        else:
            st.error(f"Error: {msg}")

def render_users_page():
    st.title("Users Management")

    # Validate token before proceeding
    token = st.session_state.get("token")
    if not token:
        st.warning("Session expired. Please login again.")
        st.session_state.logged_in = False
        st.session_state.token = None
        st.session_state.page = "login"
        st.rerun()

    # Button to fetch all users
    if st.button("Get All Users"):
        all_users = fetch_all_users(token)
        if all_users:
            st.subheader("All Users")
            st.table([{k: u.get(k) for k in ["id", "name", "email", "phone", "gender", "date_of_birth", "place"]} for u in all_users])
        else:
            st.info("No users found.")

    # Search bar at the top
    st.subheader("Search User")
    user_id = st.text_input("Enter User ID to search", placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9")
    searched_user = None

    if st.button("Search"):
        if user_id:
            searched_user = fetch_user_by_id(token, user_id)
            if not searched_user:
                st.error("User not found.")
        else:
            st.warning("Please enter a valid User ID.")

    # Display user details if found
    if searched_user:
        st.subheader("User Details")
        st.write({
            "ID": searched_user.get("id"),
            "Name": searched_user.get("name"),
            "Email": searched_user.get("email"),
            "Phone": searched_user.get("phone"),
            "Gender": searched_user.get("gender"),
            "Date of Birth": searched_user.get("date_of_birth"),
            "Place": searched_user.get("place")
        })

        # Edit and Delete buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit User", key=f"edit_{searched_user['id']}"):
                st.session_state.edit_user = searched_user  # Set the edit_user state
                st.rerun()
        with col2:
            confirmation = st.checkbox("Are you sure you want to delete this user?")
            if st.button("Delete User", key=f"delete_{searched_user['id']}") and confirmation:
                success, msg = delete_user(token, searched_user["id"])
                if success:
                    st.success(msg)
                    del st.session_state.edit_user  # Clear edit state if any
                    st.rerun()
                else:
                    st.error(msg)

    # Render Update User Form (if triggered)
    if getattr(st.session_state, "edit_user", None):
        render_update_user_form(
            user_id=st.session_state.edit_user["id"],
            current_user_data=st.session_state.edit_user
        )

    # Add new user section (only if not editing)
    if not getattr(st.session_state, "edit_user", None):
        st.subheader("Add New User")
        with st.form("create_user_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number", placeholder="+91XXXXXXXXXX")
            gender = st.selectbox("Gender", ["male", "female", "other"])
            dob = st.date_input("Date of Birth", value=datetime.today() - timedelta(days=365 * 20)).strftime("%Y-%m-%d")
            place = st.text_input("Place")
            password = st.text_input("Password", type="password")
            role_ids = st.multiselect("Role IDs", [1, 2, 3], default=[2])

            if st.form_submit_button("Create"):
                if not all([name, email, phone, password]):
                    st.error("All fields except place are required.")
                else:
                    success, msg = create_user(token, name, email, phone, gender, dob, place, password, role_ids)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")