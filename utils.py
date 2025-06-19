#utitls.py
import requests
import streamlit as st

def fetch_data(token: str, url: str):
    try:
        response = requests.get(url, headers={
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        })
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch data: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Network error while fetching data: {e}")
        return []

def create_data(token: str, url: str, payload: dict):
    try:
        response = requests.post(url, json=payload, headers={
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Check for both 200 and 201 status codes for successful creation
        if response.status_code in [200, 201]:
            return True, "Created successfully"
        else:
            error_msg = response.json().get("detail", response.text) if response.text else "Unknown error"
            print(f"Create Error: {response.status_code} - {error_msg}")
            return False, f"Error {response.status_code}: {error_msg}"
    except Exception as e:
        error_msg = f"Network error: {e}"
        print(f"Create Exception: {error_msg}")
        return False, error_msg

def update_data(token: str, url: str, payload: dict):
    try:
        response = requests.put(url, json=payload, headers={
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
            "Content-Type": "application/json"
        })
        
        if response.status_code == 200:
            return True, "Updated successfully"
        else:
            error_msg = response.json().get("detail", response.text) if response.text else "Unknown error"
            print(f"Update Error: {response.status_code} - {error_msg}")
            return False, f"Error {response.status_code}: {error_msg}"
    except Exception as e:
        error_msg = f"Network error: {e}"
        print(f"Update Exception: {error_msg}")
        return False, error_msg

def delete_data(token: str, url: str):
    try:
        response = requests.delete(url, headers={
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        })
        
        if response.status_code in [200, 204]:
            return True, "Deleted successfully"
        else:
            error_msg = response.json().get("detail", response.text) if response.text else "Unknown error"
            print(f"Delete Error: {response.status_code} - {error_msg}")
            return False, f"Error {response.status_code}: {error_msg}"
    except Exception as e:
        error_msg = f"Network error: {e}"
        print(f"Delete Exception: {error_msg}")
        return False, error_msg

def is_token_valid(token):
    """Check if the token is valid by making a request to the auth/me endpoint"""
    try:
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        response = requests.get("https://backend2.swecha.org/api/v1/auth/me", headers=headers)
        return response.status_code == 200
    except:
        return False
