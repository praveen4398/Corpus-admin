import streamlit as st
from datetime import datetime
import uuid
from utils import fetch_data, create_data, update_data, delete_data, is_token_valid

RECORDS_API_URL = "https://backend2.swecha.org/api/v1/records"

def render_records_page():
    st.title("Records Page")

    token = st.session_state.get("token")
    if not token or not is_token_valid(token):
        st.warning("Session expired. Please login again.")
        st.session_state.logged_in = False
        st.session_state.token = None
        st.session_state.page = "login"
        st.rerun()
        return

    records = fetch_data(token, RECORDS_API_URL)

    # View records
    st.subheader("All Records")
    if records:
        st.table([
            {
                "ID": rec["uid"],
                "Title": rec["title"],
                "Status": rec["status"],
                "Reviewed": rec["reviewed"]
            }
            for rec in records
        ])
    else:
        st.info("No records available.")

    # Create a new record
    st.subheader("Add New Record")
    with st.form("create_record_form"):
        title = st.text_input("Title*")
        description = st.text_area("Description")
        media_type = st.selectbox("Media Type", ["text", "image", "video", "audio"])
        file_url = st.text_input("File URL (optional)")
        file_name = st.text_input("File Name (optional)")
        file_size = st.number_input("File Size in Bytes", min_value=0, step=1)
        latitude = st.number_input("Latitude", value=17.385)
        longitude = st.number_input("Longitude", value=78.4867)
        category_id = st.text_input("Category ID")
        status = st.selectbox("Status", ["pending", "approved", "rejected"])

        submitted = st.form_submit_button("Create Record")
        if submitted:
            if not title.strip():
                st.error("Title is required.")
            else:
                payload = {
                    "uid": str(uuid.uuid4()),
                    "title": title.strip(),
                    "description": description.strip(),
                    "media_type": media_type,
                    "file_url": file_url,
                    "file_name": file_name,
                    "file_size": file_size,
                    "status": status,
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "reviewed": False,
                    "reviewed_by": str(uuid.uuid4()),  # Replace if reviewer is known
                    "reviewed_at": datetime.utcnow().isoformat() + "Z",
                    "user_id": st.session_state.get("user_id", str(uuid.uuid4())),
                    "category_id": category_id,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                }

                with st.expander("Payload Preview"):
                    st.json(payload)

                success, message = create_data(token, RECORDS_API_URL, payload)
                if success:
                    st.success("Record created successfully.")
                    st.rerun()
                else:
                    st.error(f"Failed to create record: {message}")

    # Update a record
    st.subheader("Update Record")
    if records:
        selected = st.selectbox("Choose Record", records, format_func=lambda r: r["title"])
        if selected:
            with st.form("update_record_form"):
                updated_title = st.text_input("New Title", value=selected["title"])
                updated_description = st.text_area("New Description", value=selected.get("description", ""))
                updated_status = st.selectbox("Status", ["pending", "approved", "rejected"], index=["pending", "approved", "rejected"].index(selected.get("status", "pending")))

                update_submitted = st.form_submit_button("Update Record")
                if update_submitted:
                    payload = {
                        "title": updated_title.strip(),
                        "description": updated_description.strip(),
                        "status": updated_status,
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    }
                    update_url = f"{RECORDS_API_URL}/{selected['uid']}"
                    success, message = update_data(token, update_url, payload)
                    if success:
                        st.success("Record updated.")
                        st.rerun()
                    else:
                        st.error(f"Update failed: {message}")

    # Delete a record
    st.subheader("Delete Record")
    if records:
        selected_delete = st.selectbox("Select Record to Delete", records, format_func=lambda r: r["title"])
        if selected_delete:
            confirm = st.checkbox("Confirm delete?")
            if st.button("Delete", type="primary", disabled=not confirm):
                delete_url = f"{RECORDS_API_URL}/{selected_delete['uid']}"
                success, message = delete_data(token, delete_url)
                if success:
                    st.success("Record deleted.")
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {message}")
