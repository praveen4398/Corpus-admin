import re
from datetime import datetime

import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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


def is_records_cache_stale(max_age_minutes=30):
    """Check if the cached records data is stale and needs refresh."""
    if 'records_cache_timestamp' not in st.session_state:
        return True
    
    cache_timestamp = st.session_state.records_cache_timestamp
    if not isinstance(cache_timestamp, datetime):
        return True
    
    age = datetime.now() - cache_timestamp
    return age.total_seconds() > (max_age_minutes * 60)


def clear_records_cache():
    """Clear the cached records data."""
    if 'records_cache' in st.session_state:
        del st.session_state.records_cache
    if 'records_cache_timestamp' in st.session_state:
        del st.session_state.records_cache_timestamp


def fetch_all_records(token):
    """Fetch all records from the backend using pagination with caching."""
    try:
        # Check if we already have records stored in session state and cache is not stale
        if ('records_cache' in st.session_state and 
            st.session_state.records_cache and 
            not is_records_cache_stale()):
            st.info(f"📋 Using cached data: {len(st.session_state.records_cache)} records")
            return st.session_state.records_cache
        
        headers = COMMON_HEADERS(token)
        all_records = []
        skip = 0
        limit = 1000  # Maximum allowed by API
        
        with st.spinner("Loading all records..."):
            progress_bar = st.progress(0)
            batch_count = 0
            
            while True:
                params = {"skip": skip, "limit": limit}
                response = requests.get(RECORDS_API_URL, headers=headers, params=params)
                
                if response.status_code == 200:
                    batch_records = response.json()
                    if isinstance(batch_records, list):
                        batch_size = len(batch_records)
                        
                        if not batch_records:  # Empty response, we've reached the end
                            break
                        
                        all_records.extend(batch_records)
                        skip += limit
                        batch_count += 1
                        
                        # Update progress (estimate based on typical response size)
                        progress = min(0.9, batch_count * 0.1)  # Assume ~10 batches max
                        progress_bar.progress(progress)
                        
                        # If we got less than limit, we've reached the end
                        if batch_size < limit:
                            break
                    else:
                        st.error("Unexpected response format from the server.")
                        break
                else:
                    st.error(
                        f"Failed to fetch records batch. Status Code: {response.status_code} - {response.text}"
                    )
                    break
            
            progress_bar.progress(1.0)
            st.success(f"✅ Loaded {len(all_records)} records in {batch_count} batches")
        
        # Store in session state for future use
        st.session_state.records_cache = all_records
        st.session_state.records_cache_timestamp = datetime.now()
        
        return all_records
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
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text or "Error deleting record."
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


def fetch_record_by_title(token, record_title, media_type_filter=None):
    """Fetch a single record by title (case-insensitive), optionally filtered by media type."""
    try:
        records = fetch_all_records(token)
        for record in records:
            if record.get("title", "").lower() == record_title.lower():
                if media_type_filter and record.get("media_type") != media_type_filter:
                    continue
                return record
        st.warning("Record not found.")
        return None
    except Exception as e:
        st.error(f"Error fetching record by title: {e}")
        return None


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
                    safe_title = str(title or "").strip()
                    safe_description = str(description or "").strip()
                    safe_user_id = str(user_id or "").strip()
                    safe_category_id = str(category_id or "").strip()
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
                            # Refresh search results if record was updated from search
                            if 'record_search_result' in st.session_state and st.session_state.record_search_result and st.session_state.record_search_result.get('uid') == record_id:
                                st.session_state.record_search_result = fetch_record_by_id(st.session_state.token, record_id)
                            del st.session_state.edit_record
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    del st.session_state.edit_record
                    st.rerun()


def create_records_visualizations(records, categories):
    """Create visualizations for records data."""
    if not records:
        return None, None
    
    # Prepare data for media type analysis
    media_type_counts = {}
    for record in records:
        media_type = record.get('media_type', 'unknown')
        media_type_counts[media_type] = media_type_counts.get(media_type, 0) + 1
    
    # Create media type chart
    media_data = [{'Media Type': k, 'Count': v} for k, v in media_type_counts.items()]
    media_df = pd.DataFrame(media_data)
    media_fig = px.bar(
        media_df, 
        x='Media Type', 
        y='Count',
        title="📊 Records by Media Type",
        color='Media Type',
        color_discrete_map={
            'text': '#1f77b4',
            'image': '#ff7f0e', 
            'video': '#2ca02c',
            'audio': '#d62728',
            'unknown': '#9467bd'
        }
    )
    media_fig.update_layout(
        xaxis_title="Media Type",
        yaxis_title="Number of Records",
        showlegend=False
    )
    
    # Prepare data for category analysis
    category_counts = {}
    category_names = {cat['id']: cat.get('title', cat.get('name', 'Unknown')) for cat in categories}
    
    for record in records:
        category_id = record.get('category_id')
        if category_id:
            category_name = category_names.get(category_id, 'Unknown')
            category_counts[category_name] = category_counts.get(category_name, 0) + 1
    
    # Create category chart
    if category_counts:
        category_data = [{'Category': k, 'Count': v} for k, v in category_counts.items()]
        category_df = pd.DataFrame(category_data)
        category_df = category_df.sort_values('Count', ascending=False)
        
        category_fig = px.pie(
            category_df,
            values='Count',
            names='Category',
            title="📈 Records by Category",
            hole=0.3
        )
        category_fig.update_traces(textposition='inside', textinfo='percent+label+value')
    else:
        category_fig = None
    
    return media_fig, category_fig


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
        
        # Cache management
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 Records data is cached for better performance. Use 'Refresh Records' to get latest data.")
        with col2:
            if st.button("🔄 Refresh Records", type="primary"):
                clear_records_cache()
                st.rerun()

        records = fetch_all_records(token)
        if records:
            # Create visualizations
            media_fig, category_fig = create_records_visualizations(records, st.session_state.categories_list)
            
            # Display charts
            col1, col2 = st.columns(2)
            
            with col1:
                if media_fig:
                    st.plotly_chart(media_fig, use_container_width=True)
                else:
                    st.info("No media type data available")
            
            with col2:
                if category_fig:
                    st.plotly_chart(category_fig, use_container_width=True)
                else:
                    st.info("No category data available")
            
            # Summary statistics
            st.markdown("### 📊 Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", len(records))
            
            with col2:
                reviewed_count = sum(1 for r in records if r.get('reviewed', False))
                st.metric("Reviewed Records", reviewed_count)
            
            with col3:
                pending_review = len(records) - reviewed_count
                st.metric("Pending Review", pending_review)
            
            with col4:
                review_rate = (reviewed_count / len(records) * 100) if records else 0
                st.metric("Review Rate", f"{review_rate:.1f}%")
            
            # Detailed records table (collapsible)
            with st.expander("📋 View Detailed Records Table"):
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
        st.markdown("### Search Record")

        # Restore search state from session or initialize
        if 'record_search_value' not in st.session_state:
            st.session_state.record_search_value = ''
        if 'record_search_mode' not in st.session_state:
            st.session_state.record_search_mode = 'ID'
        if 'record_search_result' not in st.session_state:
            st.session_state.record_search_result = None
        if 'record_search_success' not in st.session_state:
            st.session_state.record_search_success = ''

        search_mode = st.radio(
            "Search by:", ["ID", "Title"], horizontal=True, key="search_mode",
            index=["ID", "Title"].index(st.session_state.record_search_mode)
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            if search_mode == "ID":
                search_value = st.text_input(
                    "Enter Record ID",
                    value=st.session_state.record_search_value if st.session_state.record_search_mode == "ID" else '',
                    placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9",
                    key="search_id_input",
                )
            else:
                search_value = st.text_input(
                    "Enter Record Title",
                    value=st.session_state.record_search_value if st.session_state.record_search_mode == "Title" else '',
                    placeholder="e.g., My Record Title",
                    key="search_title_input",
                )
        with col2:
            media_type_filter = st.selectbox(
                "Media Type (optional)",
                ["Any", "text", "image", "video", "audio"],
                key="media_type_filter",
            )
            search_clicked = st.button("🔍 Search", type="primary", key="search_btn")

        searched_record = None
        if search_clicked:
            st.session_state.record_search_mode = search_mode
            st.session_state.record_search_value = search_value if search_value is not None else ''
            st.session_state.record_search_success = ''
            safe_search_value = str(search_value or '')
            if safe_search_value.strip():
                with st.spinner("Searching..."):
                    if search_mode == "ID":
                        searched_record = fetch_record_by_id(token, safe_search_value.strip())
                        # If media type filter is set, check it
                        if (
                            searched_record
                            and media_type_filter != "Any"
                            and searched_record.get("media_type") != media_type_filter
                        ):
                            searched_record = None
                    else:
                        mt = media_type_filter if media_type_filter != "Any" else None
                        searched_record = fetch_record_by_title(token, safe_search_value.strip(), mt)
                    st.session_state.record_search_result = searched_record
                if not searched_record:
                    st.error("❌ Record not found.")
            else:
                st.warning(f"⚠️ Please enter a valid Record {search_mode}.")

        # Use session state for displaying results after rerun
        search_mode = st.session_state.record_search_mode
        search_value = st.session_state.record_search_value
        searched_record = st.session_state.record_search_result
        if st.session_state.record_search_success:
            st.success(st.session_state.record_search_success)
            st.session_state.record_search_success = ''

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
                    confirm = st.checkbox("🗑️ Confirm deletion", key=f"confirm_delete_{searched_record['uid']}")
                    if st.button(
                        "🗑️ Delete Record",
                        key=f"delete_{searched_record['uid']}",
                        disabled=not confirm,
                        type="secondary",
                    ):
                        with st.spinner("Deleting..."):
                            success, msg = delete_record(token, searched_record["uid"])
                        if success:
                            st.session_state.record_search_success = msg
                            st.session_state.record_search_result = None
                            if hasattr(st.session_state, "edit_record"):
                                del st.session_state.edit_record
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
