from __future__ import annotations

COUNTRY_ALIASES = {
    "australia": "Australia",
    "austria": "Austria",
    "be": "Belgium",
    "brazil": "Brazil",
    "ca": "Canada",
    "canada": "Canada",
    "china": "China",
    "cyprus": "Cyprus",
    "czechia": "Czechia",
    "denmark": "Denmark",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "greece": "Greece",
    "hungary": "Hungary",
    "india": "India",
    "ireland": "Ireland",
    "italy": "Italy",
    "japan": "Japan",
    "korea": "South Korea",
    "republic of korea": "South Korea",
    "south korea": "South Korea",
    "morocco": "Morocco",
    "netherlands": "Netherlands",
    "the netherlands": "Netherlands",
    "portugal": "Portugal",
    "singapore": "Singapore",
    "spain": "Spain",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "thailand": "Thailand",
    "u.a.e.": "United Arab Emirates",
    "u.a.e": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "u.s.": "United States",
    "u.s": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "usa": "United States",
    "united states": "United States",
}

STATE_TO_COUNTRY = {
    "ca": "United States",
    "pa": "United States",
    "ga": "United States",
    "california": "United States",
    "colorado": "United States",
    "florida": "United States",
    "georgia": "United States",
    "hawaii": "United States",
    "illinois": "United States",
    "louisiana": "United States",
    "massachusetts": "United States",
    "new york": "United States",
    "north carolina": "United States",
    "pennsylvania": "United States",
    "tennessee": "United States",
    "texas": "United States",
    "utah": "United States",
    "virginia": "United States",
    "washington": "United States",
}

COUNTRY_KO = {
    "Australia": "\ud638\uc8fc",
    "Austria": "\uc624\uc2a4\ud2b8\ub9ac\uc544",
    "Belgium": "\ubca8\uae30\uc5d0",
    "Brazil": "\ube0c\ub77c\uc9c8",
    "Canada": "\uce90\ub098\ub2e4",
    "China": "\uc911\uad6d",
    "Cyprus": "\ud0a4\ud504\ub85c\uc2a4",
    "Czechia": "\uccb4\ucf54",
    "Denmark": "\ub374\ub9c8\ud06c",
    "Finland": "\ud540\ub780\ub4dc",
    "France": "\ud504\ub791\uc2a4",
    "Germany": "\ub3c5\uc77c",
    "Greece": "\uadf8\ub9ac\uc2a4",
    "Hungary": "\ud5dd\uac00\ub9ac",
    "India": "\uc778\ub3c4",
    "Ireland": "\uc544\uc77c\ub79c\ub4dc",
    "Italy": "\uc774\ud0c8\ub9ac\uc544",
    "Japan": "\uc77c\ubcf8",
    "South Korea": "\ub300\ud55c\ubbfc\uad6d",
    "Morocco": "\ubaa8\ub85c\ucf54",
    "Netherlands": "\ub124\ub35c\ub780\ub4dc",
    "Portugal": "\ud3ec\ub974\ud22c\uac08",
    "Singapore": "\uc2f1\uac00\ud3ec\ub974",
    "Spain": "\uc2a4\ud398\uc778",
    "Sweden": "\uc2a4\uc6e8\ub374",
    "Switzerland": "\uc2a4\uc704\uc2a4",
    "Thailand": "\ud0dc\uad6d",
    "United Arab Emirates": "\uc544\ub78d\uc5d0\ubbf8\ub9ac\ud2b8",
    "United Kingdom": "\uc601\uad6d",
    "United States": "\ubbf8\uad6d",
}


def normalize_country(value: str | None, *, prefer_state: bool = False) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    lowered = cleaned.lower().strip(".")
    if prefer_state and lowered in STATE_TO_COUNTRY:
        return STATE_TO_COUNTRY[lowered]
    if lowered in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[lowered]
    if lowered in STATE_TO_COUNTRY:
        return STATE_TO_COUNTRY[lowered]
    return cleaned


def country_ko(value: str | None) -> str | None:
    normalized = normalize_country(value)
    if not normalized:
        return None
    return COUNTRY_KO.get(normalized, normalized)
