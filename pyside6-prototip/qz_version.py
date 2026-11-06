"""qaZNot sürüm bilgisi ve sürüm geçmişi (Yardım > Sürüm Geçmişi)."""
CODENAME = "VisCreate"
VERSION = "0.3_061126_var1"
BUILD_DATE = "06.11.2026"


def version_number(v=VERSION):
    """'0.3_061126_var1' -> (0, 3, 0): karşılaştırma için yalnızca sayısal kısım."""
    return tuple(int(x) for x in v.split("_")[0].split(".") if x.isdigit())


# (sürüm, tarih, başlık, maddeler) - en yeni başta
HISTORY = [
    ("0.3_061126_var1", "06.11.2026", "VisCreate", [
        "Kod adı: VisCreate. Sürüm biçimi: <sürüm>_<gg><aa><yy>_var<n>.",
        "Güncelleme denetimi sürüm biçimini anlar (sayısal kısım karşılaştırılır).",
    ]),
    ("2.1.0", "03.11.2026", "Sekmeler, şifreleme, dışa aktarma", [
        "Sekmeler: tek pencerede birden fazla belge (Ctrl+N yeni sekme, Ctrl+W kapat, Ctrl+Tab geçiş).",
        "Dosya ilişkilendirme: .qaz dosyasına çift tıklayınca qaZNot açılır (Yardım menüsünden açılıp kapatılır, kurucu da ayarlar).",
        "Tek kopya: qaZNot zaten açıksa dosyalar var olan pencerede yeni sekmede açılır; dosyaları pencereye sürükleyebilirsin.",
        "Bul/değiştir: tam sözcük, düzenli ifade (regex, \\1 grup desteğiyle), başa sarma. Ana ekranda belge içeriğinde arama.",
        "Biçimli PDF ve HTML dışa aktarma, biçimli yazdırma.",
        "Madde işaretli ve numaralı listeler, girinti, satır aralığı; nota resim ekleme (yapıştır, sürükle, menü).",
        "Belge şifreleme (AES-256-GCM): Dosya > Şifre Ayarla. Şifreli belgenin geçmişi ve taslağı düz metin saklanmaz.",
        "Belge geçmişi: her kayıtta kopya saklanır (20 adet), istediğin sürüme dönebilirsin.",
        "Odak modu (F11), kelime hedefi, ayarlar penceresi, klavye kısayolu listesi, sistem temasını takip etme.",
        "Güvenlik: lisans anahtarı artık settings.json'da düz metin değil, Windows ile şifreli saklanır.",
        "Hata kaydı (Yardım > Hata Kaydını Aç) ve güncelleme denetimi (update_url ayarlanırsa).",
        "qAnvas: katman kopyala/kes/yapıştır (belgeler arası dahil), eşit dağıtma, gradyan dolgu, tuvalde metni çift tıklayıp düzenleme, PDF dışa aktarma.",
        "Windows kurucusu (qaZNot-Kurulum): masaüstü kısayolu, başlat menüsü, kaldırıcı.",
    ]),
    ("2.0.0", "03.11.2026", "PySide6 sürümü", [
        "Uygulamanın tamamı Tkinter'den PySide6'ya taşındı; her yerde yeni arayüz.",
        "Açılışta önce başlangıç ekranı (menü) gelir: yeni belge, aç, sabitlenen ve son belgeler, klasördeki dosyalar.",
        "Tüm düğmelerde, pencerelerde ve sayfa geçişlerinde animasyon; giriş ekranında süzülen daireler.",
        "Biçimlendirme (yazı tipi, renk, hizalama) artık Ctrl+Z / Ctrl+Y ile geri alınabilir.",
        "Yakınlaştırma yazı biçimini değiştirmeden çalışır (Ctrl+tekerlek, Ctrl+Artı/Eksi).",
        "Yazı tipi listesi her yazı tipini kendi görünüşüyle gösterir.",
        "qAnvas aynı programın içinde açılır; metni köşeden çekince yazı da büyür/küçülür.",
        "qAnvas: geri al/yinele, hizalama, akıllı kılavuz çizgileri, çizgi aracı, PNG/JPG dışa aktarma.",
        "Eski .qaz belgeleriyle ve imzalarla tam uyumlu; hesap ve ayarlar eski sürümle ortak.",
    ]),
    ("1.1.0", "02.11.2026", "qAnvas geliştirmeleri (Tkinter)", [
        "qAnvas'ta metin yazarken yazı tipi çubuğu (yazı tipi, boyut, kalın, italik, hizalama, renk).",
        "Yüklemeler paneli: dosya seç, panodan yapıştır (Ctrl+Shift+V), sürükle-bırak.",
        "İnternet şablonları (açık lisanslı kaynaklardan), eksik Google yazı tipleri otomatik iner.",
        "Büyük görseller yakınlaştırmada yalnızca görünen kısım kadar çizilir.",
    ]),
    ("1.0.0", "Ekim 2026", "İlk sürüm (Tkinter)", [
        "Temalı, zengin metin destekli not defteri; .qaz biçimi ve düz metin (.txt).",
        "Lisans anahtarına bağlı hesaplar: Core, Enterprise, Professional.",
        "9 tema, Google hesabı bağlama, Discord'da durum gösterme.",
        "Başlangıç ekranı, taslak kurtarma, bul/değiştir, belge imzalama (Professional).",
        "qAnvas: basit tasarım editörü (Core'da 3 hazır boyut; Enterprise/Professional'da şablonlar ve özel boyut).",
    ]),
]


def history_html(T):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
    parts = [f"<body style='color:{T['fg']};'>"]
    for i, (v, date, title, items) in enumerate(HISTORY):
        cur = f" <span style='color:{T['accent']};'>(şu anki)</span>" if v == VERSION else ""
        parts.append(f"<h3 style='margin-bottom:0;'>Sürüm {v}{cur}</h3>"
                     f"<div style='color:{T['muted']};'>{esc(date)} · {esc(title)}</div><ul style='margin-top:4px;'>")
        parts += [f"<li>{esc(x)}</li>" for x in items]
        parts.append("</ul>")
    parts.append("</body>")
    return "".join(parts)
