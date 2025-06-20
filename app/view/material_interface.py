# coding:utf-8
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import FluentIcon as FIF

from .gallery_interface import GalleryInterface
from ..common.translator import Translator
from ..common.config import cfg


class MaterialInterface(GalleryInterface):
    """ Material interface """

    def __init__(self, parent=None):
        t = Translator()
        super().__init__(
            title=t.material,
            subtitle='qfluentwidgets.components.widgets',
            parent=parent
        )
        self.setObjectName('materialInterface')

        # 使用普通QLabel替代AcrylicLabel，避免警告
        self.label = QLabel()
        self.label.setPixmap(QPixmap(':/gallery/images/chidanta.jpg'))
        self.label.setMaximumSize(787, 579)
        self.label.setMinimumSize(197, 145)
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignCenter)

        self.addExampleCard(
            self.tr('Acrylic label'),
            self.label,
            'https://github.com/zhiyiYo/PyQt-Fluent-Widgets/blob/master/examples/material/acrylic_label/demo.py',
            stretch=1
        )

    def onBlurRadiusChanged(self, radius: int):
        # 简单实现，不再支持模糊效果
        pass
