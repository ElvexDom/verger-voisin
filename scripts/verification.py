#!/usr/bin/env python3
"""Contrôle de bon fonctionnement de l'environnement de Verger Voisin.

Trois vérifications, toujours toutes exécutées, même si l'une échoue :
  1. PostgreSQL : connexion avec les identifiants du .env, requête triviale ;
  2. Spark      : session locale avec limite de mémoire (variable SPARK_DRIVER_MEMORY),
                  opération simple, arrêt de la session ;
  3. Open Food Facts : un seul appel à l'API, avec un User-Agent construit depuis le .env.

Code de sortie : 0 si les trois vérifications réussissent, 1 sinon.

Ce script ne lit pas le fichier .env lui-même : il lit les variables d'environnement.
Lance-le avec `bash scripts/verifier.sh`, qui l'exécute dans le conteneur de travail
(Docker Compose passe alors les variables du .env au conteneur). Dans le conteneur,
PostgreSQL est joint par le nom de son service Compose (POSTGRES_HOST=postgres).
Aucun mot de passe n'est affiché ni journalisé.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from verger_voisin.config import (  # noqa: E402
    ConfigurationManquante,
    lire,
    lire_obligatoire,
)
from verger_voisin.journalisation import configurer_journalisation, masquer  # noqa: E402

# Chemin de l'API d'Open Food Facts pour lire un produit par code-barres.
# Format de la version 2 de l'API : vérifié le 2026-10-19.
CHEMIN_API_PRODUIT = "/api/v2/product"
DELAI_APPEL_SECONDES = 15
ADRESSES_LOCALES = {"localhost", "127.0.0.1", "::1"}
LONGUEUR_MAX_DETAIL = 600


class EchecVerification(Exception):
    """Échec attendu d'une vérification, avec un message clair pour ElvexDom."""


def verifier_postgres() -> tuple[str, list[str]]:
    """Connexion à PostgreSQL et requête triviale. Retourne (détail, avertissements)."""
    try:
        import psycopg
    except ImportError as erreur:
        raise EchecVerification(
            "Le paquet psycopg n'est pas installé dans l'environnement Python de l'image "
            "(reconstruis l'image : bash scripts/installer.sh)."
        ) from erreur

    parametres = {
        "host": lire_obligatoire("POSTGRES_HOST"),
        "dbname": lire_obligatoire("POSTGRES_DB"),
        "user": lire_obligatoire("POSTGRES_USER"),
        "password": lire_obligatoire("POSTGRES_PASSWORD", nettoyer=False),
        "connect_timeout": 5,
    }
    port = lire("POSTGRES_PORT")
    if port:
        parametres["port"] = port

    avertissements: list[str] = []
    with psycopg.connect(**parametres) as connexion:
        with connexion.cursor() as curseur:
            curseur.execute("SELECT 1")
            if curseur.fetchone() != (1,):
                raise EchecVerification("La requête « SELECT 1 » n'a pas renvoyé 1.")
            # Ce contrôle n'a de sens que pour une base installée sur la machine elle-même.
            # Dans le conteneur de travail, la base est jointe par le nom de son service
            # Compose : PostgreSQL y écoute sur toutes les adresses de SON conteneur (réglage
            # normal de l'image officielle). Ce qui compte alors est de ne rien publier sur
            # l'hôte, ce qui se vérifie avec « docker compose ps » (voir docs/installation.md).
            if parametres["host"] in ADRESSES_LOCALES:
                try:
                    curseur.execute("SHOW listen_addresses")
                    ecoute = curseur.fetchone()[0]
                    adresses = [a.strip() for a in ecoute.split(",") if a.strip()]
                    if any(a not in ADRESSES_LOCALES for a in adresses):
                        avertissements.append(
                            f"PostgreSQL écoute sur « {ecoute} » : il ne devrait écouter qu'en "
                            "local (localhost)."
                        )
                except Exception:
                    avertissements.append(
                        "Impossible de lire le réglage listen_addresses de PostgreSQL."
                    )

    detail = (
        f"connexion établie à la base « {parametres['dbname']} » "
        f"(utilisateur « {parametres['user']} »), requête « SELECT 1 » réussie"
    )
    return detail, avertissements


def verifier_spark() -> tuple[str, list[str]]:
    """Session Spark locale avec limite de mémoire. Retourne (détail, avertissements)."""
    memoire = lire_obligatoire("SPARK_DRIVER_MEMORY")
    if not re.fullmatch(r"[0-9]+[a-zA-Z]{0,2}", memoire):
        raise EchecVerification(
            f"SPARK_DRIVER_MEMORY='{memoire}' n'a pas un format valide "
            "(attendu : un nombre suivi d'une unité, par exemple 512m ou 2g)."
        )
    nb_coeurs = lire("SPARK_NB_COEURS")
    if nb_coeurs and not nb_coeurs.isdigit():
        raise EchecVerification(
            f"SPARK_NB_COEURS='{nb_coeurs}' doit être un nombre entier (ou rester vide)."
        )
    master = f"local[{nb_coeurs}]" if nb_coeurs else "local[*]"

    if shutil.which("java") is None and not lire("JAVA_HOME"):
        raise EchecVerification(
            "Java est introuvable (commande « java » absente et JAVA_HOME vide). "
            "Reconstruis l'image : bash scripts/installer.sh."
        )
    try:
        from pyspark.sql import SparkSession
    except ImportError as erreur:
        raise EchecVerification(
            "Le paquet pyspark n'est pas installé dans l'environnement Python de l'image "
            "(reconstruis l'image : bash scripts/installer.sh)."
        ) from erreur

    # Les éventuels processus Python de Spark utilisent le même Python que ce script.
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)

    avertissements: list[str] = []
    session = None
    try:
        session = (
            SparkSession.builder.master(master)
            .appName("verger-voisin-verification")
            .config("spark.driver.memory", memoire)
            # Pas d'interface web de Spark, et rien d'ouvert hors du VPS.
            .config("spark.ui.enabled", "false")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .config("spark.driver.host", "127.0.0.1")
            .getOrCreate()
        )
        session.sparkContext.setLogLevel("WARN")

        nb_lignes = session.range(1000).count()
        if nb_lignes != 1000:
            raise EchecVerification(
                f"L'opération Spark a renvoyé {nb_lignes} lignes au lieu de 1000."
            )

        limite = session.sparkContext.getConf().get("spark.driver.memory", memoire)
        try:
            octets = session._jvm.java.lang.Runtime.getRuntime().maxMemory()
            complement = f" ; mémoire maximale réellement vue par la JVM : {octets // (1024 * 1024)} Mo"
        except Exception:
            complement = ""
            avertissements.append(
                "La mémoire réelle de la JVM n'a pas pu être lue (sans conséquence)."
            )
    finally:
        if session is not None:
            session.stop()

    detail = (
        f"session Spark démarrée en mode {master}, limite de mémoire appliquée : {limite}"
        f"{complement} ; opération « range(1000).count() » réussie ; session arrêtée"
    )
    return detail, avertissements


def verifier_open_food_facts() -> tuple[str, list[str]]:
    """Un seul appel à l'API Open Food Facts. Retourne (détail, avertissements)."""
    try:
        import requests
    except ImportError as erreur:
        raise EchecVerification(
            "Le paquet requests n'est pas installé dans l'environnement Python de l'image "
            "(reconstruis l'image : bash scripts/installer.sh)."
        ) from erreur

    base = lire_obligatoire("OFF_API_BASE_URL").rstrip("/")
    nom_application = lire_obligatoire("OFF_APP_NOM")
    lien_depot = lire_obligatoire("OFF_APP_LIEN_DEPOT")
    code_barres = lire_obligatoire("OFF_CODE_BARRES_TEST")

    if not base.startswith(("http://", "https://")):
        raise EchecVerification("OFF_API_BASE_URL doit commencer par https:// (ou http://).")
    if "@" in nom_application or "@" in lien_depot:
        raise EchecVerification(
            "Le User-Agent ne doit contenir aucune adresse e-mail : "
            "retire le « @ » de OFF_APP_NOM et de OFF_APP_LIEN_DEPOT."
        )
    if not code_barres.isdigit():
        raise EchecVerification("OFF_CODE_BARRES_TEST ne doit contenir que des chiffres.")

    user_agent = f"{nom_application} ({lien_depot})"
    url = f"{base}{CHEMIN_API_PRODUIT}/{code_barres}"

    # Un seul appel, sans nouvelle tentative : on reste très en dessous de toute limite de débit.
    reponse = requests.get(
        url,
        params={"fields": "code,product_name"},
        headers={"User-Agent": user_agent},
        timeout=DELAI_APPEL_SECONDES,
    )
    if reponse.status_code != 200:
        raise EchecVerification(f"L'API a répondu avec le statut HTTP {reponse.status_code}.")
    try:
        contenu = reponse.json()
    except ValueError as erreur:
        raise EchecVerification("La réponse de l'API n'est pas du JSON valide.") from erreur
    if not isinstance(contenu, dict) or contenu.get("status") != 1 or not isinstance(
        contenu.get("product"), dict
    ):
        raise EchecVerification(
            "La réponse de l'API est du JSON mais n'a pas la forme attendue "
            "(status = 1 et un objet « product »). Vérifie OFF_CODE_BARRES_TEST "
            "et la documentation de l'API."
        )

    detail = "un appel à l'API, statut HTTP 200, JSON valide, produit trouvé"
    return detail, []


def executer(numero: int, total: int, nom: str, fonction, journal) -> bool:
    """Exécute une vérification, affiche et journalise son résultat. Retourne True si OK."""
    print(f"[{numero}/{total}] {nom} ...", flush=True)
    journal.info("Vérification « %s » : démarrage", nom)
    debut = time.monotonic()
    avertissements: list[str] = []
    try:
        detail, avertissements = fonction()
        reussi = True
    except ConfigurationManquante as erreur:
        reussi, detail = False, str(erreur)
    except EchecVerification as erreur:
        reussi, detail = False, str(erreur)
    except Exception as erreur:  # toute autre erreur est un échec, jamais un plantage
        # Masquer avant de réduire les espaces : sinon un secret contenant plusieurs espaces
        # ou une tabulation ne serait plus reconnu par masquer().
        message = " ".join(masquer(str(erreur)).split())
        reussi, detail = False, f"{type(erreur).__name__} : {message}"

    detail = masquer(detail)
    if len(detail) > LONGUEUR_MAX_DETAIL:
        detail = detail[:LONGUEUR_MAX_DETAIL] + " [...]"
    duree = time.monotonic() - debut

    if reussi:
        print(f"      OK : {detail} ({duree:.1f} s)")
        journal.info("Vérification « %s » : OK (%.1f s) : %s", nom, duree, detail)
    else:
        print(f"      ÉCHEC : {detail}")
        journal.error("Vérification « %s » : ÉCHEC (%.1f s) : %s", nom, duree, detail)
    for avertissement in avertissements:
        avertissement = masquer(avertissement)
        print(f"      ATTENTION : {avertissement}")
        journal.warning("Vérification « %s » : %s", nom, avertissement)
    return reussi


def main() -> int:
    journal, fichier_journal = configurer_journalisation("verification.log")

    print("=== Contrôle de bon fonctionnement de Verger Voisin ===")
    if fichier_journal is not None:
        print(f"Journal : {fichier_journal}")
    journal.info("Début du contrôle de bon fonctionnement")

    verifications = [
        ("PostgreSQL", verifier_postgres),
        ("Spark (mode local)", verifier_spark),
        ("API Open Food Facts", verifier_open_food_facts),
    ]
    echecs = []
    for numero, (nom, fonction) in enumerate(verifications, start=1):
        if not executer(numero, len(verifications), nom, fonction, journal):
            echecs.append(nom)

    print()
    if echecs:
        print(f"RÉSULTAT GLOBAL : ÉCHEC ({len(echecs)} vérification(s) sur "
              f"{len(verifications)}) : {', '.join(echecs)}")
        print("Voir « Dépannage » dans docs/installation.md.")
        journal.error("Fin du contrôle : ÉCHEC (%s)", ", ".join(echecs))
        return 1
    print("RÉSULTAT GLOBAL : OK (3 vérifications sur 3)")
    journal.info("Fin du contrôle : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
