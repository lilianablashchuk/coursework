#include "register_tab.h"
#include "../server_url.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QMessageBox>
#include <QFrame>
#include <QSpacerItem>

RegisterTab::RegisterTab(QWidget *parent, QNetworkAccessManager* manager)
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

    QLabel *title = new QLabel("New Account");
    title->setObjectName("titleLabel");
    title->setAlignment(Qt::AlignCenter);
    cardLayout->addWidget(title);

    cardLayout->addSpacing(15);

    QLabel *lblUsername = new QLabel("Username:");
    lblUsername->setStyleSheet(labelStyle);
    cardLayout->addWidget(lblUsername);

    editUsername = new QLineEdit(this);
    editUsername->setPlaceholderText("Enter your desired username");
    editUsername->setStyleSheet(lineEditStyle);
    cardLayout->addWidget(editUsername);

    QLabel *lblPassword = new QLabel("Password:");
    lblPassword->setStyleSheet(labelStyle);
    cardLayout->addWidget(lblPassword);

    editPassword = new QLineEdit(this);
    editPassword->setEchoMode(QLineEdit::Password);
    editPassword->setPlaceholderText("Enter a secure password");
    editPassword->setStyleSheet(lineEditStyle);
    cardLayout->addWidget(editPassword);

    btnRegister = new QPushButton("Register", this);

    QHBoxLayout *buttonCenterLayout = new QHBoxLayout();
    buttonCenterLayout->addStretch();
    btnRegister->setFixedWidth(200);
    buttonCenterLayout->addWidget(btnRegister);
    buttonCenterLayout->addStretch();

    cardLayout->addSpacing(20);
    cardLayout->addLayout(buttonCenterLayout);

    outerLayout->addWidget(cardFrame);

    outerLayout->addStretch();

    connect(btnRegister, &QPushButton::clicked, this, &RegisterTab::registerUser);
}

void RegisterTab::registerUser()
{
    if(editUsername->text().isEmpty() || editPassword->text().isEmpty()){
        QMessageBox::warning(this, "Input error", "Please fill all fields");
        return;
    }


    QNetworkRequest request(QUrl(serverUrl + "/auth/register/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject json;
    json["username"] = editUsername->text();
    json["password"] = editPassword->text();

    QNetworkReply *reply = networkManager->post(request, QJsonDocument(json).toJson());


    reply->ignoreSslErrors();

    connect(reply, &QNetworkReply::finished, [reply, this](){
        QByteArray resp = reply->readAll();
        reply->deleteLater();

        QJsonDocument doc = QJsonDocument::fromJson(resp);
        QJsonObject obj = doc.object();

        if ((reply->error() == QNetworkReply::NoError || reply->error() == QNetworkReply::SslHandshakeFailedError) &&
            obj.contains("status") && obj["status"] == "ok") {

            QString token = obj["token"].toString();
            this->authToken = token;

            emit registrationSuccessful(editUsername->text());

            editUsername->clear();
            editPassword->clear();

        } else if(obj.contains("message")) {
            QMessageBox::warning(this, "Register failed", obj["message"].toString());
        } else {

            if (reply->error() != QNetworkReply::SslHandshakeFailedError) {
                QMessageBox::warning(this, "Register failed", reply->errorString());
            } else {
                QMessageBox::warning(this, "Register failed", "Registration failed or unknown error occurred.");
            }
        }
    });
}

QString RegisterTab::getAuthToken() const
{
    return authToken;
}
