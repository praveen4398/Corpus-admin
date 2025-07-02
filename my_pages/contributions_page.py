from datetime import datetime, timedelta
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
    if 'activity_analysis_cache' in st.session_state:
        del st.session_state.activity_analysis_cache
    if 'activity_analysis_timestamp' in st.session_state:
        del st.session_state.activity_analysis_timestamp


def fetch_user_contributions_summary(token, user_id):
    """Fetch contribution summary for a specific user (optimized for bulk analysis)."""
    try:
        headers = COMMON_HEADERS(token)
        url = CONTRIBUTIONS_API_URL.format(user_id=user_id)
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                total_contributions = data.get('total_contributions', 0)
                return user_id, total_contributions
            else:
                return user_id, 0
        else:
            return user_id, 0
    except Exception as e:
        return user_id, 0


def analyze_user_activity_bulk(token, users, max_workers=20):
    """Analyze user activity in bulk using threading for better performance."""
    
    # Check if we have cached activity analysis
    if ('activity_analysis_cache' in st.session_state and 
        'activity_analysis_timestamp' in st.session_state and
        not is_cache_stale(max_age_minutes=15)):  # Cache for 15 minutes
        return st.session_state.activity_analysis_cache
    
    user_activity = {}
    total_users = len(users)
    
    # Create progress tracking
    progress_container = st.container()
    with progress_container:
        st.info("🔍 Analyzing user activity... This may take a few minutes for large datasets.")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    completed_count = 0
    lock = threading.Lock()
    
    def update_progress():
        nonlocal completed_count
        with lock:
            completed_count += 1
            progress = completed_count / total_users
            progress_bar.progress(progress)
            status_text.text(f"Processed {completed_count}/{total_users} users ({progress:.1%})")
    
    # Use ThreadPoolExecutor to fetch contributions in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_user = {
            executor.submit(fetch_user_contributions_summary, token, user['id']): user
            for user in users if user.get('id')
        }
        
        # Process completed futures
        for future in as_completed(future_to_user):
            user = future_to_user[future]
            try:
                user_id, total_contributions = future.result()
                user_activity[user_id] = {
                    'user': user,
                    'total_contributions': total_contributions,
                    'has_contributions': total_contributions > 0
                }
            except Exception as e:
                # Handle individual user failures gracefully
                user_activity[user['id']] = {
                    'user': user,
                    'total_contributions': 0,
                    'has_contributions': False
                }
            finally:
                update_progress()
    
    # Clear progress indicators
    progress_container.empty()
    
    # Cache the results
    st.session_state.activity_analysis_cache = user_activity
    st.session_state.activity_analysis_timestamp = datetime.now()
    
    return user_activity


def get_user_activity_statistics(token):
    """Get comprehensive user activity statistics."""
    try:
        all_users = fetch_all_users_batched(token)
        if not all_users:
            return None
        
        total_users = len(all_users)
        
        # Analyze user activity in bulk
        user_activity = analyze_user_activity_bulk(token, all_users)
        
        # Calculate statistics
        users_with_contributions = sum(1 for activity in user_activity.values() 
                                     if activity['has_contributions'])
        users_with_zero_records = total_users - users_with_contributions
        activity_rate = (users_with_contributions / total_users * 100) if total_users > 0 else 0
        
        # Gender distribution
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
            
            gender = str(gender).lower().strip()
            
            if gender in ['male', 'm']:
                gender_counts['male'] += 1
            elif gender in ['female', 'f']:
                gender_counts['female'] += 1
            elif gender in ['other', 'o']:
                gender_counts['other'] += 1
            else:
                gender_counts['unknown'] += 1
        
        # Active users (based on is_active flag)
        active_users_flag = sum(1 for user in all_users if user.get('is_active', False))
        
        # Detailed contribution statistics
        total_contributions_sum = sum(activity['total_contributions'] 
                                    for activity in user_activity.values())
        
        # Top contributors
        top_contributors = sorted(
            [(activity['user'], activity['total_contributions']) 
             for activity in user_activity.values()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_users': total_users,
            'users_with_contributions': users_with_contributions,
            'users_with_zero_records': users_with_zero_records,
            'activity_rate': activity_rate,
            'gender_counts': gender_counts,
            'active_users_flag': active_users_flag,
            'total_contributions_sum': total_contributions_sum,
            'top_contributors': top_contributors,
            'user_activity': user_activity
        }
        
    except Exception as e:
        st.error(f"Error calculating activity statistics: {e}")
        return None


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
    tab1, tab2, tab3, tab4 = st.tabs(["📈 User Activity Analysis", "👤 User Contributions", "📱 Media Contributions", "👥 All Users"])

    with tab1:
        # User Activity Analysis Header
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 2rem;">
            <div style="background: linear-gradient(45deg, #4CAF50, #45a049); padding: 0.5rem; border-radius: 50%; margin-right: 1rem;">
                <span style="color: white; font-size: 1.5rem;">👥</span>
            </div>
            <h2 style="color: #333; margin: 0;">User Activity Analysis</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Cache management
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 Analysis results are cached for better performance. Use 'Refresh Analysis' to get latest data.")
        with col2:
            if st.button("🔄 Refresh Analysis", type="primary"):
                clear_users_cache()
                st.rerun()
        
        # Get comprehensive statistics
        with st.spinner("Analyzing user activity..."):
            stats = get_user_activity_statistics(token)
        
        if stats:
            # Success message with user count
            st.success(f"✅ Successfully loaded {stats['total_users']} users!")
            
            # Main metrics in a styled layout
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="background: white; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #4CAF50; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="color: #666; margin: 0; font-size: 0.9rem;">Active Users</h4>
                    <h2 style="color: #333; margin: 0.5rem 0 0 0; font-size: 2rem;">{stats['users_with_contributions']}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: white; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #ff9800; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="color: #666; margin: 0; font-size: 0.9rem;">Users with Zero Records</h4>
                    <h2 style="color: #333; margin: 0.5rem 0 0 0; font-size: 2rem;">{stats['users_with_zero_records']}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style="background: white; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #2196F3; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="color: #666; margin: 0; font-size: 0.9rem;">Activity Rate</h4>
                    <h2 style="color: #333; margin: 0.5rem 0 0 0; font-size: 2rem;">{stats['activity_rate']:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
            
            # Total registered users (larger display)
            st.markdown("---")
            st.markdown(f"""
            <div style="text-align: center; margin: 2rem 0;">
                <h4 style="color: #666; margin: 0;">Total Registered Users</h4>
                <h1 style="color: #333; margin: 0.5rem 0; font-size: 3rem; font-weight: bold;">{stats['total_users']}</h1>
            </div>
            """, unsafe_allow_html=True)
            
            # Additional statistics
            st.markdown("### 📊 Additional Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Contributions", f"{stats['total_contributions_sum']:,}")
            
            with col2:
                avg_contributions = stats['total_contributions_sum'] / stats['users_with_contributions'] if stats['users_with_contributions'] > 0 else 0
                st.metric("Avg Contributions per Active User", f"{avg_contributions:.1f}")
            
            with col3:
                st.metric("Users with Active Flag", stats['active_users_flag'])
            
            with col4:
                inactive_flag_users = stats['total_users'] - stats['active_users_flag']
                st.metric("Users with Inactive Flag", inactive_flag_users)
            
            # Activity distribution chart
            st.markdown("### 📈 Activity Distribution")
            
            # Create a pie chart for activity distribution
            activity_data = {
                'Users with Contributions': stats['users_with_contributions'],
                'Users with Zero Records': stats['users_with_zero_records']
            }
            
            fig = px.pie(
                values=list(activity_data.values()),
                names=list(activity_data.keys()),
                title="User Activity Distribution",
                color_discrete_map={
                    'Users with Contributions': '#4CAF50',
                    'Users with Zero Records': '#ff9800'
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label+value')
            st.plotly_chart(fig, use_container_width=True)

            # Gender distribution chart
            if stats['gender_counts']:
                st.markdown("### 👥 Gender Distribution")
                
                valid_gender_counts = {k: v for k, v in stats['gender_counts'].items() if v > 0}
                
                if valid_gender_counts:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Pie chart
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
                    
                    with col2:
                        # Gender statistics table
                        gender_data = []
                        for gender, count in valid_gender_counts.items():
                            percentage = (count / stats['total_users']) * 100
                            gender_data.append({
                                "Gender": gender.title(),
                                "Count": count,
                                "Percentage": f"{percentage:.1f}%"
                            })
                        
                        st.markdown("#### Gender Statistics")
                        st.dataframe(pd.DataFrame(gender_data), use_container_width=True)
            
            # Top contributors
            if stats['top_contributors']:
                st.markdown("### 🏆 Top Contributors")
                
                top_contrib_data = []
                for rank, (user, contrib_count) in enumerate(stats['top_contributors'], 1):
                    if contrib_count > 0:  # Only show users with contributions
                        top_contrib_data.append({
                            "Rank": rank,
                            "Name": user.get('name', 'Unknown'),
                            "Email": user.get('email', ''),
                            "Contributions": contrib_count,
                            "Gender": user.get('gender', 'Unknown').title() if user.get('gender') else 'Unknown'
                        })
                
                if top_contrib_data:
                    st.dataframe(pd.DataFrame(top_contrib_data), use_container_width=True)
                else:
                    st.info("No users with contributions found.")
        
        else:
            st.error("Failed to load user activity statistics.")

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

                    # Display detailed contributions
                    contrib_list = contributions.get('contributions', [])
                    if contrib_list:
                        st.markdown(f"#### Detailed {media_type.title()} Contributions")
                        
                        # Create detailed data table
                        detailed_data = []
                        for contrib in contrib_list:
                            detailed_data.append({
                                "ID": contrib.get('id', '')[:8] + "..." if contrib.get('id') else 'N/A',
                                "Title": contrib.get('title', 'No title'),
                                "Description": contrib.get('description', 'No description')[:50] + "..." if contrib.get('description') and len(contrib.get('description', '')) > 50 else contrib.get('description', 'No description'),
                                "Size": contrib.get('size', 0),
                                "Reviewed": "✅" if contrib.get('reviewed') else "❌",
                                "Created": contrib.get('created_at', 'Unknown')[:10] if contrib.get('created_at') else 'Unknown',
                                "Updated": contrib.get('updated_at', 'Unknown')[:10] if contrib.get('updated_at') else 'Unknown'
                            })
                        
                        df = pd.DataFrame(detailed_data)
                        st.dataframe(df, use_container_width=True)

                        # Show additional statistics
                        if len(contrib_list) > 0:
                            st.markdown("#### Statistics")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                total_size = sum(contrib.get('size', 0) for contrib in contrib_list)
                                st.metric("Total Size", f"{total_size:,} bytes")
                            
                            with col2:
                                avg_size = total_size / len(contrib_list) if len(contrib_list) > 0 else 0
                                st.metric("Average Size", f"{avg_size:,.0f} bytes")
                            
                            with col3:
                                reviewed_percentage = (reviewed_count / len(contrib_list)) * 100 if len(contrib_list) > 0 else 0
                                st.metric("Review Rate", f"{reviewed_percentage:.1f}%")
                            
                            with col4:
                                pending_review = len(contrib_list) - reviewed_count
                                st.metric("Pending Review", pending_review)

                    else:
                        st.info(f"No {media_type} contributions found for this user.")
                else:
                    st.error("Failed to fetch contributions.")
            else:
                st.error("User not found.")

    with tab4:
        st.markdown("### 👥 All Users")
        
        # Cache management for all users
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 User data is cached for better performance. Use 'Refresh Users' to get latest data.")
        with col2:
            if st.button("🔄 Refresh Users", type="primary"):
                clear_users_cache()
                st.rerun()
        
        # Get all users
        all_users = fetch_all_users_batched(token)
        
        if all_users:
            st.success(f"✅ Loaded {len(all_users)} users")
            
            # Search and filter options
            col1, col2 = st.columns([2, 1])
            
            with col1:
                search_term = st.text_input("🔍 Search users by name or email", key="user_search")
            
            with col2:
                gender_filter = st.selectbox(
                    "Filter by Gender",
                    ["All", "Male", "Female", "Other", "Unknown"],
                    key="gender_filter"
                )
            
            # Filter users based on search and gender
            filtered_users = all_users
            
            if search_term:
                filtered_users = [
                    user for user in filtered_users
                    if search_term.lower() in user.get('name', '').lower() or 
                       search_term.lower() in user.get('email', '').lower()
                ]
            
            if gender_filter != "All":
                filtered_users = [
                    user for user in filtered_users
                    if user.get('gender', '').lower() == gender_filter.lower() or
                       (gender_filter == "Unknown" and not user.get('gender'))
                ]
            
            st.info(f"Showing {len(filtered_users)} of {len(all_users)} users")
            
            # Display users in a table
            if filtered_users:
                user_data = []
                for user in filtered_users:
                    user_data.append({
                        "ID": user.get('id', '')[:8] + "..." if user.get('id') else 'N/A',
                        "Name": user.get('name', 'Unknown'),
                        "Email": user.get('email', 'No email'),
                        "Gender": user.get('gender', 'Unknown').title() if user.get('gender') else 'Unknown',
                        "Active": "✅" if user.get('is_active') else "❌",
                        "Verified": "✅" if user.get('is_verified') else "❌",
                        "Created": user.get('created_at', 'Unknown')[:10] if user.get('created_at') else 'Unknown'
                    })
                
                # Create DataFrame and display
                df = pd.DataFrame(user_data)
                
                # Add pagination for large datasets
                if len(user_data) > 100:
                    st.warning("⚠️ Large dataset detected. Showing first 100 users for performance.")
                    df = df.head(100)
                
                st.dataframe(df, use_container_width=True)
                
                # Export options
                st.markdown("### 📥 Export Options")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📋 Copy to Clipboard", type="secondary"):
                        st.code(df.to_csv(index=False), language="csv")
                        st.success("Data formatted for copying!")
                
                with col2:
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="📁 Download CSV",
                        data=csv_data,
                        file_name=f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
            else:
                st.info("No users match your search criteria.")
        
        else:
            st.error("Failed to load users.")


# Additional utility functions that might be useful
def export_activity_data(stats):
    """Export activity analysis data to CSV format."""
    if not stats:
        return None
    
    export_data = []
    for user_id, activity in stats['user_activity'].items():
        user = activity['user']
        export_data.append({
            'user_id': user_id,
            'name': user.get('name', 'Unknown'),
            'email': user.get('email', ''),
            'gender': user.get('gender', 'Unknown'),
            'is_active': user.get('is_active', False),
            'is_verified': user.get('is_verified', False),
            'total_contributions': activity['total_contributions'],
            'has_contributions': activity['has_contributions'],
            'created_at': user.get('created_at', '')
        })
    
    return pd.DataFrame(export_data)


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(
        page_title="User Contributions Analytics",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .main > div {
            padding-top: 2rem;
        }
        .stMetric {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #e0e0e0;
        }
        .stSelectbox > div > div {
            background-color: white;
        }
        div[data-testid="metric-container"] {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 1rem;
            border-radius: 0.375rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if user is authenticated
    if 'token' not in st.session_state:
        st.error("❌ Please authenticate first to access this page.")
        st.info("💡 Go to the login page to get your authentication token.")
        return
    
    # Render the main contributions page
    render_contributions_page()


if __name__ == "__main__":
    main()
