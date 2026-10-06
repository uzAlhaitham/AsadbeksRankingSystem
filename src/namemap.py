import json, time
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer, QUrl
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply
from .constants import (
    USER_AGENT, AVATARS_SOURCES, LOCS_SOURCES, ui_urls,
    avatar_icon_urls, avatar_art_urls
)

CACHE = Path.home() / ".cache" / "asadbeks-ranking-system"
CACHE.mkdir(parents=True, exist_ok=True)
AV = CACHE / "avatars.json"
LC = CACHE / "locs.json"
TM = CACHE / "textmap_en.json"
NC = CACHE / "namecards.json"
MAX_AGE = 7 * 24 * 3600

TEXTMAP_SOURCES = [
    "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/master/TextMap/TextMapEN.json",
    "https://gitlab.com/Dimbreath/AnimeGameData/-/raw/master/TextMap/TextMapEN.json",
]
NAMECARDS_SOURCES = [
    "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/gi/namecards.json",
    "https://cdn.jsdelivr.net/gh/EnkaNetwork/API-docs@master/store/gi/namecards.json",
]

# Statik artefakt setId -> nom (GitHub API cheklovsiz)
ARTIFACT_SETS = {
    15001: "Gladiator's Finale",
    15002: "Wanderer's Troupe",
    15003: "Noblesse Oblige",
    15005: "Maiden Beloved",
    15007: "Viridescent Venerer",
    15009: "Crimson Witch of Flames",
    15011: "Blizzard Strayer",
    15013: "Thundersoother",
    15014: "Thundering Fury",
    15015: "Lavawalker",
    15016: "Heart of Depth",
    15017: "Tenacity of the Millelith",
    15018: "Pale Flame",
    15019: "Shimenawa's Reminiscence",
    15020: "Emblem of Severed Fate",
    15021: "Husk of Opulent Dreams",
    15022: "Ocean-Hued Clam",
    15023: "Vermillion Hereafter",
    15024: "Echoes of an Offering",
    15025: "Deepwood Memories",
    15026: "Gilded Dreams",
    15027: "Desert Pavilion Chronicle",
    15028: "Flower of Paradise Lost",
    15029: "Nymph's Dream",
    15030: "Vourukasha's Glow",
    15031: "Marechaussee Hunter",
    15032: "Golden Troupe",
    15033: "Song of Days Past",
    15034: "Nighttime Whispers in the Echoing Woods",
    15035: "Fragment of Harmonic Whimsy",
    15036: "Unfinished Reverie",
    15037: "Scroll of the Hero of Cinder City",
    15038: "Obsidian Codex",
    15039: "Long Night's Oath",
    15040: "Finale of the Deep Galleries",
    15041: "Silken Moon's Serenade",
    15042: "Unfinished Reverie",  # alt id
    15043: "Fragment of Harmonic Whimsy",  # alt
    15044: "Obsidian Codex",  # alt
    15045: "Scroll of the Hero of Cinder City",  # alt
    15046: "Long Night's Oath",  # alt
    15047: "Finale of the Deep Galleries",  # alt
    15048: "Silken Moon's Serenade",  # alt
    14001: "Resolution of Sojourner",
    14002: "Brave Heart",
    14003: "Defender's Will",
    14004: "Tiny Miracle",
    14005: "Berserker",
    14006: "Martial Artist",
    14007: "Instructor",
    14008: "Gambler",
    14009: "The Exile",
    14010: "Adventurer",
    14011: "Lucky Dog",
    14012: "Scholar",
    14013: "Traveling Doctor",
}


class NameMap(QObject):
    ready = Signal()
    artifacts_ready = Signal()  # mosligi uchun qoldirildi

    def __init__(self, loader, parent=None):
        super().__init__(parent)
        self.nam = loader.nam
        self.avatars = {}
        self.loc = {}
        self.textmap = {}
        self.namecards = {}
        self.artifacts = {str(k): v for k, v in ARTIFACT_SETS.items()}
        self._av_ok = False
        self._lc_ok = False
        self._tm_ok = False
        self._nc_ok = False
        self._ar_ok = True
        self._emitted = False

        self._load_cache()
        need_av = self._needs(AV, self._av_ok)
        need_lc = self._needs(LC, self._lc_ok)
        need_tm = self._needs(TM, self._tm_ok)
        need_nc = self._needs(NC, self._nc_ok)

        if need_av: self._try_avatars(0)
        if need_lc: self._try_locs(0)
        if need_tm: self._try_textmap(0)
        if need_nc: self._try_namecards(0)

        if not (need_av or need_lc or need_tm or need_nc):
            QTimer.singleShot(0, self._emit_ready)

    def _needs(self, path, ok):
        if not path.exists(): return True
        if not ok: return True
        if time.time() - path.stat().st_mtime > MAX_AGE: return True
        return False

    def _load_cache(self):
        for path, attr, flag in ((AV, "avatars", "_av_ok"), (LC, "loc", "_lc_ok"),
                                  (TM, "textmap", "_tm_ok"), (NC, "namecards", "_nc_ok")):
            if path.exists():
                try:
                    d = json.loads(path.read_text())
                    if d:
                        setattr(self, attr, d)
                        setattr(self, flag, True)
                except Exception: pass

    def _emit_ready(self):
        if self._emitted: return
        self._emitted = True
        print(f"[NameMap] READY av={self._av_ok} lc={self._lc_ok} tm={self._tm_ok}")
        self.ready.emit()

    def is_ready(self):
        return self._av_ok and (self._lc_ok or self._tm_ok)

    def _check(self):
        if self.is_ready(): self._emit_ready()

    def _try_namecards(self, idx):
        if idx >= len(NAMECARDS_SOURCES):
            self._nc_ok = True
            return
        req = QNetworkRequest(QUrl(NAMECARDS_SOURCES[idx]))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        r = self.nam.get(req)
        r.finished.connect(lambda rr=r, i=idx: self._on_namecards(i, rr))

    def _on_namecards(self, idx, reply):
        err = reply.error(); http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll()); reply.deleteLater()
        if err != QNetworkReply.NetworkError.NoError or (http and http >= 400):
            self._try_namecards(idx+1); return
        try:
            obj = json.loads(data.decode())
            if not obj: raise ValueError()
        except Exception:
            self._try_namecards(idx+1); return
        self.namecards = obj
        self._nc_ok = True
        NC.write_bytes(data)
        print(f"[NameMap] namecards OK: {len(obj)}")

    def namecard_icon(self, nc_id):
        """namecardId -> icon nomi (masalan UI_NameCardPic_Navia_P)."""
        if not nc_id: return None
        info = self.namecards.get(str(nc_id))
        if not info: return None
        raw = None
        if isinstance(info, dict):
            raw = info.get("Icon") or info.get("icon")
        elif isinstance(info, str):
            raw = info
        if not raw: return None
        name = raw.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return name

    def namecard_urls_from_icon(self, icon_name):
        """Icon nomidan URL ro'yxati."""
        if not icon_name: return []
        return [
            f"https://enka.network/ui/{icon_name}.png",
            f"https://enka.network/ui/{icon_name}.jpg",
            f"https://gi.yatta.moe/assets/UI/{icon_name}.png",
        ]

    def namecard_for_char(self, aid):
        """Personajning O'Z namecard rasmi URL larini qaytaradi.
        Avval namecards.json dan qidiradi, keyin URL yasaydi."""
        icon = self._get_icon_name(aid)
        if not icon:
            print(f"[NameCard] aid={aid} no icon")
            return []
        short = icon.replace("UI_AvatarIcon_Side_", "").replace("UI_AvatarIcon_", "")
        # Genshin typo lar va maxsus holatlar
        aliases = {
            "Alhaitham": ["Alhaitham", "Alhatham"],
            "Shougun":   ["Shougun", "RaidenShogun"],
            "Kokomi":    ["Kokomi", "SangonomiyaKokomi"],
            "Ayaka":     ["Ayaka", "KamisatoAyaka"],
            "Ayato":     ["Ayato", "KamisatoAyato"],
            "Kazuha":    ["Kazuha", "KaedeharaKazuha"],
            "Itto":      ["Itto", "AratakiItto"],
            "Heizou":    ["Heizou", "ShikanoinHeizou"],
            "Shinobu":   ["Shinobu", "KukiShinobu"],
            "Miko":      ["Miko", "YaeMiko"],
            "Wanderer":  ["Wanderer", "HatGuy"],
            "Tartaglia": ["Tartaglia", "Childe"],
            "Nahida":    ["Nahida", "LesserLordKusanali"],
            "Yumemizuki": ["Yumemizuki", "Mizuki"],
        }
        candidates = list(aliases.get(short, [short]))

        # 1) namecards.json dan aniq qidirish
        for cand in candidates:
            want = f"UI_NameCardPic_{cand}_P"
            for nc_id, info in self.namecards.items():
                if not isinstance(info, dict): continue
                ic = info.get("Icon") or ""
                fname = ic.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                if fname == want:
                    print(f"[NameCard] aid={aid} found in json: {fname}")
                    return self.namecard_urls_from_icon(fname)

        # 2) JSON da topilmadi — to'g'ridan-to'g'ri URL yasash
        print(f"[NameCard] aid={aid} not in json, trying: {candidates}")
        urls = []
        for cand in candidates:
            urls += self.namecard_urls_from_icon(f"UI_NameCardPic_{cand}_P")
        return urls

    def _try_avatars(self, idx):
        if idx >= len(AVATARS_SOURCES): return
        req = QNetworkRequest(QUrl(AVATARS_SOURCES[idx]))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        r = self.nam.get(req)
        r.finished.connect(lambda rr=r, i=idx: self._on_avatars(i, rr))

    def _on_avatars(self, idx, reply):
        err = reply.error(); http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll()); reply.deleteLater()
        if err != QNetworkReply.NetworkError.NoError or (http and http >= 400):
            self._try_avatars(idx+1); return
        try:
            obj = json.loads(data.decode())
            if not obj: raise ValueError()
        except Exception:
            self._try_avatars(idx+1); return
        self.avatars = obj; self._av_ok = True; AV.write_bytes(data)
        print(f"[NameMap] avatars OK: {len(obj)}"); self._check()

    def _try_locs(self, idx):
        if idx >= len(LOCS_SOURCES): return
        req = QNetworkRequest(QUrl(LOCS_SOURCES[idx]))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        r = self.nam.get(req)
        r.finished.connect(lambda rr=r, i=idx: self._on_locs(i, rr))

    def _on_locs(self, idx, reply):
        err = reply.error(); http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll()); reply.deleteLater()
        if err != QNetworkReply.NetworkError.NoError or (http and http >= 400):
            self._try_locs(idx+1); return
        try:
            obj = json.loads(data.decode())
            if not obj: raise ValueError()
        except Exception:
            self._try_locs(idx+1); return
        self.loc = obj; self._lc_ok = True; LC.write_bytes(data)
        print("[NameMap] locs OK"); self._check()

    def _try_textmap(self, idx):
        if idx >= len(TEXTMAP_SOURCES): return
        req = QNetworkRequest(QUrl(TEXTMAP_SOURCES[idx]))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        r = self.nam.get(req)
        r.finished.connect(lambda rr=r, i=idx: self._on_textmap(i, rr))

    def _on_textmap(self, idx, reply):
        err = reply.error(); http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll()); reply.deleteLater()
        print(f"[NameMap] textmap #{idx+1}: HTTP {http} {len(data)} bytes")
        if err != QNetworkReply.NetworkError.NoError or (http and http >= 400):
            self._try_textmap(idx+1); return
        try:
            obj = json.loads(data.decode())
            if not obj: raise ValueError()
        except Exception as e:
            print(f"[NameMap] textmap parse FAIL: {e}")
            self._try_textmap(idx+1); return
        self.textmap = obj; self._tm_ok = True; TM.write_bytes(data)
        print(f"[NameMap] textmap OK: {len(obj)}"); self._check()

    def _lookup(self, h):
        if h is None or h == "": return None
        h = str(h)
        if isinstance(self.textmap, dict):
            v = self.textmap.get(h)
            if isinstance(v, str) and v: return v
        en = self.loc.get("en") if isinstance(self.loc, dict) else None
        if isinstance(en, dict):
            v = en.get(h)
            if isinstance(v, str) and v: return v
        old = self.loc.get(h) if isinstance(self.loc, dict) else None
        if isinstance(old, dict):
            for k in ("en","EN","English"):
                if old.get(k): return old[k]
        if isinstance(old, str) and old: return old
        return None

    def char_name(self, aid):
        info = self.avatars.get(str(aid))
        if not info: return f"#{aid}"
        return self._lookup(info.get("NameTextMapHash")) or f"#{aid}"

    def loc_name(self, h): return self._lookup(h) or "-"

    def set_name_by_id(self, set_id):
        if set_id is None: return "-"
        return self.artifacts.get(str(set_id), "-")

    def icon_urls(self, name): return ui_urls(name)

    # ============ AVATAR ICON (SideIconName dan) ============
    def _normalize_icon(self, raw):
        """Har xil formatni UI_AvatarIcon_X ga aylantiradi.
        Misol:
          '/ui/Mavuika.png'                    -> 'UI_AvatarIcon_Mavuika'
          '/ui/UI_AvatarIcon_Side_Mavuika.png' -> 'UI_AvatarIcon_Mavuika'
          'UI_AvatarIcon_Side_Alhaitham'       -> 'UI_AvatarIcon_Alhaitham'
          'UI_AvatarIcon_Alhaitham'            -> 'UI_AvatarIcon_Alhaitham'
        """
        if not raw: return None
        # Fayl nomini olish
        if raw.startswith("/"):
            name = raw.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        else:
            name = raw.rsplit(".", 1)[0]
        # UI_AvatarIcon_Side_X -> X
        if name.startswith("UI_AvatarIcon_Side_"):
            return "UI_AvatarIcon_" + name[len("UI_AvatarIcon_Side_"):]
        # UI_AvatarIcon_X -> allaqachon to'g'ri
        if name.startswith("UI_AvatarIcon_"):
            return name
        # Faqat "Mavuika" -> "UI_AvatarIcon_Mavuika"
        return "UI_AvatarIcon_" + name

    def _get_icon_name(self, aid):
        info = self.avatars.get(str(aid))
        if not info or not isinstance(info, dict):
            print(f"[Icon] aid={aid} NOT in avatars")
            return None
        for key in ("Icon", "icon", "IconName", "SideIconName", "sideIconName"):
            v = info.get(key)
            if isinstance(v, str) and v:
                return self._normalize_icon(v)
        return None

    def _paimon_slug(self, char_name):
        if not char_name or char_name.startswith("#"):
            return None
        jp_families = ("kamisato", "kaedehara", "sangonomiya", "yae",
                       "raiden", "kujou", "arataki", "shikanoin", "kuki",
                       "yumemizuki", "shogun", "hiiragi", "sangonomiya",
                       "kamisato", "kaedehara")
        parts = char_name.split()
        if len(parts) >= 2 and parts[0].lower() in jp_families:
            return parts[1].lower()
        return char_name.lower().replace(" ", "").replace("'", "")

    def char_icon_urls(self, aid):
        name = self.char_name(aid)
        icon = self._get_icon_name(aid)
        urls = []
        if icon:
            if "Alhaitham" in icon:
                urls.append(f"https://enka.network/ui/{icon.replace('Alhaitham','Alhatham')}.png")
            urls.append(f"https://enka.network/ui/{icon}.png")
            urls.append(f"https://gi.yatta.moe/assets/UI/{icon}.png")
        slug = self._paimon_slug(name)
        if slug:
            urls.append(f"https://paimon.moe/images/characters/{slug}.png")
        return urls

    def char_art_urls(self, aid):
        name = self.char_name(aid)
        icon = self._get_icon_name(aid)
        urls = []
        # Enka BIRINCHI
        if icon:
            gacha = icon.replace("UI_AvatarIcon_", "UI_Gacha_AvatarImg_")
            if "Alhaitham" in gacha:
                urls.append(f"https://enka.network/ui/{gacha.replace('Alhaitham','Alhatham')}.png")
            urls.append(f"https://enka.network/ui/{gacha}.png")
            urls.append(f"https://gi.yatta.moe/assets/UI/{gacha}.png")
        # Zaxira — kichik ikonka
        urls += self.char_icon_urls(aid)
        return urls

    def _short_name(self, aid):
        """UI_AvatarIcon_Mavuika -> Mavuika (Alhaitham substitution bilan)."""
        icon = self._get_icon_name(aid)
        if not icon: return None
        short = icon.replace("UI_AvatarIcon_", "")
        # Alhaitham typo fix
        if short == "Alhaitham":
            short = "Alhatham"
        return short

    def constellation_icon_urls(self, aid, index):
        """index 1..6"""
        short = self._short_name(aid)
        if not short: return []
        return [
            f"https://enka.network/ui/UI_Talent_S_{short}_{index}.png",
            f"https://enka.network/ui/UI_Talent_S_{short}_{index:02d}.png",
            f"https://gi.yatta.moe/assets/UI/UI_Talent_S_{short}_{index}.png",
        ]

    def _weapon_type(self, aid):
        """WEAPON_CLAYMORE -> Claymore, WEAPON_SWORD_ONE_HAND -> Sword"""
        info = self.avatars.get(str(aid))
        if not info: return None
        wt = (info.get("WeaponType") or "").replace("WEAPON_", "")
        if wt.startswith("SWORD"): return "Sword"
        if wt.startswith("CLAYMORE"): return "Claymore"
        if wt.startswith("POLE"): return "Pole"
        if wt.startswith("CATALYST"): return "Catalyst"
        if wt.startswith("BOW"): return "Bow"
        return None

    def talent_icon_urls(self, aid, ttype):
        """ttype: 'Attack', 'Skill', 'Burst'"""
        short = self._short_name(aid)
        if not short: return []
        if ttype == "Attack":
            wt = self._weapon_type(aid)
            if not wt: return []
            return [
                f"https://enka.network/ui/UI_Talent_Attack_{wt}.png",
                f"https://gi.yatta.moe/assets/UI/UI_Talent_Attack_{wt}.png",
            ]
        if ttype == "Skill":
            return [
                f"https://enka.network/ui/UI_Talent_Skill_{short}.png",
                f"https://gi.yatta.moe/assets/UI/UI_Talent_Skill_{short}.png",
            ]
        if ttype == "Burst":
            return [
                f"https://enka.network/ui/UI_Talent_Burst_{short}.png",
                f"https://gi.yatta.moe/assets/UI/UI_Talent_Burst_{short}.png",
            ]
        return []

    def char_element(self, aid):
        info = self.avatars.get(str(aid))
        if not info: return None
        raw = info.get("Element")
        if not raw: return None
        # Enka ba'zi hollarda eski nomlarni ishlatadi
        elem_map = {
            "Grass": "Dendro",
            "Fire": "Pyro",
            "Water": "Hydro",
            "Electric": "Electro",
            "Ice": "Cryo",
            "Wind": "Anemo",
            "Rock": "Geo",
            "Physical": "Physical",
        }
        return elem_map.get(raw, raw)
