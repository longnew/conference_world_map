from __future__ import annotations

COUNTRY_ALIASES = {
    "australia": "Australia",
    "austria": "Austria",
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
    "Australia": "호주",
    "Austria": "오스트리아",
    "Brazil": "브라질",
    "Canada": "캐나다",
    "China": "중국",
    "Cyprus": "키프로스",
    "Czechia": "체코",
    "Denmark": "덴마크",
    "Finland": "핀란드",
    "France": "프랑스",
    "Germany": "독일",
    "Greece": "그리스",
    "Hungary": "헝가리",
    "India": "인도",
    "Ireland": "아일랜드",
    "Italy": "이탈리아",
    "Japan": "일본",
    "South Korea": "대한민국",
    "Morocco": "모로코",
    "Netherlands": "네덜란드",
    "Portugal": "포르투갈",
    "Singapore": "싱가포르",
    "Spain": "스페인",
    "Sweden": "스웨덴",
    "Switzerland": "스위스",
    "Thailand": "태국",
    "United Arab Emirates": "아랍에미리트",
    "United Kingdom": "영국",
    "United States": "미국",
}


def normalize_country(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    lowered = cleaned.lower().strip(".")
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
