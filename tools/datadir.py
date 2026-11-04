import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
old = """QString Config::dataDir() const {
    QString d = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    // AppDataLocation 含组织名，收敛到 %APPDATA%/TackShot
    QString base = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    QDir().mkpath(base + "/" + TS_APP_NAME);
    return base + "/" + TS_APP_NAME;
}"""
new = """QString Config::dataDir() const {
    // 便携模式 / 自检用：可用环境变量重定向
    const QString override = qEnvironmentVariable("TACKSHOT_DATA_DIR");
    if (!override.isEmpty()) {
        QDir().mkpath(override);
        return override;
    }
    QString base = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    QDir().mkpath(base + "/" + TS_APP_NAME);
    return base + "/" + TS_APP_NAME;
}"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("dataDir override added")
else:
    print("MISS")
