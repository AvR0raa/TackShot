import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

old = """int main(int argc, char** argv) {
    QApplication::setHighDpiScaleFactorRoundingPolicy(Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
    QApplication app(argc, argv);"""
new = """int main(int argc, char** argv) {
    // 有些宿主（IDE/沙箱/启动器）会注入 QT_SCALE_FACTOR 之类的变量，
    // 它们会让 Qt 把 125% 的屏幕按 100% 渲染，导致截图覆盖层只铺满 80% 屏幕。
    // 我们始终按系统 DPI 工作，所以启动前清掉这些覆盖项。
    qunsetenv("QT_SCALE_FACTOR");
    qunsetenv("QT_SCALE_FACTOR_ROUNDING_POLICY");
    qunsetenv("QT_AUTO_SCREEN_SCALE_FACTOR");
    qputenv("QT_ENABLE_HIGHDPI_SCALING", "1");

    QApplication::setHighDpiScaleFactorRoundingPolicy(Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
    QApplication app(argc, argv);"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("env overrides cleared")
else:
    print("MISS")
