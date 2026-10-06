"""Stat va talent ikonkalari — Emoji asosida (hamma Linux da ishlaydi)."""

STAT_EMOJI = {
    "HP": "❤️",
    "ATK": "⚔️",
    "DEF": "🛡️",
    "Elemental Mastery": "✨",
    "Crit Rate": "⭐",
    "Crit DMG": "💥",
    "Energy Recharge": "⚡",
    "Pyro DMG": "🔥",
    "Electro DMG": "⚡",
    "Hydro DMG": "💧",
    "Dendro DMG": "🌿",
    "Anemo DMG": "💨",
    "Geo DMG": "🪨",
    "Cryo DMG": "❄️",
    "Physical DMG": "⚔️",
    "HP%": "❤️", "ATK%": "⚔️", "DEF%": "🛡️",
}

TALENT_EMOJI = {
    "Attack": "🗡️",
    "Skill": "🌀",
    "Burst": "💫",
}


def stat_emoji(name):
    return STAT_EMOJI.get(name, "◆")


def talent_emoji(name):
    return TALENT_EMOJI.get(name, "◆")
