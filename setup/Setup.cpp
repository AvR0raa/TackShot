// TackShot 安装程序：单文件，内嵌压缩载荷（payload.rcc 追加在 exe 末尾）
#include <QApplication>
#include <QDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QProgressBar>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QResource>
#include <QSettings>
#include <QStandardPaths>
#include <QProcess>
#include <QMessageBox>
#include <QTextStream>
#include <QTimer>
#include <QCoreApplication>
#include <QDebug>

#include <windows.h>
#include <shlobj.h>
#include <objidl.h>
#include <functional>
#include <cstring>

static const char* kMagic = "TSPAYLOAD1";
static const int kFooter = 16;   // 8 magic + 4 offset + 4 size

static QString installRoot() {
    QString base = qEnvironmentVariable("LOCALAPPDATA");
    return base + "/Programs/TackShot";
}

static bool readFooter(QFile& self, qint64& offset, qint64& size) {
    if (!self.open(QIODevice::ReadOnly)) return false;
    qint64 total = self.size();
    if (total <= kFooter) return false;
    if (!self.seek(total - kFooter)) return false;
    QByteArray tail = self.read(kFooter);
    if (tail.size() != kFooter) return false;
    if (memcmp(tail.constData(), kMagic, 8) != 0) return false;
    memcpy(&offset, tail.constData() + 8, 4);
    memcpy(&size, tail.constData() + 12, 4);
    return offset > 0 && size > 0 && offset + size <= total;
}

static bool extractPayload(const QString& destDir, QString* err, std::function<void(int,int)> progress) {
    qint64 off = 0, sz = 0;
    QFile self(QCoreApplication::applicationFilePath());
    if (!readFooter(self, off, sz)) { if (err) *err = QStringLiteral("安装包损坏：找不到载荷"); return false; }
    if (!self.seek(off)) { if (err) *err = QStringLiteral("读取载荷失败"); return false; }
    QByteArray blob = self.read(sz);
    self.close();
    if (blob.size() != sz) { if (err) *err = QStringLiteral("载荷读取不完整"); return false; }

    QString tmp = QDir::tempPath() + QString("/tackshot_payload_%1.rcc").arg(QCoreApplication::applicationPid());
    {
        QFile tf(tmp);
        if (!tf.open(QIODevice::WriteOnly | QIODevice::Truncate)) { if (err) *err = QStringLiteral("无法写入临时文件"); return false; }
        tf.write(blob);
        tf.close();
    }
    bool ok = QResource::registerResource(tmp);
    if (!ok) {
        QFile::remove(tmp);
        if (err) *err = QStringLiteral("载荷注册失败");
        return false;
    }

    QDir().mkpath(destDir);
    QDir root(":/payload");
    if (!root.exists()) {
        QResource::unregisterResource(tmp);
        QFile::remove(tmp);
        if (err) *err = QStringLiteral("载荷内容为空");
        return false;
    }

    int totalFiles = 0, done = 0;
    {
        std::function<void(const QString&)> count = [&](const QString& p) {
            QDir d(p);
            for (const QFileInfo& fi : d.entryInfoList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot)) {
                if (fi.isDir()) count(fi.absoluteFilePath());
                else totalFiles++;
            }
        };
        count(":/payload");
    }

    bool failed = false;
    std::function<void(const QString&, const QString&)> copyTree = [&](const QString& src, const QString& dst) {
        QDir d(src);
        for (const QFileInfo& fi : d.entryInfoList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot)) {
            QString target = dst + "/" + fi.fileName();
            if (fi.isDir()) {
                QDir().mkpath(target);
                copyTree(fi.absoluteFilePath(), target);
            } else {
                QFile::remove(target);
                if (QFile::copy(fi.absoluteFilePath(), target)) {
                    QFile::setPermissions(target, QFile::ReadOwner | QFile::WriteOwner | QFile::ReadGroup |
                                                  QFile::ReadOther | QFile::WriteUser);
                } else {
                    failed = true;
                }
                done++;
                if (progress) progress(done, totalFiles);
            }
        }
    };
    copyTree(":/payload", destDir);

    QResource::unregisterResource(tmp);
    QFile::remove(tmp);
    if (failed) { if (err) *err = QStringLiteral("部分文件写入失败"); return false; }
    return true;
}

static bool createShortcut(const QString& linkPath, const QString& target, const QString& workDir,
                           const QString& desc, const QString& args = QString()) {
    IShellLinkW* link = nullptr;
    if (FAILED(CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, IID_IShellLinkW, (void**)&link)))
        return false;
    link->SetPath(reinterpret_cast<LPCWSTR>(target.utf16()));
    link->SetWorkingDirectory(reinterpret_cast<LPCWSTR>(workDir.utf16()));
    link->SetDescription(reinterpret_cast<LPCWSTR>(desc.utf16()));
    if (!args.isEmpty())
        link->SetArguments(reinterpret_cast<LPCWSTR>(args.utf16()));
    QString icon = workDir + "/TackShot.exe";
    link->SetIconLocation(reinterpret_cast<LPCWSTR>(icon.utf16()), 0);

    IPersistFile* pf = nullptr;
    bool ok = false;
    if (SUCCEEDED(link->QueryInterface(IID_IPersistFile, (void**)&pf))) {
        ok = SUCCEEDED(pf->Save(reinterpret_cast<LPCOLESTR>(linkPath.utf16()), TRUE));
        pf->Release();
    }
    link->Release();
    return ok;
}

static QString desktopDir() {
    wchar_t buf[MAX_PATH] = {};
    if (SUCCEEDED(SHGetFolderPathW(nullptr, CSIDL_DESKTOPDIRECTORY, nullptr, 0, buf)))
        return QString::fromWCharArray(buf);
    return QStandardPaths::writableLocation(QStandardPaths::DesktopLocation);
}

static QString startMenuDir() {
    wchar_t buf[MAX_PATH] = {};
    if (SUCCEEDED(SHGetFolderPathW(nullptr, CSIDL_PROGRAMS, nullptr, 0, buf)))
        return QString::fromWCharArray(buf) + "/TackShot";
    return qEnvironmentVariable("APPDATA") + "/Microsoft/Windows/Start Menu/Programs/TackShot";
}

static void writeUninstallEntry(const QString& dir) {
    QSettings reg("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TackShot",
                  QSettings::NativeFormat);
    reg.setValue("DisplayName", "TackShot 图钉截图");
    reg.setValue("DisplayVersion", "1.0.0");
    reg.setValue("Publisher", "TackShot");
    reg.setValue("InstallLocation", QDir::toNativeSeparators(dir));
    reg.setValue("DisplayIcon", QDir::toNativeSeparators(dir + "/TackShot.exe"));
    reg.setValue("UninstallString", "\"" + QDir::toNativeSeparators(dir + "/TackShot.exe") + "\" --uninstall");
    reg.setValue("InstallSource", "TackShot-Setup.exe");
    reg.setValue("NoModify", 1);
    reg.setValue("NoRepair", 1);
    qint64 kb = 0;
    QDir d(dir);
    for (const QFileInfo& fi : d.entryInfoList(QDir::Files))
        kb += fi.size();
    reg.setValue("EstimatedSize", int(kb / 1024));
}

static bool doUninstall() {
    QString dir = installRoot();
    QString link1 = desktopDir() + "/TackShot.lnk";
    QString link2 = startMenuDir() + "/TackShot.lnk";
    QFile::remove(link1);
    QFile::remove(link2);
    QDir().rmdir(startMenuDir());
    QSettings reg("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TackShot",
                  QSettings::NativeFormat);
    reg.remove("");
    QSettings run("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run", QSettings::NativeFormat);
    run.remove("TackShot");
    // 删除安装目录（自身进程在目录内，交给 cmd 延迟删除）
    QString cmd = QString("timeout /t 1 /nobreak >nul & rmdir /s /q \"%1\"").arg(QDir::toNativeSeparators(dir));
    QProcess::startDetached("cmd.exe", QStringList() << "/c" << cmd);
    return true;
}

class SetupWindow : public QDialog {
public:
    SetupWindow() {
        setWindowTitle(QStringLiteral("TackShot 安装程序"));
        setFixedSize(520, 300);
        auto* lay = new QVBoxLayout(this);
        lay->setContentsMargins(24, 20, 24, 18);

        auto* title = new QLabel(QStringLiteral("<h2>TackShot 图钉截图</h2>"
                                                "<p>本地截图 / 标注 / 贴图工具（无网络依赖）</p>"));
        lay->addWidget(title);

        pathLabel = new QLabel(QStringLiteral("安装位置：") + QDir::toNativeSeparators(installRoot()));
        pathLabel->setWordWrap(true);
        pathLabel->setStyleSheet("color:#666;");
        lay->addWidget(pathLabel);
        lay->addSpacing(8);

        bar = new QProgressBar;
        bar->setRange(0, 100);
        bar->setValue(0);
        lay->addWidget(bar);

        status = new QLabel(QStringLiteral("准备就绪"));
        status->setStyleSheet("color:#666;");
        lay->addWidget(status);
        lay->addStretch();

        auto* row = new QHBoxLayout;
        row->addStretch();
        cancelBtn = new QPushButton(QStringLiteral("取消"));
        installBtn = new QPushButton(QStringLiteral("安装"));
        installBtn->setDefault(true);
        row->addWidget(cancelBtn);
        row->addWidget(installBtn);
        lay->addLayout(row);

        connect(cancelBtn, &QPushButton::clicked, this, &QDialog::reject);
        connect(installBtn, &QPushButton::clicked, this, [this]() { startInstall(); });
    }

private:
    void startInstall() {
        installBtn->setEnabled(false);
        cancelBtn->setEnabled(false);
        status->setText(QStringLiteral("正在解压…"));
        QApplication::processEvents();

        QString err;
        bool ok = extractPayload(installRoot(), &err, [this](int done, int total) {
            int pct = total ? int(done * 100.0 / total) : 0;
            bar->setValue(pct);
            status->setText(QStringLiteral("正在解压… %1 / %2").arg(done).arg(total));
            QApplication::processEvents();
        });
        if (!ok) {
            status->setText(QStringLiteral("安装失败：") + err);
            QMessageBox::critical(this, QStringLiteral("安装失败"), err);
            installBtn->setEnabled(true);
            cancelBtn->setEnabled(true);
            return;
        }

        status->setText(QStringLiteral("正在创建快捷方式…"));
        QApplication::processEvents();
        QString dir = installRoot();
        QString exe = dir + "/TackShot.exe";
        QDir().mkpath(startMenuDir());
        createShortcut(desktopDir() + "/TackShot.lnk", exe, dir, "TackShot 截图");
        createShortcut(startMenuDir() + "/TackShot.lnk", exe, dir, "TackShot 截图");

        writeUninstallEntry(dir);
        bar->setValue(100);
        status->setText(QStringLiteral("安装完成"));
        QMessageBox::information(this, QStringLiteral("完成"),
            QStringLiteral("TackShot 已安装到：\n%1\n\n按 Ctrl+Alt+A 截图，或点击托盘图标。").arg(QDir::toNativeSeparators(dir)));
        accept();
        QProcess::startDetached(exe, QStringList());
    }

    QLabel* pathLabel = nullptr;
    QLabel* status = nullptr;
    QProgressBar* bar = nullptr;
    QPushButton* installBtn = nullptr;
    QPushButton* cancelBtn = nullptr;
};

int main(int argc, char** argv) {
    QApplication app(argc, argv);
    QApplication::setApplicationName("TackShot Setup");
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

    QStringList args = app.arguments();
    if (args.contains("--silent")) {
        QString err;
        bool ok = extractPayload(installRoot(), &err, nullptr);
        if (ok) {
            QString dir = installRoot();
            QString exe = dir + "/TackShot.exe";
            QDir().mkpath(startMenuDir());
            createShortcut(desktopDir() + "/TackShot.lnk", exe, dir, "TackShot 截图");
            createShortcut(startMenuDir() + "/TackShot.lnk", exe, dir, "TackShot 截图");
            writeUninstallEntry(dir);
        }
        return ok ? 0 : 1;
    }
    if (args.contains("--uninstall")) {
        doUninstall();
        return 0;
    }

    SetupWindow w;
    w.show();
    return app.exec();
}
