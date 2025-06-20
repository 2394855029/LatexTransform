from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QTableWidgetItem, QHeaderView,
                           QApplication, QScrollArea)
from qfluentwidgets import (SearchLineEdit, PrimaryPushButton, TableWidget, 
                          ComboBox, ToolButton, FluentIcon, InfoBar,
                          InfoBarPosition, MessageBox, PrimaryToolButton,
                          PushButton)
from qfluentwidgets import FluentIcon as FIF
import base64
from datetime import datetime  # 添加到文件顶部的导入部分

from ..common.db_manager import DatabaseManager
from ..common.user_manager import userManager
from ..common.signal_bus import signalBus

class ClickableLabel(QLabel):
    """可点击的标签"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 获取图片并复制到剪贴板
            if self.pixmap():
                QApplication.clipboard().setPixmap(self.pixmap())
                self.showCopySuccess()
                
    def showCopySuccess(self):
        InfoBar.success(
            title='复制成功',
            content='已复制图片到剪贴板',
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=self.window()
        )

class ClickableItem(QTableWidgetItem):
    """可点击的表格项"""
    def __init__(self, text='', is_latex=False):
        super().__init__(text)
        self.is_latex = is_latex
        
    def copyToClipboard(self):
        text = self.text()
        if self.is_latex:
            # LaTeX结果需要加上 $$
            text = f"$${text}$$"
        QApplication.clipboard().setText(text)
        
        InfoBar.success(
            title='复制成功',
            content=f'已复制{"LaTeX" if self.is_latex else "文本"}到剪贴板',
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=self.tableWidget().window()
        )

class HistoryInterface(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('historyInterface')
        # 添加样式
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QWidget#historyInterface {
                background-color: transparent;
            }
            
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        self.db = DatabaseManager()
        self.current_page = 1
        self.page_size = 15
        self.total_count = 0
        self.search_text = None
        
        # 获取当前用户ID
        self.current_user_id = None
        current_user = userManager.get_current_user()
        if current_user:
            self.current_user_id = current_user['id']
        
        # 创建一个容器 widget
        self.scrollWidget = QWidget(self)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        # 连接用户切换信号
        signalBus.userChanged.connect(self.onUserChanged)
        
        self.initUI()
        self.loadHistory()

    def initUI(self):
        # 主布局
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)  # 应用到 scrollWidget
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        
        # 顶部工具栏
        self.topLayout = QHBoxLayout()
        
        # 搜索框
        self.searchBox = SearchLineEdit(self)
        self.searchBox.setPlaceholderText('搜索LaTeX结果')
        self.searchBox.textChanged.connect(self.onSearch)
        
        # 清空历史按钮
        self.clearButton = PrimaryPushButton('清空历史', self, FIF.DELETE)
        self.clearButton.clicked.connect(self.clearHistory)
        
        self.topLayout.addWidget(self.searchBox)
        self.topLayout.addWidget(self.clearButton)
        
        # 表格
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        # 调整列的顺序：ID, 图片, LaTeX结果, 置信度, 时间, 操作
        self.table.setHorizontalHeaderLabels(['ID', '图片', 'LaTeX结果', '置信度', '时间', '操作'])
        
        # 设置表格列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # ID列固定宽度
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 图片列固定宽度
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # LaTeX结果列自适应
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # 置信度列固定宽度
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 时间列固定宽度
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 操作列固定宽度
        
        # 设置固定列的宽度
        self.table.setColumnWidth(0, 80)   # ID
        self.table.setColumnWidth(1, 100)  # 图片
        self.table.setColumnWidth(3, 80)   # 置信度
        self.table.setColumnWidth(4, 160)  # 时间 - 减小宽度
        self.table.setColumnWidth(5, 60)   # 操作
        
        # 表格点击事件
        self.table.cellClicked.connect(self.onCellClicked)
        
        # 分页控件布局
        self.paginationLayout = QHBoxLayout()
        self.paginationLayout.setContentsMargins(16, 8, 16, 8)
        self.paginationLayout.setSpacing(8)
        
        self.totalLabel = QLabel(self)
        self.prevButton = PushButton('上一页', self)
        self.pageLabel = QLabel(self)
        self.nextButton = PushButton('下一页', self)
        
        self.paginationLayout.addWidget(self.totalLabel)
        self.paginationLayout.addStretch()
        self.paginationLayout.addWidget(self.prevButton)
        self.paginationLayout.addWidget(self.pageLabel)
        self.paginationLayout.addWidget(self.nextButton)
        
        # 绑定事件
        self.prevButton.clicked.connect(self.prevPage)
        self.nextButton.clicked.connect(self.nextPage)
        self.searchBox.textChanged.connect(self.onSearch)
        
        # 添加到主布局
        self.vBoxLayout.addLayout(self.topLayout)
        self.vBoxLayout.addWidget(self.table)
        self.vBoxLayout.addLayout(self.paginationLayout)
        
    def loadHistory(self, search_text=None, user_id=None):
        """加载历史记录"""
        self.search_text = search_text
        # 如果没有指定用户ID，使用当前用户ID
        if user_id is None:
            user_id = self.current_user_id
        
        # 获取记录数据
        records, total_count = self.db.get_history_records(
            page=self.current_page,
            page_size=self.page_size,
            search_text=search_text,
            user_id=user_id
        )
        self.total_count = total_count
        
        # 更新分页信息
        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        if self.current_page > total_pages:
            self.current_page = total_pages
            return self.loadHistory(search_text, user_id)
            
        self.totalLabel.setText(f"共 {total_count} 条记录")
        self.pageLabel.setText(f"第 {self.current_page} / {total_pages} 页")
        
        # 更新按钮状态
        self.prevButton.setEnabled(self.current_page > 1)
        self.nextButton.setEnabled(self.current_page < total_pages)
        
        # 清空表格内容
        self.table.setRowCount(0)
        
        # 如果没有记录，显示提示
        if not records:
            self.showEmptyHint()
            return
            
        # 添加新记录到表格
        for record in records:
            record_id, timestamp, image_data, latex_result, confidence, request_id = record
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(record_id)))
            
            # 图片
            image_label = ClickableLabel(self)
            image_data = base64.b64decode(image_data)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            self.table.setCellWidget(row, 1, image_label)
            
            # LaTeX结果
            self.table.setItem(row, 2, ClickableItem(latex_result, True))
            
            # 置信度
            self.table.setItem(row, 3, QTableWidgetItem(f"{confidence:.1%}"))
            
            # 时间 - 格式化显示
            try:
                # 将字符串转换为datetime对象
                dt = datetime.strptime(str(timestamp), '%Y-%m-%d %H:%M:%S.%f')
                # 格式化为更简洁的形式
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 4, QTableWidgetItem(formatted_time))
            except:
                # 如果转换失败，就使用原始时间戳
                self.table.setItem(row, 4, QTableWidgetItem(str(timestamp)))
            
            # 删除按钮 - 使用 PrimaryToolButton
            deleteButton = PrimaryToolButton(FIF.DELETE, self)
            deleteButton.setToolTip('删除')  # 添加工具提示
            deleteButton.clicked.connect(lambda checked, rid=record_id: self.confirmDelete(rid))
            # 创建一个容器来居中按钮
            buttonContainer = QWidget()
            buttonLayout = QHBoxLayout(buttonContainer)
            buttonLayout.setContentsMargins(0, 0, 0, 0)
            buttonLayout.addWidget(deleteButton, 0, Qt.AlignCenter)
            self.table.setCellWidget(row, 5, buttonContainer)

    def showEmptyHint(self):
        """显示空记录提示"""
        self.table.setRowCount(1)
        empty_label = QLabel('暂无历史记录' if not self.search_text else '未找到匹配的记录')
        empty_label.setStyleSheet('color: #666666; font-size: 14px;')
        empty_label.setAlignment(Qt.AlignCenter)
        self.table.setCellWidget(0, 0, empty_label)
        self.table.setSpan(0, 0, 1, 6)  # 合并单元格

    def prevPage(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.loadHistory(self.search_text, self.current_user_id)

    def nextPage(self):
        """下一页"""
        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self.loadHistory(self.search_text, self.current_user_id)

    def onSearchTextChanged(self):
        """搜索文本变化处理"""
        self.current_page = 1  # 重置到第一页
        text = self.searchEdit.text().strip()
        self.loadHistory(text if text else None, self.current_user_id)

    def onRecordDeleted(self):
        """记录删除后的处理"""
        self.loadHistory(self.search_text, self.current_user_id)

    def onCellClicked(self, row, column):
        """处理单元格点击事件"""
        item = self.table.item(row, column)
        if isinstance(item, ClickableItem):
            item.copyToClipboard()
        
    def onSearch(self, text):
        """搜索"""
        self.search_text = text if text else None
        self.current_page = 1
        self.loadData()
        
    def changePage(self, action):
        """换页"""
        if action == 'first':
            self.current_page = 1
        elif action == 'prev':
            self.current_page = max(1, self.current_page - 1)
        elif action == 'next':
            self.current_page = min(self.total_pages, self.current_page + 1)
        elif action == 'last':
            self.current_page = self.total_pages
        
        self.loadData()
        
    def onPageSelected(self, text):
        """选择页码"""
        page = int(text.split('/')[0])
        if page != self.current_page:
            self.current_page = page
            self.loadData()
            
    def deleteRecord(self, record_id):
        """删除记录"""
        self.db.delete_record(record_id)
        self.loadData()
        InfoBar.success(
            title='删除成功',
            content='已删除该记录',
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=self
        )
        
    def confirmDelete(self, record_id):
        """删除确认"""
        w = MessageBox(
            '删除确认',
            '确定要删除这条记录吗？',
            self
        )
        if w.exec():
            self.deleteRecord(record_id)
        
    def clearHistory(self):
        """清空历史"""
        w = MessageBox(
            '清空确认',
            '确定要清空当前用户的所有历史记录吗？\n此操作不可恢复！',
            self
        )
        if w.exec_():
            self.db.clear_history(user_id=self.current_user_id)
            self.current_page = 1
            self.loadData()
            InfoBar.success(
                title='清空成功',
                content='已清空当前用户的所有历史记录',
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
        
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 每次显示时重新加载数据
        self.loadData() 

    def loadData(self):
        """加载数据（用于刷新）"""
        self.loadHistory(self.search_text, self.current_user_id)
        
    def onUserChanged(self, user):
        """用户切换事件处理"""
        # 更新当前用户ID
        self.current_user_id = user['id'] if user else 'default'
        # 重置页码
        self.current_page = 1
        # 重新加载数据
        self.loadData()
        print(f"历史记录已切换到用户: {user['name'] if user else 'default'}")