import math
from PySide6.QtCore import Qt, Signal, QRect, QSize, QPoint, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPainterPath, QLinearGradient, QPen, QPixmap,
    QPolygonF, QBrush
)
from PySide6.QtWidgets import (
    QFrame, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy, QGridLayout,
    QLayout, QWidget, QScrollArea
)
from .constants import (ELEMENT_COLORS, SLOT_NAMES, STAT_ICONS,
                        MAX_ROLL, num_val, TEAM_BY_CHAR)


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=12):
        super().__init__(parent)
        self._items = []; self._spacing = spacing
        self.setContentsMargins(margin, margin, margin, margin)
    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i): return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return Qt.Orientations(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, w): return self._do(QRect(0, 0, w, 0), True)
    def setGeometry(self, r): super().setGeometry(r); self._do(r, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QSize()
        for it in self._items: s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left()+m.right(), m.top()+m.bottom())
    def _do(self, rect, test_only):
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, lh = eff.x(), eff.y(), 0
        for it in self._items:
            w = it.sizeHint().width(); h = it.sizeHint().height()
            if x + w > eff.right() and lh > 0:
                x = eff.x(); y += lh + self._spacing; lh = 0
            if not test_only:
                it.setGeometry(QRect(QPoint(x, y), it.sizeHint()))
            x += w + self._spacing
            lh = max(lh, h)
        return y + lh - rect.y() + m.bottom()

    def addWidget(self, w):
        super().addWidget(w)
        self.invalidate()
        self.update()

    def invalidate(self):
        super().invalidate()
        # Parent widget'ga ham xabar beramiz
        parent = self.parentWidget()
        if parent:
            parent.updateGeometry()
            parent.update()


class CircleAvatar(QLabel):
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setStyleSheet("background: transparent; border: none;")
        self._pm = None
    def set_image(self, pm):
        if pm: self._pm = pm; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); path.addEllipse(self.rect().adjusted(2,2,-2,-2))
        p.setClipPath(path)
        if self._pm:
            s = self._pm.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap((self.width()-s.width())//2, (self.height()-s.height())//2, s)
        else:
            p.fillRect(self.rect(), QColor("#1f1f2e"))
        p.setClipping(False)
        p.setPen(QPen(QColor("#3a3a52"), 2)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(self.rect().adjusted(1,1,-1,-1))


class ProfileBanner(QFrame):
    clicked = Signal()
    def __init__(self, loader, compact=False, parent=None):
        super().__init__(parent)
        self.loader = loader; self.compact = compact
        self._bg = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)
        h = 100 if compact else 180
        self.setFixedHeight(h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 16, 28, 16); lay.setSpacing(20)
        self.avatar = CircleAvatar(h - 32)
        self.avatar.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(self.avatar)
        info = QVBoxLayout(); info.setSpacing(3)
        self.name_lbl = QLabel()
        f = QFont(); f.setPointSize(11 if compact else 20); f.setBold(True)
        self.name_lbl.setFont(f)
        self.name_lbl.setStyleSheet("color:#fff; background:transparent;")
        self.uid_lbl = QLabel()
        self.uid_lbl.setStyleSheet("color:#7a7a8c; font-size:11px; background:transparent;")
        self.bio_lbl = QLabel()
        self.bio_lbl.setStyleSheet("color:#c0c0cc; font-size:11px; background:transparent;")
        self.bio_lbl.setWordWrap(True)
        info.addWidget(self.name_lbl)
        info.addWidget(self.uid_lbl)
        if not compact: info.addWidget(self.bio_lbl)
        info.addStretch()
        lay.addLayout(info, 1)
        right = QVBoxLayout(); right.setSpacing(6)
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ar_lbl = QLabel()
        self.ar_lbl.setStyleSheet(
            "color:#fff; background:#7c5cff; padding:5px 14px; border-radius:12px;"
            "font-weight:bold; font-size:11px;")
        self.ar_lbl.setAlignment(Qt.AlignCenter)
        self.wl_lbl = QLabel()
        self.wl_lbl.setStyleSheet(
            "color:#c0c0cc; background:#1f1f2e; padding:4px 12px; border-radius:10px;"
            "font-size:10px;")
        self.wl_lbl.setAlignment(Qt.AlignCenter)
        right.addWidget(self.ar_lbl); right.addWidget(self.wl_lbl); right.addStretch()
        lay.addLayout(right)
    def set_data(self, player, avatar_urls, ncard_urls=None):
        self.name_lbl.setText(player.get("nickname", ""))
        self.uid_lbl.setText(f"UID {player.get('uid', '-')}")
        self.bio_lbl.setText(player.get("signature", "") or "—")
        self.ar_lbl.setText(f"AR {player.get('level','?')}")
        self.wl_lbl.setText(f"WL {player.get('worldLevel','?')}")
        print(f"[Banner] avatar_urls={avatar_urls}")
        print(f"[Banner] ncard_urls={ncard_urls}")
        if ncard_urls: self.loader.load(ncard_urls, self._set_bg)
        if avatar_urls: self.loader.load(avatar_urls, self.avatar.set_image)
    def _set_bg(self, pm):
        if pm: self._bg = pm; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(self.rect(), 14, 14)
        p.setClipPath(path)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0, QColor("#1a1a2e")); g.setColorAt(1, QColor("#12121c"))
        p.fillRect(self.rect(), g)
        if self._bg:
            pm = self._bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.setOpacity(0.3)
            p.drawPixmap((self.width()-pm.width())//2, (self.height()-pm.height())//2, pm)
            p.setOpacity(1.0)
        p.setClipping(False)
        p.setPen(QPen(QColor("#26263a"), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(0,0,-1,-1), 14, 14)
        super().paintEvent(e)
    def mousePressEvent(self, e):
        self.clicked.emit(); super().mousePressEvent(e)


class RankedCard(QFrame):
    clicked = Signal(dict)
    def __init__(self, char, rank, loader):
        super().__init__()
        self.char = char; self.rank = rank; self.loader = loader
        self.setFixedSize(190, 250)
        self.setCursor(Qt.PointingHandCursor)
        self._art = None; self._icon = None; self._hover = False
        self.setAttribute(Qt.WA_Hover, True)
        # Faqat kichik ikonka — katta art StatsPanel da yuklanadi
        if char.get("icon_urls"):
            loader.load(char["icon_urls"], self._set_icon)
    def _set_art(self, pm):
        if pm: self._art = pm; self.update()
    def _set_icon(self, pm):
        if pm: self._icon = pm; self.update()
    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 12, 12)
        p.setClipPath(path)
        p.fillRect(r, QColor("#14141f"))
        if self._art:
            s = self._art.scaled(QSize(r.width(), int(r.height()*1.15)),
                                 Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap((r.width()-s.width())//2, r.height()-s.height()+8, s)
        elif self._icon:
            s = self._icon.scaled(155, 155, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((r.width()-s.width())//2, 40, s)
        g = QLinearGradient(0, r.height()*0.5, 0, r.height())
        g.setColorAt(0, QColor(0,0,0,0)); g.setColorAt(1, QColor(0,0,0,230))
        p.fillRect(r, g)
        elem = (self.char.get("element") or "").capitalize()
        color = QColor(ELEMENT_COLORS.get(elem, "#7c5cff"))

        # ===== TEPA: category badge (masalan "120% ER") =====
        cat = self.rank.get("type") or "Ranked"
        f_cat = QFont(); f_cat.setPointSize(9); f_cat.setBold(True)
        p.setFont(f_cat)
        cat_w = min(r.width() - 16, 90)
        badge = QRect((r.width() - cat_w) // 2, 8, cat_w, 22)
        bp = QPainterPath(); bp.addRoundedRect(badge, 8, 8)
        p.fillPath(bp, QColor(0, 0, 0, 190))
        p.setPen(color)
        p.drawText(badge, Qt.AlignCenter, cat)

        # ===== Pastda: NAME =====
        f2 = QFont(); f2.setPointSize(10); f2.setBold(True); p.setFont(f2)
        p.setPen(QColor("#fff"))
        p.drawText(QRect(8, r.height() - 46, r.width()-16, 16), Qt.AlignCenter,
                   self.char.get("name","?"))

        # ===== Pastda: #27 of 212K =====
        top_val = self.rank.get("top", "?")
        t = self.rank.get("total", 0)
        tstr = f"{t/1000:.0f}K" if t >= 1000 else str(t)
        f3 = QFont(); f3.setPointSize(9); p.setFont(f3)
        p.setPen(QColor("#b0b0c0"))
        p.drawText(QRect(8, r.height() - 26, r.width()-16, 14), Qt.AlignCenter,
                   f"#{top_val} of {tstr}")

        p.setClipping(False)
        pen = QPen(color if self._hover else QColor("#26263a"), 1)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(0,0,-1,-1), 12, 12)
    def mousePressEvent(self, e):
        self.clicked.emit(self.char); super().mousePressEvent(e)


class CharacterRow(QFrame):
    clicked = Signal(dict)
    def __init__(self, char, loader):
        super().__init__()
        self.char = char; self.loader = loader
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(84)
        self._hover = False
        self.setAttribute(Qt.WA_Hover, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10); lay.setSpacing(16)
        self.avatar = QLabel(); self.avatar.setFixedSize(64, 64)
        self.avatar.setStyleSheet("background:#14141f; border-radius:8px;")
        lay.addWidget(self.avatar)
        mid = QVBoxLayout(); mid.setSpacing(2)
        name = QLabel(char.get("name", "?"))
        f = QFont(); f.setBold(True); f.setPointSize(12)
        name.setFont(f)
        name.setStyleSheet("color:#fff; background:transparent;")
        sub = QLabel(f"Lv. {char.get('level','?')}  •  C{char.get('constellation',0)}")
        sub.setStyleSheet("color:#7a7a8c; font-size:10px; background:transparent;")
        mid.addWidget(name); mid.addWidget(sub); mid.addStretch()
        lay.addLayout(mid)
        for s in char.get("artifact_sets", [])[:3]:
            ic = QLabel(); ic.setFixedSize(44, 44)
            ic.setStyleSheet("background:#14141f; border-radius:6px;")
            if s.get("icon_urls"):
                loader.load(s["icon_urls"],
                    lambda pm, l=ic: l.setPixmap(pm.scaled(44,44, Qt.KeepAspectRatio, Qt.SmoothTransformation)) if pm else None)
            lay.addWidget(ic)
        self.weapon = QLabel(); self.weapon.setFixedSize(50, 50)
        self.weapon.setStyleSheet("background:#14141f; border-radius:6px;")
        if char.get("weapon_icon_urls"):
            loader.load(char["weapon_icon_urls"],
                lambda pm: self.weapon.setPixmap(pm.scaled(50,50, Qt.KeepAspectRatio, Qt.SmoothTransformation)) if pm else None)
        lay.addWidget(self.weapon)
        stats = QLabel("   ".join(char.get("stats_short", [])))
        stats.setStyleSheet("color:#9090a0; font-size:10px; background:transparent;")
        lay.addWidget(stats, 1)
        if char.get("icon_urls"):
            loader.load(char["icon_urls"],
                lambda pm: self.avatar.setPixmap(pm.scaled(64,64, Qt.KeepAspectRatio, Qt.SmoothTransformation)) if pm else None)
    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 10, 10)
        p.setClipPath(path)
        p.fillRect(r, QColor("#1a1a24"))
        p.setClipping(False)
        p.setPen(QPen(QColor("#3a3a52") if self._hover else QColor("#26263a"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(0,0,-1,-1), 10, 10)
        super().paintEvent(e)
    def mousePressEvent(self, e):
        self.clicked.emit(self.char); super().mousePressEvent(e)


class WeaponBlock(QFrame):
    def __init__(self, loader):
        super().__init__()
        self.loader = loader
        self.setFixedWidth(400)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(14)
        self.icon = QLabel()
        self.icon.setFixedSize(72, 72)
        self.icon.setStyleSheet("background:#0f0f16; border-radius:8px;")
        self.icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.icon)
        right = QVBoxLayout(); right.setSpacing(3)
        self.name_lbl = QLabel()
        f = QFont(); f.setBold(True); f.setPointSize(13)
        self.name_lbl.setFont(f)
        self.name_lbl.setStyleSheet("color:#fff; background:transparent;")
        self.stars_lbl = QLabel()
        self.stars_lbl.setStyleSheet("color:#ffd76e; font-size:12px; background:transparent;")
        self.atk_lbl = QLabel()
        self.atk_lbl.setStyleSheet("color:#c0c0cc; font-size:11px; background:transparent;")
        self.sub_lbl = QLabel()
        self.sub_lbl.setStyleSheet("color:#8fe4f5; font-size:11px; background:transparent;")
        self.meta_lbl = QLabel()
        self.meta_lbl.setStyleSheet("color:#7a7a8c; font-size:10px; background:transparent;")
        right.addWidget(self.name_lbl)
        right.addWidget(self.stars_lbl)
        right.addWidget(self.atk_lbl)
        right.addWidget(self.sub_lbl)
        right.addWidget(self.meta_lbl)
        right.addStretch()
        lay.addLayout(right, 1)
    def set_weapon(self, w):
        if not w:
            self.name_lbl.setText("No weapon"); return
        self.name_lbl.setText(w.get("name", "-"))
        stars = w.get("stars", 0)
        self.stars_lbl.setText("★" * stars + "☆" * max(0, 5 - stars))
        base_atk = w.get("base_atk", 0)
        self.atk_lbl.setText(f"Base ATK: {base_atk}" if base_atk else "Base ATK: —")
        sn = w.get("substat_name"); sv = w.get("substat_value")
        self.sub_lbl.setText(f"{sn}: {sv}" if sn and sv else "")
        ref = w.get("refinement", 1)
        lvl = w.get("level", "?")
        self.meta_lbl.setText(f"R{ref}  •  Lv. {lvl}/90")
        urls = w.get("icon_urls")
        if urls: self.loader.load(urls, self._set_pm)
    def _set_pm(self, pm):
        if pm:
            self.icon.setPixmap(pm.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 10, 10)
        p.setClipPath(path)
        p.fillRect(r, QColor(18, 18, 26, 145))
        p.setClipping(False)
        super().paintEvent(e)


class RadarChart(QWidget):
    """8 o'qli elliptik radar chart (eni keng, bo'yi past)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(500)
        self.setMinimumHeight(220)
        self.setMaximumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._values = []
        self._color = QColor("#7c5cff")
        self._logged = False

    def set_values(self, values, color="#7c5cff"):
        self._values = values
        self._color = QColor(color)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if not self._logged:
            self._logged = True
            print(f"[Radar] size: {w}x{h}")

        # Fon
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 12, 12)
        p.fillPath(path, QColor(18, 18, 26, 145))

        n = max(3, len(self._values))
        if n < 3:
            return

        cx, cy = w / 2, h / 2
        # ELLIPTIK radiuslar — kengroq
        rx = (h / 2) - 30
        ry = (h / 2) - 30

        # Grid circles (elliptik)
        p.setPen(QPen(QColor("#2a2a3a"), 1))
        for r_frac in (0.25, 0.5, 0.75, 1.0):
            pts = []
            for i in range(n):
                ang = -math.pi/2 + 2*math.pi*i/n
                pts.append(QPointF(cx + rx*r_frac*math.cos(ang),
                                   cy + ry*r_frac*math.sin(ang)))
            p.drawPolygon(QPolygonF(pts))

        # Axis lines
        for i in range(n):
            ang = -math.pi/2 + 2*math.pi*i/n
            x = cx + rx*math.cos(ang)
            y = cy + ry*math.sin(ang)
            p.drawLine(int(cx), int(cy), int(x), int(y))

        # Data polygon (elliptik)
        if self._values:
            data_pts = []
            for i, (_, ratio) in enumerate(self._values):
                ang = -math.pi/2 + 2*math.pi*i/n
                r = max(0.15, min(1.0, ratio))
                data_pts.append(QPointF(cx + rx*r*math.cos(ang),
                                        cy + ry*r*math.sin(ang)))
            poly = QPolygonF(data_pts)
            p.setPen(QPen(self._color, 2))
            fill = QColor(self._color); fill.setAlpha(90)
            p.setBrush(QBrush(fill))
            p.drawPolygon(poly)
            p.setBrush(Qt.NoBrush)

        # Labels
        f = QFont(); f.setPointSize(8); p.setFont(f)
        p.setPen(QColor("#a8b0c0"))
        for i, (label, _) in enumerate(self._values):
            ang = -math.pi/2 + 2*math.pi*i/n
            lx = cx + (rx + 22) * math.cos(ang)
            ly = cy + (ry + 12) * math.sin(ang)
            rect = QRectF(lx - 55, ly - 10, 110, 20)
            p.drawText(rect, Qt.AlignCenter, label)


class ArtifactCard(QFrame):
    """Bitta artefakt: rasm + level + main stat + 4 substat."""
    def __init__(self, relic, loader):
        super().__init__()
        self.relic = relic; self.loader = loader
        self.setFixedSize(165, 180)
        self._pm = None
        self._hover = False
        self._enabled_stats = set()
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setStyleSheet("ArtifactCard { background: transparent; border: none; }")
        # Border rangi yulduzlar bo'yicha
        stars = relic.get("stars", 5)
        self._border = {5: "#e0a94a", 4: "#b16fd8", 3: "#5f9dd3"}.get(stars, "#3a3a52")
        if relic.get("icon_urls"):
            loader.load(relic["icon_urls"], self._set_pm)
    def _set_pm(self, pm):
        if pm: self._pm = pm; self.update()

    def set_stat_enabled(self, name, is_on):
        if is_on:
            self._enabled_stats.add(name)
        else:
            self._enabled_stats.discard(name)
        self.update()

    def set_enabled_set(self, enabled):
        if isinstance(enabled, dict):
            self._enabled_stats = {n for n, on in enabled.items() if on}
        else:
            self._enabled_stats = set(enabled)
        self.update()

    def enterEvent(self, e): self._hover = True; self.update()
    def leaveEvent(self, e): self._hover = False; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 10, 10)
        p.setClipPath(path)

        # Fon — qisman shaffof
        p.fillRect(r, QColor(18, 18, 26, 145))

        # ===== Icon (tepadan) =====
        icon_size = 62
        ic_x = (r.width() - icon_size) // 2
        ic_y = 4
        if self._pm:
            scaled = self._pm.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(ic_x + (icon_size - scaled.width()) // 2, ic_y, scaled)

        # ===== Level badge (icon o'ng tepasida, kichik) =====
        lvl = self.relic.get("level", "?")
        badge_w = 28
        badge_h = 15
        badge = QRect(r.width() - badge_w - 4, 4, badge_w, badge_h)
        bp = QPainterPath(); bp.addRoundedRect(badge, 7, 7)
        p.fillPath(bp, QColor(0, 0, 0, 200))
        f_badge = QFont(); f_badge.setPointSize(8); f_badge.setBold(True)
        p.setFont(f_badge)
        p.setPen(QColor("#ffd76e"))
        p.drawText(badge, Qt.AlignCenter, f"+{lvl}")

        # ===== Main stat (icon ustiga qisman chiqadi) =====
        main_y = ic_y + icon_size - 10
        # Gradient fon (icon va main stat orasida yumshoq o'tish)
        grad = QLinearGradient(0, main_y - 8, 0, main_y + 24)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.5, QColor(10, 10, 18, 180))
        grad.setColorAt(1, QColor(10, 10, 18, 200))
        p.fillRect(QRect(0, main_y - 8, r.width(), 32), grad)

        f_main = QFont(); f_main.setPointSize(15); f_main.setBold(True)
        p.setFont(f_main)
        p.setPen(QColor("#fff"))
        p.drawText(QRect(8, main_y, r.width() - 16, 20), Qt.AlignCenter,
                   self.relic.get("main_value", "-"))

        f_mainn = QFont(); f_mainn.setPointSize(8)
        p.setFont(f_mainn)
        p.setPen(QColor("#a0a8b8"))
        p.drawText(QRect(8, main_y + 18, r.width() - 16, 12), Qt.AlignCenter,
                   self.relic.get("main_name", "-"))

        # ===== Divider =====
        div_y = main_y + 30
        p.setPen(QPen(QColor("#2a2a3a"), 1))
        p.drawLine(12, div_y, r.width() - 12, div_y)

        # ===== Substats (4 ta) =====
        f4 = QFont(); f4.setPointSize(9)
        y = div_y + 3
        for name, val in self.relic.get("subs", [])[:4]:
            enabled = name in self._enabled_stats
            if enabled:
                f_marker = QFont(); f_marker.setPointSize(10); f_marker.setBold(True)
                p.setFont(f_marker)
                p.setPen(QColor("#ffd76e"))
                p.drawText(QRect(4, y, 12, 14), Qt.AlignLeft | Qt.AlignVCenter, "✓")
            f4b = QFont(); f4b.setPointSize(8); p.setFont(f4b)
            p.setPen(QColor("#e8e8f0") if enabled else QColor("#6a7484"))
            p.drawText(QRect(18, y, 90, 14), Qt.AlignLeft, name)
            p.setPen(QColor("#fff") if enabled else QColor("#b0b8c4"))
            p.drawText(QRect(0, y, r.width() - 8, 14), Qt.AlignRight, val)
            y += 13

        # ===== RV/CV — substatlardan 4px pastda =====
        rv = self.relic.get("rv", 0)
        cv = self.relic.get("cv", 0)
        rv_y = y + 1
        f5 = QFont(); f5.setPointSize(10); f5.setBold(True); p.setFont(f5)
        p.setPen(QColor("#ffd76e"))
        p.drawText(QRect(10, rv_y, r.width() // 2 - 10, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, f"RV {rv:.0f}%")
        p.setPen(QColor("#8fe4f5"))
        p.drawText(QRect(r.width() // 2, rv_y, r.width() // 2 - 10, 14),
                   Qt.AlignRight | Qt.AlignVCenter, f"CV {cv:.1f}")

        # ===== Border =====
        p.setClipping(False)
        border = {"5": "#e0a94a", "4": "#b16fd8", "3": "#5f9dd3"}.get(
            str(self.relic.get("stars", 5)), "#3a3a52")
        pen = QPen(QColor(border) if self._hover else QColor(border).darker(140), 2)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -2, -2), 10, 10)

        super().paintEvent(e)

    def mousePressEvent(self, e):
        self.is_on = not self.is_on
        self.toggled.emit(self.stat_name, self.is_on)
        self.update()


class SubstatPill(QFrame):
    """Bosiladigan substat tugmasi. RV hisoblashda ishlatiladi."""
    toggled = Signal(str, bool)

    def __init__(self, name, value_str, icon_urls, loader, is_on=True):
        super().__init__()
        self.stat_name = name
        self.is_on = is_on
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(26)
        self.setMinimumWidth(70)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setStyleSheet("SubstatPill { background: transparent; border: none; }")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 2, 12, 2)
        lay.setSpacing(6)

        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet(
            "background:transparent; font-size:11px; color:#c8c8d4; font-weight:bold;")
        lay.addWidget(self.name_lbl)

        self.val_lbl = QLabel(value_str)
        self.val_lbl.setStyleSheet(
            "background:transparent; font-size:11px; font-weight:bold; color:#fff;")
        lay.addWidget(self.val_lbl)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 13, 13)
        p.setClipPath(path)
        p.fillRect(r, QColor(18, 18, 26, 145))
        if self.is_on:
            p.fillRect(r, QColor(255, 200, 60, 40))
        p.setClipping(False)
        pen = QPen(QColor(255, 215, 100) if self.is_on else QColor(60, 60, 75),
                   2 if self.is_on else 1)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -2, -2), 13, 13)

    def mousePressEvent(self, e):
        self.is_on = not self.is_on
        self.toggled.emit(self.stat_name, self.is_on)
        self.update()


class CharacterArtWidget(QWidget):
    """Personaj rasmi + constellation (chap) + talent (o'ng) ikonkalar."""
    def __init__(self, loader, parent=None):
        super().__init__(parent)
        self.loader = loader
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 360)
        self._art = None
        self._const_count = 0
        self._const_pms = [None] * 6
        self._talent_pms = [None] * 3
        self._talent_levels = [0, 0, 0]
        self._header_text = ""

    def set_character(self, char):
        self._art = None
        self._header_text = (f"{char.get('name','?')}   •   "
                             f"Lv. {char.get('level','?')}   •   "
                             f"C{char.get('constellation',0)}")
        self._const_count = char.get("constellation", 0)
        self._const_pms = [None] * 6
        self._talent_pms = [None] * 3
        self._talent_levels = [0, 0, 0]
        # Art
        if char.get("art_urls"):
            self.loader.load(char["art_urls"], self._set_art)
        elif char.get("icon_urls"):
            self.loader.load(char["icon_urls"], self._set_art)
        # Constellations
        for i, urls in enumerate(char.get("const_icon_urls", [])):
            if urls:
                self.loader.load(urls, self._make_const_setter(i))
        # Talents — levels only
        for i, t in enumerate(char.get("talents", [])):
            if i < 3:
                self._talent_levels[i] = t.get("level", 0)
        self.update()

    def _make_const_setter(self, idx):
        def _set(pm):
            if pm and 0 <= idx < 6:
                self._const_pms[idx] = pm
                self.update()
        return _set

    def _make_talent_setter(self, idx):
        def _set(pm):
            if pm and 0 <= idx < 3:
                self._talent_pms[idx] = pm
                self.update()
        return _set

    def _set_art(self, pm):
        if pm:
            self._art = pm
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        # Art — balandlikka to'liq sig'diriladi, eni ortiqcha bo'lsa chetlari kesiladi
        if self._art:
            # Rasmni BALANDLIKKA moslab scale qilamiz (tepadan pastgacha to'liq)
            scaled = self._art.scaled(10000, r.height(),
                                       Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)
            # Gorizontal markazga
            x = (r.width() - scaled.width()) // 2
            y = 0
            p.drawPixmap(x, y, scaled)

            # O'ng tomonni fade — 80px
            fade = QLinearGradient(r.width() - 80, 0, r.width(), 0)
            fade.setColorAt(0.0, QColor(10, 10, 18, 0))
            fade.setColorAt(1.0, QColor(10, 10, 18, 230))
            p.fillRect(QRect(r.width() - 80, 0, 80, r.height()), fade)
        else:
            p.fillRect(r, QColor("#14141f"))

        # ---- Header (tepadan, personaj rasmi ustiga) ----
        if self._header_text:
            f_h = QFont(); f_h.setPointSize(12); f_h.setBold(True)
            p.setFont(f_h)
            # Matn o'lchamini aniqlash
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(self._header_text) + 24
            th = 28
            hx, hy = 12, 12
            # Fon
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(10, 10, 18, 210))
            p.drawRoundedRect(hx, hy, tw, th, 8, 8)
            # Matn
            p.setPen(QColor("#fff"))
            p.drawText(QRect(hx, hy, tw, th), Qt.AlignCenter, self._header_text)

        # ---- Constellation ustuni (chap) — TEPADA ----
        c_size = 38
        c_x = 10
        c_y0 = 60
        c_step = 52
        for i in range(6):
            y = c_y0 + i * c_step
            if y + c_size > r.height() - 10:
                break
            unlocked = i < self._const_count
            self._draw_circle(p, c_x, y, c_size, unlocked)
            pm = self._const_pms[i]
            if unlocked and pm:
                ic = pm.scaled(c_size - 8, c_size - 8, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
                p.drawPixmap(c_x + 4, y + 4, ic)
            else:
                self._draw_lock(p, c_x, y, c_size)
            # C raqami
            f = QFont(); f.setPointSize(7); f.setBold(True)
            p.setFont(f); p.setPen(QColor("#c8c8d4"))
            p.drawText(c_x, y + c_size, c_size, 12, Qt.AlignCenter, f"C{i+1}")

        # ---- Talent ustuni (o'ng) — PASTDA ----
        t_size = 32
        t_step = 44
        card_w = 170
        t_x = r.width() - card_w - 8
        # Pastdan hisoblaymiz
        t_y0 = r.height() - 3 * t_step - 10
        for i in range(3):
            y = t_y0 + i * t_step
            if y + t_step > r.height():
                break
            tname = ["Normal Attack", "Elemental Skill", "Elemental Burst"][i]
            # Label kartochka
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(20, 20, 30, 220))
            p.drawRoundedRect(t_x, y, card_w, t_size + 4, 8, 8)
            # Nom
            f_lbl = QFont(); f_lbl.setPointSize(10); f_lbl.setBold(True)
            p.setFont(f_lbl)
            p.setPen(QColor("#e0e0e8"))
            p.drawText(t_x + 10, y, card_w - 50, t_size + 4, Qt.AlignLeft | Qt.AlignVCenter, tname)
            # Level
            lvl = self._talent_levels[i]
            f_lvl = QFont(); f_lvl.setPointSize(11); f_lvl.setBold(True)
            p.setFont(f_lvl)
            p.setPen(QColor("#ffd76e"))
            p.drawText(t_x + card_w - 42, y, 38, t_size + 4, Qt.AlignCenter, str(lvl))

    def _draw_circle(self, p, x, y, size, unlocked):
        p.setPen(Qt.NoPen)
        bg = QColor(20, 20, 30, 200) if unlocked else QColor(10, 10, 15, 230)
        p.setBrush(bg)
        p.drawEllipse(x, y, size, size)
        border = QColor(255, 215, 100, 220) if unlocked else QColor(70, 70, 85, 220)
        p.setPen(QPen(border, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(x, y, size, size)

    def _draw_lock(self, p, x, y, size):
        cx = x + size / 2
        cy = y + size / 2 + 2
        # Body
        body_w = size * 0.45
        body_h = size * 0.35
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(140, 140, 160, 220))
        p.drawRoundedRect(int(cx - body_w/2), int(cy - 2),
                          int(body_w), int(body_h), 2, 2)
        # Shackle
        p.setPen(QPen(QColor(140, 140, 160, 220), 2))
        p.setBrush(Qt.NoBrush)
        arc_w = int(body_w * 0.7)
        p.drawArc(int(cx - arc_w/2), int(cy - body_h*0.8 - 4),
                  arc_w, int(body_h * 1.1), 0, 180 * 16)
        # Keyhole
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(80, 80, 100))
        p.drawEllipse(int(cx - 2), int(cy + body_h*0.25 - 3), 4, 4)


class TeamPanel(QFrame):
    """Akasha uslubi: tavsiya etilgan jamoa + ranking badge."""
    def __init__(self, loader, name_map, parent=None):
        super().__init__(parent)
        self.loader = loader
        self.name_map = name_map
        print(f"[TeamPanel] init: loader={loader is not None}, name_map={name_map is not None}")
        self.setFixedWidth(280)
        self.setFixedHeight(85)
        self.setStyleSheet("background:transparent;")

        self._rank = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)


        # ===== O'rta: TOP X% + QB COMBO badge =====
        self.badges_row = QHBoxLayout()
        self.badges_row.setSpacing(6)
        self.badges_row.setAlignment(Qt.AlignCenter)

        self.top_lbl = QLabel("—")
        self.top_lbl.setStyleSheet(
            "background:rgba(60,140,90,220); color:#fff;"
            "padding:5px 14px; border-radius:12px;"
            "font-weight:bold; font-size:11px;")
        self.top_lbl.setAlignment(Qt.AlignCenter)
        self.badges_row.addWidget(self.top_lbl, 1)

        self.combo_lbl = QLabel("—")
        self.combo_lbl.setStyleSheet(
            "background:rgba(60,140,90,220); color:#fff;"
            "padding:5px 14px; border-radius:12px;"
            "font-weight:bold; font-size:11px;")
        self.combo_lbl.setAlignment(Qt.AlignCenter)
        self.badges_row.addWidget(self.combo_lbl, 1)
        lay.addLayout(self.badges_row)

        # ===== Past: rank / total =====
        self.rank_lbl = QLabel("—")
        self.rank_lbl.setAlignment(Qt.AlignCenter)
        self.rank_lbl.setStyleSheet(
            "color:#e0e0e8; font-weight:bold; font-size:16px;"
            "background:transparent;")
        lay.addWidget(self.rank_lbl)

    def set_team(self, char_id, rank_info):
        """Faqat ranking badge ko'rsatamiz (jamoa tavsiyalari o'chirilgan)."""
        if not rank_info:
            self.top_lbl.setText("—")
            self.combo_lbl.setText("—")
            self.rank_lbl.setText("—")
            return

        top = rank_info.get("top", 0)
        total = rank_info.get("total", 0)
        short = rank_info.get("type", "—")

        if total > 0:
            pct = top / total * 100
            if pct < 0.01:
                pct_str = f"TOP {pct:.3f}%"
            elif pct < 1:
                pct_str = f"TOP {pct:.2f}%"
            else:
                pct_str = f"TOP {pct:.1f}%"
        else:
            pct_str = "—"
        self.top_lbl.setText(pct_str)
        self.combo_lbl.setText(short.upper() if short != "—" else "—")

        t_str = f"{total:,}".replace(",", " ")
        self.rank_lbl.setText(f"{top} / {t_str}")


    def _make_icon_setter(self, lbl):
        def _set(pm):
            if pm:
                lbl.setPixmap(pm.scaled(44, 44, Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation))
        return _set

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 12, 12)
        p.setClipPath(path)
        p.fillRect(r, QColor(18, 18, 26, 145))
        p.setClipping(False)
        p.setPen(QPen(QColor("#2a2a3a"), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(0, 0, -1, -1), 12, 12)
        super().paintEvent(e)


class StatsPanel(QFrame):
    """Akasha.cv uslubi:
       - Chap 40%: personaj rasmi — butun panel balandligi
       - O'ng 60%: qurol, artefakt seti, statlar, radar, 5 ta artefakt
    """
    def __init__(self, loader, name_map=None):
        super().__init__()
        self.loader = loader
        self.name_map = name_map
        self.setStyleSheet("StatsPanel { background:transparent; border-radius:12px; }")
        self.setMinimumHeight(400)
        self.setVisible(False)
        self._bg = None
        self._char = None

        # Asosiy layout — GORIZONTAL (chap: rasm, o'ng: content)
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 20, 12)
        main.setSpacing(12)

        # ===== CHAP: personaj rasmi (butun balandlik) =====
        self.art_widget = CharacterArtWidget(loader)
        main.addWidget(self.art_widget, 4)

        # ===== O'NG: content =====
        right = QWidget()
        right.setStyleSheet("background:transparent;")
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 12, 0, 0)
        rl.setSpacing(6)

        # ===== Tavsiya etilgan jamoa paneli (overlay) =====
        if name_map is not None:
            self.team_panel = TeamPanel(loader, name_map, parent=self)
            self.team_panel.setFixedWidth(300)
            self.team_panel.hide()
        else:
            self.team_panel = None


        # Weapon
        self.weapon_block = WeaponBlock(loader)
        self.weapon_block.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(self.weapon_block, 0, Qt.AlignLeft)

        # Artifacts set
        self.artifacts_widget = QWidget()
        self.artifacts_widget.setStyleSheet("background:transparent;")
        self.artifacts_widget.setFixedWidth(400)
        self.artifacts_layout = QVBoxLayout(self.artifacts_widget)
        self.artifacts_layout.setContentsMargins(0, 0, 0, 0)
        self.artifacts_layout.setSpacing(2)
        rl.addWidget(self.artifacts_widget, 0, Qt.AlignLeft)

        # Stats + Radar
        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(14)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background:transparent;")
        self.grid_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.grid_container.setFixedWidth(400)
        gc_layout = QVBoxLayout(self.grid_container)
        gc_layout.setContentsMargins(0, 0, 0, 0)
        gc_layout.setSpacing(0)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(0)
        self.grid.setVerticalSpacing(4)
        self.grid.setContentsMargins(0, 0, 0, 0)
        gc_layout.addLayout(self.grid)
        mid.addWidget(self.grid_container, 0, Qt.AlignLeft | Qt.AlignTop)

        self.radar = RadarChart()
        self.radar.setMinimumWidth(200)
        self.radar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mid.addWidget(self.radar, 1)

        rl.addLayout(mid, 1)

        # 5 ta artefakt
        self.relic_row = QHBoxLayout()
        self.relic_row.setContentsMargins(0, 6, 0, 0)
        self.relic_row.setSpacing(10)
        self.relic_row.setAlignment(Qt.AlignLeft)
        rl.addLayout(self.relic_row)

        # Pastdagi substat lenta
        strip_wrap = QHBoxLayout()
        strip_wrap.setContentsMargins(0, 4, 0, 0)
        strip_wrap.setSpacing(10)

        self.substat_scroll = QScrollArea()
        self.substat_scroll.setWidgetResizable(True)
        self.substat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.substat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.substat_scroll.setFixedHeight(48)
        self.substat_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")

        self.substat_container = QWidget()
        self.substat_container.setStyleSheet("background:transparent;")
        self.substat_row = QHBoxLayout(self.substat_container)
        self.substat_row.setContentsMargins(0, 4, 0, 4)
        self.substat_row.setSpacing(6)
        self.substat_row.setAlignment(Qt.AlignLeft)
        self.substat_scroll.setWidget(self.substat_container)
        strip_wrap.addWidget(self.substat_scroll, 1)

        self.rv_label = QLabel("RV 0%")
        self.rv_label.setStyleSheet(
            "color:#ffd76e; font-size:13px; font-weight:bold;"
            "background:rgba(26,26,36,220); padding:5px 14px; border-radius:12px;")
        self.rv_label.setFixedHeight(30)
        self.rv_label.setAlignment(Qt.AlignCenter)
        strip_wrap.addWidget(self.rv_label, 0)

        self.cv_label = QLabel("CV 0")
        self.cv_label.setStyleSheet(
            "color:#8fe4f5; font-size:13px; font-weight:bold;"
            "background:rgba(26,26,36,220); padding:5px 14px; border-radius:12px;")
        self.cv_label.setFixedHeight(30)
        self.cv_label.setAlignment(Qt.AlignCenter)
        strip_wrap.addWidget(self.cv_label, 0)

        rl.addLayout(strip_wrap)

        main.addWidget(right, 6)

        self._w = []
        self._relics = []
        self._enabled = {}

    def show_for(self, char, ncard_urls=None):
        print(f"[StatsPanel] show_for called: {char.get('name')}")
        try:
            self._show_for_impl(char, ncard_urls)
        except Exception as e:
            import traceback
            print(f"[StatsPanel] ERROR: {e}")
            traceback.print_exc()

    def _show_for_impl(self, char, ncard_urls=None):
        self._char = char
        # Team panel yangilash
        if hasattr(self, "team_panel") and self.team_panel:
            rank = char.get("rank")
            cid = char.get("id")
            if rank and cid:
                self.team_panel.set_team(cid, rank)
                self.team_panel.show()
                self.team_panel.raise_()
                # Joylashtirish
                w = self.width()
                self.team_panel.move(w - self.team_panel.width() - 20, 12)
            else:
                self.team_panel.hide()
        self.weapon_block.set_weapon(char.get("weapon"))

        # Artefakt setlari — 4x bo'lsa gul icon, aks holda matn
        while self.artifacts_layout.count():
            it = self.artifacts_layout.takeAt(0)
            w = it.widget() if it else None
            if w: w.setParent(None)

        sets = [x for x in char.get("artifact_sets", []) if x.get("count", 0) >= 2]
        # 4x setni topamiz
        four = [s for s in sets if s.get("count", 0) >= 4]

        if four:
            s4 = four[0]
            row = QWidget()
            row.setStyleSheet("background:rgba(26,26,36,200); border-radius:5px;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            ic = QLabel()
            ic.setFixedSize(26, 26)
            ic.setStyleSheet("background:transparent;")
            if s4.get("icon_urls"):
                self.loader.load(s4["icon_urls"],
                    lambda pm, l=ic: l.setPixmap(pm.scaled(26, 26, Qt.KeepAspectRatio,
                                                            Qt.SmoothTransformation)) if pm else None)
            rl.addWidget(ic)
            name = QLabel(s4.get("name", "?"))
            name.setStyleSheet("color:#c8b8d8; font-size:12px; background:transparent;")
            rl.addWidget(name)
            rl.addSpacing(10)
            cnt = QLabel(f"×{s4.get('count','?')}")
            cnt.setStyleSheet("color:#fff; font-size:12px; font-weight:bold; background:transparent;")
            rl.addWidget(cnt)
            rl.addStretch()
            self.artifacts_layout.addWidget(row)

            # Qolgan 2x setlar matn sifatida
            others = [s for s in sets if s is not s4 and s.get("count", 0) > 0]
            if others:
                parts = []
                for s in others:
                    parts.append(f"{s.get('count','?')}× {s.get('name','?')}")
                sub = QLabel("  +  ".join(parts))
                sub.setStyleSheet(
                    "color:#a0a8b8; background:rgba(26,26,36,150);"
                    "padding:4px 12px; border-radius:6px; font-size:11px;")
                self.artifacts_layout.addWidget(sub)
        else:
            # Faqat 2x+2x yoki boshqa
            parts = []
            for s in sets:
                parts.append(f"{s.get('count','?')}× {s.get('name','?')}")
            sub = QLabel("  +  ".join(parts) if parts else "-")
            sub.setStyleSheet(
                "color:#a0a8b8; background:rgba(26,26,36,150);"
                "padding:6px 12px; border-radius:6px; font-size:11px;")
            sub.setWordWrap(True)
            self.artifacts_layout.addWidget(sub)

        # Stats — gorizontal qatorlar (ikonka bilan)
        for wdg in self._w: wdg.setParent(None)
        self._w.clear()
        stats_list = char.get("stats_ordered") or list(char.get("stats", {}).items())
        # grid_container balandligini statlar soniga moslash
        self.grid_container.setFixedHeight(len(stats_list) * 27 + 6)
        for i, (k, v) in enumerate(stats_list):
            row = QWidget()
            row.setStyleSheet("background:rgba(26,26,36,180); border-radius:5px;")
            row.setFixedHeight(24)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(16, 0, 20, 0)
            rl.setSpacing(6)

            lk = QLabel(k)
            lk.setStyleSheet("color:#a8b0c0; font-size:10px; background:transparent;")
            lv = QLabel(v)
            lv.setStyleSheet("color:#fff; font-size:10px; font-weight:bold; background:transparent;")
            lv.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(lk)
            rl.addStretch()
            rl.addWidget(lv)
            self.grid.addWidget(row, i, 0)
            self._w.append(row)

        # Radar — faqat ranked bo'lsa
        if char.get("is_ranked"):
            self.radar.setVisible(True)
            radar_vals = char.get("radar_values") or []
            elem = (char.get("element") or "").capitalize()
            self.radar.set_values(radar_vals, ELEMENT_COLORS.get(elem, "#7c5cff"))
        else:
            self.radar.setVisible(False)

        # Personaj art + constellation + talents
        self.art_widget.set_character(char)

        # Namecard fon
        own_nc = char.get("own_namecard_urls")
        if own_nc:
            self.loader.load(own_nc, self._set_bg)
        elif ncard_urls:
            self.loader.load(ncard_urls, self._set_bg)

        # ===== Pastdagi substat lenta (self._enabled ni to'ldiradi) =====
        self._build_substat_strip(char)

        # 5 ta artefakt kartochkasi — endi _enabled tayyor
        for w in self._relics: w.setParent(None)
        self._relics.clear()
        for rel in char.get("relics", []):
            card = ArtifactCard(rel, self.loader)
            card.set_enabled_set(self._enabled)
            self.relic_row.addWidget(card)
            self._relics.append(card)

        self.setVisible(True)

    def _build_substat_strip(self, char):
        # Tozalash
        while self.substat_row.count():
            it = self.substat_row.takeAt(0)
            w = it.widget() if it else None
            if w: w.setParent(None)
        self._enabled = {}

        # Aggregatsiya
        agg = {}
        for relic in char.get("relics", []):
            for name, val in relic.get("subs", []):
                agg[name] = agg.get(name, 0.0) + num_val(val)

        # Default: flat statlar OFF, qolgani ON
        FLAT = {"HP", "ATK", "DEF"}
        for name in agg:
            self._enabled[name] = name not in FLAT

        # Tartib
        ORDER = ["Crit Rate", "Crit DMG", "ATK%", "HP%", "DEF%",
                 "Elemental Mastery", "Energy Recharge",
                 "Pyro DMG", "Electro DMG", "Hydro DMG", "Dendro DMG",
                 "Anemo DMG", "Geo DMG", "Cryo DMG", "Physical DMG",
                 "HP", "ATK", "DEF"]
        ordered = [n for n in ORDER if n in agg] + [n for n in agg if n not in ORDER]

        for name in ordered:
            v = agg[name]
            is_pct = (name.endswith("%") or name in ("Crit Rate", "Crit DMG",
                                                      "Energy Recharge")
                      or name.endswith("DMG"))
            val_str = f"{v:.1f}%" if is_pct else f"{int(round(v))}"
            icon_name = STAT_ICONS.get(name)
            icon_urls = [
                f"https://enka.network/ui/{icon_name}.png",
                f"https://gi.yatta.moe/assets/UI/{icon_name}.png",
            ] if icon_name else []
            pill = SubstatPill(name, val_str, icon_urls, self.loader,
                                self._enabled[name])
            pill.toggled.connect(self._on_pill_toggled)
            self.substat_row.addWidget(pill)

        self._recompute_rv()

    def _on_pill_toggled(self, name, is_on):
        self._enabled[name] = is_on
        # Har bir relic kartaga tarqatamiz
        for card in self._relics:
            card.set_stat_enabled(name, is_on)
        self._recompute_rv()

    def _recompute_rv(self):
        if not self._char: return
        total = 0.0
        for relic in self._char.get("relics", []):
            rv = 0.0
            for sname, sval in relic.get("subs", []):
                if not self._enabled.get(sname, True): continue
                mx = MAX_ROLL.get(sname)
                if mx:
                    rv += num_val(sval) / mx * 100
            relic["rv"] = rv
            total += rv
        self.rv_label.setText(f"RV {total:.0f}%")

        # Umumiy CV — substatlar + circlet main stat
        total_cv = 0.0
        for relic in self._char.get("relics", []):
            total_cv += relic.get("cv", 0)
        # Circlet main stat hissasi
        for relic in self._char.get("relics", []):
            if relic.get("slot") == "EQUIP_DRESS":
                mp = relic.get("main_prop", "")
                mv = num_val(relic.get("main_value", "0"))
                if mp == "FIGHT_PROP_CRITICAL":
                    # CR circlet: 2× qo'shiladi
                    total_cv += 2 * mv
                elif mp == "FIGHT_PROP_CRITICAL_HURT":
                    # CD circlet: 1× qo'shiladi
                    total_cv += mv
                break
        self.cv_label.setText(f"CV {total_cv:.1f}")

        for card in self._relics:
            card.update()

    def _set_bg(self, pm):
        if pm: self._bg = pm; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 12, 12)
        p.setClipPath(path)
        # Fon: namecard
        if self._bg:
            pm = self._bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding,
                                 Qt.SmoothTransformation)
            p.setOpacity(1.0)
            p.drawPixmap((r.width()-pm.width())//2, (r.height()-pm.height())//2, pm)
            p.fillRect(r, QColor(10, 10, 18, 125))
        else:
            p.fillRect(r, QColor(20, 20, 31, 200))
        p.setClipping(False)
        p.setPen(QPen(QColor("#26263a"), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(0, 0, -1, -1), 12, 12)
        super().paintEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "team_panel") and self.team_panel:
            w = self.width()
            self.team_panel.move(w - self.team_panel.width() - 20, 12)

    def hide_panel(self):
        self.setVisible(False)
        self._bg = None
        if hasattr(self, "team_panel") and self.team_panel:
            self.team_panel.hide()
