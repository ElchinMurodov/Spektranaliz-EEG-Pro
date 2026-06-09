"""
Spektranaliz EEG Pro — Sportchining EEG signallarini spektral tahlil qilish (GUI).

Bu dastur IKKI loyihaning birlashmasi va optimallashtirilgan ko'rinishi:
  * Dizayn va dastur tuzilishi  -> Spektranaliz-EEG-installation7 (Tkinter GUI,
    fon rasmi, logotip, .exe ga yig'ish).
  * Tahlil algoritmi (yadro)    -> eeg_engine paketi, u installation7 va
    EEG-signal-edf-bdf algoritmlarini birlashtiradi (iAPF, FAA, FMT,
    engagement, dominant chastota, spektral chegara, harmonizatsiya,
    individual kalibrlash, 8 funksional holat, HTML/SVG topomap).

GUI faqat ko'rinish (presentation) qatlami; barcha hisob-kitob eeg_engine da.
Yuqoridagi menyu orqali qo'shimcha imkoniyatlar (HTML hisobot, individual
kalibrlash, harmonizatsiya) mavjud.
"""

import io
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox

from PIL import Image, ImageDraw, ImageTk

# Tahlil yadrosi (sof Python; numpy/scipy/pyedflib/mne bo'lsa avtomatik tezlashadi)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eeg_engine import (analyze_objects, export_html, export_pdf, export_txt,
                        calibration, config)
from eeg_engine import charts


def resource_path(relative_path):
    """Resurs faylning to'liq yo'lini qaytaradi (.py va PyInstaller .exe uchun ham)."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


APP_NAME = "Spektranaliz EEG Pro"
ICON_PATH = resource_path("spektranaliz-eeg-icon.ico")

LOGO_LIGHT_PNG = resource_path("spektranaliz-eeg-logo.png")
LOGO_DARK_PNG = resource_path("spektranaliz-eeg-logo-dark.png")
LOGO_LIGHT_PATH = resource_path("spektranaliz-eeg-logo.svg")
LOGO_DARK_PATH = resource_path("spektranaliz-eeg-logo-dark.svg")
LOGO_ASPECT = 1320.0 / 420.0

BACKGROUND_PATH = resource_path("EEG spectrum background 700x700.svg")
BACKGROUND_FALLBACK_PATHS = [
    resource_path("EEG-spectrum-background-730x730.png"),
    resource_path("EEG spectrum background 685x685.jpg"),
]
WINDOW_W, WINDOW_H = 700, 700
LAYOUT_W, LAYOUT_H = 700, 700

try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.LANCZOS


class EEGSpektralTahlilDasturi:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.minsize(600, 600)
        self.root.resizable(True, True)
        self.set_window_icon()

        self.selected_file = None
        self.baseline_file = None      # individual kalibrlash uchun tinch holat
        self.baseline_features = None
        self.target_fs = None          # harmonizatsiya chastotasi (None = o'chiq)
        self.last_objs = None          # oxirgi tahlil jonli obyektlari (eksport uchun)
        self.report_image_full = None  # natija posteri (PIL, to'liq o'lcham)
        self.report_photo = None       # ko'rsatilayotgan (masshtablangan) rasm
        self.result_view_w = 460       # natija oynasi ichki kengligi (redraw yangilaydi)
        self.resize_job = None

        self.bg_path = BACKGROUND_PATH
        self.bg_is_svg = os.path.splitext(self.bg_path)[1].lower() == ".svg"
        self.bg_size = self.get_svg_size(self.bg_path) if self.bg_is_svg else None
        self.bg_original = None if self.bg_is_svg else Image.open(self.bg_path).convert("RGB")
        self.bg_fallback_original = self.load_background_fallback()
        self.bg_photo = None
        self.bg_error_shown = False

        self.build_menu()

        # --- Pastki eksport paneli (HTML / PDF / TXT) ---
        # side="bottom" bilan joylanadi, shuning uchun asosiy canvas dizayni
        # (koordinatalar matematikasi) buzilmaydi.
        self.toolbar = tk.Frame(root, bg="#0e2a3a")
        self.toolbar.pack(side="bottom", fill="x")
        tk.Label(self.toolbar, text="  Natijani eksport qilish:", bg="#0e2a3a",
                 fg="#cfe6f2", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 4), pady=6)
        self._make_export_button(self.toolbar, "HTML", "#2f80d8", self.save_html)
        self._make_export_button(self.toolbar, "PDF", "#c0392b", self.save_pdf)
        self._make_export_button(self.toolbar, "TXT", "#4f972d", self.save_text)

        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_id = self.canvas.create_image(0, 0, anchor="nw")

        self.logo_photo = None
        self.logo_cache = {}
        self.logo_id = self.canvas.create_image(0, 0, anchor="center")

        self.title_id = self.canvas.create_text(
            0, 0,
            text="Sportchining Elektroensefalografik(EEG) signallarini spektral tahlil qilish",
            fill="red", justify="center",
        )

        self.upload_label_id = self.canvas.create_text(
            0, 0,
            text="Elektroensefalografik(EEG) signal faylini yuklang:",
            fill="black", justify="center",
        )

        self.file_shadow = self.rounded_rect(0, 0, 1, 1, 1, fill="#b9dede", outline="")
        self.file_panel = self.rounded_rect(0, 0, 1, 1, 1, fill="#fbffff", outline="#f0a000", width=2)
        self.file_label_id = self.canvas.create_text(0, 0, text="Faylni tanlash:", fill="#777777")

        self.file_btn_shadow = self.rounded_rect(0, 0, 1, 1, 1, fill="#b8c2ce", outline="", tags="file_btn")
        self.file_btn = self.rounded_rect(0, 0, 1, 1, 1, fill="#f7f9fc", outline="#7d8795", width=1, tags="file_btn")
        self.file_btn_highlight = self.rounded_rect(0, 0, 1, 1, 1, fill="#ffffff", outline="", tags="file_btn")
        self.file_icon_photo = None
        self.file_icon_id = self.canvas.create_image(0, 0, anchor="center", tags="file_btn")
        self.file_btn_text = self.canvas.create_text(0, 0, text="Fayl tanlash", fill="#111111", tags="file_btn")

        self.main_shadow = self.rounded_rect(0, 0, 1, 1, 1, fill="#144e8d", outline="")
        self.main_btn = self.rounded_rect(0, 0, 1, 1, 1, fill="#2f80d8", outline="#1d5fa8", width=2, tags="result_btn")
        self.main_highlight = self.rounded_rect(0, 0, 1, 1, 1, fill="#4d9be6", outline="", tags="result_btn")
        self.main_text = self.canvas.create_text(0, 0, text="Natijani olish", fill="white", tags="result_btn")

        self.result_title_id = self.canvas.create_text(
            0, 0,
            text="Elektroensefalografik(EEG) spektral natijasi:",
            fill="black", justify="center",
        )

        self.result_shadow = self.rounded_rect(0, 0, 1, 1, 1, fill="#9fd6cf", outline="")
        self.result_panel = self.rounded_rect(0, 0, 1, 1, 1, fill="#eaffff", outline="#4f972d", width=2)
        self.placeholder_id = self.canvas.create_text(0, 0, text="Natijalar oynasi", fill="#837777", justify="center")

        # --- Natijalar oynasi: chiroyli grafiklarni ko'rsatuvchi varaqlanadigan soha ---
        self.result_view = tk.Frame(root, bg="#eaffff", highlightthickness=0)
        self.result_scroll = tk.Scrollbar(self.result_view, orient="vertical")
        self.chart_canvas = tk.Canvas(self.result_view, bg="#eaffff", highlightthickness=0,
                                      yscrollcommand=self.result_scroll.set)
        self.result_scroll.config(command=self.chart_canvas.yview)
        self.result_scroll.pack(side="right", fill="y")
        self.chart_canvas.pack(side="left", fill="both", expand=True)
        self.chart_img_id = self.chart_canvas.create_image(0, 0, anchor="nw")
        self.result_view_id = self.canvas.create_window(0, 0, window=self.result_view,
                                                        state="hidden", anchor="center")
        # Sichqoncha g'ildiragi bilan varaqlash
        self.chart_canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.chart_canvas.bind("<Leave>", lambda e: self._bind_wheel(False))

        self.status_id = self.canvas.create_text(0, 0, text="", fill="#1f4f5a", justify="center")
        self.copyright_id = self.canvas.create_text(
            0, 0, text="©" + config.AUTHOR, fill="#1f4f5a", justify="center",
        )

        self.canvas.tag_bind("file_btn", "<Enter>", lambda event: self.hover_file(True))
        self.canvas.tag_bind("file_btn", "<Leave>", lambda event: self.hover_file(False))
        self.canvas.tag_bind("file_btn", "<Button-1>", lambda event: self.select_file())

        self.canvas.tag_bind("result_btn", "<Enter>", lambda event: self.hover_result(True))
        self.canvas.tag_bind("result_btn", "<Leave>", lambda event: self.hover_result(False))
        self.canvas.tag_bind("result_btn", "<Button-1>", lambda event: self.analyze_eeg())

        self.root.bind("<Configure>", self.on_resize)
        self.root.after(100, self.redraw)

    # ------------------------------------------------------------------
    # Yuqori menyu (qo'shimcha imkoniyatlar — dizaynni buzmaydi)
    # ------------------------------------------------------------------
    def build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="EEG fayl tanlash...", command=self.select_file)
        file_menu.add_command(label="Natijani olish", command=self.analyze_eeg)
        file_menu.add_separator()
        file_menu.add_command(label="HTML hisobotni saqlash...", command=self.save_html)
        file_menu.add_command(label="PDF hisobotni saqlash...", command=self.save_pdf)
        file_menu.add_command(label="Matnli (TXT) hisobotni saqlash...", command=self.save_text)
        file_menu.add_separator()
        file_menu.add_command(label="Chiqish", command=self.root.quit)
        menubar.add_cascade(label="Fayl", menu=file_menu)

        tool_menu = tk.Menu(menubar, tearoff=0)
        tool_menu.add_command(label="Individual kalibrlash: baseline (tinch holat) tanlash...",
                              command=self.select_baseline)
        tool_menu.add_command(label="Kalibrlashni tozalash", command=self.clear_baseline)
        tool_menu.add_separator()
        tool_menu.add_command(label="Harmonizatsiya chastotasini o'rnatish...",
                              command=self.set_target_fs)
        tool_menu.add_command(label="Harmonizatsiyani o'chirish", command=self.clear_target_fs)
        menubar.add_cascade(label="Vositalar", menu=tool_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Dastur haqida", command=self.show_about)
        menubar.add_cascade(label="Yordam", menu=help_menu)

        self.root.config(menu=menubar)

    def set_window_icon(self):
        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(default=ICON_PATH)
                return
        except Exception:
            pass
        for candidate in (
            resource_path("spektranaliz-eeg-icon.png"),
            resource_path("EEG-spectrum-background-730x730.png"),
        ):
            try:
                if os.path.exists(candidate):
                    self._icon_photo = ImageTk.PhotoImage(Image.open(candidate))
                    self.root.iconphoto(True, self._icon_photo)
                    return
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Yumaloq to'rtburchak yordamchilari
    # ------------------------------------------------------------------
    def rr_points(self, x1, y1, x2, y2, r):
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        return [
            x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r,
            x1, y1 + r, x1, y1, x1 + r, y1,
        ]

    def rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        return self.canvas.create_polygon(self.rr_points(x1, y1, x2, y2, r), smooth=True, **kwargs)

    def set_rect(self, item, x1, y1, x2, y2, r):
        self.canvas.coords(item, *self.rr_points(x1, y1, x2, y2, r))

    def get_svg_size(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                svg_text = file.read(4096)
        except OSError:
            return WINDOW_W, WINDOW_H
        viewbox = re.search(r'viewBox=["\']\s*([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s*["\']', svg_text)
        if viewbox:
            return float(viewbox.group(3)), float(viewbox.group(4))
        width = re.search(r'width=["\']([\d.]+)', svg_text)
        height = re.search(r'height=["\']([\d.]+)', svg_text)
        if width and height:
            return float(width.group(1)), float(height.group(1))
        return WINDOW_W, WINDOW_H

    def make_cover_background(self, width, height):
        if self.bg_is_svg:
            return self.render_svg_cover(width, height)
        return self.resize_cover(self.bg_original, width, height)

    def render_svg_cover(self, width, height):
        bg_w, bg_h = self.bg_size
        ratio = max(width / bg_w, height / bg_h)
        render_w = max(1, int(bg_w * ratio))
        render_h = max(1, int(bg_h * ratio))
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(url=self.bg_path, output_width=render_w, output_height=render_h)
            rendered = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            return self.crop_center(rendered, width, height)
        except ImportError:
            pass
        try:
            from reportlab.graphics import renderPM
            from svglib.svglib import svg2rlg
            drawing = svg2rlg(self.bg_path)
            png_bytes = renderPM.drawToString(drawing, fmt="PNG")
            rendered = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            return self.resize_cover(rendered, width, height)
        except ImportError:
            pass
        if self.bg_fallback_original is not None:
            return self.resize_cover(self.bg_fallback_original, width, height)
        raise ImportError(
            "SVG fonni ishlatish uchun SVG renderer kerak.\n"
            "O'rnatish: pip install cairosvg\n"
            "Muqobil: pip install svglib reportlab\n"
            "Yoki shu papkaga PNG fon faylini joylashtiring."
        )

    def load_background_fallback(self):
        for path in BACKGROUND_FALLBACK_PATHS:
            if os.path.exists(path):
                try:
                    return Image.open(path).convert("RGB")
                except Exception:
                    continue
        return None

    def resize_cover(self, image, width, height):
        img_w, img_h = image.size
        ratio = max(width / img_w, height / img_h)
        resized = image.resize((max(1, int(img_w * ratio)), max(1, int(img_h * ratio))), RESAMPLE)
        return self.crop_center(resized, width, height)

    def crop_center(self, image, width, height):
        left = max(0, (image.width - width) // 2)
        top = max(0, (image.height - height) // 2)
        return image.crop((left, top, left + width, top + height))

    def render_svg_image(self, path, target_w, target_h):
        target_w = max(1, int(target_w))
        target_h = max(1, int(target_h))
        if not os.path.exists(path):
            return None
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(url=path, output_width=target_w, output_height=target_h)
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            drawing = svg2rlg(path)
            if drawing is None or not drawing.width or not drawing.height:
                return None
            scale = min(target_w / drawing.width, target_h / drawing.height)
            drawing.scale(scale, scale)
            drawing.width *= scale
            drawing.height *= scale
            png_bytes = renderPM.drawToString(drawing, fmt="PNG", bg=0xFF00FF)
            image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            pixels = image.getdata()
            cleaned = [
                (r, g, b, 0) if (r > 230 and g < 40 and b > 230) else (r, g, b, a)
                for (r, g, b, a) in pixels
            ]
            image.putdata(cleaned)
            return image
        except Exception:
            return None

    def load_logo_image(self, path, width, height):
        width = max(1, int(width))
        height = max(1, int(height))
        ext = os.path.splitext(path)[1].lower()
        if ext == ".png":
            try:
                return Image.open(path).convert("RGBA").resize((width, height), RESAMPLE)
            except Exception:
                return None
        return self.render_svg_image(path, width, height)

    def region_is_dark(self, image, box):
        try:
            left, top, right, bottom = box
            left = max(0, min(left, image.width - 1))
            top = max(0, min(top, image.height - 1))
            right = max(left + 1, min(right, image.width))
            bottom = max(top + 1, min(bottom, image.height))
            region = image.crop((left, top, right, bottom)).convert("L")
            stat = region.resize((16, 16), RESAMPLE)
            pixels = list(stat.getdata())
            mean = sum(pixels) / len(pixels)
            return mean < 130
        except Exception:
            return False

    def place_logo(self, w, h, background_pil):
        target_h = min(h * 0.095, (w * 0.46) / LOGO_ASPECT)
        target_h = max(40, target_h)
        target_w = target_h * LOGO_ASPECT
        top_margin = max(6, int(h * 0.012))
        center_x = w / 2
        center_y = top_margin + target_h / 2
        box = (
            int(center_x - target_w / 2), int(top_margin),
            int(center_x + target_w / 2), int(top_margin + target_h),
        )
        dark_bg = self.region_is_dark(background_pil, box)
        candidates = (
            [LOGO_DARK_PNG, LOGO_DARK_PATH] if dark_bg
            else [LOGO_LIGHT_PNG, LOGO_LIGHT_PATH]
        )
        chosen = next((path for path in candidates if os.path.exists(path)), None)
        if chosen is None:
            self.canvas.itemconfig(self.logo_id, state="hidden")
            return 0
        cache_key = (chosen, int(target_w), int(target_h))
        photo = self.logo_cache.get(cache_key)
        if photo is None:
            image = self.load_logo_image(chosen, target_w, target_h)
            if image is None:
                self.canvas.itemconfig(self.logo_id, state="hidden")
                return 0
            photo = ImageTk.PhotoImage(image)
            self.logo_cache[cache_key] = photo
        self.logo_photo = photo
        self.canvas.itemconfig(self.logo_id, image=photo, state="normal")
        self.canvas.coords(self.logo_id, center_x, center_y)
        self.canvas.tag_raise(self.logo_id, self.bg_id)
        return top_margin + target_h

    def make_folder_icon(self, size):
        size = max(18, int(size))
        stroke = max(2, size // 12)
        pad = max(3, size // 8)
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        shadow_offset = max(1, size // 16)
        body_top = int(size * 0.38)
        body_bottom = size - pad
        left = pad
        right = size - pad
        tab_left = left
        tab_top = int(size * 0.23)
        tab_right = int(size * 0.48)
        tab_bottom = body_top + stroke
        shadow = [
            (left + shadow_offset, body_top + shadow_offset),
            (right + shadow_offset, body_top + shadow_offset),
            (int(size * 0.84) + shadow_offset, body_bottom + shadow_offset),
            (left + shadow_offset, body_bottom + shadow_offset),
        ]
        draw.polygon(shadow, fill=(182, 192, 205, 150))
        tab = [
            (tab_left, tab_bottom), (tab_left, tab_top), (tab_right, tab_top),
            (int(size * 0.58), body_top), (right, body_top), (right, tab_bottom),
        ]
        draw.polygon(tab, fill="#f7fbff", outline="#111111")
        draw.line(tab + [tab[0]], fill="#111111", width=stroke, joint="curve")
        body = [
            (left, body_top), (right, body_top),
            (int(size * 0.84), body_bottom), (left, body_bottom),
        ]
        draw.polygon(body, fill="#ffffff", outline="#111111")
        draw.line(body + [body[0]], fill="#111111", width=stroke, joint="curve")
        lip_y = int(size * 0.56)
        draw.line(
            [(left + stroke * 2, lip_y), (right - stroke * 2, lip_y)],
            fill="#111111", width=max(1, stroke - 1),
        )
        return img

    def update_file_icon(self, x1, y1, x2, y2):
        btn_w = x2 - x1
        btn_h = y2 - y1
        icon_size = min(btn_h * 0.48, btn_w * 0.16)
        icon_x = x1 + btn_w * 0.17
        icon_y = y1 + btn_h * 0.52
        self.file_icon_photo = ImageTk.PhotoImage(self.make_folder_icon(icon_size))
        self.canvas.itemconfig(self.file_icon_id, image=self.file_icon_photo)
        self.canvas.coords(self.file_icon_id, icon_x, icon_y)
        return icon_x + icon_size / 2

    def fit_file_button_text(self, text, max_width, preferred_size):
        size = preferred_size
        while size > 7:
            check_font = tkfont.Font(family="Arial", size=size, weight="bold")
            if check_font.measure(text) <= max_width:
                return size
            size -= 1
        return 7

    def on_resize(self, event):
        if event.widget == self.root:
            if self.resize_job:
                self.root.after_cancel(self.resize_job)
            self.resize_job = self.root.after(30, self.redraw)

    def redraw(self):
        w, h = self.root.winfo_width(), self.root.winfo_height()
        if w < 100 or h < 100:
            return
        sx, sy = w / LAYOUT_W, h / LAYOUT_H
        s = min(sx, sy)
        font = lambda size: max(9, int(size * s))
        x = lambda value: value * sx
        y = lambda value: value * sy

        try:
            bg = self.make_cover_background(w, h)
        except Exception as error:
            bg = Image.new("RGB", (w, h), "#dffafa")
            if not self.bg_error_shown:
                self.bg_error_shown = True
                messagebox.showerror("Fon rasmi xatosi", str(error))
        self.bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.itemconfig(self.bg_id, image=self.bg_photo)
        self.canvas.tag_lower(self.bg_id)

        logo_bottom = self.place_logo(w, h, bg)

        panel_top = y(153)
        title_y = (logo_bottom + panel_top) / 2 if logo_bottom else y(63)
        self.canvas.itemconfig(self.title_id, font=("Times New Roman", font(16), "bold italic"), width=int(w * 0.95))
        self.canvas.coords(self.title_id, x(342), title_y)
        self.canvas.tag_raise(self.title_id)

        self.canvas.itemconfig(self.upload_label_id, font=("Times New Roman", font(18), "bold"), width=int(w * 0.40))
        self.canvas.coords(self.upload_label_id, x(183), y(186))

        self.set_rect(self.file_shadow, x(332), y(157), x(642), y(215), font(10))
        self.set_rect(self.file_panel, x(328), y(153), x(638), y(211), font(10))
        self.canvas.itemconfig(self.file_label_id, font=("Times New Roman", font(15), "italic"))
        self.canvas.coords(self.file_label_id, x(420), y(182))

        bx1, by1, bx2, by2 = x(492), y(159), x(630), y(204)
        self.set_rect(self.file_btn_shadow, bx1 + x(2), by1 + y(3), bx2 + x(2), by2 + y(3), font(9))
        self.set_rect(self.file_btn, bx1, by1, bx2, by2, font(9))
        self.set_rect(self.file_btn_highlight, bx1 + x(4), by1 + y(4), bx2 - x(4), by1 + y(20), font(7))

        btn_w = bx2 - bx1
        icon_right = self.update_file_icon(bx1, by1, bx2, by2)
        text_left = max(icon_right + btn_w * 0.08, bx1 + btn_w * 0.34)
        text_right = bx2 - btn_w * 0.08
        text_width = max(20, text_right - text_left)
        file_text_size = self.fit_file_button_text("Fayl tanlash", text_width, font(10))
        self.canvas.itemconfig(self.file_btn_text, font=("Arial", file_text_size, "bold"))
        self.canvas.coords(self.file_btn_text, (text_left + text_right) / 2, by1 + (by2 - by1) * 0.52)

        self.set_rect(self.main_shadow, x(217), y(246), x(473), y(304), font(12))
        self.set_rect(self.main_btn, x(214), y(242), x(470), y(300), font(12))
        self.set_rect(self.main_highlight, x(219), y(247), x(465), y(270), font(9))
        self.canvas.itemconfig(self.main_text, font=("Times New Roman", font(22), "bold"))
        self.canvas.coords(self.main_text, x(342), y(270))

        self.canvas.itemconfig(self.result_title_id, font=("Times New Roman", font(20), "bold"), width=int(w * 0.9))
        self.canvas.coords(self.result_title_id, x(342), y(344))

        self.set_rect(self.result_shadow, x(82), y(380), x(611), y(644), font(12))
        self.set_rect(self.result_panel, x(78), y(376), x(607), y(640), font(12))
        self.canvas.itemconfig(self.placeholder_id, font=("Times New Roman", font(30), "italic"))
        self.canvas.coords(self.placeholder_id, x(342), y(508))

        # Natija grafik oynasini panel ichiga joylash
        view_w = int(x(505))
        view_h = int(y(244))
        self.canvas.coords(self.result_view_id, x(342), y(508))
        self.canvas.itemconfig(self.result_view_id, width=view_w, height=view_h)
        self.result_view_w = max(60, view_w - 20)
        self._render_chart_image(self.result_view_w)

        self.canvas.itemconfig(self.status_id, font=("Times New Roman", font(10), "italic"))
        self.canvas.coords(self.status_id, x(342), y(656))
        self.update_status()

        self.canvas.itemconfig(self.copyright_id, font=("Times New Roman", font(11), "bold"))
        self.canvas.coords(self.copyright_id, x(342), y(676))

    def _make_export_button(self, parent, text, color, command):
        btn = tk.Button(parent, text=text, command=command, bg=color, fg="white",
                        activebackground=color, activeforeground="white",
                        relief="flat", bd=0, padx=14, pady=4,
                        font=("Segoe UI", 9, "bold"), cursor="hand2")
        btn.pack(side="left", padx=4, pady=6)
        return btn

    def _bind_wheel(self, active):
        if active:
            self.chart_canvas.bind_all("<MouseWheel>", self._on_wheel)
            self.chart_canvas.bind_all("<Button-4>", self._on_wheel)
            self.chart_canvas.bind_all("<Button-5>", self._on_wheel)
        else:
            self.chart_canvas.unbind_all("<MouseWheel>")
            self.chart_canvas.unbind_all("<Button-4>")
            self.chart_canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.chart_canvas.yview_scroll(delta, "units")

    def _render_chart_image(self, view_w):
        """To'liq natija posterini joriy oynaga moslab masshtablaydi va ko'rsatadi."""
        if self.report_image_full is None or view_w < 40:
            return
        img = self.report_image_full
        scale = view_w / img.width
        new_h = max(1, int(img.height * scale))
        resized = img.resize((int(view_w), new_h), RESAMPLE)
        self.report_photo = ImageTk.PhotoImage(resized)
        self.chart_canvas.itemconfig(self.chart_img_id, image=self.report_photo)
        self.chart_canvas.config(scrollregion=(0, 0, int(view_w), new_h))

    def update_status(self):
        bits = []
        if self.baseline_file:
            bits.append("Kalibrlash: " + os.path.basename(self.baseline_file))
        if self.target_fs:
            bits.append("Harmonizatsiya: %.0f Hz" % self.target_fs)
        self.canvas.itemconfig(self.status_id, text="  |  ".join(bits))

    def hover_file(self, active):
        self.canvas.config(cursor="hand2" if active else "")
        self.canvas.itemconfig(self.file_btn, fill="#edf4ff" if active else "#f7f9fc")
        self.canvas.itemconfig(self.file_btn_highlight, fill="#ffffff")
        self.canvas.itemconfig(self.file_btn_shadow, fill="#9fb3cc" if active else "#b8c2ce")

    def hover_result(self, active):
        self.canvas.config(cursor="hand2" if active else "")
        self.canvas.itemconfig(self.main_btn, fill="#2272c7" if active else "#2f80d8")
        self.canvas.itemconfig(self.main_highlight, fill="#5aa7ef" if active else "#4d9be6")

    # ------------------------------------------------------------------
    # Fayl tanlash
    # ------------------------------------------------------------------
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="EEG signal faylini tanlang",
            filetypes=[
                ("EEG files", "*.edf *.EDF *.bdf *.BDF *.csv *.CSV"),
                ("EDF/EDF+ files", "*.edf *.EDF"),
                ("BDF/BDF+ files", "*.bdf *.BDF"),
                ("CSV files", "*.csv *.CSV"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            self.selected_file = file_path
            self.canvas.itemconfig(self.file_label_id, text=os.path.basename(file_path))

    def select_baseline(self):
        path = filedialog.askopenfilename(
            title="Tinch holat (baseline) faylini tanlang",
            filetypes=[("EEG files", "*.edf *.EDF *.bdf *.BDF *.csv *.CSV"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.baseline_features = calibration.compute_baseline(path, target_fs=self.target_fs)
            self.baseline_file = path
            self.update_status()
            messagebox.showinfo("Kalibrlash",
                                "Individual baseline hisoblandi:\n%s\n\nKeyingi tahlillar shu tinch "
                                "holatga nisbatan baholanadi." % os.path.basename(path))
        except Exception as error:
            messagebox.showerror("Kalibrlash xatosi", str(error))

    def clear_baseline(self):
        self.baseline_file = None
        self.baseline_features = None
        self.update_status()
        messagebox.showinfo("Kalibrlash", "Individual kalibrlash o'chirildi.")

    def set_target_fs(self):
        from tkinter import simpledialog
        value = simpledialog.askfloat(
            "Harmonizatsiya",
            "Maqsadli namuna chastotasini (Hz) kiriting.\n"
            "Turli qurilmalardagi yozuvlarni bir xil chastotaga keltiradi\n"
            "(masalan 100 yoki 256):",
            minvalue=16.0, maxvalue=2000.0)
        if value:
            self.target_fs = float(value)
            self.update_status()

    def clear_target_fs(self):
        self.target_fs = None
        self.update_status()

    # ------------------------------------------------------------------
    # Asosiy tahlil — eeg_engine yadrosi chaqiriladi, natija GRAFIK ko'rinadi
    # ------------------------------------------------------------------
    def analyze_eeg(self):
        if not self.selected_file:
            messagebox.showwarning("Ogohlantirish", "Avval EEG signal faylini tanlang!")
            return
        try:
            self.canvas.itemconfig(self.placeholder_id, text="Tahlil qilinmoqda...", state="normal")
            self.root.update_idletasks()
            objs = analyze_objects(
                self.selected_file,
                target_fs=self.target_fs,
                baseline=self.baseline_features,
            )
            self.last_objs = objs
            # Natijani chiroyli grafik poster sifatida chizamiz
            self.report_image_full = charts.composite_report_image(
                objs["rec"], objs["spec"], objs["features"], objs["classification"])
            self.canvas.itemconfig(self.placeholder_id, state="hidden")
            self.canvas.itemconfig(self.result_view_id, state="normal")
            self._render_chart_image(self.result_view_w)
            self.chart_canvas.yview_moveto(0.0)
        except Exception as error:
            self.canvas.itemconfig(self.placeholder_id, text="Natijalar oynasi", state="normal")
            messagebox.showerror("Xatolik", "Faylni tahlil qilib bo'lmadi:\n%s" % error)

    def _ensure_analyzed(self):
        if self.last_objs is None:
            messagebox.showwarning("Ogohlantirish", "Avval faylni tanlab, \"Natijani olish\" tugmasini bosing.")
            return False
        return True

    def save_html(self):
        if not self._ensure_analyzed():
            return
        path = filedialog.asksaveasfilename(
            title="HTML hisobotni saqlash", defaultextension=".html",
            initialfile="eeg_hisobot.html", filetypes=[("HTML", "*.html")])
        if not path:
            return
        try:
            export_html(self.last_objs, path)
            messagebox.showinfo("HTML hisobot", "Saqlandi:\n%s" % path)
        except Exception as error:
            messagebox.showerror("Xatolik", str(error))

    def save_pdf(self):
        if not self._ensure_analyzed():
            return
        path = filedialog.asksaveasfilename(
            title="PDF hisobotni saqlash", defaultextension=".pdf",
            initialfile="eeg_hisobot.pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            export_pdf(self.last_objs, path)
            messagebox.showinfo("PDF hisobot", "Saqlandi:\n%s" % path)
        except Exception as error:
            messagebox.showerror("Xatolik", str(error))

    def save_text(self):
        if not self._ensure_analyzed():
            return
        path = filedialog.asksaveasfilename(
            title="Matnli hisobotni saqlash", defaultextension=".txt",
            initialfile="eeg_hisobot.txt", filetypes=[("Matn", "*.txt")])
        if not path:
            return
        try:
            export_txt(self.last_objs, path)
            messagebox.showinfo("Hisobot", "Saqlandi:\n%s" % path)
        except Exception as error:
            messagebox.showerror("Xatolik", str(error))

    def show_about(self):
        messagebox.showinfo(
            "Dastur haqida",
            "%s\n\n"
            "Sportchining EEG signallarini spektral tahlil qilish va funksional\n"
            "holatini aniqlash dasturi.\n\n"
            "Bu dastur ikki loyihaning birlashtirilgan, optimallashtirilgan ko'rinishi:\n"
            "  - Spektranaliz-EEG-installation7 (dizayn va tuzilish)\n"
            "  - EEG-signal-edf-bdf (ilmiy yadro)\n\n"
            "Qo'llab-quvvatlanadigan formatlar: EDF/EDF+, BDF/BDF+, CSV\n"
            "Aniqlanadigan holatlar (8): %s\n\n"
            "(c) %s"
            % (APP_NAME, ", ".join(config.STATES), config.AUTHOR),
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = EEGSpektralTahlilDasturi(root)
    root.mainloop()
