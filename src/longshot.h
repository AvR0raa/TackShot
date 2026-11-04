#pragma once
#include <QImage>

// 竖向滚动拼接：把新一帧接到画布下方
// 返回拼接后的画布；matched 表示是否找到重叠区域
namespace longshot {

// 竖向：新内容出现在下方
QImage appendFrame(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

// 横向：新内容出现在右侧（内部用转置复用竖向逻辑）
QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

// 估算 cur 相对 prev 的竖向位移（像素）：
//   > 0  内容上移（向下滚动），值即滚动距离
//   <= 0 内容下移（向上回滚）或几乎没动
//   INT_MIN 表示无法判断（尺寸不一致 / 找不到匹配）
int verticalShift(const QImage& prev, const QImage& cur);

// 自动判断方向：返回图，dir 输出 0=竖向 1=横向
QImage appendAuto(const QImage& canvas, const QImage& frame, int* dir, bool* matched);

} // namespace longshot
