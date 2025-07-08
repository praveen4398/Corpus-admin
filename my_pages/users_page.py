from datetime import datetime, timedelta

import requests
import streamlit as st
import pandas as pd
import plotly.express as px

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


def fetch_all_users_batched(token, batch_size=1000):
    """Fetch all users in batches and cache them."""
    try:
        # Use cache if available and not stale
        if ('all_users_cache' in st.session_state and 
            st.session_state.all_users_cache and 
            not is_cache_stale()):
            return st.session_state.all_users_cache
        
        headers = COMMON_HEADERS(token)
        all_users = []
        skip = 0
        while True:
            params = {"skip": skip, "limit": batch_size}
            r = requests.get(USERS_API_URL, params=params, headers=headers)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    if not data:
                        break
                    all_users.extend(data)
                    skip += batch_size
                    if len(data) < batch_size:
                        break
                else:
                    st.error("Unexpected response format from the server.")
                    break
            else:
                st.error(f"Failed to fetch users. Status Code: {r.status_code}")
                break
        st.session_state.all_users_cache = all_users
        st.session_state.all_users_cache_timestamp = datetime.now()
        return all_users
    except Exception as e:
        st.error(f"Network error: {e}")
        return []


def is_cache_stale(max_age_minutes=30):
    """Check if the cached data is stale and needs refresh."""
    if 'all_users_cache_timestamp' not in st.session_state:
        return True
    
    cache_timestamp = st.session_state.all_users_cache_timestamp
    if not isinstance(cache_timestamp, datetime):
        return True
    
    age = datetime.now() - cache_timestamp
    return age.total_seconds() > (max_age_minutes * 60)


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
        if r.status_code == 200:
            try:
                message = r.json().get("message", "User deleted successfully.")
            except Exception:
                message = "User deleted successfully."
            return True, message, 200
        try:
            detail = r.json().get("detail", "Error deleting user.")
        except Exception:
            detail = r.text or "Error deleting user."
        return False, detail, r.status_code
    except Exception as e:
        return False, f"Network error: {e}", None


def fetch_users_by_name(token, user_name):
    """Fetch all users by name (case-insensitive)."""
    try:
        users = fetch_all_users_batched(token)
        matches = [user for user in users if user.get("name", "").lower() == user_name.lower()]
        if not matches:
            st.warning("No users found with that name.")
        return matches
    except Exception as e:
        st.error(f"Error fetching users by name: {e}")
        return []


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
                    safe_name = str(name or "")
                    safe_email = str(email or "")
                    safe_place = str(place or "")
                    if not safe_name.strip() or not safe_email.strip():
                        st.error("Name and Email are required.")
                    else:
                        success, msg = update_user(
                            token=st.session_state.token,
                            user_id=user_id,
                            name=safe_name.strip(),
                            email=safe_email.strip(),
                            gender=gender,
                            date_of_birth=date_of_birth,
                            place=safe_place.strip(),
                            is_active=is_active,
                            has_given_consent=has_given_consent,
                        )
                        if success:
                            st.success(msg)
                            # Refresh search results if user was updated from search
                            if 'user_search_single' in st.session_state and st.session_state.user_search_single and st.session_state.user_search_single['id'] == user_id:
                                st.session_state.user_search_single = fetch_user_by_id(st.session_state.token, user_id)
                            if 'user_search_results' in st.session_state and st.session_state.user_search_results:
                                st.session_state.user_search_results = [fetch_user_by_id(st.session_state.token, u['id']) if u['id'] == user_id else u for u in st.session_state.user_search_results]
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
        
        # Cache management
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔄 Refresh Users", type="secondary"):
                if 'all_users_cache' in st.session_state:
                    del st.session_state.all_users_cache
                if 'all_users_cache_timestamp' in st.session_state:
                    del st.session_state.all_users_cache_timestamp
                st.rerun()
        with col2:
            if st.button("🗑️ Clear Cache", type="secondary"):
                if 'all_users_cache' in st.session_state:
                    del st.session_state.all_users_cache
                if 'all_users_cache_timestamp' in st.session_state:
                    del st.session_state.all_users_cache_timestamp
                st.rerun()

        # Show cache info if available
        if 'all_users_cache' in st.session_state and st.session_state.all_users_cache:
            cache_timestamp = st.session_state.get('all_users_cache_timestamp', 'Unknown')
            if isinstance(cache_timestamp, datetime):
                cache_time_str = cache_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                cache_time_str = str(cache_timestamp)
            st.success(f"✅ Cached {len(st.session_state.all_users_cache)} users (last updated: {cache_time_str})")

        # --- Fetch all users (not just 1000) ---
        all_users = fetch_all_users_batched(token, batch_size=1000)
        if all_users:
            # --- Summary Metrics ---
            total_users = len(all_users)
            active_users = sum(1 for u in all_users if u.get('is_active'))
            inactive_users = total_users - active_users
            gender_counts = {'male': 0, 'female': 0, 'other': 0, 'unknown': 0}
            for u in all_users:
                gender = (u.get('gender') or 'unknown').lower().strip()
                if gender in ['male', 'm']:
                    gender_counts['male'] += 1
                elif gender in ['female', 'f']:
                    gender_counts['female'] += 1
                elif gender in ['other', 'o']:
                    gender_counts['other'] += 1
                else:
                    gender_counts['unknown'] += 1
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", total_users)
            with col2:
                st.metric("Active Users", active_users)
            with col3:
                st.metric("Inactive Users", inactive_users)
            
            # --- Charts ---
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                # Gender Pie Chart
                gender_labels = [k.title() for k in gender_counts.keys() if gender_counts[k] > 0]
                gender_values = [v for k, v in gender_counts.items() if v > 0]
                if gender_values:
                    fig = px.pie(
                        names=gender_labels,
                        values=gender_values,
                        title="Gender Distribution",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label+value')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No gender data available.")
            with chart_col2:
                # Active/Inactive Bar Chart
                status_df = pd.DataFrame({
                    'Status': ['Active', 'Inactive'],
                    'Count': [active_users, inactive_users]
                })
                fig2 = px.bar(
                    status_df,
                    x='Status',
                    y='Count',
                    title="User Status",
                    color='Status',
                    color_discrete_map={'Active': '#4CAF50', 'Inactive': '#FF9800'}
                )
                fig2.update_layout(xaxis_title="Status", yaxis_title="Number of Users", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            
            # --- Registration Date Plot ---
            reg_dates = [u.get('created_at', '')[:10] for u in all_users if u.get('created_at')]
            if reg_dates:
                reg_df = pd.DataFrame({'Registration Date': reg_dates})
                reg_count = reg_df['Registration Date'].value_counts().sort_index()
                reg_plot_df = pd.DataFrame({'Date': reg_count.index, 'Count': reg_count.values})
                fig3 = px.bar(
                    reg_plot_df,
                    x='Date',
                    y='Count',
                    title="Users by Registration Date",
                    labels={'Date': 'Registration Date', 'Count': 'Number of Users'}
                )
                fig3.update_layout(xaxis_title="Registration Date", yaxis_title="Number of Users")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No registration date data available.")
            
            # --- Detailed Table in Expander ---
            with st.expander("📋 View Detailed Users Table"):
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
                            "Created": u.get("created_at", "")[:10] if u.get("created_at") else "",
                            "Last Login": u.get("last_login_at", "")[:10] if u.get("last_login_at") else ""
                        }
                    )
                st.dataframe(display_data, use_container_width=True)
                st.info(f"Showing {len(all_users)} users")
        else:
            st.info(" No users found.")

    with tab2:
        st.markdown("### Search User")

        # Restore search state from session or initialize
        if 'user_search_value' not in st.session_state:
            st.session_state.user_search_value = ''
        if 'user_search_mode' not in st.session_state:
            st.session_state.user_search_mode = 'ID'
        if 'user_search_results' not in st.session_state:
            st.session_state.user_search_results = []
        if 'user_search_single' not in st.session_state:
            st.session_state.user_search_single = None
        if 'user_search_success' not in st.session_state:
            st.session_state.user_search_success = ''

        search_mode = st.radio(
            "Search by:", ["ID", "Name"], horizontal=True, key="search_mode",
            index=["ID", "Name"].index(st.session_state.user_search_mode)
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            if search_mode == "ID":
                search_value = st.text_input(
                    "Enter User ID",
                    value=st.session_state.user_search_value if st.session_state.user_search_mode == "ID" else '',
                    placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9",
                    key="search_id_input",
                )
            else:
                search_value = st.text_input(
                    "Enter User Name",
                    value=st.session_state.user_search_value if st.session_state.user_search_mode == "Name" else '',
                    placeholder="e.g., John Doe",
                    key="search_name_input",
                )
        with col2:
            search_clicked = st.button("🔍 Search", type="primary", key="search_btn")

        searched_users = []
        searched_user = None
        if search_clicked:
            st.session_state.user_search_mode = search_mode
            st.session_state.user_search_value = search_value if search_value is not None else ''
            st.session_state.user_search_success = ''
            safe_search_value = str(search_value or '')
            if safe_search_value.strip():
                with st.spinner("Searching..."):
                    if search_mode == "ID":
                        searched_user = fetch_user_by_id(token, safe_search_value.strip())
                        st.session_state.user_search_single = searched_user
                        st.session_state.user_search_results = []
                    else:
                        searched_users = fetch_users_by_name(token, safe_search_value.strip())
                        st.session_state.user_search_results = searched_users
                        st.session_state.user_search_single = None
                if search_mode == "ID" and not searched_user:
                    st.error("❌ User not found.")
                elif search_mode == "Name" and not searched_users:
                    st.error("❌ No users found with that name.")
            else:
                st.warning(f"⚠️ Please enter a valid User {search_mode}.")

        # Use session state for displaying results after rerun
        search_mode = st.session_state.user_search_mode
        search_value = st.session_state.user_search_value
        searched_user = st.session_state.user_search_single
        searched_users = st.session_state.user_search_results
        if st.session_state.user_search_success:
            st.success(st.session_state.user_search_success)
            st.session_state.user_search_success = ''

        safe_search_value = str(search_value or '')

        # Display user details if found
        if search_mode == "ID" and searched_user:
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
                    st.markdown(f"**Date of Birth:** {searched_user.get('date_of_birth', '')}")
                    st.markdown(f"**Place:** {searched_user.get('place', '')}")
                    st.markdown(f"**Active:** {'✅ Yes' if searched_user.get('is_active') else '❌ No'}")
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✏️ Edit User", key=f"edit_{searched_user['id']}", type="primary"
                    ):
                        st.session_state.edit_user = searched_user
                        st.rerun()
                with col2:
                    confirm_key = f"confirm_delete_{searched_user['id']}"
                    confirm = st.checkbox("🗑️ Confirm deletion", key=confirm_key)
                    if confirm:
                        if st.button(
                            "🗑️ Delete User",
                            key=f"delete_{searched_user['id']}",
                            type="secondary",
                        ):
                            with st.spinner("Deleting..."):
                                success, msg, status = delete_user(token, searched_user["id"])
                            if success:
                                st.session_state.user_search_success = msg
                                st.session_state.user_search_single = None
                                st.session_state.user_search_results = []
                                if hasattr(st.session_state, "edit_user"):
                                    del st.session_state.edit_user
                                st.rerun()
                            else:
                                if status == 500:
                                    st.error("Internal server error. Please contact the administrator or check backend logs.")
                                else:
                                    st.error(f"Error: {msg} (Status code: {status})")
        elif search_mode == "Name" and searched_users:
            st.markdown(f"### Users with name '{safe_search_value.strip()}'")
            for idx, user in enumerate(searched_users):
                with st.container():
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**ID:** `{user.get('id', '')}`")
                        st.markdown(f"**Name:** {user.get('name', '')}")
                        st.markdown(f"**Email:** {user.get('email', '')}")
                        st.markdown(f"**Phone:** {user.get('phone', '')}")
                    with col2:
                        st.markdown(f"**Gender:** {user.get('gender', '')}")
                        st.markdown(f"**Date of Birth:** {user.get('date_of_birth', '')}")
                        st.markdown(f"**Place:** {user.get('place', '')}")
                        st.markdown(f"**Active:** {'✅ Yes' if user.get('is_active') else '❌ No'}")
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "✏️ Edit User", key=f"edit_{user['id']}_{idx}", type="primary"
                        ):
                            st.session_state.edit_user = user
                            st.rerun()
                    with col2:
                        confirm_key = f"confirm_delete_{user['id']}_{idx}"
                        confirm = st.checkbox("🗑️ Confirm deletion", key=confirm_key)
                        if confirm:
                            if st.button(
                                "🗑️ Delete User",
                                key=f"delete_{user['id']}_{idx}",
                                type="secondary",
                            ):
                                with st.spinner("Deleting..."):
                                    success, msg, status = delete_user(token, user["id"])
                                if success:
                                    st.session_state.user_search_success = msg
                                    # Remove deleted user from results
                                    st.session_state.user_search_results = [u for u in st.session_state.user_search_results if u['id'] != user['id']]
                                    if hasattr(st.session_state, "edit_user"):
                                        del st.session_state.edit_user
                                    st.rerun()
                                else:
                                    if status == 500:
                                        st.error("Internal server error. Please contact the administrator or check backend logs.")
                                    else:
                                        st.error(f"Error: {msg} (Status code: {status})")

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
