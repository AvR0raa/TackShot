#pragma once
#include <QImage>
#include <QColor>
#include <QVector>
#include <QPointF>
#include <QString>
#include <QPainter>

enum class Tool {
    None = 0, Rect, Ellipse, Arrow, Line, Pen, Highlight, Mosaic, Text, Number, Select
};

struct Annotation {
    Tool type = Tool::None;
    QVector<QPointF> pts;      // 图像坐标
    QColor color = QColor("#ff3b30");
    qreal width = 3.0;
    QString text;
    int number = 0;
    bool filled = false;
};

namespace annot {

// 把标注画到 canvas 上（canvas 为选区图像，本地坐标）
void renderToImage(QImage& canvas, const QVector<Annotation>& list, int skipIndex = -1);

// 鼠标拖拽结束后生成一个标注
Annotation fromDrag(Tool t, const QPointF& a, const QPointF& b, const QColor& c, qreal w);

} // namespace annot
