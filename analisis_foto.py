"""
analisis_foto.py
================
Menunjukkan bahwa sebuah foto sebenarnya hanyalah kumpulan DATA dan ANGKA.

Yang dianalisis:
  A. Metadata  : nama file, format, resolusi, tanggal, kamera, ISO, aperture, dll.
  B. Data gambar: ukuran, jumlah piksel, nilai piksel, RGB, histogram, warna dominan, dll.
"""

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime

import numpy as np
from PIL import ExifTags, Image, ImageStat

# ----------------------------------------------------------------------
# Utilitas tampilan
# ----------------------------------------------------------------------
LEBAR = 70


def judul(teks):
    print("\n" + "=" * LEBAR)
    print(f" {teks}")
    print("=" * LEBAR)


def sub(teks):
    print(f"\n--- {teks} " + "-" * max(0, LEBAR - len(teks) - 5))


def baris(label, nilai):
    print(f"  {label:<34}: {nilai}")


def ukuran_file(byte):
    for satuan in ("B", "KB", "MB", "GB"):
        if byte < 1024:
            return f"{byte:,.2f} {satuan}"
        byte /= 1024
    return f"{byte:,.2f} TB"


def ke_float(v):
    """Ubah nilai EXIF (IFDRational / tuple) menjadi float."""
    try:
        return float(v)
    except Exception:
        try:
            return v[0] / v[1]
        except Exception:
            return None


# ----------------------------------------------------------------------
# Membaca EXIF
# ----------------------------------------------------------------------
def baca_exif(img):
    """Mengembalikan dict EXIF lengkap (IFD utama + Exif + GPS)."""
    hasil = {}
    try:
        exif = img.getexif()
    except Exception:
        return hasil

    # IFD utama (Make, Model, Software, DateTime, ...)
    for tag_id, nilai in exif.items():
        nama = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
        hasil[nama] = nilai

    # Exif IFD (ISO, aperture, shutter, focal length, ...)
    try:
        for tag_id, nilai in exif.get_ifd(ExifTags.IFD.Exif).items():
            nama = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
            hasil[nama] = nilai
    except Exception:
        pass

    # GPS IFD
    try:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if gps:
            hasil["GPSInfo"] = {
                ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()
            }
    except Exception:
        pass

    return hasil


def gps_ke_desimal(gps):
    try:
        def konversi(dms, ref):
            d, m, s = [float(x) for x in dms]
            nilai = d + m / 60 + s / 3600
            return -nilai if ref in ("S", "W") else nilai

        lat = konversi(gps["GPSLatitude"], gps["GPSLatitudeRef"])
        lon = konversi(gps["GPSLongitude"], gps["GPSLongitudeRef"])
        return lat, lon
    except Exception:
        return None


def tanggal_dari_nama(nama):
    """Cari pola tanggal di nama file"""
    m = re.search(r"(20\d{2}|19\d{2})(\d{2})(\d{2})[_-]?(\d{2})(\d{2})(\d{2})", nama)
    if not m:
        return None
    try:
        return datetime(*[int(x) for x in m.groups()])
    except ValueError:
        return None


# ----------------------------------------------------------------------
# BAGIAN A: METADATA
# ----------------------------------------------------------------------
def analisis_metadata(path, img, exif):
    judul("A. METADATA FOTO")

    # --- 1-3. File, format, resolusi
    sub("Informasi File")
    st = os.stat(path)
    baris("Nama file", os.path.basename(path))
    baris("Lokasi (path)", os.path.abspath(path))
    baris("Ukuran file", f"{ukuran_file(st.st_size)} ({st.st_size:,} byte)")
    baris("Format (PIL)", img.format)
    baris("MIME type", Image.MIME.get(img.format, "-"))
    baris("Mode warna", f"{img.mode}  ({len(img.getbands())} kanal: {', '.join(img.getbands())})")
    w, h = img.size
    baris("Resolusi (lebar x tinggi)", f"{w} x {h} piksel")
    baris("Orientasi", "Portrait (tegak)" if h > w else "Landscape (mendatar)" if w > h else "Persegi")
    baris("Dibuat (OS)", datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"))
    baris("Dimodifikasi (OS)", datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))

    # hash file
    with open(path, "rb") as f:
        isi = f.read()
    baris("MD5", hashlib.md5(isi).hexdigest())
    baris("SHA-256", hashlib.sha256(isi).hexdigest()[:32] + "...")

    dpi = img.info.get("dpi")
    if dpi:
        baris("DPI", f"{ke_float(dpi[0]):.0f} x {ke_float(dpi[1]):.0f}")
    if "progressive" in img.info or "progression" in img.info:
        baris("JPEG progressive", "Ya")
    if "icc_profile" in img.info:
        baris("Profil warna ICC", f"Ada ({len(img.info['icc_profile'])} byte)")

    if not exif:
        print("\n  [!] Tidak ada data EXIF (mungkin sudah dihapus oleh WhatsApp/medsos).")
        dt = tanggal_dari_nama(os.path.basename(path))
        if dt:
            sub("Tanggal Pengambilan (dari pola nama file)")
            hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][dt.weekday()]
            baris("Perkiraan waktu pengambilan", dt.strftime("%d-%m-%Y %H:%M:%S"))
            baris("Hari", hari)
            baris("Selisih dari sekarang", f"{(datetime.now() - dt).days} hari lalu")
        return

    # --- 4. Tanggal pengambilan
    sub("Tanggal & Waktu Pengambilan")
    for kunci in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        if kunci in exif:
            baris(kunci, exif[kunci])
    for kunci in ("OffsetTimeOriginal", "OffsetTime", "SubsecTimeOriginal"):
        if kunci in exif:
            baris(kunci, exif[kunci])
    tgl = exif.get("DateTimeOriginal") or exif.get("DateTime")
    if tgl:
        try:
            dt = datetime.strptime(str(tgl), "%Y:%m:%d %H:%M:%S")
            hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][dt.weekday()]
            baris("Hari", hari)
            baris("Format mudah dibaca", dt.strftime("%d-%m-%Y pukul %H:%M:%S"))
            baris("Selisih dari sekarang", f"{(datetime.now() - dt).days} hari lalu")
        except ValueError:
            pass

    # --- 5. Kamera
    sub("Kamera & Perangkat")
    for kunci in ("Make", "Model", "LensMake", "LensModel", "Software",
                  "BodySerialNumber", "LensSpecification"):
        if kunci in exif:
            baris(kunci, exif[kunci])

    # --- 6. Pengaturan eksposur
    sub("Pengaturan Eksposur")
    iso = exif.get("ISOSpeedRatings") or exif.get("PhotographicSensitivity")
    if iso is not None:
        baris("ISO", iso)

    et = ke_float(exif.get("ExposureTime"))
    if et:
        baris("Shutter speed", f"{et:.6f} detik  (~1/{round(1 / et)} detik)" if et < 1 else f"{et} detik")

    fn = ke_float(exif.get("FNumber"))
    if fn:
        baris("Aperture (F-number)", f"f/{fn:.1f}")

    fl = ke_float(exif.get("FocalLength"))
    if fl:
        baris("Focal length", f"{fl:.2f} mm")
    fl35 = exif.get("FocalLengthIn35mmFilm")
    if fl35:
        baris("Focal length (setara 35mm)", f"{fl35} mm")

    for kunci, label in [
        ("ExposureProgram", "Program eksposur"),
        ("ExposureMode", "Mode eksposur"),
        ("ExposureBiasValue", "Kompensasi eksposur (EV)"),
        ("MeteringMode", "Mode metering"),
        ("Flash", "Flash (kode)"),
        ("WhiteBalance", "White balance (0=auto,1=manual)"),
        ("SceneCaptureType", "Tipe scene"),
        ("BrightnessValue", "Brightness value"),
        ("ShutterSpeedValue", "Shutter speed value (APEX)"),
        ("ApertureValue", "Aperture value (APEX)"),
        ("MaxApertureValue", "Max aperture (APEX)"),
        ("DigitalZoomRatio", "Digital zoom"),
        ("LightSource", "Sumber cahaya"),
        ("SensingMethod", "Metode sensor"),
        ("SubjectDistance", "Jarak subjek"),
        ("Contrast", "Kontras"),
        ("Saturation", "Saturasi"),
        ("Sharpness", "Ketajaman"),
    ]:
        if kunci in exif:
            nilai = exif[kunci]
            f = ke_float(nilai) if not isinstance(nilai, (str, bytes)) else None
            baris(label, f"{f:.3f}" if isinstance(f, float) and not float(f).is_integer() else nilai)

    # Hitung Exposure Value (EV) dari angka-angka di atas
    if fn and et and iso:
        ev = np.log2(fn ** 2 / et)
        ev100 = ev - np.log2(float(iso) / 100)
        baris("Exposure Value (EV)", f"{ev:.2f}")
        baris("EV @ ISO 100", f"{ev100:.2f}   (<5 = gelap, 15 = siang terik)")

    # --- Ukuran piksel menurut EXIF
    sub("Dimensi Menurut EXIF")
    for kunci in ("ExifImageWidth", "ExifImageHeight", "PixelXDimension",
                  "PixelYDimension", "Orientation", "ColorSpace",
                  "XResolution", "YResolution", "ResolutionUnit",
                  "YCbCrPositioning", "ComponentsConfiguration",
                  "ExifVersion", "FlashPixVersion"):
        if kunci in exif:
            baris(kunci, exif[kunci])

    # --- GPS
    sub("Lokasi GPS")
    gps = exif.get("GPSInfo")
    if gps:
        pos = gps_ke_desimal(gps)
        if pos:
            baris("Latitude, Longitude", f"{pos[0]:.6f}, {pos[1]:.6f}")
            baris("Google Maps", f"https://maps.google.com/?q={pos[0]:.6f},{pos[1]:.6f}")
        for k, v in gps.items():
            if k not in ("GPSLatitude", "GPSLongitude"):
                baris(str(k), v)
    else:
        print("  Tidak ada data GPS.")

    # --- Sisa tag EXIF
    sub("Semua Tag EXIF Mentah")
    for k, v in sorted(exif.items(), key=lambda x: str(x[0])):
        if k in ("GPSInfo", "MakerNote", "UserComment", "PrintImageMatching"):
            continue
        teks = str(v)
        if len(teks) > 60:
            teks = teks[:57] + "..."
        baris(str(k), teks)
    if "MakerNote" in exif:
        baris("MakerNote", f"<data biner {len(exif['MakerNote'])} byte>")


# ----------------------------------------------------------------------
# BAGIAN B: DATA GAMBAR
# ----------------------------------------------------------------------
def analisis_data_gambar(img, x=None, y=None):
    judul("B. DATA GAMBAR (PIKSEL & ANGKA)")

    rgb = img.convert("RGB")
    arr = np.array(rgb)            # bentuk: (tinggi, lebar, 3)
    h, w, c = arr.shape
    total = h * w

    # --- 1-2. Ukuran & jumlah piksel
    sub("Ukuran & Jumlah Piksel")
    baris("Lebar", f"{w:,} piksel")
    baris("Tinggi", f"{h:,} piksel")
    baris("Jumlah piksel total", f"{total:,} piksel")
    baris("Megapiksel", f"{total / 1_000_000:.2f} MP")
    baris("Rasio aspek", f"{w / np.gcd(w, h):.0f}:{h / np.gcd(w, h):.0f}  (= {w / h:.4f})")
    baris("Jumlah kanal", f"{c}  (R, G, B)")
    baris("Jumlah angka (piksel x kanal)", f"{total * c:,} angka")
    baris("Bit per kanal", "8 bit  (rentang 0-255)")
    baris("Kemungkinan warna per piksel", f"{256 ** 3:,} warna  (256 x 256 x 256)")
    baris("Ukuran mentah di memori", ukuran_file(arr.nbytes))
    baris("Tipe data array", f"{arr.dtype}  ({arr.itemsize} byte/angka)")
    baris("Bentuk array (shape)", f"{arr.shape}  = (tinggi, lebar, kanal)")

    # --- 3. Nilai piksel
    sub("Nilai Piksel: Pojok Kiri-Atas (5 x 5), format [R G B]")
    for baris_px in arr[:5, :5]:
        print("   " + "  ".join(f"[{p[0]:3d} {p[1]:3d} {p[2]:3d}]" for p in baris_px))

    sub("Nilai Piksel: Tengah Gambar (5 x 5), format [R G B]")
    cy, cx = h // 2, w // 2
    for baris_px in arr[cy - 2:cy + 3, cx - 2:cx + 3]:
        print("   " + "  ".join(f"[{p[0]:3d} {p[1]:3d} {p[2]:3d}]" for p in baris_px))

    sub("Satu Piksel Tertentu")
    px = x if x is not None else cx
    py = y if y is not None else cy
    px = min(max(px, 0), w - 1)
    py = min(max(py, 0), h - 1)
    r, g, b = [int(v) for v in arr[py, px]]
    baris("Koordinat (x, y)", f"({px}, {py})")
    baris("Nilai RGB", f"({r}, {g}, {b})")
    baris("Hex", f"#{r:02X}{g:02X}{b:02X}")
    baris("Biner", f"{r:08b} {g:08b} {b:08b}")
    baris("Grayscale (luminansi)", f"{0.299 * r + 0.587 * g + 0.114 * b:.2f}")

    # --- 4. RGB per kanal
    sub("Statistik per Kanal RGB")
    print(f"  {'Kanal':<8}{'Min':>6}{'Max':>6}{'Rata2':>10}{'Median':>9}{'StdDev':>10}{'Varians':>12}")
    for i, nama in enumerate("RGB"):
        k = arr[:, :, i]
        print(f"  {nama:<8}{k.min():>6}{k.max():>6}{k.mean():>10.2f}"
              f"{np.median(k):>9.1f}{k.std():>10.2f}{k.var():>12.2f}")
    k_all = arr.reshape(-1)
    print(f"  {'Semua':<8}{k_all.min():>6}{k_all.max():>6}{k_all.mean():>10.2f}"
          f"{np.median(k_all):>9.1f}{k_all.std():>10.2f}{k_all.var():>12.2f}")

    rata = arr.reshape(-1, 3).mean(axis=0)
    baris("\n  Warna rata-rata gambar",
          f"RGB({rata[0]:.0f}, {rata[1]:.0f}, {rata[2]:.0f})  "
          f"#{int(rata[0]):02X}{int(rata[1]):02X}{int(rata[2]):02X}")

    # --- Kecerahan
    sub("Kecerahan, Kontras & Eksposur")
    gray = np.array(rgb.convert("L"), dtype=np.float64)
    baris("Kecerahan rata-rata (0-255)", f"{gray.mean():.2f}  ({gray.mean() / 255 * 100:.1f}%)")
    baris("Kontras (std. deviasi)", f"{gray.std():.2f}")
    baris("Rentang dinamis", f"{gray.min():.0f} - {gray.max():.0f}")
    gelap = (gray < 50).mean() * 100
    terang = (gray > 205).mean() * 100
    baris("Piksel sangat gelap (<50)", f"{gelap:.2f}%")
    baris("Piksel sangat terang (>205)", f"{terang:.2f}%")
    baris("Piksel 'terbakar' (=255)", f"{(gray >= 254).mean() * 100:.3f}%  (overexposed)")
    baris("Piksel hitam pekat (=0)", f"{(gray <= 1).mean() * 100:.3f}%  (underexposed)")
    kategori = ("Gelap (low-key)" if gray.mean() < 85
                else "Normal" if gray.mean() < 170 else "Terang (high-key)")
    baris("Kategori kecerahan", kategori)

    # --- Warna: saturasi, HSV
    sub("Warna: HSV & Saturasi")
    hsv = np.array(rgb.convert("HSV"), dtype=np.float64)
    baris("Hue rata-rata (0-255 -> 0-360 deg)", f"{hsv[:, :, 0].mean():.1f} -> {hsv[:, :, 0].mean() / 255 * 360:.1f} deg")
    baris("Saturasi rata-rata", f"{hsv[:, :, 1].mean() / 255 * 100:.2f}%")
    baris("Value (kecerahan HSV) rata-rata", f"{hsv[:, :, 2].mean() / 255 * 100:.2f}%")
    dom = "R (merah)" if rata.argmax() == 0 else "G (hijau)" if rata.argmax() == 1 else "B (biru)"
    baris("Kanal dominan", dom)
    baris("Piksel warna dominan R > G,B", f"{((arr[:, :, 0] > arr[:, :, 1]) & (arr[:, :, 0] > arr[:, :, 2])).mean() * 100:.2f}%")
    baris("Piksel warna dominan G > R,B", f"{((arr[:, :, 1] > arr[:, :, 0]) & (arr[:, :, 1] > arr[:, :, 2])).mean() * 100:.2f}%")
    baris("Piksel warna dominan B > R,G", f"{((arr[:, :, 2] > arr[:, :, 0]) & (arr[:, :, 2] > arr[:, :, 1])).mean() * 100:.2f}%")

    # --- Warna unik & dominan
    sub("Warna Unik & Palet Dominan")
    flat = arr.reshape(-1, 3)
    kode = (flat[:, 0].astype(np.uint32) << 16) | (flat[:, 1].astype(np.uint32) << 8) | flat[:, 2]
    unik = np.unique(kode)
    baris("Jumlah warna unik", f"{len(unik):,}  dari {total:,} piksel ({len(unik) / total * 100:.2f}%)")

    kuant = rgb.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = kuant.getpalette()[:24]
    hitung = np.bincount(np.array(kuant).reshape(-1), minlength=8)
    urut = np.argsort(-hitung)
    print(f"\n  {'#':<3}{'RGB':<20}{'HEX':<10}{'Jumlah piksel':>15}{'Persen':>9}  Bar")
    for no, i in enumerate(urut, 1):
        rr, gg, bb = pal[i * 3:i * 3 + 3]
        persen = hitung[i] / total * 100
        print(f"  {no:<3}({rr:3d},{gg:3d},{bb:3d})".ljust(25)
              + f"#{rr:02X}{gg:02X}{bb:02X}".ljust(10)
              + f"{hitung[i]:>15,}{persen:>8.2f}%  " + "█" * int(persen / 2))

    # --- Histogram teks
    sub("Histogram Kecerahan (16 bin)")
    hist, tepi = np.histogram(gray, bins=16, range=(0, 256))
    maks = hist.max()
    for i, jml in enumerate(hist):
        print(f"  {int(tepi[i]):3d}-{int(tepi[i + 1]) - 1:3d} | "
              f"{'█' * int(jml / maks * 40):<40} {jml:>10,} ({jml / total * 100:5.2f}%)")

    # --- Ketajaman & noise
    sub("Ketajaman & Noise (perkiraan)")
    gx = np.diff(gray, axis=1)
    gy = np.diff(gray, axis=0)
    tepi_mag = np.sqrt(gx[:-1, :] ** 2 + gy[:, :-1] ** 2)
    baris("Rata-rata kekuatan tepi (gradien)", f"{tepi_mag.mean():.3f}")
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    baris("Variansi Laplacian (ketajaman)", f"{lap.var():.2f}   (makin besar = makin tajam)")
    baris("Persentase piksel tepi (>30)", f"{(tepi_mag > 30).mean() * 100:.2f}%")

    # --- Entropi
    p = hist / hist.sum()
    p = p[p > 0]
    h256, _ = np.histogram(gray, bins=256, range=(0, 256))
    p256 = h256 / h256.sum()
    p256 = p256[p256 > 0]
    entropi = -(p256 * np.log2(p256)).sum()
    baris("Entropi Shannon", f"{entropi:.4f} bit  (maks 8.0 = sangat acak/detail)")

    # --- Kompresi
    return arr, gray


def info_kompresi(path, arr):
    sub("Informasi Kompresi")
    baris("Ukuran mentah (tanpa kompresi)", ukuran_file(arr.nbytes))
    ukuran = os.path.getsize(path)
    baris("Ukuran file terkompresi", ukuran_file(ukuran))
    baris("Rasio kompresi", f"{arr.nbytes / ukuran:.1f} : 1")
    baris("Penghematan", f"{(1 - ukuran / arr.nbytes) * 100:.2f}%")
    baris("Bit per piksel (bpp)", f"{ukuran * 8 / (arr.shape[0] * arr.shape[1]):.3f}")


# ----------------------------------------------------------------------
# Wilayah gambar (grid 3x3)
# ----------------------------------------------------------------------
def analisis_grid(arr):
    sub("Rata-rata Warna per Wilayah (grid 3 x 3)")
    h, w, _ = arr.shape
    nama = [["Kiri-Atas", "Tengah-Atas", "Kanan-Atas"],
            ["Kiri-Tengah", "Tengah", "Kanan-Tengah"],
            ["Kiri-Bawah", "Tengah-Bawah", "Kanan-Bawah"]]
    for i in range(3):
        for j in range(3):
            blok = arr[i * h // 3:(i + 1) * h // 3, j * w // 3:(j + 1) * w // 3]
            m = blok.reshape(-1, 3).mean(axis=0)
            kec = (0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2])
            print(f"  {nama[i][j]:<14} RGB({m[0]:6.1f},{m[1]:6.1f},{m[2]:6.1f})  "
                  f"#{int(m[0]):02X}{int(m[1]):02X}{int(m[2]):02X}  kecerahan {kec:6.1f}")


# ----------------------------------------------------------------------
# Visualisasi
# ----------------------------------------------------------------------
def buat_grafik(img, arr, gray, path, x=None, y=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h, w, _ = arr.shape
    cy, cx = h // 2, w // 2
    px = x if x is not None else cx
    py = y if y is not None else cy

    fig = plt.figure(figsize=(16, 11))
    fig.suptitle(f"Foto = Data & Angka  |  {os.path.basename(path)}  |  {w}x{h} px",
                 fontsize=15, fontweight="bold")

    # 1. Gambar asli
    ax = fig.add_subplot(2, 4, 1)
    ax.imshow(arr)
    ax.set_title("1. Gambar asli (matriks angka)")
    ax.axis("off")

    # 2. Kanal R, G, B
    for i, (nama, cmap) in enumerate([("Merah (R)", "Reds"), ("Hijau (G)", "Greens"), ("Biru (B)", "Blues")]):
        ax = fig.add_subplot(2, 4, 2 + i)
        ax.imshow(arr[:, :, i], cmap=cmap, vmin=0, vmax=255)
        ax.set_title(f"{i + 2}. Kanal {nama}")
        ax.axis("off")

    # 5. Histogram RGB
    ax = fig.add_subplot(2, 4, 5)
    for i, warna in enumerate(["red", "green", "blue"]):
        hist, _ = np.histogram(arr[:, :, i], bins=256, range=(0, 256))
        ax.plot(hist, color=warna, alpha=0.8, linewidth=1)
        ax.fill_between(range(256), hist, color=warna, alpha=0.15)
    ax.set_title("5. Histogram RGB")
    ax.set_xlabel("Nilai piksel (0-255)")
    ax.set_ylabel("Jumlah piksel")
    ax.set_xlim(0, 255)

    # 6. Grayscale
    ax = fig.add_subplot(2, 4, 6)
    ax.imshow(gray, cmap="gray", vmin=0, vmax=255)
    ax.set_title("6. Grayscale (1 angka/piksel)")
    ax.axis("off")

    # 7. Zoom 12x12 piksel dengan angka
    n = 12
    y0 = int(np.clip(py - n // 2, 0, h - n))
    x0 = int(np.clip(px - n // 2, 0, w - n))
    zoom = arr[y0:y0 + n, x0:x0 + n]
    ax = fig.add_subplot(2, 4, 7)
    ax.imshow(zoom, interpolation="nearest")
    ax.set_title(f"7. Zoom {n}x{n} piksel @({x0},{y0})")
    ax.set_xticks([]), ax.set_yticks([])
    # tampilkan angka R di tiap piksel
    for i in range(n):
        for j in range(n):
            lum = 0.299 * zoom[i, j, 0] + 0.587 * zoom[i, j, 1] + 0.114 * zoom[i, j, 2]
            ax.text(j, i, str(zoom[i, j, 0]), ha="center", va="center", fontsize=5,
                    color="white" if lum < 128 else "black")
    ax.set_xlabel("angka = nilai Red tiap piksel", fontsize=8)

    # 8. Palet warna dominan
    ax = fig.add_subplot(2, 4, 8)
    kuant = img.convert("RGB").quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = np.array(kuant.getpalette()[:24]).reshape(8, 3)
    hitung = np.bincount(np.array(kuant).reshape(-1), minlength=8)
    urut = np.argsort(-hitung)
    for k, i in enumerate(urut):
        ax.barh(k, hitung[i] / hitung.sum() * 100, color=pal[i] / 255)
        ax.text(hitung[i] / hitung.sum() * 100 + 0.5, k,
                f"#{pal[i][0]:02X}{pal[i][1]:02X}{pal[i][2]:02X}", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_title("8. Palet 8 warna dominan")
    ax.set_xlabel("% piksel")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    keluar = os.path.splitext(os.path.basename(path))[0] + "_analisis.png"
    plt.savefig(keluar, dpi=130)
    plt.close()
    return keluar


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Analisis foto: metadata + data piksel")
    ap.add_argument("foto", help="path file foto (jpg/png/dll)")
    ap.add_argument("--x", type=int, help="koordinat x piksel yang ingin dilihat")
    ap.add_argument("--y", type=int, help="koordinat y piksel yang ingin dilihat")
    ap.add_argument("--no-plot", action="store_true", help="jangan buat grafik")
    args = ap.parse_args()

    if not os.path.isfile(args.foto):
        sys.exit(f"File tidak ditemukan: {args.foto}")

    img = Image.open(args.foto)
    exif = baca_exif(img)

    print("#" * LEBAR)
    print("#  ANALISIS FOTO: SEBUAH GAMBAR ADALAH KUMPULAN ANGKA".ljust(LEBAR - 1) + "#")
    print("#" * LEBAR)

    analisis_metadata(args.foto, img, exif)
    arr, gray = analisis_data_gambar(img, args.x, args.y)
    info_kompresi(args.foto, arr)
    analisis_grid(arr)

    if not args.no_plot:
        try:
            keluar = buat_grafik(img, arr, gray, args.foto, args.x, args.y)
            judul("GRAFIK")
            baris("Grafik disimpan ke", keluar)
        except ImportError:
            print("\n[!] matplotlib belum terpasang: pip install matplotlib")

    judul("KESIMPULAN")
    h, w, _ = arr.shape
    print(f"  Foto ini = {w * h:,} piksel x 3 kanal = {w * h * 3:,} angka (0-255).")
    print("  Tidak ada 'gambar' sama sekali di dalam komputer, hanya deretan angka")
    print("  yang ditafsirkan layar menjadi cahaya berwarna.\n")


if __name__ == "__main__":
    main()
