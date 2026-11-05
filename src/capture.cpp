#include "capture.h"
#include <QGuiApplication>
#include <QScreen>
#include <QPixmap>
#include <QDebug>
#include <QVector>
#include <QPainter>
#include <cstring>
#include <cmath>

#include <windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>

namespace {

struct Surface {
    QRect rect;     // 物理像素，虚拟桌面坐标
    QImage image;
};

// half float (f16) -> float，无依赖手写解码
inline float halfToFloat(quint16 h) {
    const quint32 sign = (h >> 15) & 1;
    const quint32 exp = (h >> 10) & 0x1F;
    const quint32 man = h & 0x3FF;
    float v;
    if (exp == 0) {
        v = std::ldexp(float(man), -24);           // 次正规
    } else if (exp == 31) {
        v = man ? NAN : INFINITY;
    } else {
        v = std::ldexp(float((man | 0x400)), int(exp) - 25);
    }
    return sign ? -v : v;
}

// 线性 scRGB [0..1+] -> sRGB 8bit（简单 tone map：超亮部 clamp）
inline quint8 scToSrgb8(float lin) {
    if (!(lin > 0.0f)) return 0;
    if (lin > 1.0f) lin = 1.0f;
    const float s = lin <= 0.0031308f ? lin * 12.92f
                                        : 1.055f * std::pow(lin, 1.0f / 2.4f) - 0.055f;
    return quint8(s * 255.0f + 0.5f);
}

} // namespace

namespace capture {

static QString g_lastPath = QStringLiteral("none");

// duplication 纹理行 -> ARGB32 行。返回 false 表示不支持的格式（走 GDI 兜底）。
// （导出到 capture:: 供 --capture-selftest 验证 HDR/10bit 转换）
bool convertDuplicationRow(QImage& img, int y, const uchar* src, unsigned width,
                           unsigned rowPitch, int dxgiFormat) {
    const DXGI_FORMAT fmt = DXGI_FORMAT(dxgiFormat);
    switch (fmt) {
    case DXGI_FORMAT_B8G8R8A8_UNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM_SRGB:
        std::memcpy(img.scanLine(y), src + size_t(y) * rowPitch, size_t(width) * 4);
        return true;
    case DXGI_FORMAT_R16G16B16A16_FLOAT: {   // HDR / 高级色彩：8 字节/像素 half float
        const quint16* s = reinterpret_cast<const quint16*>(src + size_t(y) * rowPitch);
        QRgb* d = reinterpret_cast<QRgb*>(img.scanLine(y));
        for (UINT x = 0; x < width; ++x) {
            const float r = halfToFloat(s[x * 4 + 0]);
            const float g = halfToFloat(s[x * 4 + 1]);
            const float b = halfToFloat(s[x * 4 + 2]);
            d[x] = qRgb(scToSrgb8(r), scToSrgb8(g), scToSrgb8(b));
        }
        return true;
    }
    case DXGI_FORMAT_R10G10B10A2_UNORM: {    // 10bit 面板
        const quint32* s = reinterpret_cast<const quint32*>(src + size_t(y) * rowPitch);
        QRgb* d = reinterpret_cast<QRgb*>(img.scanLine(y));
        for (UINT x = 0; x < width; ++x) {
            const quint32 v = s[x];
            d[x] = qRgb(quint8(((v >> 0) & 0x3FF) >> 2),
                        quint8(((v >> 10) & 0x3FF) >> 2),
                        quint8(((v >> 20) & 0x3FF) >> 2));
        }
        return true;
    }
    default:
        return false;
    }
}

// 近全黑检测（抽样）：>99.5% 像素 qGray<8 视为黑帧
bool isAlmostBlack(const QImage& img) {
    if (img.isNull()) return true;
    long long dark = 0, total = 0;
    for (int y = 0; y < img.height(); y += 7) {
        const QRgb* line = reinterpret_cast<const QRgb*>(img.constScanLine(y));
        for (int x = 0; x < img.width(); x += 7) {
            if (qGray(line[x]) < 8) ++dark;
            ++total;
        }
    }
    return total > 0 && dark * 1000 >= total * 995;
}

QImage compose(const QVector<Surface>& surfaces, QRect& virtualRect) {
    if (surfaces.isEmpty()) return QImage();
    QRect v;
    for (const auto& s : surfaces) v = v.united(s.rect);
    virtualRect = v;
    QImage canvas(v.size(), QImage::Format_ARGB32);
    canvas.fill(Qt::black);
    QPainter p(&canvas);
    for (const auto& s : surfaces)
        p.drawImage(s.rect.topLeft() - v.topLeft(), s.image);
    p.end();
    return canvas;
}

bool grabOutputDesktop(ID3D11Device* dev, ID3D11DeviceContext* ctx, IDXGIOutput* out, Surface& result) {
    IDXGIOutput1* out1 = nullptr;
    if (FAILED(out->QueryInterface(__uuidof(IDXGIOutput1), (void**)&out1)) || !out1)
        return false;

    HRESULT hr = E_FAIL;
    IDXGIOutputDuplication* dup = nullptr;
    hr = out1->DuplicateOutput(dev, &dup);
    out1->Release();
    if (FAILED(hr) || !dup) return false;

    IDXGIResource* res = nullptr;
    DXGI_OUTDUPL_FRAME_INFO frameInfo{};
    for (int attempt = 0; attempt < 3 && !res; ++attempt) {
        hr = dup->AcquireNextFrame(attempt == 0 ? 300 : 700, &frameInfo, &res);
        if (hr == DXGI_ERROR_WAIT_TIMEOUT) continue;
        if (FAILED(hr)) break;
    }
    if (!res) { dup->Release(); return false; }

    bool ok = false;
    ID3D11Texture2D* tex = nullptr;
    if (SUCCEEDED(res->QueryInterface(__uuidof(ID3D11Texture2D), (void**)&tex)) && tex) {
        D3D11_TEXTURE2D_DESC desc{};
        tex->GetDesc(&desc);
        const DXGI_FORMAT srcFmt = desc.Format;
        desc.Usage = D3D11_USAGE_STAGING;
        desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        desc.BindFlags = 0;
        desc.MiscFlags = 0;
        desc.ArraySize = 1;
        desc.MipLevels = 1;
        ID3D11Texture2D* staging = nullptr;
        if (SUCCEEDED(dev->CreateTexture2D(&desc, nullptr, &staging)) && staging) {
            ctx->CopyResource(staging, tex);
            D3D11_MAPPED_SUBRESOURCE map{};
            if (SUCCEEDED(ctx->Map(staging, 0, D3D11_MAP_READ, 0, &map))) {
                QImage img(int(desc.Width), int(desc.Height), QImage::Format_ARGB32);
                const uchar* src = static_cast<const uchar*>(map.pData);
                bool conv = true;
                for (UINT y = 0; y < desc.Height && conv; ++y)
                    conv = convertDuplicationRow(img, int(y), src, desc.Width,
                                                  map.RowPitch, int(srcFmt));
                ctx->Unmap(staging, 0);

                DXGI_OUTPUT_DESC od{};
                out->GetDesc(&od);
                result.rect = QRect(od.DesktopCoordinates.left, od.DesktopCoordinates.top,
                                    od.DesktopCoordinates.right - od.DesktopCoordinates.left,
                                    od.DesktopCoordinates.bottom - od.DesktopCoordinates.top);
                result.image = img;
                ok = conv;
            }
            staging->Release();
        }
        tex->Release();
    }
    dup->ReleaseFrame();
    res->Release();
    dup->Release();

    // 黑帧防护：部分驱动/双显卡首帧为黑，或格式不支持得到坏图时，
    // 用 GDI 交叉验证——GDI 有内容而 duplication 全黑则采用 GDI（真黑桌面 GDI 也黑，不误伤）
    if (ok && isAlmostBlack(result.image)) {
        QImage gdi = capture::captureRect(result.rect);
        if (!gdi.isNull() && gdi.size() == result.image.size() && !isAlmostBlack(gdi))
            result.image = gdi;
    }
    return ok;
}

bool dxgiAvailable() {
    ID3D11Device* dev = nullptr;
    D3D_FEATURE_LEVEL fl;
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0,
                                   D3D11_SDK_VERSION, &dev, &fl, nullptr);
    if (dev) dev->Release();
    return SUCCEEDED(hr);
}

QImage captureWithQt(QRect* physicalRectOut) {
    g_lastPath = QStringLiteral("gdi");
    QVector<Surface> surfaces;
    for (QScreen* s : QGuiApplication::screens()) {
        const qreal dpr = s->devicePixelRatio();
        QRect g = s->geometry();
        QRect phys(QPoint(qRound(g.x() * dpr), qRound(g.y() * dpr)),
                   QSize(qRound(g.width() * dpr), qRound(g.height() * dpr)));
        // 优先用 GDI 直接按物理像素抓（BitBlt 走的是物理坐标系）
        QImage img = captureRect(phys);
        if (img.isNull() || img.size() != phys.size()) {
            QPixmap pm = s->grabWindow(0);
            if (pm.isNull()) continue;
            QImage alt = pm.toImage();
            if (alt.size() != phys.size())
                alt = alt.scaled(phys.size(), Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
            img = alt;
        }
        surfaces.push_back({phys, img});
    }
    QRect v;
    QImage img = compose(surfaces, v);
    if (physicalRectOut) *physicalRectOut = v;
    return img;
}

QImage captureRect(const QRect& r) {
    if (r.width() <= 0 || r.height() <= 0) return QImage();
    HDC screen = GetDC(nullptr);
    if (!screen) return QImage();
    HDC mem = CreateCompatibleDC(screen);
    BITMAPINFO bi{};
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = r.width();
    bi.bmiHeader.biHeight = -r.height();
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    void* bits = nullptr;
    HBITMAP bmp = CreateDIBSection(screen, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
    QImage img;
    if (bmp && bits) {
        HGDIOBJ old = SelectObject(mem, bmp);
        BOOL ok = BitBlt(mem, 0, 0, r.width(), r.height(), screen, r.x(), r.y(), SRCCOPY | CAPTUREBLT);
        if (!ok)   // 部分驱动/远程会话不支持 CAPTUREBLT（叠加层采集），去掉重试
            ok = BitBlt(mem, 0, 0, r.width(), r.height(), screen, r.x(), r.y(), SRCCOPY);
        SelectObject(mem, old);
        if (ok) {
            QImage tmp(static_cast<uchar*>(bits), r.width(), r.height(), r.width() * 4,
                       QImage::Format_ARGB32);
            img = tmp.copy();
        }
        DeleteObject(bmp);
    }
    DeleteDC(mem);
    ReleaseDC(nullptr, screen);
    return img;
}

QImage captureVirtualDesktop(QRect* physicalRectOut, QString* error) {
    QVector<Surface> surfaces;
    QString err;

    ID3D11Device* dev = nullptr;
    ID3D11DeviceContext* ctx = nullptr;
    D3D_FEATURE_LEVEL fl;
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr,
                                   D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0,
                                   D3D11_SDK_VERSION, &dev, &fl, &ctx);
    if (SUCCEEDED(hr) && dev && ctx) {
        IDXGIFactory1* factory = nullptr;
        hr = CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)&factory);
        if (SUCCEEDED(hr) && factory) {
            for (UINT ai = 0;; ++ai) {
                IDXGIAdapter1* ad = nullptr;
                if (factory->EnumAdapters1(ai, &ad) == DXGI_ERROR_NOT_FOUND) break;
                if (!ad) break;
                for (UINT oi = 0;; ++oi) {
                    IDXGIOutput* out = nullptr;
                    if (ad->EnumOutputs(oi, &out) == DXGI_ERROR_NOT_FOUND) break;
                    if (!out) break;
                    Surface s;
                    if (!grabOutputDesktop(dev, ctx, out, s)) {
                        // 双显卡（Optimus 等）：默认设备与该输出不在同一适配器时
                        // DuplicateOutput 返回 UNSUPPORTED -> 用输出所在适配器重建设备重试
                        ID3D11Device* dev2 = nullptr;
                        ID3D11DeviceContext* ctx2 = nullptr;
                        D3D_FEATURE_LEVEL fl2;
                        if (SUCCEEDED(D3D11CreateDevice(ad, D3D_DRIVER_TYPE_UNKNOWN, nullptr,
                                                        D3D11_CREATE_DEVICE_BGRA_SUPPORT,
                                                        nullptr, 0, D3D11_SDK_VERSION,
                                                        &dev2, &fl2, &ctx2)) && dev2 && ctx2) {
                            grabOutputDesktop(dev2, ctx2, out, s);
                            ctx2->Release();
                            dev2->Release();
                        }
                    }
                    if (!s.image.isNull())
                        surfaces.push_back(s);
                    out->Release();
                }
                ad->Release();
            }
            factory->Release();
        }
    }
    if (dev) dev->Release();
    if (ctx) ctx->Release();

    // 覆盖度检查：未被 DXGI 覆盖的屏幕用 Qt 兜底
    QRect covered;
    for (const auto& s : surfaces) covered = covered.united(s.rect);
    bool complete = true;
    for (QScreen* s : QGuiApplication::screens()) {
        const qreal dpr = s->devicePixelRatio();
        QRect g = s->geometry();
        QRect pr(QPoint(qRound(g.x() * dpr), qRound(g.y() * dpr)), g.size() * dpr);
        if (!covered.contains(pr)) { complete = false; break; }
    }
    if (!complete || surfaces.isEmpty()) {
        QRect v;
        QImage fallback = captureWithQt(&v);
        if (!fallback.isNull())
            return fallback;
        if (error) *error = err.isEmpty() ? QStringLiteral("抓屏失败") : err;
        return QImage();
    }

    QRect v;
    QImage img = compose(surfaces, v);
    if (physicalRectOut) *physicalRectOut = v;
    g_lastPath = QStringLiteral("dxgi");
    return img;
}

QRect nativeMonitorRect(quintptr id) {
    HMONITOR mon = MonitorFromWindow(reinterpret_cast<HWND>(id), MONITOR_DEFAULTTONEAREST);
    MONITORINFO mi{};
    mi.cbSize = sizeof(mi);
    if (mon && GetMonitorInfoW(mon, &mi)) {
        const RECT& r = mi.rcMonitor;
        return QRect(r.left, r.top, int(r.right - r.left), int(r.bottom - r.top));
    }
    return QRect();
}

QString lastPath() { return g_lastPath; }

QString dpiAwarenessInfo() {
    QStringList parts;
    DPI_AWARENESS_CONTEXT ctx = GetThreadDpiAwarenessContext();
    DPI_AWARENESS aw = GetAwarenessFromDpiAwarenessContext(ctx);
    switch (aw) {
    case DPI_AWARENESS_UNAWARE: parts << "thread=unaware"; break;
    case DPI_AWARENESS_SYSTEM_AWARE: parts << "thread=system"; break;
    case DPI_AWARENESS_PER_MONITOR_AWARE: parts << "thread=permonitor"; break;
    default: parts << "thread=?"; break;
    }
    parts << QString("threadDpi=%1").arg(GetDpiForSystem());
    HDC dc = GetDC(nullptr);
    if (dc) {
        parts << QString("dcCaps=%1x%2").arg(GetDeviceCaps(dc, HORZRES)).arg(GetDeviceCaps(dc, VERTRES));
        parts << QString("desktopDpi=%1").arg(GetDeviceCaps(dc, LOGPIXELSX));
        ReleaseDC(nullptr, dc);
    }
    return parts.join(" ");
}

QRect trimBlackBorder(QImage& img, QRect rectIn) {
    if (img.isNull() || img.width() < 64 || img.height() < 64) return rectIn;

    auto rowHasContent = [&img](int y) {
        const QRgb* line = reinterpret_cast<const QRgb*>(img.constScanLine(y));
        for (int x = 0; x < img.width(); x += 3)
            if (qGray(line[x]) > 12) return true;
        return false;
    };
    auto colHasContent = [&img](int x) {
        for (int y = 0; y < img.height(); y += 3)
            if (qGray(img.pixel(x, y)) > 12) return true;
        return false;
    };

    int right = img.width() - 1;
    while (right > img.width() / 2 && !colHasContent(right)) --right;
    int bottom = img.height() - 1;
    while (bottom > img.height() / 2 && !rowHasContent(bottom)) --bottom;
    int left = 0;
    while (left < img.width() / 4 && !colHasContent(left)) ++left;
    int top = 0;
    while (top < img.height() / 4 && !rowHasContent(top)) ++top;

    // 边缘再留 1px，避免把内容切掉
    right = qMin(img.width() - 1, right + 1);
    bottom = qMin(img.height() - 1, bottom + 1);

    QRect trimmed(left, top, right - left + 1, bottom - top + 1);
    if (trimmed.width() < 64 || trimmed.height() < 64) return rectIn;
    // 只有确实存在明显黑边时才裁
    const int lostW = img.width() - trimmed.width();
    const int lostH = img.height() - trimmed.height();
    if (lostW < 24 && lostH < 24) return rectIn;

    img = img.copy(trimmed);
    return QRect(rectIn.topLeft() + QPoint(left, top), trimmed.size());
}

QRect nativeWindowRect(quintptr id) {
    RECT r{};
    if (GetWindowRect(reinterpret_cast<HWND>(id), &r))
        return QRect(r.left, r.top, int(r.right - r.left), int(r.bottom - r.top));
    return QRect();
}

} // namespace capture
