Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Image]::FromFile("C:\Users\laiki\.dsh\workspace\tackshot\build\snap.png")
"CropLeft source = " + $src.Width + "x" + $src.Height
$dst = New-Object System.Drawing.Bitmap(2560, 1440)
$g = [System.Drawing.Graphics]::FromImage($dst)
$g.DrawImage($src, (New-Object System.Drawing.Rectangle(0, 0, 2560, 1440)), (New-Object System.Drawing.Rectangle(0, 0, 2560, 1440)), [System.Drawing.GraphicsUnit]::Pixel)
$g.Dispose()
$dst.Save("C:\Users\laiki\.dsh\workspace\tackshot\build\snap_left.png", [System.Drawing.Imaging.ImageFormat]::Png)
$dst.Dispose(); $src.Dispose()
"ok"
