import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include <QString>', '#include <QString>\n#include <QElapsedTimer>')
s = s.replace("    qint64 m_pts = 0;              // 100ns", "    qint64 m_pts = 0;              // 100ns\n    QElapsedTimer m_clock;")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    m_writer = writer;\n    m_started = true;",
              "    m_writer = writer;\n    m_started = true;\n    m_clock.start();")
old = """    const LONGLONG dur = 10'000'000LL / m_fps;
    sample->SetSampleTime(m_pts);
    sample->SetSampleDuration(dur);
    m_pts += dur;"""
new = """    const LONGLONG dur = 10'000'000LL / m_fps;
    // 用真实时间做时间戳：编码跟不上时会丢帧而不是整体加速
    LONGLONG now = LONGLONG(m_clock.nsecsElapsed() / 100);
    if (now <= m_pts) now = m_pts + dur;
    sample->SetSampleTime(now);
    sample->SetSampleDuration(dur);
    m_pts = now;"""
if old in s:
    s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("pts patched", "now" in s)
