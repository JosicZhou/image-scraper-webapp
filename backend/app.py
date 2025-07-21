import os
import re
import requests
import io
import zipfile
import concurrent.futures
import threading
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS, cross_origin
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse, unquote

frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app = Flask(__name__, static_folder=frontend_folder, static_url_path='')
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Use proxy only if the environment variable is set
USE_PROXY = os.environ.get('USE_PROXY', 'false').lower() == 'true'
proxies = {
    'http': 'http://127.0.0.1:1080',
    'https': 'http://127.0.0.1:1080',
} if USE_PROXY else None

def get_proxies():
    """Returns the proxy dictionary if USE_PROXY is True, otherwise None."""
    if os.environ.get('USE_PROXY', 'false').lower() == 'true':
        return {
           'http': 'http://127.0.0.1:1080',
           'https': 'http://127.0.0.1:1080',
        }
    return None

def clean_fandom_url(url):
    """
    Removes Fandom/Wikia image resizing parameters from a URL to get the full-resolution image.
    e.g. .../image.png/revision/latest/scale-to-width-down/150 -> .../image.png
    """
    if 'wikia.nocookie.net' in url:
        # Find the image file extension and cut off any path info after it.
        match = re.search(r'\.(png|jpg|jpeg|gif|webp)', url, re.IGNORECASE)
        if match:
            end_pos = match.end()
            base_url = url[:end_pos]
            # Keep the original query string if it exists (e.g., ?cb=...)
            query_match = re.search(r'\?.*', url)
            query_string = query_match.group(0) if query_match else ''
            return base_url + query_string
    return url

def sanitize_filename(filename):
    """
    Sanitizes a string to be a valid filename.
    """
    # Replace underscores with spaces for better readability
    sanitized = filename.replace('_', ' ')
    # Remove characters that are invalid in Windows filenames
    sanitized = re.sub(r'[\\/*?:"<>|]',"", sanitized)
    # Limit length to prevent issues with file systems
    return sanitized[:100]

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=20, proxies=get_proxies())
        response.raise_for_status() # Raise an exception for bad status codes
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(response.content, 'html.parser')
    images = []
    for img in soup.find_all('img'):
        if isinstance(img, Tag):
            # Handle lazy-loaded images that use 'data-src'
            src = img.get('data-src') or img.get('src')
            alt = img.get('alt') # Will be None if 'alt' attribute doesn't exist

            # IMPORTANT: Only process images that have both a 'src' and a non-empty 'alt' attribute.
            if src and alt:
                # Make URL absolute
                src = urljoin(url, str(src))

                # Clean Fandom/Wikia URLs to get full resolution images
                src = clean_fandom_url(src)

                # --- HIERARCHICAL RENAMING LOGIC ---
                # Rule 1: By default, trust the alt text.
                final_name = str(alt)

                # Rule 2: Check if the alt text is suspicious (e.g., is a URL, too long).
                is_suspicious = ('http:' in final_name.lower()) or \
                                ('https:' in final_name.lower()) or \
                                ('.php' in final_name.lower()) or \
                                (len(final_name) > 80)

                # Rule 3: If suspicious, try to get a better name from the URL.
                if is_suspicious:
                    try:
                        parsed_url = urlparse(src)
                        filename_from_url = os.path.basename(parsed_url.path)
                        image_name_from_url, _ = os.path.splitext(unquote(filename_from_url))
                        
                        # If a name is successfully extracted, use it.
                        if image_name_from_url:
                            final_name = image_name_from_url
                    except Exception as e:
                        print(f"Could not parse name from URL {src} despite suspicious alt text: {e}")
                        # Fallback to the original (suspicious) alt text if parsing fails.
                        pass
                
                # FINAL UNIFICATION: Replace underscores with spaces for both display and download.
                final_name = final_name.replace('_', ' ')

                images.append({'src': src, 'alt': final_name})

    return jsonify(images)

@app.route('/proxy')
def proxy_image():
    image_url = request.args.get('url')
    if not image_url:
        # Return a 400 Bad Request error if the URL is missing
        return jsonify({"error": "Image URL parameter is required"}), 400
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Add a referer header to mimic a direct request from the site
        parsed_url = urlparse(image_url)
        headers['Referer'] = f"{parsed_url.scheme}://{parsed_url.netloc}/"

        response = requests.get(image_url, headers=headers, stream=True, timeout=20, proxies=get_proxies())
        response.raise_for_status()
        
        return send_file(
            io.BytesIO(response.content),
            mimetype=response.headers.get('content-type', 'image/jpeg')
        )
            
    except requests.exceptions.RequestException as e:
        # If fetching fails, return an error
        return jsonify({"error": str(e)}), 500

@app.route('/download-image', methods=['POST'])
@cross_origin()
def download_image():
    data = request.get_json()
    image_url = data.get('url')
    alt_text = data.get('alt', 'no_alt_name')

    if not image_url:
        return jsonify({"error": "Image URL is required"}), 400

    try:
        response = requests.get(image_url, stream=True, timeout=20, proxies=get_proxies())
        response.raise_for_status()

        # Get file extension
        content_type = response.headers.get('content-type')
        extension = '.jpg' # default
        if content_type:
            if 'jpeg' in content_type:
                extension = '.jpg'
            elif 'png' in content_type:
                extension = '.png'
            elif 'gif' in content_type:
                extension = '.gif'
            elif 'svg' in content_type:
                extension = '.svg'

        filename = sanitize_filename(alt_text) + extension
        
        return send_file(
            io.BytesIO(response.content),
            mimetype=response.headers.get('content-type', 'image/jpeg'),
            as_attachment=True,
            download_name=filename
        )

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download-selected', methods=['POST'])
@cross_origin()
def download_selected():
    data = request.get_json()
    images_to_download = data.get('images', [])

    if not images_to_download:
        return jsonify({"error": "Image list is required"}), 400

    seen_filenames = set()
    lock = threading.Lock()

    def download_and_prepare(image_info):
        image_url = image_info.get('src')
        alt_text = image_info.get('alt', 'no_alt_name')

        if not image_url:
            return None

        try:
            response = requests.get(image_url, stream=True, timeout=20, proxies=get_proxies())
            response.raise_for_status()

            content_type = response.headers.get('content-type')
            extension = '.jpg'
            if content_type:
                if 'jpeg' in content_type:
                    extension = '.jpg'
                elif 'png' in content_type:
                    extension = '.png'
                elif 'gif' in content_type:
                    extension = '.gif'
                elif 'svg' in content_type:
                    extension = '.svg'
            
            filename = f"{sanitize_filename(alt_text)}{extension}"
            
            with lock:
                if filename in seen_filenames:
                    print(f"Skipping duplicate file: {filename}")
                    return None
                seen_filenames.add(filename)

            return (filename, response.content)
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {image_url}: {e}")
            return None

    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w') as zf:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_image = {executor.submit(download_and_prepare, img): img for img in images_to_download}
            
            for future in concurrent.futures.as_completed(future_to_image):
                result = future.result()
                if result:
                    filename, content = result
                    zf.writestr(filename, content)

    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='images.zip'
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # For local development, you might want to enable the proxy.
    # You can do this by setting an environment variable before running the script:
    # $env:USE_PROXY="true"
    # Or in Linux/macOS:
    # export USE_PROXY=true
    app.run(host='0.0.0.0', debug=True, port=5000)
