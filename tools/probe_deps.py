import pefile, os, sys
p = r"C:\Users\laiki\.dsh\workspace\tackshot\build\ort_probe.exe"
pe = pefile.PE(p, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
for e in pe.DIRECTORY_ENTRY_IMPORT:
    d = e.dll.decode()
    here = os.path.join(os.path.dirname(p), d)
    sys32 = os.path.join(r"C:\Windows\System32", d)
    print("%-40s appdir=%s system32=%s" % (d, os.path.exists(here), os.path.exists(sys32)))
