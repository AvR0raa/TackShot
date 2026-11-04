QT += core gui widgets svg network

CONFIG += c++17 windows
CONFIG -= console
TEMPLATE = app
TARGET = TackShot
VERSION = 1.0.0

DEFINES += APP_VERSION=\\\"1.0.0\\\" UNICODE _UNICODE

INCLUDEPATH += src

SOURCES += \
    src/main.cpp \
    src/config.cpp \
    src/hotkey.cpp \
    src/capture.cpp \
    src/annotate.cpp \
    src/overlay.cpp \
    src/pinwindow.cpp \
    src/hisimport.cpp \
    src/settingsdialog.cpp

HEADERS += \
    src/common.h \
    src/config.h \
    src/hotkey.h \
    src/capture.h \
    src/annotate.h \
    src/overlay.h \
    src/pinwindow.h \
    src/hisimport.h \
    src/settingsdialog.h

LIBS += -ld3d11 -ldxgi -lole32 -luuid -lshell32 -luser32 -lgdi32 -ldwmapi -ladvapi32

RC_ICONS = res/tackshot.ico
