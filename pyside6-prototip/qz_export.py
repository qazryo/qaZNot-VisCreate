"""qaZNot dışa aktarma ve yazdırma: biçimli PDF, HTML, yazıcı (QtPrintSupport)."""
import os

from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import QFileDialog, QApplication

APP = "qaZNot"


class ExportMixin:
    def _export_doc(self):
        """Ekrandaki belgenin kopyası (yakınlaştırma/geçerli düzen etkilenmesin)."""
        return self.editor.document().clone()

    def _base_name(self):
        return os.path.splitext(self.filename)[0] if self.filename else "belge"

    def write_pdf(self, path):
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        pr.setOutputFileName(path)
        pr.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        pr.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter)
        self._export_doc().print_(pr)

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "PDF olarak dışa aktar", self._base_name() + ".pdf", "PDF (*.pdf)")
        if not path:
            return False
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.write_pdf(path)
        except Exception as e:  # noqa: BLE001
            self.error(f"PDF oluşturulamadı:\n{e}")
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.toast(f"PDF kaydedildi: {os.path.basename(path)}")
        return True

    def write_html(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._export_doc().toHtml())

    def export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "HTML olarak dışa aktar", self._base_name() + ".html", "HTML (*.html)")
        if not path:
            return False
        if not path.lower().endswith((".html", ".htm")):
            path += ".html"
        try:
            self.write_html(path)
        except OSError as e:
            self.error(f"HTML kaydedilemedi:\n{e}")
            return False
        self.toast(f"HTML kaydedildi: {os.path.basename(path)}")
        return True

    def print_file(self):
        """Biçimli yazdırma (yazıcı penceresi açılır)."""
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        pr.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter)
        dlg = QPrintDialog(pr, self)
        dlg.setWindowTitle("Yazdır")
        if dlg.exec() == QPrintDialog.DialogCode.Accepted:
            try:
                self._export_doc().print_(pr)
                self.toast("Yazdırma gönderildi")
            except Exception as e:  # noqa: BLE001
                self.error(f"Yazdırılamadı:\n{e}")
