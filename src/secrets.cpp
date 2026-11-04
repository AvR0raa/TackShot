#include "secrets.h"
#include "config.h"
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QDir>
#include <QDebug>

#ifdef Q_OS_WIN
#include <windows.h>
#include <wincrypt.h>
#endif

namespace secrets {

QString storePath() { return Config::get().dataDir() + "/secrets.dat"; }

#ifdef Q_OS_WIN
static QByteArray protect(const QByteArray& plain) {
    DATA_BLOB in{ DWORD(plain.size()), (BYTE*)plain.constData() };
    DATA_BLOB out{};
    if (!CryptProtectData(&in, L"TackShot secret", nullptr, nullptr, nullptr,
                          CRYPTPROTECT_UI_FORBIDDEN, &out))
        return QByteArray();
    QByteArray r((const char*)out.pbData, int(out.cbData));
    LocalFree(out.pbData);
    return r;
}

static QByteArray unprotect(const QByteArray& cipher) {
    DATA_BLOB in{ DWORD(cipher.size()), (BYTE*)cipher.constData() };
    DATA_BLOB out{};
    if (!CryptUnprotectData(&in, nullptr, nullptr, nullptr, nullptr,
                            CRYPTPROTECT_UI_FORBIDDEN, &out))
        return QByteArray();
    QByteArray r((const char*)out.pbData, int(out.cbData));
    LocalFree(out.pbData);
    return r;
}
#else
static QByteArray protect(const QByteArray& p) { return p; }
static QByteArray unprotect(const QByteArray& c) { return c; }
#endif

static QJsonObject readAll() {
    QFile f(storePath());
    if (!f.open(QIODevice::ReadOnly)) return QJsonObject();
    auto doc = QJsonDocument::fromJson(f.readAll());
    return doc.object();
}

static void writeAll(const QJsonObject& o) {
    QDir().mkpath(Config::get().dataDir());
    QFile f(storePath());
    if (f.open(QIODevice::WriteOnly | QIODevice::Truncate))
        f.write(QJsonDocument(o).toJson(QJsonDocument::Compact));
}

bool save(const QString& name, const QString& value) {
    QJsonObject o = readAll();
    QByteArray enc = protect(value.toUtf8());
    o[name] = QString::fromLatin1(enc.toBase64());
    writeAll(o);
    return !enc.isEmpty();
}

QString load(const QString& name) {
    QJsonObject o = readAll();
    if (!o.contains(name)) return QString();
    QByteArray enc = QByteArray::fromBase64(o[name].toString().toLatin1());
    QByteArray plain = unprotect(enc);
    return QString::fromUtf8(plain);
}

bool remove(const QString& name) {
    QJsonObject o = readAll();
    o.remove(name);
    writeAll(o);
    return true;
}

bool has(const QString& name) { return readAll().contains(name); }

} // namespace secrets
