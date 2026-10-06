APP_NAME = "Asadbek's Ranking System"
APP_VERSION = "1.2.0"
USER_AGENT = f"AsadbeksRankingSystem/{APP_VERSION}"

GAMES = {"Genshin Impact": "https://enka.network/api/uid/{uid}"}

REGIONS = {
    "os_usa": "America", "os_euro": "Europe", "os_asia": "Asia",
    "os_cht": "TW/HK/MO", "prod_official_usa": "America",
    "prod_official_eur": "Europe", "prod_official_asia": "Asia",
    "prod_official_cht": "TW/HK/MO",
}

def _slug(name):
    return (name.lower().replace(" ", "").replace("'", "")
            .replace("&", "").replace("-", "").replace(".", "")
            .replace(":", "").replace(",", ""))

def ui_urls(name):
    if not name: return []
    if name.startswith("UI_RelicIcon_"):
        return [f"https://gi.yatta.moe/assets/UI/reliquary/{name}.png",
                f"https://enka.network/ui/{name}.png"]
    if name.startswith("UI_EquipIcon_"):
        return [f"https://gi.yatta.moe/assets/UI/{name}.png",
                f"https://enka.network/ui/{name}.png"]
    if name.startswith("UI_NameCardPic_"):
        return [f"https://enka.network/ui/{name}.png",
                f"https://gi.yatta.moe/assets/UI/{name}.png"]
    return [f"https://enka.network/ui/{name}.png",
            f"https://gi.yatta.moe/assets/UI/{name}.png"]

def avatar_icon_urls(icon_name, char_name=None):
    urls = []
    name = icon_name
    if "Alhaitham" in icon_name:
        urls.append(f"https://enka.network/ui/{icon_name.replace('Alhaitham','Alhatham')}.png")
    urls.append(f"https://enka.network/ui/{icon_name}.png")
    urls.append(f"https://gi.yatta.moe/assets/UI/{icon_name}.png")
    if char_name and not char_name.startswith("#"):
        s = _slug(char_name)
        urls.append(f"https://paimon.moe/images/characters/{s}.png")
    return urls

def avatar_art_urls(icon_name, char_name=None):
    if not icon_name: return []
    gacha = icon_name.replace("UI_AvatarIcon_", "UI_Gacha_AvatarImg_")
    urls = []
    if "Alhaitham" in gacha:
        urls.append(f"https://enka.network/ui/{gacha.replace('Alhaitham','Alhatham')}.png")
    urls.append(f"https://enka.network/ui/{gacha}.png")
    urls.append(f"https://gi.yatta.moe/assets/UI/{gacha}.png")
    urls += avatar_icon_urls(icon_name, char_name)
    return urls

AVATARS_SOURCES = [
    "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/gi/avatars.json",
    "https://cdn.jsdelivr.net/gh/EnkaNetwork/API-docs@master/store/gi/avatars.json",
]
LOCS_SOURCES = [
    "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/gi/locs.json",
    "https://cdn.jsdelivr.net/gh/EnkaNetwork/API-docs@master/store/gi/locs.json",
]

# Stat tartibi (akasha.cv uslubi)
STAT_KEYS = {
    "2000": "HP",
    "2001": "ATK",
    "2002": "DEF",
    "28": "Elemental Mastery",
    "20": "Crit Rate",
    "22": "Crit DMG",
    "23": "Energy Recharge",
    "40": "Pyro DMG",
    "41": "Electro DMG",
    "42": "Hydro DMG",
    "43": "Dendro DMG",
    "44": "Anemo DMG",
    "45": "Geo DMG",
    "46": "Cryo DMG",
    "30": "Physical DMG",
}

# Stat ikonkalari
STAT_ICONS = {
    "HP": "UI_Icon_Attribute_Hp",
    "ATK": "UI_Icon_Attribute_Attack",
    "DEF": "UI_Icon_Attribute_Defense",
    "Elemental Mastery": "UI_Icon_Attribute_ElementalMastery",
    "Crit Rate": "UI_Icon_Attribute_Critical",
    "Crit DMG": "UI_Icon_Attribute_CriticalHurt",
    "Energy Recharge": "UI_Icon_Attribute_ChargeEfficiency",
    "Pyro DMG": "UI_Icon_Attribute_FireAddHurt",
    "Electro DMG": "UI_Icon_Attribute_ElecAddHurt",
    "Hydro DMG": "UI_Icon_Attribute_WaterAddHurt",
    "Dendro DMG": "UI_Icon_Attribute_GrassAddHurt",
    "Anemo DMG": "UI_Icon_Attribute_WindAddHurt",
    "Geo DMG": "UI_Icon_Attribute_RockAddHurt",
    "Cryo DMG": "UI_Icon_Attribute_IceAddHurt",
    "Physical DMG": "UI_Icon_Attribute_PhysicalAddHurt",
}

# Substat nomlari (fightPropMap kalitlaridan)
PROP_NAMES = {
    "FIGHT_PROP_HP": "HP",
    "FIGHT_PROP_HP_PERCENT": "HP%",
    "FIGHT_PROP_ATTACK": "ATK",
    "FIGHT_PROP_ATTACK_PERCENT": "ATK%",
    "FIGHT_PROP_DEFENSE": "DEF",
    "FIGHT_PROP_DEFENSE_PERCENT": "DEF%",
    "FIGHT_PROP_ELEMENT_MASTERY": "Elemental Mastery",
    "FIGHT_PROP_CRITICAL": "Crit Rate",
    "FIGHT_PROP_CRITICAL_HURT": "Crit DMG",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "Energy Recharge",
    "FIGHT_PROP_HEAL_ADD": "Healing Bonus",
    "FIGHT_PROP_FIRE_ADD_HURT": "Pyro DMG",
    "FIGHT_PROP_ELEC_ADD_HURT": "Electro DMG",
    "FIGHT_PROP_WATER_ADD_HURT": "Hydro DMG",
    "FIGHT_PROP_GRASS_ADD_HURT": "Dendro DMG",
    "FIGHT_PROP_WIND_ADD_HURT": "Anemo DMG",
    "FIGHT_PROP_ROCK_ADD_HURT": "Geo DMG",
    "FIGHT_PROP_ICE_ADD_HURT": "Cryo DMG",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "Physical DMG",
}

PROP_IS_PCT = {
    "FIGHT_PROP_HP_PERCENT", "FIGHT_PROP_ATTACK_PERCENT",
    "FIGHT_PROP_DEFENSE_PERCENT", "FIGHT_PROP_CRITICAL",
    "FIGHT_PROP_CRITICAL_HURT", "FIGHT_PROP_CHARGE_EFFICIENCY",
    "FIGHT_PROP_HEAL_ADD", "FIGHT_PROP_FIRE_ADD_HURT",
    "FIGHT_PROP_ELEC_ADD_HURT", "FIGHT_PROP_WATER_ADD_HURT",
    "FIGHT_PROP_GRASS_ADD_HURT", "FIGHT_PROP_WIND_ADD_HURT",
    "FIGHT_PROP_ROCK_ADD_HURT", "FIGHT_PROP_ICE_ADD_HURT",
    "FIGHT_PROP_PHYSICAL_ADD_HURT",
}

SLOT_NAMES = {
    "EQUIP_BRACER": "Flower",
    "EQUIP_NECKLACE": "Plume",
    "EQUIP_SHOES": "Sands",
    "EQUIP_RING": "Goblet",
    "EQUIP_DRESS": "Circlet",
}

ELEMENT_COLORS = {
    "Pyro": "#ff6b3d", "Hydro": "#4fc3f7", "Anemo": "#6fe6b8",
    "Electro": "#b388ff", "Dendro": "#8bc34a", "Cryo": "#8fe4f5",
    "Geo": "#ffb547", "Physical": "#c8c8d0",
}

ELEMENT_TO_DMG = {
    "Pyro": "40", "Electro": "41", "Hydro": "42",
    "Dendro": "43", "Anemo": "44", "Geo": "45", "Cryo": "46",
}

def namecard_urls(nc_id):
    """Namecard ID -> URL ro'yxati."""
    if not nc_id: return []
    return [
        f"https://enka.network/ui/UI_NameCardPic_{nc_id}_P.png",
        f"https://enka.network/ui/UI_NameCardPic_{nc_id}_P.jpg",
        f"https://gi.yatta.moe/assets/UI/UI_NameCardPic_{nc_id}_P.png",
        f"https://upload-os-bbs.mihoyo.com/game_record/genshin/name_card/UI_NameCardPic_{nc_id}_P.png",
    ]



MAX_ROLL = {
    "Crit Rate": 3.89, "Crit DMG": 7.77,
    "HP%": 5.83, "ATK%": 5.83, "DEF%": 7.29,
    "Elemental Mastery": 23.31,
    "Energy Recharge": 6.48,
    "HP": 298.75, "ATK": 19.45, "DEF": 23.31,
}


def num_val(v):
    return float(str(v).replace(",", "").replace("%", ""))


# Combo short nomi -> jamoa a'zolari (characterId)
# Akasha'dagi tayyor jamoalar
TEAM_BY_CHAR = {}   # Bo'sh — jamoa tavsiyalari o'chirildi

