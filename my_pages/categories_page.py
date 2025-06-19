import uuid
from datetime import datetime

import requests
import streamlit as st

# API URLs
CATEGORIES_API_URL = "https://backend2.swecha.org/api/v1/categories/"
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


def fetch_all_categories(token):
    """Fetch all categories from the backend."""
    try:
        print("FETCH TOKEN:", token)
        headers = {"accept": "application/json", "Authorization": f"Bearer {token}"}
        response = requests.get(CATEGORIES_API_URL, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning("Failed to fetch categories.")
            return []
    except Exception as e:
        st.error(f"Network error while fetching categories: {e}")
        return []


def fetch_category_by_id(token, category_id):
    """Fetch a single category by ID."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.get(f"{CATEGORIES_API_URL}{category_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning("Category not found.")
            return None
    except Exception as e:
        st.error(f"Error fetching category: {e}")
        return None


def fetch_category_by_name(token, category_name):
    """Fetch a single category by name (case-insensitive)."""
    try:
        categories = fetch_all_categories(token)
        for category in categories:
            if category.get("name", "").lower() == category_name.lower():
                return category
        st.warning("Category not found.")
        return None
    except Exception as e:
        st.error(f"Error fetching category by name: {e}")
        return None


def create_category(token, name, title, description, published, rank):
    """Create a new category."""
    payload = {
        "id": str(uuid.uuid4()),
        "name": name,
        "title": title,
        "description": description,
        "published": published,
        "rank": int(rank),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        headers = COMMON_HEADERS(token)
        response = requests.post(CATEGORIES_API_URL, json=payload, headers=headers)
        if response.status_code == 201:
            return True, "Category created successfully."
        else:
            return False, response.json().get("detail", "Unknown error occurred.")
    except Exception as e:
        return False, f"Network error: {e}"


def update_category(token, category_id, name, title, description, published, rank):
    """Update an existing category."""
    payload = {
        "name": name,
        "title": title,
        "description": description,
        "published": published,
        "rank": int(rank),
    }
    try:
        headers = COMMON_HEADERS(token)
        response = requests.put(
            f"{CATEGORIES_API_URL}{category_id}", json=payload, headers=headers
        )
        if response.status_code == 200:
            return True, "Category updated successfully."
        else:
            return False, response.json().get("detail", "Unknown error occurred.")
    except Exception as e:
        return False, f"Network error: {e}"


def delete_category(token, category_id):
    """Delete a category."""
    try:
        headers = COMMON_HEADERS(token)
        response = requests.delete(
            f"{CATEGORIES_API_URL}{category_id}", headers=headers
        )
        if response.status_code == 204:
            return True, "Category deleted successfully."
        try:
            detail = response.json().get("detail", "Unknown error occurred.")
        except Exception:
            detail = response.text or "Unknown error occurred."
        return False, detail
    except Exception as e:
        return False, f"Network error: {e}"


def render_update_category_form(category_id, current_data):
    """Render form to update a category."""
    with st.container():
        st.markdown("### ✏️ Update Category")
        st.markdown("---")

        # Use session state to persist error/success messages across reruns
        if "update_category_error" not in st.session_state:
            st.session_state.update_category_error = None
        if "update_category_success" not in st.session_state:
            st.session_state.update_category_success = None

        with st.form("update_category_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", value=current_data.get("name", ""))
                title = st.text_input("Title", value=current_data.get("title", ""))
                rank = st.number_input(
                    "Rank", min_value=0, step=1, value=current_data.get("rank", 0)
                )

            with col2:
                description = st.text_area(
                    "Description", value=current_data.get("description", ""), height=100
                )
                published = st.checkbox(
                    "Published", value=current_data.get("published", False)
                )

            submitted = st.form_submit_button("✅ Update", type="primary")
            cancel = st.form_submit_button("❌ Cancel")

            if submitted:
                safe_name = str(name or "")
                safe_title = str(title or "")
                safe_description = str(description or "")
                if not safe_name.strip() or not safe_title.strip():
                    st.session_state.update_category_error = (
                        "Name and Title are required."
                    )
                    st.session_state.update_category_success = None
                else:
                    success, msg = update_category(
                        token=st.session_state.token,
                        category_id=category_id,
                        name=safe_name.strip(),
                        title=safe_title.strip(),
                        description=safe_description.strip(),
                        published=published,
                        rank=rank,
                    )
                    if success:
                        st.session_state.update_category_success = msg
                        st.session_state.update_category_error = None
                        # Refresh search results if category was updated from search
                        if 'category_search_result' in st.session_state and st.session_state.category_search_result and st.session_state.category_search_result.get('id') == category_id:
                            st.session_state.category_search_result = fetch_category_by_id(token, category_id)
                        del st.session_state.edit_category
                        st.rerun()
                    else:
                        st.session_state.update_category_error = msg
                        st.session_state.update_category_success = None
            elif cancel:
                del st.session_state.edit_category
                st.session_state.update_category_error = None
                st.session_state.update_category_success = None
                st.rerun()

        # Show error or success messages outside the form
        if st.session_state.update_category_error:
            st.error(st.session_state.update_category_error)
        if st.session_state.update_category_success:
            st.success(st.session_state.update_category_success)


def render_categories_page():
    # Page header with styling
    st.markdown(
        """
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center;">📂 Categories Management</h1>
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
    tab1, tab2, tab3 = st.tabs(
        ["📋 View Categories", "🔍 Search Category", "➕ Add New Category"]
    )

    with tab1:
        st.markdown("### All Categories")
        if st.button("🔄 Refresh Categories", type="secondary"):
            st.rerun()

        categories = fetch_all_categories(token)
        if categories:
            # Create a more readable table
            display_data = []
            for c in categories:
                display_data.append(
                    {
                        "ID": c.get("id", "")[:8] + "...",
                        "Name": c.get("name", ""),
                        "Title": c.get("title", ""),
                        "Published": "✅" if c.get("published") else "❌",
                        "Rank": c.get("rank", 0),
                    }
                )
            st.dataframe(display_data, use_container_width=True)
        else:
            st.info("📭 No categories found.")

    with tab2:
        st.markdown("### Search Category")

        # Restore search state from session or initialize
        if 'category_search_value' not in st.session_state:
            st.session_state.category_search_value = ''
        if 'category_search_mode' not in st.session_state:
            st.session_state.category_search_mode = 'ID'
        if 'category_search_result' not in st.session_state:
            st.session_state.category_search_result = None
        if 'category_search_success' not in st.session_state:
            st.session_state.category_search_success = ''

        search_mode = st.radio(
            "Search by:", ["ID", "Name"], horizontal=True, key="search_mode",
            index=["ID", "Name"].index(st.session_state.category_search_mode)
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            if search_mode == "ID":
                search_value = st.text_input(
                    "Enter Category ID",
                    value=st.session_state.category_search_value if st.session_state.category_search_mode == "ID" else '',
                    placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9",
                    key="search_id_input",
                )
            else:
                search_value = st.text_input(
                    "Enter Category Name",
                    value=st.session_state.category_search_value if st.session_state.category_search_mode == "Name" else '',
                    placeholder="e.g., science",
                    key="search_name_input",
                )
        with col2:
            search_clicked = st.button("🔍 Search", type="primary", key="search_btn")

        searched_category = None
        if search_clicked:
            st.session_state.category_search_mode = search_mode
            st.session_state.category_search_value = search_value if search_value is not None else ''
            st.session_state.category_search_success = ''
            safe_search_value = str(search_value or '')
            if safe_search_value.strip():
                with st.spinner("Searching..."):
                    if search_mode == "ID":
                        searched_category = fetch_category_by_id(token, safe_search_value.strip())
                    else:
                        searched_category = fetch_category_by_name(token, safe_search_value.strip())
                    st.session_state.category_search_result = searched_category
                if not searched_category:
                    st.error("❌ Category not found.")
            else:
                st.warning(f"⚠️ Please enter a valid Category {search_mode}.")

        # Use session state for displaying results after rerun
        search_mode = st.session_state.category_search_mode
        search_value = st.session_state.category_search_value
        searched_category = st.session_state.category_search_result
        if st.session_state.category_search_success:
            st.success(st.session_state.category_search_success)
            st.session_state.category_search_success = ''

        # Display category details
        if searched_category:
            st.markdown("### Category Details")
            with st.container():
                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**ID:** `{searched_category.get('id', '')}`")
                    st.markdown(f"**Name:** {searched_category.get('name', '')}")
                    st.markdown(f"**Title:** {searched_category.get('title', '')}")

                with col2:
                    st.markdown(
                        f"**Published:** {'✅ Yes' if searched_category.get('published') else '❌ No'}"
                    )
                    st.markdown(f"**Rank:** {searched_category.get('rank', 0)}")
                    st.markdown(
                        f"**Description:** {searched_category.get('description', 'No description')}"
                    )

                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✏️ Edit Category",
                        key=f"edit_{searched_category['id']}",
                        type="primary",
                    ):
                        st.session_state.edit_category = searched_category
                        st.rerun()

                with col2:
                    confirm = st.checkbox(
                        "🗑️ Confirm deletion",
                        key=f"confirm_delete_{searched_category['id']}",
                    )
                    if st.button(
                        "🗑️ Delete Category",
                        key=f"delete_{searched_category['id']}",
                        disabled=not confirm,
                        type="secondary",
                    ):
                        with st.spinner("Deleting..."):
                            success, msg = delete_category(
                                token, searched_category["id"]
                            )
                        if success:
                            st.session_state.category_search_success = msg
                            st.session_state.category_search_result = None
                            if hasattr(st.session_state, "edit_category"):
                                del st.session_state.edit_category
                            st.rerun()
                        else:
                            st.error(msg)

    with tab3:
        # Only show create form if not editing
        if not getattr(st.session_state, "edit_category", None):
            st.markdown("### Add New Category")
            st.markdown("---")

            with st.form("create_category_form"):
                col1, col2 = st.columns(2)

                with col1:
                    name = st.text_input("Name *", placeholder="Enter category name")
                    title = st.text_input("Title *", placeholder="Enter category title")
                    rank = st.number_input("Rank", min_value=0, step=1, value=0)

                with col2:
                    description = st.text_area(
                        "Description",
                        placeholder="Enter category description",
                        height=100,
                    )
                    published = st.checkbox("Published", value=False)

                st.markdown("---")

                if st.form_submit_button("✅ Create Category", type="primary"):
                    if not name.strip() or not title.strip():
                        st.error("❌ Name and Title are required.")
                    else:
                        with st.spinner("Creating category..."):
                            success, msg = create_category(
                                token,
                                name.strip(),
                                title.strip(),
                                description.strip(),
                                published,
                                rank,
                            )
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {msg}")

    # Render update form if editing (outside tabs)
    if getattr(st.session_state, "edit_category", None):
        st.markdown("---")
        render_update_category_form(
            category_id=st.session_state.edit_category["id"],
            current_data=st.session_state.edit_category,
        )
