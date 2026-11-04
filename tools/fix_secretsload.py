import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    if (secretsLoaded()) {}\n", """    {
        QString vid = Config::get().visionProvider;
        QString vk = secrets::load("vision_api_key_" + vid);
        if (!vk.isEmpty()) m_visionKey->setText(vk);
    }
""")
io.open(p, "w", encoding="utf-8").write(s)
print("vision key load fixed:", "secretsLoaded" not in s)
