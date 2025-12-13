#include "login_tab.h"
#include "../server_url.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QMessageBox>
#include <QFrame>
#include <QSpacerItem>

LoginTab::LoginTab(QWidget *parent, QNetworkAccessManager* manager)
    : QWidget(parent), networkManager(manager)
{

    QVBoxLayout *outerLayout = new QVBoxLayout(this);
    outerLayout->setAlignment(Qt::AlignCenter);

    QFrame *cardFrame = new QFrame(this);
    cardFrame->setFixedWidth(450);
    cardFrame->setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D3D3D3; border-radius: 10px; padding: 25px; }");

    QVBoxLayout *cardLayout = new QVBoxLayout(cardFrame);
    cardLayout->setSpacing(5);
    cardLayout->setAlignment(Qt::AlignTop | Qt::AlignHCenter);

    QString labelStyle = "QLabel { padding: 0px; margin-top: 10px; margin-bottom: 0px; }";
    QString lineEditStyle = "QLineEdit { padding: 4px; }";

    QLabel *title = new QLabel("User Login");
    title->setObjectName("titleLabel");
    title->setAlignment(Qt::AlignCenter);
    cardLayout->addWidget(title);

    cardLayout->addSpacing(15);

    QLabel *lblUsername = new QLabel("Username:");
    lblUsername->setStyleSheet(labelStyle);
    cardLayout->addWidget(lblUsername);

    editUsername = new QLineEdit(this);
    editUsername->setPlaceholderText("Enter your username");
    editUsername->setStyleSheet(lineEditStyle);
    cardLayout->addWidget(editUsername);

    QLabel *lblPassword = new QLabel("Password:");
    lblPassword->setStyleSheet(labelStyle);
    cardLayout->addWidget(lblPassword);

    editPassword = new QLineEdit(this);
    editPassword->setEchoMode(QLineEdit::Password);
    editPassword->setPlaceholderText("Enter your password");
    editPassword->setStyleSheet(lineEditStyle);
    cardLayout->addWidget(editPassword);

    btnLogin = new QPushButton("Login", this);

    QHBoxLayout *buttonCenterLayout = new QHBoxLayout();
    buttonCenterLayout->addStretch();
    btnLogin->setFixedWidth(200);
    buttonCenterLayout->addWidget(btnLogin);
    buttonCenterLayout->addStretch();

    cardLayout->addSpacing(20);
    cardLayout->addLayout(buttonCenterLayout);

    outerLayout->addWidget(cardFrame);

    outerLayout->addStretch();

    connect(btnLogin, &QPushButton::clicked, this, &LoginTab::login);
}

void LoginTab::login()
{
    if(editUsername->text().isEmpty() || editPassword->text().isEmpty()){
        QMessageBox::warning(this, "Input error", "Please fill all fields");
        return;
    }

    const QString username = editUsername->text();


    QNetworkRequest request(QUrl(serverUrl + "/auth/login/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject json;
    json["username"] = username;
    json["password"] = editPassword->text();

    QNetworkReply *reply = networkManager->post(request, QJsonDocument(json).toJson());


    reply->ignoreSslErrors();


    connect(reply, &QNetworkReply::finished, [reply, this, username](){
        QByteArray resp = reply->readAll();
        reply->deleteLater();

        QJsonDocument doc = QJsonDocument::fromJson(resp);
        QJsonObject obj = doc.object();


        if ((reply->error() == QNetworkReply::NoError || reply->error() == QNetworkReply::SslHandshakeFailedError) &&
            obj.contains("status") && obj["status"] == "ok") {

            QString token = obj["token"].toString();
            this->authToken = token;

            emit loginSuccessful(username, token);


            editUsername->clear();
            editPassword->clear();

        } else if(obj.contains("message")) {
            QMessageBox::warning(this, "Login failed", obj["message"].toString());
        } else {
            if (reply->error() != QNetworkReply::SslHandshakeFailedError) {
                QMessageBox::warning(this, "Login failed", reply->errorString());
            } else {
                QMessageBox::warning(this, "Login failed", "Authentication failed or unknown error occurred.");
            }
        }
    });
}


QString LoginTab::getAuthToken() const
{
    return authToken;
}
