import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
sys.argv = ["x"]
import qanvas_proto as q
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(q.QSS)
w = q.MainWindow()
w.show()
app.processEvents()
w.view.fit()
app.processEvents()
vp = w.view.viewport()


def vpos(sx, sy):
    return w.view.mapFromScene(QPointF(sx, sy))


ok = []


def check(name, cond):
    ok.append(cond)
    print(("OK   " if cond else "FAIL ") + name)


n0 = len(w.layer_items())

# 1) dikdortgen aracıyla çiz
w.set_tool("rect")
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(100, 560))
QTest.mouseMove(vp, vpos(260, 640))
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(260, 640))
app.processEvents()
check("cizim: katman eklendi", len(w.layer_items()) == n0 + 1)
c = w.cur
check("cizim: secili ve arac select", c is not None and w.tool == "select")
check("cizim: boyut ~160x80", c is not None and abs(c.w - 160) < 3 and abs(c.h - 80) < 3)

# 2) sag-alt tutamaçtan yeniden boyutla
x, y, cw, ch = c.pos().x(), c.pos().y(), c.w, c.h
a = vpos(x + cw, y + ch)
b = vpos(x + cw + 80, y + ch + 40)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
QTest.mouseMove(vp, b)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
app.processEvents()
check("resize: genislik arttı", c.w > cw + 60)

# 3) tasi
p0 = c.pos()
a = vpos(x + 20, y + 20)
b = vpos(x + 120, y + 20)
QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
QTest.mouseMove(vp, b)
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
app.processEvents()
check("tasima: x degisti", c.pos().x() > p0.x() + 50)
check("panel X guncel", abs(w.sx.value() - round(c.pos().x())) < 1)

# 4) panelden deger
w.sw.setValue(300)
check("panel -> genislik", abs(c.w - 300) < 0.5)
w.so.setValue(50)
check("panel -> opaklik", abs(c.opacity() - 0.5) < 0.01)

# 5) katman listesinden secim
w.scene.clearSelection()
li = w.layers.item(0)
li.setSelected(True)
app.processEvents()
check("liste -> sahne secimi", w.cur is not None and w.cur.name == li.text())

# 6) kopya, sil, z-sirasi
w.duplicate()
app.processEvents()
check("kopya", len(w.layer_items()) == n0 + 2)
w.delete_selected()
check("sil", len(w.layer_items()) == n0 + 1)
w.layers.item(w.layers.count() - 1).setSelected(True)
app.processEvents()
w.reorder(+1)
check("one getir", w.layers.item(0).data(Qt.ItemDataRole.UserRole).isSelected())

# 7) yakinlastirma
z0 = w.view.zoom()
w.view.zoom_by(1.25, False)
check("zoom", w.view.zoom() > z0 * 1.2)

# 8) metin araci
w.set_tool("text")
QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpos(900, 600))
app.processEvents()
check("metin: tek tikla varsayilan boyut", w.cur is not None and w.cur.kind == "text" and w.cur.w >= 200)

print("SONUC:", sum(ok), "/", len(ok))
os._exit(0 if all(ok) else 1)
