#pragma once

#include <QNetworkAccessManager>
#include <QObject>
#include <QCoreApplication>
#include <QElapsedTimer>

extern const QString serverUrl;

class RestBenchmark : public QObject {
    Q_OBJECT
public:
    explicit RestBenchmark(QObject *parent = nullptr);

    void runBenchmark(const QString& username, const QString& password, int lotIdToBid);

private:
    QNetworkAccessManager *manager;
    QString currentUser;
    QString currentToken;
    int targetLotId;

    QElapsedTimer benchmarkTimer;
    void logLatency(const QString& operation, bool success = true, const QString& errorDetails = "");

    void step1_register();
    void step2_login();
    void step3_getAuctions();
    void step4_createLot();
    void step5_placeBid(double amount);
    void finishBenchmark(int exitCode);

signals:
    void finished(int exitCode);

private slots:
    void handleRegisterFinished(QNetworkReply* reply);
    void handleLoginFinished(QNetworkReply* reply);
    void handleGetAuctionsFinished(QNetworkReply* reply);
    void handleCreateLotFinished(QNetworkReply* reply);
    void handlePlaceBidFinished(QNetworkReply* reply);
};
