#pragma once
#include <QString>
#include <QObject>
#include <QJsonObject>

class Config : public QObject {
    Q_OBJECT
public:
    static Config& get();

    void load();
    void save();

    // 全局热键（Win32 修饰符 + 虚拟键）
    quint32 hotkeyMods = 0x0002 | 0x0001;  // MOD_CONTROL | MOD_ALT
    quint32 hotkeyVk   = 'A';
    QString hotkeyText() const;
    void setHotkeyFromSequence(const QKeySequence& seq);

    QString saveDir;
    QString format = "png";     // png / jpg / webp
    QString recordFormat = "mp4";   // mp4 / gif
    QString recordAudio = "system"; // none / system / mic / both

    // 翻译
    QString translateProvider = "deepseek";   // deepseek / gemini / custom
    QString translateBaseUrl;                  // 空 = 用预设
    QString translateModel;                    // 空 = 用预设
    QString translateSource = "English";       // 源语言（默认英文，可设“自动检测”）
    QString translateTarget = "简体中文";        // 目标语言
    bool translatePrivacyAccepted = false;
    QString translateFallbackProvider;            // 空 = 不降级
    QString translateFallbackBaseUrl;
    QString translateFallbackModel;
    QString translateGlossary;                    // 每行 "原文=译法"
    int translateChunkChars = 1500;
    // 识别（OCR）
    QString ocrBackend = "local";               // local / online / auto
    bool    ocrFormula = true;                  // 是否启用公式识别
    bool    ocrPrivacyAccepted = false;         // 在线识别隐私确认
    QString visionProvider = "gemini";          // 视觉模型 engine（复用 translate 预设体系）
    QString visionBaseUrl;                      // 空 = 用预设
    QString visionModel;                        // 空 = 用预设

    bool copyAfterCapture = true;
    bool showCursorMagnifier = true;
    QString appearance = "system";   // system / light / dark
    bool autoStart = false;

    // 标注默认样式（可被 PixPin 配置导入覆盖）
    qreal penWidth = 3.0;
    QString penColor = "#ff3b30";
    qreal rectRadius = 0.0;
    bool shadow = true;

    QString configPath() const;
    QString dataDir() const;      // %APPDATA%/TackShot

signals:
    void changed();

private:
    Config();
    QJsonObject toJson() const;
    void fromJson(const QJsonObject& o);
    void importPixPinIfPossible();
};
