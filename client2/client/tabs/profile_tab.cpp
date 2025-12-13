#include "profile_tab.h"
#include "../server_url.h"
#include <QVBoxLayout>
#include <QLabel>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QDebug>
#include <QMessageBox>
#include <QNetworkAccessManager>
#include <QUrl>
#include <QFrame>
#include <QPushButton>

const QString PROFILE_CARD_QSS = R"(


    QWidget#profileTabWidget {
        background-color: #F0FFF0;
        font-family: "Segoe UI", "Helvetica", Arial, sans-serif;
        color: #333333;
    }

    QFrame#profileCardFrame {
        background-color: #FFFFFF;
        border: 1px solid #B2DFDB;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.08);
    }

    QLabel#userLabel {
        color: #4CAF50;
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 15px;
        padding: 5px 0;
        border-bottom: 2px solid #A2D9CE;
    }

    QLabel {
        color: #333333;
        font-size: 16px;
        font-weight: 600;
        margin-top: 10px;
        margin-bottom: 5px;
    }

    QListWidget#bidsListWidget {
        border: 1px solid #B2DFDB;
        border-radius: 6px;
        padding: 0;
        background-color: #FFFFFF;
        font-size: 14px;
        outline: none;
    }

    QListWidget#bidsListWidget::item {
        padding: 10px;
        color: #333333;
        border-bottom: 1px solid #E0F2F1;
    }

    QListWidget#bidsListWidget::item:selected {
        background: #B2DFDB;
        color: #333333;
    }

    QListWidget#bidsListWidget::item:hover {
        background: #E0F2F1;
    }

    QPushButton {
        background-color: #A2D9CE;
        color: #004D40;
        border: 1px solid #79A39D;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
        margin-top: 20px;
        min-height: 30px;
    }
    QPushButton:hover {
        background-color: #8CCDC4;
    }
    QPushButton:pressed {
        box-shadow: none;
    }
)";


ProfileTab::ProfileTab(QWidget *parent, QNetworkAccessManager* manager)
    : QWidget(parent), manager(manager)
{
    this->setObjectName("profileTabWidget");

    QVBoxLayout *outerLayout = new QVBoxLayout(this);
    outerLayout->setAlignment(Qt::AlignCenter);

    QFrame *cardFrame = new QFrame(this);
    cardFrame->setObjectName("profileCardFrame");
    cardFrame->setFixedWidth(500);

    QVBoxLayout *cardLayout = new QVBoxLayout(cardFrame);
    cardLayout->setContentsMargins(20, 20, 20, 20);
    cardLayout->setSpacing(10);

    lblUser = new QLabel("Please log in to view profile details", this);
    lblUser->setObjectName("userLabel");
    cardLayout->addWidget(lblUser);

    cardLayout->addWidget(new QLabel("Your recent bids:"));

    listBids = new QListWidget(this);
    listBids->setObjectName("bidsListWidget");
    listBids->setMinimumHeight(250);
    cardLayout->addWidget(listBids);

    QPushButton *btnLogOut = new QPushButton("Log Out", this);
    cardLayout->addWidget(btnLogOut);

    outerLayout->addWidget(cardFrame);
    outerLayout->addStretch();

    this->setStyleSheet(PROFILE_CARD_QSS);
}

void ProfileTab::setUserName(const QString &username)
{
    if (currentUser == username) return;

    currentUser = username;
    lblUser->setText(QString("Welcome, %1").arg(currentUser));

    loadUserBids();
}

void ProfileTab::loadUserBids()
{
    listBids->clear();
    if (currentUser.isEmpty() || !manager) {
        listBids->addItem("Login required or server manager is null.");
        return;
    }

    listBids->addItem("Loading bids...");


    QString url = QString(serverUrl + "/bids/user/%1/").arg(currentUser);
    QUrl targetUrl(url);
    QNetworkRequest request(targetUrl);

    QNetworkReply *reply = manager->get(request);

    reply->ignoreSslErrors();

    connect(reply, &QNetworkReply::finished, [=]() {
        listBids->clear();

        if (reply->error() != QNetworkReply::NoError && reply->error() != QNetworkReply::SslHandshakeFailedError) {
            QByteArray data = reply->readAll();
            QJsonDocument doc = QJsonDocument::fromJson(data);
            QString errorMessage = reply->errorString();

            if (doc.isObject() && doc.object().contains("message")) {
                errorMessage = doc.object()["message"].toString();
            }

            listBids->addItem(QString("Error loading bids: %1").arg(errorMessage));
        } else {
            QByteArray data = reply->readAll();
            QJsonDocument doc = QJsonDocument::fromJson(data);

            if (!doc.isArray()) {
                listBids->addItem("Error: Invalid server response format.");
                reply->deleteLater();
                return;
            }

            QJsonArray bidsArray = doc.array();
            if (bidsArray.isEmpty()) {
                listBids->addItem("You have not placed any bids yet.");
            } else {
                for (const QJsonValue &bidVal : bidsArray) {
                    QJsonObject bidObj = bidVal.toObject();

                    QString lotId = QString::number(bidObj["lotId"].toInt());
                    QString lotTitle = bidObj["lotTitle"].toString();
                    QString safeLotTitle = lotTitle.toHtmlEscaped();
                    QString amount = QString::number(bidObj["amount"].toDouble(), 'f', 2);

                    listBids->addItem(QString("Lot: %1 %2 | Bid:%3 ₴")
                                          .arg(lotId)
                                          .arg(safeLotTitle)
                                          .arg(amount));
                }
            }
        }

        reply->deleteLater();
    });
}
