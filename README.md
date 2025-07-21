# Image Scraper

This project allows you to scrape images from a website, view them, and download them individually or in bulk.

## How to Run

### 1. Backend Setup

First, you need to set up and run the Python backend.

```bash
# Navigate to the backend directory
cd backend

# Install the required Python packages
# It's recommended to use a virtual environment
pip install -r requirements.txt

# Run the Flask server
python app.py
```

The backend server will start running on `http://127.0.0.1:5000`.

### 2. Frontend Setup

The frontend is a simple set of HTML, CSS, and JavaScript files. The easiest way to run it is by using a simple local HTTP server.

```bash
# Open a NEW terminal window/tab
# Navigate to the frontend directory
cd frontend

# Start a simple Python HTTP server
# If you have Python 3:
python -m http.server 8000
# If you have Python 2:
# python -m SimpleHTTPServer 8000
```

Now, open your web browser and go to the following address:

[http://localhost:8000](http://localhost:8000)

### How to Use

1.  Paste a website URL into the input box (e.g., `https://www.wikipedia.org/`).
2.  Click the "Scrape Images" button.
3.  The application will find and display the first 50 images from the website.
4.  You can then:
    *   Click "Load More" to see the next batch of images.
    *   Use the checkboxes to select images.
    *   Download or delete individual or selected images.
    *   Downloaded images will be saved in the `backend/uploads` directory.

## Project Structure

```
/
├── backend/
│   ├── app.py         # 后端 Flask 服务
│   ├── requirements.txt # 后端依赖库
│   └── uploads/       # 保存下载的图片
├── frontend/
│   ├── index.html     # 前端页面
│   ├── style.css      # 页面样式
│   └── script.js      # 页面交互逻辑
└── README.md          # 项目说明和运行指南
```
