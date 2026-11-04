#pragma once
#include <QString>

// DPAPI 保护的本地小秘密存储（目前只放翻译 API Key）
namespace secrets {

QString storePath();
bool save(const QString& name, const QString& value);
QString load(const QString& name);
bool remove(const QString& name);
bool has(const QString& name);

} // namespace secrets
