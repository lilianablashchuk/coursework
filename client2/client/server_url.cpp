#include "server_url.h"

#ifdef Q_OS_WIN

const QString serverUrl = "http://localhost:5000";
#else

const QString serverUrl = "http://172.26.48.1:5000";
#endif
