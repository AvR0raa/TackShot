#include "managed.h"
#include <QtGlobal>
#include "proxy_embedded.inc"   // kManagedProxy：build.ps1 从 tools/proxy_local.json 生成

namespace managed {

QString proxyUrl() {
    const QString override = qEnvironmentVariable("TACKSHOT_MANAGED_PROXY");
    // "off"：显式禁用托管（自检与需要强制直连/报错语义的场景）
    if (override == QLatin1String("off")) return QString();
    if (!override.isEmpty()) return override;
    return QString::fromLatin1(kManagedProxy);
}

bool available() {
    return !proxyUrl().isEmpty();
}

QString endpoint(const QString& route) {
    QString base = proxyUrl();
    while (base.endsWith(QLatin1Char('/'))) base.chop(1);
    return base + QLatin1Char('/') + route;
}

} // namespace managed
