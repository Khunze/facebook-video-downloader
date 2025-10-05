# Facebook Video Downloader Flask App

from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import yt_dlp
import uuid
import tempfile
import time
from threading import Thread

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash messages
# Ensure downloads directory exists at import time (works with flask run and reloader)
os.makedirs('downloads', exist_ok=True)

def cleanup_old_files():
    """Delete files older than 10 days from downloads folder"""
    while True:
        try:
            current_time = time.time()
            downloads_dir = 'downloads'
            for filename in os.listdir(downloads_dir):
                filepath = os.path.join(downloads_dir, filename)
                if os.path.isfile(filepath):
                    # Check if file is older than 10 days (864000 seconds)
                    if current_time - os.path.getmtime(filepath) > 864000:
                        os.remove(filepath)
                        print(f"Cleaned up old file: {filename}")
        except Exception as e:
            print(f"Cleanup error: {e}")
        # Run cleanup every 24 hours
        time.sleep(86400)

# Start cleanup thread
cleanup_thread = Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how-it-works.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/dmca')
def dmca():
    return render_template('dmca.html')

@app.route('/files')
def list_files():
    """List all downloaded files"""
    try:
        files = []
        downloads_dir = 'downloads'
        for filename in os.listdir(downloads_dir):
            filepath = os.path.join(downloads_dir, filename)
            if os.path.isfile(filepath):
                # Get file info
                file_size = os.path.getsize(filepath)
                file_time = os.path.getmtime(filepath)
                files.append({
                    'name': filename,
                    'size': round(file_size / (1024 * 1024), 2),  # Size in MB
                    'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_time))
                })
        # Sort by date (newest first)
        files.sort(key=lambda x: x['date'], reverse=True)
        return render_template('files.html', files=files, total=len(files))
    except Exception as e:
        return f"Error listing files: {str(e)}", 500

@app.route('/files/<filename>')
def download_file(filename):
    """Direct access to download a specific file"""
    try:
        filepath = os.path.join('downloads', filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return "File not found", 404
    except Exception as e:
        return f"Error downloading file: {str(e)}", 500


@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    if not url:
        return redirect(url_for('index', error='Please enter a Facebook video URL'))
    # Basic validation to reduce accidental non-Facebook inputs
    if not (url.startswith('http://') or url.startswith('https://')):
        return redirect(url_for('index', error='Please provide a valid URL starting with http:// or https://'))

    # Get quality preference
    quality = request.form.get('quality', 'best')
    quality_formats = {
        'best': 'best[ext=mp4]/best',
        'hd': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
        'sd': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best',
        'low': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best'
    }

    cookies_file = None
    if 'cookies' in request.files and request.files['cookies'].filename:
        cookies_upload = request.files['cookies']
        # Save cookies to a real temporary file (system temp). Windows-friendly.
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        cookies_upload.save(temp.name)
        cookies_file = temp.name

    file_id = str(uuid.uuid4())
    outtmpl = f"downloads/{file_id}.mp4"
    ydl_opts = {
        'outtmpl': outtmpl,
        'format': quality_formats.get(quality, 'best[ext=mp4]/best'),
        'quiet': True,
        'noplaylist': True,
        # Improve robustness with Facebook
        'retries': 3,
        'fragment_retries': 3,
        'http_headers': {
            # Modern desktop UA helps some FB endpoints
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Referer': 'https://www.facebook.com/',
        },
    }
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # Provide a friendly download filename
        response = send_file(outtmpl, as_attachment=True, download_name='facebook_video.mp4')
        
        # Files will be kept for 10 days (automatic cleanup handles deletion)
        # No immediate deletion - files remain available
        return response
    except Exception as e:
        error_msg = str(e)
        # Simplify common errors for users
        if 'private' in error_msg.lower() or 'unavailable' in error_msg.lower():
            error_msg = 'This video is private or unavailable. Please check the URL and try again.'
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            error_msg = 'Video not found. Please check the URL and try again.'
        elif 'network' in error_msg.lower() or 'connection' in error_msg.lower():
            error_msg = 'Network error. Please check your connection and try again.'
        else:
            error_msg = f'Download failed: {error_msg[:100]}'  # Limit error message length
        
        return redirect(url_for('index', error=error_msg))
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
