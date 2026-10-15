# Déploiement gratuit de SunuTribunal (frontend et backend séparés)

En attendant le VPS (`docs/DEPLOIEMENT.md`), tout peut tourner gratuitement :

| Partie | Hébergeur gratuit | Adresse obtenue |
|---|---|---|
| Frontend React | **Cloudflare Pages** | `https://sunutribunal.pages.dev` |
| Backend Django + Django Admin | **Render** (Web Service gratuit, Docker) | `https://sunutribunal-api.onrender.com` |
| Base PostgreSQL | **Neon** (0,5 Go, sans expiration) | — |
| Scans (fichiers envoyés) | **Cloudflare R2** (10 Go, compartiment privé) | — |

Ordre conseillé : Neon → R2 → Render → Cloudflare Pages → UptimeRobot.

## Limites à connaître

- **Render gratuit s'endort après 15 min sans visite** ; la visite suivante attend ~1 minute.
  Parade : UptimeRobot (étape 5). Render offre 750 h/mois, assez pour un service toujours allumé.
- Le disque de Render est effacé à chaque redémarrage : c'est pour ça que la base est chez Neon
  et les scans chez R2. Ne jamais compter sur un fichier écrit sur le serveur Render.
- Neon gratuit : 0,5 Go et 100 h de calcul par mois, la base se met en veille après 5 min
  (réveil en moins d'une seconde). Suffisant pour une démo, pas pour un tribunal en activité.
- E-mails : utiliser **Brevo** (`BREVO_API_KEY`, passe par HTTPS) plutôt que Gmail SMTP.

## 1. Neon — base PostgreSQL

1. https://neon.com → créer un compte → *New Project* : nom `sunutribunal`, région la plus proche
   (Europe, ex. Frankfurt).
2. *Connect* → décocher **Connection pooling** → copier l'adresse
   `postgresql://…@…neon.tech/neondb?sslmode=require…` → ce sera `DATABASE_URL`.

## 2. Cloudflare R2 — scans

1. https://dash.cloudflare.com → créer un compte → *R2 Object Storage* → activer R2
   (Cloudflare peut demander un moyen de paiement, rien n'est facturé sous 10 Go).
2. *Create bucket* : `sunutribunal-scans`, **laisser l'accès public désactivé**.
3. *Manage R2 API Tokens* → *Create API token* : permission **Object Read & Write**, limité au
   compartiment `sunutribunal-scans`. Noter :
   - Access Key ID → `S3_ACCESS_KEY_ID`
   - Secret Access Key → `S3_SECRET_ACCESS_KEY` (affichée une seule fois)
   - l'adresse `https://<id-compte>.r2.cloudflarestorage.com` → `S3_ENDPOINT_URL`

## 3. Render — backend

1. https://render.com → compte avec GitHub → *New* → *Web Service* → dépôt `Sunu_Tribunal`.
2. Réglages :

   | Réglage | Valeur |
   |---|---|
   | Name | `sunutribunal-api` |
   | Language | Docker |
   | Root Directory | `backend` |
   | Instance Type | **Free** |
   | Health Check Path (*Advanced*) | `/admin/login/` |

3. Variables d'environnement (*Environment*) :

   | Variable | Valeur |
   |---|---|
   | `DATABASE_URL` | adresse Neon (étape 1) |
   | `SECRET_KEY` | longue valeur aléatoire (commande ci-dessous) |
   | `S3_BUCKET` | `sunutribunal-scans` |
   | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | étape 2 |
   | `CORS_ORIGINS` | `https://sunutribunal.pages.dev` (adresse de l'étape 4) |
   | `FRONTEND_URL` | la même adresse |
   | `GUNICORN_WORKERS` | `2` (512 Mo de mémoire en gratuit) |
   | `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_NOM` | premier compte (voir plus bas) |
   | `GROQ_API_KEY`, `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL`, `CODE_JURIDICTION` | comme en local |
   | `SMSGATE_LOGIN`, `SMSGATE_PASSWORD`, `TWILIO_*`, `BREVO_SMS_SENDER` | facultatif (SMS) |

   Ne pas définir `DEBUG` : il vaut `False` dès que `DATABASE_URL` est présente.

   Générer `SECRET_KEY` (**PC**, PowerShell, dans `backend` avec le venv activé) :

   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

4. *Create Web Service*. Le premier build prend quelques minutes ; les journaux (*Logs*) doivent
   finir par `Superutilisateur créé : …` puis `Listening at: http://0.0.0.0:…`.

**Premier compte** : Render gratuit n'a pas de terminal. Au démarrage, `start.sh` crée le
superutilisateur décrit par `DJANGO_SUPERUSER_*` s'il n'existe pas (mot de passe solide exigé).
Une fois connecté à `https://sunutribunal-api.onrender.com/admin`, **supprimer la variable
`DJANGO_SUPERUSER_PASSWORD`** dans Render (le compte reste). Puis créer le greffier en chef
(rôle « admin ») avec son tribunal, comme en local.

Chaque push sur `main` redéploie le backend automatiquement (*Auto-Deploy*).

## 4. Cloudflare Pages — frontend

1. https://dash.cloudflare.com → *Workers & Pages* → *Create* → *Pages* → *Connect to Git* →
   dépôt `Sunu_Tribunal`.
2. Réglages de build :

   | Réglage | Valeur |
   |---|---|
   | Project name | `sunutribunal` (→ `https://sunutribunal.pages.dev`) |
   | Framework preset | Vite (ou *None*) |
   | Root directory | `frontend` |
   | Build command | `npm run build` |
   | Build output directory | `dist` |

3. Variables (*Environment variables*, Production) :

   | Variable | Valeur |
   |---|---|
   | `VITE_API_URL` | `https://sunutribunal-api.onrender.com/api` |
   | `NODE_VERSION` | `22` |

4. *Save and Deploy*. Si l'adresse finale diffère de `sunutribunal.pages.dev`, la reporter dans
   `CORS_ORIGINS` et `FRONTEND_URL` sur Render.

Chaque push sur `main` redéploie aussi le frontend. Après un changement de `VITE_API_URL`,
relancer un déploiement (*Deployments* → *Retry deployment*).

## 5. UptimeRobot — garder le backend éveillé

https://uptimerobot.com → compte gratuit → *New monitor* : type HTTP(s),
URL `https://sunutribunal-api.onrender.com/admin/login/`, intervalle 5 minutes.
Vous êtes aussi prévenu par e-mail si le backend tombe.

## 6. Application Android (APK)

**PC** — dans `frontend\.env` : `VITE_API_URL=https://sunutribunal-api.onrender.com/api`, puis :

```bat
cd frontend
npm run build
npx cap sync android
cd android
gradlew assembleDebug
```

## 7. Nom de domaine (plus tard)

- Frontend : Cloudflare Pages → *Custom domains* → `sunutribunal.sn`.
- Backend : Render → *Settings* → *Custom Domains* → `api.sunutribunal.sn`, puis ajouter
  `api.sunutribunal.sn` à `ALLOWED_HOSTS` sur Render.
- Mettre à jour `CORS_ORIGINS`, `FRONTEND_URL` (Render) et `VITE_API_URL` (Pages, APK).

## Passer ensuite sur le VPS

Le code est le même. Exporter la base Neon (`pg_dump`) et la recharger sur le VPS
(`docs/DEPLOIEMENT.md`, section Sauvegardes). Les scans peuvent rester dans R2 : garder les
variables `S3_*` dans `.env.production`.
