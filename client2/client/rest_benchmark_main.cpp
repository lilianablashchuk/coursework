#include "rest_benchmark.h"
#include <QCoreApplication>
#include <iostream>
#include <QTimer>

int main(int argc, char *argv[]) {
    QCoreApplication a(argc, argv);

    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <username> <password> <lot_id_to_bid>" << std::endl;
        return 1;
    }

    QString username = argv[1];
    QString password = argv[2];
    int lotIdToBid = QString(argv[3]).toInt();

    if (lotIdToBid <= 0) {
        std::cerr << "Invalid lot ID or missing arguments." << std::endl;
        return 1;
    }

    RestBenchmark benchmark;

    QObject::connect(&benchmark, &RestBenchmark::finished, &a,
                     [&a](int exitCode) {
                         a.exit(exitCode);
                     });


    QTimer::singleShot(0, [&]() {
        benchmark.runBenchmark(username, password, lotIdToBid);
    });

    return a.exec();
}
