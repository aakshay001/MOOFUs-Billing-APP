# gdrive_storage.py - OAuth version with timeout handling
import streamlit as st
import pandas as pd
import io
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_credentials():
    """Get user credentials from session state"""
    if 'credentials' not in st.session_state:
        return None
    
    creds_data = st.session_state['credentials']
    creds = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data.get('token_uri'),
        client_id=creds_data.get('client_id'),
        client_secret=creds_data.get('client_secret'),
        scopes=creds_data.get('scopes')
    )
    return creds

def google_drive_login():
    """Handle Google Drive authentication"""
    st.sidebar.header("🔐 Google Drive")
    
    if 'credentials' in st.session_state:
        st.sidebar.success("✅ Connected")
        if st.sidebar.button("🚪 Logout"):
            del st.session_state['credentials']
            if 'folder_id' in st.session_state:
                del st.session_state['folder_id']
            st.rerun()
        return True
    
    st.sidebar.warning("⚠️ Login required")
    
    try:
        redirect_uri = st.secrets["google_oauth"].get("redirect_uri", "http://localhost:8501")
        
        client_config = {
            "web": {
                "client_id": st.secrets["google_oauth"]["client_id"],
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Handle callback first
        query_params = st.query_params
        if 'code' in query_params:
            code = query_params['code']
            
            with st.spinner("Authenticating..."):
                try:
                    flow.fetch_token(code=code)
                    
                    creds = flow.credentials
                    st.session_state['credentials'] = {
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'client_id': creds.client_id,
                        'client_secret': creds.client_secret,
                        'scopes': creds.scopes
                    }
                    
                    st.query_params.clear()
                    st.success("✅ Login successful!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
                    st.query_params.clear()
                    return False
        
        # Show login button
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        st.sidebar.markdown(f"### [🔗 Login with Google]({auth_url})")
        
    except Exception as e:
        st.sidebar.error(f"Auth error: {e}")
        return False
    
    return False

@st.cache_resource(ttl=300)  # Cache for 5 minutes
def get_drive_service(_creds):
    """Get Google Drive service with timeout"""
    import socket
    socket.setdefaulttimeout(30)  # 30 second timeout
    return build('drive', 'v3', credentials=_creds, cache_discovery=False)

def retry_api_call(func, max_retries=3, delay=2):
    """Retry API calls on timeout"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            raise e

def get_or_create_app_folder():
    """Get or create GST BillBook folder"""
    if 'folder_id' in st.session_state:
        return st.session_state['folder_id']
    
    creds = get_credentials()
    if not creds:
        return None
    
    try:
        service = get_drive_service(creds)
        
        def search_folder():
            query = "name='GST_BillBook_Data' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            return service.files().list(
                q=query, 
                fields="files(id, name)",
                pageSize=10
            ).execute()
        
        # Retry search with timeout handling
        results = retry_api_call(search_folder)
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
        else:
            # Create new folder
            def create_folder():
                file_metadata = {
                    'name': 'MOOFUs_Billbook_Data',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                return service.files().create(
                    body=file_metadata, 
                    fields='id'
                ).execute()
            
            folder = retry_api_call(create_folder)
            folder_id = folder['id']
        
        st.session_state['folder_id'] = folder_id
        return folder_id
        
    except Exception as e:
        st.error(f"Folder error: {e}")
        return None

def list_files_in_folder():
    """List all files in app folder"""
    creds = get_credentials()
    if not creds:
        return []
    
    folder_id = get_or_create_app_folder()
    if not folder_id:
        return []
    
    try:
        service = get_drive_service(creds)
        
        def list_files():
            return service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name)",
                pageSize=100
            ).execute()
        
        results = retry_api_call(list_files)
        return results.get('files', [])
        
    except Exception as e:
        # Return empty list on error instead of showing error
        return []

def upload_csv_to_drive(df, filename):
    """Upload DataFrame as CSV to Google Drive"""
    creds = get_credentials()
    if not creds:
        return None
    
    folder_id = get_or_create_app_folder()
    if not folder_id:
        return None
    
    try:
        service = get_drive_service(creds)
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        existing_files = list_files_in_folder()
        existing_file = next((f for f in existing_files if f['name'] == filename), None)
        
        file_metadata = {'name': filename}
        if not existing_file:
            file_metadata['parents'] = [folder_id]
        
        media = MediaIoBaseUpload(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
            mimetype='text/csv',
            resumable=True,
            chunksize=256*1024  # 256KB chunks
        )
        
        def upload():
            if existing_file:
                return service.files().update(
                    fileId=existing_file['id'],
                    media_body=media
                ).execute()
            else:
                return service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
        
        file = retry_api_call(upload)
        return file.get('id')
        
    except Exception as e:
        st.warning(f"Upload delayed for {filename}")
        return None

def download_csv_from_drive(filename):
    """Download CSV from Google Drive"""
    creds = get_credentials()
    if not creds:
        return pd.DataFrame()
    
    try:
        service = get_drive_service(creds)
        files = list_files_in_folder()
        file = next((f for f in files if f['name'] == filename), None)
        
        if not file:
            return pd.DataFrame()
        
        def download():
            request = service.files().get_media(fileId=file['id'])
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            return pd.read_csv(file_content)
        
        return retry_api_call(download)
        
    except:
        return pd.DataFrame()
