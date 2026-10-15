# Déploiement de SunuTribunal sur le VPS OVHcloud (Ubuntu 24.04)

Tout tourne avec Docker sur le VPS (`docker-compose.prod.yml`) :

| Service | Rôle |
|---|---|
| `caddy` | Porte d'entrée HTTPS (certificats Let's Encrypt automatiques), seuls ports ouverts : 80 et 443 |
| `frontend` | Site React — `https://DOMAINE` |
| `backend` | API Django + Django Admin — `https://api.DOMAINE` |
| `db` | PostgreSQL 17 (interne, jamais exposé) |
| `sauvegarde` | Sauvegarde quotidienne de la base et des scans, 14 jours gardés |

Les commandes marquées **PC** se tapent dans PowerShell sur Windows ; celles marquées **VPS**
se tapent sur le serveur, après connexion SSH (c'est un serveur Linux).

## 1. Connexion SSH par clé

OVHcloud envoie par e-mail l'adresse IP du VPS et l'utilisateur (`ubuntu`).

**PC** — créer une clé (une seule fois, Entrée pour les valeurs par défaut) puis l'envoyer au VPS :

```powershell
ssh-keygen -t ed25519
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh ubuntu@IP_DU_VPS "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
ssh ubuntu@IP_DU_VPS
```

Le mot de passe de l'e-mail n'est demandé qu'une fois ; ensuite la clé suffit.

## 2. Sécuriser le serveur

**VPS** :

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y unattended-upgrades fail2ban     # mises à jour de sécurité auto + anti force brute
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
sudo ufw enable
```

Puis, **après avoir vérifié que la connexion par clé marche**, interdire les mots de passe SSH :

```bash
echo "PasswordAuthentication no" | sudo tee /etc/ssh/sshd_config.d/99-sunutribunal.conf
sudo systemctl restart ssh
```

## 3. Installer Docker

**VPS** :

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit
```

Se reconnecter (`ssh ubuntu@IP_DU_VPS`) pour que le groupe `docker` soit pris en compte.

## 4. Récupérer le projet et le configurer

**VPS** :

```bash
git clone https://github.com/ndkhady49-cpu/Sunu_Tribunal.git sunutribunal
cd sunutribunal
cp .env.production.example .env.production
chmod 600 .env.production
openssl rand -hex 24                       # → POSTGRES_PASSWORD
openssl rand -base64 48 | tr -d '\n'; echo # → SECRET_KEY
nano .env.production                       # remplir DOMAINE, EMAIL_ADMIN, les deux secrets, les clés
```

Raccourci pratique pour la suite :

```bash
echo "alias dcp='docker compose -f docker-compose.prod.yml --env-file .env.production'" >> ~/.bashrc
source ~/.bashrc
```

## 5. Nom de domaine (DNS)

Chez le bureau d'enregistrement du domaine, créer deux enregistrements **A** vers l'IP du VPS :

| Nom | Type | Valeur |
|---|---|---|
| `@` (le domaine lui-même) | A | IP du VPS |
| `api` | A | IP du VPS |

**Avant l'achat du domaine**, on peut déjà tout tester avec sslip.io (gratuit, HTTPS compris) :
`DOMAINE=51-75-12-34.sslip.io` pour l'IP `51.75.12.34` → site sur `https://51-75-12-34.sslip.io`,
API sur `https://api.51-75-12-34.sslip.io`.

## 6. Lancer

**VPS** (dans `~/sunutribunal`) :

```bash
dcp up -d --build
dcp ps                 # tous les services « Up »
dcp logs -f caddy      # obtention des certificats (Ctrl+C pour quitter)
dcp exec backend python manage.py createsuperuser
```

Puis `https://api.DOMAINE/admin` → créer le greffier en chef (rôle « admin ») avec son tribunal.

## 7. Mettre à jour après un push sur GitHub

Vérifier d'abord que la CI GitHub est verte, puis **VPS** :

```bash
cd ~/sunutribunal && git pull && dcp up -d --build
```

Les tables manquantes sont créées au démarrage du backend (`backend/start.sh`).

## 8. Sauvegardes

- Automatiques chaque jour dans `~/sunutribunal/sauvegardes/` : `base_*.sql.gz` (PostgreSQL)
  et `scans_*.tar.gz` (fichiers envoyés). Vérifier : `dcp logs sauvegarde`.
- **Une sauvegarde sur le même serveur ne protège pas d'une panne du serveur.** Copier
  régulièrement sur le PC (**PC**) :

  ```powershell
  scp "ubuntu@IP_DU_VPS:sunutribunal/sauvegardes/*" C:\Users\PC\Documents\SauvegardesSunuTribunal\
  ```

- Activer aussi l'option « Backup automatique » du VPS dans l'espace client OVHcloud.

Restaurer une base (**VPS**, efface les données actuelles) :

```bash
dcp stop backend
dcp exec -T db dropdb -U sunutribunal sunutribunal
dcp exec -T db createdb -U sunutribunal sunutribunal
gunzip -c sauvegardes/base_AAAA-MM-JJ_HHMM.sql.gz | dcp exec -T db psql -q -U sunutribunal -d sunutribunal
dcp start backend
```

## 9. Application Android (APK)

**PC** — dans `frontend\.env` : `VITE_API_URL=https://api.DOMAINE/api`, puis :

```bat
cd frontend
npm run build
npx cap sync android
cd android
gradlew assembleDebug
```

## 10. Essai local de la configuration de production

`docker-compose.yml` (sans HTTPS) : Docker Desktop lancé, à la racine du projet, après avoir arrêté
`runserver` et `npm run dev` (mêmes ports) : `docker compose up --build`, puis http://localhost:3000.

## Limites connues

- Les scans ne sont jamais publics : l'API donne des liens signés valables 1 heure
  (`backend/sunutribunal/fichiers.py`), seulement à qui voit le dossier. Un lien copié reste
  utilisable par n'importe qui pendant cette heure. `/media/` est réservé aux comptes de Django Admin.
- Changer `SECRET_KEY` invalide tous les liens en cours (il suffit de recharger la page).
- Le VPS est hébergé dans le centre de données OVHcloud choisi à la commande, hors du Sénégal :
  si une juridiction exige un hébergement au Sénégal, il faudra migrer (la même configuration
  Docker fonctionne sur tout serveur Linux).
