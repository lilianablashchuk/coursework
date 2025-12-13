# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(800, 600)
        self.listWidget = QListWidget(Widget)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setGeometry(QRect(40, 40, 256, 192))
        self.refreshButton = QPushButton(Widget)
        self.refreshButton.setObjectName(u"refreshButton")
        self.refreshButton.setGeometry(QRect(400, 60, 90, 29))
        self.addLotButton = QPushButton(Widget)
        self.addLotButton.setObjectName(u"addLotButton")
        self.addLotButton.setGeometry(QRect(400, 100, 90, 29))
        self.placeBidButton = QPushButton(Widget)
        self.placeBidButton.setObjectName(u"placeBidButton")
        self.placeBidButton.setGeometry(QRect(400, 170, 90, 29))
        self.titleEdit = QLineEdit(Widget)
        self.titleEdit.setObjectName(u"titleEdit")
        self.titleEdit.setGeometry(QRect(20, 310, 113, 28))
        self.priceEdit = QLineEdit(Widget)
        self.priceEdit.setObjectName(u"priceEdit")
        self.priceEdit.setGeometry(QRect(240, 310, 113, 28))
        self.bidEdit = QLineEdit(Widget)
        self.bidEdit.setObjectName(u"bidEdit")
        self.bidEdit.setGeometry(QRect(470, 310, 113, 28))

        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Widget", None))
        self.refreshButton.setText(QCoreApplication.translate("Widget", u"PushButton", None))
        self.addLotButton.setText(QCoreApplication.translate("Widget", u"PushButton", None))
        self.placeBidButton.setText(QCoreApplication.translate("Widget", u"PushButton", None))
    # retranslateUi

