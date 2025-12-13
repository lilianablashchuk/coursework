#include "rest_benchmark.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QCoreApplication>
#include <iostream>
#include <QDateTime>
#include <QTimer>
#include <QElapsedTimer>
#include <QDebug>


const QString serverUrl = "http://172.26.48.1:5000";


RestBenchmark::RestBenchmark(QObject *parent) : QObject(parent) {
    manager = new QNetworkAccessManager(this);
}

void RestBenchmark::logLatency(const QString& operation, bool success, const QString& errorDetails) {
    long long latency = benchmarkTimer.elapsed();

    if (success) {
        std::cout << qPrintable(QString("REST_%1_Latency: %2ms").arg(operation).arg(latency)) << std::endl;
    } else {
        std::cout << qPrintable(QString("REST_%1_Error_Time: %2ms, Details: %3").arg(operation).arg(latency).arg(errorDetails)) << std::endl;
    }
}

void RestBenchmark::runBenchmark(const QString& username, const QString& password, int lotIdToBid) {
    currentUser = username;
    currentToken = "";
    targetLotId = lotIdToBid;
    benchmarkTimer.start();

    step1_register();
}

void RestBenchmark::finishBenchmark(int exitCode) {
    emit finished(exitCode);
}


void RestBenchmark::step1_register() {
    benchmarkTimer.restart();
    QNetworkRequest request(QUrl(serverUrl + "/auth/register"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject json;
    json["username"] = currentUser;
    json["password"] = "password123";

    QNetworkReply *reply = manager->post(request, QJsonDocument(json).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        handleRegisterFinished(reply);
        reply->deleteLater();
    });
}

void RestBenchmark::handleRegisterFinished(QNetworkReply* reply) {
    QByteArray resp = reply->readAll();
    QJsonDocument doc = QJsonDocument::fromJson(resp);

    bool success = reply->error() == QNetworkReply::NoError || doc.object()["message"].toString().contains("exists", Qt::CaseInsensitive);

    if (success) {
        logLatency("Register", true);
        step2_login();
    } else {
        logLatency("Register", false, reply->errorString());
        finishBenchmark(1);
    }
}

void RestBenchmark::step2_login() {
    benchmarkTimer.restart();
    QNetworkRequest request(QUrl(serverUrl + "/auth/login"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject json;
    json["username"] = currentUser;
    json["password"] = "password123";

    QNetworkReply *reply = manager->post(request, QJsonDocument(json).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        handleLoginFinished(reply);
        reply->deleteLater();
    });
}

void RestBenchmark::handleLoginFinished(QNetworkReply* reply) {
    QByteArray resp = reply->readAll();
    QJsonDocument doc = QJsonDocument::fromJson(resp);
    QJsonObject obj = doc.object();

    if (reply->error() == QNetworkReply::NoError && obj.contains("token")) {
        logLatency("Login", true);
        currentToken = obj["token"].toString();

        step4_createLot();
    } else {
        logLatency("Login", false, obj["message"].toString());
        finishBenchmark(1);
    }
}

void RestBenchmark::step4_createLot() {
    benchmarkTimer.restart();

    QDateTime startTimeDt = QDateTime::currentDateTimeUtc().addSecs(-60);
    QString startTimeStr = startTimeDt.toString(Qt::ISODate);

    QJsonObject obj;
    obj["title"] = QString("BenchLot-%1").arg(QDateTime::currentSecsSinceEpoch());
    obj["description"] = "REST Benchmark Test Lot";
    obj["startingPrice"] = 100.00;
    obj["startTime"] = startTimeStr;
    obj["durationMinutes"] = 5;

    QNetworkRequest request(QUrl(serverUrl + "/auctions"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    request.setRawHeader("Authorization", QString("Bearer %1").arg(currentToken).toUtf8());

    QNetworkReply *reply = manager->post(request, QJsonDocument(obj).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        handleCreateLotFinished(reply);
        reply->deleteLater();
    });
}

void RestBenchmark::handleCreateLotFinished(QNetworkReply* reply) {
    bool success = reply->error() == QNetworkReply::NoError;
    if (success) {
        logLatency("CreateLot", true);
        step5_placeBid(1000.00);
    } else {
        logLatency("CreateLot", false, reply->errorString());
        finishBenchmark(1);
    }
}


void RestBenchmark::step5_placeBid(double amount) {
    benchmarkTimer.restart();

    QJsonObject obj;
    obj["lotId"] = targetLotId;
    obj["user"] = currentUser;
    obj["amount"] = amount;

    QNetworkRequest request(QUrl(serverUrl + "/bids"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    request.setRawHeader("Authorization", QString("Bearer %1").arg(currentToken).toUtf8());

    QNetworkReply *reply = manager->post(request, QJsonDocument(obj).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        handlePlaceBidFinished(reply);
        reply->deleteLater();
    });
}

void RestBenchmark::handlePlaceBidFinished(QNetworkReply* reply) {
    int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    bool success = reply->error() == QNetworkReply::NoError || statusCode == 400;

    if (success) {
        logLatency("PlaceBid", true);
        step3_getAuctions();
    } else {
        logLatency("PlaceBid", false, reply->errorString());
        finishBenchmark(1);
    }
}

void RestBenchmark::step3_getAuctions() {
    benchmarkTimer.restart();
    QNetworkRequest request(QUrl(serverUrl + "/auctions"));

    QNetworkReply *reply = manager->get(request);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        handleGetAuctionsFinished(reply);
        reply->deleteLater();
    });
}

void RestBenchmark::handleGetAuctionsFinished(QNetworkReply* reply) {
    bool success = reply->error() == QNetworkReply::NoError && QJsonDocument::fromJson(reply->readAll()).isArray();

    if (success) {
        logLatency("GetAuctions", true);
        finishBenchmark(0);
    } else {
        logLatency("GetAuctions", false, reply->errorString());
        finishBenchmark(1);
    }
}
