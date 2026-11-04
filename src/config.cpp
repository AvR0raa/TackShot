#include "config.h"
#include "common.h"
#include <windows.h>
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QKeySequence>
#include <QDebug>

Config::Config() {
    saveDir = QStandardPaths::writableLocation(QStandardPaths::PicturesLocation) + "/TackShot";
}

Config& Config::get() {
    static Config c;
    return c;
}

QString Config::dataDir() const {
    // 便携模式 / 自检用：可用环境变量重定向
    const QString override = qEnvironmentVariable("TACKSHOT_DATA_DIR");
    if (!override.isEmpty()) {
        QDir().mkpath(override);
        return override;
    }
    QString base = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    QDir().mkpath(base + "/" + TS_APP_NAME);
    return base + "/" + TS_APP_NAME;
}

QString Config::configPath() const { return dataDir() + "/config.json"; }

QString Config::hotkeyText() const {
    int qtKey = 0;
    if (hotkeyVk >= 'A' && hotkeyVk <= 'Z') qtKey = Qt::Key_A + (hotkeyVk - 'A');
    else if (hotkeyVk >= '0' && hotkeyVk <= '9') qtKey = Qt::Key_0 + (hotkeyVk - '0');
    else if (hotkeyVk >= VK_F1 && hotkeyVk <= VK_F24) qtKey = Qt::Key_F1 + (hotkeyVk - VK_F1);
    else if (hotkeyVk == VK_SNAPSHOT) qtKey = Qt::Key_Print;

    Qt::KeyboardModifiers m;
    if (hotkeyMods & 0x0002) m |= Qt::ControlModifier;
    if (hotkeyMods & 0x0001) m |= Qt::AltModifier;
    if (hotkeyMods & 0x0004) m |= Qt::ShiftModifier;
    if (hotkeyMods & 0x0008) m |= Qt::MetaModifier;
    if (qtKey == 0) return QString();
    return QKeySequence(qtKey | m).toString(QKeySequence::NativeText);
}

void Config::setHotkeyFromSequence(const QKeySequence& seq) {
    if (seq.isEmpty()) return;
    int key = seq[0].key();
    Qt::KeyboardModifiers m = seq[0].keyboardModifiers();
    quint32 vk = 0;
    if (key >= Qt::Key_A && key <= Qt::Key_Z) vk = 'A' + (key - Qt::Key_A);
    else if (key >= Qt::Key_0 && key <= Qt::Key_9) vk = '0' + (key - Qt::Key_0);
    else if (key >= Qt::Key_F1 && key <= Qt::Key_F24) vk = VK_F1 + (key - Qt::Key_F1);
    else if (key == Qt::Key_Print) vk = VK_SNAPSHOT;
    if (!vk) return;
    quint32 mods = 0;
    if (m & Qt::ControlModifier) mods |= 0x0002;
    if (m & Qt::AltModifier)     mods |= 0x0001;
    if (m & Qt::ShiftModifier)   mods |= 0x0004;
    if (m & Qt::MetaModifier)    mods |= 0x0008;
    hotkeyMods = mods;
    hotkeyVk = vk;
    emit changed();
}

QJsonObject Config::toJson() const {
    QJsonObject o;
    o["hotkeyMods"] = double(hotkeyMods);
    o["hotkeyVk"] = double(hotkeyVk);
    o["saveDir"] = saveDir;
    o["format"] = format;
    o["recordFormat"] = recordFormat;
    o["recordAudio"] = recordAudio;
    o["translateProvider"] = translateProvider;
    o["translateBaseUrl"] = translateBaseUrl;
    o["translateModel"] = translateModel;
    o["translateSource"] = translateSource;
    o["translateTarget"] = translateTarget;
    o["translatePrivacyAccepted"] = translatePrivacyAccepted;
    o["translateFallbackProvider"] = translateFallbackProvider;
    o["translateFallbackBaseUrl"] = translateFallbackBaseUrl;
    o["translateFallbackModel"] = translateFallbackModel;
    o["translateGlossary"] = translateGlossary;
    o["translateChunkChars"] = translateChunkChars;
    o["ocrBackend"] = ocrBackend;
    o["ocrFormula"] = ocrFormula;
    o["ocrPrivacyAccepted"] = ocrPrivacyAccepted;
    o["visionProvider"] = visionProvider;
    o["visionBaseUrl"] = visionBaseUrl;
    o["visionModel"] = visionModel;
    o["copyAfterCapture"] = copyAfterCapture;
    o["showCursorMagnifier"] = showCursorMagnifier;
    o["appearance"] = appearance;
    o["autoStart"] = autoStart;
    o["penWidth"] = penWidth;
    o["penColor"] = penColor;
    o["rectRadius"] = rectRadius;
    o["shadow"] = shadow;
    return o;
}

void Config::fromJson(const QJsonObject& o) {
    if (o.contains("hotkeyMods")) hotkeyMods = quint32(o["hotkeyMods"].toDouble());
    if (o.contains("hotkeyVk"))   hotkeyVk   = quint32(o["hotkeyVk"].toDouble());
    if (o.contains("saveDir"))    saveDir    = o["saveDir"].toString();
    if (o.contains("format"))     format     = o["format"].toString();
    if (o.contains("recordFormat")) recordFormat = o["recordFormat"].toString();
    if (o.contains("recordAudio")) recordAudio = o["recordAudio"].toString();
    if (o.contains("translateProvider")) translateProvider = o["translateProvider"].toString();
    if (o.contains("translateBaseUrl")) translateBaseUrl = o["translateBaseUrl"].toString();
    if (o.contains("translateModel")) translateModel = o["translateModel"].toString();
    if (o.contains("translateSource")) translateSource = o["translateSource"].toString();
    if (o.contains("translateTarget")) translateTarget = o["translateTarget"].toString();
    if (o.contains("translatePrivacyAccepted")) translatePrivacyAccepted = o["translatePrivacyAccepted"].toBool();
    if (o.contains("translateFallbackProvider")) translateFallbackProvider = o["translateFallbackProvider"].toString();
    if (o.contains("translateFallbackBaseUrl")) translateFallbackBaseUrl = o["translateFallbackBaseUrl"].toString();
    if (o.contains("translateFallbackModel")) translateFallbackModel = o["translateFallbackModel"].toString();
    if (o.contains("translateGlossary")) translateGlossary = o["translateGlossary"].toString();
    if (o.contains("translateChunkChars")) translateChunkChars = int(o["translateChunkChars"].toDouble());
    if (o.contains("ocrBackend")) ocrBackend = o["ocrBackend"].toString();
    if (o.contains("ocrFormula")) ocrFormula = o["ocrFormula"].toBool();
    if (o.contains("ocrPrivacyAccepted")) ocrPrivacyAccepted = o["ocrPrivacyAccepted"].toBool();
    if (o.contains("visionProvider")) visionProvider = o["visionProvider"].toString();
    if (o.contains("visionBaseUrl")) visionBaseUrl = o["visionBaseUrl"].toString();
    if (o.contains("visionModel")) visionModel = o["visionModel"].toString();
    if (o.contains("copyAfterCapture")) copyAfterCapture = o["copyAfterCapture"].toBool();
    if (o.contains("showCursorMagnifier")) showCursorMagnifier = o["showCursorMagnifier"].toBool();
    if (o.contains("appearance")) appearance = o["appearance"].toString();
    if (o.contains("autoStart")) autoStart = o["autoStart"].toBool();
    if (o.contains("penWidth")) penWidth = o["penWidth"].toDouble();
    if (o.contains("penColor")) penColor = o["penColor"].toString();
    if (o.contains("rectRadius")) rectRadius = o["rectRadius"].toDouble();
    if (o.contains("shadow")) shadow = o["shadow"].toBool();
}

void Config::load() {
    QFile f(configPath());
    if (f.open(QIODevice::ReadOnly)) {
        QJsonParseError e{};
        auto doc = QJsonDocument::fromJson(f.readAll(), &e);
        if (e.error == QJsonParseError::NoError && doc.isObject())
            fromJson(doc.object());
        f.close();
    } else {
        save();
    }
    if (saveDir.isEmpty())
        saveDir = QStandardPaths::writableLocation(QStandardPaths::PicturesLocation) + "/TackShot";
}

void Config::save() {
    QDir().mkpath(dataDir());
    QFile f(configPath());
    if (f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        f.write(QJsonDocument(toJson()).toJson(QJsonDocument::Indented));
        f.close();
    }
}
