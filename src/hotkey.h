#pragma once
#include <QObject>
#include <QAbstractNativeEventFilter>

class HotkeyManager : public QObject, public QAbstractNativeEventFilter {
    Q_OBJECT
public:
    explicit HotkeyManager(QObject* parent = nullptr);
    ~HotkeyManager() override;

    bool install(quint32 mods, quint32 vk);
    void uninstall();

    bool nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) override;

signals:
    void activated();

private:
    bool m_registered = false;
    static const int HOTKEY_ID = 0x5453;  // 'TS'
};
