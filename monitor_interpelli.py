#!/usr/bin/env python3
"""
Monitor Interpelli Scuola - Pistoia, Prato, Lucca, Bologna
============================================================
Controlla le pagine ufficiali degli Uffici Scolastici Territoriali,
individua i nuovi avvisi di interpello compatibili con le tue classi
di concorso e invia una email di notifica.

Pensato per essere eseguito periodicamente (es. ogni 20 minuti) tramite
cron (Linux/Mac) o Task Scheduler (Windows). Non serve tenerlo aperto
manualmente: è lo scheduler del sistema a rilanciarlo.

Configurazione: modifica le costanti qui sotto, oppure imposta le
variabili d'ambiente corrispondenti (consigliato per le credenziali email).
"""

import os
import re
import json
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# CONFIGURAZIONE
# --------------------------------------------------------------------------

# Pagine da monitorare: (nome, url, tipo)
# tipo "wordpress" = sito WordPress classico (Bologna, Lucca-Massa, singole scuole)
# tipo "telegram"  = pagina pubblica di anteprima di un canale Telegram
#
# NOTA IMPORTANTE: il sito ufficiale centrale di Pistoia e Prato
# (ufficioscolasticoprovinciale.pistoia.it e .prato.it) blocca l'accesso
# automatico via robots.txt. Non li includiamo per rispetto delle loro
# regole. Per Pistoia usiamo il canale Telegram ufficiale dell'USP.
# Per Prato non esiste un canale equivalente: monitoriamo direttamente le
# pagine interpelli delle singole scuole che NON bloccano l'accesso
# automatico (verificato manualmente). Al momento solo IC Filippino Lippi
# risulta accessibile in questo modo tra quelle controllate — altre
# scuole di Prato pubblicano solo tramite il portale Argo (applicazione
# JavaScript, non leggibile con questo metodo semplice) o bloccano i bot.
# Aggiungi altre righe qui sotto man mano che trovi altre scuole di Prato
# accessibili (vedi README, sezione "Aggiungere altre scuole di Prato").
SOURCES = [
    ("Pistoia (canale Telegram USP)", "https://t.me/s/USPistoiainforma", "telegram"),
    ("Lucca-Massa", "https://www.ustms.it/category/docenti/interpelli/", "wordpress"),
    ("Bologna", "https://bo.istruzioneer.gov.it/tag/interpelli/", "wordpress"),
    ("Prato - IC Filippino Lippi", "https://www.lippiprato.edu.it/messe-a-disposizione-nuova-modalita-di-presentazione/", "wordpress"),
]

# Parole chiave che identificano un avviso potenzialmente utile per te.
# Aggiungi/togli liberamente. Il match è case-insensitive e su tutto il
# testo del link (titolo dell'avviso).
KEYWORDS = [
    "a060", "a-60", "tecnologia",
    "a001", "a-01", "am01", "arte e immagine", "educazione artistica",
    "a037", "a-37", "scienze e tecnologie delle costruzioni",
    "rappresentazione grafica", "costruzioni ambiente e territorio",
]

# NOTA IMPORTANTE (24/08/2026): A028 è stato rimosso da qui deliberatamente.
# Nel sistema di codifica attuale A028 = Matematica (e Scienze) alla scuola
# media, NON Arte e Immagine — che invece è A001. Fonte: documento organico
# di diritto 2024/25 pubblicato dall'USP di Pistoia. Diverse guide online
# confondono la vecchia numerazione (dove "28/A" indicava Educazione
# Artistica) con quella nuova, che riusa gli stessi numeri per materie
# diverse — lo stesso problema già visto con A036/A037 e la filosofia.

# Parole che, se presenti, ESCLUDONO l'avviso anche se contiene una keyword
# sopra (utile per filtrare rumore, es. "arte" che compare in contesti non
# pertinenti). Lascia vuoto se non ti serve.
EXCLUDE_KEYWORDS = []

# Percorso del file che tiene traccia degli avvisi già visti (state).
STATE_FILE = Path(__file__).parent / "seen_interpelli.json"

# --- Email (consigliato: usa variabili d'ambiente invece di scrivere qui) ---
SMTP_HOST = os.environ.get("INTERPELLI_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("INTERPELLI_SMTP_PORT", "465"))
SMTP_USER = os.environ.get("INTERPELLI_SMTP_USER", "")          # es. tuamail@gmail.com
SMTP_PASSWORD = os.environ.get("INTERPELLI_SMTP_PASSWORD", "")  # App Password, non la password normale
EMAIL_TO = os.environ.get("INTERPELLI_EMAIL_TO", SMTP_USER)     # a chi mandare l'avviso

# --- Telegram (alternativa o aggiunta all'email) ---
TELEGRAM_BOT_TOKEN = os.environ.get("INTERPELLI_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("INTERPELLI_TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

# --------------------------------------------------------------------------
# LOGICA
# --------------------------------------------------------------------------

def load_seen():
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_seen(seen):
    STATE_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8")


def matches_keywords(text):
    t = text.lower()
    if any(bad.lower() in t for bad in EXCLUDE_KEYWORDS):
        return False
    return any(kw.lower() in t for kw in KEYWORDS)


def _get_with_retry(url, max_attempts=2, backoff_seconds=3):
    """Richiesta HTTP con un tentativo di retry in caso di errore transitorio
    (utile contro blocchi anti-bot momentanei tipo Cloudflare)."""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt < max_attempts:
                time.sleep(backoff_seconds)
    raise last_exc


def fetch_links_wordpress(url):
    """Scarica una pagina WordPress ed estrae (titolo, link) di ogni avviso.

    Alcune pagine (es. quelle degli USP) marcano i titoli con tag
    strutturati (h2/h3/.entry-title/article). Altre (es. pagine "servizio"
    di singole scuole, dove gli interpelli sono semplici link in mezzo al
    testo) non hanno questa struttura: per queste usiamo un selettore più
    ampio e filtriamo per la parola "interpel" nel testo del link, per
    evitare di catturare i link del menu di navigazione.
    """
    resp = _get_with_retry(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    seen_links = set()

    # Primo tentativo: struttura "a blog" classica (USP, ecc.)
    structured = soup.select("h2 a, h3 a, .entry-title a, article a")
    for a in structured:
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or not href or len(title) < 8 or href in seen_links:
            continue
        seen_links.add(href)
        items.append((title, href))

    # Fallback: qualunque link il cui testo contenga "interpel"
    # (interpello/interpelli), utile per pagine "servizio" di singole
    # scuole senza struttura a blog.
    if not items:
        for a in soup.find_all("a"):
            title = a.get_text(strip=True)
            href = a.get("href")
            if not title or not href or href in seen_links:
                continue
            if "interpel" not in title.lower():
                continue
            seen_links.add(href)
            items.append((title, href))

    return items


def fetch_links_telegram(url):
    """Scarica la pagina pubblica di anteprima di un canale Telegram ed
    estrae (testo_messaggio, link_permanente) per ogni post."""
    resp = _get_with_retry(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for msg in soup.select(".tgme_widget_message"):
        text_el = msg.select_one(".tgme_widget_message_text")
        if not text_el:
            continue
        title = text_el.get_text(" ", strip=True)
        post_id = msg.get("data-post")  # es. "USPistoiainforma/2489"
        if not title or not post_id:
            continue
        link = f"https://t.me/{post_id}"
        items.append((title, link))
    return items


def fetch_links(source_type, url):
    if source_type == "telegram":
        return fetch_links_telegram(url)
    return fetch_links_wordpress(url)


def send_email(new_items):
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[!] Credenziali email non configurate: salto invio email.")
        return

    body_lines = ["Nuovi interpelli compatibili trovati:\n"]
    for source, title, link in new_items:
        body_lines.append(f"[{source}] {title}\n{link}\n")
    body = "\n".join(body_lines)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Interpelli scuola: {len(new_items)} nuovo/i avviso/i"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())
    print(f"[✓] Email inviata a {EMAIL_TO} con {len(new_items)} avviso/i.")


def _escape_markdown_v2(text):
    """Escapa i caratteri speciali richiesti da Telegram in modalità MarkdownV2."""
    specials = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in specials else c for c in text)


def send_telegram(new_items):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Credenziali Telegram non configurate: salto invio Telegram.")
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Telegram limita i messaggi a 4096 caratteri: se sono tanti avvisi,
    # li spediamo divisi in più messaggi invece di uno enorme.
    for source, title, link in new_items:
        text = (
            f"🔔 *Nuovo interpello*\n"
            f"📍 {_escape_markdown_v2(source)}\n"
            f"{_escape_markdown_v2(title)}\n"
            f"{link}"
        )
        try:
            resp = requests.post(
                api_url,
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": False,
                },
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[!] Errore invio Telegram per '{title}': {e}")
            continue

    print(f"[✓] Notifiche Telegram inviate ({len(new_items)} avviso/i).")


def main():
    print(f"--- Controllo interpelli — {datetime.now().isoformat(timespec='seconds')} ---")
    seen = load_seen()
    new_items = []

    for source, url, source_type in SOURCES:
        try:
            items = fetch_links(source_type, url)
        except requests.RequestException as e:
            print(f"[!] Errore su {source} ({url}): {e}")
            continue

        for title, link in items:
            if link in seen:
                continue
            seen.add(link)
            if matches_keywords(title):
                new_items.append((source, title, link))

        print(f"[i] {source}: {len(items)} avvisi letti sulla pagina.")

    save_seen(seen)

    if new_items:
        print(f"[+] Trovati {len(new_items)} nuovi avvisi compatibili.")
        for source, title, link in new_items:
            print(f" - [{source}] {title}\n   {link}")

        if not (SMTP_USER and SMTP_PASSWORD) and not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
            print("[!] Nessun canale di notifica configurato (né email né Telegram). "
                  "Vedi README per la configurazione.")
        if SMTP_USER and SMTP_PASSWORD:
            send_email(new_items)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram(new_items)
    else:
        print("[i] Nessun nuovo avviso compatibile.")


if __name__ == "__main__":
    main()
