# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QUrl, QSize, QTimer, QRect
from PyQt5.QtGui import QIcon, QDesktopServices, QColor, QPainter, QImage, QBrush, QColor, QFont, QDesktopServices, QPainterPath, QPixmap
from PyQt5.QtWidgets import QApplication

from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, SystemThemeListener, isDarkTheme, NavigationWidget)
from qfluentwidgets import FluentIcon as FIF

from .gallery_interface import GalleryInterface
from .home_interface import HomeInterface
from .basic_input_interface import BasicInputInterface
from .date_time_interface import DateTimeInterface
from .dialog_interface import DialogInterface
from .layout_interface import LayoutInterface
from .icon_interface import IconInterface
from .material_interface import MaterialInterface
from .menu_interface import MenuInterface
from .navigation_view_interface import NavigationViewInterface
from .scroll_interface import ScrollInterface
from .status_info_interface import StatusInfoInterface
from .setting_interface import SettingInterface
from .text_interface import TextInterface
from .view_interface import ViewInterface
from .latex_ocr_interface import LatexOcrInterface
from .history_interface import HistoryInterface
from ..common.config import ZH_SUPPORT_URL, EN_SUPPORT_URL, cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common.translator import Translator
from ..common import resource


class AvatarWidget(NavigationWidget):
    """ Avatar widget """

    def __init__(self, parent=None):
        super().__init__(isSelectable=False, parent=parent)
        # 使用与窗口图标相同的处理方式，但尺寸为24x24
        self.avatar_size = 24
        
        # 从UserManager加载当前用户信息
        from ..common.user_manager import userManager
        self.userManager = userManager
        user = self.userManager.get_current_user()
        
        # 使用MainWindow的静态方法创建圆形头像
        self.avatar = MainWindow.create_rounded_image(user['avatar'], self.avatar_size)
        self.username = user['name']
        
        # 监听用户变更信号
        from ..common.signal_bus import signalBus
        signalBus.userChanged.connect(self.onUserChanged)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.SmoothPixmapTransform | QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)

        if self.isPressed:
            painter.setOpacity(0.7)

        # draw background
        if self.isEnter:
            c = 255 if isDarkTheme() else 0
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        # draw avatar - 直接绘制已经处理好的圆形头像
        painter.translate(8, 6)
        painter.drawImage(0, 0, self.avatar)
        painter.translate(-8, -6)

        if not self.isCompacted:
            painter.setPen(Qt.white if isDarkTheme() else Qt.black)
            font = QFont('Segoe UI')
            font.setPixelSize(14)
            painter.setFont(font)
            painter.drawText(QRect(44, 0, 255, 36), Qt.AlignVCenter, self.username)
            
    def onUserChanged(self, user):
        """用户信息变更处理"""
        # 更新头像
        self.avatar = MainWindow.create_rounded_image(user['avatar'], self.avatar_size)
        self.username = user['name']
        self.update()  # 触发重绘


class MainWindow(FluentWindow):

    @staticmethod
    def create_rounded_image(img_path, size):
        """创建圆形图像，确保图像居中显示"""
        # 加载原始图像
        original = QImage(img_path)
        
        # 计算居中裁剪的起始点
        # 先将图像缩放为正方形，保持宽高比
        if original.width() > original.height():
            # 宽图像，以高度为基准
            scaled = original.scaledToHeight(size, Qt.SmoothTransformation)
            # 计算水平居中的起始点
            x_offset = (scaled.width() - size) // 2
            y_offset = 0
        else:
            # 高图像，以宽度为基准
            scaled = original.scaledToWidth(size, Qt.SmoothTransformation)
            # 计算垂直居中的起始点
            x_offset = 0
            y_offset = (scaled.height() - size) // 2
        
        # 创建一个正方形图像，裁剪居中部分
        square = QImage(size, size, QImage.Format_ARGB32)
        square.fill(Qt.transparent)
        
        # 绘制居中裁剪的图像
        painter = QPainter(square)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(0, 0, scaled, x_offset, y_offset, size, size)
        painter.end()
        
        # 创建圆形蒙版
        rounded = QImage(size, size, QImage.Format_ARGB32)
        rounded.fill(Qt.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawImage(0, 0, square)
        painter.end()
        
        return rounded
        
    def get_rounded_icon(self, img_path, size=64):
        """将图片裁剪为圆形并返回QIcon"""
        rounded = self.create_rounded_image(img_path, size)
        return QIcon(QPixmap.fromImage(rounded))

    def __init__(self):
        super().__init__()
        
        # 加载用户管理器
        from ..common.user_manager import userManager
        self.userManager = userManager
        
        self.initWindow()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # create sub interface
        self.homeInterface = HomeInterface(self)
        self.iconInterface = IconInterface(self)
        self.basicInputInterface = BasicInputInterface(self)
        self.dateTimeInterface = DateTimeInterface(self)
        self.dialogInterface = DialogInterface(self)
        self.layoutInterface = LayoutInterface(self)
        self.menuInterface = MenuInterface(self)
        self.materialInterface = MaterialInterface(self)
        self.navigationViewInterface = NavigationViewInterface(self)
        self.scrollInterface = ScrollInterface(self)
        self.statusInfoInterface = StatusInfoInterface(self)
        self.settingInterface = SettingInterface(self)
        self.textInterface = TextInterface(self)
        self.viewInterface = ViewInterface(self)
        # self.objectDetectionInterface = ObjectDetectionInterface(self)
        self.latexOcrInterface = LatexOcrInterface(self)
        self.historyInterface = HistoryInterface(self)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        self.connectSignalToSlot()

        # add items to navigation interface
        self.initNavigation()
        
        # start theme listener
        self.themeListener.start()

    def connectSignalToSlot(self):
        from ..common.signal_bus import signalBus
        
        # 主题监听信号
        self.themeListener.systemThemeChanged.connect(self._onThemeChangedFinished)
        
        # 信号总线信号
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.switchToSampleCard.connect(self.switchToSample)
        signalBus.supportSignal.connect(self.onSupport)
        
        # 监听用户变更信号
        signalBus.userChanged.connect(self.onUserChanged)

    def initNavigation(self):
        # add navigation items
        t = Translator()
        # self.addSubInterface(self.homeInterface, FIF.HOME, self.tr('Home'))
        # self.addSubInterface(self.iconInterface, Icon.EMOJI_TAB_SYMBOLS, t.icons)
        # self.navigationInterface.addSeparator()

        pos = NavigationItemPosition.SCROLL
        # self.addSubInterface(self.basicInputInterface, FIF.CHECKBOX,t.basicInput, pos)
        # self.addSubInterface(self.dateTimeInterface, FIF.DATE_TIME, t.dateTime, pos)
        # self.addSubInterface(self.dialogInterface, FIF.MESSAGE, t.dialogs, pos)
        # self.addSubInterface(self.layoutInterface, FIF.LAYOUT, t.layout, pos)
        # self.addSubInterface(self.materialInterface, FIF.PALETTE, t.material, pos)
        # self.addSubInterface(self.menuInterface, Icon.MENU, t.menus, pos)
        # self.addSubInterface(self.navigationViewInterface, FIF.MENU, t.navigation, pos)
        # self.addSubInterface(self.scrollInterface, FIF.SCROLL, t.scroll, pos)
        # self.addSubInterface(self.statusInfoInterface, FIF.CHAT, t.statusInfo, pos)
        # self.addSubInterface(self.textInterface, Icon.TEXT, t.text, pos)
        # self.addSubInterface(self.viewInterface, Icon.GRID, t.view, pos)

        self.addSubInterface(self.latexOcrInterface, FIF.ZOOM, '公式识别', pos)
        self.addSubInterface(self.historyInterface, FIF.SAVE_AS, '历史记录', pos)

        # # add custom widget to bottom
        # self.navigationInterface.addItem(
        #     routeKey='price',
        #     icon=Icon.PRICE,
        #     text=t.price,
        #     onClick=self.onSupport,
        #     selectable=False,
        #     tooltip=t.price,
        #     position=NavigationItemPosition.BOTTOM
        # )

        self.navigationInterface.addWidget(
            routeKey='price',
            widget=AvatarWidget(),
            onClick=self.showUserProfileDialog,
            position=NavigationItemPosition.BOTTOM
        )
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1030, 800)
        self.setMinimumWidth(760)
        
        # 从用户管理器获取当前用户头像
        user = self.userManager.get_current_user()
        self.setWindowIcon(self.get_rounded_icon(user['avatar'], 64))
        self.setWindowTitle('Latex公式识别')

        # self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # 加上这两行
        self.updateFrameless()
        self.setMicaEffectEnabled(False)

        # 不再创建和显示 splash screen
        # 直接设置窗口位置并显示
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

    def onSupport(self):
        language = cfg.get(cfg.language).value
        if language.name() == "zh_CN":
            QDesktopServices.openUrl(QUrl(ZH_SUPPORT_URL))
        else:
            QDesktopServices.openUrl(QUrl(EN_SUPPORT_URL))

    def resizeEvent(self, e):
        super().resizeEvent(e)

    def closeEvent(self, e):
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        super().closeEvent(e)

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # retry
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def switchToSample(self, routeKey, index):
        """ switch to sample """
        interfaces = self.findChildren(GalleryInterface)
        for w in interfaces:
            if w.objectName() == routeKey:
                self.stackedWidget.setCurrentWidget(w, False)
                w.scrollToCard(index)
    
    def showMessageBox(self):
        w = MessageBox(
            '<strong>Author:</strong> andy',
            '<strong>Github:</strong> https://github.com/2394855029/LatexTransform <br> <strong>UI:</strong> PyQt-Fluent-Widgets',
            self
        )
        w.yesButton.setText('Github')
        w.cancelButton.setText('Cancel')

        if w.exec():
            QDesktopServices.openUrl(QUrl("https://github.com/2394855029/LatexTransform"))
            
    def showUserProfileDialog(self):
        """显示用户资料对话框"""
        from .user_profile_dialog import UserProfileDialog
        dialog = UserProfileDialog(self)
        dialog.exec()
        
    def onUserChanged(self, user):
        """用户信息变更处理"""
        # 更新窗口图标
        self.setWindowIcon(self.get_rounded_icon(user['avatar'], 64))
