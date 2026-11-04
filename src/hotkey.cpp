#include "hotkey.h"
#include <QCoreApplication>
#include <QDebug>
#include <windows.h>

HotkeyManager::HotkeyManager(QObject* parent) : QObject(parent) {
    QCoreApplication::instance()->installNativeEventFilter(this);
}

HotkeyManager::~HotkeyManager() { uninstall(); }

bool HotkeyManager::install(quint32 mods, quint32 vk) {
    uninstall();
    if (vk == 0) return false;
    m_registered = RegisterHotKey(nullptr, HOTKEY_ID, mods | MOD_NOREPEAT, vk) != 0;
    if (!m_registered)
        qWarning() << "RegisterHotKey failed, error" << GetLastError();
    return m_registered;
}

void HotkeyManager::uninstall() {
    if (m_registered) {
        UnregisterHotKey(nullptr, HOTKEY_ID);
        m_registered = false;
    }
}

bool HotkeyManager::nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) {
    Q_UNUSED(result);
    if (eventType != "windows_generic_MSG") return false;
    MSG* msg = static_cast<MSG*>(message);
    if (msg->message == WM_HOTKEY && int(msg->wParam) == HOTKEY_ID) {
        emit activated();
        return true;
    }
    return false;
}
