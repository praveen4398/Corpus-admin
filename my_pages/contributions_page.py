from datetime import datetime, timedelta
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# API URLs
USERS_API_URL = "https://backend2.swecha.org/api/v1/users/"
CONTRIBUTIONS_API_URL = "https://backend2.swecha.org/api/v1/users/{user_id}/contributions"
CONTRIBUTIONS_BY_MEDIA_API_URL = "https://backend2.swecha.org/api/v1/users/{user_id}/contributions/{media_type}"


def COMMON_HEADERS(token):
    return {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def is_cache_stale(max_age_minutes=30):
    """Check if the cached data is stale and needs refresh."""
    if 'all_users_cache_timestamp' not in st.session_state:
        return True
    
    cache_timestamp = st.session_state.all_users_cache_timestamp
    if not isinstance(cache_timestamp, datetime):
        return True
    
    age = datetime.now() - cache_timestamp
    return age.total_seconds() > (max_age_minutes * 60)


def fetch_all_users_batched(token, batch_size=1000):
    """Fetch all users in batches and store them in session state."""
    try:
        # Check if we already have all users stored in session state and cache is not stale
        if ('all_users_cache' in st.session_state and 
            st.session_state.all_users_cache and 
            not is_cache_stale()):
            return st.session_state.all_users_cache
        
        headers = COMMON_HEADERS(token)
        all_users = []
        skip = 0
        
        with st.spinner("Loading all users..."):
            progress_bar = st.progress(0)
            batch_count = 0
            
            while True:
                params = {"skip": skip, "limit": batch_size}
                r = requests.get(USERS_API_URL, params=params, headers=headers)
                
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        if not data:  # Empty response, we've reached the end
                            break
                        all_users.extend(data)
                        skip += batch_size
                        batch_count += 1
                        
                        # Update progress (estimate based on typical response size)
                        progress = min(0.9, batch_count * 0.1)  # Assume ~10 batches max
                        progress_bar.progress(progress)
                        
                        # If we got less than batch_size, we've reached the end
                        if len(data) < batch_size:
                            break
                    else:
                        st.error("Unexpected response format from the server.")
                        break
                else:
                    st.error(f"Failed to fetch users batch. Status Code: {r.status_code}")
                    break
            
            progress_bar.progress(1.0)
            st.success(f"✅ Loaded {len(all_users)} users in {batch_count} batches")
        
        # Store in session state for future use
        st.session_state.all_users_cache = all_users
        st.session_state.all_users_cache_timestamp = datetime.now()
        
        return all_users
    except Exception as e:
        st.error(f"Network error while fetching users: {e}")
        return []


def clear_users_cache():
    """Clear the cached users data."""
    if 'all_users_cache' in st.session_state:
        del st.session_state.all_users_cache
    if 'all_users_cache_timestamp' in st.session_state:
        del st.session_state.all_users_cache_timestamp


def fetch_user_contributions(token, user_id):
    """Fetch all contributions for a specific user."""
    try:
        headers = COMMON_HEADERS(token)
        url = CONTRIBUTIONS_API_URL.format(user_id=user_id)
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            # Ensure we have a valid response structure
            if isinstance(data, dict):
                # Ensure all contribution lists exist
                for media_type in ['text_contributions', 'audio_contributions', 'video_contributions', 'image_contributions']:
                    if media_type not in data:
                        data[media_type] = []
                if 'contributions_by_media_type' not in data:
                    data['contributions_by_media_type'] = {}
                return data
            else:
                # If response is not a dict, create a valid structure
                return {
                    'user_id': user_id,
                    'total_contributions': 0,
                    'contributions_by_media_type': {},
                    'text_contributions': [],
                    'audio_contributions': [],
                    'video_contributions': [],
                    'image_contributions': []
                }
        else:
            st.error(f"Failed to fetch contributions. Status Code: {r.status_code}")
            return {
                'user_id': user_id,
                'total_contributions': 0,
                'contributions_by_media_type': {},
                'text_contributions': [],
                'audio_contributions': [],
                'video_contributions': [],
                'image_contributions': []
            }
    except Exception as e:
        st.error(f"Network error: {e}")
        return {
            'user_id': user_id,
            'total_contributions': 0,
            'contributions_by_media_type': {},
            'text_contributions': [],
            'audio_contributions': [],
            'video_contributions': [],
            'image_contributions': []
        }


def fetch_user_contributions_by_media(token, user_id, media_type):
    """Fetch contributions for a specific user by media type."""
    try:
        headers = COMMON_HEADERS(token)
        url = CONTRIBUTIONS_BY_MEDIA_API_URL.format(user_id=user_id, media_type=media_type)
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            # Ensure we have a valid response structure
            if isinstance(data, dict):
                # Ensure contributions list exists
                if 'contributions' not in data:
                    data['contributions'] = []
                return data
            else:
                # If response is not a dict, create a valid structure
                return {
                    'user_id': user_id,
                    'total_contributions': 0,
                    'contributions': []
                }
        else:
            st.error(f"Failed to fetch {media_type} contributions. Status Code: {r.status_code}")
            return {
                'user_id': user_id,
                'total_contributions': 0,
                'contributions': []
            }
    except Exception as e:
        st.error(f"Network error: {e}")
        return {
            'user_id': user_id,
            'total_contributions': 0,
            'contributions': []
        }


def get_user_statistics(token):
    """Get total users and gender distribution statistics."""
    try:
        all_users = fetch_all_users_batched(token)
        if not all_users:
            return None, None, None
        total_users = len(all_users)

        # Initialize gender counts with default keys to avoid missing keys
        gender_counts = {
            'male': 0,
            'female': 0,
            'other': 0,
            'unknown': 0
        }

        for user in all_users:
            gender = user.get('gender', 'unknown')
            if gender is None:
                gender = 'unknown'
            
            # Normalize gender to lowercase and strip whitespace
            gender = str(gender).lower().strip()

            # Map common variants to standard categories
            if gender in ['male', 'm']:
                gender_counts['male'] += 1
            elif gender in ['female', 'f']:
                gender_counts['female'] += 1
            elif gender in ['other', 'o']:
                gender_counts['other'] += 1
            elif gender in ['string', 'unknown', 'null', '', 'unkonown']:
                gender_counts['unknown'] += 1
            else:
                # Log unexpected values for debugging
                print(f"Unexpected gender value found: {gender}")
                gender_counts['unknown'] += 1

        # Active users count
        active_users = sum(1 for user in all_users if user.get('is_active', False))

        return total_users, gender_counts, active_users

    except Exception as e:
        st.error(f"Error calculating statistics: {e}")
        return None, None, None


def render_contributions_page():
    """Render the main user contributions page."""
    # Page header with styling
    st.markdown(
        """
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center;">📊 User Contributions & Analytics</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Get token from session state
    token = st.session_state.get("token")
    if not token:
        st.error("❌ No authentication token found. Please log in again.")
        return

    # Create tabs for better organization
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Statistics", "👤 User Contributions", "📱 Media Contributions", "👥 All Users"])

    with tab1:
        st.markdown("### 📊 Platform Statistics")
        
        # Cache management for statistics
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔄 Refresh Statistics", type="secondary"):
                clear_users_cache()
                st.rerun()
        with col2:
            if st.button("🗑️ Clear Cache", type="secondary"):
                clear_users_cache()
                st.rerun()

        # Get statistics
        total_users, gender_counts, active_users = get_user_statistics(token)
        
        if total_users is not None:
            # Create metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Users", total_users)
            
            with col2:
                st.metric("Active Users", active_users or 0)
            
            with col3:
                inactive_users = total_users - (active_users or 0)
                st.metric("Inactive Users", inactive_users)
            
            with col4:
                if total_users > 0:
                    active_percentage = ((active_users or 0) / total_users) * 100
                    st.metric("Active Rate", f"{active_percentage:.1f}%")
                else:
                    st.metric("Active Rate", "0%")

            # Gender distribution chart
            if gender_counts:
                st.markdown("### Gender Distribution")
                
                # Filter out None values and ensure we have valid data
                valid_gender_counts = {k: v for k, v in gender_counts.items() if k is not None and v > 0}
                
                if valid_gender_counts:
                    # Create pie chart
                    fig = px.pie(
                        values=list(valid_gender_counts.values()),
                        names=list(valid_gender_counts.keys()),
                        title="User Gender Distribution",
                        color_discrete_map={
                            'male': '#1f77b4',
                            'female': '#ff7f0e',
                            'other': '#2ca02c',
                            'unknown': '#d62728'
                        }
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)

                    # Display gender counts in a table
                    gender_data = []
                    for gender, count in valid_gender_counts.items():
                        percentage = (count / total_users) * 100
                        gender_data.append({
                            "Gender": gender.title() if gender else "Unknown",
                            "Count": count,
                            "Percentage": f"{percentage:.1f}%"
                        })
                    
                    st.markdown("### Gender Statistics")
                    st.dataframe(pd.DataFrame(gender_data), use_container_width=True)
                else:
                    st.info("No gender data available for visualization.")
        else:
            st.error("Failed to load statistics.")

    with tab2:
        st.markdown("### 👤 User Contributions")
        
        # User selection
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Get all users for dropdown
            all_users = fetch_all_users_batched(token)
            if all_users:
                user_options = {f"{user.get('name', 'Unknown')}": user.get('id') 
                               for user in all_users}
                selected_user_display = st.selectbox(
                    "Select User",
                    options=list(user_options.keys()),
                    key="user_contributions_select"
                )
                selected_user_id = user_options[selected_user_display]
            else:
                st.error("No users found.")
                return
        
        with col2:
            if st.button("🔍 Load Contributions", type="primary"):
                st.session_state.selected_user_id = selected_user_id
                st.rerun()

        # Display contributions if user is selected
        if hasattr(st.session_state, 'selected_user_id'):
            user_id = st.session_state.selected_user_id
            
            # Get user details
            selected_user = next((user for user in all_users if user.get('id') == user_id), None)
            
            if selected_user:
                st.markdown(f"### Contributions for: {selected_user.get('name', 'Unknown')}")
                
                # Fetch contributions
                contributions = fetch_user_contributions(token, user_id)
                
                if contributions:
                    # Display summary
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Contributions", contributions.get('total_contributions', 0))
                    
                    with col2:
                        text_count = contributions.get('contributions_by_media_type', {}).get('text', 0)
                        st.metric("Text", text_count)
                    
                    with col3:
                        audio_count = contributions.get('contributions_by_media_type', {}).get('audio', 0)
                        st.metric("Audio", audio_count)
                    
                    with col4:
                        video_count = contributions.get('contributions_by_media_type', {}).get('video', 0)
                        image_count = contributions.get('contributions_by_media_type', {}).get('image', 0)
                        st.metric("Video + Image", video_count + image_count)

                    # Media type distribution chart
                    media_data = contributions.get('contributions_by_media_type', {})
                    if any(media_data.values()):
                        fig = px.bar(
                            x=list(media_data.keys()),
                            y=list(media_data.values()),
                            title="Contributions by Media Type",
                            labels={'x': 'Media Type', 'y': 'Count'}
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    # Display detailed contributions
                    st.markdown("### Detailed Contributions")
                    
                    # Text contributions
                    text_contributions = contributions.get('text_contributions', [])
                    if text_contributions:
                        st.markdown("#### 📝 Text Contributions")
                        text_data = []
                        for contrib in text_contributions:
                            text_data.append({
                                "ID": contrib.get('id', '')[:8] + "...",
                                "Title": contrib.get('title', 'No title'),
                                "Size": contrib.get('size', 0),
                                "Reviewed": "✅" if contrib.get('reviewed') else "❌"
                            })
                        st.dataframe(pd.DataFrame(text_data), use_container_width=True)

                    # Audio contributions
                    audio_contributions = contributions.get('audio_contributions', [])
                    if audio_contributions:
                        st.markdown("#### 🎵 Audio Contributions")
                        audio_data = []
                        for contrib in audio_contributions:
                            audio_data.append({
                                "ID": contrib.get('id', '')[:8] + "...",
                                "Title": contrib.get('title', 'No title'),
                                "Size": contrib.get('size', 0),
                                "Reviewed": "✅" if contrib.get('reviewed') else "❌"
                            })
                        st.dataframe(pd.DataFrame(audio_data), use_container_width=True)

                    # Video contributions
                    video_contributions = contributions.get('video_contributions', [])
                    if video_contributions:
                        st.markdown("#### 🎬 Video Contributions")
                        video_data = []
                        for contrib in video_contributions:
                            video_data.append({
                                "ID": contrib.get('id', '')[:8] + "...",
                                "Title": contrib.get('title', 'No title'),
                                "Size": contrib.get('size', 0),
                                "Reviewed": "✅" if contrib.get('reviewed') else "❌"
                            })
                        st.dataframe(pd.DataFrame(video_data), use_container_width=True)

                    # Image contributions
                    image_contributions = contributions.get('image_contributions', [])
                    if image_contributions:
                        st.markdown("#### 🖼️ Image Contributions")
                        image_data = []
                        for contrib in image_contributions:
                            image_data.append({
                                "ID": contrib.get('id', '')[:8] + "...",
                                "Title": contrib.get('title', 'No title'),
                                "Size": contrib.get('size', 0),
                                "Reviewed": "✅" if contrib.get('reviewed') else "❌"
                            })
                        st.dataframe(pd.DataFrame(image_data), use_container_width=True)

                else:
                    st.info("No contributions found for this user.")
            else:
                st.error("User not found.")

    with tab3:
        st.markdown("### 📱 Media Contributions")
        
        # User and media type selection
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Get all users for dropdown
            all_users = fetch_all_users_batched(token)
            if all_users:
                user_options = {f"{user.get('name', 'Unknown')}": user.get('id') 
                               for user in all_users}
                selected_user_display = st.selectbox(
                    "Select User",
                    options=list(user_options.keys()),
                    key="media_contributions_user_select"
                )
                selected_user_id = user_options[selected_user_display]
            else:
                st.error("No users found.")
                return
        
        with col2:
            media_type = st.selectbox(
                "Media Type",
                ["text", "audio", "video", "image"],
                key="media_type_select"
            )
        
        with col3:
            if st.button("🔍 Load", type="primary"):
                st.session_state.media_user_id = selected_user_id
                st.session_state.media_type = media_type
                st.rerun()

        # Display media-specific contributions
        if hasattr(st.session_state, 'media_user_id') and hasattr(st.session_state, 'media_type'):
            user_id = st.session_state.media_user_id
            media_type = st.session_state.media_type
            
            # Get user details
            selected_user = next((user for user in all_users if user.get('id') == user_id), None)
            
            if selected_user:
                st.markdown(f"### {media_type.title()} Contributions for: {selected_user.get('name', 'Unknown')}")
                
                # Fetch media-specific contributions
                contributions = fetch_user_contributions_by_media(token, user_id, media_type)
                
                if contributions:
                    # Display summary
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Contributions", contributions.get('total_contributions', 0))
                    
                    with col2:
                        contrib_list = contributions.get('contributions', [])
                        if contrib_list:
                            reviewed_count = sum(1 for contrib in contrib_list if contrib.get('reviewed', False))
                            st.metric("Reviewed", f"{reviewed_count}/{len(contrib_list)}")
                        else:
                            st.metric("Reviewed", "0/0")

                    # Display contributions
                    contrib_list = contributions.get('contributions', [])
                    if contrib_list:
                        contrib_data = []
                        for contrib in contrib_list:
                            contrib_data.append({
                                "ID": contrib.get('id', '')[:8] + "..." if contrib.get('id') else 'N/A',
                                "Title": contrib.get('title', 'No title'),
                                "Size": contrib.get('size', 0),
                                "Reviewed": "✅" if contrib.get('reviewed') else "❌",
                                "Category ID": contrib.get('category_id', '')[:8] + "..." if contrib.get('category_id') else 'N/A'
                            })
                        
                        st.dataframe(pd.DataFrame(contrib_data), use_container_width=True)
                    else:
                        st.info(f"No {media_type} contributions found for this user.")
                else:
                    st.info(f"No {media_type} contributions found for this user.")
            else:
                st.error("User not found.")

    with tab4:
        st.markdown("### 👥 All Users with Pagination")
        
        # Cache management
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 Users are cached for better performance. Use 'Refresh Cache' to get latest data.")
        with col2:
            if st.button("🔄 Refresh Cache", type="secondary"):
                clear_users_cache()
                st.rerun()
        
        # Show cache info if available
        if 'all_users_cache' in st.session_state and st.session_state.all_users_cache:
            cache_timestamp = st.session_state.get('all_users_cache_timestamp', 'Unknown')
            if isinstance(cache_timestamp, datetime):
                cache_time_str = cache_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                cache_time_str = str(cache_timestamp)
            st.success(f"✅ Cached {len(st.session_state.all_users_cache)} users (last updated: {cache_time_str})")
        
        # Pagination controls
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            skip = st.number_input("Skip", min_value=0, value=0, step=100, key="users_skip_input")
        
        with col2:
            limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, key="users_limit_input")
        
        with col3:
            if st.button("🔄 Load Users", type="primary"):
                st.session_state.current_skip = skip
                st.session_state.current_limit = limit
                st.rerun()

        # Load users with pagination from cache
        if hasattr(st.session_state, 'current_skip') and hasattr(st.session_state, 'current_limit'):
            skip = st.session_state.current_skip
            limit = st.session_state.current_limit
            
            # Get cached users
            all_cached_users = fetch_all_users_batched(token)
            
            if all_cached_users:
                # Apply pagination to cached data
                start_idx = skip
                end_idx = skip + limit
                users = all_cached_users[start_idx:end_idx]
                
                st.success(f"✅ Showing {len(users)} users (from cache)")
                
                # Create a more readable table
                display_data = []
                for u in users:
                    display_data.append({
                        "ID": u.get("id", "")[:8] + "...",
                        "Name": u.get("name", ""),
                        "Email": u.get("email", ""),
                        "Phone": u.get("phone", ""),
                        "Gender": u.get("gender", ""),
                        "Active": "✅" if u.get("is_active") else "❌",
                        "Created": u.get("created_at", "")[:10] if u.get("created_at") else "",
                        "Last Login": u.get("last_login_at", "")[:10] if u.get("last_login_at") else ""
                    })
                
                st.dataframe(display_data, use_container_width=True)
                
                # Pagination info
                total_cached = len(all_cached_users)
                st.info(f"Showing users {skip + 1} to {skip + len(users)} of {total_cached} total users (limit: {limit})")
                
                # Navigation buttons
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if skip > 0:
                        prev_skip = max(0, skip - limit)
                        if st.button("⬅️ Previous", key="prev_page"):
                            st.session_state.current_skip = prev_skip
                            st.rerun()
                
                with col2:
                    current_page = (skip // limit) + 1
                    total_pages = (total_cached + limit - 1) // limit
                    st.write(f"Page {current_page} of {total_pages}")
                
                with col3:
                    if skip + limit < total_cached:  # If there are more users to show
                        next_skip = skip + limit
                        if st.button("➡️ Next", key="next_page"):
                            st.session_state.current_skip = next_skip
                            st.rerun()
            else:
                st.warning("No users found. Try refreshing the cache.")
        else:
            st.info("Click 'Load Users' to start browsing users with pagination.") 