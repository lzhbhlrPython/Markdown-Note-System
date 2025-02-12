import os
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

import sys
import threading
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

import app  # 导入 Flask 应用

def run_flask():
    # 启动 Flask 服务（非调试模式，避免多线程下重复加载）
    app.app.run(debug=False, use_reloader=False, port=25680)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Markdown Note System")
        self.resize(1024, 768)

        self.browser = QWebEngineView(self)
        self.setCentralWidget(self.browser)

        # 监听下载请求以解决保存文件问题
        self.browser.page().profile().downloadRequested.connect(self.handle_download)
        self.browser.load(QUrl("http://127.0.0.1:25680"))

    def handle_download(self, download):
        # 获取建议的文件名
        suggested_path = download.downloadFileName()
        file_path, _ = QFileDialog.getSaveFileName(self, "保存文件", suggested_path)
        if file_path:
            # 将 file_path 分解为目录和文件名
            directory, filename = os.path.split(file_path)
            # 设置下载目录和文件名，然后开始下载
            download.setDownloadDirectory(directory)
            download.setDownloadFileName(filename)
            download.accept()
        else:
            download.cancel()

    def trigger_blob_download(self, blob_url, filename):
        # 通过注入 JavaScript 触发下载 Blob 对象
        js_code = f"""
        (function(){{
            var a = document.createElement('a');
            a.href = '{blob_url}';
            a.download = '{filename}';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }})();
        """
        self.browser.page().runJavaScript(js_code)

if __name__ == '__main__':
    if not os.path.exists(app.app.config["DATA_DIR"]):
        os.makedirs(app.app.config["DATA_DIR"])
    # 后台线程启动 Flask 服务
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    qt_app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(qt_app.exec())