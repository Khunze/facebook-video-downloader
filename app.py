# Facebook Video Downloader Flask App

from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import yt_dlp
import uuid
import tempfile

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash messages
# Ensure downloads directory exists at import time (works with flask run and reloader)
os.makedirs('downloads', exist_ok=True)

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


@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    if not url:
        flash('Please enter a Facebook video URL.')
        return redirect(url_for('index'))
    # Basic validation to reduce accidental non-Facebook inputs
    if not (url.startswith('http://') or url.startswith('https://')):
        flash('Please provide a valid URL starting with http:// or https://')
        return redirect(url_for('index'))

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
        'format': 'best[ext=mp4]/best',
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
        return send_file(outtmpl, as_attachment=True, download_name='facebook_video.mp4')
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
