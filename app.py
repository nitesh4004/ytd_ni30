import streamlit as st
import yt_dlp
import os
import shutil
import zipfile
import time

# --- Page Config ---
st.set_page_config(page_title="YouTube Downloader", page_icon="📺")

# --- Helper Functions ---

def zip_directory(folder_path, zip_path):
    """Zips a directory for playlist downloads."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

def get_video_info(url):
    """Fetches video/playlist metadata without downloading."""
    ydl_opts = {'quiet': True, 'extract_flat': True} 
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            return None

def download_content(url, download_subs, is_playlist):
    """Downloads video(s) to a temporary folder."""
    
    # Create a unique temporary directory for this download
    temp_dir = "temp_downloads"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # yt-dlp Options
    ydl_opts = {
        # Optimum Quality: Best video + Best audio, merged
        'format': 'bestvideo+bestaudio/best',
        
        # Save path template
        'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
        
        # Post-processors to merge video/audio into mp4 if possible
        'merge_output_format': 'mp4',
        
        # Subtitles
        'writesubtitles': download_subs,
        'writeautomaticsub': False, # Change to True if you want auto-generated caps
        'subtitleslangs': ['en'],   # English subtitles. remove list to get all
        
        # Stability
        'noplaylist': not is_playlist, # If False, it allows playlist downloading
        'quiet': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return temp_dir, None
    except Exception as e:
        return None, str(e)

# --- UI Layout ---

st.title("📺 Ultimate YouTube Downloader")
st.markdown("Download Videos and Playlists in **Optimum Quality** with Subtitles.")

# Input Section
url = st.text_input("Paste YouTube URL here:")

col1, col2 = st.columns(2)
with col1:
    include_subs = st.checkbox("Download Subtitles (English)", value=False)
with col2:
    is_playlist_mode = st.checkbox("Is this a Playlist?", value=False)

# Analyze Button (Optional but good for UX)
if url:
    if st.button("Analyze URL"):
        with st.spinner("Fetching metadata..."):
            info = get_video_info(url)
            if info:
                title = info.get('title', 'Unknown Title')
                st.success(f"Found: **{title}**")
                if 'thumbnails' in info and info['thumbnails']:
                    st.image(info['thumbnails'][-1]['url'], width=300)
            else:
                st.error("Invalid URL or Video unavailable.")

st.divider()

# Download Action
if st.button("🚀 Start Download"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.text("Processing... This may take a while for high quality/playlists.")
        progress_bar.progress(10)

        # Perform Download
        with st.spinner("Downloading and Merging (FFmpeg)..."):
            download_path, error = download_content(url, include_subs, is_playlist_mode)
        
        if error:
            st.error(f"Error occurred: {error}")
        else:
            progress_bar.progress(100)
            status_text.success("Processing Complete!")
            
            # Check what we have in the folder
            files = os.listdir(download_path)
            
            if len(files) == 0:
                st.error("Download failed silently. No files found.")
            
            # Case 1: Single Video (Video file + maybe .vtt subtitle file)
            elif not is_playlist_mode and len(files) <= 3: 
                # Find the video file (not the sub file)
                video_file = None
                sub_file = None
                
                for f in files:
                    if f.endswith(('.mp4', '.mkv', '.webm')):
                        video_file = f
                    elif f.endswith('.vtt'):
                        sub_file = f
                
                if video_file:
                    file_path = os.path.join(download_path, video_file)
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"💾 Download Video: {video_file}",
                            data=f,
                            file_name=video_file,
                            mime="video/mp4"
                        )
                
                if sub_file:
                    sub_path = os.path.join(download_path, sub_file)
                    with open(sub_path, "rb") as f:
                        st.download_button(
                            label=f"📝 Download Subtitles: {sub_file}",
                            data=f,
                            file_name=sub_file,
                            mime="text/vtt"
                        )

            # Case 2: Playlist (Multiple files)
            else:
                st.info("Playlist detected. Compressing into ZIP...")
                zip_name = "playlist_download.zip"
                zip_directory(download_path, zip_name)
                
                with open(zip_name, "rb") as f:
                    st.download_button(
                        label="📦 Download Playlist (ZIP)",
                        data=f,
                        file_name=zip_name,
                        mime="application/zip"
                    )
                
                # Cleanup zip
                os.remove(zip_name)

            # Cleanup temp folder after reading into memory
            # Note: In a real production app, you might use a tempfile library 
            # to avoid permission issues, but this works for local scripts.
            shutil.rmtree(download_path)

st.markdown("---")
st.caption("Note: This tool requires FFmpeg installed on the host machine for 1080p+ merging.")