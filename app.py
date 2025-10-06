# Facebook Video Downloader Flask App

from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
from werkzeug.security import check_password_hash
import os
import yt_dlp
import uuid
import time
from threading import Thread
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'natorverse_fb_downloader_2025_secure_key_x9k2m5p8'
# Ensure downloads directory exists at import time (works with flask run and reloader)
os.makedirs('downloads', exist_ok=True)

# Stats file to track downloads
STATS_FILE = 'stats.json'

def load_stats():
    """Load download statistics"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {'total_downloads': 0, 'unique_users': set()}

def save_stats(stats):
    """Save download statistics"""
    # Convert set to list for JSON serialization
    stats_copy = stats.copy()
    stats_copy['unique_users'] = list(stats_copy['unique_users'])
    with open(STATS_FILE, 'w') as f:
        json.dump(stats_copy, f)

def update_stats(user_ip):
    """Update download statistics"""
    stats = load_stats()
    if isinstance(stats['unique_users'], list):
        stats['unique_users'] = set(stats['unique_users'])
    
    stats['total_downloads'] += 1
    stats['unique_users'].add(user_ip)
    save_stats(stats)
    return stats

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

@app.route('/api/stats')
def get_stats():
    """API endpoint to get real-time stats"""
    stats = load_stats()
    if isinstance(stats['unique_users'], list):
        unique_count = len(stats['unique_users'])
    else:
        unique_count = len(stats['unique_users'])
    
    return jsonify({
        'total_downloads': stats['total_downloads'],
        'unique_users': unique_count
    })

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

@app.route('/admin')
def admin():
    # Simple password protection (replace with your password)
    admin_password = 'admin123'  # Change this!

    if request.args.get('password') != admin_password:
        return '''
        <html>
        <head><title>Admin Access</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <form method="get">
                <input type="password" name="password" placeholder="Enter admin password" style="padding: 10px; font-size: 16px;">
                <button type="submit" style="padding: 10px 20px; font-size: 16px;">Access Dashboard</button>
            </form>
        </body>
        </html>

@app.route('/dmca')
def dmca():
    return render_template('dmca.html')


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

    # Generate professional filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_id = str(uuid.uuid4())[:8]  # Short unique ID
    filename = f"FB_Video_{timestamp}_{file_id}"
    outtmpl = f"downloads/{filename}.mp4"
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Update statistics
        user_ip = request.remote_addr
        update_stats(user_ip)

        # Provide a professional download filename with timestamp
        download_name = f"Facebook_Video_{timestamp}.mp4"
        response = send_file(outtmpl, as_attachment=True, download_name=download_name)

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

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
