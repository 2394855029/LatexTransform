# coding:utf-8
import sys
from enum import Enum

from PyQt5.QtCore import QLocale
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, RangeConfigItem, RangeValidator,
                            FolderListValidator, Theme, FolderValidator, ConfigSerializer, __version__)


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


class NonEmptyStringValidator(BoolValidator):
    """ 非空字符串验证器 """
    def validate(self, value):
        return isinstance(value, str) and bool(value.strip())


class Config(QConfig):
    """ Config of application """

    # folders
    musicFolders = ConfigItem(
        "Folders", "LocalMusic", [], FolderListValidator())
    downloadFolder = ConfigItem(
        "Folders", "Download", "app/download", FolderValidator())

    # main window
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)

    # Material
    blurRadius  = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())

    # Object
    confidenceThreshold = RangeConfigItem("ObjectDetection", "ConfidenceThreshold", 45, RangeValidator(0, 100))
    iouThreshold = RangeConfigItem("ObjectDetection", "IoUThreshold", 71, RangeValidator(0, 100))
    model = OptionsConfigItem("ObjectDetection", "Model", "YOLO11n", OptionsValidator(["YOLO11n", "YOLO11s", "YOLO11x", "YOLOv8m", "mask"]))


    # LatexOCR
    type = OptionsConfigItem("LatexOCR", "Type", "simpletex", OptionsValidator(["Simpletex"]))
    api_url = ConfigItem("LatexOCR", "ApiUrl", "https://server.simpletex.cn/api/latex_ocr", NonEmptyStringValidator())
    token = ConfigItem("LatexOCR", "Token", "abc" * 10, NonEmptyStringValidator())

YEAR = 2025
AUTHOR = "andy"
VERSION = "1.0.0"
HELP_URL = "https://github.com/ziuch/LatexOCR-GUI"
REPO_URL = "https://github.com/ziuch/LatexOCR-GUI"
EXAMPLE_URL = "https://github.com/ziuch/LatexOCR-GUI/tree/master/examples"
FEEDBACK_URL = "https://github.com/ziuch/LatexOCR-GUI/issues"
RELEASE_URL = "https://github.com/ziuch/LatexOCR-GUI/releases/latest"
ZH_SUPPORT_URL = "https://github.com/ziuch/LatexOCR-GUI"
EN_SUPPORT_URL = "https://github.com/ziuch/LatexOCR-GUI"


cfg = Config()
cfg.themeMode.value = Theme.AUTO
qconfig.load('app/config/config.json', cfg)