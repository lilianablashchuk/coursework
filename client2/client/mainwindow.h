#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTabWidget>
#include <QSqlDatabase>
#include <QPushButton>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>

class LoginTab;
class RegisterTab;
class ProfileTab;
class AuctionTab;

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();


protected:
    void closeEvent(QCloseEvent *event) override;

private slots:
    void handleLoginSuccess(const QString &username, const QString &token);


private:
    QTabWidget *tabs;
    QSqlDatabase db;

    QWidget *mainPage;
    QPushButton *btnLogin;
    QPushButton *btnRegister;
    QPushButton *btnProfile;
    QPushButton *btnAuction;

    QString currentUser;
    LoginTab *loginTab;
    AuctionTab *auctionTab;
    RegisterTab *registerTab;
    ProfileTab *profileTab;

    QNetworkAccessManager *networkManager;

    void setupDatabase();
    void setupTabs();
    void setupMainPage();
};

#endif // MAINWINDOW_H
