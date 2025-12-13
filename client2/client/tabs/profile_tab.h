#ifndef PROFILE_TAB_H
#define PROFILE_TAB_H

#include <QWidget>
#include <QListWidget>

class QLabel;
class QNetworkAccessManager;

class ProfileTab : public QWidget
{
    Q_OBJECT
public:
    explicit ProfileTab(QWidget *parent = nullptr, QNetworkAccessManager* manager = nullptr);
    void setUserName(const QString &username);
     void loadUserBids();

private:
    QNetworkAccessManager *manager;
    QString currentUser;
    QLabel *lblUser;
    QListWidget *listBids;
};

#endif // PROFILE_TAB_H
