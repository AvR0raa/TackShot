#include "ocr.h"
#include "common.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QDebug>
#include <QThread>
#include <QtMath>
#include <algorithm>
#include <cmath>
#include <vector>

#include "onnxruntime_c_api.h"

#ifdef Q_OS_WIN
#include <windows.h>
#endif

namespace {

const OrtApi* g = nullptr;

#ifdef Q_OS_WIN
HMODULE g_ortMod = nullptr;
bool loadOrt(const QString& exeDir) {
    QString path = exeDir + "/onnxruntime.dll";
    if (!QFileInfo::exists(path)) path = "onnxruntime.dll";
    g_ortMod = LoadLibraryW(reinterpret_cast<LPCWSTR>(path.utf16()));
    if (!g_ortMod) return false;
    auto fn = (const OrtApiBase* (*)(void))GetProcAddress(g_ortMod, "OrtGetApiBase");
    if (!fn) return false;
    const OrtApiBase* base = fn();
    g = base->GetApi(ORT_API_VERSION);
    return g != nullptr;
}
#else
bool loadOrt(const QString&) { return false; }
#endif

struct Img {
    int w = 0, h = 0;
    std::vector<uint8_t> rgb;   // RGB888
};

Img toRgb(const QImage& src) {
    Img im;
    QImage img = src.convertToFormat(QImage::Format_RGB888);
    im.w = img.width(); im.h = img.height();
    im.rgb.resize(size_t(im.w) * im.h * 3);
    for (int y = 0; y < im.h; ++y)
        memcpy(im.rgb.data() + size_t(y) * im.w * 3, img.constScanLine(y), size_t(im.w) * 3);
    return im;
}

Img resizeBilinear(const Img& s, int nw, int nh) {
    Img d; d.w = nw; d.h = nh; d.rgb.resize(size_t(nw) * nh * 3);
    for (int y = 0; y < nh; ++y) {
        float fy = (y + 0.5f) * s.h / nh - 0.5f;
        int y0 = std::max(0, int(std::floor(fy))); int y1 = std::min(s.h - 1, y0 + 1);
        float wy = fy - y0; if (wy < 0) { wy = 0; y0 = y1 = std::max(0, std::min(s.h - 1, int(fy))); }
        for (int x = 0; x < nw; ++x) {
            float fx = (x + 0.5f) * s.w / nw - 0.5f;
            int x0 = std::max(0, int(std::floor(fx))); int x1 = std::min(s.w - 1, x0 + 1);
            float wx = fx - x0; if (wx < 0) { wx = 0; x0 = x1 = std::max(0, std::min(s.w - 1, int(fx))); }
            for (int c = 0; c < 3; ++c) {
                auto px = [&](int xx, int yy) { return s.rgb[(size_t(yy) * s.w + xx) * 3 + c]; };
                float v = px(x0, y0) * (1 - wx) * (1 - wy) + px(x1, y0) * wx * (1 - wy)
                        + px(x0, y1) * (1 - wx) * wy + px(x1, y1) * wx * wy;
                d.rgb[(size_t(y) * nw + x) * 3 + c] = uint8_t(std::lround(std::min(255.f, std::max(0.f, v))));
            }
        }
    }
    return d;
}

// 归一化到 NCHW float
std::vector<float> toNchw(const Img& im, float mean, float stdv) {
    std::vector<float> out(size_t(3) * im.w * im.h);
    const size_t plane = size_t(im.w) * im.h;
    for (int y = 0; y < im.h; ++y) {
        for (int x = 0; x < im.w; ++x) {
            size_t idx = size_t(y) * im.w + x;
            for (int c = 0; c < 3; ++c) {
                float v = im.rgb[idx * 3 + c] / 255.0f;
                out[c * plane + idx] = (v - mean) / stdv;
            }
        }
    }
    return out;
}

} // namespace

Ocr& Ocr::get() {
    static Ocr e;
    return e;
}

bool Ocr::init(QString* err) {
    if (m_ready) return true;
    if (!loadSessions()) {
        if (err) *err = m_error;
        return false;
    }
    m_ready = true;
    return true;
}

void Ocr::release() {
    if (!g) return;
    if (m_det) { g->ReleaseSession((OrtSession*)m_det); m_det = nullptr; }
    if (m_rec) { g->ReleaseSession((OrtSession*)m_rec); m_rec = nullptr; }
    if (m_memInfo) { g->ReleaseMemoryInfo((OrtMemoryInfo*)m_memInfo); m_memInfo = nullptr; }
    if (m_env) { g->ReleaseEnv((OrtEnv*)m_env); m_env = nullptr; }
}

bool Ocr::loadSessions() {
    QString exeDir = QCoreApplication::applicationDirPath();
    if (!loadOrt(exeDir)) {
        m_error = QStringLiteral("找不到 onnxruntime.dll");
        return false;
    }

    QString modelDir = exeDir + "/models";
    QString detPath = modelDir + "/ch_PP-OCRv4_det_infer.onnx";
    QString recPath = modelDir + "/ch_PP-OCRv4_rec_infer.onnx";
    QString dictPath = modelDir + "/ppocr_keys_v1.txt";
    if (!QFileInfo::exists(detPath) || !QFileInfo::exists(recPath)) {
        m_error = QStringLiteral("缺少 OCR 模型（models/）");
        return false;
    }

    // 字典：blank(0) + 字符 + 空格
    QFile df(dictPath);
    if (df.open(QIODevice::ReadOnly)) {
        QString all = QString::fromUtf8(df.readAll());
        df.close();
        m_dict = all.split('\n', Qt::SkipEmptyParts);
        for (QString& s : m_dict) s = s.trimmed();
    }
    if (m_dict.isEmpty()) {
        m_error = QStringLiteral("缺少字典 ppocr_keys_v1.txt");
        return false;
    }
    m_dict.prepend(QStringLiteral("blank"));
    m_dict.append(QStringLiteral(" "));

    if (g->CreateEnv(ORT_LOGGING_LEVEL_ERROR, "TackShotOcr", (OrtEnv**)&m_env) != nullptr) {
        m_error = QStringLiteral("ORT 初始化失败");
        return false;
    }
    OrtSessionOptions* opts = nullptr;
    g->CreateSessionOptions(&opts);
    g->SetIntraOpNumThreads(opts, std::max(1, QThread::idealThreadCount() / 2));
    g->SetSessionGraphOptimizationLevel(opts, ORT_ENABLE_ALL);

    auto load = [&](const QString& path, void** out) -> bool {
        OrtStatus* st = g->CreateSession((OrtEnv*)m_env, (const ORTCHAR_T*)path.utf16(),
                                         opts, (OrtSession**)out);
        if (st) {
            m_error = QString::fromUtf8(g->GetErrorMessage(st));
            g->ReleaseStatus(st);
            return false;
        }
        return true;
    };
    if (!load(detPath, &m_det) || !load(recPath, &m_rec)) {
        g->ReleaseSessionOptions(opts);
        return false;
    }
    g->ReleaseSessionOptions(opts);
    g->CreateCpuMemoryInfo(OrtArenaAllocator, OrtMemTypeDefault, (OrtMemoryInfo**)&m_memInfo);
    return true;
}

QVector<OcrLine> Ocr::recognize(const QImage& src, QString* err) {
    QVector<OcrLine> lines;
    if (!m_ready && !init(err)) return lines;
    if (src.isNull()) return lines;

    const Img orig = toRgb(src);
    if (orig.w < 8 || orig.h < 8) return lines;

    // ---------- det ----------
    // 屏幕截图场景：不放大，只限制长边（放大反而让 DB 输出变糊）
    int limit = 1280;
    float ratio = 1.0f;
    if (std::max(orig.w, orig.h) > limit)
        ratio = float(limit) / float(std::max(orig.w, orig.h));
    int rh = int(std::lround(orig.h * ratio / 32.0) * 32);
    int rw = int(std::lround(orig.w * ratio / 32.0) * 32);
    rh = std::max(32, rh); rw = std::max(32, rw);
    // 控制显存/内存
    const long long maxPix = 1600LL * 1600;
    if (1LL * rw * rh > maxPix) {
        float k = std::sqrt(float(maxPix) / float(rw * rh));
        rh = std::max(32, int(rh * k) / 32 * 32);
        rw = std::max(32, int(rw * k) / 32 * 32);
    }

    Img detImg = resizeBilinear(orig, rw, rh);
    std::vector<float> detIn = toNchw(detImg, 0.5f, 0.5f);
    const int64_t detShape[4] = {1, 3, rh, rw};

    OrtValue* inVal = nullptr;
    if (g->CreateTensorWithDataAsOrtValue((OrtMemoryInfo*)m_memInfo, detIn.data(),
                                          detIn.size() * sizeof(float), detShape, 4,
                                          ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT, &inVal) != nullptr) {
        if (err) *err = QStringLiteral("det 输入张量创建失败");
        return lines;
    }

    const char* detInName = nullptr; const char* detOutName = nullptr;
    {
        OrtAllocator* alloc = nullptr; g->GetAllocatorWithDefaultOptions(&alloc);
        char* n = nullptr;
        g->SessionGetInputName((OrtSession*)m_det, 0, alloc, &n); detInName = n;
        char* n2 = nullptr;
        g->SessionGetOutputName((OrtSession*)m_det, 0, alloc, &n2); detOutName = n2;
    }

    OrtValue* detOut = nullptr;
    OrtStatus* st = g->Run((OrtSession*)m_det, nullptr, &detInName, (const OrtValue* const*)&inVal, 1,
                           &detOutName, 1, &detOut);
    g->ReleaseValue(inVal);
    if (st) {
        if (err) *err = QString::fromUtf8(g->GetErrorMessage(st));
        g->ReleaseStatus(st);
        return lines;
    }

    float* map = nullptr;
    g->GetTensorMutableData(detOut, (void**)&map);
    OrtTensorTypeAndShapeInfo* tsi = nullptr;
    g->GetTensorTypeAndShape(detOut, &tsi);
    size_t nd = 0; g->GetDimensionsCount(tsi, &nd);
    int64_t dims[8] = {0};
    g->GetDimensions(tsi, dims, nd);
    int mh = int(dims[nd - 2]), mw = int(dims[nd - 1]);
    g->ReleaseTensorTypeAndShapeInfo(tsi);

    // ---------- DB 后处理（连通域 + 外扩） ----------
    std::vector<uint8_t> bin(size_t(mw) * mh, 0);
    for (int y = 0; y < mh; ++y)
        for (int x = 0; x < mw; ++x)
            bin[size_t(y) * mw + x] = map[size_t(y) * mw + x] > 0.3f ? 1 : 0;

    // 2x2 膨胀
    {
        std::vector<uint8_t> d(bin.size(), 0);
        for (int y = 0; y < mh; ++y)
            for (int x = 0; x < mw; ++x) {
                if (!bin[size_t(y) * mw + x]) continue;
                for (int dy = 0; dy < 2; ++dy)
                    for (int dx = 0; dx < 2; ++dx) {
                        int yy = y + dy, xx = x + dx;
                        if (yy < mh && xx < mw) d[size_t(yy) * mw + xx] = 1;
                    }
            }
        bin.swap(d);
    }

    std::vector<int> stack;
    std::vector<uint8_t> seen(bin.size(), 0);
    struct Box { int x0, y0, x1, y1; double score; int area; };
    std::vector<Box> boxes;

    for (int y = 0; y < mh; ++y) {
        for (int x = 0; x < mw; ++x) {
            size_t idx = size_t(y) * mw + x;
            if (!bin[idx] || seen[idx]) continue;
            stack.clear(); stack.push_back(int(idx)); seen[idx] = 1;
            int x0 = x, x1 = x, y0 = y, y1 = y, area = 0;
            double sum = 0;
            while (!stack.empty()) {
                int cur = stack.back(); stack.pop_back();
                int cy = cur / mw, cx = cur % mw;
                area++;
                sum += map[cur];
                x0 = std::min(x0, cx); x1 = std::max(x1, cx);
                y0 = std::min(y0, cy); y1 = std::max(y1, cy);
                for (int dy = -1; dy <= 1; ++dy)
                    for (int dx = -1; dx <= 1; ++dx) {
                        int ny = cy + dy, nx = cx + dx;
                        if (ny < 0 || nx < 0 || ny >= mh || nx >= mw) continue;
                        size_t ni = size_t(ny) * mw + nx;
                        if (bin[ni] && !seen[ni]) { seen[ni] = 1; stack.push_back(int(ni)); }
                    }
            }
            if (area < 12) continue;
            double score = sum / area;
            if (score < 0.5) continue;
            boxes.push_back({x0, y0, x1, y1, score, area});
        }
    }
    g->ReleaseValue(detOut);

    // 映射回原图 + 外扩
    float sx = float(orig.w) / mw, sy = float(orig.h) / mh;
    struct Cand { QRect r; float score; };
    std::vector<Cand> cands;
    for (const auto& b : boxes) {
        QRect r(int(b.x0 * sx), int(b.y0 * sy), int((b.x1 - b.x0 + 1) * sx), int((b.y1 - b.y0 + 1) * sy));
        int padx = std::max(2, int(r.width() * 0.02));
        int pady = std::max(4, int(r.height() * 0.45));
        QRect rr = r.adjusted(-padx, -pady, padx, pady);
        r = rr.intersected(QRect(0, 0, orig.w, orig.h));
        if (r.height() < 8 || r.width() < 8) continue;
        cands.push_back({r, float(b.score)});
    }

    // 按行排序（y 聚类，再按 x）
    std::sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) {
        int ay = a.r.center().y(), by = b.r.center().y();
        if (std::abs(ay - by) > std::max(8, std::min(a.r.height(), b.r.height()) / 2))
            return ay < by;
        return a.r.x() < b.r.x();
    });

    // ---------- rec ----------
    const char* recInName = nullptr; const char* recOutName = nullptr;
    {
        OrtAllocator* alloc = nullptr; g->GetAllocatorWithDefaultOptions(&alloc);
        char* n = nullptr;
        g->SessionGetInputName((OrtSession*)m_rec, 0, alloc, &n); recInName = n;
        char* n2 = nullptr;
        g->SessionGetOutputName((OrtSession*)m_rec, 0, alloc, &n2); recOutName = n2;
    }

    for (const auto& c : cands) {
        QImage crop = src.copy(c.r);
        Img ci = toRgb(crop);
        int h = 48;
        int w = std::max(16, int(std::lround(48.0 * ci.w / std::max(1, ci.h))));
        w = std::min(w, 1600);
        Img ri = resizeBilinear(ci, w, h);
        std::vector<float> in = toNchw(ri, 0.5f, 0.5f);
        const int64_t shape[4] = {1, 3, h, w};
        OrtValue* iv = nullptr;
        if (g->CreateTensorWithDataAsOrtValue((OrtMemoryInfo*)m_memInfo, in.data(),
                                              in.size() * sizeof(float), shape, 4,
                                              ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT, &iv) != nullptr)
            continue;
        OrtValue* ov = nullptr;
        OrtStatus* st2 = g->Run((OrtSession*)m_rec, nullptr, &recInName, (const OrtValue* const*)&iv, 1,
                                &recOutName, 1, &ov);
        g->ReleaseValue(iv);
        if (st2) { g->ReleaseStatus(st2); continue; }

        float* p = nullptr;
        g->GetTensorMutableData(ov, (void**)&p);
        OrtTensorTypeAndShapeInfo* ti = nullptr;
        g->GetTensorTypeAndShape(ov, &ti);
        size_t n2 = 0; g->GetDimensionsCount(ti, &n2);
        int64_t d2[8] = {0};
        g->GetDimensions(ti, d2, n2);
        int T = int(d2[n2 - 2]), C = int(d2[n2 - 1]);
        g->ReleaseTensorTypeAndShapeInfo(ti);

        QString text; float psum = 0; int pcount = 0; int prev = -1;
        for (int t = 0; t < T; ++t) {
            const float* row = p + size_t(t) * C;
            int best = 0; float bp = row[0];
            for (int k = 1; k < C; ++k) if (row[k] > bp) { bp = row[k]; best = k; }
            if (best == 0) { prev = 0; continue; }
            if (best == prev) { prev = best; continue; }
            prev = best;
            if (best < m_dict.size()) text += m_dict[best];
            psum += bp; pcount++;
        }
        g->ReleaseValue(ov);
        text = text.trimmed();
        if (text.isEmpty()) continue;
        lines.push_back({text, pcount ? psum / pcount : c.score, c.r});
    }
    return lines;
}
