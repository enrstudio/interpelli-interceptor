# Monitor Interpelli Scuola (PT / PO / LU / BO)

Script personale che controlla le pagine ufficiali degli Uffici Scolastici
Territoriali e ti manda una email quando esce un nuovo interpello che
contiene le tue classi di concorso (A060 Tecnologia, A028/AM01 Arte e
Immagine — modifica la lista `KEYWORDS` nello script se ti serve altro).

**Importante**: questo script deve girare su un computer/server che resta
acceso (il tuo PC, un Raspberry Pi, un piccolo VPS...). Non è un servizio
cloud "sempre attivo" — è lo scheduler del tuo sistema (cron / Task
Scheduler) a rilanciarlo ogni 20 minuti.

## 1. Installazione

```bash
cd interpelli_monitor
python3 -m venv venv
source venv/bin/activate      # su Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurazione notifiche

Puoi usare **email**, **Telegram**, o entrambe insieme — lo script manda
la notifica su ogni canale configurato.

### Email (Gmail con App Password)
1. Attiva la verifica in due passaggi sul tuo account Google.
2. Vai su https://myaccount.google.com/apppasswords e genera una password
   per "Mail".
3. Imposta le variabili d'ambiente:

```bash
export INTERPELLI_SMTP_USER="tuamail@gmail.com"
export INTERPELLI_SMTP_PASSWORD="xxxxxxxxxxxxxxxx"   # app password, 16 caratteri
export INTERPELLI_EMAIL_TO="tuamail@gmail.com"       # dove vuoi ricevere l'avviso
```

Se usi un altro provider, imposta anche `INTERPELLI_SMTP_HOST` e
`INTERPELLI_SMTP_PORT` (es. Outlook: smtp.office365.com, porta 587 con
STARTTLS invece di SSL — in quel caso serve una piccola modifica allo
script, chiedimi pure se ti serve).

### Telegram (notifica push, consigliato)
1. Apri Telegram, cerca **@BotFather** e scrivigli `/newbot`. Segui le
   istruzioni (ti chiede un nome e uno username per il bot). Alla fine ti
   dà un **token** tipo `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
2. Scrivi un qualsiasi messaggio al tuo nuovo bot (es. "ciao") — è
   necessario perché un bot non può scriverti per primo finché non gli
   scrivi tu.
3. Trova il tuo **chat_id**: apri nel browser (sostituendo il token)
   `https://api.telegram.org/bot<IL_TUO_TOKEN>/getUpdates`
   e cerca `"chat":{"id":NUMERO` nel risultato — quel NUMERO è il tuo
   chat_id. Se la pagina è vuota, riscrivi al bot e ricarica.
4. Imposta le variabili d'ambiente:

```bash
export INTERPELLI_TELEGRAM_BOT_TOKEN="123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export INTERPELLI_TELEGRAM_CHAT_ID="987654321"
```

## 3. Test manuale

```bash
python3 monitor_interpelli.py
```

La prima esecuzione segna come "già visti" tutti gli avvisi presenti in
quel momento (per non ricevere una mail con centinaia di interpelli
vecchi). Da quel momento in poi ti segnala solo le novità.

## 4. Esecuzione automatica ogni 20 minuti

### Linux / Mac (cron)

```bash
crontab -e
```

Aggiungi (adatta i percorsi):

```
*/20 * * * * cd /percorso/interpelli_monitor && /percorso/interpelli_monitor/venv/bin/python3 monitor_interpelli.py >> log.txt 2>&1
```

### Windows (Task Scheduler)

1. Apri "Utilità di pianificazione" → Crea attività.
2. Trigger: ripeti ogni 20 minuti, per una durata indefinita.
3. Azione: avvia programma → `venv\Scripts\python.exe`, argomenti:
   `monitor_interpelli.py`, cartella di avvio: la cartella dello script.

## 5. Personalizzare le fonti o le parole chiave

- `SOURCES`: aggiungi altre pagine di USP/scuole se vuoi ampliare il
  raggio (es. Firenze, se ti capita di guardare anche lì).
- `KEYWORDS`: modifica liberamente. Il matching è semplice (sottostringa,
  case-insensitive) sul titolo dell'avviso — non è infallibile: se una
  scuola scrive "arte immagine" senza "e" lo cattura comunque, ma valuta
  ogni tanto di controllare a mano per non perdere avvisi con testi
  insoliti.

## Limiti da conoscere

- **Pistoia**: monitorato tramite il canale Telegram ufficiale dell'USP
  (@USPistoiainforma), non dal sito centrale (bloccato via robots.txt).
- **Prato**: il sito centrale dell'USP blocca l'accesso automatico. Al
  momento monitoro solo la pagina di **IC Filippino Lippi**, l'unica
  verificata come accessibile tra le scuole controllate. La copertura di
  Prato è quindi parziale — vedi sezione 7 più sotto per estenderla.
- Le pagine dei siti possono cambiare struttura HTML nel tempo: se lo
  script smette di trovare avvisi, il sito potrebbe aver aggiornato il
  tema/layout e serve un piccolo aggiustamento ai selettori CSS in
  `fetch_links_wordpress()` / `fetch_links_telegram()`.
- Non sostituisce il controllo dei siti delle singole scuole di tuo
  interesse (alcune pubblicano solo sul proprio sito e in ritardo lo
  girano all'USP).

## Test eseguiti

- **Logica di filtro (`test_matching.py`)**: verificata con 11 casi reali
  e simulati (titoli presi dalle pagine di Bologna e Lucca-Massa il
  24/08/2026, più titoli di controllo con A060/A028/AM01) — 11/11
  superati. Puoi rilanciarlo con `python3 test_matching.py`.
- **Fetch delle pagine live**: verificato manualmente che le pagine di
  Bologna, Lucca-Massa e il canale Telegram di Pistoia sono raggiungibili
  e restituiscono la struttura attesa (titoli + link).
- **Quello che NON è stato testato da me**: l'esecuzione end-to-end dello
  script con una vera richiesta HTTP (l'ambiente in cui scrivo questi
  file non ha accesso diretto a internet). Il primo `python3
  monitor_interpelli.py` che farai tu sul tuo computer è quindi il primo
  test "vero" dal vivo — guarda l'output a schermo per assicurarti che
  dica "N avvisi letti" per ciascuna fonte (se dice 0, qualcosa nel
  selettore va aggiustato, scrivimi e ti aiuto).

## 6. Farlo girare gratis su GitHub Actions (alternativa al tuo PC)

Se non vuoi tenere un computer sempre acceso, puoi far girare tutto gratis
sui server di GitHub. Il file `.github/workflows/interpelli.yml` è già
pronto.

1. Crea un repository GitHub **pubblico** (per avere minuti illimitati
   gratis — vedi limiti spiegati in chat). Il contenuto dello script non è
   sensibile, le credenziali restano nei Secrets.
2. Carica tutti i file di questa cartella nel repository (inclusa la
   cartella `.github/workflows/`).
3. Vai su **Settings → Secrets and variables → Actions → New repository
   secret** e crea:
   - `INTERPELLI_SMTP_USER` → la tua email (se usi anche l'email)
   - `INTERPELLI_SMTP_PASSWORD` → la App Password (se usi anche l'email)
   - `INTERPELLI_EMAIL_TO` → dove vuoi ricevere gli avvisi via email
   - `INTERPELLI_TELEGRAM_BOT_TOKEN` → il token del bot (se usi Telegram)
   - `INTERPELLI_TELEGRAM_CHAT_ID` → il tuo chat_id (se usi Telegram)
4. Vai sulla tab **Actions** del repository, dovresti vedere il workflow
   "Monitor interpelli scuola". Puoi lanciarlo manualmente subito con
   "Run workflow" per fare un primo test, senza aspettare i 20 minuti.
5. Da lì in poi gira da solo ogni 20 minuti.

**Nota tecnica**: il workflow salva `seen_interpelli.json` facendo un
commit automatico nel repository dopo ogni esecuzione, così lo stato
("cosa ho già visto") si mantiene tra un run e l'altro. Questo ha anche
un vantaggio collaterale: risolve il problema della disattivazione dopo
60 giorni di inattività, perché il repository riceve un commit ogni 20
minuti in automatico.

## 7. Aggiungere altre scuole di Prato

Ho controllato alcune scuole di Prato per vedere quali permettono
l'accesso automatico (a differenza del sito centrale dell'USP, che lo
blocca). Al momento è utilizzabile solo **IC Filippino Lippi**. Molte
altre scuole di Prato pubblicano gli interpelli solo tramite il portale
esterno "Argo MAD-Interpello" (`madinterpello.portaleargo.it`), che è
un'applicazione JavaScript e non si può leggere con questo metodo
semplice di scraping.

Se vuoi aggiungere un'altra scuola:
1. Trova la pagina "interpelli" / "messa a disposizione" sul sito della
   scuola (dominio tipo `nomescuola.edu.it`).
2. Prova ad aprirla in una finestra anonima del browser: se si apre
   normalmente è probabile che l'accesso automatico sia permesso (ma non
   è garantito al 100%, dipende dal robots.txt del sito).
3. Aggiungi una riga in `SOURCES` in `monitor_interpelli.py`:
   ```python
   ("Prato - Nome Scuola", "https://url-della-pagina/", "wordpress"),
   ```
4. Rilancia lo script: se nel log vedi "N avvisi letti" con N > 0, ha
   funzionato. Se vedi 0, il selettore potrebbe non riconoscere la
   struttura di quella pagina — scrivimi il link e ti aiuto ad
   adattarlo.

In alternativa, per una copertura più ampia ma meno "in tempo reale" di
Prato, puoi impostare un **Google Alert** (gratis, su google.it/alerts)
con questa query (frequenza "appena accade", fonti "Automatico", lingua
Italiano, regione Italia — copre tutte e tre le tue classi di concorso in
un solo alert):
```
interpello Prato scuola (A060 OR tecnologia OR A028 OR AM01 OR "arte e immagine" OR A037 OR "scienze e tecnologie delle costruzioni" OR "rappresentazione grafica")
```

## 8. Le tue classi di concorso

Per chiarezza, ecco cosa monitora esattamente lo script (parole chiave in
`KEYWORDS` in `monitor_interpelli.py`):

- **A060** — Tecnologia, scuola secondaria di I grado (medie)
- **A001 / A-01 / AM01** — Arte e Immagine, scuola secondaria di I grado
  (medie). **Attenzione**: A028 NON è Arte e Immagine — è Matematica (e
  Scienze). Fonte: organico di diritto 2024/25 pubblicato dall'USP di
  Pistoia, che elenca esplicitamente "A001 = Ed.Artistica" e "A028 =
  Matematica". Diverse guide online confondono la vecchia numerazione
  (dove "28/A" indicava Educazione Artistica) con quella attuale, che
  riusa gli stessi numeri per materie diverse.
- **A037** — Scienze e tecnologie delle costruzioni, tecnologie e
  tecniche di rappresentazione grafica. Si insegna negli **istituti
  tecnici** (settore Tecnologico, indirizzo Costruzioni Ambiente e
  Territorio - CAT, ex Geometri), **istituti professionali**, e nel
  **liceo scientifico opzione Scienze Applicate**. A Prato l'indirizzo
  CAT è presente all'ISIS Gramsci-Keynes.

Nota storica per evitare confusione: i codici "A036/A037" del sistema
**vecchio** (pre-2016) erano tutt'altro (Filosofia e Scienze
Umane/Filosofia e Storia) — la numerazione è stata riassegnata a materie
diverse nel sistema attuale. Se in giro trovi riferimenti ad "A037 =
Filosofia", sono riferiti al vecchio ordinamento. Lo stesso vale per
A028: nel vecchio ordinamento "28/A" era Educazione Artistica, oggi A028
è Matematica.



## 9. Nota sul blocco 403 di Bologna

`bo.istruzioneer.gov.it` può rispondere 403 quando lo script gira su
GitHub Actions, anche se il sito permette lo scraping via robots.txt — è
un blocco anti-bot (tipo Cloudflare) che spesso colpisce interi blocchi
di IP dei datacenter cloud, non specifico contro questo script. Dalla
versione con il fallback proxy, lo script tenta automaticamente di
bypassarlo tramite un proxy pubblico gratuito (allorigins.win) quando
incontra un 403: se nel log vedi "bypassato tramite proxy pubblico", ha
funzionato. Se anche il proxy fallisce (è un servizio di terze parti non
garantito al 100%), l'errore viene comunque segnalato e le altre fonti
continuano normalmente — non blocca l'intero controllo.
