include("C:/Users/Liliana/Desktop/course1/client2/.qt/QtDeploySupport.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/client-plugins.cmake" OPTIONAL)
set(__QT_DEPLOY_I18N_CATALOGS "qtbase")

qt6_deploy_runtime_dependencies(
    EXECUTABLE "C:/Users/Liliana/Desktop/course1/client2/client.exe"
    GENERATE_QT_CONF
)
