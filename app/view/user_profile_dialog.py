from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QColor, QIcon
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QWidget, QListWidget, QListWidgetItem, QGridLayout, QMessageBox, QFileDialog,
    QFrame, QFormLayout, QSizePolicy
)
import os

from qfluentwidgets import (PrimaryPushButton, PushButton, StrongBodyLabel, BodyLabel, 
                           RoundMenu, Action, FluentIcon, MessageBox, LineEdit,
                           TransparentPushButton, TransparentToolButton, ToolButton,
                           InfoBar, InfoBarPosition, PasswordLineEdit, Theme)

from ..common.user_manager import userManager
from ..common.signal_bus import signalBus


class UserAvatarWidget(QWidget):
    """用户头像选择组件"""
    
    avatarChanged = pyqtSignal(str)
    
    def __init__(self, avatar_path, parent=None):
        super().__init__(parent)
        self.avatar_path = avatar_path
        self.avatar_size = 100
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 头像显示
        self.avatarLabel = QLabel()
        self.avatarLabel.setFixedSize(self.avatar_size, self.avatar_size)
        self.avatarLabel.setAlignment(Qt.AlignCenter)
        self.updateAvatar(self.avatar_path)
        
        # 更改头像按钮
        self.changeAvatarButton = QPushButton("更改头像")
        self.changeAvatarButton.clicked.connect(self.onChangeAvatar)
        
        layout.addWidget(self.avatarLabel, alignment=Qt.AlignCenter)
        layout.addWidget(self.changeAvatarButton, alignment=Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
    def updateAvatar(self, path):
        """更新头像显示"""
        self.avatar_path = path
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            # 创建圆形头像
            rounded_avatar = self.createRoundedAvatar(pixmap)
            self.avatarLabel.setPixmap(rounded_avatar)
        else:
            # 创建一个带提示文字的圆形占位头像
            self.createPlaceholderAvatar()
            
    def createRoundedAvatar(self, pixmap):
        """创建圆形头像"""
        # 确保图像为正方形，并缩放到所需大小
        if pixmap.width() != pixmap.height():
            # 如果不是正方形，取最小边作为大小
            size = min(pixmap.width(), pixmap.height())
            # 从中心裁剪为正方形
            x = (pixmap.width() - size) // 2
            y = (pixmap.height() - size) // 2
            pixmap = pixmap.copy(x, y, size, size)
        
        # 缩放到指定大小
        pixmap = pixmap.scaled(
            self.avatar_size, self.avatar_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # 创建空白目标图像
        result = QPixmap(self.avatar_size, self.avatar_size)
        result.fill(Qt.transparent)  # 透明背景
        
        # 创建绘制器
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing, True)  # 抗锈齿
        
        # 创建圆形路径
        path = QPainterPath()
        path.addEllipse(0, 0, self.avatar_size, self.avatar_size)
        
        # 设置裁剪路径并绘制图像
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        return result
        
    def createPlaceholderAvatar(self):
        """创建占位头像在头像加载失败时显示"""
        # 创建空白图像
        result = QPixmap(self.avatar_size, self.avatar_size)
        result.fill(Qt.transparent)  # 透明背景
        
        # 创建绘制器
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing, True)  # 抗锈齿
        
        # 绘制圆形
        painter.setPen(Qt.gray)
        painter.setBrush(Qt.lightGray)
        painter.drawEllipse(0, 0, self.avatar_size, self.avatar_size)
        
        # 添加文字提示
        painter.setPen(Qt.black)
        painter.setFont(self.font())
        painter.drawText(0, 0, self.avatar_size, self.avatar_size, Qt.AlignCenter, "请设置\n头像")
        painter.end()
        
        self.avatarLabel.setPixmap(result)
        
    def onChangeAvatar(self):
        """更改头像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            # 将选择的图片复制到应用的图片目录
            import os
            import shutil
            from datetime import datetime
            
            # 确保目标目录存在
            target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'images')
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            # 生成唯一文件名
            file_ext = os.path.splitext(file_path)[1]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"avatar_{timestamp}{file_ext}"
            target_path = os.path.join(target_dir, new_filename)
            
            # 复制文件
            try:
                shutil.copy2(file_path, target_path)
                # 更新头像路径（使用相对路径）
                relative_path = os.path.join('images', new_filename)
                self.updateAvatar(relative_path)
                self.avatarChanged.emit(relative_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"更改头像失败: {str(e)}")


class UserListWidget(QListWidget):
    """用户列表组件"""
    
    userSelected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置字体大小
        font = self.font()
        font.setPointSize(9)
        self.setFont(font)
        
        # 初始化UI
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setFocusPolicy(Qt.StrongFocus)  # 强制焦点显示选择框
        self.setIconSize(QSize(40, 40))  # 设置更大的图标尺寸
        self.setSpacing(4)  # 增加项目间距以补偿移除的margin
        
        # 设置样式
        self.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 5px;
            }
            QListWidget::item {
                background-color: transparent;
                margin: 2px 0px;
                padding: 0px;
                border: none;
                border-radius: 0px;
                min-height: 45px;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)
        
        # 连接信号
        self.currentItemChanged.connect(self.onCurrentItemChanged)
        
    def updateUserList(self):
        """更新用户列表"""
        self.clear()
        
        try:
            # 获取用户数据
            users = userManager.get_all_users()
            current_user = userManager.get_current_user()
            
            # 如果没有用户数据，添加提示项
            if not users:
                item = QListWidgetItem("无用户数据")
                item.setTextAlignment(Qt.AlignCenter)
                self.addItem(item)
                return
            
            # 处理用户数据
            for index, user in enumerate(users):
                try:
                    # 验证用户数据完整性
                    if not isinstance(user, dict):
                        continue
                        
                    user_id = user.get('id')
                    user_name = user.get('name', '未命名用户')
                    
                    if not user_id:
                        continue
                    
                    # 创建列表项
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, user_id)
                    item.setSizeHint(QSize(0, 45))  # 适应简化布局的高度
                    
                    # 创建自定义小部件
                    user_item_widget = self.createUserItemWidget(user, current_user)
                    
                    if user_item_widget is None:
                        continue
                    
                    # 添加到列表
                    self.addItem(item)
                    self.setItemWidget(item, user_item_widget)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            # 添加错误提示项
            error_item = QListWidgetItem(f"加载用户列表失败: {str(e)}")
            error_item.setTextAlignment(Qt.AlignCenter)
            self.addItem(error_item)
            
    def createUserItemWidget(self, user, current_user):
        """创建仅显示用户名的列表项小部件"""
        try:
            # 验证输入参数
            if not isinstance(user, dict):
                return None
                
            # 创建主容器小部件
            widget = QWidget()
            widget.setFixedHeight(40)
            
            # 检查是否为当前用户
            is_current = (current_user and user.get('id') == current_user.get('id'))
            
            # 设置小部件样式
            if is_current:
                widget.setStyleSheet("""
                    QWidget { 
                        background-color: #e3f2fd; 
                        border: 2px solid #2196f3; 
                        border-radius: 8px; 
                        margin: 0px;
                    }
                    QWidget:hover {
                        background-color: #bbdefb;
                        border-color: #1976d2;
                    }
                """)
            else:
                widget.setStyleSheet("""
                    QWidget { 
                        background-color: #ffffff; 
                        border: 2px solid transparent; 
                        border-radius: 8px; 
                        margin: 0px;
                    }
                    QWidget:hover {
                        background-color: #f5f5f5;
                        border-color: #2196f3;
                    }
                """)
            
            # 创建水平布局
            main_layout = QHBoxLayout(widget)
            main_layout.setContentsMargins(15, 8, 15, 8)
            main_layout.setSpacing(10)
            main_layout.setAlignment(Qt.AlignVCenter)
            
            # 用户名标签
            username = user.get('name', '未命名用户')
            name_label = QLabel(username)
            name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            name_label.setWordWrap(False)
            
            # 设置字体和样式
            font = name_label.font()
            font.setPointSize(14)
            if is_current:
                font.setBold(True)
                name_label.setStyleSheet("""
                    QLabel {
                        color: #1976d2; 
                        font-weight: bold; 
                        background-color: transparent;
                        padding: 0px;
                        border: none;
                    }
                """)
            else:
                font.setBold(False)
                name_label.setStyleSheet("""
                    QLabel {
                        color: #333333; 
                        background-color: transparent;
                        padding: 0px;
                        border: none;
                    }
                """)
            name_label.setFont(font)
            
            # 添加用户名到布局
            main_layout.addWidget(name_label, 1)
            
            # 为当前用户添加右侧指示器
            if is_current:
                current_indicator = QLabel("当前")
                current_indicator.setStyleSheet("""
                    QLabel {
                        color: #1976d2; 
                        font-weight: bold; 
                        font-size: 12px; 
                        background-color: #ffffff; 
                        padding: 4px 8px; 
                        border-radius: 4px;
                        border: 1px solid #2196f3;
                    }
                """)
                current_indicator.setAlignment(Qt.AlignCenter)
                current_indicator.setFixedSize(50, 25)
                main_layout.addWidget(current_indicator, 0)
                
            return widget
            
        except Exception as e:
            # 创建一个简单的错误提示项
            error_widget = QWidget()
            error_layout = QHBoxLayout(error_widget)
            error_label = QLabel(f"加载用户失败: {user.get('name', 'Unknown')}")
            error_label.setStyleSheet("color: red; padding: 10px;")
            error_layout.addWidget(error_label)
            return error_widget
        
    def setDefaultAvatar(self, label, name):
        """设置默认头像"""
        label.setText(name[0].upper() if name else "?")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "background-color: #e0e0e0; border-radius: 20px; "
            "color: #333333; font-weight: bold; font-size: 16px;"
        )
        
    
            
    def onCurrentItemChanged(self, current, previous):
        """当前选择的用户变更"""
        if current:
            user_id = current.data(Qt.UserRole)
            self.userSelected.emit(user_id)


class UserProfileDialog(QDialog):
    """用户资料对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户资料")
        self.resize(600, 400)
        
        self.current_user = userManager.get_current_user()
        self.selected_user_id = self.current_user['id'] if self.current_user else None
        
        self.initUI()
        self.loadUserData()  # 确保加载用户数据
        
    def initUI(self):
        """初始化UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除布局的边距
        main_layout.setSpacing(0)  # 减少左右两侧的间距
        
        # 创建左侧容器
        left_widget = QWidget()
        left_widget.setFixedWidth(220)  # 设置左侧宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 15, 10, 15)  # 可以调整内边距
        
        # 创建一个带背景的面板来容纳所有元素
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(5, 8, 5, 15)  # 减少左右边距，使内容更靠近边框
        left_layout.addWidget(panel)
        
        # 添加标题标签，确保没有边框
        title_label = QLabel("账户列表")
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title_label.setStyleSheet("margin: 0; padding: 0; background: transparent; border: none;")
        panel_layout.addWidget(title_label)
        
        # 添加提示标签，确保没有边框并缩短与标题的距离
        tip_label = QLabel("选择账户")
        tip_label.setStyleSheet("color: #666666; font-size: 11px; background: transparent; margin: 0; padding: 2px; border: none;")
        tip_label.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(tip_label)
        
        # 创建用户列表
        self.userList = UserListWidget(self)
        # 不在此处设置样式，以避免覆盖UserListWidget类中的样式设置
        self.userList.userSelected.connect(self.onUserSelected)  # 重新连接用户选择信号
        panel_layout.addWidget(self.userList)
        
        # 创建右侧内容区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # 用户信息标题
        self.titleLabel = StrongBodyLabel("用户信息")
        
        # 用户头像
        self.avatarWidget = UserAvatarWidget(self.current_user['avatar'] if self.current_user else "")
        self.avatarWidget.avatarChanged.connect(self.onAvatarChanged)
        
        # 用户名编辑
        name_layout = QHBoxLayout()
        name_label = BodyLabel("用户名:")
        name_label.setFixedWidth(60)  # 固定标签宽度
        name_layout.addWidget(name_label)
        name_layout.addSpacing(5)  # 在标签和输入框之间添加小间距
        
        self.nameEdit = LineEdit()
        self.nameEdit.setPlaceholderText("请输入用户名")
        self.nameEdit.setFixedWidth(250)
        name_layout.addWidget(self.nameEdit)
        name_layout.setContentsMargins(0, 10, 0, 10)
        name_layout.addStretch(1)  # 添加弹性空间使输入框靠左对齐
        
        # 按钮区域 - 使用单列网格布局
        button_area = QVBoxLayout()
        button_area.setContentsMargins(20, 0, 20, 0)  # 左右留出更多空间使按钮不至于邪宽
        button_area.setSpacing(12)  # 行间距
        
        # 保存按钮 - 主要操作用主色按钮
        self.saveButton = PrimaryPushButton("保存")
        self.saveButton.setFixedHeight(36)
        self.saveButton.clicked.connect(self.onSave)
        button_area.addWidget(self.saveButton)
        
        # 切换用户按钮 - 次要操作用普通按钮
        self.switchButton = PushButton("切换到此用户")
        self.switchButton.setIcon(FluentIcon.LINK)
        self.switchButton.setFixedHeight(36)
        self.switchButton.clicked.connect(self.onSwitchUser)
        button_area.addWidget(self.switchButton)
        
        # 增加分隔行
        button_area.addSpacing(6)
        
        # 新建用户按钮 - 使用PushButton
        self.newUserButton = PushButton("新建用户")
        self.newUserButton.setIcon(FluentIcon.ADD)
        self.newUserButton.setFixedHeight(36)
        self.newUserButton.clicked.connect(self.onNewUser)
        button_area.addWidget(self.newUserButton)
        
        # 删除用户按钮 - 与新建用户按钮保持一致的样式
        self.deleteUserButton = PushButton("删除用户")
        self.deleteUserButton.setIcon(FluentIcon.DELETE)
        self.deleteUserButton.setFixedHeight(36)
        self.deleteUserButton.clicked.connect(self.onDeleteUser)
        
        button_area.addWidget(self.deleteUserButton)
        
        # 添加组件到右侧布局
        right_layout.addWidget(self.titleLabel)
        right_layout.addSpacing(5)
        right_layout.addWidget(self.avatarWidget, alignment=Qt.AlignCenter)
        right_layout.addSpacing(15)  # 头像和用户名之间的间距
        right_layout.addLayout(name_layout)
        right_layout.addSpacing(25)  # 用户名和按钮之间的间距增加
        right_layout.addLayout(button_area)
        right_layout.addStretch()  # 在底部添加弹性空间
        
        # 添加左右两侧到主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        main_layout.setStretchFactor(left_widget, 0)  # 不将宽度分配给左侧
        main_layout.setStretchFactor(right_widget, 1)  # 将剩余空间分配给右侧
        
        # 初始化完UI后更新用户列表
        self.userList.updateUserList()
        
    def loadUserData(self):
        """加载用户数据"""
        if not self.selected_user_id:
            return
            
        # 查找选中的用户
        users = userManager.get_all_users()
        selected_user = None
        
        for user in users:
            if user['id'] == self.selected_user_id:
                selected_user = user
                break
                
        if selected_user:
            self.nameEdit.setText(selected_user['name'])
            self.avatarWidget.updateAvatar(selected_user['avatar'])
            
            # 更新按钮状态
            is_current_user = (self.current_user and self.selected_user_id == self.current_user['id'])
            self.switchButton.setEnabled(not is_current_user)
            self.deleteUserButton.setEnabled(not is_current_user and len(users) > 1)
            
    def onUserSelected(self, user_id):
        """用户选择变更"""
        self.selected_user_id = user_id
        self.loadUserData()
        
    def onAvatarChanged(self, avatar_path):
        """头像变更"""
        self.new_avatar_path = avatar_path
        
    def onSave(self):
        """保存用户信息"""
        if not self.selected_user_id:
            return
            
        name = self.nameEdit.text().strip()
        if not name:
            InfoBar.error(
                title="错误",
                content="用户名不能为空",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return
            
        # 如果是当前用户，直接更新
        if self.selected_user_id == self.current_user['id']:
            avatar_path = getattr(self, 'new_avatar_path', None)
            userManager.update_current_user(name=name, avatar=avatar_path)
            InfoBar.success(
                title="成功",
                content="用户信息已更新",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        else:
            # 如果是其他用户，需要先切换到该用户再更新
            userManager.set_current_user(self.selected_user_id)
            avatar_path = getattr(self, 'new_avatar_path', None)
            userManager.update_current_user(name=name, avatar=avatar_path)
            userManager.set_current_user(self.current_user['id'])  # 切回原用户
            InfoBar.success(
                title="成功",
                content="用户信息已更新",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            
        # 更新用户列表
        self.userList.updateUserList()
        
    def onSwitchUser(self):
        """切换用户"""
        if not self.selected_user_id or self.selected_user_id == self.current_user['id']:
            return
            
        # 创建密码验证对话框
        verify_dialog = QDialog(self)
        verify_dialog.setWindowTitle("验证密码")
        verify_dialog.resize(300, 120)
        
        layout = QVBoxLayout(verify_dialog)
        
        # 用户名信息
        selected_user = None
        for user in userManager.get_all_users():
            if user['id'] == self.selected_user_id:
                selected_user = user
                break
                
        if selected_user:
            user_info = BodyLabel(f"切换到用户: {selected_user['name']}")
            layout.addWidget(user_info)
        
        # 密码输入框
        password_layout = QHBoxLayout()
        password_layout.addWidget(BodyLabel("密码:"))
        password_edit = PasswordLineEdit()
        password_edit.setPlaceholderText("请输入密码")
        password_layout.addWidget(password_edit)
        layout.addLayout(password_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        ok_button = PrimaryPushButton("确认")
        cancel_button = QPushButton("取消")
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        cancel_button.clicked.connect(verify_dialog.reject)
        ok_button.clicked.connect(lambda: self.verifyPasswordAndSwitch(verify_dialog, password_edit.text()))
        
        # 执行对话框
        verify_dialog.exec_()
    
    def verifyPasswordAndSwitch(self, dialog, password):
        """验证密码并切换用户"""
        # 验证密码
        if userManager.verify_password(self.selected_user_id, password):
            # 密码正确，切换用户
            if userManager.set_current_user(self.selected_user_id):
                # 更新UI
                self.current_user = userManager.get_current_user()
                self.userList.updateUserList()
                InfoBar.success(
                    title="成功",
                    content="已切换用户",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )
                dialog.accept()
        else:
            # 密码错误
            InfoBar.error(
                title="错误",
                content="密码不正确",
                parent=dialog,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            
            # 关闭对话框
            self.accept()
            
    def onNewUser(self):
        """新建用户"""
        # 创建新用户对话框
        new_user_dialog = QDialog(self)
        new_user_dialog.setWindowTitle("新建用户")
        new_user_dialog.resize(300, 180)
        
        layout = QFormLayout(new_user_dialog)
        
        # 用户名输入框
        name_edit = LineEdit()
        name_edit.setPlaceholderText("请输入用户名")
        layout.addRow(BodyLabel("用户名:"), name_edit)
        
        # 密码输入框
        password_edit = PasswordLineEdit()
        password_edit.setPlaceholderText("请设置密码")
        layout.addRow(BodyLabel("密码:"), password_edit)
        
        # 确认密码输入框
        confirm_password_edit = PasswordLineEdit()
        confirm_password_edit.setPlaceholderText("请再次输入密码")
        layout.addRow(BodyLabel("确认密码:"), confirm_password_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        ok_button = PrimaryPushButton("创建")
        cancel_button = QPushButton("取消")
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow("", button_layout)
        
        # 连接信号
        cancel_button.clicked.connect(new_user_dialog.reject)
        ok_button.clicked.connect(lambda: self.createNewUser(new_user_dialog, name_edit.text(), password_edit.text(), confirm_password_edit.text()))
        
        # 执行对话框
        new_user_dialog.exec_()
        
    def createNewUser(self, dialog, name, password, confirm_password):
        """创建新用户"""
        # 验证输入
        if not name.strip():
            InfoBar.error(
                title="错误",
                content="用户名不能为空",
                parent=dialog,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return
            
        if not password:
            InfoBar.error(
                title="错误",
                content="密码不能为空",
                parent=dialog,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return
            
        if password != confirm_password:
            InfoBar.error(
                title="错误",
                content="两次输入的密码不一致",
                parent=dialog,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return
        
        # 创建新用户
        new_user = userManager.add_user(name, 'images/default_avatar.png', password)
        if new_user:
            # 更新用户列表
            self.userList.updateUserList()
            # 选中新用户
            self.onUserSelected(new_user['id'])
            # 关闭对话框
            dialog.accept()
            
            # 显示创建成功提示
            InfoBar.success(
                title="成功",
                content="已创建新用户",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            
    def onDeleteUser(self):
        """删除用户"""
        if not self.selected_user_id or self.selected_user_id == self.current_user['id']:
            return
            
        # 确认对话框
        w = MessageBox(
            "删除用户",
            "确定要删除选中的用户吗？此操作不可恢复！",
            self
        )
        w.yesButton.setText("确定")
        w.cancelButton.setText("取消")
        
        if w.exec():
            if userManager.delete_user(self.selected_user_id):
                # 更新用户列表
                self.userList.updateUserList()
                
                # 选中第一个用户
                if self.userList.count() > 0:
                    self.userList.setCurrentRow(0)
                    
                InfoBar.success(
                    title="成功",
                    content="已删除用户",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )
            else:
                InfoBar.error(
                    title="错误",
                    content="删除用户失败",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )
