cmake_minimum_required(VERSION 3.19)
project(client LANGUAGES CXX)

find_package(Qt6 6 REQUIRED COMPONENTS Core Widgets Network Sql)


set(CLIENT_SOURCES
    main.cpp
    mainwindow.cpp
    mainwindow.h
    mainwindow.ui

    server_url.h
    server_url.cpp

    tabs/login_tab.h
    tabs/login_tab.cpp
    tabs/register_tab.h
    tabs/register_tab.cpp
    tabs/profile_tab.h
    tabs/profile_tab.cpp
    tabs/auction_tab.h
    tabs/auction_tab.cpp
    tabs/lot_window.h
    tabs/lot_window.cpp
)



qt_standard_project_setup()
qt_add_executable(client ${CLIENT_SOURCES})


if(WIN32 OR APPLE)
    set_target_properties(client PROPERTIES
        WIN32_EXECUTABLE ON
        MACOSX_BUNDLE ON
    )
endif()


target_link_libraries(client
    PRIVATE
        Qt::Core
        Qt::Widgets
        Qt::Network
        Qt::Sql
)


set(REST_BENCHMARK_SOURCES
    rest_benchmark_main.cpp
    rest_benchmark.cpp
    rest_benchmark.h
)


add_executable(rest_benchmark_app ${REST_BENCHMARK_SOURCES})


target_link_libraries(rest_benchmark_app
    PRIVATE
        Qt::Core
        Qt::Network
)

if(WIN32)
    target_compile_definitions(rest_benchmark_app PRIVATE QT_NO_GUI_LIB)
    # ВИПРАВЛЕННЯ: Видаляємо помилкову опцію лінкування Windows.
    # MinGW/GCC за замовчуванням створює консольну програму,
    # якщо не вказано інше (як WIN32_EXECUTABLE).
    # target_link_options(rest_benchmark_app PRIVATE /SUBSYSTEM:CONSOLE) <-- ЦЕЙ РЯДОК БУВ ПОМИЛКОВИМ
endif()

include(GNUInstallDirs)

install(FILES client_style.qss DESTINATION ${CMAKE_INSTALL_BINDIR})

install(TARGETS client
    BUNDLE  DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

install(TARGETS rest_benchmark_app
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

if(WIN32 OR APPLE)
    qt_generate_deploy_app_script(
        TARGET client
        OUTPUT_SCRIPT deploy_script
        NO_UNSUPPORTED_PLATFORM_ERROR
    )
    install(SCRIPT ${deploy_script})
endif()
