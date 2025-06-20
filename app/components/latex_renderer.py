from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, QTimer
import os

class LaTeXRenderer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.MinimumExpanding
        )
        
        # 创建定时器用于检查内容高度
        self.heightCheckTimer = QTimer(self)
        self.heightCheckTimer.setInterval(100)  # 100ms 检查一次
        self.heightCheckTimer.timeout.connect(self.checkContentHeight)
        
        self.template = """
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
                <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
                <script>
                    window.MathJax = {
                        startup: {
                            pageReady: function() {
                                return MathJax.startup.defaultPageReady().then(function() {
                                    // 当 MathJax 完成渲染后，发送高度信息
                                    var height = document.body.scrollHeight;
                                    window.parent.postMessage(height, '*');
                                });
                            }
                        }
                    };
                </script>
                <style>
                    body {
                        margin: 0;
                        padding: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 60px;
                        height: auto;
                        background: white;
                    }
                    .math {
                        font-size: 18px;
                        line-height: 1.2;
                        padding: 16px;
                        margin: 0;
                        width: 100%;
                        text-align: center;
                    }
                    .MathJax {
                        margin: 0 !important;
                        padding: 0 !important;
                        display: inline-block !important;
                    }
                </style>
            </head>
            <body>
                <div class="math">$$__LATEX__$$</div>
            </body>
            </html>
        """

    def render_latex(self, latex_str):
        """渲染LaTeX公式"""
        if not latex_str:
            self.setHtml("")
            self.heightCheckTimer.stop()
            return
            
        # HTML模板
        html = self.template.replace('__LATEX__', latex_str)
        self.setHtml(html)
        
        # 启动高度检查定时器
        self.heightCheckTimer.start()

    def checkContentHeight(self):
        """检查内容高度"""
        # 执行 JavaScript 来获取内容高度
        self.page().runJavaScript("""
            document.body.scrollHeight;
        """, self.updateHeight)

    def updateHeight(self, height):
        """更新高度"""
        if height and height > self.minimumHeight():
            # 添加一些边距
            self.setFixedHeight(height + 32)
            # 停止定时器
            self.heightCheckTimer.stop()

    def get_image(self):
        """获取渲染后的图像，裁剪掉多余的空白"""
        full = self.grab()
        # 获取非空白区域
        image = full.toImage()
        rect = image.rect()
        for x in range(rect.left(), rect.right()):
            for y in range(rect.top(), rect.bottom()):
                if image.pixelColor(x, y).alpha() > 0:
                    rect.setLeft(max(0, x - 5))  # 左边留5像素边距
                    break
            else:
                continue
            break
        
        for x in range(rect.right(), rect.left(), -1):
            for y in range(rect.top(), rect.bottom()):
                if image.pixelColor(x, y).alpha() > 0:
                    rect.setRight(min(image.width(), x + 5))  # 右边留5像素边距
                    break
            else:
                continue
            break
        
        return full.copy(rect) 