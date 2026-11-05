#pragma once

#include <QDialog>
#include <QImage>
#include <QString>
#include <QStringList>
#include <QVector>

#include "ocrline.h"

class QComboBox;
class QLabel;
class QPlainTextEdit;
class QPushButton;
class QShowEvent;
class QSplitter;
class QTabWidget;
class QWidget;

// 左侧识别图预览（自绘控件，实现见 ocrdialog.cpp）
class OcrPreview;
// 顶栏小徽标（backend / 行数 / 耗时）
class OcrBadge;

// 「识别结果」对话框的输入数据
struct OcrDialogInput {
    QImage           image;         // 原图
    QVector<OcrLine> lines;         // 识别行（文字 + 置信度 + 像素框）
    QString          backend;       // 识别后端名，例如 “PP-OCRv4”
    int              elapsedMs = 0; // 识别耗时（毫秒）
};

// 识别结果对话框：左边原图 + 识别框，右边「文字 / 译文 / LaTeX」三页
class OcrDialog : public QDialog {
    Q_OBJECT
public:
    explicit OcrDialog(const OcrDialogInput& in, QWidget* parent = nullptr);

    void setTranslated(const QStringList& translated);
    void setLatex(const QString& latex);
    void setBusy(bool busy, const QString& status);
    void setStatusText(const QString& status);

    QStringList sourceLines() const;
    QVector<OcrLine> lines() const;

    QString sourceLang() const;
    QString targetLang() const;
    QString modelId() const;

    void setSourceLang(const QString& lang);
    void setTargetLang(const QString& lang);
    void setModels(const QStringList& ids, const QString& current);
    void setOnlineAvailable(bool available);

signals:
    void translateRequested();
    void imageTranslateRequested();
    void copyRequested(const QString& text);
    void latexRequested();   // 首次切到 LaTeX 页时发出（公式识别懒加载）

protected:
    void showEvent(QShowEvent* e) override;

private:
    void buildUi();
    QWidget* makeHeader();
    QWidget* makeBody();
    QWidget* makeFooter();
    QWidget* makeTextPage();
    QWidget* makeTranslatedPage();
    QWidget* makeLatexPage();

    void applyTheme();
    void updateBadges();
    void updateButtons();
    void setCurrentLine(int index);
    void copyCurrentPage();
    QString currentPageText() const;

    static void fillLanguages(QComboBox* box);
    static void selectLanguage(QComboBox* box, const QString& lang);

    OcrDialogInput   m_in;
    QVector<OcrLine> m_lines;
    int  m_currentLine = -1;
    bool m_busy = false;
    bool m_online = true;
    bool m_shown = false;
    bool m_latexAsked = false;

    QWidget*    m_header = nullptr;
    QWidget*    m_footer = nullptr;
    QSplitter*  m_split = nullptr;
    OcrPreview* m_preview = nullptr;
    QTabWidget* m_tabs = nullptr;

    QPlainTextEdit* m_text = nullptr;
    QPlainTextEdit* m_translatedEdit = nullptr;
    QPlainTextEdit* m_latexEdit = nullptr;

    QComboBox* m_srcLang = nullptr;
    QComboBox* m_tgtLang = nullptr;
    QComboBox* m_model = nullptr;

    QPushButton* m_translateBtn = nullptr;
    QPushButton* m_imageBtn = nullptr;
    QPushButton* m_copyBtn = nullptr;

    QLabel* m_status = nullptr;

    OcrBadge* m_backendBadge = nullptr;
    OcrBadge* m_linesBadge = nullptr;
    OcrBadge* m_timeBadge = nullptr;
};
