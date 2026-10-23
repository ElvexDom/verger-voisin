# Installation de l'environnement sur le serveur (Docker)

Cette procédure met en place, sur le serveur (Ubuntu 26.04 LTS, Docker et Docker Compose déjà
installés), l'environnement de travail de Verger Voisin pour l'évaluation E1. Tout tourne dans des
conteneurs décrits par le fichier `compose.yaml` :

- **`postgres`** : la base de données PostgreSQL (image officielle), avec un volume persistant ;
- **`travail`** : l'environnement de travail (Python + Java + PySpark + les dépendances du projet),
  construit depuis le `Dockerfile` du dépôt. Le code est monté dans ce conteneur.

Rien d'autre que Docker n'est installé sur le serveur. Pourquoi : la compatibilité de PySpark avec
la version de Python du serveur (3.14.4) n'est pas confirmée ; l'image fixe elle-même ses versions
de Python et de Java. La procédure peut être suivie pas à pas, et rejouée sur une machine neuve
qui a Docker.

> **Statut** : les fichiers de cette procédure ont été écrits sans pouvoir être exécutés. Chaque
> étape indique le résultat attendu ; si tu observes autre chose, va à « Dépannage »
> (section 12) et note l'écart : il servira à corriger le script ou le document.

> **`sudo` et Docker** : tant que ton utilisateur n'est pas dans le groupe `docker`, les commandes
> `docker` se lancent avec `sudo` (`sudo docker ...`). Les commandes de ce document sont écrites
> avec `sudo`. Les scripts `scripts/installer.sh` et `scripts/verifier.sh` s'en occupent seuls :
> **lance-les sans `sudo`**, ils appellent `sudo` à l'intérieur quand c'est nécessaire.

## 1. Les objets techniques attendus

À la fin de la procédure, le serveur doit contenir ces objets. Chacun se vérifie par une commande,
à lancer depuis la racine du dépôt cloné. `<POSTGRES_USER>` et `<POSTGRES_DB>` sont les valeurs de
ton `.env`.

| # | Objet technique | Commande de vérification | Résultat attendu |
|---|---|---|---|
| 1 | Dépôt cloné et à jour | `git status` | `On branch main` et `nothing to commit` |
| 2 | Fichier `.env` rempli, ignoré par Git | `git status --short` | le `.env` n'apparaît pas |
| 3 | Docker installé et actif | `docker --version` puis `systemctl is-active docker` | une version de Docker, puis `active` |
| 4 | Docker Compose installé | `docker compose version` | une version de Compose s'affiche |
| 5 | Image de l'environnement de travail construite | `sudo docker image ls verger-voisin-travail` | une ligne avec l'étiquette `local` |
| 6 | Python dans l'image | `sudo docker compose run --rm --no-deps -T travail python --version` | `Python 3.12.x` (version de `IMAGE_PYTHON`) |
| 7 | Java dans l'image | `sudo docker compose run --rm --no-deps -T travail java -version` | une version de Java s'affiche (21 si `JAVA_PAQUET` n'a pas changé) |
| 8 | PySpark et dépendances dans l'image | `sudo docker compose run --rm --no-deps -T travail pip list` | `pyspark`, `SQLAlchemy`, `psycopg`, `fastapi`, `pydantic`, `uvicorn`, `requests`, `pytest` dans la liste |
| 9 | Conteneur PostgreSQL démarré et en bonne santé | `sudo docker compose ps` | le service `postgres` est `Up` avec `(healthy)` |
| 10 | Base non publiée sur le serveur | `sudo docker compose ps` puis `ss -ltn` | la colonne `PORTS` de `postgres` affiche `5432/tcp` **sans** `->` ; `ss -ltn` ne montre aucun port 5432 |
| 11 | Volume persistant de la base | `sudo docker volume ls` | `verger-voisin_donnees_postgres` dans la liste |
| 12 | Base et utilisateur créés (noms du `.env`) | `sudo docker compose exec postgres psql -U <POSTGRES_USER> -d postgres -c "\l"` puis `... -c "\du"` | ta base et ton utilisateur sont listés |
| 13 | Conteneur de travail non root | `sudo docker compose run --rm --no-deps -T travail id` | `uid=` suivi d'un nombre différent de 0, utilisateur `verger` |
| 14 | Dossiers de données et de journaux | `ls <DONNEES_HOTE>` | `export  parquet  sorties` |
| 15 | Contrôle de bon fonctionnement (PostgreSQL joint par le réseau avec le mot de passe, Spark, API) | `bash scripts/verifier.sh` | `RÉSULTAT GLOBAL : OK (3 vérifications sur 3)` |

## 2. Hypothèses à vérifier sur le serveur

Les versions et étiquettes ci-dessous étaient les **hypothèses de départ** ; elles ont été
vérifiées sur le serveur le 2026-10-20 (voir `docs/justifications.md`). Elles sont écrites dans
des variables du `.env` pour être changées sans toucher au code.

| Hypothèse | Pourquoi elle compte | Comment la vérifier |
|---|---|---|
| Docker 29.9.1 et Docker Compose v5.6.0 sont installés et actifs sur Ubuntu 26.04.1 LTS | constaté sur le serveur le 2026-10-20 ; tout en dépend | objets 3 et 4 du tableau ; `lsb_release -d` |
| L'option `docker compose up --wait` (attendre qu'un service soit en bonne santé) existe dans cette version de Compose | le script d'installation l'utilise | `docker compose up --help` doit lister `--wait` |
| L'étiquette `postgres:17-bookworm` (variable `IMAGE_POSTGRES`) existe sur Docker Hub | sans elle, la base ne démarre pas | `sudo docker pull postgres:17-bookworm` ; sinon chercher une étiquette existante sur la page Docker Hub de l'image `postgres` |
| PostgreSQL 17 convient (version majeure choisie en hypothèse) | un changement de version majeure demande une migration des données | `sudo docker compose exec postgres postgres --version` |
| L'étiquette `python:3.12-slim-trixie` (variable `IMAGE_PYTHON`) existe sur Docker Hub | sans elle, l'image de travail ne se construit pas | `sudo docker pull python:3.12-slim-trixie` |
| Le paquet `openjdk-21-jre-headless` (variable `JAVA_PAQUET`) existe dans le système de cette image | sinon la construction échoue à l'étape `apt-get install` | au message d'erreur de la construction ; ou `sudo docker run --rm python:3.12-slim-trixie sh -c "apt-get update -qq && apt-cache policy openjdk-21-jre-headless"` |
| La version de PySpark installée par pip accepte **Python 3.12** et **Java 21** | PySpark ne démarre pas avec une version de Java ou de Python qu'il ne gère pas | version de PySpark : objet 8 ; comparer avec la page « Installation » / « Requirements » de la documentation de cette version. Hypothèse de travail non vérifiée : les versions récentes de PySpark acceptent Python 3.12 et Java 21 |
| Les paquets de `requirements.txt` (sans version fixée) ont des versions installables avec Python 3.12 | pip refuse un paquet incompatible | erreurs de `pip install` pendant la construction |
| Dans l'image officielle `postgres`, la connexion locale du conteneur (`psql` lancé par `docker compose exec`) ne demande pas de mot de passe | le script d'installation s'en sert pour resynchroniser le mot de passe et créer la base | si le script échoue à l'étape « mot de passe », voir « Dépannage » |
| Le conteneur de travail a accès à Internet (réseau Docker par défaut, translation d'adresses) | l'appel à l'API Open Food Facts en dépend | contrôle, vérification 3 |
| L'API Open Food Facts répond à `OFF_API_BASE_URL` + `/api/v2/product/<code-barres>` avec un JSON contenant `status` = 1 et `product` | le contrôle repose sur ce format | vérifié le 2026-10-19 (HTTP 200, `status` = 1, objet `product`) ; en cas d'écart, documentation officielle de l'API Open Food Facts |
| Ton utilisateur du serveur a les droits `sudo` (ou est dans le groupe `docker`) | les commandes Docker en dépendent | `sudo -v` ou `groups` |

## 3. Le circuit du code (rappel)

Les fichiers sont écrits sur le poste de ElvexDom, poussés sur GitHub, puis récupérés sur le serveur.
Le serveur ne reçoit **rien** tant que tu n'as pas fait `git push` (poste) puis `git pull`
(serveur). Détail dans le `README.md`, section « Le circuit ».

## 4. Étape 0 : vérifier Docker

```bash
docker --version
docker compose version
systemctl is-active docker
```

*Résultat attendu* : une version de Docker (29.9.1 au 2026-10-20), une version de Compose
(v5.6.0 au 2026-10-20), puis `active`.

*Si ça échoue* : `docker: command not found` -> Docker n'est pas installé : l'installation de
Docker sur le serveur n'est pas faite par ce dépôt : installer Docker et Docker Compose avant de
continuer. `inactive` -> `sudo systemctl
start docker`.

Pour savoir si tu as besoin de `sudo` : `docker ps`. Si la réponse est `permission denied while
trying to connect to the Docker daemon socket`, ton utilisateur n'est pas dans le groupe `docker` :
utilise `sudo docker ...` (ajouter l'utilisateur au groupe `docker` donne un accès équivalent à
root, ce n'est pas fait par ce dépôt).

## 5. Étape 1 : récupérer le dépôt sur le serveur

Connexion au serveur : depuis ton poste, `ssh <utilisateur>@<adresse-du-serveur>` (les valeurs sont
celles de ton serveur).

**Première fois** (le dépôt est public, aucun identifiant n'est nécessaire pour le lire) :

```bash
git clone https://github.com/ElvexDom/verger-voisin.git
cd verger-voisin
```

*Résultat attendu* : `Cloning into 'verger-voisin'...` puis un dossier `verger-voisin` qui contient
`README.md`, `compose.yaml`, `Dockerfile`, `.env.example`, `requirements.txt`, `docs/`, `scripts/`...

**Les fois suivantes** (après un `git push` depuis ton poste) :

```bash
cd verger-voisin
git pull
```

*Résultat attendu* : `Already up to date.` ou la liste des fichiers mis à jour.

*Si ça échoue* : `git: command not found` -> `sudo apt-get install -y git`. `repository not found`
-> vérifie le nom du compte, l'orthographe, et que le dépôt est bien public. `Could not resolve
host` -> le serveur n'a pas accès à Internet (voir « Dépannage »).

## 6. Étape 2 : créer et remplir le `.env`

```bash
cp .env.example .env
nano .env
```

(Si tu sautes cette étape, `bash scripts/installer.sh` crée le `.env` à ta place, puis s'arrête
pour que tu le remplisses.)

*Résultat attendu* : un fichier `.env` est ouvert dans l'éditeur. Remplis les variables selon le
tableau ci-dessous, enregistre (`Ctrl+O`, Entrée), quitte (`Ctrl+X`).

| Variable | À mettre | Obligatoire pour |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `verger-voisin` (déjà rempli) : préfixe des conteneurs, du réseau et des volumes | Docker |
| `IMAGE_POSTGRES` | `postgres:17-bookworm` (déjà rempli, **à vérifier**, section 2) | Docker |
| `IMAGE_PYTHON` | `python:3.12-slim-trixie` (déjà rempli, **à vérifier**, section 2) | Docker |
| `JAVA_PAQUET` | `openjdk-21-jre-headless` (déjà rempli, **à vérifier**, section 2) | Docker |
| `IMAGE_TRAVAIL` | `verger-voisin-travail:local` (déjà rempli) : nom de l'image construite | Docker |
| `CONTENEUR_UID`, `CONTENEUR_GID` | **vides** : le script d'installation les remplit avec ceux de ton utilisateur (`id -u`, `id -g`) | Docker |
| `POSTGRES_DB` | le nom de la base que tu choisis (minuscules, chiffres, `_`) | installation, contrôle |
| `POSTGRES_USER` | le nom de l'utilisateur que tu choisis (mêmes règles) | installation, contrôle |
| `POSTGRES_PASSWORD` | un mot de passe long, généré par ton gestionnaire de mots de passe, avec seulement des lettres, des chiffres et les symboles `. _ + = : , -` (pas de `$`, de guillemets, de `#` ni d'espace) | installation, contrôle |
| `POSTGRES_PORT_HOTE` | vide, sauf si tu utilises `compose.acces-hote.yaml` (section 14) | facultatif |
| `SPARK_DRIVER_MEMORY` | la limite de mémoire de Spark, par exemple `2g` pour un premier essai (simple exemple de format : la répartition de la mémoire entre Spark, PostgreSQL et l'API reste à décider après essais) | contrôle |
| `SPARK_NB_COEURS` | vide (tous les cœurs) ou un nombre | facultatif |
| `OFF_API_BASE_URL` | l'adresse de base de l'API Open Food Facts : déjà préremplie dans `.env.example` (`https://world.openfoodfacts.org`, vérifiée le 2026-10-19), à laisser telle quelle | contrôle |
| `OFF_APP_NOM` | le nom de l'application, par exemple `VergerVoisin` | contrôle |
| `OFF_APP_LIEN_DEPOT` | le lien complet de ton dépôt GitHub public | contrôle |
| `OFF_CODE_BARRES_TEST` | le code-barres (chiffres) d'un produit connu d'Open Food Facts : déjà prérempli dans `.env.example` (`3017620422003`, produit trouvé par l'API le 2026-10-19), à laisser tel quel ou à remplacer par un autre code-barres connu | contrôle |
| `DONNEES_HOTE` | un chemin absolu **hors du dépôt**, par exemple `/home/<utilisateur>/verger-voisin-donnees` ; par défaut `./donnees` (dossier du dépôt dont le contenu est ignoré par Git). N'utilise pas `~` | installation |
| `JOURNAUX_HOTE` | par défaut `./journaux` (ignoré par Git) ou un chemin absolu | installation |
| `LOG_LEVEL`, `LOG_FORMAT` | déjà remplis (`INFO`, `texte`) | journalisation |

Règles du fichier : une variable par ligne, `NOM=valeur`, sans espace autour du `=`, sans
commentaire sur la même ligne qu'une valeur, sans guillemets ni `$`.

Dans le conteneur de travail, la base est jointe par le nom du service Compose (`postgres`) et son
port interne (5432) : `POSTGRES_HOST` et `POSTGRES_PORT` sont réglés dans `compose.yaml`, pas dans
le `.env`. De même, dans le conteneur, les dossiers de données et de journaux s'appellent toujours
`/donnees` et `/journaux`.

**User-Agent d'Open Food Facts** : le contrôle l'écrit sous la forme `OFF_APP_NOM (OFF_APP_LIEN_DEPOT)`.
N'y mets **aucune adresse e-mail** : ce serait une donnée personnelle. Le contrôle refuse un `@`.

Vérifie ensuite que Git ignore bien ce fichier :

```bash
git status --short
```

*Résultat attendu* : aucune ligne ne mentionne `.env`. *Si `.env` apparaît* : **ne commite pas** ;
vérifie que le fichier s'appelle exactement `.env` (pas `.env.txt`) et que `.gitignore` n'a pas
été modifié.

## 7. Étape 3 : lancer l'installation

```bash
bash scripts/installer.sh
```

**Sans `sudo`** devant : si ton utilisateur n'est pas dans le groupe `docker`, le script demande
ton mot de passe `sudo` lui-même, une fois. Il enchaîne : vérification de Docker, lecture du
`.env`, création des dossiers, construction de l'image de travail, démarrage de la base,
synchronisation du mot de passe, récapitulatif. Il affiche `[INFO]`, `[ OK ]`, `[ATTENTION]` ou
`[ERREUR]` à chaque étape.

*Résultat attendu* (extrait, dans cet ordre) :

```
=== Installation de Verger Voisin (Docker) ===
[ OK ]      Système : Ubuntu 26.04...
[ OK ]      Docker version ...
[ OK ]      Docker Compose version ...
[ OK ]      Fichier .env lu (droits restreints à ton utilisateur).
[ OK ]      Utilisateur du conteneur de travail : uid ..., gid ....
[ OK ]      Dossier des données : ... (sous-dossiers export, parquet, sorties)
[ OK ]      compose.yaml est valide.
[ OK ]      Image de travail construite (ou déjà à jour).
[ OK ]      PostgreSQL répond (conteneur « postgres » en bonne santé).
[ OK ]      Le mot de passe de l'utilisateur « ... » est synchronisé avec le .env.
[ OK ]      Base « ... » créée (propriétaire : ...).    <- ou « existe : elle n'est pas touchée »
=== Récapitulatif (versions réellement installées dans les conteneurs) ===
[ OK ]      Installation terminée.
```

Le récapitulatif affiche les versions de Python, Java, PySpark et PostgreSQL réellement présentes
dans les conteneurs : **note-les**, elles servent à vérifier les hypothèses de la section 2, à
l'étape 7 et au rapport.

La première construction de l'image télécharge l'image de base, Java et PySpark (volumineux) : elle
peut prendre plusieurs minutes. Les suivantes réutilisent le cache de Docker et sont rapides.

*Si ça échoue* : le script s'arrête à la première erreur et indique la ligne concernée. Corrige la
cause (voir « Dépannage »), puis relance la même commande : elle reprend sans rien détruire.

Le script ne supprime jamais rien : ni conteneur, ni volume, ni dossier, ni donnée.

## 8. Étape 4 : vérifier chaque objet technique

Lance les commandes du tableau de la section 1 (objets 5 à 14) et compare avec le résultat
attendu. Pour l'objet 10 : `sudo docker compose ps` doit afficher pour `postgres` une colonne
`PORTS` du type `5432/tcp` (port interne au conteneur), jamais `0.0.0.0:5432->5432/tcp`.

*Si un objet n'est pas conforme* : relance `bash scripts/installer.sh`, puis consulte « Dépannage ».

## 9. Étape 5 : lancer le contrôle de bon fonctionnement

```bash
bash scripts/verifier.sh
```

C'est la seule commande du contrôle. Elle exécute `scripts/verification.py` **dans le conteneur de
travail** (équivalent à la main : `sudo docker compose run --rm -T travail python
scripts/verification.py`). Elle lance trois vérifications, **toutes exécutées même si l'une
échoue** :

1. **PostgreSQL** : connexion par le réseau Docker (hôte `postgres`) avec les identifiants du
   `.env`, requête `SELECT 1`.
2. **Spark** : session locale avec la limite `SPARK_DRIVER_MEMORY`, une opération simple
   (compter 1000 lignes), arrêt de la session. La limite appliquée est affichée.
3. **Open Food Facts** : un seul appel à l'API, avec le User-Agent construit depuis le `.env`.

*Résultat attendu* :

```
=== Contrôle de bon fonctionnement de Verger Voisin ===
Journal : /journaux/verification.log
[1/3] PostgreSQL ...
      OK : connexion établie à la base « ... » (utilisateur « ... »), requête « SELECT 1 » réussie (0.1 s)
[2/3] Spark (mode local) ...
      OK : session Spark démarrée en mode local[*], limite de mémoire appliquée : 2g ... (x.x s)
[3/3] API Open Food Facts ...
      OK : un appel à l'API, statut HTTP 200, JSON valide, produit trouvé (x.x s)

RÉSULTAT GLOBAL : OK (3 vérifications sur 3)
```

(Les durées et les noms varient. `/journaux` est le nom du dossier dans le conteneur ; sur le
serveur, c'est `JOURNAUX_HOTE`.) Le code de sortie est `0` si tout est OK, `1` sinon : `echo $?`
juste après la commande l'affiche. En cas d'échec, le script écrit `ÉCHEC` sous la vérification
concernée, indique la cause, puis termine avec le code `1`. Aucun mot de passe n'est affiché ni
écrit dans le journal.

Le journal du contrôle est dans `verification.log`, dans le dossier `JOURNAUX_HOTE` du serveur
(`journaux/` du dépôt par défaut), avec une ligne datée par vérification :
`cat journaux/verification.log`. Ce fichier est ignoré par Git.

Spark peut afficher des avertissements (`WARN`) au démarrage : ils sont normaux tant que le
résultat final est `OK`.

## 10. Étape 6 : prouver que l'installation est relançable

```bash
bash scripts/installer.sh
```

*Résultat attendu* : le script se termine sans erreur, avec des messages du type « La base ...
existe : elle n'est pas touchée » et « Image de travail construite (ou déjà à jour) ». Aucune
donnée n'est supprimée ; les conteneurs déjà en route ne sont pas recréés s'ils n'ont pas changé.
Seul le mot de passe de l'utilisateur de la base est remis à la valeur du `.env`.

## 11. Étape 7 : versions figées et mise à jour

Les versions sont figées depuis le 2026-10-20, après un contrôle réussi sur le serveur :

- **images** : `IMAGE_POSTGRES=postgres:17.11-bookworm` et
  `IMAGE_PYTHON=python:3.12.15-slim-trixie` dans `.env` ;
- **dépendances directes** : versions exactes dans `requirements.txt` et `requirements-dev.txt` ;
- **toutes les dépendances, indirectes comprises** : `requirements-verrou.txt`, utilisé comme
  fichier de contraintes par le `Dockerfile`.

Reconstruire l'image redonne donc exactement le même environnement.

Pour mettre à jour une dépendance : change sa version dans `requirements.txt`, reconstruis l'image
sans le verrou, relance le contrôle et les tests, puis régénère le verrou :

```bash
sudo docker compose run --rm --no-deps -T travail pip freeze > requirements-verrou.txt
```

*Résultat attendu* : une ligne `paquet==version` par paquet. Remets en tête du fichier le
commentaire explicatif, puis commite-le. Aucun secret n'y figure.

## 12. Dépannage

| Symptôme | Cause probable | Que faire |
|---|---|---|
| `[ERREUR] Ne lance pas ce script en root ni avec sudo` | script lancé avec `sudo` | relancer sans `sudo` : `bash scripts/installer.sh` |
| `La commande docker est introuvable` | Docker absent | installer Docker et Docker Compose (hors du périmètre de ce dépôt), puis relancer |
| `permission denied while trying to connect to the Docker daemon socket` (commande lancée à la main) | utilisateur hors du groupe `docker` | ajouter `sudo` devant la commande |
| `Le démon Docker ne répond pas` | service arrêté | `sudo systemctl status docker` puis `sudo systemctl start docker` |
| `Variable(s) vide(s) dans .env` | `.env` pas rempli | éditer `.env` (`nano .env`) puis relancer |
| `POSTGRES_DB doit contenir seulement des minuscules...` | nom de base ou d'utilisateur non conforme | choisir un nom en minuscules, chiffres et `_` |
| `POSTGRES_PASSWORD ne doit contenir que des lettres...` | symbole que Docker Compose lirait de travers | choisir un mot de passe avec lettres, chiffres et `. _ + = : , -` seulement |
| `variable is not set` / `... est vide dans .env` au lancement de `docker compose` | `.env` absent ou incomplet à la racine du dépôt | commande lancée depuis un autre dossier, ou `.env` à remplir |
| Construction : `manifest for ... not found` / `pull access denied` | étiquette d'image inexistante | corriger `IMAGE_PYTHON` ou `IMAGE_POSTGRES` dans `.env` (section 2), relancer |
| Construction : `Unable to locate package openjdk-...` | paquet Java absent de ce système | corriger `JAVA_PAQUET` dans `.env` (liste dans l'image : `sudo docker run --rm <IMAGE_PYTHON> sh -c "apt-get update -qq && apt-cache search openjdk"`), relancer |
| Construction : erreur de `pip` (`No matching distribution`, version de Python) | paquet incompatible avec le Python de l'image | lire le message ; essayer une autre étiquette `IMAGE_PYTHON` ; noter la version |
| Construction : `useradd: UID ... is not unique` | un utilisateur de l'image a déjà cet identifiant | indiquer d'autres `CONTENEUR_UID` / `CONTENEUR_GID` dans `.env` (non nuls) : attention, ils doivent pouvoir écrire dans les dossiers `DONNEES_HOTE` et `JOURNAUX_HOTE` |
| `dependency failed to start: container ... is unhealthy` ou attente dépassée | la base ne démarre pas | `sudo docker compose logs postgres` |
| Étape « mot de passe » : `role "..." does not exist` | le volume de la base a été créé avec un autre `POSTGRES_USER` | remettre dans `.env` le nom d'utilisateur de la première installation. Le script ne supprime jamais de volume ; supprimer le volume (donc la base) est ta décision, avec une sauvegarde |
| Étape « mot de passe » : `password authentication failed` | l'image n'accepte pas la connexion locale sans mot de passe (hypothèse de la section 2 fausse) | `sudo docker compose logs postgres` ; ouvrir un ticket d'incident décrivant l'écart |
| Contrôle, PostgreSQL : `ÉCHEC ... password authentication failed` | mot de passe du `.env` différent de celui de la base | relancer `bash scripts/installer.sh` (il resynchronise le mot de passe) |
| Contrôle, PostgreSQL : `ÉCHEC ... could not translate host name "postgres"` ou `Connection refused` | base arrêtée ou conteneur de travail hors du réseau du projet | `sudo docker compose ps` ; relancer `bash scripts/installer.sh` |
| Contrôle, Spark : `Java est introuvable` | image sans Java | reconstruire : `bash scripts/installer.sh` ; `... travail java -version` |
| Contrôle, Spark : `JAVA_GATEWAY_EXITED` ou erreur Java | Java incompatible avec PySpark, ou mémoire trop grande | comparer les versions (section 2) ; baisser `SPARK_DRIVER_MEMORY` ; `free -h` pour voir la mémoire libre |
| Contrôle, Spark : `format invalide` | `SPARK_DRIVER_MEMORY` mal écrite | un nombre et une unité : `512m`, `2g` |
| Contrôle : `Permission denied` sur `/journaux` | le dossier `JOURNAUX_HOTE` n'appartient pas à l'utilisateur du conteneur | `ls -ln <JOURNAUX_HOTE>` : le propriétaire doit être `CONTENEUR_UID` ; ne pas créer ce dossier avec `sudo` |
| Contrôle, Open Food Facts : variable vide / `@` refusé | `.env` incomplet ou adresse e-mail dans le User-Agent | corriger `OFF_*` dans `.env` |
| Contrôle, Open Food Facts : erreur de connexion ou statut HTTP 4xx/5xx | pas de réseau dans le conteneur, adresse erronée, ou service indisponible | `curl -I <OFF_API_BASE_URL>` depuis le serveur ; vérifier l'adresse ; réessayer plus tard (ne pas enchaîner les essais : limites de débit inconnues) |
| Contrôle, Open Food Facts : `pas la forme attendue` | code-barres inconnu d'Open Food Facts, ou format de l'API modifié depuis la vérification du 2026-10-19 | remettre le code-barres prérempli dans `.env.example` (`3017620422003`) ou en essayer un autre ; si l'écart persiste, relire la documentation de l'API |

## 13. Commandes utiles

Toutes depuis la racine du dépôt, avec `sudo` tant que ton utilisateur n'est pas dans le groupe
`docker`.

| Besoin | Commande |
|---|---|
| Voir l'état des conteneurs | `sudo docker compose ps` |
| Voir les messages de la base | `sudo docker compose logs postgres` |
| Ouvrir une console SQL | `sudo docker compose exec postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB>` |
| Lancer les tests automatisés | `sudo docker compose run --rm -T travail python -m pytest` |
| Ouvrir un terminal dans le conteneur de travail | `sudo docker compose run --rm travail bash` |
| Arrêter la base (les données restent) | `sudo docker compose stop postgres` |
| Redémarrer la base | `sudo docker compose up -d postgres` |

**À ne pas faire sans décision explicite** : `docker compose down -v`, `docker volume rm` et
`docker system prune --volumes` effacent le volume de la base, donc toutes ses données.
`docker compose down` (sans `-v`) supprime les conteneurs mais garde les données.

## 14. Accès à la base depuis ton poste (facultatif)

Par défaut, PostgreSQL n'est publié nulle part : seuls les conteneurs du projet le joignent. Pour
l'interroger depuis ton poste, publie-le **seulement sur l'interface locale du serveur
(`127.0.0.1`)**, puis passe par un tunnel SSH, sans rien ouvrir sur Internet :

```bash
sudo docker compose -f compose.yaml -f compose.acces-hote.yaml up -d postgres
```

Le port local du serveur est `POSTGRES_PORT_HOTE` (5432 si vide). Depuis ton poste :

```bash
ssh -L <PORT_LOCAL>:127.0.0.1:<PORT_HOTE> <utilisateur>@<adresse-du-serveur>
```

Choisis un `<PORT_LOCAL>` libre sur ton poste ; ensuite, ton outil se connecte à
`localhost:<PORT_LOCAL>`. Pour revenir à l'état par défaut (base non publiée) :
`sudo docker compose up -d postgres`. Le durcissement complet du serveur (pare-feu, SSH) est hors
de ce lot.

## 15. Données personnelles et journaux (pour le registre de la base, C4)

- Le User-Agent envoyé à Open Food Facts contient le nom de l'application et le lien du dépôt
  public, **sans adresse e-mail**.
- Les journaux ne contiennent ni mot de passe, ni jeton, ni donnée personnelle (règle du projet).
  Un filtre masque en plus la valeur des variables secrètes si l'une d'elles apparaissait.
- Le `.env` est lisible seulement par ton utilisateur (le script fait `chmod 600`). Le mot de passe
  de la base est transmis aux conteneurs en variable d'environnement : il est visible par un
  administrateur du serveur avec `docker inspect`.
- L'image Docker ne contient ni le `.env` ni les données (`.dockerignore` n'envoie à Docker que les
  fichiers de dépendances).

## 16. Ce qui n'est pas dans ce lot

Sauvegarde de la base, téléchargement de l'export Open Food Facts, scripts d'extraction,
d'agrégation et d'import, schéma de la base, API, durcissement du serveur, limites de mémoire des
conteneurs : lots suivants.
