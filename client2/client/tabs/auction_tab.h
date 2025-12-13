#ifndef AUCTION_TAB_H
#define AUCTION_TAB_H

#include <QWidget>
#include <QNetworkAccessManager>
#include <QString>
#include <QList>
#include <QLineEdit>
#include <QPushButton>
#include <QComboBox>
#include <QListWidget>
#include <QLabel>
#include <QTimer>
#include <QComboBox>
#include <QDialog>


struct Bid {
    QString user;
    double amount;
    QString time;
};

struct Lot {
    int id;
    QString title;
    QString description;
    QString creator;
    QString createdAt;
    double startingPrice;
    int endTime;
    int usersPresent;


    QString startTime;
    int durationMinutes;

    QList<Bid> bids;

    double getCurrentPrice() const {
        double currentPrice = startingPrice;
        for (const auto &b : bids) {
            if (b.amount > currentPrice) {
                currentPrice = b.amount;
            }
        }
        return currentPrice;
    }
};

class AuctionTab : public QWidget
{
    Q_OBJECT
public:
    AuctionTab(QWidget *parent = nullptr, QNetworkAccessManager* manager = nullptr, QString currentUser="");


    void setCurrentUser(const QString &username);
    void setAuthToken(const QString &token);

signals:

    void bidSuccessful();
private:
    QString authToken;
QPushButton *deleteLotButton;
    QNetworkAccessManager *manager;
   QString currentUser;

    QLineEdit *filterEdit;
    QLineEdit *bidEdit;

    QPushButton *refreshButton;
    QPushButton *addLotButton;
    QPushButton *placeBidButton;

    QComboBox *filterCombo;
    QComboBox *sortCombo;

    QListWidget *listWidget;
    QListWidget *listBids;
    QLabel *statusLabel;

    QList<Lot> currentLots;
    QTimer *refreshTimer;
    QTimer *bidTimer;

    void updateList(int preserveRow=-1);
    void updateBidHistory(int row);

private slots:
    void refreshAuctions();
    void handleAuctionsReply(QNetworkReply* reply, int preserveRow);
    void onAddLot();
    void onPlaceBid();
    void onDeleteLot();
    void showAuctionWindow(int lotId);
};

#endif // AUCTION_TAB_H
