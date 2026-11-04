#include "theme.h"
#include "config.h"

#include <QApplication>
#include <QGuiApplication>
#include <QSettings>
#include <QStyleHints>
#include <QProxyStyle>
#include <QStyleOption>
#include <QPainterPath>
#include <QDir>
#include <QPainter>
#include <QPainterPath>
#include <QPixmap>

Theme& Theme::instance() {
    static Theme t;
    return t;
}

Theme::Theme() {
    rebuild();
}

bool Theme::systemPrefersDark() {
    // 1) Qt 自己的判定（6.5+，最可靠）
    if (QGuiApplication::styleHints()) {
        const Qt::ColorScheme cs = QGuiApplication::styleHints()->colorScheme();
        if (cs == Qt::ColorScheme::Dark) return true;
        if (cs == Qt::ColorScheme::Light) return false;
    }
    // 2) 回退：读注册表
    QSettings s("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                QSettings::NativeFormat);
    const int v = s.value("AppsUseLightTheme", 1).toInt();
    return v == 0;
}

void Theme::initFromConfig() {
    const QString a = Config::get().appearance;
    Mode m = System;
    if (a.compare("light", Qt::CaseInsensitive) == 0) m = Light;
    else if (a.compare("dark", Qt::CaseInsensitive) == 0) m = Dark;
    setMode(m, false);

    // 跟随系统时，系统主题变化要实时切换
    if (QGuiApplication::styleHints()) {
        QObject::connect(QGuiApplication::styleHints(), &QStyleHints::colorSchemeChanged,
                         &instance(), [](Qt::ColorScheme) {
                             if (instance().m_mode == System) {
                                 instance().rebuild();
                                 instance().applyGlobal();
                                 emit instance().changed();
                             }
                         });
    }
}

void Theme::setMode(Mode m, bool save) {
    instance().m_mode = m;
    if (save) {
        Config::get().appearance = (m == Light ? "light" : (m == Dark ? "dark" : "system"));
        Config::get().save();
    }
    instance().rebuild();
    instance().applyGlobal();
    emit instance().changed();
}

Theme::Mode Theme::mode() { return instance().m_mode; }
bool Theme::isDark() { return instance().m_dark; }
const Palette& Theme::p() { return instance().m_pal; }

void Theme::rebuild() {
    const bool dark = (m_mode == Dark) || (m_mode == System && systemPrefersDark());
    m_dark = dark;
    Palette& q = m_pal;
    q.dark = dark;
    if (dark) {
        q.windowBg    = QColor("#1b1d21");
        q.surface     = QColor(30, 32, 36, 247);
        q.surfaceAlt  = QColor("#25282d");
        q.hover       = QColor(255, 255, 255, 26);
        q.pressed     = QColor(255, 255, 255, 46);
        q.text        = QColor("#e8eaed");
        q.subText     = QColor("#9aa0a6");
        q.border      = QColor(255, 255, 255, 26);
        q.accent      = QColor("#2f6fed");
        q.accentText  = QColor("#ffffff");
        q.danger      = QColor("#ff453a");
        q.dim         = QColor(0, 0, 0);
        q.shadow      = QColor(0, 0, 0, 160);
    } else {
        q.windowBg    = QColor("#f6f7f9");
        q.surface     = QColor(255, 255, 255, 250);
        q.surfaceAlt  = QColor("#ffffff");
        q.hover       = QColor(0, 0, 0, 18);
        q.pressed     = QColor(0, 0, 0, 34);
        q.text        = QColor("#1f2328");
        q.subText     = QColor("#6a737d");
        q.border      = QColor(0, 0, 0, 38);
        q.accent      = QColor("#1f6feb");
        q.accentText  = QColor("#ffffff");
        q.danger      = QColor("#d1242f");
        q.dim         = QColor(0, 0, 0);
        q.shadow      = QColor(0, 0, 0, 60);
    }
}

class TsStyle : public QProxyStyle {
public:
    void drawPrimitive(PrimitiveElement pe, const QStyleOption* opt, QPainter* p,
                       const QWidget* w) const override {
        if (pe == PE_IndicatorCheckBox && opt && p) {
            const Palette& c = Theme::p();
            const bool on = (opt->state & State_On) != 0;
            const bool hover = (opt->state & State_MouseOver) != 0;
            const bool disabled = (opt->state & State_Enabled) == 0;
            QRectF r = QRectF(opt->rect).adjusted(0.5, 0.5, -0.5, -0.5);
            p->save();
            p->setRenderHint(QPainter::Antialiasing, true);
            QColor fill = on ? c.accent : (hover ? c.hover : c.surfaceAlt);
            QColor line = on ? c.accent : c.border;
            if (disabled) { fill.setAlpha(90); line.setAlpha(90); }
            p->setPen(QPen(line, 1.2));
            p->setBrush(fill);
            p->drawRoundedRect(r, 3.5, 3.5);
            if (on) {
                QPainterPath path;
                path.moveTo(r.left() + r.width() * 0.24, r.top() + r.height() * 0.52);
                path.lineTo(r.left() + r.width() * 0.44, r.top() + r.height() * 0.72);
                path.lineTo(r.left() + r.width() * 0.78, r.top() + r.height() * 0.28);
                QColor tick = c.accentText;
                if (disabled) tick.setAlpha(120);
                p->setPen(QPen(tick, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
                p->setBrush(Qt::NoBrush);
                p->drawPath(path);
            }
            p->restore();
            return;
        }
        QProxyStyle::drawPrimitive(pe, opt, p, w);
    }
};

static QString ensureCheckPixmap() {
    const Palette& c = Theme::p();
    QString dir = Config::get().dataDir() + "/theme";
    QDir().mkpath(dir);
    QString path = dir + QString("/check_%1.png").arg(c.dark ? "dark" : "light");
    QPixmap pm(30, 30);
    pm.fill(Qt::transparent);
    QPainter p(&pm);
    p.setRenderHint(QPainter::Antialiasing, true);
    p.setPen(Qt::NoPen);
    p.setBrush(c.accent);
    p.drawRoundedRect(QRectF(1, 1, 28, 28), 7, 7);
    QPainterPath check;
    check.moveTo(8, 15.5);
    check.lineTo(13, 20.5);
    check.lineTo(22, 9.5);
    p.setBrush(Qt::NoBrush);
    p.setPen(QPen(c.accentText, 2.4, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
    p.drawPath(check);
    p.end();
    if (pm.save(path)) return path;
    return QString();
}

QString Theme::styleSheet() {
    const Palette& c = p();
    const QString checkPath = ensureCheckPixmap();
    auto rgba = [](const QColor& col) {
        return QString("rgba(%1,%2,%3,%4)").arg(col.red()).arg(col.green())
            .arg(col.blue()).arg(col.alphaF(), 0, 'f', 3);
    };
    return QString(
        "QDialog, QWidget#tsPage { background: %1; color: %2; }"
        "QLabel { color: %2; }"
        "QLabel#tsSub { color: %3; }"
        "QLabel#tsWarn { color: #8a6d00; background: rgba(255,214,0,0.16);"
        "                border: 1px solid rgba(255,214,0,0.45); border-radius: 6px; padding: 6px 10px; }"
        "QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QKeySequenceEdit {"
        "  background: %4; color: %2; border: 1px solid %5; border-radius: 6px;"
        "  padding: 4px 8px; selection-background-color: %6; }"
        "QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QKeySequenceEdit:focus {"
        "  border-color: %6; }"
        "QComboBox::drop-down { border: 0; width: 18px; }"
        "QComboBox QAbstractItemView { background: %4; color: %2; border: 1px solid %5;"
        "  selection-background-color: %6; selection-color: %7; }"
        "QPushButton { background: %8; color: %2; border: 1px solid %5; border-radius: 6px;"
        "  padding: 5px 14px; }"
        "QPushButton:hover { background: %9; }"
        "QPushButton:pressed { background: %10; }"
        "QPushButton:default, QPushButton#tsPrimary { background: %6; color: %7; border: 0; }"
        "QCheckBox { color: %2; spacing: 8px; }"
        "QCheckBox::indicator { width: 15px; height: 15px; }"
        "QListWidget#tsNav { background: %12; border-right: 1px solid %5; }"
        "QListWidget { background: %11; color: %2; border: 0; outline: 0; }"
        "QListWidget::item { padding: 8px 10px; border-radius: 6px; margin: 2px 6px; }"
        "QListWidget::item:hover { background: %9; }"
        "QListWidget::item:selected { background: %6; color: %7; }"
        "QMenu { background: %1; color: %2; border: 1px solid %5; padding: 4px; }"
        "QMenu::item { padding: 6px 24px 6px 10px; border-radius: 5px; }"
        "QMenu::item:selected { background: %6; color: %7; }"
        "QMenu::separator { height: 1px; background: %5; margin: 4px 8px; }"
        "QToolTip { background: %1; color: %2; border: 1px solid %5; padding: 4px 6px; }"
        "QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }"
        "QScrollBar::handle:vertical { background: %5; border-radius: 4px; min-height: 24px; }"
        "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }")
        .arg(rgba(c.windowBg), rgba(c.text), rgba(c.subText), rgba(c.surfaceAlt),
             rgba(c.border), rgba(c.accent), rgba(c.accentText), rgba(c.surface),
             rgba(c.hover), rgba(c.pressed), rgba(c.surfaceAlt), rgba(c.windowBg));
}

void Theme::applyGlobal() {
    if (!qApp) return;
    static bool styleInstalled = false;
    if (!styleInstalled) {
        qApp->setStyle(new TsStyle);
        styleInstalled = true;
    }
    qApp->setStyleSheet(styleSheet());
}

void Theme::refresh() {
    instance().rebuild();
    instance().applyGlobal();
    emit instance().changed();
}
