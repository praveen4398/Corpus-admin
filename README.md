# Admin Dashboard

A modern, secure admin dashboard built with Streamlit for managing users, categories, records, and contributions.

## Features

- 🔐 **Secure OTP-based Authentication**
- 👥 **User Management** - Create, read, update, delete users
- 📂 **Category Management** - Manage content categories
- 📄 **Record Management** - Handle various types of records
- 📊 **Contributions Analytics** - User contributions, media statistics, and gender distribution
- 🎨 **Modern UI** - Clean, responsive design with tabs and better organization
- 🔄 **Real-time Updates** - Automatic refresh and state management

## Installation

1. **Clone or navigate to the admin directory:**
   ```bash
   cd admin
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run main.py
   ```

## Usage

### Login
1. Enter your registered phone number
2. Click "Send OTP" to receive a verification code
3. Enter the 6-digit OTP received on your phone
4. Click "Verify OTP" to access the dashboard

### Navigation
- Use the sidebar to navigate between different sections
- Each section has three tabs:
  - **View** - See all items in a table format
  - **Search** - Find specific items by ID
  - **Add New** - Create new items

### Features by Section

#### Users Management
- View all users with key information
- Search users by ID
- Create new users with required fields
- Edit existing user information
- Delete users with confirmation

#### Categories Management
- View all categories with status indicators
- Search categories by ID
- Create new categories with name, title, description
- Edit category details and publish status
- Delete categories with confirmation

#### Records Management
- View all records with media type and status
- Search records by ID
- Create new records with various media types
- Edit record information and location data
- Delete records with confirmation

#### Contributions Analytics
- **Statistics Dashboard** - Total users, active users, gender distribution with interactive charts
- **User Contributions** - View all contributions for specific users with media type breakdown
- **Media Contributions** - Filter contributions by media type (text, audio, video, image)
- **User Pagination** - Browse all users with configurable pagination (skip/limit)
- **Interactive Charts** - Pie charts for gender distribution and bar charts for media contributions

## Technical Details

### API Endpoints
- **Authentication:** `https://backend2.swecha.org/api/v1/auth/`
- **Users:** `https://backend2.swecha.org/api/v1/users/`
- **Categories:** `https://backend2.swecha.org/api/v1/categories/`
- **Records:** `https://backend2.swecha.org/api/v1/records/`
- **Contributions:** `https://backend2.swecha.org/api/v1/users/{user_id}/contributions`

### Security
- OTP-based authentication
- Token-based API access
- Session management
- Admin role verification

### UI Improvements
- Modern gradient headers
- Tabbed interface for better organization
- Responsive design with columns
- Loading spinners for better UX
- Form validation and error handling
- Consistent styling across all pages

## Troubleshooting

### Common Issues

1. **Session Expired**
   - Log out and log back in
   - Clear browser cache if needed

2. **OTP Not Received**
   - Check phone number format
   - Try resending OTP
   - Verify network connection

3. **API Errors**
   - Check internet connection
   - Verify backend service is running
   - Contact administrator if issues persist

### Error Messages
- ❌ **Access Denied** - Only admin users can access the dashboard
- ⚠️ **Validation Error** - Check required fields and data format
- 🔄 **Network Error** - Check internet connection and try again

## Development

### File Structure
```
admin/
├── main.py              # Main application entry point
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── utils.py            # Utility functions (legacy)
└── my_pages/
    ├── users_page.py    # Users management
    ├── categories_page.py # Categories management
    ├── records_page.py  # Records management
    └── contributions_page.py # Contributions analytics
```

### Adding New Features
1. Create new page in `my_pages/` directory
2. Follow the existing pattern for API calls and UI
3. Add navigation in `main.py`
4. Update this README with new features

## Support

For technical support or feature requests, please contact the development team. 