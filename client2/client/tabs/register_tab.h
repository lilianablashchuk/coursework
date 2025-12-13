#ifndef REGISTER_TAB_H
#define REGISTER_TAB_H

#include <QWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QNetworkAccessManager>
#include <QString>

class RegisterTab : public QWidget
{
    Q_OBJECT
public:
    explicit RegisterTab(QWidget *parent = nullptr, QNetworkAccessManager* manager = nullptr);


    QString getAuthToken() const;

signals:
    void registrationSuccessful(const QString &username);

private slots:
    void registerUser();

private:
    QLineEdit *editUsername;
    QLineEdit *editPassword;
    QPushButton *btnRegister;
    QNetworkAccessManager* networkManager;

    QString authToken;
};

#endif // REGISTER_TAB_H
