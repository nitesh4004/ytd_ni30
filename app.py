import streamlit as st
import yt_dlp
import os
import shutil
import zipfile
import tempfile
import random

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

def get_random_user_agent():
    """Returns a random user agent to avoid fingerprinting"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    ]
    return random.choice(agents)

def download_content(url, download_subs, is_playlist, cookies_content=None):
    temp_dir = tempfile.mkdtemp()
    
    # 1. Setup Cookies File
    cookie_file_path = None
    if cookies_content:
        # Create a temp file for cookies with strictly correct permissions
        fd, cookie_file_path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(cookies_content)

    # 2. Configure yt-dlp Options
    ydl_opts = {
        # Quality
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        
        # Subtitles
        'writesubtitles': download_subs,
        'writeautomaticsub': False,
        'subtitleslangs': ['en'],
        
        # Playlist Handling
        'noplaylist': not is_playlist,
        'ignoreerrors': True, # If one video in playlist fails, keep going
        
        # Network / Anti-Bot
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True, # bypass SSL issues on cloud
        'user_agent': get_random_user_agent(),
        'referer': 'https://www.youtube.com/',
        'socket_timeout': 30,
        
        # Cloud/Server Fixes
        'source_address': '0.0.0.0', # Force IPv4
    }

    # Attach cookies if they exist
    if cookie_file_path:
        ydl_opts['cookiefile'] = cookie_file_path

    # 3. Execution
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # clear cache to prevent using old bad tokens
            ydl.cache.remove()
            ydl.download([url])
        
        # Cleanup cookie file
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
            
        return temp_dir, None
    except Exception as e:
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
        return None, str(e)

# --- UI Layout ---

st.title("📺 YouTube Downloader (Cloud Fixed)")

# ERROR EXPLANATION BOX
st.info("""
**READ THIS IF IT FAILS:**
If you see `HTTP Error 403: Forbidden`, it means YouTube blocked this server.
You **MUST** paste your browser cookies in the box below to fix it.
""")

# 1. URL Input
url = st.text_input("Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")

# 2. Settings
col1, col2 = st.columns(2)
with col1:
    include_subs = st.checkbox("Download Subtitles", value=False)
with col2:
    is_playlist_mode = st.checkbox("Is this a Playlist?", value=False)

# 3. COOKIE INPUT (CRITICAL)
with st.expander("🍪 Authentication (REQUIRED for Streamlit Cloud)", expanded=True):
    st.write("1. Install 'Get cookies.txt LOCALLY' extension (Chrome/Firefox).")
    st.write("2. Open YouTube, click extension, click 'Copy'.")
    st.write("3. Paste below:")
    cookies_input = st.text_area("Paste Cookies Here:", height=150, help="Paste the full content of the cookies.txt file here.")

st.divider()

# 4. Download Button
if st.button("🚀 Start Download", type="primary"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.text("Initializing connection...")
        progress_bar.progress(10)

        # Execute Download
        with st.spinner("Downloading... (This uses FFmpeg for 1080p+)"):
            cookies_to_pass = cookies_input if cookies_input.strip() != "" else None
            download_path, error = download_content(url, include_subs, is_playlist_mode, cookies_to_pass)

        # Handle Results
        if error:
            st.error("❌ Error Occurred")
            st.error(f"Details: {error}")
            if "403" in error:
                st.warning("👉 **Diagnosis:** You are being blocked by YouTube. Please fill in the 'Authentication' box with fresh cookies.")
        else:
            progress_bar.progress(100)
            status_text.success("Success!")
            
            # Check for files
            try:
                files = os.listdir(download_path)
                video_files = [f for f in files if f.endswith(('.mp4', '.mkv', '.webm'))]
                
                if not files:
                    st.error("Download completed, but no files found. (The stream might have been blocked silently).")
                
                # Single Video Download
                elif not is_playlist_mode and len(video_files) == 1:
                    vid_name = video_files[0]
                    vid_path = os.path.join(download_path, vid_name)
                    with open(vid_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Download Video",
                            data=f,
                            file_name=vid_name,
                            mime="video/mp4"
                        )

                # Playlist Download (ZIP)
                else:
                    zip_name = "download.zip"
                    zip_path = os.path.join(tempfile.gettempdir(), zip_name)
                    zip_directory(download_path, zip_path)
                    
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="📦 Download ZIP",
                            data=f,
                            file_name="youtube_downloads.zip",
                            mime="application/zip"
                        )
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
            except Exception as e:
                st.error(f"File processing error: {e}")
            
            # Cleanup
            if os.path.exists(download_path):
                shutil.rmtree(download_path)
