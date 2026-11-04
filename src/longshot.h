#pragma once
#include <QImage>

// 竖向滚动拼接：把新一帧接到画布下方
// 返回拼接后的画布；matched 表示是否找到重叠区域
namespace longshot {

// 竖向：新内容出现在下方
QImage appendFrame(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

// 横向：新内容出现在右侧（内部用转置复用竖向逻辑）
QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

// 自动判断方向：返回图，dir 输出 0=竖向 1=横向
QImage appendAuto(const QImage& canvas, const QImage& frame, int* dir, bool* matched);

} // namespace longshot
