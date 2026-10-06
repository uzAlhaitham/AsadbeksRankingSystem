from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QStackedWidget, QFrame
)
from .constants import (GAMES, STAT_KEYS, PROP_NAMES, PROP_IS_PCT,
                        ELEMENT_TO_DMG, SLOT_NAMES, MAX_ROLL, num_val)
from .widgets import (
    ProfileBanner, RankedCard, CharacterRow, StatsPanel, FlowLayout
)


# ============ Helper funksiyalar ============
def calc_relic_cv(subs):
    cr = cd = 0.0
    for name, val in subs:
        if name == "Crit Rate": cr = num_val(val)
        elif name == "Crit DMG": cd = num_val(val)
    return 2 * cr + cd


def parse_weapon_stats(flat):
    stats = flat.get("weaponStats") or []
    base_atk = 0; sub_name = None; sub_val = None
    for s in stats:
        prop = s.get("appendPropId", "")
        val = s.get("statValue", 0)
        if prop == "FIGHT_PROP_BASE_ATTACK":
            base_atk = int(val)
        else:
            sub_name = PROP_NAMES.get(prop, prop.replace("FIGHT_PROP_", ""))
            if prop in PROP_IS_PCT:
                sub_val = f"{val:.1f}%"
            else:
                sub_val = f"{int(val)}"
    return base_atk, sub_name, sub_val


def parse_relic(eq, nm):
    flat = eq.get("flat", {}) or {}
    if flat.get("itemType") != "ITEM_RELIQUARY":
        return None
    rel = eq.get("reliquary", {}) or {}
    slot = flat.get("equipType", "")
    stars = flat.get("rankLevel", 5)
    level = rel.get("level", 0)
    if level > 20: level = 20
    icon = flat.get("icon")
    icon_urls = nm.icon_urls(icon) if icon else []

    mst = flat.get("reliquaryMainstat") or {}
    mprop = mst.get("mainPropId", "")
    mval = mst.get("statValue", 0)
    mname = PROP_NAMES.get(mprop, mprop.replace("FIGHT_PROP_", ""))
    mval_str = f"{mval:.1f}%" if mprop in PROP_IS_PCT else f"{int(mval)}"

    subs = []
    for s in flat.get("reliquarySubstats", []) or []:
        ap = s.get("appendPropId", "")
        sv = s.get("statValue", 0)
        sn = PROP_NAMES.get(ap, ap.replace("FIGHT_PROP_", ""))
        sv_str = f"{sv:.1f}%" if ap in PROP_IS_PCT else f"{int(sv)}"
        subs.append((sn, sv_str))

    return {
        "slot": slot,
        "slot_name": SLOT_NAMES.get(slot, ""),
        "stars": stars,
        "level": level,
        "icon_urls": icon_urls,
        "main_prop": mprop,
        "main_name": mname,
        "main_value": mval_str,
        "subs": subs,
        "cv": calc_relic_cv(subs),
        "rv": 0,
        "set_id": flat.get("setId"),
    }


def calc_radar(stats, element):
    def num(s):
        if not s: return 0
        return float(str(s).replace(",", "").replace("%", ""))
    hp = num(stats.get("Max HP", stats.get("HP")))
    atk = num(stats.get("ATK"))
    df = num(stats.get("DEF"))
    em = num(stats.get("Elemental Mastery"))
    er = num(stats.get("Energy Recharge"))
    cr = num(stats.get("Crit Rate"))
    cd = num(stats.get("Crit DMG"))
    dmg = 0
    for k, v in stats.items():
        if "DMG" in k: dmg = max(dmg, num(v))
    def norm(v, good, perfect):
        if v <= 0: return 0.0
        if v >= perfect: return 1.0
        if v >= good: return 0.75 + 0.25 * (v - good) / (perfect - good)
        return 0.75 * (v / good)
    elem_label = f"{element} DMG" if element else "Element DMG"
    return [
        ("HP",        norm(hp, 20000, 45000)),
        ("ATK",       norm(atk, 1500, 3000)),
        ("DEF",       norm(df, 800, 2500)),
        ("EM",        norm(em, 300, 1000)),
        ("ER%",       norm(er, 120, 200)),
        ("Crit Rate", norm(cr, 60, 100)),
        ("Crit DMG",  norm(cd, 150, 250)),
        (elem_label,  norm(dmg, 60, 120)),
    ]


# ============ HomePage (oddiy UID input) ============
class HomePage(QWidget):
    submit = Signal(str)
    open_profile = Signal()

    def __init__(self, loader):
        super().__init__()
        self.loader = loader
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # State 0: UID input
        inp = QWidget()
        il = QVBoxLayout(inp); il.addStretch()

        logo = QLabel("Asadbek's Ranking System")
        f = QFont(); f.setPointSize(36); f.setBold(True)
        logo.setFont(f); logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("color:#fff;")
        il.addWidget(logo)

        sub = QLabel("Enter your UID to view your profile")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color:#8a8a9a; font-size:12px; margin-bottom:28px;")
        il.addWidget(sub)

        row = QHBoxLayout(); row.addStretch()
        self.uid_edit = QLineEdit()
        self.uid_edit.setPlaceholderText("UID")
        self.uid_edit.setFixedWidth(320); self.uid_edit.setAlignment(Qt.AlignCenter)
        self.uid_edit.setMaxLength(12)
        self.btn = QPushButton("Search")
        self.btn.setFixedSize(110, 40)
        self.btn.setStyleSheet(
            "QPushButton { background:#7c5cff; color:#fff; border:none;"
            " border-radius:10px; font-weight:bold; font-size:12px; }"
            "QPushButton:hover { background:#8b6fff; }"
            "QPushButton:disabled { background:#3a3a52; color:#8a8a9a; }")
        row.addWidget(self.uid_edit); row.addWidget(self.btn)
        row.addStretch(); il.addLayout(row)

        self.err = QLabel(""); self.err.setAlignment(Qt.AlignCenter)
        self.err.setStyleSheet("color:#ff6b6b; margin-top:16px; font-size:11px;")
        il.addWidget(self.err); il.addStretch()
        self.stack.addWidget(inp)

        # State 1: katta banner
        wrap = QWidget()
        wl = QVBoxLayout(wrap); wl.setContentsMargins(100, 60, 100, 60)
        wl.addStretch()
        self.banner = ProfileBanner(loader, compact=False)
        self.banner.clicked.connect(self.open_profile.emit)
        wl.addWidget(self.banner)
        hint = QLabel("Click to view characters")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#8a8a9a; margin-top:18px; font-size:11px;")
        wl.addWidget(hint); wl.addStretch()
        self.stack.addWidget(wrap)

        self.btn.clicked.connect(self._submit)
        self.uid_edit.returnPressed.connect(self._submit)

    def set_error(self, t): self.err.setText(t)
    def set_loading(self, on):
        self.btn.setEnabled(not on); self.uid_edit.setEnabled(not on)

    def show_profile(self, player, avatar_urls, ncard_urls=None):
        self.banner.set_data(player, avatar_urls, ncard_urls)
        self.stack.setCurrentIndex(1)

    def show_input(self):
        self.stack.setCurrentIndex(0)

    def _submit(self):
        uid = self.uid_edit.text().strip()
        if not uid.isdigit() or not (8 <= len(uid) <= 10):
            self.set_error("Invalid UID. Please enter 8-10 digits."); return
        self.set_error("")
        self.submit.emit(uid)


# ============ CharactersPage ============
class CharactersPage(QWidget):
    refresh_requested = Signal()
    home_requested = Signal()
    remove_cached = Signal(int)   # avatar_id

    def __init__(self, loader, name_map):
        super().__init__()
        self.loader = loader; self.name_map = name_map
        self.characters = []
        self._current_ncard = None
        self._open_row_panel = None
        self._open_row_char_id = None
        self._top_panel_char_id = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        content = QWidget()
        content.setContentsMargins(24, 24, 24, 24)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 24, 24, 24); cl.setSpacing(18)

        # Katta profil banner — scroll ichida
        self.banner = ProfileBanner(loader, compact=True)
        cl.addWidget(self.banner)

        self.rank_title = QLabel("◆  Akasha Leaderboard")
        self.rank_title.setStyleSheet("color:#fff; font-size:14px; font-weight:bold; padding:4px 0;")
        cl.addWidget(self.rank_title)

        self.rank_container = QWidget()
        self.rank_flow = FlowLayout(self.rank_container, margin=0, spacing=10)
        cl.addWidget(self.rank_container)

        self.stats_panel = StatsPanel(loader, name_map)
        cl.addWidget(self.stats_panel)

        self.other_title = QLabel("◇  Other Characters")
        self.other_title.setStyleSheet("color:#fff; font-size:14px; font-weight:bold; padding:4px 0;")
        cl.addWidget(self.other_title)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0); self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignTop)
        cl.addWidget(self.list_container)
        cl.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # ===== Refresh tugma — floating (chap pastda) =====
        self.refresh_btn = QPushButton("↻  Refresh", self)
        self.refresh_btn.setFixedSize(120, 36)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet(
            "QPushButton { background:rgba(38,38,46,240); color:#fff;"
            " border:1px solid #3a3a44; border-radius:10px;"
            " font-size:11px; font-weight:bold; }"
            "QPushButton:hover { background:rgba(60,60,75,250); border-color:#7c5cff; }"
            "QPushButton:disabled { background:rgba(26,26,32,220); color:#5a5a6a; }")
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.refresh_btn.show()
        self.refresh_btn.raise_()

    def set_account(self, player, avatar_urls, ncard_urls=None):
        self._current_ncard = ncard_urls
        self.banner.set_data(player, avatar_urls, ncard_urls)

    def load(self, payload, akasha_ranks):
        self.characters = self._parse(payload)
        self._rebuild(akasha_ranks)

    def _parse(self, payload):
        nm = self.name_map
        out = []
        avatars = payload.get("avatarInfoList") or []
        if not avatars:
            avatars = (payload.get("detailInfo") or {}).get("avatarDetailList") or []
        for av in avatars:
            aid = av.get("avatarId")
            from_cache_ids = payload.get("_from_cache_ids") or []
            c = {
                "id": aid, "name": nm.char_name(aid),
                "from_cache": str(aid) in from_cache_ids,
                "icon_urls": nm.char_icon_urls(aid),
                "art_urls": nm.char_art_urls(aid),
                "own_namecard_urls": nm.namecard_for_char(aid),
                "element": nm.char_element(aid),
                "level": (av.get("propMap", {}).get("4001", {}) or {}).get("ival"),
                "constellation": len(av.get("talentIdList", []) or []),
                "weapon": {}, "artifact_sets": [], "stats": {}, "stats_short": [],
                "relics": [],
            }
            fp = av.get("fightPropMap", {}) or {}
            elem = nm.char_element(aid)

            # QAT'IY TARTIB
            ordered = []  # [(label, value_str)]

            # 1. Max HP
            if "2000" in fp and int(fp["2000"]) > 0:
                ordered.append(("Max HP", f"{int(fp['2000']):,}"))
            # 2. ATK
            if "2001" in fp and int(fp["2001"]) > 0:
                ordered.append(("ATK", f"{int(fp['2001']):,}"))
            # 3. DEF
            if "2002" in fp and int(fp["2002"]) > 0:
                ordered.append(("DEF", f"{int(fp['2002']):,}"))
            # 4. Elemental Mastery
            if "28" in fp and int(fp["28"]) > 0:
                ordered.append(("Elemental Mastery", f"{int(fp['28'])}"))
            # 5. Crit Rate
            if "20" in fp:
                pct = fp["20"] * 100
                if abs(pct) >= 0.05:
                    ordered.append(("Crit Rate", f"{pct:.1f}%"))
            # 6. Crit DMG
            if "22" in fp:
                pct = fp["22"] * 100
                if abs(pct) >= 0.05:
                    ordered.append(("Crit DMG", f"{pct:.1f}%"))
            # 7. Energy Recharge
            if "23" in fp:
                pct = fp["23"] * 100
                if abs(pct) >= 0.05:
                    ordered.append(("Energy Recharge", f"{pct:.1f}%"))
            # 8. Elemental DMG Bonus (elementga mos) yoki Physical
            elem_dmg_key = ELEMENT_TO_DMG.get(elem, "")
            dmg_label = None
            dmg_val = 0
            if elem_dmg_key and elem_dmg_key in fp:
                dmg_val = fp[elem_dmg_key] * 100
                dmg_label = f"{elem} DMG Bonus"
            elif "30" in fp and fp["30"] * 100 >= 0.05:
                # Physical DMG
                dmg_val = fp["30"] * 100
                dmg_label = "Physical DMG Bonus"
            if dmg_label and abs(dmg_val) >= 0.05:
                ordered.append((dmg_label, f"{dmg_val:.1f}%"))

            c["stats"] = dict(ordered)
            c["stats_ordered"] = ordered
            c["stats_short"] = [f"{k} {v}" for k, v in ordered[:3]]
            c["radar_values"] = calc_radar(c["stats"], c.get("element") or "")

            c["const_icon_urls"] = [nm.constellation_icon_urls(aid, i) for i in range(1, 7)]

            slm = av.get("skillLevelMap", {}) or {}
            entries = []
            for k, v in slm.items():
                try: entries.append((int(k), v))
                except: pass
            entries.sort()
            na = skill = burst = 0
            for sid, lvl in entries:
                last = sid % 10
                if last == 1 and na == 0: na = lvl
                elif last == 2 and skill == 0: skill = lvl
                elif last == 5 and burst == 0: burst = lvl
            if na == 0 and skill == 0 and burst == 0 and len(entries) >= 3:
                na = entries[0][1]; skill = entries[1][1]; burst = entries[2][1]
            c["talents"] = [
                {"type": "Attack", "level": na},
                {"type": "Skill",  "level": skill},
                {"type": "Burst",  "level": burst},
            ]

            sets = {}
            for eq in av.get("equipList", []) or []:
                flat = eq.get("flat", {}) or {}
                icon = flat.get("icon")
                icon_urls = nm.icon_urls(icon)
                et = flat.get("equipType", "")
                is_weapon = (et == "EQUIP_WEAPON" or flat.get("itemType") == "ITEM_WEAPON" or "weapon" in eq)
                if is_weapon:
                    w = eq.get("weapon", {}) or {}
                    aff = (w.get("affixMap") or {})
                    ref = (list(aff.values())[0] + 1) if aff else 1
                    wname = nm.loc_name(flat.get("nameTextMapHash"))
                    stars = flat.get("rankLevel", 0)
                    base_atk, sub_name, sub_val = parse_weapon_stats(flat)
                    c["weapon"] = {
                        "name": wname, "level": w.get("level", "?"),
                        "stars": stars, "refinement": ref,
                        "base_atk": base_atk,
                        "substat_name": sub_name, "substat_value": sub_val,
                        "icon_urls": icon_urls,
                    }
                    c["weapon_icon_urls"] = icon_urls
                else:
                    rel = parse_relic(eq, nm)
                    if rel: c["relics"].append(rel)
                    sh = flat.get("setNameTextMapHash")
                    set_id = flat.get("setId")
                    if sh:
                        if sh not in sets:
                            sname = nm.set_name_by_id(set_id) if set_id else "-"
                            sicon = f"UI_RelicIcon_{set_id}_4" if set_id else None
                            sicon_urls = nm.icon_urls(sicon) if sicon else []
                            sets[sh] = {"name": sname, "count": 0, "icon_urls": sicon_urls}
                        sets[sh]["count"] += 1
            c["artifact_sets"] = list(sets.values())
            order = ["EQUIP_BRACER", "EQUIP_NECKLACE", "EQUIP_SHOES", "EQUIP_RING", "EQUIP_DRESS"]
            c["relics"].sort(key=lambda x: order.index(x["slot"]) if x["slot"] in order else 99)
            out.append(c)
        return out

    def _clear(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget() if it else None
            if w:
                w.hide()          # avval yashiramiz
                w.setParent(None) # keyin parent uzamiz
                w.deleteLater()   # va o'chiramiz

    def _rebuild(self, ranks):
        try:
            self._rebuild_impl(ranks)
        except Exception as e:
            import traceback
            print(f"[Rebuild] XATO: {e}")
            traceback.print_exc()

    def _rebuild_impl(self, ranks):
        # Avval panellarni yopamiz
        self._close_row_panel()
        self.stats_panel.hide_panel()
        self._clear(self.rank_flow)
        self._clear(self.list_layout)
        self._top_panel_char_id = None

        ranked, unranked = [], []
        for c in self.characters:
            cid = str(c.get("id"))
            r = ranks.get(cid) if ranks else None
            if r and r.get("top") and r.get("total"):
                c["is_ranked"] = True
                c["rank"] = r
                ranked.append((c, r))
            else:
                c["is_ranked"] = False
                unranked.append(c)

        print(f"[Rebuild] chars={len(self.characters)}, ranks={len(ranks)}, "
              f"ranked={len(ranked)}, unranked={len(unranked)}")
        if self.characters and ranks:
            print(f"[Rebuild] sample rank keys: {sorted(ranks.keys())[:5]}")
            print(f"[Rebuild] sample char ids: {[str(c['id']) for c in self.characters[:5]]}")
            for c in self.characters[:3]:
                cid = str(c.get('id'))
                r = ranks.get(cid)
                print(f"[Rebuild]   char {cid}: rank={'YES' if r else 'NO'}")
                if r:
                    print(f"[Rebuild]     top={r.get('top')}, total={r.get('total')}")

        # Ranked cards
        if not ranked:
            ph = QLabel("No Akasha ranking data available yet.")
            ph.setStyleSheet("color:#6a6a7a; padding:30px; font-size:12px;")
            self.rank_flow.addWidget(ph)
        for c, r in ranked:
            card = RankedCard(c, r, self.loader)
            card.clicked.connect(self._toggle_top)
            self.rank_flow.addWidget(card)

        # Unranked rows
        for c in unranked:
            row = CharacterRow(c, self.loader)
            row.clicked.connect(lambda ch, r=row: self._toggle_row(ch, r))
            self.list_layout.addWidget(row)

        print(f"[Rebuild] flow_count={self.rank_flow.count()}, "
              f"list_count={self.list_layout.count()}")

        # Layout'ni majburiy yangilash
        self.rank_container.updateGeometry()
        self.rank_container.update()
        if self.rank_container.parent():
            self.rank_container.parent().updateGeometry()
        self.rank_flow.invalidate()
        self.rank_flow.update()


    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "refresh_btn") and self.refresh_btn:
            # Chap pastki burchak, 20px margin
            self.refresh_btn.move(20, self.height() - self.refresh_btn.height() - 20)
            self.refresh_btn.raise_()

    def _on_refresh(self):
        print("[Refresh] clicked")
        self.refresh_requested.emit()

    def set_refreshing(self, on):
        if on:
            self.refresh_btn.setText("↻  Loading…")
            self.refresh_btn.setEnabled(False)
        else:
            self.refresh_btn.setText("↻  Refresh")
            self.refresh_btn.setEnabled(True)

    def _toggle_top(self, char):
        print(f"[Toggle] _toggle_top: {char.get('name')}")
        if self.stats_panel.isVisible() and self._top_panel_char_id == char.get("id"):
            self.stats_panel.hide_panel()
            self._top_panel_char_id = None
        else:
            self.stats_panel.show_for(char, self._current_ncard)
            self._top_panel_char_id = char.get("id")
        self._close_row_panel()

    def _toggle_row(self, char, row_widget):
        self.stats_panel.hide_panel()
        self._top_panel_char_id = None
        same = (self._open_row_char_id == char.get("id"))
        self._close_row_panel()
        if same: return
        panel = StatsPanel(self.loader, self.name_map)
        panel.show_for(char, self._current_ncard)
        idx = self.list_layout.indexOf(row_widget)
        if idx >= 0:
            self.list_layout.insertWidget(idx + 1, panel)
            self._open_row_panel = panel
            self._open_row_char_id = char.get("id")

    def get_open_panel_id(self):
        """Hozir ochiq panelning char_id sini qaytaradi (yoki None)."""
        if self._top_panel_char_id is not None:
            return self._top_panel_char_id
        if self._open_row_char_id is not None:
            return self._open_row_char_id
        return None

    def reopen_panel_by_id(self, char_id):
        """Berilgan char_id uchun panelni qayta ochadi."""
        if char_id is None:
            return
        for c in self.characters:
            if c.get("id") == char_id:
                self._toggle_top(c)
                return

    def _close_row_panel(self):
        if self._open_row_panel is not None:
            try:
                self.list_layout.removeWidget(self._open_row_panel)
                self._open_row_panel.hide()
                self._open_row_panel.setParent(None)
                self._open_row_panel.deleteLater()
            except RuntimeError:
                pass
            self._open_row_panel = None
            self._open_row_char_id = None
