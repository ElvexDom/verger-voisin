# Justification des choix et des actions

Ce document garde la trace de chaque décision technique du projet et de sa raison. Il sert de
base aux parties « spécifications techniques » et « choix » des rapports d'évaluation.

Chaque entrée indique : la décision, sa justification, les solutions écartées, la compétence du
référentiel concernée, et qui l'a validée. Les entrées sont classées par date.

Toutes les décisions de ce fichier ont été prises par Nikko, porteur et gestionnaire du projet.
Les propositions faites par un assistant d'IA n'y figurent qu'une fois acceptées par lui
(voir la section « Méthode de travail et usage de l'IA » du `README.md`).

---

## 2026-10-11 : Sujet et commanditaire

- **Décision** : une application qui propose, pour un produit alimentaire, des produits
  similaires mais mieux notés sur le plan nutritionnel. Commanditaire fictif : « Le Verger
  Voisin », enseigne de magasins bio de proximité inventée.
- **Justification** : le sujet couvre les cinq évaluations avec un seul projet (collecte
  multi-sources, service d'IA existant, modèle à soi, application, monitoring). Les données
  ouvertes nécessaires existent et sont réutilisables. Un commanditaire fictif est accepté par
  le référentiel (« contexte réel ou fictif ») et évite toute dépendance à une entreprise.
- **Écartés** : bibliothèque de philosophie (besoin plus flou, modèle plus difficile à
  mesurer) ; collection de pièces de 2 euros (trop peu de données pour un système big data et
  pour entraîner un modèle de reconnaissance d'images).
- **Compétences** : C1 (présentation du projet et de son contexte).
- **Validé par** : Nikko.

## 2026-10-11 : Les cinq sources de données

- **Décision** : API d'Open Food Facts (service web) ; export complet d'Open Food Facts
  interrogé avec Spark (système big data) ; table Ciqual 2025 de l'ANSES (fichier) ; catalogue
  fictif du Verger Voisin dans PostgreSQL (base de données) ; règlement (CE) n° 1333/2008
  consolidé sur EUR-Lex (scraping).
- **Justification** : le critère de C1 exige les cinq types de sources. Chacune est sous
  licence ouverte et utile au projet : Open Food Facts fournit les produits, Ciqual des valeurs
  de référence pour repérer les erreurs de saisie, EUR-Lex la liste officielle des additifs, le
  catalogue les produits réellement vendus par l'enseigne.
- **Écartés** : Wikipédia pour la liste des additifs (fiabilité jugée insuffisante, source non
  officielle) ; base du Codex alimentaire de la FAO (refuse les requêtes automatisées) ; sites
  marchands (conditions d'utilisation interdisant le scraping) ; Tavily (renvoie un texte déjà
  nettoyé, pas l'HTML : ne démontre pas le scraping attendu).
- **Compétences** : C1, C3.
- **Validé par** : Nikko.

## 2026-10-11 : Outil de scraping choisi d'après le site

- **Décision** : l'outil de scraping se choisit selon la page visée. Page statique : requête
  HTTP simple et analyse de l'HTML. Page dynamique : Selenium, avec la raison écrite.
- **Justification** : un navigateur piloté consomme beaucoup plus de ressources ; l'utiliser
  sans nécessité va contre l'éco-conception. La page d'EUR-Lex est statique.
- **Compétences** : C1 (« identification des contraintes techniques propres aux sources »).
- **Validé par** : Nikko.

## 2026-10-11 : Hébergement sur le VPS existant

- **Décision** : tout le projet est hébergé sur le VPS Hostinger déjà loué pour la formation,
  situé à Paris.
- **Justification** : aucun coût d'infrastructure supplémentaire ; réutiliser un serveur
  existant plutôt qu'en louer un autre est une démarche de sobriété ; données hébergées en
  France, dans l'Union européenne (RGPD) ; électricité française peu carbonée. L'hébergeur
  publie un rapport de durabilité annuel.
- **Compétences** : C1 (environnement et budget), C4 (RGPD), C15 (éco-responsabilité).
- **Validé par** : Nikko.

## 2026-10-19 : Langages et bibliothèques

- **Décision** : Python ; SQLAlchemy pour l'accès aux données ; FastAPI et Pydantic pour
  l'API ; pytest pour les tests.
- **Justification** : outils indiqués dans le modèle de rapport du formateur ; FastAPI produit
  automatiquement une documentation au standard OpenAPI, cité par le critère de C5 ; Pydantic
  assure la validation des requêtes demandée en C5.
- **Compétences** : C2, C5.
- **Validé par** : Nikko.

## 2026-10-19 : PostgreSQL comme système de gestion de base de données

- **Décision** : PostgreSQL.
- **Justification** : modèle de données relationnel, cohérent avec la méthode Merise ; gratuit
  et libre ; géré nativement par SQLAlchemy ; lisible et alimentable par Spark ; tient la charge
  de plusieurs services en parallèle.
- **Écarté** : SQLite (plus simple, mais mal adapté à une API utilisée par plusieurs
  composants en même temps).
- **Compétences** : C4 (« la base de données est choisie au regard de la modélisation des
  données et des contraintes du projet »).
- **Validé par** : Nikko.

## 2026-10-19 : GitHub pour le code et le suivi

- **Décision** : dépôt public `verger-voisin` sur GitHub ; tâches et incidents suivis dans les
  tickets du dépôt ; licence MIT.
- **Justification** : le référentiel exige un dépôt Git distant accessible ; un dépôt public
  est consultable par le jury sans démarche ; les tickets gardent la trace du débogage, demandée
  en C21 ; les chaînes d'intégration de GitHub serviront pour E3 et E4. La licence MIT est
  courte et connue ; elle couvre le code seulement, pas les données des sources.
- **Compétences** : C1, C3, C21.
- **Validé par** : Nikko.

## 2026-10-20 : Tout le projet en conteneurs

- **Décision** : PostgreSQL et l'environnement de travail (Python 3.12, Java 21, PySpark)
  tournent dans des conteneurs décrits par Docker Compose. Seul Docker est installé sur le
  serveur.
- **Justification** : le serveur réinstallé est sous Ubuntu 26.04 avec Python 3.14, version
  dont la compatibilité avec PySpark n'est pas confirmée ; le conteneur fixe lui-même ses
  versions. L'installation se réduit à quelques commandes reproductibles, ce que demande C4. Le
  serveur reste propre, et la conteneurisation est prévue par le modèle de rapport du
  formateur.
- **Écarté** : installation directe des logiciels sur le système (dépendante de la version
  d'Ubuntu, plus difficile à reproduire).
- **Compétences** : C4 (« la reproduction des procédures d'installation décrites a pour
  résultat un système conforme »), C5.
- **Validé par** : Nikko.

## 2026-10-20 : La base de données n'est pas exposée sur Internet

- **Décision** : PostgreSQL n'est publié sur aucun port du serveur ; seuls les conteneurs du
  projet le joignent. Un accès depuis le serveur lui-même reste possible, limité à l'adresse
  locale, par un fichier de configuration séparé.
- **Justification** : réduire la surface d'attaque ; la base n'a pas à être joignable depuis
  l'extérieur, l'accès aux données passera par l'API.
- **Compétences** : C4, C5 (sécurisation), recommandations OWASP.
- **Validé par** : Nikko.

## 2026-10-20 : Configuration du fichier `.env` sur le serveur

- **Décision** : le fichier `.env` est créé à partir de `.env.example`, lisible uniquement par
  son propriétaire. Réglages non secrets :
  - `POSTGRES_DB=verger_voisin` : nom explicite de la base du projet ;
  - `POSTGRES_USER=verger` : utilisateur propre au projet, distinct de l'administrateur de
    PostgreSQL, pour limiter les droits ;
  - `SPARK_DRIVER_MEMORY=4g` : environ un quart des 15 Go de mémoire du serveur, pour laisser
    de la place à la base, à l'API et au système ;
  - `SPARK_NB_COEURS=3` : trois des quatre cœurs, pour garder un cœur libre pour les autres
    services pendant les traitements.
- **Mot de passe de la base** : saisi par Nikko lui-même, jamais écrit dans le dépôt, limité
  aux caractères que Docker Compose ne réinterprète pas.
- **Justification** : aucun secret dans le dépôt public ; séparation des droits ; répartition
  des ressources d'un serveur partagé entre plusieurs services. Les valeurs de mémoire et de
  cœurs sont des points de départ, à ajuster après les premiers traitements.
- **Compétences** : C1 (gestion des connexions externes et des erreurs), C4, C5.
- **Validé par** : Nikko.

## 2026-10-20 : Installation sur le serveur et versions constatées

- **Action** : installation lancée sur le serveur (Ubuntu 26.04.1 LTS, Docker 29.9.1,
  Compose v5.6.0) avec `bash scripts/installer.sh`, puis contrôle avec
  `bash scripts/verifier.sh` et exécution des tests du socle dans le conteneur de travail.
- **Versions réellement installées dans les conteneurs** :
  - Python 3.12.15 ;
  - OpenJDK 21.0.12.1 ;
  - PySpark 4.2.0 ;
  - PostgreSQL 17.11.
- **Résultats** :
  - contrôle de bon fonctionnement : 3 vérifications sur 3 réussies (PostgreSQL, Spark en mode
    local avec 3 cœurs et 4 Go, API Open Food Facts) ;
  - tests du socle : 133 sur 133 réussis ;
  - la base n'est publiée sur aucun port du serveur (port 5432 interne au réseau Docker).
- **Justification** : ces versions remplacent les hypothèses « à vérifier » de la
  documentation d'installation. Le conteneur fixe Python 3.12, indépendamment du Python 3.14 du
  serveur.
- **Reste à faire** : figer les versions des dépendances Python dans les fichiers de
  dépendances, pour que la reconstruction de l'image redonne exactement le même environnement.
- **Compétences** : C1, C4 (procédure d'installation reproductible).
- **Validé par** : Nikko (accord donné pour l'installation).

## 2026-10-20 : Versions figées

- **Décision** : figer les versions à trois niveaux :
  - images Docker à la version précise (`postgres:17.11-bookworm`,
    `python:3.12.15-slim-trixie`) plutôt qu'à la version majeure ;
  - dépendances directes à la version exacte dans `requirements.txt` et
    `requirements-dev.txt` ;
  - toutes les dépendances, indirectes comprises, dans `requirements-verrou.txt`, utilisé comme
    fichier de contraintes par le `Dockerfile`.
- **Justification** : sans versions figées, reconstruire l'image plus tard pourrait installer
  des versions plus récentes et changer le comportement du projet. Le critère de C4 demande que
  la procédure d'installation reproduise un système conforme.
- **Vérification** : sur le serveur, image reconstruite avec les versions figées, contrôle à 3
  sur 3, 133 tests sur 133, et versions installées identiques au verrou.
- **Écarté** : un gestionnaire de dépendances plus complet (Poetry, uv), jugé inutile à ce
  stade : `pip` avec un fichier de contraintes suffit et reste simple à documenter.
- **Compétences** : C4.
- **Validé par** : Nikko.

## 2026-10-20 : Test du lien entre commit, ticket et demande de fusion

- **Action** : procédure de `docs/versionnement.md` (section 6) déroulée sur GitHub : ticket
  n° 1, branche `tache/1-test-versionnement`, commit citant `(#1)`, demande de fusion n° 2
  contenant `Closes #1`, fusion, suppression de la branche.
- **Constat** : le commit poussé sur la branche n'apparaît pas dans le ticket tant que la
  branche n'est pas fusionnée. Après la fusion, la chronologie du ticket montre la référence
  croisée de la demande de fusion n° 2, le commit de fusion qui cite le ticket, et la fermeture
  automatique du ticket.
- **Justification** : chaque incident traité en E5 sera ainsi retrouvable depuis son ticket,
  comme le demande le critère de C21 (« la procédure de débogage du code est documentée depuis
  l'outil de suivi »). La documentation a été corrigée d'après ce constat.
- **Compétences** : C21 (préparation), critère A19 du lot 1.
- **Validé par** : Nikko (fusion faite par lui sur GitHub).

## 2026-10-23 : Choix techniques validés après coup

Treize choix avaient été appliqués par défaut pendant la mise en place, ou proposés sans
validation explicite. Nikko les a revus un par un et validés le 23 octobre 2026.

| N° | Choix | Justification | Compétences |
|---|---|---|---|
| 1 | La base PostgreSQL n'est publiée sur aucun port du serveur ; seuls les conteneurs du projet la joignent | Réduire la surface d'attaque ; l'accès aux données passe par l'API | C4, C5 |
| 2 | Environnement : Python 3.12, Java 21, PySpark 4.2.0, PostgreSQL 17 | Combinaison vérifiée sur le serveur (contrôle à 3 sur 3, 133 tests sur 133), indépendante du Python 3.14 du système | C1, C4 |
| 3 | Conteneurs durcis : utilisateur non administrateur, droits système retirés, code monté en lecture seule | Limiter les dégâts possibles d'une faille, sans contrepartie fonctionnelle | C5, C17 |
| 4 | Mot de passe de la base limité aux lettres, chiffres et `. _ + = : , -` | Contrainte de Docker Compose, qui réinterprète les autres caractères du `.env` ; compensée par la longueur (48 caractères aléatoires recommandés) | C4 |
| 5 | Identification auprès de l'API Open Food Facts par le nom du projet et le lien du dépôt, sans adresse électronique | Identification exigée par l'API, sans créer de donnée personnelle | C1, C4 |
| 6 | Aucun secret ni donnée personnelle dans les journaux, avec masquage automatique des secrets | Exigence du RGPD et de sécurité ; le masquage est couvert par des tests | C4, C20 |
| 7 | Données hors de Git, dans le dossier `donnees/` ignoré par le dépôt | Dépôt public ; volumes importants ; licences des sources | C1, C3 |
| 8 | Versionnement : commits en français, une branche par ticket, numéro du ticket dans le message, fusion par demande contenant `Closes #n` | Traçabilité de chaque tâche et de chaque incident depuis l'outil de suivi | C21 |
| 9 | Les commits préparés avec l'assistant d'IA portent la mention « Co-Authored-By: Claude » | Transparence sur l'usage de l'IA (voir le README) | — |
| 10 | Sauvegardes de la base traitées au lot base de données | Elles dépendent de la structure de la base, définie à ce lot | C4 |
| 11 | Rapports : l'assistant prépare des brouillons ; Nikko les relit, les reformule et en reste l'auteur | Les rapports engagent Nikko, seul responsable du projet | E1 à E5 |
| 12 | Service d'IA de E2 : lecture d'étiquettes par OCR, avec PaddleOCR comme favori, à confirmer par le benchmark | Besoin réel (fiches incomplètes), bien relié au modèle de E3, comparable par une mesure claire (taux d'erreur par caractère) ; alternatives écartées : modèle de langage pour expliquer les substituts (plus cosmétique, plus énergivore), reconnaissance d'image du produit (redondante avec le code-barres) | C7, C8 |
| 13 | Garde-fous du modèle de E3 : score affiché comme « estimé » et sans le logo officiel, abstention quand le modèle est peu sûr, mesure par catégorie, gravité des erreurs prise en compte, limite des produits non notés documentée | Risques de biais identifiés (sélection, information incomplète, erreurs inégales) ; le logo Nutri-Score est une marque réservée | C11, C12, C14 |

- **Validé par** : Nikko.
