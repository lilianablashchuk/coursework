# -*- coding: utf-8 -*-
import sys
import subprocess
import grpc
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QListWidget, QLineEdit, QPushButton, QMessageBox, QLabel,
    QComboBox, QTabWidget, QGroupBox, QDialog, QListWidgetItem,
    QScrollArea, QFrame
)
from PySide6.QtCore import QTimer, Qt, QSize, QObject, Signal, QDateTime
from PySide6.QtGui import QBrush, QColor, QFont
from datetime import datetime, timedelta, timezone


import auction_pb2
import auction_pb2_grpc

FIXED_WINDOWS_HOST_IP = "172.26.48.1"

def get_server_address(port=50051):
    return f"{FIXED_WINDOWS_HOST_IP}:{port}"

SERVER_ADDRESS = get_server_address()


GLOBAL_STYLE = """
QWidget {
    background-color: #F8F8FF;
    color: #333333;
    font-size: 14px;
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
}


QTabWidget::pane {
    border: 1px solid #DDA0DD;
    border-radius: 10px;
    background-color: #F8F8FF;
}

QTabWidget::tab-bar {
    left: 5px;
}

QTabBar::tab {
    background: #E6E6FA;
    border: 1px solid #DDA0DD;
    border-bottom-color: #DDA0DD;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 15px;
    font-weight: bold;
    color: #5D3FD3;
}

QTabBar::tab:selected {
    background: #FFC0CB;
    border-color: #FF69B4;
    border-bottom-color: #FFC0CB;
    color: #333333;
}


QLabel#titleLabel {
    color: #FF69B4;
    font-size: 36px;
    font-weight: bold;
}


QGroupBox {
    border: 1px solid #DDA0DD;
    border-radius: 15px;
    margin-top: 15px;
    background-color: #FFFFFF;
    padding: 20px;
    font-weight: bold;
    color: #333333;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #FF69B4;
    font-size: 18px;
}


QPushButton {
    background-color: #FFC0CB;
    color: #5D3FD3;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 700;
    border: none;
}
QPushButton:hover {
    background-color: #F8BBD0;
}
QPushButton:disabled {
    background-color: #E6E6FA;
    color: #AAAAAA;
}


QPushButton#PlaceBidButton {
    background-color: #B0E0E6;
    color: #38761D;
}
QPushButton#PlaceBidButton:hover {
    background-color: #A2D9D9;
}
QPushButton#PlaceBidButton:disabled {
    background-color: #E6E6FA;
    color: #AAAAAA;
}


QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #DDA0DD;
    border-radius: 8px;
    padding: 8px;
    color: #333333;
}


QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #DDA0DD;
    border-radius: 8px;
    padding: 5px;
}


QListWidget::item:selected {
    background-color: #FFC0CB;
    color: #5D3FD3;
    border-radius: 5px;
}


QListWidget QWidget {
    background-color: transparent;
}
QListWidget QWidget:hover {
    background-color: #E6E6FA;
}

/* Стиль для картки лота */
QFrame#LotCard {
    border: 2px solid #DDA0DD;
    border-radius: 12px;
    background-color: #FFFFFF;
    padding: 10px;
    margin: 5px;
}
QFrame#LotCard:hover {
    border-color: #FF69B4;
    background-color: #FFF0F5;
}

QWidget#UserLot {
    background-color: #F8BBD0;
}
QWidget#UserLot:hover {
    background-color: #FFC0CB;
}
"""


class BidData:
    def __init__(self, user, amount, time):
        self.user = user
        try:
             self.amount = float(amount)
        except (TypeError, ValueError):
             self.amount = 0.0
        self.time = time

class Lot:
    def __init__(self, lot_pb):
        self.id = lot_pb.id
        self.title = lot_pb.title
        self.description = lot_pb.description
        self.creator = lot_pb.creator
        self.createdAt = lot_pb.createdAt

        try:
             self.startingPrice = float(lot_pb.startingPrice)
        except (TypeError, ValueError):
             self.startingPrice = 0.0

        self.startTime = lot_pb.startTime

        try:
             self.durationMinutes = int(lot_pb.durationMinutes)
        except (TypeError, ValueError):
             self.durationMinutes = 0

        try:
             self.usersPresent = int(getattr(lot_pb, 'usersPresent', 0))
        except (TypeError, ValueError):
             self.usersPresent = 0

        self.status = getattr(lot_pb, 'status', 'unknown')

        self.bids = [BidData(b.user, b.amount, b.time) for b in lot_pb.bids]

    def getCurrentPrice(self):
        if not self.bids:
            return self.startingPrice
        return max(b.amount for b in self.bids)

def iso_to_local_str(iso_time_str, fmt="%d.%m.%Y %H:%M"):
    try:
        dt_utc = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
        dt_local = dt_utc.astimezone(datetime.now().astimezone().tzinfo)
        return dt_local.strftime(fmt)
    except Exception:
        return "N/A"


class HomeTab(QWidget):
    changeTabSignal = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("gRPC Auction Client")
        title.setObjectName("titleLabel")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        info = QLabel("Use the tabs or buttons below to navigate.")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        buttonLayout = QHBoxLayout()

        self.btnLogin = QPushButton("Login")
        self.btnRegister = QPushButton("Register")
        self.btnAuction = QPushButton("View Auctions")
        self.btnProfile = QPushButton("Profile")

        buttonLayout.addWidget(self.btnLogin)
        buttonLayout.addWidget(self.btnRegister)
        buttonLayout.addWidget(self.btnAuction)
        buttonLayout.addWidget(self.btnProfile)

        layout.addLayout(buttonLayout)
        layout.addStretch()

        self.btnLogin.clicked.connect(lambda: self.changeTabSignal.emit(1))
        self.btnRegister.clicked.connect(lambda: self.changeTabSignal.emit(2))
        self.btnProfile.clicked.connect(lambda: self.changeTabSignal.emit(3))
        self.btnAuction.clicked.connect(lambda: self.changeTabSignal.emit(4))


class LoginOnlyTab(QWidget):
    loginSuccessful = Signal(str, str)

    def __init__(self, stub, parent=None):
        super().__init__(parent)
        self.stub = stub

        layout = QVBoxLayout(self)
        lbl = QLabel("Client Login")
        lbl.setObjectName("titleLabel")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        layout.addWidget(QLabel("Username:"))
        self.loginUsername = QLineEdit()
        self.loginUsername.setPlaceholderText("Username")
        layout.addWidget(self.loginUsername)

        layout.addWidget(QLabel("Password:"))
        self.loginPassword = QLineEdit()
        self.loginPassword.setPlaceholderText("Password")
        self.loginPassword.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.loginPassword)

        self.loginButton = QPushButton("Login")
        layout.addWidget(self.loginButton)

        self.loginMessage = QLabel("")
        self.loginMessage.setAlignment(Qt.AlignCenter)
        self.loginMessage.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(self.loginMessage)
        layout.addStretch()

        self.loginButton.clicked.connect(self.handleLogin)

    def handleLogin(self):
        user = self.loginUsername.text().strip()
        passwd = self.loginPassword.text().strip()
        if not user or not passwd:
            self.loginMessage.setStyleSheet("color: #FF69B4; font-weight: bold;")
            self.loginMessage.setText("Enter username and password.")
            return
        try:
            resp = self.stub.Login(auction_pb2.AuthRequest(username=user, password=passwd))
            if resp.status == "ok":
                self.loginMessage.setStyleSheet("color: #38761D; font-weight: bold;")
                self.loginMessage.setText("Login successful!")
                self.loginSuccessful.emit(user, "dummy_token")
            else:
                self.loginMessage.setStyleSheet("color: #FF69B4; font-weight: bold;")
                self.loginMessage.setText(resp.message)
        except grpc.RpcError as e:
            details = e.details() or "Connection Error"
            self.loginMessage.setStyleSheet("color: #FF69B4; font-weight: bold;")
            self.loginMessage.setText(f"Login Error: {details}")


class RegisterOnlyTab(QWidget):
    registerSuccessful = Signal(str, str)

    def __init__(self, stub, parent=None):
        super().__init__(parent)
        self.stub = stub

        layout = QVBoxLayout(self)
        lbl = QLabel("Client Registration")
        lbl.setObjectName("titleLabel")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        layout.addWidget(QLabel("Username:"))
        self.registerUsername = QLineEdit()
        self.registerUsername.setPlaceholderText("Username")
        layout.addWidget(self.registerUsername)

        layout.addWidget(QLabel("Password:"))
        self.registerPassword = QLineEdit()
        self.registerPassword.setPlaceholderText("Password")
        self.registerPassword.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.registerPassword)

        self.registerButton = QPushButton("Register")
        layout.addWidget(self.registerButton)

        self.registerMessage = QLabel("")
        self.registerMessage.setAlignment(Qt.AlignCenter)
        self.registerMessage.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(self.registerMessage)
        layout.addStretch()

        self.registerButton.clicked.connect(self.handleRegister)

    def handleRegister(self):
        user = self.registerUsername.text().strip()
        passwd = self.registerPassword.text().strip()
        if not user or not passwd:
            self.registerMessage.setStyleSheet("color: #FF69B4; font-weight: bold;")
            self.registerMessage.setText("Enter username and password.")
            return
        try:
            resp = self.stub.Register(auction_pb2.AuthRequest(username=user, password=passwd))
            if resp.status == "ok":
                self.registerMessage.setStyleSheet("color: #38761D; font-weight: bold;")
                self.registerMessage.setText("Registration successful! Proceed to Login.")
                self.registerSuccessful.emit(user, "dummy_token")
            else:
                self.registerMessage.setStyleSheet("color: #FF69B4; font-weight: bold;")
                self.registerMessage.setText(resp.message)
        except grpc.RpcError as e:
            details = e.details() or "Connection Error"
            self.registerMessage.setStyleSheet("color: #FF69B4; font-weight: bold;")
            self.registerMessage.setText(f"Registration Error: {details}")


class ProfileTab(QWidget):
    def __init__(self, stub, parent=None):
        super().__init__(parent)
        self.stub = stub
        self.currentUser = ""

        layout = QVBoxLayout(self)

        self.lblUser = QLabel("Please log in to view profile details", self)
        self.lblUser.setObjectName("userLabel")
        self.lblUser.setStyleSheet("font-size: 18px; color: #5D3FD3;")
        layout.addWidget(self.lblUser)

        layout.addWidget(QLabel("Your recent bids:"))
        self.listBids = QListWidget(self)
        self.listBids.setObjectName("bidsListWidget")
        self.listBids.setMinimumHeight(150)
        layout.addWidget(self.listBids)

        layout.addWidget(QLabel("<b>Your Winnings (Purchased Lots):</b>"))
        self.listWinnings = QListWidget(self)
        self.listWinnings.setObjectName("winningsListWidget")
        self.listWinnings.setMinimumHeight(150)
        layout.addWidget(self.listWinnings)

        layout.addStretch()

    def setUserName(self, username):
        self.currentUser = username
        self.lblUser.setText(f"Welcome, <b>{self.currentUser}</b>")
        self.loadUserBids()
        self.loadUserWinnings()

    def loadUserBids(self):
        self.listBids.clear()
        if not self.currentUser:
            self.listBids.addItem("Login required.")
            return

        self.listBids.addItem("Loading bids...")
        try:
            request = auction_pb2.UserRequest(username=self.currentUser)
            response = self.stub.GetBidsByUser(request)

            self.listBids.clear()
            if not response.bids:
                self.listBids.addItem("You have not placed any bids yet.")
            else:
                for bid_info in response.bids:
                    text = f"Лот: {bid_info.lotId} ({bid_info.lotTitle}) | Ставка: {bid_info.amount:.2f} ₴"
                    self.listBids.addItem(text)
        except grpc.RpcError as e:
            self.listBids.clear()
            self.listBids.addItem(f"Error loading bids: {e.details()}")

    def loadUserWinnings(self):
        self.listWinnings.clear()
        if not self.currentUser:
            self.listWinnings.addItem("Login required.")
            return

        self.listWinnings.addItem("Checking for won lots...")
        try:
            request = auction_pb2.UserRequest(username=self.currentUser)
            response = self.stub.GetWinningsByUser(request)

            self.listWinnings.clear()
            if not response.winnings:
                self.listWinnings.addItem("You have not won any finished auctions yet.")
            else:
                for win_info in response.winnings:
                    text = f"Лот {win_info.lotId}: {win_info.lotTitle} | Фінальна ціна: {win_info.winningAmount:.2f} ₴"
                    item = QListWidgetItem(text)
                    item.setBackground(QBrush(QColor("#B0E0E6")))
                    self.listWinnings.addItem(item)
        except grpc.RpcError as e:
            self.listWinnings.clear()
            self.listWinnings.addItem(f"Error loading winnings: {e.details()}")


class AuctionTab(QWidget):
    bidSuccessful = Signal()

    def __init__(self, stub, parent=None):
        super().__init__(parent)
        self.stub = stub
        self.currentUser = ""
        self.currentLots = []
        self.selectedLotId = None

        mainLayout = QVBoxLayout(self)

        self.statusLabel = QLabel("Status: Login Required")
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.statusLabel.setStyleSheet("color: #FF69B4; font-weight: bold;")
        mainLayout.addWidget(self.statusLabel)

        hLayoutFilters = QHBoxLayout()
        self.filterEdit = QLineEdit()
        self.filterEdit.setPlaceholderText("Filter by title...")
        hLayoutFilters.addWidget(self.filterEdit)

        self.filterCombo = QComboBox()
        self.filterCombo.addItems(["All lots", "With bids", "Without bids"])
        self.sortCombo = QComboBox()
        self.sortCombo.addItems(["ID Ascending", "ID Descending", "Price Ascending", "Price Descending"])

        hLayoutFilters.addWidget(QLabel("Filter:"))
        hLayoutFilters.addWidget(self.filterCombo)
        hLayoutFilters.addWidget(QLabel("Sort:"))
        hLayoutFilters.addWidget(self.sortCombo)
        mainLayout.addLayout(hLayoutFilters)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setMinimumHeight(250)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scrollContent = QWidget()
        self.hLotLayout = QHBoxLayout(self.scrollContent)
        self.hLotLayout.setAlignment(Qt.AlignLeft)

        self.scrollContent.setLayout(self.hLotLayout)
        self.scrollArea.setWidget(self.scrollContent)

        mainLayout.addWidget(self.scrollArea, 2)

        mainLayout.addWidget(QLabel("Bid History:"))

        self.listBids = QListWidget()
        self.listBids.setMinimumHeight(120)
        mainLayout.addWidget(self.listBids, 1)

        buttonLayout = QHBoxLayout()
        self.refreshButton = QPushButton("Refresh")
        self.addLotButton = QPushButton("Add Lot")
        self.deleteLotButton = QPushButton("Delete Lot")
        self.deleteLotButton.setEnabled(False)

        buttonLayout.addWidget(self.refreshButton)
        buttonLayout.addWidget(self.addLotButton)
        buttonLayout.addWidget(self.deleteLotButton)
        mainLayout.addLayout(buttonLayout)

        bidLayout = QHBoxLayout()
        self.bidEdit = QLineEdit()
        self.bidEdit.setPlaceholderText("Bid Amount")
        self.placeBidButton = QPushButton("Place Bid")
        self.placeBidButton.setObjectName("PlaceBidButton")
        self.placeBidButton.setEnabled(False)
        self.bidEdit.setEnabled(False)
        bidLayout.addWidget(self.bidEdit)
        bidLayout.addWidget(self.placeBidButton)
        mainLayout.addLayout(bidLayout)

        self.refreshButton.clicked.connect(self.refreshAuctions)
        self.addLotButton.clicked.connect(self.onAddLot)
        self.deleteLotButton.clicked.connect(self.onDeleteLot)
        self.placeBidButton.clicked.connect(self.onPlaceBid)

        self.filterEdit.textChanged.connect(self.updateList)
        self.filterCombo.currentTextChanged.connect(self.updateList)
        self.sortCombo.currentTextChanged.connect(self.updateList)

        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshAuctions)
        self.refreshTimer.start(5000)

        self.refreshAuctions()

    def setCurrentUser(self, username):
        self.currentUser = username
        self.deleteLotButton.setEnabled(False)
        self.placeBidButton.setEnabled(bool(username))
        self.bidEdit.setEnabled(bool(username))
        self.refreshAuctions()

    def refreshAuctions(self):
        if not self.currentUser:
            self.statusLabel.setText("Status: Login Required")
            self.statusLabel.setStyleSheet("color: #FF69B4; font-weight: bold;")
            return

        selected_id = self.selectedLotId

        try:
            response = self.stub.GetAuctions(auction_pb2.Empty())
            self.currentLots = [Lot(lot) for lot in response.lots]

            self.statusLabel.setText("Status: Connected (Refreshed)")
            self.statusLabel.setStyleSheet("color: #38761D; font-weight: bold;")
            self.updateList(selected_id)
        except grpc.RpcError as e:
            self.statusLabel.setText(f"Status: Server Error: {e.details()}")
            self.statusLabel.setStyleSheet("color: #FF69B4; font-weight: bold;")

    def updateList(self, preserve_id=None):
        while self.hLotLayout.count():
            child = self.hLotLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if preserve_id is not None and not any(lot.id == preserve_id for lot in self.currentLots):
             self.selectedLotId = None
        else:
             self.selectedLotId = preserve_id

        filteredLots = []
        textFilter = self.filterEdit.text().lower().strip()
        bidFilter = self.filterCombo.currentText()

        for lot in self.currentLots:
            if textFilter and textFilter not in lot.title.lower(): continue
            if bidFilter == "With bids" and not lot.bids: continue
            if bidFilter == "Without bids" and lot.bids: continue
            filteredLots.append(lot)

        sortMode = self.sortCombo.currentText()
        if sortMode == "ID Ascending":
            filteredLots.sort(key=lambda x: x.id)
        elif sortMode == "ID Descending":
            filteredLots.sort(key=lambda x: x.id, reverse=True)
        elif sortMode == "Price Ascending":
            filteredLots.sort(key=lambda x: x.getCurrentPrice())
        elif sortMode == "Price Descending":
            filteredLots.sort(key=lambda x: x.getCurrentPrice(), reverse=True)

        for lot in filteredLots:
            card = self._createLotCard(lot)
            self.hLotLayout.addWidget(card)

        self.hLotLayout.addStretch(1)

        self.updateBidHistory(self.selectedLotId)

    def _createLotCard(self, lot):
        card = QFrame()
        card.setObjectName("LotCard")
        card.setFixedWidth(280)

        cardLayout = QVBoxLayout(card)
        cardLayout.setSpacing(5)

        title_label = QLabel(f"<b>ID {lot.id}: {lot.title}</b>")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setTextFormat(Qt.RichText)
        cardLayout.addWidget(title_label)

        status_text = ""
        if lot.status == "ended":
             status_text = "<span style='color: red; font-weight: bold;'>[CLOSED]</span>"
        elif lot.status == "not_started":
             status_text = "<span style='color: orange;'>[PENDING]</span>"
        else:
             status_text = "<span style='color: green;'>[ACTIVE]</span>"

        cardLayout.addWidget(QLabel(f"Status: {status_text}"))

        currentPrice = lot.getCurrentPrice()
        price_label = QLabel(f"Price: <span style='color: #FF69B4; font-weight: bold;'>{currentPrice:.2f} ₴</span>")
        price_label.setTextFormat(Qt.RichText)
        cardLayout.addWidget(price_label)

        cardLayout.addWidget(QLabel(f"Creator: {lot.creator}"))

        participants_info = f"Participants: {lot.usersPresent}"
        cardLayout.addWidget(QLabel(participants_info))

        joinBtn = QPushButton("Join Auction")
        joinBtn.clicked.connect(lambda: self.showAuctionWindow(lot.id))

        if lot.status == "ended":
             joinBtn.setText("VIEW RESULTS")
             joinBtn.setEnabled(True)

        cardLayout.addWidget(joinBtn)

        cardLayout.addStretch(1)

        custom_style = ""
        if lot.creator == self.currentUser:
             custom_style = "QFrame#LotCard { border: 3px solid #38761D; background-color: #F8BBD0; }"

        if lot.id == self.selectedLotId:

            custom_style = "QFrame#LotCard { border: 3px solid #5D3FD3; background-color: #E6E6FA; }"

        if custom_style:
             card.setStyleSheet(custom_style)

        card.mousePressEvent = lambda event: self._selectLotCard(lot.id)

        return card

    def _selectLotCard(self, lotId):
        self.selectedLotId = lotId
        self.updateList(lotId)
        self.updateBidHistory(lotId)

    def updateBidHistory(self, lotId):
        self.listBids.clear()

        if lotId is None:
             self.deleteLotButton.setEnabled(False)
             self.placeBidButton.setEnabled(False)
             self.bidEdit.setEnabled(False)
             return

        lot = next((l for l in self.currentLots if l.id == lotId), None)

        if not lot:
            self.deleteLotButton.setEnabled(False)
            return

        sorted_bids = sorted(lot.bids, key=lambda b: b.amount, reverse=True)
        if lot.status == "ended":
            self.listBids.addItem("AUCTION CLOSED")
            if sorted_bids:
                winner = sorted_bids[0]
                self.listBids.addItem(f"WINNER: {winner.user} with {winner.amount:.2f} ₴")
            else:
                 self.listBids.addItem("No winner (No bids placed).")


        if not sorted_bids:
            self.listBids.addItem("No bids placed yet.")
        else:
            for b in sorted_bids:
                bid_time = iso_to_local_str(b.time, fmt="%H:%M:%S")
                bidText = f"User: {b.user} | Amount: {b.amount:.2f} ₴ | Time: {bid_time}"
                self.listBids.addItem(bidText)

        is_creator = lot.creator == self.currentUser
        is_ended = lot.status == "ended"

        self.deleteLotButton.setEnabled(is_creator and not is_ended)
        self.placeBidButton.setEnabled(bool(self.currentUser) and not is_creator and not is_ended)
        self.bidEdit.setEnabled(bool(self.currentUser) and not is_creator and not is_ended)

        if is_ended:
             self.bidEdit.setPlaceholderText("Auction is closed")
        elif is_creator:
             self.bidEdit.setPlaceholderText("Cannot bid on your own lot")
        else:
             self.bidEdit.setPlaceholderText(f"Min Bid: {lot.getCurrentPrice() + 0.01:.2f} ₴")

    def onAddLot(self):
        if not self.currentUser:
            QMessageBox.critical(self, "Error", "Login required to add a lot.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Lot")
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        titleEdit = QLineEdit(); titleEdit.setPlaceholderText("Title (Required)"); layout.addWidget(titleEdit)
        descEdit = QLineEdit(); descEdit.setPlaceholderText("Description"); layout.addWidget(descEdit)
        priceEdit = QLineEdit(); priceEdit.setPlaceholderText("Starting Price (Required)"); layout.addWidget(priceEdit)

        startTimeEdit = QLineEdit()
        default_start_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        startTimeEdit.setText(default_start_time.isoformat().replace('+00:00', 'Z'))
        startTimeEdit.setPlaceholderText("Start Time (Format: YYYY-MM-DDThh:mm:ssZ)"); layout.addWidget(startTimeEdit)

        durationEdit = QLineEdit()
        durationEdit.setText("5")
        durationEdit.setPlaceholderText("Duration in Minutes (e.g., 5)"); layout.addWidget(durationEdit)

        createBtn = QPushButton("Create Lot"); layout.addWidget(createBtn)

        createBtn.clicked.connect(lambda: self._handleCreateLot(dialog, titleEdit.text(), descEdit.text(), priceEdit.text(), startTimeEdit.text(), durationEdit.text()))
        dialog.exec()

    def _handleCreateLot(self, dialog, title, desc, price_str, start_time_str, duration_str):
        try:
            price = float(price_str)
            duration = int(duration_str)
        except ValueError:
            QMessageBox.warning(dialog, "Warning", "Enter valid price and duration (positive numbers).")
            return

        if not title or price <= 0 or duration <= 0 or not start_time_str.endswith('Z'):
            QMessageBox.warning(dialog, "Warning", "Enter valid title, price (> 0), start time (ISO 8601 with Z) and duration (> 0).")
            return

        try:
            request = auction_pb2.CreateLotRequest(
                title=title,
                description=desc,
                creator=self.currentUser,
                startingPrice=price,
                startTime=start_time_str,
                durationMinutes=duration
            )
            self.stub.CreateLot(request)
            QMessageBox.information(dialog, "Success", "Lot created successfully.")
            self.refreshAuctions()
            dialog.accept()
        except grpc.RpcError as e:
            QMessageBox.critical(dialog, "Error", e.details() or str(e))

    def onDeleteLot(self):
        lotId = self.selectedLotId
        if lotId is None: return

        lot = next((l for l in self.currentLots if l.id == lotId), None)

        if not lot or lot.creator != self.currentUser:
            QMessageBox.critical(self, "Forbidden", "You can only delete your own lots.")
            return

        if lot.status == "ended":
             QMessageBox.critical(self, "Forbidden", "Cannot delete an auction that has already ended.")
             return

        reply = QMessageBox.question(self, "Confirm Deletion",
                                            f"Are you sure you want to delete lot {lotId}: '{lot.title}'? This action will also delete all bids.",
                                             QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No: return

        try:
            request = auction_pb2.DeleteLotRequest(lotId=lotId, deleterUsername=self.currentUser)
            response = self.stub.DeleteLot(request)

            if response.status == "ok":
                QMessageBox.information(self, "Success", response.message)
                self.selectedLotId = None
                self.refreshAuctions()
            else:
                QMessageBox.critical(self, "Error Deleting Lot", response.message)

        except grpc.RpcError as e:
            QMessageBox.critical(self, "Error Deleting Lot", e.details() or str(e))

    def onPlaceBid(self):
        lotId = self.selectedLotId
        if lotId is None:
            QMessageBox.warning(self, "Warning", "Select a lot first.")
            return

        lot = next((l for l in self.currentLots if l.id == lotId), None)
        if not lot: return

        if lot.creator == self.currentUser:
             QMessageBox.warning(self, "Warning", "You cannot place a bid on your own lot.")
             return

        if lot.status == "ended":
             QMessageBox.warning(self, "Warning", "Auction is closed.")
             return

        try:
            amount = float(self.bidEdit.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Enter a valid bid amount.")
            return

        currentMax = lot.getCurrentPrice()

        # --- ДОДАНА ПЕРЕВІРКА ---
        if lot.bids:
            # Знаходимо найвищу ставку та її користувача
            highest_bid = max(lot.bids, key=lambda b: b.amount)

            if highest_bid.user == self.currentUser:
                QMessageBox.warning(self, "Warning", "You are currently the highest bidder. You cannot bid against yourself.")
                return
        # ------------------------

        if amount <= currentMax:
            QMessageBox.warning(self, "Warning", f"Bid must be higher than current max ({currentMax:.2f} ₴)")
            return

        bid = auction_pb2.PlaceBidRequest(lotId=lot.id, user=self.currentUser, amount=amount)
        try:
            self.stub.PlaceBid(bid)
            self.bidEdit.clear()
            QMessageBox.information(self, "Success", "Bid successfully placed!")
            self.refreshAuctions()
            self.bidSuccessful.emit()
        except grpc.RpcError as e:
            QMessageBox.critical(self, "Error Placing Bid", e.details() or str(e))

    def showAuctionWindow(self, lotId):
        if not self.currentUser:
             QMessageBox.warning(self, "Forbidden", "You must be logged in to join an auction.")
             return

        lotWindow = LotWindow(lotId, self.stub, self.currentUser, self)

        lotWindow.bidSuccessful.connect(self.refreshAuctions)
        lotWindow.bidSuccessful.connect(self.bidSuccessful)

        lotWindow.exec()



class LotWindow(QDialog):
    bidSuccessful = Signal()

    def __init__(self, lot_id, stub, current_user, parent=None):
        super().__init__(parent)
        self.lotId = lot_id
        self.stub = stub
        self.currentUser = current_user
        self.currentLot = None

        self.setWindowTitle(f"Auction Lot {lot_id}")
        self.resize(500, 650)
        self.setStyleSheet(GLOBAL_STYLE)

        self.lblDescription = QLabel("")
        self.lblDescription.setWordWrap(True)

        self.lblTitle = QLabel("Loading lot details...")
        self.lblTitle.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF69B4;")

        self.lblTimer = QLabel("Time Remaining: --:--:--")
        self.lblTimer.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF69B4;")

        self.lblTimer.setAlignment(Qt.AlignCenter)

        self.lblCurrentPrice = QLabel("Current Price: 0.00 ₴")
        self.lblUsersCount = QLabel("Users Present: 0")

        self.listBids = QListWidget()
        self.editBidAmount = QLineEdit()
        self.editBidAmount.setPlaceholderText("Enter your bid amount")
        self.btnPlaceBid = QPushButton("Place Bid")
        self.btnPlaceBid.setObjectName("PlaceBidButton")

        mainLayout = QVBoxLayout(self)

        mainLayout.addWidget(self.lblTitle, 0)

        mainLayout.addWidget(self.lblDescription, 0)

        mainLayout.addWidget(self.lblTimer, 0)

        mainLayout.addWidget(self.lblCurrentPrice, 0)
        mainLayout.addWidget(self.lblUsersCount, 0)
        mainLayout.addWidget(QLabel("Bid History:"), 0)

        mainLayout.addWidget(self.listBids, 3)

        bidLayout = QHBoxLayout()
        bidLayout.addWidget(self.editBidAmount)
        bidLayout.addWidget(self.btnPlaceBid)
        mainLayout.addLayout(bidLayout)
        self.joinAuction()

        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.fetchLotDetails)
        self.refreshTimer.start(3000)

        self.countdownTimer = QTimer(self)
        self.countdownTimer.timeout.connect(self.updateTimer)
        self.countdownTimer.start(1000)

        self.btnPlaceBid.clicked.connect(self.onPlaceBidClicked)
        self.fetchLotDetails()


    def closeEvent(self, event):
        self.leaveAuction()

        if hasattr(self, 'refreshTimer') and self.refreshTimer.isActive():
            self.refreshTimer.stop()
        if hasattr(self, 'countdownTimer') and self.countdownTimer.isActive():
            self.countdownTimer.stop()
        event.accept()

    def joinAuction(self):
        try:
            request = auction_pb2.LotIdUserRequest(lotId=self.lotId, username=self.currentUser)
            self.stub.JoinAuction(request)
        except grpc.RpcError as e:
            print(f"Error joining auction {self.lotId}: {e.details()}")

    def leaveAuction(self):
        try:
            request = auction_pb2.LotIdUserRequest(lotId=self.lotId, username=self.currentUser)
            self.stub.LeaveAuction(request)
        except grpc.RpcError as e:
            print(f"Error leaving auction {self.lotId}: {e.details()}")


    def calculateRemainingSeconds(self):
        if not self.currentLot or not self.currentLot.startTime or self.currentLot.durationMinutes <= 0:
            return -1
        try:
            start_time_dt = datetime.fromisoformat(self.currentLot.startTime.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            duration = timedelta(minutes=self.currentLot.durationMinutes)
            end_time_dt = start_time_dt + duration

            current_time_dt = datetime.now(timezone.utc)

            remaining = (end_time_dt - current_time_dt).total_seconds()
            if remaining < 0: return 0
            return int(remaining)
        except Exception:
            return -1

    def updateTimer(self):

        remainingSeconds = self.calculateRemainingSeconds()

        if remainingSeconds == -1:
            self.lblTimer.setText("Time Remaining: N/A")
            self.lblTimer.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF69B4;")
            self.btnPlaceBid.setEnabled(False)
            self.editBidAmount.setEnabled(False)
            return

        if remainingSeconds <= 0:
            self.checkWinnerStatus()
            return

        hours = remainingSeconds // 3600
        minutes = (remainingSeconds % 3600) // 60
        seconds = remainingSeconds % 60

        timeStr = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        self.lblTimer.setText("Time Remaining: " + timeStr)
        self.lblTimer.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF69B4;")
        self.btnPlaceBid.setEnabled(True)
        self.editBidAmount.setEnabled(True)

    def checkWinnerStatus(self):
        if self.countdownTimer.isActive(): self.countdownTimer.stop()
        if self.refreshTimer.isActive(): self.refreshTimer.stop()

        try:
            request = auction_pb2.GetLotStatusRequest(lotId=self.lotId)
            response = self.stub.GetLotStatus(request)
        except grpc.RpcError as e:
            self.lblTimer.setText("Time Remaining: ERROR")
            self.lblTimer.setStyleSheet("font-size: 24px; font-weight: bold; color: red;")
            return

        self.lblTitle.setText(response.lotTitle)

        if response.status == "ended_with_winner":
            winner = response.winner
            finalPrice = response.finalPrice

            message = f"AUCTION CLOSED. Winner: {winner} ({finalPrice:.2f} ₴)"

            self.lblTimer.setText(f"<span style='color: black;'>{message}</span>")
            self.lblTimer.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")

            if winner == self.currentUser:
                QMessageBox.information(self, "CONGRATULATIONS!", f"You won the lot '{response.lotTitle}' за {finalPrice:.2f} ₴!")

            self.bidSuccessful.emit()

        elif response.status == "ended_no_bids":
            self.lblTimer.setText("Time Remaining: <span style='color: black;'>AUCTION CLOSED (No Bids)</span>")
            self.lblTimer.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")

        else:
             self.lblTimer.setText("Time Remaining: <span style='color: black;'>AUCTION CLOSED</span>")
             self.lblTimer.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")

        self.btnPlaceBid.setEnabled(False)
        self.editBidAmount.setEnabled(False)

    def displayLotDetails(self):
        if not self.currentLot: return

        self.lblTitle.setText(self.currentLot.title)
        self.lblDescription.setText(self.currentLot.description)

        currentPrice = self.currentLot.getCurrentPrice()
        self.lblCurrentPrice.setText(f"Current Price: <b>{currentPrice:.2f} ₴</b> (Starting: {self.currentLot.startingPrice:.2f} ₴)")

        self.lblUsersCount.setText(f"Users Present: <b>{self.currentLot.usersPresent}</b>")

        self.listBids.clear()

        bids_to_display = sorted(self.currentLot.bids, key=lambda b: b.time, reverse=False)

        for i, b in enumerate(bids_to_display):
            time_local = iso_to_local_str(b.time, fmt="%H:%M:%S")
            bidText = f"{b.user} | {b.amount:.2f} ₴ | Time: {time_local}"

            item = QListWidgetItem(bidText)

            if i == len(bids_to_display) - 1:
                item.setBackground(QBrush(QColor("#F0C4FF")))

            self.listBids.addItem(item)

        is_creator = self.currentLot.creator == self.currentUser
        is_ended = self.currentLot.status == "ended"

        self.btnPlaceBid.setEnabled(not is_creator and not is_ended)
        self.editBidAmount.setEnabled(not is_creator and not is_ended)

        if is_ended:
            self.editBidAmount.setPlaceholderText("Auction is closed")
            self.checkWinnerStatus()
        elif is_creator:
             self.editBidAmount.setPlaceholderText("Cannot bid on your own lot")
        else:
             self.editBidAmount.setPlaceholderText(f"Min Bid: {currentPrice + 0.01:.2f} ₴")

        if not is_ended:
            self.updateTimer()

    def fetchLotDetails(self):
        try:
            response = self.stub.GetAuctions(auction_pb2.Empty())

            lot_data = next((lot for lot in response.lots if lot.id == self.lotId), None)

            if lot_data:

                self.currentLot = Lot(lot_data)
                self.displayLotDetails()
            else:
                self.currentLot = None
                QMessageBox.critical(self, "Error", f"Lot #{self.lotId} not found or deleted.")
                self.close()

        except grpc.RpcError as e:
            QMessageBox.critical(self, "Error", f"Failed to load lot: {e.details()}")

    def onPlaceBidClicked(self):
        if self.currentLot and self.currentLot.creator == self.currentUser:
             QMessageBox.warning(self, "Warning", "You cannot place a bid on your own lot.")
             return

        if self.currentLot and self.currentLot.status == "ended":
             QMessageBox.warning(self, "Forbidden", "Auction is closed.")
             return

        if self.calculateRemainingSeconds() <= 0:
            QMessageBox.warning(self, "Forbidden", "Auction is closed.")
            return

        try:
            amount = float(self.editBidAmount.text())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Enter a valid bid amount.")
            return

        currentPrice = self.currentLot.getCurrentPrice() if self.currentLot else 0

        if self.currentLot and self.currentLot.bids:

            highest_bid = max(self.currentLot.bids, key=lambda b: b.amount)

            if highest_bid.user == self.currentUser:
                QMessageBox.warning(self, "Warning", "You are currently the highest bidder. You cannot bid against yourself.")
                return

        if amount <= currentPrice:
            QMessageBox.warning(self, "Warning", f"Your bid must be higher than the current price ({currentPrice:.2f} ₴).")
            return

        bid_request = auction_pb2.PlaceBidRequest(lotId=self.lotId, user=self.currentUser, amount=amount)

        try:
            self.stub.PlaceBid(bid_request)
            self.editBidAmount.clear()
            QMessageBox.information(self, "Success", "Bid successfully placed!")
            self.fetchLotDetails()
            self.bidSuccessful.emit()
        except grpc.RpcError as e:
            QMessageBox.critical(self, "Bid Error", e.details() or str(e))


class AuctionClient(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auction gRPC Client")

        self.setFixedSize(800, 650)

        self.currentUser = ""
        self.authToken = ""

        self.channel = grpc.insecure_channel(SERVER_ADDRESS)
        self.stub = auction_pb2_grpc.AuctionServiceStub(self.channel)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.setStyleSheet(GLOBAL_STYLE)

        self.homeTab = HomeTab()
        self.loginTab = LoginOnlyTab(self.stub)
        self.registerTab = RegisterOnlyTab(self.stub)
        self.profileTab = ProfileTab(self.stub)
        self.auctionTab = AuctionTab(self.stub)

        self.tabs.addTab(self.homeTab, "Home")
        self.tabs.addTab(self.loginTab, "Login")
        self.tabs.addTab(self.registerTab, "Register")
        self.tabs.addTab(self.profileTab, "Profile")
        self.tabs.addTab(self.auctionTab, "Auction")

        self.loginTab.loginSuccessful.connect(self.handleLoginSuccess)
        self.registerTab.registerSuccessful.connect(lambda u, t: self.tabs.setCurrentWidget(self.loginTab))

        self.auctionTab.bidSuccessful.connect(self.profileTab.loadUserBids)
        self.auctionTab.bidSuccessful.connect(self.profileTab.loadUserWinnings)
        self.homeTab.changeTabSignal.connect(self.tabs.setCurrentIndex)

        self.tabs.setCurrentWidget(self.homeTab)

    def handleLoginSuccess(self, username, token):
        self.currentUser = username
        self.authToken = token
        QMessageBox.information(self, "Login Success", f"You have successfully logged in as: {username}")

        self.auctionTab.setCurrentUser(username)
        self.profileTab.setUserName(username)

        self.tabs.setCurrentWidget(self.auctionTab)

        self.auctionTab.refreshAuctions()
        if not self.auctionTab.refreshTimer.isActive():
            self.auctionTab.refreshTimer.start(5000)

    def closeEvent(self, event):
        if hasattr(self.auctionTab, 'refreshTimer'):
            self.auctionTab.refreshTimer.stop()
        if hasattr(self, 'channel') and self.channel:
            self.channel.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = AuctionClient()
    widget.show()
    sys.exit(app.exec())
