#include "capture.h"
#include <QGuiApplication>
#include <QScreen>
#include <QPixmap>
#include <QDebug>
#include <QVector>
#include <QPainter>
#include <cstring>

#include <windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>

namespace {

struct Surface {
    QRect rect;     // 物理像素，虚拟桌面坐标
    QImage image;
};

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
                const BYTE* src = static_cast<const BYTE*>(map.pData);
                for (UINT y = 0; y < desc.Height; ++y)
                    std::memcpy(img.scanLine(int(y)), src + size_t(y) * map.RowPitch, size_t(desc.Width) * 4);
                ctx->Unmap(staging, 0);

                DXGI_OUTPUT_DESC od{};
                out->GetDesc(&od);
                result.rect = QRect(od.DesktopCoordinates.left, od.DesktopCoordinates.top,
                                    od.DesktopCoordinates.right - od.DesktopCoordinates.left,
                                    od.DesktopCoordinates.bottom - od.DesktopCoordinates.top);
                result.image = img;
                ok = true;
            }
            staging->Release();
        }
        tex->Release();
    }
    dup->ReleaseFrame();
    res->Release();
    dup->Release();
    return ok;
}

} // namespace

namespace capture {

static QString g_lastPath = QStringLiteral("none");


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
                    if (grabOutputDesktop(dev, ctx, out, s))
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
