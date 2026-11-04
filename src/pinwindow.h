#pragma once
#include <QWidget>
#include <QImage>
#include <QRect>

class PinWindow : public QWidget {
    Q_OBJECT
public:
    explicit PinWindow(const QImage& img, QWidget* parent = nullptr);
    void placeAt(const QPoint& globalPos);
    void demoShowChrome() { m_hover = true; m_reveal = 1.0; m_hoverBtn = -1; update(); }

protected:
    void paintEvent(QPaintEvent*) override;
    void mousePressEvent(QMouseEvent*) override;
    void mouseMoveEvent(QMouseEvent*) override;
    void mouseReleaseEvent(QMouseEvent*) override;
    void wheelEvent(QWheelEvent*) override;
    void keyPressEvent(QKeyEvent*) override;
    void contextMenuEvent(QContextMenuEvent*) override;
    void mouseDoubleClickEvent(QMouseEvent*) override;
    void leaveEvent(QEvent*) override;

private:
    void saveToFile();
    void copyImage();
    void toggleOneToOne();
    QRect barRect() const;              // 标题条区域（悬停时显示）
    QPointF buttonPos(int index) const; // 0..3 从右到左
    int buttonAt(const QPoint& p) const;

    QImage m_img;
    QImage m_scaled;
    qreal  m_zoom = 1.0;
    bool   m_dragging = false;
    bool   m_dragBar = false;
    QPoint m_dragOffset;
    bool   m_hover = false;
    qreal  m_reveal = 1.0;              // 入场动画进度
    int    m_hoverBtn = -1;
    void updateSize();
};
