#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DraveContrast - kleurcontrast-checker volgens WCAG.
Kies een tekstkleur en een achtergrond; de app rekent de contrastverhouding uit
en laat zien of het voldoende is (AA / AAA), met een live voorbeeld.
Dravenlock-huisstijl. Lokaal, offline, toegankelijk.
"""
import os
import sys
import json
import colorsys

from PyQt6.QtCore import Qt, QLocale, QUrl, pyqtSignal
from PyQt6.QtGui import (QPixmap, QColor, QIcon, QDesktopServices)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QLineEdit, QComboBox, QFrame, QMessageBox,
    QDialog, QToolButton, QStatusBar, QPlainTextEdit, QColorDialog, QFileDialog,
    QSizePolicy)

APP_NAME = "DraveContrast"
APP_VERSION = "0.2.1"
DONATE_URL = "https://paypal.me/roger076"
SUPPORT_MAIL = "service@dravenlock.nl"

# ---- Dravenlock-huisstijl ----
BG = "#0e0e11"
PANEL = "#16161b"
SILVER = "#d4d4d4"
MUTE = "#8a8a94"
ACCENT = "#6fa3d6"
GOOD = "#4fb477"
BAD = "#d6645f"

PALETTE = ["#0e0e11", "#16161b", "#8a8a94", "#d4d4d4", "#6fa3d6", "#ffffff"]


# ---------------------------------------------------------------------------
# Pad / config
# ---------------------------------------------------------------------------
def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    return os.path.join(_app_dir(), "dravecontrast_config.json")


DEFAULT_CONFIG = {"lang": "", "fg": "#d4d4d4", "bg": "#0e0e11"}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Taal
# ---------------------------------------------------------------------------
_LANG = "nl"

TRANSLATIONS = {
    "en": {
        "Instellingen\u2026": "Settings\u2026", "Snelgids": "Quick guide",
        "Over": "About", "Sluiten": "Close", "Taal:": "Language:",
        "Automatisch (OS)": "Automatic (OS)", "Nederlands": "Dutch",
        "Engels": "English", "Donatie": "Donate",
        "Sommige instellingen gaan pas in na herstarten.":
            "Some settings apply after a restart.",
        "Tekstkleur": "Text color", "Achtergrond": "Background",
        "Kies\u2026": "Pick\u2026", "Verwisselen": "Swap",
        "Huisstijl-kleuren": "House palette",
        "Voorbeeld": "Preview",
        "De snelle bruine vos springt over de luie hond.":
            "The quick brown fox jumps over the lazy dog.",
        "Grote tekst Aa 123": "Large text Aa 123",
        "Contrastverhouding": "Contrast ratio",
        "Gewone tekst (AA)": "Normal text (AA)",
        "Grote tekst (AA)": "Large text (AA)",
        "Gewone tekst (AAA)": "Normal text (AAA)",
        "Grote tekst (AAA)": "Large text (AAA)",
        "Knoppen / iconen (AA)": "UI / icons (AA)",
        "voldoende": "pass", "onvoldoende": "fail",
        "Maak leesbaar (AA)": "Make readable (AA)",
        "CSS-code": "CSS code", "Kopi\u00ebren": "Copy",
        "Opslaan als CSS\u2026": "Save as CSS\u2026",
        "Gekopieerd naar klembord": "Copied to clipboard",
        "Opgeslagen": "Saved", "Kon niet opslaan": "Could not save",
        "CSS-bestanden (*.css)": "CSS files (*.css)",
        "Ongeldige kleur. Gebruik bijv. #1a2b3c.":
            "Invalid color. Use e.g. #1a2b3c.",
        "Grote tekst = 18pt, of 14pt vetgedrukt.":
            "Large text = 18pt, or 14pt bold.",
        "snelgids_titel": "DraveContrast - quick guide",
    }
}


def detect_lang(cfg):
    forced = (cfg.get("lang") or "").strip().lower()
    if forced in ("nl", "en"):
        return forced
    try:
        if QLocale.system().name().lower().startswith("nl"):
            return "nl"
        return "en"
    except Exception:
        return "nl"


def t(s, lang=None):
    lg = lang or _LANG
    if lg == "nl":
        return s
    return TRANSLATIONS.get(lg, {}).get(s, s)


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------
def _logo_path():
    dirs = [_app_dir()]
    mp = getattr(sys, "_MEIPASS", None)
    if mp:
        dirs.append(mp)
    dirs.append(os.path.join(_app_dir(), "_internal"))
    for d in dirs:
        for name in ("logo.ico", "logo.png"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None


def app_icon():
    p = _logo_path()
    if p:
        ic = QIcon(p)
        if not ic.isNull():
            return ic
    return QIcon()


def logo_pixmap(size=30):
    p = _logo_path()
    if p:
        pm = QPixmap(p)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return QPixmap()


# ---------------------------------------------------------------------------
# WCAG-berekening
# ---------------------------------------------------------------------------
def parse_hex(s):
    """'#rgb' of '#rrggbb' (met of zonder #) -> (r,g,b) 0-255, of None."""
    if not s:
        return None
    s = s.strip().lstrip("#")
    if len(s) == 3 and all(c in "0123456789abcdefABCDEF" for c in s):
        s = "".join(c * 2 for c in s)
    if len(s) != 6 or any(c not in "0123456789abcdefABCDEF" for c in s):
        return None
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def to_hex(rgb):
    return "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(rgb1, rgb2):
    l1, l2 = luminance(rgb1), luminance(rgb2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# WCAG-drempels
THRESHOLDS = [
    ("Gewone tekst (AA)", 4.5),
    ("Grote tekst (AA)", 3.0),
    ("Gewone tekst (AAA)", 7.0),
    ("Grote tekst (AAA)", 4.5),
    ("Knoppen / iconen (AA)", 3.0),
]


def make_readable(fg_rgb, bg_rgb, target=4.5):
    """Verschuif de tekstkleur in helderheid tot de verhouding >= target,
    naar wit als de achtergrond donker is, anders naar zwart."""
    h, l, s = colorsys.rgb_to_hls(fg_rgb[0] / 255, fg_rgb[1] / 255, fg_rgb[2] / 255)
    bg_dark = luminance(bg_rgb) < 0.5
    step = 0.02 if bg_dark else -0.02
    best = fg_rgb
    for _ in range(60):
        if contrast_ratio(best, bg_rgb) >= target:
            return best
        l = min(1.0, max(0.0, l + step))
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        best = (round(r * 255), round(g * 255), round(b * 255))
        if l <= 0.0 or l >= 1.0:
            break
    return best


# ---------------------------------------------------------------------------
# Snelgids
# ---------------------------------------------------------------------------
GUIDE_NL = """DraveContrast - Snelgids

DraveContrast controleert of een tekstkleur goed leesbaar is op een
achtergrondkleur, volgens de WCAG-toegankelijkheidsregels.

Aan de slag
- Kies een Tekstkleur en een Achtergrond: typ een hex-code (bijv. #d4d4d4)
  of klik 'Kies...' voor een kleurkiezer. Onder elk veld staan ook de
  huisstijl-kleuren om snel te prikken.
- 'Verwisselen' wisselt tekst- en achtergrondkleur om.
- In het Voorbeeld zie je meteen hoe het eruitziet (gewone en grote tekst).

De uitslag
- 'Contrastverhouding' is een getal, bijv. 4.8 : 1. Hoe hoger, hoe beter.
- Daaronder staat per geval of het voldoende is:
    Gewone tekst (AA)  -> minimaal 4.5
    Grote tekst (AA)   -> minimaal 3.0   (groot = 18pt of 14pt vet)
    Gewone tekst (AAA) -> minimaal 7.0   (strenger niveau)
    Grote tekst (AAA)  -> minimaal 4.5
    Knoppen / iconen   -> minimaal 3.0
- Lukt het net niet? Klik 'Maak leesbaar (AA)'; de app maakt de tekstkleur
  iets lichter of donkerder tot het wel voldoende is.

CSS opslaan
- Onder 'CSS-code' staat een kant-en-klaar stukje CSS met je twee
  kleuren (als variabelen) en de contrast-uitslag als commentaar. Klik
  'Kopieren' om het te plakken, of 'Opslaan als CSS...' voor een .css-bestand.
  Werkt ook als Qt-stylesheet (QSS): dezelfde kleurnotatie.

Vragen of een tip? service@dravenlock.nl
"""

GUIDE_EN = """DraveContrast - Quick guide

DraveContrast checks whether a text color is readable on a background color,
following the WCAG accessibility rules.

Getting started
- Pick a Text color and a Background: type a hex code (e.g. #d4d4d4) or click
  'Pick...' for a color picker. Below each field are the house colors for
  quick selection.
- 'Swap' swaps the text and background colors.
- The Preview shows immediately how it looks (normal and large text).

The result
- 'Contrast ratio' is a number, e.g. 4.8 : 1. Higher is better.
- Below it you see, per case, whether it passes:
    Normal text (AA)  -> at least 4.5
    Large text (AA)   -> at least 3.0   (large = 18pt or 14pt bold)
    Normal text (AAA) -> at least 7.0   (stricter level)
    Large text (AAA)  -> at least 4.5
    UI / icons        -> at least 3.0
- Just short? Click 'Make readable (AA)'; the app nudges the text color
  lighter or darker until it passes.

Saving CSS
- Under 'CSS code' there is a ready-made CSS snippet with your two
  colors (as variables) and the contrast result as a comment. Click 'Copy'
  to paste it, or 'Save as CSS...' for a .css file. Works as a Qt stylesheet
  (QSS) too: same color notation.

Questions or feedback? service@dravenlock.nl
"""


class GuideDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent)
        self.setWindowTitle(t("snelgids_titel", lang))
        self.setWindowIcon(app_icon())
        self.resize(560, 560)
        lay = QVBoxLayout(self)
        box = QPlainTextEdit()
        box.setReadOnly(True)
        box.setObjectName("guide")
        box.setPlainText(GUIDE_NL if lang == "nl" else GUIDE_EN)
        lay.addWidget(box)
        row = QHBoxLayout()
        donate = QPushButton("\u2665 " + t("Donatie", lang))
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        row.addWidget(donate)
        row.addStretch(1)
        close = QPushButton(t("Sluiten", lang))
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)


class SettingsDialog(QDialog):
    def __init__(self, parent, cfg, lang):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle(t("Instellingen\u2026", lang))
        self.setWindowIcon(app_icon())
        self.resize(360, 160)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("Taal:", lang)))
        self.langbox = QComboBox()
        self.langbox.addItem(t("Automatisch (OS)", lang), "")
        self.langbox.addItem(t("Nederlands", lang), "nl")
        self.langbox.addItem(t("Engels", lang), "en")
        self.langbox.setCurrentIndex(
            {"": 0, "nl": 1, "en": 2}.get(cfg.get("lang", ""), 0))
        lay.addWidget(self.langbox)
        hint = QLabel(t("Sommige instellingen gaan pas in na herstarten.", lang))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)

    def result_cfg(self):
        self.cfg["lang"] = self.langbox.currentData()
        return self.cfg


# ---------------------------------------------------------------------------
# Kleurveld (hex + kiezer + huisstijl-stalen)
# ---------------------------------------------------------------------------
class ColorField(QWidget):
    changed = pyqtSignal()

    def __init__(self, title, value, lang):
        super().__init__()
        self.lang = lang
        self.value = value
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lbl = QLabel(title)
        lbl.setObjectName("fieldttl")
        lay.addWidget(lbl)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.swatch = QFrame()
        self.swatch.setObjectName("swatch")
        self.swatch.setFixedSize(40, 40)
        row.addWidget(self.swatch)
        self.edit = QLineEdit(value)
        self.edit.setObjectName("hex")
        self.edit.setMaxLength(7)
        self.edit.textChanged.connect(self._on_text)
        row.addWidget(self.edit, 1)
        pick = QPushButton(t("Kies\u2026", lang))
        pick.clicked.connect(self._pick)
        row.addWidget(pick)
        lay.addLayout(row)
        # huisstijl-stalen
        prow = QHBoxLayout()
        prow.setSpacing(6)
        for c in PALETTE:
            b = QToolButton()
            b.setObjectName("palswatch")
            b.setFixedSize(26, 26)
            b.setStyleSheet("QToolButton#palswatch{background:%s;border:1px solid #555;"
                            "border-radius:5px;}" % c)
            b.setToolTip(c)
            b.clicked.connect(lambda _=False, col=c: self.set_value(col))
            prow.addWidget(b)
        prow.addStretch(1)
        lay.addLayout(prow)
        self._refresh_swatch()

    def _on_text(self):
        if parse_hex(self.edit.text()):
            self.value = to_hex(parse_hex(self.edit.text()))
            self._refresh_swatch()
            self.changed.emit()

    def set_value(self, hexv):
        self.value = hexv
        self.edit.blockSignals(True)
        self.edit.setText(hexv)
        self.edit.blockSignals(False)
        self._refresh_swatch()
        self.changed.emit()

    def _pick(self):
        col = QColorDialog.getColor(QColor(self.value), self,
                                    t("Kies\u2026", self.lang))
        if col.isValid():
            self.set_value(col.name())

    def _refresh_swatch(self):
        rgb = parse_hex(self.value)
        ok = rgb is not None
        self.swatch.setStyleSheet(
            "QFrame#swatch{background:%s;border:1px solid #555;border-radius:6px;}"
            % (self.value if ok else "#000000"))


# ---------------------------------------------------------------------------
# Hoofdvenster
# ---------------------------------------------------------------------------
class DraveContrast(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.lang = _LANG
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(720, 880)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header())

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(18, 16, 18, 16)
        bl.setSpacing(14)
        outer.addWidget(body, 1)

        # kleurvelden
        cols = QHBoxLayout()
        cols.setSpacing(16)
        self.fg_field = ColorField(t("Tekstkleur", self.lang),
                                   cfg.get("fg", "#d4d4d4"), self.lang)
        self.bg_field = ColorField(t("Achtergrond", self.lang),
                                   cfg.get("bg", "#0e0e11"), self.lang)
        self.fg_field.changed.connect(self.update_result)
        self.bg_field.changed.connect(self.update_result)
        cols.addWidget(self.fg_field, 1)
        swapcol = QVBoxLayout()
        swapcol.addStretch(1)
        self.b_swap = QToolButton()
        self.b_swap.setText("\u21c4")
        self.b_swap.setObjectName("swap")
        self.b_swap.setToolTip(t("Verwisselen", self.lang))
        self.b_swap.clicked.connect(self.swap)
        swapcol.addWidget(self.b_swap)
        swapcol.addStretch(1)
        cols.addLayout(swapcol)
        cols.addWidget(self.bg_field, 1)
        bl.addLayout(cols)

        # voorbeeld
        self.preview = QFrame()
        self.preview.setObjectName("preview")
        self.preview.setMinimumHeight(130)
        pl = QVBoxLayout(self.preview)
        pl.setContentsMargins(18, 14, 18, 14)
        self.prev_big = QLabel(t("Grote tekst Aa 123", self.lang))
        self.prev_big.setObjectName("prevbig")
        self.prev_small = QLabel(
            t("De snelle bruine vos springt over de luie hond.", self.lang))
        self.prev_small.setObjectName("prevsmall")
        self.prev_small.setWordWrap(True)
        pl.addWidget(self.prev_big)
        pl.addWidget(self.prev_small)
        pl.addStretch(1)
        bl.addWidget(self.preview)

        # ratio + maak-leesbaar
        rrow = QHBoxLayout()
        self.ratio_lbl = QLabel("")
        self.ratio_lbl.setObjectName("ratio")
        rrow.addWidget(self.ratio_lbl)
        rrow.addStretch(1)
        self.b_fix = QPushButton(t("Maak leesbaar (AA)", self.lang))
        self.b_fix.setObjectName("primary")
        self.b_fix.clicked.connect(self.fix_readable)
        rrow.addWidget(self.b_fix)
        bl.addLayout(rrow)

        # resultaten
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)
        self.rows = []
        for i, (key, need) in enumerate(THRESHOLDS):
            name = QLabel(t(key, self.lang))
            name.setObjectName("crow")
            need_lbl = QLabel("\u2265 %.1f" % need)
            need_lbl.setObjectName("cneed")
            verdict = QLabel("")
            verdict.setObjectName("cverdict")
            verdict.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid.addWidget(name, i, 0)
            self.grid.addWidget(need_lbl, i, 1)
            self.grid.addWidget(verdict, i, 2)
            self.rows.append((need, verdict))
        self.grid.setColumnStretch(0, 1)
        gframe = QFrame()
        gframe.setObjectName("resframe")
        gframe.setLayout(self.grid)
        bl.addWidget(gframe)

        # CSS-export
        expf = QFrame()
        expf.setObjectName("resframe")
        exl = QVBoxLayout(expf)
        exl.setContentsMargins(12, 12, 12, 12)
        exl.setSpacing(8)
        csslbl = QLabel(t("CSS-code", self.lang))
        csslbl.setObjectName("fieldttl")
        exl.addWidget(csslbl)
        self.css_box = QPlainTextEdit()
        self.css_box.setReadOnly(True)
        self.css_box.setObjectName("cssbox")
        self.css_box.setFixedHeight(150)
        exl.addWidget(self.css_box)
        brow = QHBoxLayout()
        self.b_copy = QPushButton(t("Kopi\u00ebren", self.lang))
        self.b_copy.clicked.connect(self.copy_css)
        brow.addWidget(self.b_copy)
        self.b_savecss = QPushButton(t("Opslaan als CSS\u2026", self.lang))
        self.b_savecss.clicked.connect(self.save_css)
        brow.addWidget(self.b_savecss)
        brow.addStretch(1)
        exl.addLayout(brow)
        bl.addWidget(expf)

        hint = QLabel(t("Grote tekst = 18pt, of 14pt vetgedrukt.", self.lang))
        hint.setObjectName("hint")
        bl.addWidget(hint)
        bl.addStretch(1)

        # statusbalk
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.addPermanentWidget(QLabel("v" + APP_VERSION))
        donate = QToolButton()
        donate.setText("\u2665 " + t("Donatie", self.lang))
        donate.setObjectName("donate")
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        sb.addPermanentWidget(donate)

        self.update_result()

    def _header(self):
        w = QWidget()
        w.setObjectName("header")
        w.setFixedHeight(56)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 8, 14, 8)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(30))
        lay.addWidget(logo)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        lay.addWidget(title)
        ver = QLabel("v" + APP_VERSION)
        ver.setObjectName("ver")
        lay.addWidget(ver)
        lay.addStretch(1)
        for label, slot in [(t("Instellingen\u2026", self.lang), self._settings),
                            (t("Snelgids", self.lang), self._guide),
                            (t("Over", self.lang), self._about)]:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, s=slot: s())
            lay.addWidget(b)
        return w

    # ---- logica ----
    def swap(self):
        fg, bg = self.fg_field.value, self.bg_field.value
        self.fg_field.set_value(bg)
        self.bg_field.set_value(fg)

    def fix_readable(self):
        fg = parse_hex(self.fg_field.value)
        bg = parse_hex(self.bg_field.value)
        if not fg or not bg:
            return
        new = make_readable(fg, bg, 4.5)
        self.fg_field.set_value(to_hex(new))

    def update_result(self):
        fg = parse_hex(self.fg_field.value)
        bg = parse_hex(self.bg_field.value)
        if not fg or not bg:
            self.ratio_lbl.setText(t("Ongeldige kleur. Gebruik bijv. #1a2b3c.", self.lang))
            return
        ratio = contrast_ratio(fg, bg)
        self.ratio_lbl.setText("%s: %.2f : 1" % (t("Contrastverhouding", self.lang), ratio))
        # voorbeeld
        self.preview.setStyleSheet(
            "QFrame#preview{background:%s;border:1px solid #2c2c36;border-radius:12px;}"
            % self.bg_field.value)
        self.prev_big.setStyleSheet("QLabel#prevbig{color:%s;background:transparent;}"
                                    % self.fg_field.value)
        self.prev_small.setStyleSheet("QLabel#prevsmall{color:%s;background:transparent;}"
                                      % self.fg_field.value)
        # resultaten
        for need, verdict in self.rows:
            ok = ratio >= need
            verdict.setText(("\u2713 " + t("voldoende", self.lang)) if ok
                            else ("\u2717 " + t("onvoldoende", self.lang)))
            verdict.setProperty("ok", "1" if ok else "0")
            verdict.style().unpolish(verdict)
            verdict.style().polish(verdict)
        # onthouden
        self.cfg["fg"] = self.fg_field.value
        self.cfg["bg"] = self.bg_field.value
        save_config(self.cfg)
        # CSS bijwerken
        self.css_box.setPlainText(self._css_text(fg, bg, ratio))

    def _css_text(self, fg, bg, ratio):
        fgh = to_hex(fg)
        bgh = to_hex(bg)
        verdict = t("voldoende", self.lang) if ratio >= 4.5 else t("onvoldoende", self.lang)
        head = "Gewone tekst (AA)" if self.lang == "nl" else "Normal text (AA)"
        return (
            "/* DraveContrast - %.2f : 1 - %s: %s */\n"
            ":root {\n"
            "  --tekstkleur: %s;\n"
            "  --achtergrond: %s;\n"
            "}\n\n"
            "body {\n"
            "  color: var(--tekstkleur);\n"
            "  background-color: var(--achtergrond);\n"
            "}\n" % (ratio, head, verdict, fgh, bgh)
        )

    def copy_css(self):
        txt = self.css_box.toPlainText()
        if not txt:
            return
        QApplication.clipboard().setText(txt)
        self.statusBar().showMessage(t("Gekopieerd naar klembord", self.lang), 3000)

    def save_css(self):
        txt = self.css_box.toPlainText()
        if not txt:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("Opslaan als CSS\u2026", self.lang), "kleuren.css",
            t("CSS-bestanden (*.css)", self.lang))
        if not path:
            return
        if not path.lower().endswith(".css"):
            path += ".css"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            self.statusBar().showMessage(
                "%s %s" % (t("Opgeslagen", self.lang), os.path.basename(path)), 4000)
        except Exception as e:
            QMessageBox.warning(self, t("Kon niet opslaan", self.lang), str(e))

    # ---- menu's ----
    def _settings(self):
        dlg = SettingsDialog(self, dict(self.cfg), self.lang)
        if dlg.exec():
            self.cfg = dlg.result_cfg()
            save_config(self.cfg)

    def _guide(self):
        GuideDialog(self, self.lang).exec()

    def _about(self):
        QMessageBox.information(
            self, t("Over", self.lang),
            "%s v%s\n\n%s\nDravenlock\n%s\n%s"
            % (APP_NAME, APP_VERSION,
               "Kleurcontrast-checker volgens WCAG." if self.lang == "nl"
               else "Color contrast checker per WCAG.",
               SUPPORT_MAIL, DONATE_URL))


QSS = """
* { font-family: 'Segoe UI', sans-serif; font-size: 14px; color: %(silver)s; }
QMainWindow, QWidget { background: %(bg)s; }
#header { background: %(panel)s; border-bottom: 1px solid #23232b; }
#title { font-size: 19px; font-weight: 700; }
#ver { color: %(mute)s; font-size: 12px; }
#fieldttl { color: %(mute)s; font-size: 13px; font-weight: 700;
            text-transform: uppercase; letter-spacing: 1px; }
#hint { color: %(mute)s; font-size: 12px; }
QPushButton { background: %(panel)s; border: 1px solid #2c2c36; border-radius: 8px;
              padding: 8px 13px; color: %(silver)s; min-height: 38px; }
QPushButton:hover { border-color: %(accent)s; }
QPushButton#primary { background: %(accent)s; color: #08131f; font-weight: 700;
                      border: none; }
QPushButton#primary:hover { background: #87b6e3; }
QToolButton#swap { background: %(panel)s; border: 1px solid #2c2c36; border-radius: 8px;
                   font-size: 20px; min-width: 44px; min-height: 44px; color: %(accent)s; }
QToolButton#swap:hover { border-color: %(accent)s; }
QToolButton#donate { border: none; background: transparent; color: %(accent)s; }
QLineEdit#hex { background: #14141a; border: 1px solid #2c2c36; border-radius: 8px;
                padding: 8px 10px; font-size: 17px; }
QLineEdit#hex:focus { border-color: %(accent)s; }
#preview { background: #ffffff; border: 1px solid #2c2c36; border-radius: 12px; }
#prevbig { font-size: 26px; font-weight: 800; }
#prevsmall { font-size: 15px; }
#ratio { font-size: 22px; font-weight: 800; }
#resframe { background: %(panel)s; border: 1px solid #2c2c36; border-radius: 12px;
            padding: 12px 14px; }
#crow { font-size: 15px; }
#cneed { color: %(mute)s; font-size: 13px; }
#cverdict { font-size: 15px; font-weight: 700; color: %(mute)s; }
#cverdict[ok="1"] { color: %(good)s; }
#cverdict[ok="0"] { color: %(bad)s; }
QStatusBar { background: %(panel)s; }
QDialog { background: %(bg)s; }
QPlainTextEdit#guide { background: %(panel)s; border: 1px solid #2c2c36;
                       border-radius: 8px; padding: 10px; }
QPlainTextEdit#cssbox { background: #14141a; border: 1px solid #2c2c36;
                        border-radius: 8px; padding: 8px 10px; color: %(silver)s;
                        font-family: 'Consolas','Courier New',monospace; font-size: 13px; }
""" % {"bg": BG, "panel": PANEL, "silver": SILVER, "mute": MUTE,
       "accent": ACCENT, "good": GOOD, "bad": BAD}


def _install_excepthook():
    import traceback

    def hook(exctype, value, tb):
        msg = "".join(traceback.format_exception(exctype, value, tb))
        try:
            with open(os.path.join(_app_dir(), "dravecontrast-fout.txt"),
                      "w", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            pass
        try:
            if QApplication.instance():
                QMessageBox.critical(None, "DraveContrast - fout",
                                     "Er ging iets mis bij het starten:\n\n"
                                     + msg[-1500:]
                                     + "\n\n(Ook opgeslagen in dravecontrast-fout.txt)")
        except Exception:
            pass
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = hook


def main():
    global _LANG
    _install_excepthook()
    app = QApplication(sys.argv)
    try:
        cfg = load_config()
        _LANG = detect_lang(cfg)
        app.setStyleSheet(QSS)
        win = DraveContrast(cfg)
        win.show()
    except Exception:
        sys.excepthook(*sys.exc_info())
        return
    try:  # Dravenlock: stille update-check (uit te zetten; Ctrl+Shift+U = met de hand)
        import drave_update
        drave_update.start(win, 'DraveContrast', APP_VERSION)
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
