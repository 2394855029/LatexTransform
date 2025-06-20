from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, FolderListSettingCard,
                            OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ComboBoxSettingCard, ExpandLayout, Theme, CustomColorSettingCard,
                            setTheme, setThemeColor, RangeSettingCard, isDarkTheme, MessageBoxBase, SubtitleLabel, LineEdit, CaptionLabel, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBar
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt5.QtGui import QDesktopServices, QColor
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog
import re  # 在文件顶部添加

from ..common.config import cfg, HELP_URL, FEEDBACK_URL, AUTHOR, VERSION, YEAR, isWin11
from ..common.signal_bus import signalBus
from ..common.style_sheet import StyleSheet


class CustomMessageBox(MessageBoxBase):

    def __init__(self, parent=None, title="设置 API 地址", content="请输入 API 地址："):
        super().__init__(parent)
        self.title = title
        self.titleLabel = SubtitleLabel(self.title, self)
        self.urlLineEdit = LineEdit(self)

        self.urlLineEdit.setPlaceholderText(content)
        self.urlLineEdit.setClearButtonEnabled(True)

        self.warningLabel = CaptionLabel("URL 不正确")
        self.warningLabel.setTextColor("#cf1010", QColor(255, 28, 32))

        # add widget to view layout
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.urlLineEdit)
        self.viewLayout.addWidget(self.warningLabel)
        self.warningLabel.hide()

        self.widget.setMinimumWidth(350)

    def validate(self):
        """ 重写验证表单数据的方法 """
        if self.title == "设置 API 地址":
            url = self.urlLineEdit.text()
            # 验证URL格式
            url_pattern = r'^https?:\/\/([\w\-]+(\.[\w\-]+)*\/)*[\w\-]+(\.[\w\-]+)*\/?(\?([\w\-\.,@?^=%&:\/~\+#]*)+)?$'
            isValid = bool(re.match(url_pattern, url))
        elif self.title == "设置令牌":
            isValid = len(self.urlLineEdit.text()) == 64
        self.warningLabel.setHidden(isValid)
        return isValid




class SettingInterface(ScrollArea):
    """ Setting interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel(self.tr("Settings"), self)

        

        # personalization
        self.personalGroup = SettingCardGroup(
            self.tr('Personalization'), self.scrollWidget)

        # self.micaCard = SwitchSettingCard(
        #     FIF.TRANSPARENT,
        #     self.tr('Mica effect'),
        #     self.tr('Apply semi transparent to windows and surfaces'),
        #     cfg.micaEnabled,
        #     self.personalGroup
        # )
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr('Application theme'),
            self.tr("Change the appearance of your application"),
            texts=[
                self.tr('Light'), self.tr('Dark'),
                self.tr('Use system setting')
            ],
            parent=self.personalGroup
        )
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            self.personalGroup
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            self.tr("Interface zoom"),
            self.tr("Change the size of widgets and fonts"),
            texts=[
                "100%", "125%", "150%", "175%", "200%",
                self.tr("Use system setting")
            ],
            parent=self.personalGroup
        )
        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr('Language'),
            self.tr('Set your preferred language for UI'),
            texts=['简体中文', '繁體中文', 'English', self.tr('Use system setting')],
            parent=self.personalGroup
        )

        # update software
        self.updateSoftwareGroup = SettingCardGroup(
            self.tr("Software update"), self.scrollWidget)
        self.updateOnStartUpCard = SwitchSettingCard(
            FIF.UPDATE,
            self.tr('Check for updates when the application starts'),
            self.tr('The new version will be more stable and have more features'),
            configItem=cfg.checkUpdateAtStartUp,
            parent=self.updateSoftwareGroup
        )

        # application
        self.aboutGroup = SettingCardGroup(self.tr('About'), self.scrollWidget)
        self.helpCard = HyperlinkCard(
            HELP_URL,
            self.tr('Open help page'),
            FIF.HELP,
            self.tr('Help'),
            self.tr(
                'Discover new features and learn useful tips about PyQt-Fluent-Widgets'),
            self.aboutGroup
        )
        self.feedbackCard = PrimaryPushSettingCard(
            self.tr('Provide feedback'),
            FIF.FEEDBACK,
            self.tr('Provide feedback'),
            self.tr('Help us improve PyQt-Fluent-Widgets by providing feedback'),
            self.aboutGroup
        )
        self.aboutCard = PrimaryPushSettingCard(
            self.tr('Check update'),
            FIF.INFO,
            self.tr('About'),
            '© ' + self.tr('Copyright') + f" {YEAR}, {AUTHOR}. " +
            self.tr('Version') + " " + VERSION,
            self.aboutGroup
        )

        # 公式识别配置
        self.latexOcrGroup = SettingCardGroup("公式识别", self.scrollWidget)
        self.typeCard = ComboBoxSettingCard(
            cfg.type,
            FIF.LABEL,
            "识别类型",
            "选择公式识别服务类型",
            texts=['Simpletex'],
            parent=self.latexOcrGroup
        )
        self.apiUrlCard = PushSettingCard(
            "设置",
            FIF.LINK,
            "API 地址",
            cfg.api_url.value,
            self.latexOcrGroup
        )
        self.tokenCard = PushSettingCard(
            "设置",
            FIF.LABEL,
            "API 令牌",
            cfg.token.value,
            self.latexOcrGroup
        )

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('settingInterface')

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')
        StyleSheet.SETTING_INTERFACE.apply(self)

        # self.micaCard.setEnabled(isWin11())

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(36, 30)

        # self.personalGroup.addSettingCard(self.micaCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)
        self.personalGroup.addSettingCard(self.languageCard)

        self.updateSoftwareGroup.addSettingCard(self.updateOnStartUpCard)

        self.aboutGroup.addSettingCard(self.helpCard)
        self.aboutGroup.addSettingCard(self.feedbackCard)
        self.aboutGroup.addSettingCard(self.aboutCard)

        # 添加公式识别配置组
        self.latexOcrGroup.addSettingCard(self.typeCard)
        self.latexOcrGroup.addSettingCard(self.apiUrlCard)
        self.latexOcrGroup.addSettingCard(self.tokenCard)
        self.expandLayout.addWidget(self.latexOcrGroup)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.updateSoftwareGroup)
        self.expandLayout.addWidget(self.aboutGroup)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.success(
            self.tr('Updated successfully'),
            self.tr('Configuration takes effect after restart'),
            duration=1500,
            parent=self
        )

    def __onDownloadFolderCardClicked(self):
        """ download folder card clicked slot """
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Choose folder"), "./")
        if not folder or cfg.get(cfg.downloadFolder) == folder:
            return

        cfg.set(cfg.downloadFolder, folder)
        self.downloadFolderCard.setContent(folder)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        cfg.appRestartSig.connect(self.__showRestartTooltip)

        # personalization
        cfg.themeChanged.connect(setTheme)
        self.themeColorCard.colorChanged.connect(lambda c: setThemeColor(c))
        # self.micaCard.checkedChanged.connect(signalBus.micaEnableChanged)

        # about
        self.feedbackCard.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_URL)))

        # 连接 API URL 和 Token 的点击事件
        self.apiUrlCard.clicked.connect(self.__onApiUrlCardClicked)
        self.tokenCard.clicked.connect(self.__onTokenCardClicked)

    def __onApiUrlCardClicked(self):
        """ API URL card clicked slot """
        w = CustomMessageBox(
            title="设置 API 地址",
            content="请输入 API 地址：",
            parent=self
        )
        w.urlLineEdit.setText(cfg.api_url.value)
        if w.exec():
            url = w.urlLineEdit.text()
            if url and url != cfg.api_url.value:
                cfg.api_url.value = url
                self.apiUrlCard.setContent(url)
                cfg.save()
                InfoBar.success(
                    title='设置成功',
                    content='API 地址已更新',
                    duration=2000,
                    position=InfoBarPosition.TOP,
                    parent=self
                )

    def __onTokenCardClicked(self):
        """ Token card clicked slot """
        w = CustomMessageBox(
            title="设置令牌",
            content="请输入 API 令牌：",
            parent=self
        )
        w.urlLineEdit.setText(cfg.token.value)
        w.warningLabel.setText("令牌长度必须为 64 位")
        if w.exec():
            token = w.urlLineEdit.text()
            if token and token != cfg.token.value:
                cfg.token.value = token
                self.tokenCard.setContent(token)
                cfg.save()
                InfoBar.success(
                    title='设置成功',
                    content='API 令牌已更新',
                    duration=2000,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
