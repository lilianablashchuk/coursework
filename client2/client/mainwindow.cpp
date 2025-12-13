#include "mainwindow.h"
#include "server_url.h"
#include <QMessageBox>
#include <QSqlDatabase>
#include <QSqlError>
#include <QVBoxLayout>
#include <QLabel>
#include <QJsonObject>
#include <QJsonDocument>
#include <QCloseEvent>
#include <QDebug>
#include <QCoreApplication>
#include <QSize>
#include "tabs/login_tab.h"
#include "tabs/register_tab.h"
#include "tabs/profile_tab.h"
#include "tabs/auction_tab.h"
#include <QNetworkReply>

const QString GLOBAL_STYLE_SHEET = R"(
    QWidget {
        background-color: #F0FFF0;
        color: #333333;
        font-size: 14px;
        font-family: "Segoe UI", "Helvetica", Arial, sans-serif;
    }

    QPushButton {
        background-color: #A2D9CE;
        color: #004D40;
        border: 1px solid #79A39D;
        padding: 10px 20px;
        border-radius: 8px;
        min-width: 100px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #8CCDC4;
    }
    QPushButton:pressed {
        background-color: #79A39D;
    }

    QTabWidget::pane {
        border: 1px solid #D3D3D3;
        top: -1px;
        background: #FFFFFF;
        border-radius: 8px;
    }
    QTabBar::tab {
        background: #EAEAEA;
        color: #555555;
        padding: 8px 15px;
        border: 1px solid #D3D3D3;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background: #FFFFFF;
        color: #4CAF50;
        border: 1px solid #B2DFDB;
        border-bottom-color: #FFFFFF;
    }

    QLineEdit {
        border: 1px solid #B2DFDB;
        border-radius: 6px;
        padding: 8px;
        background-color: #FFFFFF;
        selection-background-color: #A2D9CE;
        selection-color: #333333;
    }
    QListWidget, QComboBox {
        border: 1px solid #B2DFDB;
        border-radius: 6px;
        background-color: #FFFFFF;
        padding: 4px;
    }

    QListWidget::item:selected {
        background: #B2DFDB;
        color: #333333;
    }

    QLabel {
        background-color: transparent;
    }

    QLabel[objectName="titleLabel"] {
        color: #4CAF50;
        font-size: 32px;
        font-weight: bold;
        padding: 15px;
    }
)";


MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setWindowTitle("Auction Client");


    setFixedSize(QSize(800, 680));

    this->setStyleSheet(GLOBAL_STYLE_SHEET);

    networkManager = new QNetworkAccessManager(this);

    setupDatabase();
    setupTabs();
}

MainWindow::~MainWindow() {}

void MainWindow::setupDatabase()
{
    QString dbPath;

#ifdef Q_OS_WIN
    dbPath = QCoreApplication::applicationDirPath() + "/auction.db";
#else
    dbPath = "/mnt/c/Users/Liliana/Desktop/course1/client2/client/build/auction.db";
#endif

    db = QSqlDatabase::addDatabase("QSQLITE");
    db.setDatabaseName(dbPath);

    qDebug() << "Attempting to open DB at:" << dbPath;

    if(!db.open()){
        QMessageBox::critical(this, "DB Error", "Unable to open database file. Details: " + db.lastError().text());
        qDebug() << "FATAL DB ERROR:" << db.lastError().text();
        exit(1);
    }
    qDebug() << "Database opened successfully.";
}

void MainWindow::setupMainPage()
{
    mainPage = new QWidget;
    QVBoxLayout *layout = new QVBoxLayout(mainPage);
    layout->setAlignment(Qt::AlignCenter);
    layout->setSpacing(20);

    QLabel *title = new QLabel("REST Auction Client");
    title->setObjectName("titleLabel");
    layout->addWidget(title);

    btnLogin = new QPushButton("Go to Login");
    btnRegister = new QPushButton("Go to Register");
    btnProfile = new QPushButton("Go to Profile");
    btnAuction = new QPushButton("Go to Auction");

    layout->addWidget(btnLogin);
    layout->addWidget(btnRegister);
    layout->addWidget(btnProfile);
    layout->addWidget(btnAuction);


    connect(btnLogin, &QPushButton::clicked, [=](){ tabs->setCurrentIndex(2); });
    connect(btnRegister, &QPushButton::clicked, [=](){ tabs->setCurrentIndex(1); });
    connect(btnProfile, &QPushButton::clicked, [=](){ tabs->setCurrentIndex(3); });
    connect(btnAuction, &QPushButton::clicked, [=](){ tabs->setCurrentIndex(4); });
}

void MainWindow::setupTabs()
{
    tabs = new QTabWidget(this);
    setCentralWidget(tabs);

    setupMainPage();

    loginTab    = new LoginTab(this, networkManager);
    registerTab = new RegisterTab(this, networkManager);
    auctionTab = new AuctionTab(this, networkManager, currentUser);
    profileTab  = new ProfileTab(this, networkManager);

    connect(loginTab, &LoginTab::loginSuccessful, this, &MainWindow::handleLoginSuccess);
    connect(registerTab, &RegisterTab::registrationSuccessful, this, [=](const QString &username){
        QMessageBox::information(this, "Registration Success", "User " + username + " registered successfully. Please log in.");
        tabs->setCurrentIndex(2);
    });
    connect(auctionTab, &AuctionTab::bidSuccessful, profileTab, &ProfileTab::loadUserBids);

    tabs->addTab(mainPage, "Home");
    tabs->addTab(registerTab, "Register");
    tabs->addTab(loginTab, "Login");
    tabs->addTab(profileTab, "Profile");
    tabs->addTab(auctionTab, "Auction");

    tabs->setCurrentWidget(mainPage);
}

void MainWindow::handleLoginSuccess(const QString &username, const QString &token)
{
    qDebug() << "MainWindow: Login success signal received for user:" << username;
    this->currentUser = username;
    auctionTab->setCurrentUser(username);
    auctionTab->setAuthToken(token);
    profileTab->setUserName(username);
    tabs->setCurrentWidget(auctionTab);
    QMessageBox::information(this, "Login Success", "You have successfully logged in as: " + username);
}


void MainWindow::closeEvent(QCloseEvent *event)
{

    QNetworkRequest request(QUrl(serverUrl + "/client-disconnected/"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject json;
    json["dummy"] = 1;

    QNetworkReply *reply = networkManager->post(request, QJsonDocument(json).toJson());

    reply->ignoreSslErrors();

    QObject::connect(reply, &QNetworkReply::finished, [reply]() {

        reply->deleteLater();
    });

    event->accept();
}
