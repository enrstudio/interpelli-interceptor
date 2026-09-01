#!/usr/bin/env python3
"""
Test della funzione matches_keywords() usando titoli REALI presi dalle
pagine di Bologna e Lucca-Massa controllate il 24/08/2026, più alcuni
titoli di controllo con classi di concorso non pertinenti (devono
risultare "NO match").
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from monitor_interpelli import matches_keywords, _escape_markdown_v2  # noqa: E402

# Titoli reali raccolti oggi da bo.istruzioneer.gov.it e ustms.it,
# più alcuni titoli fittizi con A060/A028/AM01/arte/tecnologia per
# verificare che il matching positivo funzioni.
CASI = [
    # (titolo, atteso: True se deve essere segnalato)
    ("Interpello preventivo per supplenze brevi ADEE – IC n. 3 \"Lame\" Bologna", False),
    ("Interpello nazionale per nomina ADAA c/o I. C. n. 5 di Imola (BO)", False),
    ("Interpello nazionale per nomina EEEE c/o I.C. Ceretolo – Casalecchio di R.(BO)", False),
    ("IC FERRARI: INTERPELLO SUPPLENZA SCUOLA INFANZIA, SEDE DI ARPIOLA", False),
    ("I.C. DON MILANI: Interpello per la classe di concorso AM12", False),
    ("IS MONTESSORI-REPETTI: Interpello nazionale ... c.d.c. (A027) Matematica e Fisica", False),
    # Titoli reali dalla pagina IC Lippi di Prato (controllata il 24/08/2026)
    ("FIRMATO_AVVISO-1-INTERPELLO-supplenze-brevi-e-saltuarie-fino-a-10-gg-ICS-F-LIPPI", False),
    ("FIRMATO_AVVISO N° 6 – AG56 – Secondaria I° (FLAUTO) – dal 26-01-2026 al 03-02-2026", False),
    ("FIRMATO_AVVISO N° 7 – AB56 – Secondaria I° (CHITARRA) – dal 26-01-2026 al 03-02-2026", False),
    ("AVVISO N° 16 – AM12 – Secondaria I° (LETTERE) – _-signed", False),
    # Casi che DEVONO essere intercettati (simulano avvisi reali per le tue classi)
    ("Interpello nazionale per supplenza cdc A060 Tecnologia - IC Don Milani Pistoia", True),
    ("INTERPELLO — Scuola secondaria I grado, classe di concorso A001 Arte e Immagine", True),
    ("I.C. Levi Prato: interpello classe di concorso AM01 - Arte e Immagine 12h settimanali", True),
    ("Interpello per supplenza breve A-01 Arte e Immagine scuola media Lucca", True),
    ("Interpello A060 9h settimanali IC Don Milani Bologna fino al 30/06", True),
    ("Interpello classe di concorso A037 Scienze e Tecnologie delle Costruzioni - IIS Gramsci-Keynes Prato", True),
    ("INTERPELLO per Rappresentazione Grafica, Istituto Tecnico settore CAT, 12h sett.", True),
    # Caso limite che NON deve scattare (denominazione vecchia, ormai desueta)
    ("Interpello A016 disegno tecnico - vecchia denominazione non più in uso", False),
    # IMPORTANTE: A028 = Matematica (non Arte e Immagine) nel sistema attuale.
    # Deve restare False, altrimenti sarebbe un falso positivo.
    ("INTERPELLO – ICS \"Raffaello\" supplenza cdc A028 (Matematica e scienze) 18h sett.", False),
]

def main():
    ok = 0
    for titolo, atteso in CASI:
        risultato = matches_keywords(titolo)
        esito = "OK " if risultato == atteso else "FAIL"
        if risultato == atteso:
            ok += 1
        print(f"[{esito}] match={risultato!s:5} atteso={atteso!s:5} | {titolo}")

    print(f"\n{ok}/{len(CASI)} test di matching superati.")

    # Test dell'escape MarkdownV2 per Telegram: i caratteri speciali nei
    # titoli reali delle scuole (parentesi, punti, trattini) devono
    # essere escapati o Telegram rifiuta il messaggio con un errore 400.
    casi_escape = [
        ("I.C. Ceretolo – Casalecchio di R.(BO)", r"I\.C\. Ceretolo – Casalecchio di R\.\(BO\)"),
        ("A027 - Matematica e Fisica", r"A027 \- Matematica e Fisica"),
        ("100% posto comune!", r"100% posto comune\!"),
    ]
    ok_escape = 0
    for originale, atteso in casi_escape:
        risultato = _escape_markdown_v2(originale)
        esito = "OK " if risultato == atteso else "FAIL"
        if risultato == atteso:
            ok_escape += 1
        print(f"[{esito}] escape | {originale!r} -> {risultato!r}")

    print(f"{ok_escape}/{len(casi_escape)} test di escape Telegram superati.")

    totale_ok = ok + ok_escape
    totale = len(CASI) + len(casi_escape)
    if totale_ok != totale:
        sys.exit(1)

if __name__ == "__main__":
    main()
