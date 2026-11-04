#pragma once
#include <QString>
#include <QRect>

// 一行识别结果（文字 / 置信度 / 在原图中的像素框）
struct OcrLine {
    QString text;
    float   score = 0.0f;
    QRect   box;
};
