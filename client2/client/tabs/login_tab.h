#ifndef LOGIN_TAB_H
#define LOGIN_TAB_H

#include <QWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QNetworkAccessManager>
#include <QString>

class LoginTab : public QWidget
{
    Q_OBJECT
public:
    explicit LoginTab(QWidget *parent = nullptr, QNetworkAccessManager* manager = nullptr);
    QString getAuthToken() const;

signals:
    void loginSuccessful(const QString &username, const QString &token);

private slots:
    void login();

private:
    QLineEdit *editUsername;
    QLineEdit *editPassword;
    QPushButton *btnLogin;
    QNetworkAccessManager* networkManager;
    QString authToken;
};

#endif // LOGIN_TAB_H
