import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\audiocap.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""bool isFloatFormat(const WAVEFORMATEX* f) {""",
"""// KSDATAFORMAT_SUBTYPE_IEEE_FLOAT = {00000003-0000-0010-8000-00AA00389B71}
static const GUID kFloatSubtype =
    {0x00000003, 0x0000, 0x0010, {0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71}};

bool isFloatFormat(const WAVEFORMATEX* f) {""")
s = s.replace("        return e->SubFormat == KSDATAFORMAT_SUBTYPE_IEEE_FLOAT;",
              "        return IsEqualGUID(e->SubFormat, kFloatSubtype) != 0;")
io.open(p, "w", encoding="utf-8").write(s)
print("guid fixed")
