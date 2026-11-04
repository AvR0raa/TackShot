import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 在 connect 之前声明挂起状态
s = s.replace("""    // 译图：逐行翻译后把译文渲染回原图，再作为贴图钉住
    connect(trImgBtn, &QPushButton::clicked, [&]() {""",
"""    // 译图：先关对话框，等 exec() 返回后再钉图（避免在对话框回调里销毁 Overlay 导致崩溃）
    QImage pinImg;
    bool pinPending = false;

    connect(trImgBtn, &QPushButton::clicked, [&]() {""")

# 2) 不再直接 emit / close
s = s.replace("""        QImage composed = renderTranslated(img, lines, translated);
        emit pinRequested(composed);
        close();
        emit closed();
    });

    dlg.exec();
}""",
"""        pinImg = renderTranslated(img, lines, translated);
        pinPending = true;
        dlg.accept();
    });

    dlg.exec();

    if (pinPending) {
        emit pinRequested(pinImg);
        close();
        emit closed();
    }
}""")
io.open(p, "w", encoding="utf-8").write(s)
print("pin crash fixed")
