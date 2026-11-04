#pragma once
#include <QColor>
#include <QObject>
#include <QString>

// 界面配色。深色/浅色两套，可跟随系统。
struct Palette {
    bool   dark = true;
    QColor windowBg;       // 设置窗背景
    QColor surface;        // 面板 / 工具条
    QColor surfaceAlt;     // 次级面板（列表、输入框底）
    QColor hover;
    QColor pressed;
    QColor text;
    QColor subText;
    QColor border;
    QColor accent;         // 主题蓝
    QColor accentText;
    QColor danger;
    QColor dim;            // 截图遮罩
    QColor shadow;
};

class Theme : public QObject {
    Q_OBJECT
public:
    enum Mode { System = 0, Light = 1, Dark = 2 };

    static Theme& instance();

    static void initFromConfig();          // 读取配置里的 appearance
    static void setMode(Mode m, bool save = true);
    static Mode mode();
    static bool isDark();
    static const Palette& p();

    static QString styleSheet();           // 全局 qApp 样式表
    static void applyGlobal();             // 应用到 QApplication
    static void refresh();                 // 重新判定系统主题并广播

signals:
    void changed();

private:
    Theme();
    static bool systemPrefersDark();

    Mode m_mode = System;
    bool m_dark = true;
    Palette m_pal;
    void rebuild();
};
