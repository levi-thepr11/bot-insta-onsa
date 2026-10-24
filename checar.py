import os
import re
import json
import html
import time
import urllib.request
from datetime import datetime
from time import mktime

import feedparser

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
FEED_URL = os.environ["FEED_URL"]
NOME_PERFIL = os.getenv("NOME_PERFIL", "perfil").lstrip("@")
ARQUIVO = "vistos.json"
COR = 0xF58220


def limpar(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    return html.unescape(re.sub(r"<[^>]+>", "", t)).strip()


def imagem(e):
    if e.get("media_content"):
        return e["media_content"][0].get("url")
    if e.get("media_thumbnail"):
        return e["media_thumbnail"][0].get("url")
    for enc in e.get("enclosures", []):
        if "image" in enc.get("type", "image"):
            return enc.get("href")
    m = re.search(r'<img[^>]+src="([^"]+)"', e.get("summary", "") or "")
    return html.unescape(m.group(1)) if m else None


def baixar_feed():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return feedparser.parse(r.read())


def enviar(p):
    legenda = p["legenda"]
    embed = {
        "title": (p["titulo"] or legenda.split("\n")[0] or f"Novo post de @{NOME_PERFIL}")[:256],
        "url": p["link"],
        "description": legenda[:4000] or None,
        "color": COR,
        "footer": {"text": f"{NOME_PERFIL} | instagram.com | {p['data'].strftime('%d/%m/%Y %H:%M')}"},
    }
    if p["imagem"]:
        embed["image"] = {"url": p["imagem"]}
    corpo = json.dumps({"username": "NEWS-ALERT", "embeds": [embed]}).encode()
    req = urllib.request.Request(
        WEBHOOK, data=corpo, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    posts = []
    for e in baixar_feed().entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        posts.append({
            "id": str(e.get("id") or e.get("link")),
            "link": e.get("link"),
            "titulo": limpar(e.get("title")),
            "legenda": limpar(e.get("summary") or e.get("title")),
            "imagem": imagem(e),
            "data": datetime.fromtimestamp(mktime(t)) if t else datetime.now(),
        })

    try:
        with open(ARQUIVO, encoding="utf-8") as f:
            vistos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        vistos = None

    if vistos is None:  # primeira execução: só registra
        vistos = [p["id"] for p in posts]
        print(f"Primeira execução: {len(vistos)} posts registrados.")
    else:
        for p in sorted((x for x in posts if x["id"] not in vistos), key=lambda x: x["data"]):
            enviar(p)
            vistos.append(p["id"])
            time.sleep(1.5)

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(vistos[-500:], f)


main()
