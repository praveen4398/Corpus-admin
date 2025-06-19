import streamlit as st
from datetime import datetime
import uuid
import requests

# API URLs
CATEGORIES_API_URL = "https://backend2.swecha.org/api/v1/categories/" 
AUTH_ME_URL = "https://backend2.swecha.org/api/v1/auth/me/" 

def COMMON_HEADERS(token):
    return {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
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
        "updated_at": datetime.utcnow().isoformat() + "Z"
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
        "rank": int(rank)
    }
    try:
        headers = COMMON_HEADERS(token)
        response = requests.put(f"{CATEGORIES_API_URL}{category_id}", json=payload, headers=headers)
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
        response = requests.delete(f"{CATEGORIES_API_URL}{category_id}", headers=headers)
        if response.status_code == 204:
            return True, "Category deleted successfully."
        else:
            return False, response.json().get("detail", "Unknown error occurred.")
    except Exception as e:
        return False, f"Network error: {e}"

def render_update_category_form(category_id, current_data):
    """Render form to update a category."""
    st.subheader("Update Category")

    name = st.text_input("Name", value=current_data.get("name", ""))
    title = st.text_input("Title", value=current_data.get("title", ""))
    description = st.text_area("Description", value=current_data.get("description", ""))
    published = st.checkbox("Published", value=current_data.get("published", False))
    rank = st.number_input("Rank", min_value=0, step=1, value=current_data.get("rank", 0))

    if st.form_submit_button("Update Category"):
        success, msg = update_category(
            token=st.session_state.token,
            category_id=category_id,
            name=name,
            title=title,
            description=description,
            published=published,
            rank=rank
        )
        if success:
            st.success(msg)
            del st.session_state.edit_category
            st.experimental_rerun()
        else:
            st.error(f"Error: {msg}")

def render_categories_page():
    st.title("Categories Management")

    # Validate session
    token = st.session_state.get("token")
    if not token or not is_authenticated(token):
        st.warning("Session expired or unauthorized. Please login again.")
        st.session_state.logged_in = False
        st.session_state.token = None
        st.session_state.page = "login"
        st.stop()

    # Fetch all categories
    categories = fetch_all_categories(token)

    # Display categories table
    st.write("### All Categories")
    if categories:
        st.table([{k: c.get(k) for k in ["id", "name", "title"]} for c in categories])
    else:
        st.info("No categories found.")

    # Search bar
    st.subheader("Search Category")
    category_id = st.text_input("Enter Category ID", placeholder="e.g., 6258d724-498c-4811-b5a9-bfabc69fa3b9")
    searched_category = None

    if st.button("Search"):
        if category_id:
            searched_category = fetch_category_by_id(token, category_id)
            if not searched_category:
                st.error("Category not found.")
        else:
            st.warning("Please enter a valid Category ID.")

    # Display category details
    if searched_category:
        st.subheader("Category Details")
        st.write({
            "ID": searched_category.get("id"),
            "Name": searched_category.get("name"),
            "Title": searched_category.get("title"),
            "Description": searched_category.get("description"),
            "Published": searched_category.get("published"),
            "Rank": searched_category.get("rank")
        })

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit Category", key=f"edit_{searched_category['id']}"):
                st.session_state.edit_category = searched_category
                st.experimental_rerun()
        with col2:
            confirm = st.checkbox("Are you sure you want to delete this category?")
            if st.button("Delete Category", key=f"delete_{searched_category['id']}") and confirm:
                success, msg = delete_category(token, searched_category["id"])
                if success:
                    st.success(msg)
                    st.experimental_rerun()
                else:
                    st.error(msg)

    # Render update form if editing
    if getattr(st.session_state, "edit_category", None):
        render_update_category_form(
            category_id=st.session_state.edit_category["id"],
            current_data=st.session_state.edit_category
        )

    # Only show create form if not editing
    if not getattr(st.session_state, "edit_category", None):
        st.subheader("Add New Category")
        with st.form("create_category_form"):
            name = st.text_input("Name")
            title = st.text_input("Title")
            description = st.text_area("Description")
            published = st.checkbox("Published", value=False)
            rank = st.number_input("Rank", min_value=0, step=1, value=0)

            if st.form_submit_button("Create Category"):
                if not name or not title:
                    st.error("Name and Title are required.")
                else:
                    success, msg = create_category(token, name, title, description, published, rank)
                    if success:
                        st.success(msg)
                        st.experimental_rerun()
                    else:
                        st.error(f"Error: {msg}")