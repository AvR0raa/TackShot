#pragma once
#include <QString>

// 内置云代理（L2）：百度/SimpleTex 密钥只存云端，客户端只持有代理 URL。
// URL 在构建时由 tools/proxy_local.json 注入（src/proxy_embedded.inc，不入库）。
namespace managed {

QString proxyUrl();               // 环境变量 TACKSHOT_MANAGED_PROXY 优先，其次内置
bool available();                 // 是否有可用代理（内置或环境变量）
QString endpoint(const QString& route);   // proxyUrl() + "/picture" "/text" "/simpletex"

} // namespace managed
