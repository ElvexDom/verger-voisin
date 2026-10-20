# Verger Voisin

Application qui, pour un produit alimentaire donné, propose des substituts proches mais mieux
notés nutritionnellement, à partir des données d'Open Food Facts.

**Verger Voisin est une enseigne de magasins bio de proximité fictive**, inventée pour ce projet
de formation en Data et IA. Aucune donnée d'une entreprise ou d'un client réel n'est utilisée.

> **Statut** : lot 1 de l'évaluation E1 (mise en place de l'environnement de travail), révisé le
> 2026-10-20 : tout tourne dans des conteneurs Docker (PostgreSQL et l'environnement de travail
> Python + Java + PySpark), décrits par `compose.yaml`. Le dépôt contient la structure, la
> procédure d'installation et le contrôle de bon fonctionnement. Les fichiers ont été écrits sans
> pouvoir être exécutés : ils n'ont pas encore été lancés sur le serveur, et les versions
> d'images sont des hypothèses « à vérifier » (voir `docs/installation.md`, section 2).
> Il n'y a pas encore de logique métier (extraction, agrégation, base, API).

## ATTENTION : ce dépôt est public

Tout ce qui est poussé sur GitHub est lisible par tout le monde, pour toujours (l'historique Git
garde tout). **Ne pousse jamais :**

- le fichier **`.env`** (mots de passe, configuration réelle) : il est dans `.gitignore`, et seul
  le modèle `.env.example` (sans valeur secrète) est versionné ;
- les **données** (export Open Food Facts, fichiers Parquet, sauvegardes de la base) : elles
  vivent hors du dépôt (variable `DONNEES_DIR`) ou dans `donnees/`, dont le contenu est ignoré ;
- les **journaux** (`journaux/`), ni aucun mot de passe, jeton, clé ou adresse e-mail personnelle,
  où que ce soit dans un fichier.

Avant chaque `git push` : `git status`, puis `git diff --staged`. Détail et marche à suivre en cas
d'erreur dans `docs/versionnement.md`, section 7.

## Le circuit : de ton poste au serveur

Les fichiers ne sont pas écrits sur le serveur. Ils suivent un circuit en trois étapes, et **rien
n'arrive sur le serveur tant que les étapes 2 et 3 ne sont pas faites** :

```
 1. ÉCRITURE                 2. PUSH                    3. PULL
 Dossier verger-voisin/  -->  GitHub (dépôt public)  -->  Serveur (dépôt cloné)
 sur ton poste                git push                    git pull
 (fichiers écrits par Octet,  (c'est toi qui pousses)     (c'est toi qui récupères,
  ou modifiés par toi)                                     puis qui lances les scripts)
```

1. **Écriture** : les fichiers sont créés dans le dossier `verger-voisin/` de ton poste. Ce
   dossier est un dépôt Git à part, indépendant du dépôt `cap-odyssee` qui le contient (celui-ci
   l'ignore).
2. **Push** : depuis le dossier `verger-voisin/` de ton poste.
   Première fois seulement (après avoir créé sur GitHub un dépôt **vide** nommé `verger-voisin`,
   sans README ni `.gitignore` ajoutés par GitHub) :
   ```bash
   git init -b main
   git add .
   git status        # relis la liste : pas de .env, pas de données
   git commit -m "Mettre en place l'environnement de travail (lot 1)"
   git remote add origin https://github.com/ElvexDom/verger-voisin.git
   git push -u origin main
   ```
   Les fois suivantes, suis les règles de
   `docs/versionnement.md` (branche, commit, demande de fusion), puis `git push`.
3. **Pull** : sur le serveur, `git clone` la première fois, ensuite `git pull` dans le dossier
   cloné (voir `docs/installation.md`, étape 1).

Le `.env` du serveur n'existe qu'à cet endroit : il ne fait jamais le circuit.
Ce `.env` est aussi distinct de celui du projet `cap-odyssee` (autre usage, autre dépôt).

## Prérequis

- Un serveur sous **Ubuntu 26.04 LTS** (4 cœurs, 16 Go de mémoire, sans GPU), avec un accès SSH,
  **Docker** et **Docker Compose** déjà installés et actifs (Docker 29.9.1 et Compose v5.6.0
  constatés par Ulysse le 2026-10-20), et Git.
- Un utilisateur du serveur avec les droits `sudo`, ou membre du groupe `docker`. **Tant que ton
  utilisateur n'est pas dans le groupe `docker`, les commandes Docker se lancent avec `sudo`**
  (`sudo docker compose ...`). Les scripts `installer.sh` et `verifier.sh` appellent `sudo`
  eux-mêmes : lance-les sans `sudo`.
- Un accès à Internet depuis le serveur (images Docker, paquets Python, API Open Food Facts).
- Un compte GitHub, et le dépôt `verger-voisin` créé dessus.
- Sur ton poste : Git.

Rien d'autre que Docker n'est installé sur le serveur : Python, Java, PySpark et PostgreSQL sont
dans les conteneurs. Pourquoi : la compatibilité de PySpark avec le Python du serveur (3.14.4)
n'est pas confirmée ; l'image de travail fixe elle-même ses versions de Python et de Java.

## Ordre des commandes (sur le serveur)

```bash
git clone https://github.com/ElvexDom/verger-voisin.git   # la première fois
cd verger-voisin
cp .env.example .env              # puis remplir .env (nano .env), voir docs/installation.md
bash scripts/installer.sh         # construit l'image, démarre la base (relançable sans danger)
bash scripts/verifier.sh          # contrôle de bon fonctionnement, dans le conteneur de travail
```

Résultat attendu à la fin : `RÉSULTAT GLOBAL : OK (3 vérifications sur 3)`.
Chaque étape, avec son résultat attendu et le dépannage, est dans
**[`docs/installation.md`](docs/installation.md)**.

Les mêmes opérations à la main (les versions d'images sont des hypothèses à vérifier, voir
`docs/installation.md`, section 2) :

```bash
sudo docker compose build travail                                   # construire l'image de travail
sudo docker compose up -d --wait postgres                           # démarrer la base
sudo docker compose run --rm -T travail python scripts/verification.py   # contrôle
```

## Documentation

| Document | Contenu |
|---|---|
| [`docs/installation.md`](docs/installation.md) | Installation pas à pas, objets techniques attendus, hypothèses à vérifier, dépannage |
| [`docs/versionnement.md`](docs/versionnement.md) | Branches, messages de commit, lien avec les tickets GitHub, tâches et incidents |
| [`docs/justifications.md`](docs/justifications.md) | Décisions techniques du projet et leur justification, classées par date |
| [`.env.example`](.env.example) | Liste des variables de configuration et leur rôle (sans valeur secrète) |

## Organisation du dépôt

```
verger-voisin/
├── README.md                  ce fichier
├── compose.yaml               services Docker : postgres (base) et travail (Python, Java, PySpark)
├── compose.acces-hote.yaml    facultatif : publie la base sur 127.0.0.1 du serveur seulement
├── Dockerfile                 image de l'environnement de travail (versions en variables)
├── .dockerignore              ce qui est envoyé à Docker à la construction (jamais le .env)
├── .env.example               modèle de configuration (le vrai .env n'est jamais commité)
├── .gitignore  .gitattributes
├── requirements.txt           dépendances Python de production (installées dans l'image)
├── requirements-dev.txt       dépendances de développement (inclut les précédentes, + pytest)
├── pytest.ini                 configuration des tests
├── docs/                      installation.md, versionnement.md, justifications.md
├── scripts/                   installer.sh, verifier.sh (sur le serveur), verification.py
│                              (dans le conteneur), _commun.sh
├── src/verger_voisin/         code (configuration et journalisation ; dossiers vides pour la suite)
│   ├── extraction/  agregation/  importation/  api/
├── tests/                     un dossier par partie du code (vides pour l'instant)
├── donnees/                   emplacement par défaut des données sur le serveur, contenu ignoré par Git
├── journaux/                  emplacement par défaut des journaux, contenu ignoré par Git
└── .github/                   modèles de tickets (tâche, incident) et de demande de fusion
```

Principe : le code (monté dans le conteneur de travail), la configuration (variables
d'environnement, fichier `.env`) et les données (dossiers du serveur et volume Docker de la base)
sont séparés. Les dossiers `donnees/` et `journaux/` sont montés dans le conteneur de travail sous
les noms `/donnees` et `/journaux`.

## Règles à retenir

- **Aucun secret dans Git** : seulement des noms de variables dans `.env.example`.
- **Aucune donnée dans Git** : ni export, ni Parquet, ni sauvegarde de base.
- **PostgreSQL n'est publié sur aucune interface** du serveur : il n'est joignable que par les
  conteneurs du projet (nom d'hôte `postgres`). Un accès depuis le serveur, limité à `127.0.0.1`,
  est possible en option (`compose.acces-hote.yaml`).
- **Les données de la base vivent dans un volume Docker** : `docker compose down -v` les efface.
  Les scripts du dépôt ne suppriment jamais de volume.
- **Le conteneur de travail ne tourne pas en root.**
- **Journaux** : niveau et format réglés par `LOG_LEVEL` et `LOG_FORMAT` ; ni secret ni donnée
  personnelle dedans.
- **Open Food Facts** : le User-Agent des appels contient le nom de l'application et le lien de
  ce dépôt, sans adresse e-mail.

## Attribution et licences des données

Ce projet utilise des données issues d'**Open Food Facts** (openfoodfacts.org), base collaborative
de produits alimentaires publiée sous licence **ODbL** (Open Database License) : toute
utilisation doit mentionner la source (attribution), et une base de données construite en
combinaison avec ces données doit rester ouverte (partage à l'identique). Les images des produits
sont sous licence CC BY-SA. Conditions de réutilisation :
https://support.openfoodfacts.org/help/en-gb/12-api-data-reuse/94-are-there-conditions-to-use-the-api

D'autres sources s'ajouteront dans les lots suivants (table Ciqual de l'ANSES, règlement
(CE) 1333/2008 sur EUR-Lex) ; leurs attributions seront ajoutées ici à ce moment-là.

Le dépôt ne contient aucune donnée Open Food Facts : seul le code est publié.
Licence du code : **MIT** (voir le fichier `LICENSE`). Elle couvre uniquement le code de ce
dépôt, pas les données des sources, qui gardent leur propre licence.

## Contexte

Projet de fin d'année en Data et IA (gestion de projets), évaluation E1 : extraction,
requêtes SQL, agrégation et nettoyage, base de données, API.
