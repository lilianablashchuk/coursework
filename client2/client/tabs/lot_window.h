#ifndef LOT_WINDOW_H
#define LOT_WINDOW_H

#include <QDialog>
#include <QLabel>
#include <QTimer>
#include <QNetworkAccessManager>
#include <QPushButton>
#include <QLineEdit>
#include <QListWidget>
#include <QDateTime>
#include <QUrl>
#include <QNetworkReply>
#include "./auction_tab.h"

class LotWindow : public QDialog
{
    Q_OBJECT

public:
    explicit LotWindow(int lotId, QNetworkAccessManager* manager, const QString &token, const QString &currentUser, QWidget *parent = nullptr);
    ~LotWindow();

private slots:
    void updateTimer();
    void fetchLotDetails();
    void onPlaceBidClicked();
    void joinAuction();
    void leaveAuction();
    void  closeEvent(QCloseEvent *event);

private:
    int lotId;
    QNetworkAccessManager *manager;
    QString authToken;
    QString currentUser;

    Lot currentLot;

    QLabel *lblTitle;
    QLabel *lblTimer;
    QLabel *lblDescription;
    QLabel *lblCurrentPrice;
    QLabel *lblUsersCount;
    QListWidget *listBids;
    QLineEdit *editBidAmount;
    QPushButton *btnPlaceBid;

    QTimer *refreshTimer;
    QTimer *countdownTimer;

    void displayLotDetails();
    qint64 calculateRemainingSeconds() const;

signals:
    void bidSuccessful();
};

#endif // LOT_WINDOW_H
