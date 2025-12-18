# gdrive_storage.py - OAuth version
import streamlit as st
import pandas as pd
import io
import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

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
    st.sidebar.header("🔐 Google Drive Login")
    
    if 'credentials' in st.session_state:
        st.sidebar.success("✅ Connected to Google Drive")
        if st.sidebar.button("🚪 Logout"):
            del st.session_state['credentials']
            if 'folder_id' in st.session_state:
                del st.session_state['folder_id']
            st.rerun()
        return True
    
    st.sidebar.warning("⚠️ Please login to Google Drive to use the app")
    
    # OAuth flow
    if 'oauth_flow' not in st.session_state:
        try:
            client_config = {
                "web": {
                    "client_id": st.secrets["google_oauth"]["client_id"],
                    "client_secret": st.secrets["google_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]]
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.session_state['oauth_flow'] = flow
            
            st.sidebar.markdown(f"[🔗 Click here to login with Google]({auth_url})")
            
            # Handle callback
            query_params = st.query_params
            if 'code' in query_params:
                code = query_params['code']
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
                
                # Clear query params
                st.query_params.clear()
                st.rerun()
                
        except Exception as e:
            st.sidebar.error(f"Authentication error: {e}")
            return False
    
    return False

@st.cache_resource
def get_drive_service(_creds):
    """Get Google Drive service"""
    return build('drive', 'v3', credentials=_creds)

def get_or_create_app_folder():
    """Get or create GST BillBook folder in user's Drive"""
    if 'folder_id' in st.session_state:
        return st.session_state['folder_id']
    
    creds = get_credentials()
    if not creds:
        return None
    
    service = get_drive_service(creds)
    
    # Search for existing folder
    query = "name='GST_BillBook_Data' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    
    if folders:
        folder_id = folders[0]['id']
    else:
        # Create new folder
        file_metadata = {
            'name': 'GST_BillBook_Data',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder['id']
    
    st.session_state['folder_id'] = folder_id
    return folder_id

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
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, modifiedTime)"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Error listing files: {e}")
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
        
        # Convert DataFrame to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Check if file exists
        existing_files = list_files_in_folder()
        existing_file = next((f for f in existing_files if f['name'] == filename), None)
        
        file_metadata = {'name': filename}
        if not existing_file:
            file_metadata['parents'] = [folder_id]
        
        media = MediaIoBaseUpload(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
            mimetype='text/csv',
            resumable=True
        )
        
        if existing_file:
            file = service.files().update(
                fileId=existing_file['id'],
                media_body=media
            ).execute()
        else:
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
        
        return file.get('id')
    
    except Exception as e:
        st.error(f"Error uploading {filename}: {e}")
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
        
        request = service.files().get_media(fileId=file['id'])
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_content.seek(0)
        df = pd.read_csv(file_content)
        return df
    
    except Exception as e:
        return pd.DataFrame()
