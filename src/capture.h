#pragma once
#include <QImage>
#include <QRect>
#include <QString>

namespace capture {

// 抓取整个虚拟桌面（物理像素）。
// physicalRectOut 返回物理像素下的虚拟桌面矩形。
QImage captureVirtualDesktop(QRect* physicalRectOut, QString* error = nullptr);

// 仅用 Qt/GDI 兜底
QImage captureWithQt(QRect* physicalRectOut);

// 用 GDI BitBlt 抓一个小区域（录制用，比全屏回读快一个数量级）
QImage captureRect(const QRect& physicalRect);

// 当前是否可用 DXGI 桌面复制
bool dxgiAvailable();

// 原生窗口在屏幕坐标下的物理矩形（DPI 校验用）
QRect nativeWindowRect(quintptr hwnd);

// 上一次抓屏走的路径："dxgi" / "gdi"
QString lastPath();

// 进程/线程 DPI 感知状态描述
QString dpiAwarenessInfo();

// 去掉显示器输出里的黑边（分辨率小于面板、驱动不缩放时会有一圈黑），
// 返回被裁掉的像素数；rectInOut 同步收缩。
QRect trimBlackBorder(QImage& img, QRect rectIn);

// 窗口所在显示器在物理像素下的矩形
QRect nativeMonitorRect(quintptr hwnd);

} // namespace capture
