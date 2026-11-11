# PE tracking: feed automatici e sincronizzazione del team (solo GitHub + Azure)

App statica (`index.html`) senza Firebase e senza Cloudflare.

1. **GitHub Action giornaliera** (`update-data.yml`): scarica notizie delle società, notizie di settore e indicatori macro in `data/`.
2. **Azure Static Web Apps** ospita l'app **e** la funzione `api/state`, che a ogni "salva" scrive i dati del team in `data/team.json` nel repository. Il token GitHub sta solo nelle impostazioni Azure, mai nel browser. L'accesso è un login Microsoft.
3. **Azione `azure-swa.yml`**: ripubblica l'app a ogni modifica e dopo ogni aggiornamento giornaliero dei dati (non per i salvataggi del team).

```
index.html                  l'app
config.js                   SYNC_URL="/api", SYNC_AUTH="azure"
staticwebapp.config.json    accesso: solo ruolo "team" (login Microsoft)
api/state/                  funzione Azure (ponte verso GitHub)
data/news.js industry.js macro.js   scritti dall'Action giornaliera
data/team.json              dati condivisi del team (scritto dalla funzione)
scripts/                    update_news.py, update_macro.py (solo libreria standard Python, nessuna chiave API)
.github/workflows/          update-data.yml, azure-swa.yml
```

## Aggiornare il DB (societa' e fondi)
Il DB sta in `data/db.xlsx` (fogli `Companies`, `Investors`, `Meta`); `index.html` lo legge all'apertura con SheetJS (`data/xlsx.full.min.js`). Per aggiornarlo basta sostituire `data/db.xlsx` nel repository (commit su `main`): `azure-swa.yml` ripubblica da solo.
- Non rinominare fogli e intestazioni di colonna. Si possono aggiungere righe; per le nuove societa' usare `id` nuovi (non riusare quelli esistenti: commenti e watchlist sono legati all'`id`).
- `Meta`: `asof` (mese del DB) e `dbv`. **Se cambi `dbv`, i dati utente (commenti, watchlist, contatti) vengono azzerati**: cambialo solo se vuoi ripartire da zero.
- `deal` e `flagV` sono testo `AAAA-MM`: in Excel formatta le colonne come Testo, altrimenti Excel le trasforma in date (l'app comunque le riconverte).
- In locale serve un server (`python -m http.server`): dal disco il browser blocca la lettura del file.

## Fonti dati (gratuite, senza chiave)
Google News RSS (notizie società e settore) · BCE Data Portal (Euribor, tasso depositi, BTP 10 anni, spread, EUR/USD) · Eurostat (PIL, inflazione) · FRED (Brent, gas europeo convertito in €/MWh).
PUN, PSV e PMI non hanno una fonte gratuita affidabile: si inseriscono a mano nella pagina Macro (il valore manuale sostituisce quello automatico della stessa data).

## Attivazione

### 0. Verifica dei permessi (5 minuti)
- **GitHub:** puoi creare un repository privato nell'organizzazione?
- **Azure:** su portal.azure.com, *Create a resource > Static Web App*: se riesci ad arrivare alla scelta del piano *Free*, hai i permessi. Altrimenti serve all'IT un ruolo *Contributor* su una subscription/resource group. Testo da girare all'IT: in fondo a questo file.

### 1. Repository
Crea il repository **privato** e carica questa cartella:
```
git remote add origin https://github.com/ORGANIZZAZIONE/REPOSITORY.git
git push -u origin main
```
*Settings > Actions > General > Workflow permissions > Read and write permissions.*

### 2. Token GitHub per la funzione
GitHub > Settings > Developer settings > *Fine-grained tokens* > Generate new token: repository **solo questo**, permesso *Contents: Read and write*. Copialo (`github_pat_…`).

### 3. Static Web App
Portale Azure > Create a resource > **Static Web App**:
- Piano **Free**, regione West Europe.
- *Deployment source*: **Other** (la pubblicazione la fa `azure-swa.yml`).
- Creata la risorsa: *Overview > Manage deployment token* > copia il token.

### 4. Segreti e impostazioni
- **GitHub** (repository > Settings > Secrets and variables > Actions): nuovo secret `AZURE_STATIC_WEB_APPS_API_TOKEN` = token del punto 3.
- **Azure** (Static Web App > *Environment variables* / *Configuration*): aggiungi `GH_TOKEN` = token del punto 2, `GH_REPO` = `organizzazione/repository`, `GH_BRANCH` = `main`.

### 5. Prima pubblicazione
GitHub > Actions > *Aggiorna dati* > Run workflow (riempie `data/`). A fine esecuzione parte da sola *Pubblica su Azure Static Web Apps*. Poi apri l'indirizzo `https://…azurestaticapps.net` mostrato in Azure.

### 6. Chi può entrare
Nel piano Free il login Microsoft accetta qualsiasi account Microsoft, quindi l'accesso si limita con gli **inviti**: Static Web App > *Role management* > *Invite*: provider *Azure Active Directory*, email del collega, ruolo `team`, scadenza. Il collega riceve un link e da quel momento accede. Limite: 25 utenti.
Con il piano **Standard** (circa 9 €/mese) si può invece limitare al tenant aziendale con una registrazione app Entra ID, senza inviti; in quel caso in `staticwebapp.config.json` si sostituisce il ruolo `team` con `authenticated`.

## Come funziona la sincronizzazione
- Dopo ogni salvataggio (commento, contatto, watchlist, override dell'exit score, dati macro manuali) l'app aspetta circa 1 secondo, legge lo stato da `/api/state`, **unisce** i dati e lo riscrive. Se un collega ha salvato nel frattempo, ripete con i dati aggiornati: nessun commento viene sovrascritto.
- Ogni 90 secondi (e al ritorno sulla pagina) rilegge i dati dei colleghi.
- Unione: commenti, notizie e ricerche si sommano; i contatti sono riconosciuti per nome, cognome e fondo; per "Cliente passato" e override vince la modifica più recente; ognuno è autore della propria watchlist; le eliminazioni si propagano.
- Il nome mostrato è l'email dell'account Microsoft.
- Ogni salvataggio è un commit su `data/team.json`: la cronologia di GitHub è backup e registro.
- Aprendo `index.html` dal disco (file locale) la sincronizzazione è spenta e i dati restano nel browser.

## Se non hai accesso ad Azure
- **Uso locale:** tutta la cartella su un percorso condiviso (SharePoint sincronizzato, rete); ognuno apre `index.html` dal disco. Notizie e macro si aggiornano con `python scripts/update_news.py` e `python scripts/update_macro.py`; commenti e contatti si scambiano con Esporta/Importa JSON nelle Impostazioni.
- **Nota:** SharePoint non può *ospitare* l'app (scarica gli HTML invece di eseguirli), serve solo come cartella o per mettere il link.

## Messaggio per l'IT (da copiare)
> Vorrei pubblicare un'app web interna (solo HTML/JS) su **Azure Static Web Apps, piano Free**, con funzione API integrata, accesso con login Microsoft. Mi serve un resource group con ruolo Contributor per creare la risorsa. Nessun database né dati sensibili dei clienti: contiene note interne del team. Il codice sta in un repository GitHub privato dell'organizzazione.

## Prova in locale
```
python scripts/update_macro.py
python scripts/update_news.py --days 3 --limit 20
```
Poi apri `index.html`.
