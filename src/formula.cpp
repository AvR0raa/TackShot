#include "formula.h"
#include "common.h"

#include <QCoreApplication>
#include <QDir>
#include <QRegularExpression>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <algorithm>
#include <cmath>
#include <vector>

#include "onnxruntime_c_api.h"

#ifdef Q_OS_WIN
#include <windows.h>
#endif

namespace {

const OrtApi* gf = nullptr;

#ifdef Q_OS_WIN
HMODULE g_ortModF = nullptr;
bool loadOrtLib(const QString& exeDir) {
    if (gf) return true;
    QString path = exeDir + "/onnxruntime.dll";
    if (!QFileInfo::exists(path)) path = "onnxruntime.dll";
    if (!g_ortModF) g_ortModF = LoadLibraryW(reinterpret_cast<LPCWSTR>(path.utf16()));
    if (!g_ortModF) return false;
    auto fn = (const OrtApiBase* (*)(void))GetProcAddress(g_ortModF, "OrtGetApiBase");
    if (!fn) return false;
    const OrtApiBase* base = fn();
    gf = base->GetApi(ORT_API_VERSION);
    return gf != nullptr;
}
#else
bool loadOrtLib(const QString&) { return false; }
#endif

// 图片 → 384x384 的 NCHW 浮点（(x/255-0.5)/0.5）
std::vector<float> preprocess(const QImage& src, int size) {
    QImage img = src.convertToFormat(QImage::Format_RGB888)
                    .scaled(size, size, Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
    std::vector<float> out(size_t(3) * size * size);
    const size_t plane = size_t(size) * size;
    for (int y = 0; y < size; ++y) {
        const uchar* line = img.constScanLine(y);
        for (int x = 0; x < size; ++x) {
            const size_t idx = size_t(y) * size + x;
            for (int c = 0; c < 3; ++c) {
                const float v = line[x * 3 + c] / 255.0f;
                out[c * plane + idx] = (v - 0.5f) / 0.5f;
            }
        }
    }
    return out;
}

QString detokenize(const QStringList& idToToken, const QVector<int>& ids) {
    QString s;
    for (int id : ids) {
        if (id < 0 || id >= idToToken.size()) continue;
        QString t = idToToken[id];
        if (t == "<s>" || t == "</s>" || t == "<pad>" || t == "<unk>") continue;
        t.replace(QChar(0x0120), QLatin1Char(' '));   // Ġ -> 空格（BPE）
        s += t;
    }
    // 规整空白
    s.replace(QRegularExpression(QStringLiteral("[ \\t]+")), QStringLiteral(" "));
    s = s.trimmed();
    s.replace(QStringLiteral(" }"), QStringLiteral("}"));
    s.replace(QStringLiteral(" {"), QStringLiteral("{"));
    return s;
}

} // namespace

FormulaRecognizer& FormulaRecognizer::get() {
    static FormulaRecognizer r;
    return r;
}

FormulaRecognizer::~FormulaRecognizer() { release(); }

void FormulaRecognizer::release() {
    if (!gf) { m_ready = false; return; }
    if (m_enc) { gf->ReleaseSession((OrtSession*)m_enc); m_enc = nullptr; }
    if (m_dec) { gf->ReleaseSession((OrtSession*)m_dec); m_dec = nullptr; }
    if (m_detEnv) { gf->ReleaseEnv((OrtEnv*)m_detEnv); m_detEnv = nullptr; }
    m_ready = false;
}

bool FormulaRecognizer::loadVocab(const QString& path) {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) { m_error = QStringLiteral("打不开 tokenizer.json"); return false; }
    const QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
    f.close();
    const QJsonObject vocab = doc.object().value("model").toObject().value("vocab").toObject();
    if (vocab.isEmpty()) { m_error = QStringLiteral("tokenizer.json 里没有 vocab"); return false; }

    int maxId = 0;
    for (auto it = vocab.begin(); it != vocab.end(); ++it)
        maxId = std::max(maxId, it.value().toInt());
    m_idToToken = QStringList();
    m_idToToken.resize(maxId + 1);
    for (auto it = vocab.begin(); it != vocab.end(); ++it)
        m_idToToken[it.value().toInt()] = it.key();
    return true;
}

bool FormulaRecognizer::init(const QString& modelDir, QString* err) {
    if (m_ready) return true;
    const QString exeDir = QCoreApplication::applicationDirPath();
    if (!loadOrtLib(exeDir)) { m_error = QStringLiteral("找不到 onnxruntime.dll"); if (err) *err = m_error; return false; }

    m_dir = modelDir.isEmpty() ? (exeDir + "/models/formula") : modelDir;
    const QString encPath = m_dir + "/encoder_model.onnx";
    const QString decPath = m_dir + "/decoder_model.onnx";
    const QString tokPath = m_dir + "/tokenizer.json";
    if (!QFileInfo::exists(encPath) || !QFileInfo::exists(decPath)) {
        m_error = QStringLiteral("缺少公式模型：%1").arg(m_dir);
        if (err) *err = m_error;
        return false;
    }
    if (!loadVocab(tokPath)) { if (err) *err = m_error; return false; }

    OrtStatus* st = gf->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "tackshot-formula", (OrtEnv**)&m_detEnv);
    if (st) { m_error = QString::fromUtf8(gf->GetErrorMessage(st)); gf->ReleaseStatus(st); return false; }
    gf->CreateCpuMemoryInfo(OrtArenaAllocator, OrtMemTypeDefault, (OrtMemoryInfo**)&m_memInfo);

    OrtSessionOptions* opts = nullptr;
    gf->CreateSessionOptions(&opts);
    gf->SetSessionGraphOptimizationLevel(opts, ORT_ENABLE_ALL);
    gf->SetIntraOpNumThreads(opts, 2);

    auto load = [&](const QString& path, void** out) -> bool {
        OrtStatus* s = gf->CreateSession((OrtEnv*)m_detEnv, (const ORTCHAR_T*)path.utf16(),
                                         opts, (OrtSession**)out);
        if (s) {
            m_error = QStringLiteral("加载 %1 失败：%2").arg(QFileInfo(path).fileName(),
                                                             QString::fromUtf8(gf->GetErrorMessage(s)));
            gf->ReleaseStatus(s);
            return false;
        }
        return true;
    };
    const bool ok = load(encPath, &m_enc) && load(decPath, &m_dec);
    gf->ReleaseSessionOptions(opts);
    if (!ok) { if (err) *err = m_error; return false; }

    m_ready = true;
    m_error.clear();
    return true;
}

QString FormulaRecognizer::recognize(const QImage& img) {
    if (!m_ready && !init(QString(), &m_error)) return QString();
    if (img.isNull()) return QString();

    const int size = 384;
    std::vector<float> in = preprocess(img, size);
    const int64_t shape[4] = {1, 3, size, size};

    OrtValue* inVal = nullptr;
    if (gf->CreateTensorWithDataAsOrtValue((OrtMemoryInfo*)m_memInfo, in.data(),
                                           in.size() * sizeof(float), shape, 4,
                                           ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT, &inVal) != nullptr)
        return QString();

    const char* encIn = nullptr;
    const char* encOut = nullptr;
    {
        OrtAllocator* alloc = nullptr;
        gf->GetAllocatorWithDefaultOptions(&alloc);
        char* n = nullptr;
        gf->SessionGetInputName((OrtSession*)m_enc, 0, alloc, &n); encIn = n;
        char* n2 = nullptr;
        gf->SessionGetOutputName((OrtSession*)m_enc, 0, alloc, &n2); encOut = n2;
    }

    OrtValue* hiddenVal = nullptr;
    OrtStatus* st = gf->Run((OrtSession*)m_enc, nullptr, &encIn, (const OrtValue* const*)&inVal, 1,
                            &encOut, 1, &hiddenVal);
    gf->ReleaseValue(inVal);
    if (st) { m_error = QString::fromUtf8(gf->GetErrorMessage(st)); gf->ReleaseStatus(st); return QString(); }

    // 取 hidden 维度
    OrtTensorTypeAndShapeInfo* tsi = nullptr;
    gf->GetTensorTypeAndShape(hiddenVal, &tsi);
    size_t nd = 0;
    gf->GetDimensionsCount(tsi, &nd);
    int64_t dims[8] = {0};
    gf->GetDimensions(tsi, dims, nd);
    gf->ReleaseTensorTypeAndShapeInfo(tsi);
    if (nd < 3) { gf->ReleaseValue(hiddenVal); return QString(); }
    m_hiddenLen = int(dims[nd - 2]);
    m_hiddenDim = int(dims[nd - 1]);

    const char* decInIds = nullptr;
    const char* decInHidden = nullptr;
    const char* decOutLogits = nullptr;
    {
        OrtAllocator* alloc = nullptr;
        gf->GetAllocatorWithDefaultOptions(&alloc);
        char* n = nullptr;
        gf->SessionGetInputName((OrtSession*)m_dec, 0, alloc, &n); decInIds = n;
        char* n2 = nullptr;
        gf->SessionGetInputName((OrtSession*)m_dec, 1, alloc, &n2); decInHidden = n2;
        char* n3 = nullptr;
        gf->SessionGetOutputName((OrtSession*)m_dec, 0, alloc, &n3); decOutLogits = n3;
    }

    QVector<int> ids;
    ids.append(1);                       // <s>
    const int maxTokens = 200;
    const int vocabSize = m_idToToken.size();

    for (int step = 0; step < maxTokens; ++step) {
        std::vector<int64_t> inputIds(ids.size());
        for (int i = 0; i < ids.size(); ++i) inputIds[i] = ids[i];
        const int64_t idShape[2] = {1, int64_t(ids.size())};

        OrtValue* idVal = nullptr;
        if (gf->CreateTensorWithDataAsOrtValue((OrtMemoryInfo*)m_memInfo, inputIds.data(),
                                               inputIds.size() * sizeof(int64_t), idShape, 2,
                                               ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64, &idVal) != nullptr)
            break;

        const char* names[2] = {decInIds, decInHidden};
        const OrtValue* vals[2] = {idVal, hiddenVal};
        OrtValue* logits = nullptr;
        OrtStatus* s2 = gf->Run((OrtSession*)m_dec, nullptr, names, vals, 2, &decOutLogits, 1, &logits);
        gf->ReleaseValue(idVal);
        if (s2) { m_error = QString::fromUtf8(gf->GetErrorMessage(s2)); gf->ReleaseStatus(s2); break; }

        float* p = nullptr;
        gf->GetTensorMutableData(logits, (void**)&p);
        OrtTensorTypeAndShapeInfo* ti = nullptr;
        gf->GetTensorTypeAndShape(logits, &ti);
        size_t n2 = 0;
        gf->GetDimensionsCount(ti, &n2);
        int64_t d2[8] = {0};
        gf->GetDimensions(ti, d2, n2);
        gf->ReleaseTensorTypeAndShapeInfo(ti);

        if (n2 < 3) { gf->ReleaseValue(logits); break; }
        const int T = int(d2[n2 - 2]);
        const int C = int(d2[n2 - 1]);
        const float* last = p + size_t(T - 1) * C;
        int best = 0;
        float bp = last[0];
        for (int k = 1; k < C; ++k) if (last[k] > bp) { bp = last[k]; best = k; }
        gf->ReleaseValue(logits);

        if (best == 2) break;                    // </s>
        if (best <= 4 || best >= vocabSize) break;  // 特殊 token / 越界
        ids.append(best);
    }

    gf->ReleaseValue(hiddenVal);
    QVector<int> body = ids.mid(1);
    return detokenize(m_idToToken, body);
}
