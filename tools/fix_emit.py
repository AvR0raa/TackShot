import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\gifenc.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("auto emit = [&](int code)", "auto emitCode = [&](int code)")
s = s.replace("    emit(1 << minCodeSize);   // clear code", "    emitCode(1 << minCodeSize);   // clear code")
s = s.replace("        emit(prev);\n", "        emitCode(prev);\n")
s = s.replace("            emit(1 << minCodeSize);\n", "            emitCode(1 << minCodeSize);\n")
s = s.replace("    if (prev >= 0) emit(prev);\n", "    if (prev >= 0) emitCode(prev);\n")
s = s.replace("    emit(nextCode);           // EOI", "    emitCode(nextCode);           // EOI")
io.open(p, "w", encoding="utf-8").write(s)
print("patched", s.count("emitCode"))
