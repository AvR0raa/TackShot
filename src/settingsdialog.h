#pragma once
#include <QDialog>

class QLabel;
class QPlainTextEdit;
class QSpinBox;
class QKeySequenceEdit;
class QLineEdit;
class QComboBox;
class QCheckBox;
class QListWidget;
class QStackedWidget;
class QTimer;

class SettingsDialog : public QDialog {
    Q_OBJECT
public:
    explicit SettingsDialog(QWidget* parent = nullptr);

protected:
    void accept() override;

private:
    QWidget* makeShotPage();
    QWidget* makeOcrPage();
    QWidget* makeRecordPage();
    QWidget* makeTranslatePage();
    QWidget* makeOtherPage();
    void scheduleApply();
    void applyNow();
    void retranslatePlaceholders();

    bool m_loading = true;
    QTimer* m_applyTimer = nullptr;

    QListWidget*    m_nav = nullptr;
    QStackedWidget* m_pages = nullptr;

    QKeySequenceEdit* m_hotkey = nullptr;
    QLineEdit*        m_dir = nullptr;
    QComboBox*        m_fmt = nullptr;
    QCheckBox*        m_copy = nullptr;
    QCheckBox*        m_magnifier = nullptr;

    QComboBox*        m_recFmt = nullptr;
    QComboBox*        m_recAudio = nullptr;

    QComboBox*        m_trProvider = nullptr;
    QLineEdit*        m_trBase = nullptr;
    QLineEdit*        m_trModel = nullptr;
    QLineEdit*        m_trKey = nullptr;
    QComboBox*        m_trSource = nullptr;
    QComboBox*        m_trTarget = nullptr;
    QLabel*           m_trStatus = nullptr;
    QComboBox*        m_trFallback = nullptr;
    QLineEdit*        m_trFallbackKey = nullptr;
    QPlainTextEdit*   m_trGlossary = nullptr;
    QSpinBox*         m_trChunk = nullptr;

    QComboBox*        m_ocrBackend = nullptr;
    QCheckBox*        m_ocrFormula = nullptr;
    QComboBox*        m_visionProvider = nullptr;
    QLineEdit*        m_visionBase = nullptr;
    QLineEdit*        m_visionModel = nullptr;
    QLineEdit*        m_visionKey = nullptr;
    QLabel*           m_visionStatus = nullptr;

    QComboBox*        m_appearance = nullptr;
    QCheckBox*        m_autostart = nullptr;
};
