import re

import requests
import streamlit as st

# API URLs
RECORDS_API_URL = "https://backend2.swecha.org/api/v1/records/"
RECORDS_UPLOAD_URL = "https://backend2.swecha.org/api/v1/records/upload"
CATEGORIES_API_URL = "https://backend2.swecha.org/api/v1/categories/"
AUTH_ME_URL = "https://backend2.swecha.org/api/v1/auth/me/"


def COMMON_HEADERS(token):
    return {"accept": "application/json", "Authorization": f"Bearer {token}"}


def is_authenticated(token: str) -> bool:
    """Verify if the token is valid using /auth/me."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(AUTH_ME_URL, headers=headers)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Auth check failed: {e}")
        return False


def fetch_all_records(token):
    """Fetch all records from the backend."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(RECORDS_API_URL, headers=headers)
        print("RECORDS FETCH RESPONSE:", response.status_code, response.text)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"Failed to fetch records: {response.status_code} - {response.text}"
            )
            return []
    except Exception as e:
        st.error(f"Network error while fetching records: {e}")
        return []


def fetch_record_by_id(token, record_id):
    """Fetch a single record by ID."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(f"{RECORDS_API_URL}/{record_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning("Record not found.")
            return None
    except Exception as e:
        st.error(f"Error fetching record: {e}")
        return None


def fetch_all_categories(token):
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(CATEGORIES_API_URL, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning("Failed to fetch categories.")
            return []
    except Exception as e:
        st.error(f"Network error while fetching categories: {e}")
        return []


def fetch_user_id(token):
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(AUTH_ME_URL, headers=headers)
        if response.status_code == 200:
            return response.json().get("id")
        else:
            st.warning("Failed to fetch user info.")
            return None
    except Exception as e:
        st.error(f"Network error while fetching user info: {e}")
        return None


def ascii_filename(filename):
    # Replace non-ASCII characters with underscore
    return re.sub(r"[^A-Za-z0-9_.-]", "_", filename)


def upload_record(token, title, description, media_type, file, user_id, category_id):
    safe_filename = ascii_filename(file.name)
    files = {"file": (safe_filename, file, file.type)}
    data = {
        "title": title,
        "description": description or "",
        "media_type": media_type,
        "use_uid_filename": "false",
        "latitude": "0",
        "longitude": "0",
        "user_id": user_id,
        "category_id": category_id,
    }
    headers = {"accept": "application/json", "Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            RECORDS_UPLOAD_URL, headers=headers, data=data, files=files
        )
        if response.status_code in [200, 201]:
            return True, "Record uploaded successfully."
        else:
            # Try to show backend error details
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            return False, f"File upload failed: {response.status_code}: {detail}"
    except Exception as e:
        return False, f"Network error: {e}"


def delete_record(token, record_id):
    """Delete a record by ID."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.delete(f"{RECORDS_API_URL}{record_id}", headers=headers)
        if response.status_code == 204:
            return True, "Record deleted successfully."
        else:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            return False, f"Delete failed: {response.status_code}: {detail}"
    except Exception as e:
        return False, f"Network error: {e}"


def update_record(
    token, record_id, title, description, media_type, user_id, category_id
):
    """Update a record by ID."""
    data = {
        "title": title,
        "description": description or "",
        "media_type": media_type,
        "user_id": user_id,
        "category_id": category_id,
    }
    headers = COMMON_HEADERS(token)
    try:
        response = requests.put(
            f"{RECORDS_API_URL}{record_id}", json=data, headers=headers
        )
        if response.status_code == 200:
            return True, "Record updated successfully."
        else:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            return False, f"Update failed: {response.status_code}: {detail}"
    except Exception as e:
        return False, f"Network error: {e}"


def render_update_record_form(record_id, current_data):
    """Render a form to update a record."""
    with st.container():
        st.markdown("### ✏️ Update Record")
        st.markdown("---")
        with st.form("update_record_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Title", value=current_data.get("title", ""))
                media_type = st.selectbox(
                    "Media Type",
                    ["text", "image", "video", "audio"],
                    index=["text", "image", "video", "audio"].index(
                        current_data.get("media_type", "text")
                    ),
                )
            with col2:
                description = st.text_area(
                    "Description (optional)",
                    value=current_data.get("description", ""),
                    height=100,
                )
                # Category selection
                categories = st.session_state.categories_list or []
                category_options = {
                    f"{c.get('title', c.get('name', ''))}": c["id"] for c in categories
                }
                category_label = None
                category_id = current_data.get("category_id")
                if category_options:
                    # Find label for current category
                    for label, cid in category_options.items():
                        if cid == category_id:
                            category_label = label
                            break
                    category_label = st.selectbox(
                        "Category *",
                        list(category_options.keys()),
                        index=list(category_options.keys()).index(category_label)
                        if category_label
                        else 0,
                    )
                    category_id = category_options[category_label]
            user_id = st.session_state.user_id
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Update", type="primary"):
                    safe_title = (title or "").strip()
                    safe_description = (description or "").strip()
                    safe_user_id = (user_id or "").strip()
                    safe_category_id = (category_id or "").strip()
                    if not safe_title:
                        st.error("❌ Title is required.")
                    elif not safe_user_id:
                        st.error("❌ User ID is required.")
                    elif not safe_category_id:
                        st.error("❌ Category is required.")
                    else:
                        with st.spinner("Updating record..."):
                            success, msg = update_record(
                                st.session_state.token,
                                record_id,
                                safe_title,
                                safe_description,
                                media_type,
                                safe_user_id,
                                safe_category_id,
                            )
                        if success:
                            st.success(msg)
                            del st.session_state.edit_record
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    del st.session_state.edit_record
                    st.rerun()


def render_records_page():
    # Page header with styling
    st.markdown(
        """
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center;">📄 Records Management</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Get token from session state (no need to validate again)
    token = st.session_state.get("token")
    if not token:
        st.error("❌ No authentication token found. Please log in again.")
        return

    # Fetch user_id and categories only once and cache in session
    if "categories_list" not in st.session_state:
        st.session_state.categories_list = fetch_all_categories(token)
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ User ID not found in session. Please log out and log in again.")
        return

    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(
        ["📋 View Records", "🔍 Search Record", "➕ Add New Record"]
    )

    with tab1:
        st.markdown("### All Records")
        if st.button("🔄 Refresh Records", type="secondary"):
            st.rerun()

        records = fetch_all_records(token)
        if records:
            # Create a more readable table
            display_data = []
            for r in records:
                display_data.append(
                    {
                        "ID": r.get("uid", "")[:8] + "...",
                        "Title": r.get("title", ""),
                        "Media Type": r.get("media_type", ""),
                        "Status": r.get("status", ""),
                        "Reviewed": "✅" if r.get("reviewed") else "❌",
                    }
                )
            st.dataframe(display_data, use_container_width=True)
        else:
            st.info("📭 No records found.")

    with tab2:
        st.markdown("### Search Record by ID")

        col1, col2 = st.columns([3, 1])
        with col1:
            record_id = st.text_input(
                "Enter Record ID",
                placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9",
            )
        with col2:
            search_clicked = st.button("🔍 Search", type="primary")

        searched_record = None
        if search_clicked:
            if record_id.strip():
                with st.spinner("Searching..."):
                    searched_record = fetch_record_by_id(token, record_id.strip())
                if not searched_record:
                    st.error("❌ Record not found.")
            else:
                st.warning("⚠️ Please enter a valid Record ID.")

        # Display record details
        if searched_record:
            st.markdown("### Record Details")
            with st.container():
                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**ID:** `{searched_record.get('uid', '')}`")
                    st.markdown(f"**Title:** {searched_record.get('title', '')}")
                    st.markdown(
                        f"**Media Type:** {searched_record.get('media_type', '')}"
                    )
                    st.markdown(f"**Status:** {searched_record.get('status', '')}")

                with col2:
                    st.markdown(
                        f"**Reviewed:** {'✅ Yes' if searched_record.get('reviewed') else '❌ No'}"
                    )
                    st.markdown(
                        f"**File Name:** {searched_record.get('file_name', 'N/A')}"
                    )
                    st.markdown(
                        f"**File Size:** {searched_record.get('file_size', 0)} bytes"
                    )
                    st.markdown(
                        f"**Description:** {searched_record.get('description', 'No description')}"
                    )

                # Location info
                location = searched_record.get("location", {})
                if location:
                    st.markdown(
                        f"**Location:** {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}"
                    )

                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✏️ Edit Record",
                        key=f"edit_{searched_record['uid']}",
                        type="primary",
                    ):
                        st.session_state.edit_record = searched_record
                        st.rerun()

                with col2:
                    confirm = st.checkbox("🗑️ Confirm deletion")
                    if st.button(
                        "🗑️ Delete Record",
                        key=f"delete_{searched_record['uid']}",
                        disabled=not confirm,
                        type="secondary",
                    ):
                        with st.spinner("Deleting..."):
                            success, msg = delete_record(token, searched_record["uid"])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    with tab3:
        if not getattr(st.session_state, "edit_record", None):
            st.markdown("### Add New Record")
            st.markdown("---")
            with st.form("create_record_form"):
                title = st.text_input("Title *", placeholder="Enter record title")
                description = st.text_area(
                    "Description (optional)",
                    placeholder="Enter record description",
                    height=100,
                )
                media_type = st.selectbox(
                    "Media Type", ["text", "image", "video", "audio"]
                )
                file = st.file_uploader("Upload File", type=None)
                # Use dropdown for category selection
                categories = st.session_state.categories_list or []
                category_options = {
                    f"{c.get('title', c.get('name', ''))}": c["id"] for c in categories
                }
                category_label = None
                category_id = None
                if category_options:
                    category_label = st.selectbox(
                        "Category *", list(category_options.keys())
                    )
                    category_id = category_options[category_label]
                user_id = st.session_state.user_id
                submit = st.form_submit_button("✅ Upload Record", type="primary")
                if submit:
                    safe_title = (title or "").strip()
                    safe_description = (description or "").strip()
                    safe_user_id = (user_id or "").strip()
                    safe_category_id = (category_id or "").strip()
                    if not safe_title:
                        st.error("❌ Title is required.")
                    elif not file:
                        st.error("❌ Please upload a file.")
                    elif not safe_user_id:
                        st.error("❌ User ID is required.")
                    elif not safe_category_id:
                        st.error("❌ Category is required.")
                    else:
                        with st.spinner("Uploading record..."):
                            success, msg = upload_record(
                                token,
                                safe_title,
                                safe_description,
                                media_type,
                                file,
                                safe_user_id,
                                safe_category_id,
                            )
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {msg}")

    # Render update form if editing (outside tabs)
    if getattr(st.session_state, "edit_record", None):
        st.markdown("---")
        render_update_record_form(
            record_id=st.session_state.edit_record["uid"],
            current_data=st.session_state.edit_record,
        )
