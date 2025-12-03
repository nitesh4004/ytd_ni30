import streamlit as st
import yt_dlp
import os
import shutil
import zipfile
import tempfile
import time

# --- Page Config ---
st.set_page_config(page_title="Pro YouTube Downloader", page_icon="📺", layout="centered")

# --- Helper Functions ---

def zip_directory(folder_path, zip_path):
    """Zips a directory for playlist downloads."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

def download_content(url, download_subs, is_playlist, cookies_content=None):
    """
    Downloads content to a temp folder.
    Returns: (path_to_downloaded_folder, error_message)
    """
    temp_dir = tempfile.mkdtemp()
    
    # Handle Cookies
    cookie_file_path = None
    if cookies_content:
        fd, cookie_file_path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(cookies_content)

    # --- UPDATED OPTIONS TO FIX 403 FORBIDDEN ---
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        
        # Subtitle Options
        'writesubtitles': download_subs,
        'writeautomaticsub': False,
        'subtitleslangs': ['en'],
        
        # Playlist Options
        'noplaylist': not is_playlist,
        
        # --- ANTI-BOT / 403 FIXES ---
        'quiet': True,
        'no_warnings': True,
        # Spoof a common browser User-Agent
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # Use specific extractor args to emulate a web client
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android'], # Try to look like a web browser or android phone
                'player_skip': ['js', 'configs', 'webpage'], 
            }
        },
        # Force IPv4 (IPv6 often causes 403 errors on some networks)
        'source_address': '0.0.0.0', 
    }

    if cookie_file_path:
        ydl_opts['cookiefile'] = cookie_file_path

    try:
        # Clear internal cache before downloading to remove old "bad" tokens
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.cache.remove()
            ydl.download([url])
        
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
            
        return temp_dir, None
    except Exception as e:
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
        return None, str(e)

# --- UI Layout ---

st.title("📺 Ultimate YouTube Downloader")
st.markdown("""
<style>
    .stAlert { padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# Instructions for 403 Error
with st.expander("🔴 Getting '403 Forbidden' Error? Read this."):
    st.warning("""
    **403 Forbidden** means YouTube detected this tool as a bot. 
    To fix this, you must use **Cookies**:
    1. Install 'Get cookies.txt LOCALLY' extension for Chrome/Firefox.
    2. Go to YouTube, click the extension, and copy the cookies.
    3. Paste them in the 'Advanced: Add Cookies' box below.
    """)

# 1. Inputs
url = st.text_input("Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    include_subs = st.checkbox("Download Subtitles (English)", value=False)
with col2:
    is_playlist_mode = st.checkbox("Is this a Playlist?", value=False)

# 2. Cookies (Critical for 403 fix)
st.markdown("---")
st.write("### 🍪 Authentication (Fixes Errors)")
cookies_input = st.text_area(
    "Paste Netscape Cookies here (Required for Age-Restricted or blocked videos):", 
    height=100,
    placeholder="# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/..."
)

st.markdown("---")

# 3. Action
if st.button("🚀 Start Download", type="primary"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.text("Connecting to YouTube...")
        progress_bar.progress(10)

        with st.spinner("Processing... (If this takes >1 min, check cookies)"):
            cookies_to_pass = cookies_input if cookies_input.strip() != "" else None
            download_path, error = download_content(url, include_subs, is_playlist_mode, cookies_to_pass)

        if error:
            st.error("❌ Download Failed")
            st.code(error, language="bash")
            st.error("💡 Recommendation: Paste your browser cookies in the box above to bypass this error.")
        else:
            progress_bar.progress(100)
            status_text.success("Done! Preparing download...")
            
            files = os.listdir(download_path)
            
            if not files:
                st.error("Download finished but folder is empty. (Bot detection likely blocked the file stream).")
            else:
                video_files = [f for f in files if f.endswith(('.mp4', '.mkv', '.webm'))]
                
                # Single Video Logic
                if not is_playlist_mode and len(video_files) == 1:
                    vid_name = video_files[0]
                    vid_path = os.path.join(download_path, vid_name)
                    with open(vid_path, "rb") as f:
                        st.download_button(
                            label=f"💾 Download Video ({os.path.getsize(vid_path)/1024/1024:.1f} MB)",
                            data=f,
                            file_name=vid_name,
                            mime="video/mp4"
                        )
                
                # Playlist Logic
                else:
                    zip_name = "youtube_download.zip"
                    zip_path = os.path.join(tempfile.gettempdir(), zip_name)
                    zip_directory(download_path, zip_path)
                    
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="📦 Download All (ZIP)",
                            data=f,
                            file_name="downloaded_playlist.zip",
                            mime="application/zip"
                        )
                    if os.path.exists(zip_path):
                        os.remove(zip_path)

            if os.path.exists(download_path):
                shutil.rmtree(download_path)
