#pragma once
#include <QWidget>
#include <QImage>
#include <QRect>
#include <QVector>
#include <QPoint>
#include "annotate.h"
#include "ocrline.h"

class QToolButton;
class QSpinBox;
class QLabel;
class QScreen;

class Overlay : public QWidget {
    Q_OBJECT
public:
    Overlay(const QImage& shot, const QRect& physicalRect, qreal dpr, QWidget* parent = nullptr);
    ~Overlay() override;

    // 演示/自检用：设置一个固定选区并填充示例标注
    void demoSetup();
    QImage demoFinal() const { return renderFinal(); }

    // 自检钩子：设置工具、模拟鼠标、读取标注
    void demoSetTool(Tool t) { m_tool = t; updateToolButtons(); }
    void setTargetScreen(QScreen* s) { m_targetScreen = s; }
    void demoSelect(const QRect& sel) { m_sel = sel; m_phase = Editing; update(); }
    void demoSimPress(const QPoint& p);
    void demoSimMove(const QPoint& p);
    void demoSimRelease(const QPoint& p);
    int demoAnnotCount() const { return m_annots.size(); }
    Annotation demoAnnot(int i) const { return m_annots.value(i); }
    int demoSelected() const { return m_selected; }
    QRect demoSel() const { return m_sel; }
    int demoHitTest(const QPoint& p) const { return hitAnnot(toLocal(p)); }
    QPointF demoToLocal(const QPoint& p) const { return toLocal(p); }
    QRect demoAnnotBounds(int i) const { return m_annots.value(i).pts.isEmpty() ? QRect() : annotBounds(m_annots.value(i)).toRect(); }
    // 自检：返回 [初始, 撤销1, 撤销2, 重做1] 的标注数量
    QVector<int> demoUndoTest();

    // 把译文渲染回原图（译图功能，自检也会用）
    static QImage renderTranslated(const QImage& base, const QVector<OcrLine>& lines,
                                   const QStringList& translated);
    // 自检：把窗口坐标映射成图像坐标（与鼠标逻辑同一条路径）
    QPoint demoMapToImage(const QPoint& widgetPos) const { return toImage(widgetPos); }
    QRect  demoPhysicalRect() const { return m_physRect; }
    qreal  demoScale() const { return m_scale; }

signals:
    void closed();
    void pinRequested(const QImage& img);

protected:
    void paintEvent(QPaintEvent*) override;
    void showEvent(QShowEvent*) override;
    void mousePressEvent(QMouseEvent*) override;
    void mouseMoveEvent(QMouseEvent*) override;
    void mouseReleaseEvent(QMouseEvent*) override;
    void keyPressEvent(QKeyEvent*) override;

private slots:
    void onToolClicked(Tool t);
    void onPickColor();
    void onUndo();
    void onRedo();
    void onCopy();
    void onOcr();
    void onLongShot();
    void onRecord();
    void onSave();
    void onPin();
    void onClose();

private:
    enum Phase { Selecting, Editing };
    enum DragMode { DragNone, DragSelect, DragMove, DragResize, DragDraw, DragAnnot, DragAnnotResize };

    QRect selRectWidget() const;
    QImage selectionImage(bool withAnnotations = true) const;
    QImage renderFinal() const;
    void buildToolbar();
    void placeToolbar();
    void updateToolButtons();
    QPoint toImage(const QPoint& widgetPos) const;
    QPointF toLocal(const QPoint& widgetPos) const;   // 相对选区左上角
    int handleAt(const QPoint& pos) const;            // 0..7 手柄, -1 无
    void finishSelection();

    QScreen* m_targetScreen = nullptr;
    bool m_rebuilding = false;
    qreal m_fade = 1.0;   // 遮罩淡入进度（不动窗口透明度，避免 surface 缩放问题）
    QImage m_shot;
    QRect  m_physRect;
    qreal  m_scale = 1.0;      // shot 像素 / widget 像素
    Phase  m_phase = Selecting;

    QRect  m_sel;              // 图像坐标（相对 m_shot）
    QPoint m_dragStart;
    DragMode m_drag = DragNone;
    int    m_resizeHandle = -1;
    QRect  m_selStart;

    QVector<Annotation> m_annots;
    int      m_selected = -1;          // 当前选中的标注
    int      m_annotHandle = -1;       // 0..7 缩放手柄
    bool     m_movingAnnot = false;
    QRectF   m_annotStartBox;
    QVector<QPointF> m_annotPtsStart;
    QPoint   m_lastDragPos;
    QPointF  m_dragStartF;
    void     drawAnnotHandles(QPainter& p);
    QRectF   annotBounds(const Annotation& a) const;
    int      hitAnnot(const QPointF& local) const;
    QVector<QVector<Annotation>> m_hist;
    int m_histPos = -1;
    void pushHistory();
    int    m_undoLimit = 200;
    Tool   m_tool = Tool::None;
    QColor m_color;
    qreal  m_width = 3.0;
    int    m_numberCounter = 1;

    bool   m_drawing = false;
    Annotation m_current;

    QPoint m_cursor;
    bool   m_hasCursor = false;

    QWidget*    m_bar = nullptr;
    QVector<QToolButton*> m_toolButtons;
    QLabel*     m_widthLabel = nullptr;
    QLabel*     m_widthPreview = nullptr;
    void setWidth(int w);
    QToolButton* m_colorBtn = nullptr;
};
