# gdrive_storage.py
import streamlit as st
import pandas as pd
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
import os

@st.cache_resource
def get_drive_service():
    """Initialize Google Drive service"""
    try:
        credentials_dict = dict(st.secrets["google_drive"])
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Error connecting to Google Drive: {e}")
        return None

def get_folder_id():
    """Get the folder ID from secrets"""
    return st.secrets["google_drive"]["folder_id"]

def list_files_in_folder(folder_id=None):
    """List all files in Google Drive folder"""
    service = get_drive_service()
    if not service:
        return []
    
    if not folder_id:
        folder_id = get_folder_id()
    
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, modifiedTime)"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return []

def upload_csv_to_drive(df, filename):
    """Upload pandas DataFrame as CSV to Google Drive"""
    service = get_drive_service()
    if not service:
        return None
    
    folder_id = get_folder_id()
    
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        existing_files = list_files_in_folder(folder_id)
        existing_file = next((f for f in existing_files if f['name'] == filename), None)
        
        file_metadata = {
            'name': filename,
            'mimeType': 'text/csv'
        }
        
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
    """Download CSV from Google Drive and return as DataFrame"""
    service = get_drive_service()
    if not service:
        return pd.DataFrame()
    
    try:
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

def upload_file_to_drive(local_path, drive_filename):
    """Upload any file to Google Drive"""
    service = get_drive_service()
    if not service:
        return None
    
    folder_id = get_folder_id()
    
    try:
        existing_files = list_files_in_folder(folder_id)
        existing_file = next((f for f in existing_files if f['name'] == drive_filename), None)
        
        file_metadata = {'name': drive_filename}
        
        if not existing_file:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(local_path, resumable=True)
        
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
        st.error(f"Error uploading file: {e}")
        return None

def download_file_from_drive(drive_filename, local_path):
    """Download any file from Google Drive"""
    service = get_drive_service()
    if not service:
        return False
    
    try:
        files = list_files_in_folder()
        file = next((f for f in files if f['name'] == drive_filename), None)
        
        if not file:
            return False
        
        request = service.files().get_media(fileId=file['id'])
        with open(local_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        return True
    
    except Exception as e:
        return False
