from pathlib import Path
from urllib.request import Request, urlopen
import sys
import json
import webbrowser
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame
)
from src.constants import APP_NAME, APP_VERSION, namecard_urls as nc_urls
from src.image_loader import ImageLoader
from src.namemap import NameMap
from src.api_enka import EnkaClient
from src.api_akasha import AkashaClient
from src.pages import HomePage, CharactersPage


class AccountTab(QFrame):
    clicked = Signal(str)
    closed = Signal(str)

    def __init__(self, uid, nickname, avatar_urls, loader, is_active=False):
        super().__init__()
        self.uid = uid
        self._active = is_active
        self._loader = loader
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(8)

        self.avatar = QLabel()
        self.avatar.setFixedSize(26, 26)
        self.avatar.setStyleSheet("background:transparent;")
        lay.addWidget(self.avatar)

        self.name_lbl = QLabel(nickname)
        self.name_lbl.setStyleSheet(
            "color:#fff; font-size:11px; font-weight:bold; background:transparent;")
        lay.addWidget(self.name_lbl)

        self.x_btn = QPushButton("✕")
        self.x_btn.setFixedSize(18, 18)
        self.x_btn.setCursor(Qt.PointingHandCursor)
        self.x_btn.setStyleSheet(
            "QPushButton { background:transparent; color:#9090a0; "
            "border:none; font-weight:bold; font-size:10px; padding:0; }"
            "QPushButton:hover { color:#ff6b6b; }")
        self.x_btn.clicked.connect(lambda: self.closed.emit(self.uid))
        lay.addWidget(self.x_btn)

        if avatar_urls:
            loader.load(avatar_urls, self._set_avatar)

    def set_active(self, active):
        self._active = active
        self.update()

    def _set_avatar(self, pm):
        if pm:
            s = self.avatar.width()
            self.avatar.setPixmap(pm.scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath(); path.addRoundedRect(r, 8, 8)
        p.setClipPath(path)
        if self._active:
            p.fillRect(r, QColor(124, 92, 255, 100))
        else:
            p.fillRect(r, QColor(26, 26, 36, 220))
        p.setClipping(False)
        pen = QPen(QColor(124, 92, 255) if self._active else QColor(60, 60, 75),
                   2 if self._active else 1)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -2, -2), 8, 8)
        super().paintEvent(e)

    def mousePressEvent(self, e):
        if not self.x_btn.geometry().contains(e.position().toPoint()):
            self.clicked.emit(self.uid)
        super().mousePressEvent(e)


class TabBar(QWidget):
    home_clicked = Signal()
    account_clicked = Signal(str)
    account_closed = Signal(str)

    def __init__(self, loader):
        super().__init__()
        self.loader = loader
        self.setFixedHeight(48)
        self.setStyleSheet("background:#0a0a12;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(6)

        self.home_btn = QPushButton("⌂  Home")
        self.home_btn.setFixedHeight(36)
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setStyleSheet(
            "QPushButton { background:#1a1a24; color:#fff; border:1px solid #2a2a3a;"
            " border-radius:8px; padding:0 14px; font-size:11px; font-weight:bold; }"
            "QPushButton:hover { background:#26262e; border-color:#7c5cff; }")
        self.home_btn.clicked.connect(self.home_clicked.emit)
        lay.addWidget(self.home_btn)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background:#2a2a3a;")
        sep.setFixedHeight(24)
        lay.addWidget(sep)

        self.tabs_layout = QHBoxLayout()
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(6)
        lay.addLayout(self.tabs_layout)
        lay.addStretch()

        self._tabs = {}
        self._active_uid = None

    def set_accounts(self, accounts, active_uid=None):
        while self.tabs_layout.count():
            it = self.tabs_layout.takeAt(0)
            w = it.widget() if it else None
            if w: w.setParent(None)
        self._tabs.clear()
        self._active_uid = active_uid

        for acc in accounts:
            tab = AccountTab(
                acc["uid"], acc["player"].get("nickname", "?"),
                acc.get("avatar_urls"), self.loader,
                is_active=(acc["uid"] == active_uid)
            )
            tab.clicked.connect(self.account_clicked.emit)
            tab.closed.connect(self.account_closed.emit)
            self.tabs_layout.addWidget(tab)
            self._tabs[acc["uid"]] = tab

    def set_active(self, uid):
        self._active_uid = uid
        for k, tab in self._tabs.items():
            tab.set_active(k == uid)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(800, 500)
        self.resize(1280, 780)
        self.setStyleSheet("""
            QWidget { background:#0d0d14; color:#e0e0e8; }
            QLabel { color:#e0e0e8; }
            QLineEdit {
                background:#1a1a24; color:#fff; border:1px solid #26263a;
                border-radius:10px; padding:10px 14px; font-size:13px;
            }
            QLineEdit:focus { border:1px solid #7c5cff; }
            QScrollBar:vertical { background:transparent; width:8px; }
            QScrollBar::handle:vertical { background:#2a2a3a; border-radius:4px; min-height:30px; }
            QScrollBar::handle:vertical:hover { background:#3a3a52; }
            QScrollBar::add-line, QScrollBar::sub-line { height:0; }
        """)

        self.loader = ImageLoader(self)
        self.name_map = NameMap(self.loader, self)
        self.name_map.ready.connect(self._on_ready)

        self.enka = EnkaClient(self)
        self.enka.success.connect(self._on_ok)
        self.enka.failure.connect(self._on_fail)

        self.akasha = AkashaClient(self)
        self.akasha.debug.connect(lambda s: print(f"[Akasha] {s}"))
        self.akasha.ranks_ready.connect(self._on_ranks)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        self.tabbar = TabBar(self.loader)
        self.tabbar.home_clicked.connect(self._go_home)
        self.tabbar.account_clicked.connect(self._open_account)
        self.tabbar.account_closed.connect(self._close_account)
        root.addWidget(self.tabbar)

        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)

        self.home = HomePage(self.loader)
        self.home.submit.connect(self._submit)
        self.home.open_profile.connect(self._open_chars)

        self.chars = CharactersPage(self.loader, self.name_map)
        self.chars.refresh_requested.connect(self._on_refresh)
        self.chars.remove_cached.connect(self._on_remove_cached)

        self.pages.addWidget(self.home)
        self.pages.addWidget(self.chars)

        self._pending_uid = None
        self._last_payload = None
        self._last_ranks = {}
        self._current_uid = None
        self.saved_accounts = []
        self._refresh_pending = False
        self._refresh_open_panel_id = None

        # Saqlangan akkauntlarni yuklaymiz
        self._load_accounts()

    def _on_ready(self):
        print("[Main] NameMap ready")
        if self._pending_uid:
            uid = self._pending_uid; self._pending_uid = None
            self._submit(uid)

    def _submit(self, uid):
        if not self.name_map.is_ready():
            self._pending_uid = uid
            self.home.set_error("Loading database… please wait")
            return
        self.home.set_loading(True)
        self.home.set_error("Loading…")
        self.enka.fetch(uid, "Genshin Impact")

    def _on_fail(self, msg):
        print(f"[Main] _on_fail: {msg}")
        self.home.set_loading(False)
        self.home.set_error(msg)
        if self._refresh_pending:
            self._refresh_pending = False
            self.chars.set_refreshing(False)

    def _get_profile_avatar_id(self, player):
        pp = player.get("profilePicture") or {}
        if isinstance(pp, dict):
            for key in ("avatarId", "avatar_id", "id", "avatarID"):
                v = pp.get(key)
                if v:
                    if isinstance(v, int) and 10000000 < v < 20000000:
                        return v
                    if isinstance(v, int) and v < 10000000:
                        break
        show_list = player.get("showAvatarInfoList") or []
        if show_list and isinstance(show_list, list):
            first = show_list[0]
            if isinstance(first, dict):
                aid = first.get("avatarId")
                if aid: return aid
        return None

    def _chars_cache_file(self, uid):
        return self._config_dir() / f"uid_{uid}_chars.json"

    def _merge_payload_with_cache(self, uid, payload):
        """Yangi Enka payload'ni eski kesh bilan birlashtiradi.
        Akkauntdan olib qo'yilgan personajlar saqlanib qoladi."""
        new_avatars = payload.get("avatarInfoList") or []
        if not new_avatars:
            new_avatars = (payload.get("detailInfo") or {}).get("avatarDetailList") or []

        # Eski keshlangan personajlar
        old_chars = {}
        cache_file = self._chars_cache_file(uid)
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                for ch in data.get("avatarInfoList", []):
                    aid = ch.get("avatarId")
                    if aid:
                        old_chars[str(aid)] = ch
            except Exception as e:
                print(f"[Cache] o'qishda xato: {e}")

        # Yangi personajlarni qo'shamiz / yangilaymiz
        new_ids = set()
        for av in new_avatars:
            aid = av.get("avatarId")
            if aid:
                new_ids.add(str(aid))
                old_chars[str(aid)] = av

        # Keshdagi personajlar — agar yangi payload'da yo'q bo'lsa, saqlanadi
        removed = [aid for aid in old_chars if aid not in new_ids]
        if removed:
            print(f"[Cache] {len(removed)} personaj akkauntdan yo'q, lekin keshdan saqlanadi")

        # Birlashtirilgan ro'yxat
        merged = list(old_chars.values())
        payload["avatarInfoList"] = merged
        payload["_from_cache_ids"] = removed    # qaysi birlari keshdan

        # Keshga saqlaymiz
        try:
            cache_file.write_text(json.dumps(
                {"avatarInfoList": merged, "lastUpdate": __import__("time").time()},
                ensure_ascii=False))
            print(f"[Cache] {len(merged)} personaj saqlandi ({len(removed)} keshdan)")
        except Exception as e:
            print(f"[Cache] saqlashda xato: {e}")

        return payload

    def _on_ok(self, payload, uid):
        print(f"[Main] _on_ok CALLED for uid={uid}")
        print(f"[Main]   _refresh_pending={self._refresh_pending}, _last_ranks={len(self._last_ranks)}")
        self.home.set_loading(False)
        self._current_uid = uid
        player = payload.get("playerInfo") or {}
        player["uid"] = uid

        # Kesh bilan birlashtiramiz
        payload = self._merge_payload_with_cache(uid, payload)

        self._last_payload = payload

        aid = self._get_profile_avatar_id(player)
        avatar_urls = self.name_map.char_icon_urls(aid) if aid else None

        nc_id = player.get("nameCardId")
        if not nc_id:
            ncard = player.get("nameCard") or {}
            if isinstance(ncard, dict):
                nc_id = ncard.get("id") or ncard.get("nameCardId")
        ncards = None
        if nc_id:
            icon_name = self.name_map.namecard_icon(nc_id)
            if icon_name:
                ncards = [
                    f"https://enka.network/ui/{icon_name}.png",
                    f"https://enka.network/ui/{icon_name}.jpg",
                    f"https://gi.yatta.moe/assets/UI/{icon_name}.png",
                ]
            else:
                ncards = nc_urls(nc_id)

        # Saqlangan ro'yxatga qo'shamiz
        self.saved_accounts = [a for a in self.saved_accounts if a["uid"] != uid]
        self.saved_accounts.insert(0, {
            "uid": uid, "player": dict(player),
            "avatar_urls": avatar_urls, "namecard_urls": ncards,
            "payload": payload,
        })
        self.tabbar.set_accounts(self.saved_accounts, active_uid=uid)

        self.home.show_profile(player, avatar_urls, ncards)
        self.chars.set_account(player, avatar_urls, ncards)
        # Eski ranks bilan yuklaymiz (refresh paytida ranked yo'qolmasin)
        self.chars.load(payload, self._last_ranks)

        # Akkauntlarni saqlaymiz
        self._save_accounts()

        # Refresh tugmasi holatini tiklash (fallback)
        if self._refresh_pending:
            print("[Main] resetting refresh button (fallback)")
            self._refresh_pending = False
            self.chars.set_refreshing(False)

        # Akasha so'rovi
        print(f"[Main] calling akasha.fetch_ranks({uid})")
        self.akasha.fetch_ranks(uid)

    def _on_ranks(self, ranks):
        print(f"[Main] _on_ranks CALLED: {len(ranks)} ranks")
        print(f"[Main]   _refresh_pending={self._refresh_pending}")
        self._last_ranks = ranks
        if self._last_payload is not None:
            self.chars.load(self._last_payload, ranks)
        # Agar refresh paytida panel ochiq bo'lsa, qayta ochamiz
        if self._refresh_pending:
            self._refresh_pending = False
            self.chars.set_refreshing(False)
            panel_id = getattr(self, '_refresh_open_panel_id', None)
            if panel_id is not None:
                # Kichik kechikish — layout joylashishi uchun
                QTimer.singleShot(50, lambda pid=panel_id: self.chars.reopen_panel_by_id(pid))
                self._refresh_open_panel_id = None

    def _on_remove_cached(self, avatar_id):
        """Keshdan personajni o'chiradi."""
        if not self._current_uid:
            return
        print(f"[Cache] O'chirish: {avatar_id} (uid {self._current_uid})")
        cache_file = self._chars_cache_file(self._current_uid)
        if not cache_file.exists():
            return
        try:
            data = json.loads(cache_file.read_text())
            chars = data.get("avatarInfoList", [])
            new_chars = [c for c in chars if str(c.get("avatarId")) != str(avatar_id)]
            data["avatarInfoList"] = new_chars
            cache_file.write_text(json.dumps(data, ensure_ascii=False))
            print(f"[Cache] {len(chars) - len(new_chars)} o'chirildi, {len(new_chars)} qoldi")

            # Panelni ham yangilaymiz
            if self._last_payload is not None:
                # _from_cache_ids dan ham olib tashlaymiz
                from_cache = self._last_payload.get("_from_cache_ids") or []
                from_cache = [x for x in from_cache if str(x) != str(avatar_id)]
                self._last_payload["_from_cache_ids"] = from_cache
                # _last_payload dan ham olib tashlaymiz
                avatars = self._last_payload.get("avatarInfoList") or []
                self._last_payload["avatarInfoList"] = [
                    a for a in avatars if str(a.get("avatarId")) != str(avatar_id)
                ]
                self.chars.load(self._last_payload, self._last_ranks)
        except Exception as e:
            print(f"[Cache] Xato: {e}")

    def _on_refresh(self):
        """Refresh: Enka'ga fon so'rov, keyin Akasha API."""
        print("[Main] Refresh clicked")
        if not self._current_uid:
            return
        uid = self._current_uid
        self._refresh_open_panel_id = self.chars.get_open_panel_id()
        self.chars.set_refreshing(True)
        self._refresh_pending = True

        # 1) Enka'ga fon so'rov (brauzersiz)
        QTimer.singleShot(100, lambda u=uid: self._trigger_enka(u))

        # 2) 5 sekunddan keyin API dan qayta so'raymiz
        QTimer.singleShot(5000, lambda u=uid: self._do_api_refresh(u))

        # 3) 30 sekund safety timeout
        QTimer.singleShot(30000, lambda u=uid: self._refresh_timeout(u))

    def _trigger_enka(self, uid):
        """Enka veb-saytiga fon so'rov (brauzer ochmasdan)."""
        if uid != self._current_uid:
            return
        url = f"https://enka.network/u/{uid}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        print(f"[Main] Triggering Enka refresh: {url}")
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=10) as resp:
                print(f"[Main] Enka trigger: HTTP {resp.status}")
        except Exception as e:
            print(f"[Main] Enka trigger fail: {e}")

    def _do_api_refresh(self, uid):
        if uid != self._current_uid:
            return
        print("[Main] Fetching fresh data from Enka API")
        self.enka.fetch(uid, "Genshin Impact")

    def _open_akasha(self, uid):
        if uid != self._current_uid:
            return
        akasha_url = f"https://akasha.cv/profile/{uid}"
        print(f"[Main] Opening {akasha_url}")
        try:
            webbrowser.open(akasha_url)
        except Exception as e:
            print(f"[Main] webbrowser fail: {e}")

    def _do_api_refresh(self, uid):
        if uid != self._current_uid:
            return
        print("[Main] Fetching fresh data from Enka API")
        self.enka.fetch(uid, "Genshin Impact")

    def _refresh_timeout(self, uid):
        if self._refresh_pending and uid == self._current_uid:
            print(f"[Main] Refresh timeout for {uid}")
            self._refresh_pending = False
            self.chars.set_refreshing(False)

    def _go_home(self):
        self._current_uid = None
        self.tabbar.set_active(None)
        self.home.show_input()
        self.pages.setCurrentWidget(self.home)

    def _open_account(self, uid):
        for acc in self.saved_accounts:
            if acc["uid"] == uid:
                self._current_uid = uid
                self.tabbar.set_active(uid)
                self.home.show_profile(acc["player"], acc["avatar_urls"], acc["namecard_urls"])
                self.chars.set_account(acc["player"], acc["avatar_urls"], acc["namecard_urls"])

                if acc.get("payload"):
                    # Saqlangan ma'lumot bor
                    self.chars.load(acc["payload"], self._last_ranks)
                    self.pages.setCurrentWidget(self.home)
                else:
                    # Payload yo'q — API dan qayta yuklaymiz
                    print(f"[Open] payload yo'q, API dan yuklaymiz: {uid}")
                    self.home.set_loading(True)
                    self.enka.fetch(uid, "Genshin Impact")
                return

    def _open_chars(self):
        self.pages.setCurrentWidget(self.chars)

    def _close_account(self, uid):
        self.saved_accounts = [a for a in self.saved_accounts if a["uid"] != uid]
        self.tabbar.set_accounts(self.saved_accounts, active_uid=self._current_uid)
        self._save_accounts()
        if uid == self._current_uid:
            self._go_home()

    # ============ Saqlash / Yuklash ============
    def _config_dir(self):
        d = Path.home() / ".config" / "asadbeks-ranking-system"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _accounts_file(self):
        return self._config_dir() / "accounts.json"

    def _save_accounts(self):
        """Saqlangan akkauntlar ro'yxatini JSON faylga yozamiz."""
        print(f"[Save] CALLED, accounts={len(self.saved_accounts)}")
        data = []
        for acc in self.saved_accounts:
            player = acc.get("player") or {}
            # Faqat kichik ma'lumotlar — payload (katta) saqlanmaydi
            data.append({
                "uid": acc["uid"],
                "player": {
                    "nickname": player.get("nickname"),
                    "level": player.get("level"),
                    "worldLevel": player.get("worldLevel"),
                    "signature": player.get("signature"),
                    "region": player.get("region"),
                    "uid": player.get("uid"),
                },
                "avatar_urls": acc.get("avatar_urls"),
                "namecard_urls": acc.get("namecard_urls"),
            })
        try:
            self._accounts_file().write_text(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            print(f"[Save] {len(data)} akkaunt saqlandi")
        except Exception as e:
            print(f"[Save] XATO: {e}")

    def _load_accounts(self):
        """Saqlangan akkauntlarni yuklaymiz."""
        print("[Load] CALLED")
        f = self._accounts_file()
        if not f.exists():
            print("[Load] saqlangan fayl yo'q")
            return
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"[Load] XATO: {e}")
            return
        for item in data:
            uid = item.get("uid")
            if not uid:
                continue
            self.saved_accounts.append({
                "uid": uid,
                "player": item.get("player") or {},
                "avatar_urls": item.get("avatar_urls"),
                "namecard_urls": item.get("namecard_urls"),
                "payload": None,   # payload kerak bo'lganda API dan olamiz
            })
        if self.saved_accounts:
            self.tabbar.set_accounts(self.saved_accounts, active_uid=None)
            print(f"[Load] {len(self.saved_accounts)} akkaunt yuklandi")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    # Taskbar/dock ikonkasi uchun — .desktop fayl nomi bilan bir xil
    app.setDesktopFileName("asadbeks-ranking-system")
    # Wayland uchun app_id
    app.setOrganizationName("Asadbek")
    app.setOrganizationDomain("asadbek.cv")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
