import re

BANDAS = {
    "160m": (1810, 2000), "80m": (3500, 3800), "60m": (5351, 5367),
    "40m": (7000, 7200), "30m": (10100, 10150), "20m": (14000, 14350),
    "17m": (18068, 18168), "15m": (21000, 21450), "12m": (24890, 24990),
    "10m": (28000, 29700), "6m": (50000, 52000), "4m": (70000, 70500),
    "2m": (144000, 146000), "70cm": (430000, 440000)
}

def obtener_banda(f):
    for b, (i, fin) in BANDAS.items():
        if i <= f <= fin: return b
    return "Otras"

def detectar_modo_definitivo(freq_khz, comentario):
    com = comentario.upper()
    try:
        f = float(freq_khz)
    except:
        return "DIGI"

    if re.search(r'\bFT8\b', com): return "FT8"
    if re.search(r'\bFT4\b', com): return "FT4"
    if re.search(r'\bCW\b', com): return "CW"
    if re.search(r'\b(RTTY|PSK|VARA|JS8|DIGI)\b', com): return "DIGI"
    if re.search(r'\b(SSB|LSB|USB|PH|FM)\b', com): return "SSB"

    # Lógica por segmentos (Exclusión)
    if (14000 <= f <= 14070) or (7000 <= f <= 7040) or (21000 <= f <= 21070): return "CW"
    if (14101 <= f <= 14350) or (7050 <= f <= 7200) or (21151 <= f <= 21450): return "SSB"
    
    dec = f - int(f)
    if 0.070 <= dec <= 0.076: return "FT8"
    if 0.080 <= dec <= 0.082: return "FT4"
    return "DIGI"