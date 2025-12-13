#include "lot_window.h"

#include "../server_url.h"

#include <QVBoxLayout>

#include <QHBoxLayout>

#include <QJsonDocument>

#include <QJsonObject>

#include <QJsonArray>

#include <QMessageBox>

#include <QDebug>

#include <QCloseEvent>

#include <QNetworkRequest>

#include <QNetworkReply>

#include <QDateTime>

#include <QFrame>

#include <QListWidgetItem>


const QString LOT_WINDOW_QSS = R"(

    QDialog {

        background-color: #F0FFF0;

        color: #333333;

    }


    QLabel#titleLabel {

        color: #4CAF50;

        font-size: 20px;

        font-weight: bold;

        margin-bottom: 5px;

    }


    QLabel#descriptionLabel {

        font-size: 14px;

        font-style: italic;

        margin-bottom: 10px;

        text-align: center;

    }


    QLabel#timerLabel {

        font-size: 24px;

        font-weight: bold;

        color: #E60000;

        margin-top: 10px;

        margin-bottom: 10px;

    }


    QLabel {

        font-size: 14px;

    }



    QListWidget {

        border: 1px solid #B2DFDB;

        border-radius: 6px;

        background-color: #FFFFFF;

        min-height: 150px;

        padding: 5px;

    }

    QListWidget::item:selected {

        background: #B2DFDB;

        color: #333333;

    }



    QLineEdit {

        border: 1px solid #B2DFDB;

        border-radius: 6px;

        padding: 4px;

    }



    QPushButton {

        background-color: #A2D9CE;

        color: #004D40;

        border: 1px solid #79A39D;

        padding: 8px 15px;

        border-radius: 6px;

        font-weight: bold;

    }

    QPushButton:hover {

        background-color: #8CCDC4;

    }

)";





LotWindow::LotWindow(int lotId, QNetworkAccessManager* manager, const QString &token, const QString &currentUser, QWidget *parent)

    : QDialog(parent), lotId(lotId), manager(manager), authToken(token), currentUser(currentUser)

{

    setWindowTitle(QString("Auction Lot #%1").arg(lotId));

    resize(500, 650);

    this->setStyleSheet(LOT_WINDOW_QSS);



    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    mainLayout->setSpacing(10);



    lblTitle = new QLabel("Loading lot details...");

    lblTitle->setObjectName("titleLabel");

    lblTitle->setAlignment(Qt::AlignCenter);

    mainLayout->addWidget(lblTitle);




    lblDescription = new QLabel("");

    lblDescription->setObjectName("descriptionLabel");

    lblDescription->setAlignment(Qt::AlignCenter);

    mainLayout->addWidget(lblDescription);



    lblTimer = new QLabel("Time Remaining: --:--:--");

    lblTimer->setObjectName("timerLabel");

    lblTimer->setAlignment(Qt::AlignCenter);

    mainLayout->addWidget(lblTimer);





    QFrame *infoFrame = new QFrame(this);

    infoFrame->setStyleSheet("QFrame { padding: 5px; border: 1px solid #F0FFF0; }");

    QVBoxLayout *infoLayout = new QVBoxLayout(infoFrame);

    infoLayout->setContentsMargins(0,0,0,0);



    lblCurrentPrice = new QLabel("Current Price: 0.00 ₴");

    lblUsersCount = new QLabel("Users Present: ");



    infoLayout->addWidget(lblCurrentPrice);

    infoLayout->addWidget(lblUsersCount);

    mainLayout->addWidget(infoFrame);



    mainLayout->addWidget(new QLabel("Bid History:"));

    listBids = new QListWidget;

    mainLayout->addWidget(listBids);



    QHBoxLayout *bidLayout = new QHBoxLayout;

    editBidAmount = new QLineEdit;

    editBidAmount->setPlaceholderText("Enter your bid amount");

    bidLayout->addWidget(editBidAmount);



    btnPlaceBid = new QPushButton("Place Bid");

    btnPlaceBid->setFixedWidth(120);

    bidLayout->addWidget(btnPlaceBid);

    mainLayout->addLayout(bidLayout);



    mainLayout->addStretch();



    connect(btnPlaceBid, &QPushButton::clicked, this, &LotWindow::onPlaceBidClicked);



    refreshTimer = new QTimer(this);

    connect(refreshTimer, &QTimer::timeout, this, &LotWindow::fetchLotDetails);

    refreshTimer->start(3000);



    countdownTimer = new QTimer(this);

    connect(countdownTimer, &QTimer::timeout, this, &LotWindow::updateTimer);

    countdownTimer->start(1000);



    joinAuction();

    fetchLotDetails();

}



LotWindow::~LotWindow() {

    refreshTimer->stop();

    countdownTimer->stop();

}



void LotWindow::closeEvent(QCloseEvent *event) {

    leaveAuction();

    QDialog::closeEvent(event);

}





qint64 LotWindow::calculateRemainingSeconds() const

{

    if (currentLot.startTime.isEmpty() || currentLot.durationMinutes <= 0) return 0;



    QDateTime startTime = QDateTime::fromString(currentLot.startTime, Qt::ISODate);

    QDateTime endTime = startTime.addSecs(currentLot.durationMinutes * 60);

    QDateTime currentTime = QDateTime::currentDateTimeUtc();





    if (startTime.timeSpec() == Qt::UTC) {

        currentTime = QDateTime::currentDateTime();

        startTime = startTime.toLocalTime();

        endTime = endTime.toLocalTime();

    }



    qint64 remaining = currentTime.secsTo(endTime);



    if (remaining < 0) return 0;

    return remaining;

}





void LotWindow::updateTimer()

{

    qint64 remainingSeconds = calculateRemainingSeconds();



    if (remainingSeconds <= 0) {

        lblTimer->setText("Time Remaining: <span style='color: black;'>AUCTION CLOSED</span>");

        lblTimer->setStyleSheet("font-size: 24px; font-weight: bold; color: black;");

        btnPlaceBid->setEnabled(false);

        editBidAmount->setEnabled(false);

        return;

    }



    int hours = remainingSeconds / 3600;

    int minutes = (remainingSeconds % 3600) / 60;

    int seconds = remainingSeconds % 60;



    QString timeStr = QString("%1:%2:%3")

                          .arg(hours, 2, 10, QChar('0'))

                          .arg(minutes, 2, 10, QChar('0'))

                          .arg(seconds, 2, 10, QChar('0'));



    lblTimer->setText("Time Remaining: " + timeStr);

    lblTimer->setStyleSheet("font-size: 24px; font-weight: bold; color: #E60000;");

    btnPlaceBid->setEnabled(true);

    editBidAmount->setEnabled(true);

}





void LotWindow::displayLotDetails()

{

    lblTitle->setText(currentLot.title);



    lblDescription->setText(currentLot.description.isEmpty() ? "No description provided." : currentLot.description);





    double currentPrice = currentLot.getCurrentPrice();

    lblCurrentPrice->setText(QString("Current Price: <b>%1 ₴</b> (Starting: %2 ₴)")

                                 .arg(currentPrice, 0, 'f', 2)

                                 .arg(currentLot.startingPrice, 0, 'f', 2));



    lblUsersCount->setText(QString("Users Present: <b>%1</b>").arg(currentLot.usersPresent));



    listBids->clear();



    for (int i = currentLot.bids.size() - 1; i >= 0; --i) {

        const auto &b = currentLot.bids.at(i);

        QString bidText = QString("%1 | %2 ₴ | Time: %3")

                              .arg(b.user)

                              .arg(b.amount, 0, 'f', 2)

                              .arg(QDateTime::fromString(b.time, Qt::ISODate).toLocalTime().toString("hh:mm:ss"));

        QListWidgetItem *item = new QListWidgetItem(bidText);



        if (i == currentLot.bids.size() - 1) {

            item->setBackground(QBrush(QColor("#B2DFDB")));

        }



        listBids->addItem(item);

    }



    updateTimer();

}





void LotWindow::fetchLotDetails()

{


    QString url = QString(serverUrl + "/auctions/%1/").arg(lotId);



    QNetworkRequest request;

    request.setUrl(QUrl(url));



    if (!authToken.isEmpty()) {

        QString bearer = "Bearer " + authToken;

        request.setRawHeader("Authorization", bearer.toUtf8());

    }



    QNetworkReply *reply = manager->get(request);

    reply->ignoreSslErrors();


    connect(reply, &QNetworkReply::finished, [=]() {


        if (reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200 || reply->error() == QNetworkReply::SslHandshakeFailedError) {

            QByteArray data = reply->readAll();

            QJsonDocument doc = QJsonDocument::fromJson(data);

            QJsonObject obj = doc.object();



            if (obj.contains("id")) {



                currentLot.id = obj["id"].toInt();

                currentLot.title = obj["title"].toString();

                currentLot.description = obj["description"].toString();

                currentLot.startingPrice = obj["startingPrice"].toDouble();

                currentLot.startTime = obj["startTime"].toString();

                currentLot.durationMinutes = obj["durationMinutes"].toInt();



                currentLot.usersPresent = obj["usersPresent"].toInt();





                currentLot.bids.clear();

                QJsonArray bidsArray = obj["bids"].toArray();

                for(auto bidVal : bidsArray){

                    QJsonObject b = bidVal.toObject();

                    currentLot.bids.append({b["user"].toString(), b["amount"].toDouble(), b["createdAt"].toString()});

                }



                displayLotDetails();

            } else {

                QMessageBox::warning(this, "Error", "Invalid lot data from server.");

            }

        } else {

            QMessageBox::critical(this, "Error", QString("Failed to load lot: %1").arg(reply->errorString()));

            if (reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 404) {

                this->close();

            }

        }

        reply->deleteLater();

    });

}



void LotWindow::onPlaceBidClicked()
{
    if (calculateRemainingSeconds() <= 0) {
        QMessageBox::warning(this, "Forbidden", "Auction is closed.");
        return;
    }

    QString amountStr = editBidAmount->text().trimmed();
    bool okAmount=false; double amount = amountStr.toDouble(&okAmount);

    if(!okAmount || amount<=0){
        QMessageBox::warning(this,"Warning","Enter a valid bid amount.");
        return;
    }

    double currentPrice = currentLot.getCurrentPrice();

    if (!currentLot.bids.isEmpty()) {
        const auto &highestBid = currentLot.bids.last();
        if (highestBid.user == currentUser) {
            QMessageBox::warning(this, "Warning", "You are currently the highest bidder. You cannot bid against yourself.");
            return;
        }
    }

    if (amount <= currentPrice) {
        QMessageBox::warning(this, "Warning", QString("Your bid must be higher than the current price (%1 ₴).").arg(currentPrice, 0, 'f', 2));
        return;
    }

    QJsonObject obj;
    obj["lotId"] = lotId;
    obj["user"] = currentUser;
    obj["amount"] = amount;

    QNetworkRequest request(QUrl(serverUrl + "/bids/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    if(!authToken.isEmpty()){
        QString bearer = "Bearer " + authToken;
        request.setRawHeader("Authorization", bearer.toUtf8());
    }

    QNetworkReply* reply = manager->post(request, QJsonDocument(obj).toJson());

    reply->ignoreSslErrors();


    connect(reply, &QNetworkReply::finished, [=]() {
        int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        if (statusCode >= 200 && statusCode < 300) {
            editBidAmount->clear();
            QMessageBox::information(this, "Success", "Bid successfully placed!");
            fetchLotDetails();
            emit bidSuccessful();
        } else if (reply->error() != QNetworkReply::NoError && reply->error() != QNetworkReply::SslHandshakeFailedError) {
            QByteArray responseData = reply->readAll();
            QJsonDocument doc = QJsonDocument::fromJson(responseData);
            QString errorMessage = reply->errorString();

            if (doc.isObject() && doc.object().contains("message")) {
                errorMessage = doc.object()["message"].toString();
            }

            QMessageBox::critical(this, "Bid Error", errorMessage);
        } else {
            QByteArray responseData = reply->readAll();
            QJsonDocument doc = QJsonDocument::fromJson(responseData);
            QString errorMessage = QString("Server responded with error %1.").arg(statusCode);

            if (doc.isObject() && doc.object().contains("message")) {
                errorMessage = doc.object()["message"].toString();
            }
            QMessageBox::critical(this, "Bid Error", errorMessage);
        }

        reply->deleteLater();

    });
}



void LotWindow::joinAuction() {

    QNetworkRequest request(QUrl(serverUrl + "/auctions/join/"));

    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");



    if (!authToken.isEmpty()) {

        request.setRawHeader("Authorization", QString("Bearer %1").arg(authToken).toUtf8());

    }



    QJsonObject obj;

    obj["lotId"] = lotId;

    obj["user"] = currentUser;



    QNetworkReply *reply = manager->post(request, QJsonDocument(obj).toJson());

    reply->ignoreSslErrors();

}



void LotWindow::leaveAuction() {


    QNetworkRequest request(QUrl(serverUrl + "/auctions/leave/"));

    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");



    if (!authToken.isEmpty()) {

        request.setRawHeader("Authorization", QString("Bearer %1").arg(authToken).toUtf8());

    }



    QJsonObject obj;

    obj["lotId"] = lotId;

    obj["user"] = currentUser;



    QNetworkReply *reply = manager->post(request, QJsonDocument(obj).toJson());
    reply->ignoreSslErrors();

}
