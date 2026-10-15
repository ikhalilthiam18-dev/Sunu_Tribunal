# Déploiement de SunuTribunal sur Railway

Trois services dans un même projet Railway : **PostgreSQL**, **backend** (Django) et **frontend** (React).
Chaque push sur `main` est redéployé automatiquement, après le passage de la CI GitHub.

## 1. Créer le projet

1. https://railway.com → *New Project* → *Deploy from GitHub repo* → choisir le dépôt SunuTribunal.
2. Dans le projet : *+ Create* → *Database* → *PostgreSQL*.

## 2. Service backend

*+ Create* → *GitHub Repo* → même dépôt, puis dans *Settings* :

| Réglage | Valeur |
|---|---|
| Root Directory | `backend` |
| Builder | Dockerfile (détecté automatiquement) |
| Networking → Generate Domain | ex. `sunutribunal-backend.up.railway.app` |
| Deploy → Wait for CI | activé |
| Healthcheck Path | `/admin/login/` |

**Volume** (clic droit sur le service → *Attach volume*) : point de montage `/app/media`
(sans volume, les scans envoyés disparaissent à chaque redéploiement).

**Variables** :

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (référence au service PostgreSQL) |
| `SECRET_KEY` | longue valeur aléatoire (voir commande ci-dessous) |
| `CORS_ORIGINS` | adresse du frontend, ex. `https://sunutribunal.up.railway.app` |
| `FRONTEND_URL` | la même adresse (liens dans les e-mails) |
| `GROQ_API_KEY` | clé Groq (assistants juridiques) |
| `BREVO_API_KEY` ou `EMAIL_HOST_USER` + `EMAIL_HOST_PASSWORD` | envoi des e-mails |
| `DEFAULT_FROM_EMAIL` | expéditeur des e-mails |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | SMS (facultatif) |
| `SMSGATE_LOGIN`, `SMSGATE_PASSWORD`, `BREVO_SMS_SENDER` | autres canaux SMS (facultatif) |
| `CODE_JURIDICTION` | ex. `TIDK` |

Générer une `SECRET_KEY` (PowerShell, dans `backend` avec le venv activé) :

```bat
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Ne pas définir `DEBUG` : il vaut `False` dès que `DATABASE_URL` est présente.

Au démarrage, `start.sh` crée les tables manquantes (`migrate auth` puis `migrate --run-syncdb`)
puis lance gunicorn sur le port fourni par Railway.

### Premier compte : le superutilisateur

Avec la [CLI Railway](https://docs.railway.com/guides/cli) (`npm i -g @railway/cli`), depuis le dossier du projet :

```bat
railway login
railway link
railway ssh --service backend
python manage.py createsuperuser
```

Puis, comme en local : https://…backend…/admin → créer le greffier en chef (rôle « admin ») avec son tribunal.

## 3. Service frontend

*+ Create* → *GitHub Repo* → même dépôt, puis :

| Réglage | Valeur |
|---|---|
| Root Directory | `frontend` |
| Networking → Generate Domain | ex. `sunutribunal.up.railway.app` |
| Deploy → Wait for CI | activé |

**Variable** : `VITE_API_URL` = `https://<domaine du backend>/api`.
Elle est intégrée au build : après l'avoir changée, redéployer le frontend.

Reporter ensuite l'adresse du frontend dans `CORS_ORIGINS` et `FRONTEND_URL` du backend.

## 4. Application Android (APK)

L'APK appelle l'adresse de `VITE_API_URL` au moment du build. Pour qu'elle utilise Railway au lieu de ngrok :

```bat
cd frontend
:: dans frontend\.env : VITE_API_URL=https://<domaine du backend>/api
npm run build
npx cap sync android
cd android
gradlew assembleDebug
```

## 5. Essai local de la configuration de production

Docker Desktop lancé, à la racine du projet (arrêter d'abord `runserver` et `npm run dev`, mêmes ports) :

```bat
docker compose up --build
```

Frontend : http://localhost:3000 — backend : http://localhost:8000/admin.
Superutilisateur : `docker compose exec backend python manage.py createsuperuser`.

## Limites connues

- Les scans ne sont jamais publics : l'API donne des liens signés valables 1 heure
  (`backend/sunutribunal/fichiers.py`), seulement à qui voit le dossier. Un lien copié reste
  utilisable par n'importe qui pendant cette heure. `/media/` est réservé aux comptes de Django Admin.
- Changer `SECRET_KEY` invalide tous les liens en cours (il suffit de recharger la page).
- SQLite local et PostgreSQL de production sont deux bases distinctes : les comptes créés en local
  ne sont pas copiés.
