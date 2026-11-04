import pefile, os, sys
sys.path.insert(0, r"C:\Users\laiki\.dsh\workspace\re_test123\pylibs")
p = r"C:\Users\laiki\.dsh\workspace\tackshot\toolchain\ort\onnxruntime-win-x64-1.31.1\lib\onnxruntime.dll"
pe = pefile.PE(p, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
deps = [e.dll.decode() for e in pe.DIRECTORY_ENTRY_IMPORT]
print("deps:", deps)
missing = []
for d in deps:
    found = False
    for base in [r"C:\Windows\System32", r"C:\Windows\SysWOW64"]:
        if os.path.exists(os.path.join(base, d)):
            found = True; break
    if not found:
        missing.append(d)
print("missing from System32:", missing)
