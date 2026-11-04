import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("outType->SetUINT32(MF_MT_MPEG2_PROFILE, eAVEncH264VProfile_Main);",
              "outType->SetUINT32(MF_MT_MPEG2_PROFILE, 77);   // eAVEncH264VProfile_Main")
io.open(p, "w", encoding="utf-8").write(s)
print("ok")
