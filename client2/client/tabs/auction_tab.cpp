#include "auction_tab.h"
#include "../server_url.h"
#include "lot_window.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QMessageBox>
#include <QDebug>
#include <QRegularExpression>
#include <QLineEdit>
#include <algorithm>
#include <QDateTime>

AuctionTab::AuctionTab(QWidget *parent, QNetworkAccessManager* manager, QString currentUser)
    : QWidget(parent), manager(manager), currentUser(currentUser)
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    statusLabel = new QLabel("Connecting...");
    statusLabel->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(statusLabel);

    filterEdit = new QLineEdit;
    filterEdit->setPlaceholderText("Filter by title...");
    mainLayout->addWidget(filterEdit);

    listWidget = new QListWidget;
    listWidget->setMinimumHeight(230);
    mainLayout->addWidget(listWidget);

    mainLayout->addWidget(new QLabel("Bid History:"));
    listBids = new QListWidget;
    listBids->setMinimumHeight(100);
    mainLayout->addWidget(listBids);

    QHBoxLayout *bidLayout = new QHBoxLayout;
    bidEdit = new QLineEdit;
    bidEdit->setPlaceholderText("Bid Amount");
    bidLayout->addWidget(bidEdit);

    QHBoxLayout *buttonLayout = new QHBoxLayout;
    refreshButton = new QPushButton("Refresh");
    addLotButton = new QPushButton("Add Lot");
    placeBidButton = new QPushButton("Place Bid");
    deleteLotButton = new QPushButton("Delete Lot");
    deleteLotButton->setEnabled(true);
    buttonLayout->addWidget(refreshButton);
    buttonLayout->addWidget(addLotButton);
    buttonLayout->addWidget(deleteLotButton);
    buttonLayout->addWidget(placeBidButton);
    mainLayout->addLayout(buttonLayout);

    mainLayout->addLayout(bidLayout);

    filterCombo = new QComboBox;
    filterCombo->addItems({"All lots", "With bids", "Without bids"});
    mainLayout->addWidget(filterCombo);

    sortCombo = new QComboBox;
    sortCombo->addItems({"ID Ascending","ID Descending","Price Ascending","Price Descending"});
    mainLayout->addWidget(sortCombo);

    connect(refreshButton, &QPushButton::clicked, this, &AuctionTab::refreshAuctions);
    connect(addLotButton, &QPushButton::clicked, this, &AuctionTab::onAddLot);
    connect(placeBidButton, &QPushButton::clicked, this, &AuctionTab::onPlaceBid);
    connect(filterEdit, &QLineEdit::textChanged, this, [=](){ updateList(); });
    connect(filterCombo, &QComboBox::currentTextChanged, this, [=](){ updateList(); });
    connect(sortCombo, &QComboBox::currentTextChanged, this, [=](){ updateList(); });
    connect(listWidget, &QListWidget::currentRowChanged, this, &AuctionTab::updateBidHistory);
    connect(deleteLotButton, &QPushButton::clicked, this, &AuctionTab::onDeleteLot);

    refreshTimer = new QTimer(this);
    connect(refreshTimer, &QTimer::timeout, this, &AuctionTab::refreshAuctions);
    refreshTimer->start(5000);

    bidTimer = new QTimer(this);
    connect(bidTimer, &QTimer::timeout, this, [=](){
        int row = listWidget->currentRow();
        if(row >= 0) updateBidHistory(row);
    });
    bidTimer->start(5000);

    refreshAuctions();
}

void AuctionTab::refreshAuctions()
{
    int selectedRow = listWidget->currentRow();

    QNetworkRequest request(QUrl(serverUrl + "/auctions/"));
    QNetworkReply *reply = manager->get(request);

    reply->ignoreSslErrors();

    connect(reply, &QNetworkReply::finished, [=](){
        if(reply->error() != QNetworkReply::NoError && reply->error() != QNetworkReply::SslHandshakeFailedError){
            statusLabel->setText(QString("Server not reachable (%1)").arg(reply->errorString()));
            statusLabel->setStyleSheet("color: red; font-weight: bold;");
        } else {
            statusLabel->setText("Connected");
            statusLabel->setStyleSheet("color: green; font-weight: bold;");
            handleAuctionsReply(reply, selectedRow);
        }
        reply->deleteLater();
    });
}


void AuctionTab::setAuthToken(const QString &token) {
    this->authToken = token;
}

void AuctionTab::handleAuctionsReply(QNetworkReply* reply, int preserveRow)
{
    QByteArray data = reply->readAll();
    QJsonDocument doc = QJsonDocument::fromJson(data);
    if(!doc.isArray()) { qDebug() << "Invalid JSON"; return; }

    QJsonArray array = doc.array();
    currentLots.clear();

    for(auto lotVal : array){
        QJsonObject obj = lotVal.toObject();
        Lot lot;
        lot.id = obj["id"].toInt();
        lot.title = obj["title"].toString();
        lot.description = obj["description"].toString();
        lot.creator = obj["creator"].toString();
        lot.createdAt = obj["createdAt"].toString();
        lot.startingPrice = obj["startingPrice"].toDouble();
        lot.startTime = obj["startTime"].toString();
        lot.durationMinutes = obj["durationMinutes"].toInt();
        lot.usersPresent = obj["usersPresent"].toInt();
        lot.bids.clear();

        QJsonArray bidsArray = obj["bids"].toArray();
        for(auto bidVal : bidsArray){
            QJsonObject b = bidVal.toObject();
            lot.bids.append({b["user"].toString(), b["amount"].toDouble(), b["createdAt"].toString()});
        }

        currentLots.append(lot);
    }

    updateList(preserveRow);
}

void AuctionTab::updateList(int preserveRow)
{
    listWidget->clear();
    QString textFilter = filterEdit->text().trimmed();
    QString bidFilter = filterCombo->currentText();
    QString sortMode = sortCombo->currentText();


    QList<Lot> filteredLots;
    for(const Lot &lot : currentLots){
        if(!textFilter.isEmpty() && !lot.title.contains(textFilter, Qt::CaseInsensitive)) continue;
        if(bidFilter=="With bids" && lot.bids.isEmpty()) continue;
        if(bidFilter=="Without bids" && !lot.bids.isEmpty()) continue;
        filteredLots.append(lot);
    }

    std::sort(filteredLots.begin(), filteredLots.end(), [=](const Lot &a, const Lot &b){
        if(sortMode=="ID Ascending") return a.id<b.id;
        if(sortMode=="ID Descending") return a.id>b.id;
        if(sortMode=="Price Ascending") return a.getCurrentPrice() < b.getCurrentPrice();
        if(sortMode=="Price Descending") return a.getCurrentPrice() > b.getCurrentPrice();
        return a.id<b.id;
    });


    for(const Lot &lot : filteredLots){


        QWidget *itemWidget = new QWidget;
        QHBoxLayout *hLayout = new QHBoxLayout(itemWidget);
        hLayout->setContentsMargins(5, 5, 5, 5);
        hLayout->setSpacing(10);

        QLabel *infoLabel = new QLabel;
        double currentPrice = lot.getCurrentPrice();
        QString startTimeOnly = QDateTime::fromString(lot.startTime, Qt::ISODate).toLocalTime().toString("dd.MM.yyyy hh:mm");

        QString participantsInfo = (lot.usersPresent > 0)
                                       ? QString(" | <b>Participants:</b> %1").arg(lot.usersPresent)
                                       : "";

        QString text = QString(
                           "<b>ID:</b> %1 | <b>Title:</b> %2%7<br>"
                           "<b>Start:</b> %3 (Duration: %4 min) | <b>Creator:</b> %5<br>"
                           "<b>Current Bid:</b> <span style='color: #E60000; font-weight: bold;'>%6 ₴</span>"
                           )
                           .arg(lot.id)
                           .arg(lot.title)
                           .arg(startTimeOnly)
                           .arg(lot.durationMinutes)
                           .arg(lot.creator)
                           .arg(currentPrice, 0, 'f', 2)
                           .arg(participantsInfo);

        infoLabel->setText(text);
        infoLabel->setTextFormat(Qt::RichText);
        hLayout->addWidget(infoLabel, 1);


        QPushButton *joinBtn = new QPushButton("Join Auction");
        joinBtn->setFixedWidth(150);
        hLayout->addWidget(joinBtn);

        QListWidgetItem *item = new QListWidgetItem(listWidget);
        item->setSizeHint(QSize(0, 70));


        if (lot.creator == currentUser) {
            itemWidget->setStyleSheet("QWidget { background-color: #e0ffe0; }");

        }

        listWidget->addItem(item);
        listWidget->setItemWidget(item, itemWidget);


        connect(joinBtn, &QPushButton::clicked, this, [=](){

            listWidget->setCurrentItem(item);
            this->showAuctionWindow(lot.id);
        });


        item->setData(Qt::UserRole, lot.id);
    }

    if(preserveRow>=0 && preserveRow<listWidget->count()) listWidget->setCurrentRow(preserveRow);
    else listWidget->setCurrentRow(0);

    updateBidHistory(listWidget->currentRow());
}

void AuctionTab::updateBidHistory(int row)
{
    listBids->clear();

    if(row < 0 || row >= listWidget->count()) {
        deleteLotButton->setEnabled(false);
        placeBidButton->setEnabled(false);
        bidEdit->setEnabled(false);
        bidEdit->setPlaceholderText("Bid Amount");
        return;
    }

    int lotId = listWidget->item(row)->data(Qt::UserRole).toInt();
    if(lotId <= 0) return;

    auto it = std::find_if(currentLots.begin(), currentLots.end(), [=](const Lot &lot){ return lot.id == lotId; });
    if(it == currentLots.end()) return;
    const Lot &lot = *it;

    deleteLotButton->setEnabled(lot.creator == currentUser);

    bool canBid = !currentUser.isEmpty() && (lot.creator != currentUser);

    placeBidButton->setEnabled(canBid);
    bidEdit->setEnabled(canBid);
    bidEdit->setPlaceholderText(QString("Min Bid: %1 ₴").arg(lot.getCurrentPrice() + 0.01, 0, 'f', 2));

    for(const auto &b : lot.bids){
        QString bidText = QString("%1 | %2 ₴ | Time: %3").arg(b.user).arg(b.amount).arg(b.time);
        listBids->addItem(bidText);
    }
}


void AuctionTab::onAddLot()
{
    if (currentUser.isEmpty()) {
        QMessageBox::critical(this, "Login Error", "You must be logged in to create a lot.");
        return;
    }

    QDialog dialog(this);

    dialog.setWindowTitle("Create New Lot");
    QVBoxLayout *layout = new QVBoxLayout(&dialog);

    QLineEdit *titleEdit = new QLineEdit; titleEdit->setPlaceholderText("Title (Required)"); layout->addWidget(titleEdit);
    QLineEdit *descEdit = new QLineEdit; descEdit->setPlaceholderText("Description"); layout->addWidget(descEdit);
    QLineEdit *priceEdit = new QLineEdit; priceEdit->setPlaceholderText("Starting Price (Required)"); layout->addWidget(priceEdit);


    QLineEdit *startTimeEdit = new QLineEdit;
    startTimeEdit->setPlaceholderText("Start Time (Format: YYYY-MM-DDThh:mm:ssZ)");
    startTimeEdit->setText(QDateTime::currentDateTimeUtc().addSecs(300).toString(Qt::ISODate));
    layout->addWidget(startTimeEdit);

    QLineEdit *durationEdit = new QLineEdit;
    durationEdit->setPlaceholderText("Duration in Minutes (e.g., 5)");
    durationEdit->setText("5");
    layout->addWidget(durationEdit);


    QPushButton *createBtn = new QPushButton("Create Lot"); layout->addWidget(createBtn);

    connect(createBtn, &QPushButton::clicked, &dialog, [&](){
        QString title = titleEdit->text().trimmed();
        QString desc = descEdit->text().trimmed();
        QString priceStr = priceEdit->text().trimmed();


        QString startTimeStr = startTimeEdit->text().trimmed();
        QString durationStr = durationEdit->text().trimmed();


        bool okPrice=false; double price=priceStr.toDouble(&okPrice);
        bool okDuration=false; int duration=durationStr.toInt(&okDuration);

        bool okTime = QDateTime::fromString(startTimeStr, Qt::ISODate).isValid();

        if(title.isEmpty() || !okPrice || price<=0 || !okTime || !okDuration || duration<=0){
            QMessageBox::warning(&dialog,"Warning","Enter valid title, starting price (> 0), start time (ISO format), and duration (> 0).");
            return;
        }

        QJsonObject obj;
        obj["title"]=title;
        obj["description"]=desc;
        obj["startingPrice"]=QJsonValue(price);
        obj["startTime"]=startTimeStr;
        obj["durationMinutes"]=QJsonValue(duration);

        QNetworkRequest request(QUrl(serverUrl+"/auctions/"));
        request.setHeader(QNetworkRequest::ContentTypeHeader,"application/json");

        if(!authToken.isEmpty()){
            QString bearer = "Bearer " + authToken;
            request.setRawHeader("Authorization", bearer.toUtf8());
        }

        QNetworkReply* reply = manager->post(request,QJsonDocument(obj).toJson());

        reply->ignoreSslErrors();

        connect(reply,&QNetworkReply::finished,&dialog,[=,&dialog](){
            if(reply->error() != QNetworkReply::NoError && reply->error() != QNetworkReply::SslHandshakeFailedError){
                QByteArray responseData = reply->readAll();
                QJsonDocument doc = QJsonDocument::fromJson(responseData);
                QString errorMessage = reply->errorString();

                if (doc.isObject() && doc.object().contains("message")) {
                    errorMessage = doc.object()["message"].toString();
                }
                QMessageBox::critical(&dialog,"Error", errorMessage);
            }
            else {
                refreshAuctions();
                dialog.accept();
            }
            reply->deleteLater();
        });
    });

    dialog.exec();
}

void AuctionTab::setCurrentUser(const QString &username)
{
    this->currentUser = username;
    qDebug() << "AuctionTab: Current user set to" << this->currentUser;
}

void AuctionTab::onPlaceBid()
{
    QListWidgetItem *item = listWidget->currentItem();
    if (!item) {
        QMessageBox::warning(this, "Warning", "Please select a lot first.");
        return;
    }

    int lotId = item->data(Qt::UserRole).toInt();
    if (lotId <= 0) {
        QMessageBox::warning(this, "Warning", "Failed to determine lot ID (Qt::UserRole).");
        return;
    }

    auto it = std::find_if(currentLots.begin(), currentLots.end(),
                           [lotId](const Lot &lot){ return lot.id == lotId; });

    if(it == currentLots.end()) {
        QMessageBox::critical(this, "Error", "Lot data not available.");
        return;
    }
    const Lot &lot = *it;

    if (lot.creator == currentUser) {
        QMessageBox::warning(this, "Warning", "You cannot place a bid on your own lot.");
        return;
    }

    QString amountStr = bidEdit->text().trimmed();
    bool okAmount = false;
    double amount = amountStr.toDouble(&okAmount);

    if (!okAmount || amount <= 0) {
        QMessageBox::warning(this, "Warning", "Enter a valid bid amount.");
        return;
    }


    if (!lot.bids.isEmpty()) {
        double currentMax = lot.getCurrentPrice();

        const Bid* highestBid = nullptr;
        for (const auto& bid : lot.bids) {
            if (bid.amount == currentMax) {
                highestBid = &bid;
            }
        }

        if (highestBid && highestBid->user == currentUser) {
            QMessageBox::warning(this, "Warning", "You are currently the highest bidder. You cannot bid against yourself.");
            return;
        }

        if (amount <= currentMax) {
            QMessageBox::warning(this, "Warning", QString("Your bid must be strictly higher than the current price (%1 ₴).").arg(currentMax, 0, 'f', 2));
            return;
        }
    } else {
        if (amount < lot.startingPrice) {
            QMessageBox::warning(this, "Warning", QString("Your bid must be at least the starting price (%1 ₴).").arg(lot.startingPrice, 0, 'f', 2));
            return;
        }
    }


    if (currentUser.isEmpty()) {
        QMessageBox::critical(this, "Login Error", "Could not determine current user. Please log in.");
        return;
    }

    QJsonObject obj;
    obj["lotId"] = lotId;
    obj["user"] = currentUser;
    obj["amount"] = amount;

    QNetworkRequest request(QUrl(serverUrl + "/bids/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    if (!authToken.isEmpty()) {
        QString bearer = "Bearer " + authToken;
        request.setRawHeader("Authorization", bearer.toUtf8());
    }


    QNetworkReply* reply = manager->post(request, QJsonDocument(obj).toJson());

    reply->ignoreSslErrors();

    connect(reply, &QNetworkReply::finished, [=]() {
        if (reply->error() != QNetworkReply::NoError && reply->error() != QNetworkReply::SslHandshakeFailedError) {
            QByteArray responseData = reply->readAll();
            QJsonDocument doc = QJsonDocument::fromJson(responseData);
            QString errorMessage = reply->errorString();


            if (doc.isObject() && doc.object().contains("message")) {
                errorMessage = doc.object()["message"].toString();
            }

            QMessageBox::critical(this, "Place Bid Error", errorMessage);
        } else {
            bidEdit->clear();
            QMessageBox::information(this, "Success", "Bid successfully placed!");
            refreshAuctions();
            emit bidSuccessful();
        }
        reply->deleteLater();
    });
}

void AuctionTab::onDeleteLot()
{
    QListWidgetItem *item = listWidget->currentItem();
    if (!item) return;

    int lotId = item->data(Qt::UserRole).toInt();
    if (lotId <= 0) {
        QMessageBox::critical(this, "Error", "Could not retrieve Lot ID.");
        return;
    }

    auto it = std::find_if(currentLots.begin(), currentLots.end(), [=](const Lot &lot){ return lot.id==lotId; });

    if(it==currentLots.end()) {
        QMessageBox::critical(this, "Error", "Lot not found in local list.");
        return;
    }

    if(it->creator != currentUser) {
        QMessageBox::critical(this, "Forbidden", "You can only delete your own lots.");
        return;
    }

    QMessageBox::StandardButton reply;
    reply = QMessageBox::question(this, "Confirm Deletion",
                                  QString("Are you sure you want to delete lot %1: '%2'? This action will also delete all bids.")
                                      .arg(lotId).arg(it->title),
                                  QMessageBox::Yes|QMessageBox::No);
    if (reply == QMessageBox::No) return;

    QNetworkRequest request(QUrl(serverUrl + QString("/auctions/%1/").arg(lotId)));

    if(!authToken.isEmpty()){
        QString bearer = "Bearer " + authToken;
        request.setRawHeader("Authorization", bearer.toUtf8());
    }

    QNetworkReply* replyNet = manager->deleteResource(request);

    replyNet->ignoreSslErrors();

    connect(replyNet, &QNetworkReply::finished, [=]() {
        if (replyNet->error() != QNetworkReply::NoError && replyNet->error() != QNetworkReply::SslHandshakeFailedError) {
            QByteArray responseData = replyNet->readAll();
            QJsonDocument doc = QJsonDocument::fromJson(responseData);
            QString errorMessage = replyNet->errorString();

            if (doc.isObject() && doc.object().contains("message")) {
                errorMessage = doc.object()["message"].toString();
            }
            QMessageBox::critical(this, "Error Deleting Lot", errorMessage);
        } else {
            QMessageBox::information(this, "Success", QString("Lot %1 successfully deleted.").arg(lotId));
            refreshAuctions();
        }
        replyNet->deleteLater();
    });
}

void AuctionTab::showAuctionWindow(int lotId)
{
    if (currentUser.isEmpty()) {
        QMessageBox::warning(this, "Forbidden", "You must be logged in to join an auction.");
        return;
    }

    LotWindow *lotWindow = new LotWindow(
        lotId,
        manager,
        authToken,
        currentUser,
        this
        );

    connect(lotWindow, &LotWindow::bidSuccessful, this, [=](){
        refreshAuctions();
        emit bidSuccessful();
    });

    lotWindow->exec();
    delete lotWindow;
}
