from qfluentwidgets import (ScrollArea, PrimaryPushButton, CardWidget, 
                          ProgressBar, InfoBar, InfoBarPosition, ImageLabel,
                          LineEdit, TextEdit, PushButton, ToolButton,
                          StateToolTip, PrimaryToolButton, Dialog, MessageBox)
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtCore import Qt, QTimer, QSize, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QPainterPath
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QApplication, QLabel, QGridLayout, QFileDialog,
                           QTabWidget, QDialog, QSizePolicy)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from ..common.config import cfg
import cv2
import numpy as np
from ..components.latex_renderer import LaTeXRenderer
from ..common.db_manager import DatabaseManager
from ..common.ocr_service import OcrServiceFactory


class DrawingBoard(QWidget):
    """ 手写板 """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = None  # 当前正在绘制的路径
        self.lastPoint = None
        self.setMinimumSize(300, 300)
        self.paths = []  # 已完成的路径列表
        self.erasing = False  # 是否正在擦除
        self.eraser_size = 30  # 增大橡皮擦大小
        
        # 设置圆角和背景样式
        self.setStyleSheet("""
            DrawingBoard {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制白色背景（带圆角）
        path = QPainterPath()
        rect = self.rect()
        # 转换 QRect 为 QRectF
        rectf = QRectF(rect)
        path.addRoundedRect(rectf, 8, 8)
        painter.fillPath(path, Qt.white)
        
        # 绘制网格线（考虑圆角裁剪）
        painter.setClipPath(path)
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.SolidLine))
        for i in range(0, self.width(), 20):
            painter.drawLine(i, 0, i, self.height())
        for i in range(0, self.height(), 20):
            painter.drawLine(0, i, self.width(), i)
            
        # 绘制所有路径
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        for path in self.paths:
            painter.drawPath(path)
        # 绘制当前路径
        if self.path:
            painter.drawPath(self.path)
            
        # 如果正在擦除，绘制橡皮擦预览
        if self.erasing and self.lastPoint:
            painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
            painter.drawEllipse(self.lastPoint, self.eraser_size/2, self.eraser_size/2)
        
    def mousePressEvent(self, event):
        self.lastPoint = event.pos()
        if event.button() == Qt.RightButton:
            self.erasing = True
            self.erasePaths(event.pos())
        else:
            self.erasing = False
            self.path = QPainterPath()
            self.path.moveTo(event.pos())
        self.update()
        
    def mouseMoveEvent(self, event):
        if self.erasing:
            self.erasePaths(event.pos())
            self.lastPoint = event.pos()
        elif self.path:
            self.path.lineTo(event.pos())
            self.lastPoint = event.pos()
        self.update()
        
    def mouseReleaseEvent(self, event):
        if self.erasing:
            self.erasing = False
        elif self.path and not self.path.isEmpty():
            self.paths.append(self.path)
            self.path = None
        self.update()
        
    def erasePaths(self, pos):
        """擦除指定位置的路径"""
        # 创建擦除区域
        eraser_rect = QRectF(
            pos.x() - self.eraser_size/2,
            pos.y() - self.eraser_size/2,
            self.eraser_size,
            self.eraser_size
        )
        
        # 检查并移除与擦除区域相交的路径
        paths_to_remove = []
        for path in self.paths:
            # 获取路径的所有点
            points = []
            for i in range(path.elementCount()):
                e = path.elementAt(i)
                points.append(QPointF(e.x, e.y))
            
            # 检查路径上的点是否在擦除区域内
            for point in points:
                if eraser_rect.contains(point):
                    paths_to_remove.append(path)
                    break
        
        # 移除相交的路径
        for path in paths_to_remove:
            self.paths.remove(path)
            
        # 如果当前路径与擦除区域相交，也清除它
        if self.path:
            points = []
            for i in range(self.path.elementCount()):
                e = self.path.elementAt(i)
                points.append(QPointF(e.x, e.y))
            
            for point in points:
                if eraser_rect.contains(point):
                    self.path = None
                    break
        
    def resizeEvent(self, event):
        """处理大小变化事件"""
        super().resizeEvent(event)
        # 确保绘图区域始终占满整个控件
        self.setMinimumSize(self.parent().size())
        
    def clear(self):
        self.path = None
        self.paths.clear()
        self.update()
        
    def undo(self):
        if self.paths:  # 如果有已完成的路径
            self.paths.pop()  # 移除最后一条路径
            self.update()
        elif self.path:  # 如果有当前正在绘制的路径
            self.path = None  # 清除当前路径
            self.update()
        
    def getImage(self):
        image = QImage(self.size(), QImage.Format_RGB888)
        image.fill(Qt.white)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.render(painter)
        return image


class DrawingDialog(QDialog):
    """ 手写输入对话框 """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('手写输入')
        
        # 设置对话框大小
        self.setFixedSize(500, 580)  # 增加一点高度来放置提示文本
        
        # 创建主布局
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 16)  # 只保留底部边距
        self.mainLayout.setSpacing(8)  # 减小间距
        
        # 创建手写板
        self.drawingBoard = DrawingBoard(self)
        self.mainLayout.addWidget(self.drawingBoard)
        
        # 添加提示文本
        self.tipLabel = QLabel('Tips：按住右键滑动可以擦除笔迹', self)
        self.tipLabel.setStyleSheet("""
            QLabel {
                color: #666666;
                padding: 8px;
                font-weight: bold;  /* 加粗文字 */
                font-size: 13px;    /* 稍微增大字号 */
            }
        """)
        self.mainLayout.addWidget(self.tipLabel)
        
        # 按钮布局
        self.buttonLayout = QHBoxLayout()
        self.clearButton = ToolButton(FIF.DELETE, self)
        self.clearButton.setToolTip('清空')
        self.undoButton = ToolButton(FIF.CANCEL, self)
        self.undoButton.setToolTip('撤销')
        self.submitButton = PrimaryPushButton('识别', self, FIF.SEND)
        
        self.buttonLayout.addWidget(self.clearButton)
        self.buttonLayout.addWidget(self.undoButton)
        self.buttonLayout.addWidget(self.submitButton)
        self.buttonLayout.setContentsMargins(16, 0, 16, 0)  # 按钮左右留边距
        
        # 添加按钮布局
        self.mainLayout.addLayout(self.buttonLayout)
        
        # 绑定事件
        self.clearButton.clicked.connect(self.confirmClear)
        self.undoButton.clicked.connect(self.drawingBoard.undo)
        self.submitButton.clicked.connect(self.checkAndSubmit)
        
    def checkAndSubmit(self):
        """检查画布内容并提交"""
        if not self.drawingBoard.paths:  # 如果没有任何笔迹
            InfoBar.warning(
                title='提示',
                content='请先绘制公式再提交',
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        self.accept()  # 有内容时才接受对话框

    def confirmClear(self):
        """确认清空画板"""
        w = MessageBox(
            '清空确认',
            '确定要清空所有笔迹吗？',
            self
        )
        if w.exec():
            self.drawingBoard.clear()

    def getImage(self):
        return self.drawingBoard.getImage()


class LatexOcrInterface(ScrollArea):
    """ 公式识别界面 """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.db = DatabaseManager()
        self.setObjectName('latexOcrInterface')
        # 添加样式
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QWidget#latexOcrInterface {
                background-color: transparent;
            }
            
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        self.stateTooltip = None
        self.updateTimer = QTimer()
        self.updateTimer.setSingleShot(True)
        self.updateTimer.timeout.connect(self.doUpdateLatex)
        self.ocr_service = OcrServiceFactory.create_service()  # 创建识别服务
        self.initUI()

    def initUI(self):
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        # 主布局
        self.hBoxLayout = QHBoxLayout(self.view)
        self.hBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.hBoxLayout.setSpacing(16)
        
        # 左侧输入区域
        self.inputCard = CardWidget(self.view)
        self.inputLayout = QVBoxLayout(self.inputCard)
        self.inputLayout.setSpacing(16)
        
        # 创建按钮容器并设置垂直居中
        self.buttonContainer = QWidget()
        self.buttonLayout = QVBoxLayout(self.buttonContainer)
        self.buttonLayout.setSpacing(16)
        self.buttonLayout.setAlignment(Qt.AlignCenter)
        
        # 两个主要按钮
        self.uploadButton = PrimaryPushButton('选择图片', self, FIF.PHOTO)
        self.drawButton = PrimaryPushButton('手写输入', self, FIF.EDIT)
        
        # 添加按钮
        self.buttonLayout.addWidget(self.uploadButton)
        self.buttonLayout.addWidget(self.drawButton)
        
        # 添加提示文本
        self.tipLabel = QLabel('提示：直接粘贴也可上传图片', self)
        self.tipLabel.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                margin-top: 8px;
            }
        """)
        self.buttonLayout.addWidget(self.tipLabel, 0, Qt.AlignCenter)
        
        # 图片显示区域（初始隐藏）
        self.imageLabel = ImageLabel(self)
        self.imageLabel.setFixedSize(300, 300)
        self.imageLabel.hide()
        
        # 添加到输入布局
        self.inputLayout.addWidget(self.buttonContainer)
        self.inputLayout.addWidget(self.imageLabel, 0, Qt.AlignCenter)
        
        # 右侧结果区域
        self.resultCard = CardWidget(self.view)
        self.resultCard.hide()
        self.resultCard.setFixedHeight(350)  # 增加一点高度
        self.resultLayout = QVBoxLayout(self.resultCard)
        self.resultLayout.setSpacing(8)
        self.resultLayout.setContentsMargins(16, 16, 16, 16)
        
        # 添加标题
        self.titleLabel = QLabel('识别结果', self)
        self.titleLabel.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: black;
                padding-bottom: 8px;
            }
        """)
        
        # 创建一个容器来包装渲染器
        self.rendererContainer = QWidget()
        self.rendererContainer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.MinimumExpanding
        )
        self.rendererLayout = QVBoxLayout(self.rendererContainer)
        self.rendererLayout.setContentsMargins(0, 0, 0, 0)
        self.rendererLayout.setSpacing(0)
        
        # LaTeX渲染
        self.latexRenderer = LaTeXRenderer(self)
        self.latexRenderer.setMinimumWidth(600)
        self.latexRenderer.setMinimumHeight(60)
        self.latexRenderer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.MinimumExpanding
        )
        
        # 将渲染器添加到容器中
        self.rendererLayout.addWidget(self.latexRenderer)
        
        # 置信度布局
        self.confidenceLayout = QHBoxLayout()
        self.confidenceLayout.setContentsMargins(0, 0, 0, 0)
        self.confidenceLabel = QLabel('置信度:', self)
        self.confidenceBar = ProgressBar(self)
        self.confidenceBar.setFixedWidth(400)
        self.confidenceBar.setFixedHeight(4)  # 进一步减小高度
        self.confidenceValueLabel = QLabel('0%', self)
        self.confidenceLayout.addWidget(self.confidenceLabel)
        self.confidenceLayout.addWidget(self.confidenceBar, 1)
        self.confidenceLayout.addWidget(self.confidenceValueLabel)
        
        # 结果显示
        self.resultEdit = TextEdit(self)
        self.resultEdit.setReadOnly(False)
        self.resultEdit.setPlaceholderText('识别结果将在这里显示，您也可以直接编辑')
        self.resultEdit.setMinimumHeight(100)  # 设置最小高度
        self.resultEdit.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.MinimumExpanding  # 允许垂直方向扩展
        )
        
        # 复制按钮
        self.copyLayout = QHBoxLayout()
        self.copyLayout.setSpacing(16)  # 增加按钮间距
        
        # 创建带文字的按钮
        self.copyTextButton = PrimaryPushButton('复制Latex', self, FIF.COPY)
        self.copyLatexButton = PrimaryPushButton('复制LaTeX(带$$)', self, FIF.CODE)
        self.copyImageButton = PrimaryPushButton('复制图片', self, FIF.PHOTO)
        
        # 添加按钮
        self.copyLayout.addWidget(self.copyTextButton)
        self.copyLayout.addWidget(self.copyLatexButton)
        self.copyLayout.addWidget(self.copyImageButton)
        self.copyLayout.addStretch(1)
        
        # 添加到结果布局
        self.resultLayout.addWidget(self.titleLabel)
        self.resultLayout.addWidget(self.rendererContainer)
        self.resultLayout.addLayout(self.confidenceLayout)
        self.resultLayout.addWidget(self.resultEdit)
        self.resultLayout.addLayout(self.copyLayout)
        
        # 添加到主布局
        self.hBoxLayout.addWidget(self.inputCard)
        self.hBoxLayout.addWidget(self.resultCard)
        self.hBoxLayout.setStretch(0, 4)  # 输入区域
        self.hBoxLayout.setStretch(1, 3)  # 结果区域
        
        # 绑定事件
        self.uploadButton.clicked.connect(self.uploadImage)
        self.drawButton.clicked.connect(self.showDrawingDialog)
        self.copyTextButton.clicked.connect(self.copyText)
        self.copyLatexButton.clicked.connect(self.copyLatex)
        self.copyImageButton.clicked.connect(self.copyImage)
        self.resultEdit.textChanged.connect(self.onLatexChanged)

    def showResult(self):
        """显示结果区域"""
        if self.resultCard.isHidden():
            self.resultCard.show()
            # 调整左右区域的大小比例为 4:3
            self.hBoxLayout.setStretch(0, 4)
            self.hBoxLayout.setStretch(1, 3)

    def showLoading(self, text="正在识别..."):
        """显示加载状态"""
        if self.stateTooltip:
            self.stateTooltip.setContent(text)
        else:
            self.stateTooltip = StateToolTip(text, '请稍候', self)
            self.stateTooltip.move(self.width() // 2 - self.stateTooltip.width() // 2,
                                 self.height() // 2 - self.stateTooltip.height() // 2)
        self.stateTooltip.show()

    def hideLoading(self):
        """隐藏加载状态"""
        if self.stateTooltip:
            self.stateTooltip.hide()
            self.stateTooltip = None

    def uploadImage(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "./", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.imageLabel.setImage(file_path)
            InfoBar.success(
                title='上传成功',
                content='已成功上传图片',
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            self.recognizeFormula()
            
    def pasteImage(self):
        self.handlePaste()
        
    def recognizeFormula(self, from_drawing=False, drawing_image=None):
        """识别公式"""
        # 显示加载状态
        self.showLoading()
        
        try:
            # 获取图像
            if from_drawing and drawing_image:
                # 从手写板获取图像
                image = drawing_image
                width = image.width()
                height = image.height()
                ptr = image.bits()
                ptr.setsize(height * width * 3)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 3))
                img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            else:
                # 从imageLabel获取图像
                pixmap = self.imageLabel.pixmap()
                if not pixmap:
                    return
                image = pixmap.toImage()
                width = image.width()
                height = image.height()
                ptr = image.bits()
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            
            # 调用识别服务
            result = self.ocr_service.recognize(img)
            
            if result['status']:
                # 保存历史记录
                _, img_encoded = cv2.imencode('.png', img)
                record_id = self.db.add_record(
                    img_encoded.tobytes(),
                    result['latex'],
                    result['confidence'],
                    result['request_id']
                )
                self.current_record_id = record_id
                
                # 更新界面
                self.resultEdit.setText(result['latex'])
                
                # 更新置信度显示
                confidence_value = int(result['confidence'] * 100)
                self.confidenceBar.setValue(confidence_value)
                self.confidenceValueLabel.setText(f"{confidence_value}%")
                
                # 设置置信度颜色
                self.updateConfidenceColor(confidence_value)
                
                # 显示成功信息
                InfoBar.success(
                    title='识别成功',
                    content=f'置信度: {result["confidence"]:.2%}',
                    duration=2000,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                
                # 显示结果区域
                self.showResult()
            else:
                InfoBar.error(
                    title='识别失败',
                    content=result['message'],
                    duration=2000,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                
        except Exception as e:
            print(f"Error details: {str(e)}")
            InfoBar.error(
                title='请求失败',
                content=str(e),
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
        finally:
            self.hideLoading()

    def updateConfidenceColor(self, confidence_value):
        """更新置信度进度条颜色"""
        if confidence_value >= 90:
            color = "#2ecc71"  # 绿色
        elif confidence_value >= 70:
            color = "#f1c40f"  # 黄色
        else:
            color = "#e74c3c"  # 红色
            
        self.confidenceBar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

    def copyText(self):
        """复制纯文本"""
        QApplication.clipboard().setText(self.resultEdit.toPlainText())
        self.showCopySuccess('文本')

    def copyLatex(self):
        """复制带有 $$ 的 LaTeX"""
        latex = f"$${self.resultEdit.toPlainText()}$$"
        QApplication.clipboard().setText(latex)
        self.showCopySuccess('LaTeX')

    def copyImage(self):
        """复制渲染后的公式图像"""
        try:
            # 等待渲染完成
            QTimer.singleShot(500, self._do_copy_image)
        except Exception as e:
            InfoBar.error(
                title='复制失败',
                content=str(e),
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def _do_copy_image(self):
        """实际执行复制图片的操作"""
        try:
            # 获取渲染后的图片
            pixmap = self.latexRenderer.get_image()
            if pixmap:
                # 复制到剪贴板
                QApplication.clipboard().setPixmap(pixmap)
                self.showCopySuccess('图像')
        except Exception as e:
            InfoBar.error(
                title='复制失败',
                content=str(e),
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def showCopySuccess(self, type_str):
        """显示复制成功信息"""
        InfoBar.success(
            title='复制成功',
            content=f'已复制{type_str}到剪贴板',
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=self
        )

    def updateRender(self):
        latex = self.resultEdit.toPlainText()
        self.latexRenderer.render_latex(latex)

    def keyPressEvent(self, event):
        """ 监控键盘事件 """
        # 检测 Ctrl+V
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            self.handlePaste()
        else:
            super().keyPressEvent(event)

    def handlePaste(self):
        """ 处理粘贴事件 """
        clipboard = QApplication.clipboard()
        mimeData = clipboard.mimeData()
        
        if mimeData.hasImage():
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                # 获取设备像素比
                device_ratio = self.devicePixelRatio()
                # 设置图片的设备像素比
                pixmap.setDevicePixelRatio(device_ratio)
                
                # 计算实际显示大小
                display_size = 300 * device_ratio
                scaled_pixmap = pixmap.scaled(
                    display_size, display_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                scaled_pixmap.setDevicePixelRatio(device_ratio)
                self.imageLabel.show()  # 显示图片标签
                self.imageLabel.setPixmap(scaled_pixmap)
                InfoBar.success(
                    title='粘贴成功',
                    content='已成功粘贴图片',
                    duration=2000,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                self.recognizeFormula()
        else:
            InfoBar.warning(
                title='提示',
                content='剪贴板内容不是图片',
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def showImage(self, image_path, label):
        pixmap = QPixmap(image_path)
        # 获取设备像素比
        device_ratio = self.devicePixelRatio()
        # 设置图片的设备像素比
        pixmap.setDevicePixelRatio(device_ratio)
        
        # 计算实际显示大小
        display_size = 300 * device_ratio
        scaled_pixmap = pixmap.scaled(
            display_size, display_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation  # 对于静态图片，使用 SmoothTransformation 效果更好
        )
        scaled_pixmap.setDevicePixelRatio(device_ratio)
        label.setPixmap(scaled_pixmap) 

    def showDrawingDialog(self):
        """显示手写输入对话框"""
        dialog = DrawingDialog(self)
        if dialog.exec_():
            # 如果点击了识别按钮
            image = dialog.getImage()
            # 显示图片（缩放到合适的尺寸）
            pixmap = QPixmap.fromImage(image)
            scaled_pixmap = pixmap.scaled(
                250, 250,  # 增加尺寸到 250x250
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.imageLabel.setFixedSize(250, 250)  # 调整标签大小
            self.imageLabel.setPixmap(scaled_pixmap)
            self.imageLabel.show()
            # 开始识别
            self.recognizeFormula(from_drawing=True, drawing_image=image)
            
    def onLatexChanged(self):
        """处理 LaTeX 文本变化（带防抖）"""
        self.updateTimer.start(500)  # 500ms 后触发更新

    def doUpdateLatex(self):
        """实际执行更新操作"""
        latex = self.resultEdit.toPlainText()
        # 更新渲染
        self.updateRender()
        # 更新数据库
        if hasattr(self, 'current_record_id'):
            print(f"Updating latex for record ID: {self.current_record_id}")  # 打印当前记录ID
            self.db.update_latex(self.current_record_id, latex)
        else:
            print("No current_record_id available")  # 打印没有ID的情况 