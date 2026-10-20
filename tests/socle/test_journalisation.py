"""Tests de la journalisation (src/verger_voisin/journalisation.py).

Règle du projet : ni secret ni donnée personnelle dans les journaux. Les mots de passe
utilisés ici sont factices.
"""

from __future__ import annotations

import json
import logging
import re

import pytest

from verger_voisin import config
from verger_voisin.journalisation import (
    FiltreSecrets,
    configurer_journalisation,
    masquer,
)

# Mots de passe factices, avec les caractères qui posent problème : $, #, espaces, guillemets,
# =, &, antislash, accent.
SECRETS_FACTICES = [
    "motdepasse-factice",
    "pa$$w0rd-factice",
    "ab#cd-factice",
    "mot de passe factice",
    'avec"guillemets"doubles',
    "avec'guillemet'simple",
    "a=b&c=d-factice",
    "back\\slash-factice",
    "mélange $x #y \"z\" 'w'",
]


@pytest.fixture
def dossier_journaux(monkeypatch, tmp_path):
    """Dossier de journaux temporaire (jamais le vrai dossier du dépôt)."""
    dossier = tmp_path / "journaux"
    monkeypatch.setenv("JOURNAUX_DIR", str(dossier))
    return dossier


def _lire_fichier(fichier):
    for handler in logging.getLogger("verger_voisin").handlers:
        handler.flush()
    return fichier.read_text(encoding="utf-8")


# --- masquer -----------------------------------------------------------------------------


@pytest.mark.parametrize("secret", SECRETS_FACTICES)
def test_masquer_remplace_le_secret_par_des_etoiles(monkeypatch, secret):
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    assert masquer(f"connexion avec {secret} refusée") == "connexion avec *** refusée"


@pytest.mark.parametrize("secret", SECRETS_FACTICES)
def test_masquer_remplace_toutes_les_occurrences(monkeypatch, secret):
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    assert masquer(f"{secret} puis {secret}") == "*** puis ***"


def test_masquer_message_sans_secret_reste_intact(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    message = "Vérification « PostgreSQL » : OK (0.1 s) avec $HOME et #tag"
    assert masquer(message) == message


def test_masquer_sans_variable_secrete_laisse_le_texte_intact():
    assert masquer("rien à cacher") == "rien à cacher"


def test_masquer_texte_vide_reste_vide(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    assert masquer("") == ""


def test_masquer_ignore_un_secret_vide(monkeypatch):
    # Un secret vide masquerait tout le texte s'il était traité : il doit être ignoré.
    monkeypatch.setenv("POSTGRES_PASSWORD", "")
    assert masquer("texte normal") == "texte normal"


def test_masquer_masque_plusieurs_secrets_differents(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "mdp-factice-1")
    monkeypatch.setenv("API_TOKEN", "jeton-factice-2")
    assert masquer("mdp-factice-1 / jeton-factice-2") == "*** / ***"


def test_masquer_secret_contenant_un_autre_est_masque_en_entier(monkeypatch):
    monkeypatch.setenv("A_PASSWORD", "abc")
    monkeypatch.setenv("B_TOKEN", "abc-suite-factice")
    # Si le plus court passait d'abord, il resterait « -suite-factice » en clair.
    assert masquer("valeur abc-suite-factice fin") == "valeur *** fin"


def test_masquer_ne_garde_pas_le_secret_dans_le_resultat(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    assert "motdepasse-factice" not in masquer("x motdepasse-factice y")


# --- FiltreSecrets (sur un enregistrement de journal) ------------------------------------


def _enregistrement(message, args=(), exc_info=None):
    return logging.LogRecord(
        name="verger_voisin",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=args,
        exc_info=exc_info,
    )


def test_filtre_masque_le_secret_dans_le_message(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    enregistrement = _enregistrement("mdp=motdepasse-factice")
    FiltreSecrets().filter(enregistrement)
    assert enregistrement.getMessage() == "mdp=***"


def test_filtre_masque_le_secret_passe_en_argument(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "mot de passe factice")
    enregistrement = _enregistrement("mdp=%s", args=("mot de passe factice",))
    FiltreSecrets().filter(enregistrement)
    assert enregistrement.getMessage() == "mdp=***"


def test_filtre_laisse_passer_le_message_cest_un_masquage_pas_un_rejet(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    assert FiltreSecrets().filter(_enregistrement("motdepasse-factice")) is True


def test_filtre_message_sans_secret_reste_intact(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    enregistrement = _enregistrement("Début du contrôle %s", args=("PostgreSQL",))
    FiltreSecrets().filter(enregistrement)
    assert enregistrement.getMessage() == "Début du contrôle PostgreSQL"


def test_filtre_message_mal_forme_ne_plante_pas(monkeypatch):
    # Trop peu d'arguments pour le format : le filtre ne doit pas lever d'exception.
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    enregistrement = _enregistrement("a %s b %s motdepasse-factice", args=("un seul",))
    assert FiltreSecrets().filter(enregistrement) is True
    assert "motdepasse-factice" not in enregistrement.getMessage()


def test_filtre_masque_le_secret_dans_la_trace_dune_exception(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    try:
        raise ValueError("échec avec motdepasse-factice")
    except ValueError:
        import sys

        enregistrement = _enregistrement("erreur", exc_info=sys.exc_info())
    FiltreSecrets().filter(enregistrement)
    assert "motdepasse-factice" not in enregistrement.exc_text
    assert "ValueError" in enregistrement.exc_text
    assert "***" in enregistrement.exc_text


def test_filtre_masque_une_trace_deja_mise_en_forme(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    enregistrement = _enregistrement("erreur")
    enregistrement.exc_text = "Traceback ... motdepasse-factice"
    FiltreSecrets().filter(enregistrement)
    assert enregistrement.exc_text == "Traceback ... ***"


# --- Fichier de journal, format texte ----------------------------------------------------


@pytest.mark.parametrize("secret", SECRETS_FACTICES)
def test_format_texte_le_secret_napparait_pas_dans_le_fichier(
    monkeypatch, dossier_journaux, secret
):
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    monkeypatch.setenv("LOG_FORMAT", "texte")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("connexion avec %s impossible", secret)
    journal.error(f"autre message {secret}")

    contenu = _lire_fichier(fichier)
    assert secret not in contenu
    assert contenu.count("***") == 2


def test_format_texte_ligne_datee_avec_niveau_logger_et_message(dossier_journaux):
    # LOG_FORMAT n'est pas défini : c'est le format texte par défaut.
    journal, fichier = configurer_journalisation("test.log")

    journal.info("Vérification OK")

    ligne = _lire_fichier(fichier).strip()
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} INFO verger_voisin ", ligne)
    assert ligne.endswith("Vérification OK")


def test_format_texte_message_sans_secret_reste_intact(monkeypatch, dossier_journaux):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("Vérification « Spark » : OK avec $HOME et #tag")

    assert _lire_fichier(fichier).strip().endswith("Vérification « Spark » : OK avec $HOME et #tag")


def test_format_texte_exception_masquee_dans_le_fichier(monkeypatch, dossier_journaux):
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    journal, fichier = configurer_journalisation("test.log")

    try:
        raise RuntimeError("connexion refusée avec motdepasse-factice")
    except RuntimeError:
        journal.exception("échec")

    contenu = _lire_fichier(fichier)
    assert "Traceback" in contenu
    assert "RuntimeError" in contenu
    assert "motdepasse-factice" not in contenu


# --- Fichier de journal, format json -----------------------------------------------------


@pytest.mark.parametrize("secret", SECRETS_FACTICES)
def test_format_json_le_secret_napparait_nulle_part_dans_le_fichier(
    monkeypatch, dossier_journaux, secret
):
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    monkeypatch.setenv("LOG_FORMAT", "json")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("connexion avec %s impossible", secret)

    brut = _lire_fichier(fichier)
    evenement = json.loads(brut.strip())
    assert evenement["message"] == "connexion avec *** impossible"
    # Ni sous sa forme brute, ni sous sa forme échappée par JSON (guillemets, antislash).
    assert secret not in brut
    assert json.dumps(secret, ensure_ascii=False)[1:-1] not in brut
    assert json.dumps(secret)[1:-1] not in brut


def test_format_json_une_ligne_valide_avec_les_quatre_champs(monkeypatch, dossier_journaux):
    monkeypatch.setenv("LOG_FORMAT", "json")
    journal, fichier = configurer_journalisation("test.log")

    journal.warning("Vérification OK")
    journal.info("deuxième")

    lignes = _lire_fichier(fichier).strip().splitlines()
    assert len(lignes) == 2
    evenement = json.loads(lignes[0])
    assert evenement["niveau"] == "WARNING"
    assert evenement["logger"] == "verger_voisin"
    assert evenement["message"] == "Vérification OK"  # accents conservés, message intact
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", evenement["horodatage"])
    assert "exception" not in evenement


def test_format_json_exception_masquee(monkeypatch, dossier_journaux):
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("POSTGRES_PASSWORD", 'mdp "factice" #1')
    journal, fichier = configurer_journalisation("test.log")

    try:
        raise RuntimeError('refus avec mdp "factice" #1')
    except RuntimeError:
        journal.exception("échec")

    brut = _lire_fichier(fichier)
    evenement = json.loads(brut.strip())
    assert "RuntimeError" in evenement["exception"]
    assert 'mdp "factice" #1' not in brut
    assert 'mdp \\"factice\\" #1' not in brut


def test_format_json_message_sans_secret_reste_intact(monkeypatch, dossier_journaux):
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("OK $HOME #tag")

    assert json.loads(_lire_fichier(fichier).strip())["message"] == "OK $HOME #tag"


# --- Console -----------------------------------------------------------------------------


@pytest.mark.parametrize("format_choisi", ["texte", "json"])
def test_console_le_secret_est_masque(monkeypatch, dossier_journaux, capsys, format_choisi):
    monkeypatch.setenv("LOG_FORMAT", format_choisi)
    monkeypatch.setenv("POSTGRES_PASSWORD", "mot de passe factice")
    journal, _ = configurer_journalisation("test.log", console=True)

    journal.info("mdp=%s", "mot de passe factice")

    sortie = capsys.readouterr().err
    assert "mot de passe factice" not in sortie
    assert "***" in sortie


def test_sans_console_rien_nest_ecrit_sur_lecran(dossier_journaux, capsys):
    journal, fichier = configurer_journalisation("test.log", console=False)

    journal.info("message")

    assert capsys.readouterr().err == ""
    assert fichier is not None


# --- Réglages par variables --------------------------------------------------------------


def test_fichier_cree_dans_journaux_dir_avec_le_nom_demande(dossier_journaux):
    journal, fichier = configurer_journalisation("mon-journal.log")

    journal.info("x")

    assert fichier == dossier_journaux / "mon-journal.log"
    assert fichier.is_file()


def test_journaux_dir_vide_retombe_sur_le_dossier_journaux_du_depot(monkeypatch, tmp_path):
    # On fait pointer la « racine du dépôt » vers un dossier temporaire pour ne pas écrire
    # dans le vrai dossier journaux/.
    monkeypatch.setattr(config, "RACINE_DEPOT", tmp_path)
    monkeypatch.setenv("JOURNAUX_DIR", "")

    _, fichier = configurer_journalisation("test.log")

    assert fichier == tmp_path / "journaux" / "test.log"


def test_niveau_par_defaut_est_info(dossier_journaux):
    journal, fichier = configurer_journalisation("test.log")

    journal.debug("trop détaillé")
    journal.info("visible")

    contenu = _lire_fichier(fichier)
    assert "trop détaillé" not in contenu
    assert "visible" in contenu


def test_niveau_warning_ecarte_les_messages_info(monkeypatch, dossier_journaux):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("info ignorée")
    journal.warning("alerte gardée")

    contenu = _lire_fichier(fichier)
    assert "info ignorée" not in contenu
    assert "alerte gardée" in contenu


def test_niveau_en_minuscules_est_accepte(monkeypatch, dossier_journaux):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    journal, fichier = configurer_journalisation("test.log")

    journal.debug("détail")

    assert "détail" in _lire_fichier(fichier)


def test_niveau_inconnu_retombe_sur_info_avec_avertissement(
    monkeypatch, dossier_journaux, capsys
):
    monkeypatch.setenv("LOG_LEVEL", "BAVARD")
    journal, fichier = configurer_journalisation("test.log")

    journal.debug("détail")
    journal.info("visible")

    contenu = _lire_fichier(fichier)
    assert "détail" not in contenu
    assert "visible" in contenu
    assert "BAVARD" in capsys.readouterr().err


def test_format_inconnu_retombe_sur_texte_avec_avertissement(
    monkeypatch, dossier_journaux, capsys
):
    monkeypatch.setenv("LOG_FORMAT", "xml")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("message")

    ligne = _lire_fichier(fichier).strip()
    assert not ligne.startswith("{")
    assert "INFO verger_voisin message" in ligne
    assert "xml" in capsys.readouterr().err


def test_format_en_majuscules_est_accepte(monkeypatch, dossier_journaux):
    monkeypatch.setenv("LOG_FORMAT", "JSON")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("message")

    assert json.loads(_lire_fichier(fichier).strip())["message"] == "message"


# --- Robustesse --------------------------------------------------------------------------


def test_appels_repetes_nempilent_pas_les_handlers(dossier_journaux):
    configurer_journalisation("test.log")
    journal, fichier = configurer_journalisation("test.log")

    journal.info("une seule fois")

    assert len(journal.handlers) == 1
    assert _lire_fichier(fichier).count("une seule fois") == 1


def test_dossier_inutilisable_continue_sans_fichier_et_sans_fuite(
    monkeypatch, tmp_path, capsys
):
    # JOURNAUX_DIR pointe sous un fichier ordinaire : mkdir échoue.
    un_fichier = tmp_path / "ordinaire"
    un_fichier.write_text("x", encoding="utf-8")
    monkeypatch.setenv("JOURNAUX_DIR", str(un_fichier / "sous-dossier"))
    monkeypatch.setenv("POSTGRES_PASSWORD", "motdepasse-factice")

    journal, fichier = configurer_journalisation("test.log")
    journal.error("échec avec motdepasse-factice")

    erreur = capsys.readouterr().err
    assert fichier is None
    assert "ATTENTION" in erreur
    assert "motdepasse-factice" not in erreur
    # Sans fichier, la console prend le relais, toujours avec masquage.
    assert "échec avec ***" in erreur


def test_le_logger_ne_propage_pas_vers_le_logger_racine(dossier_journaux):
    journal, _ = configurer_journalisation("test.log")
    assert journal.propagate is False
