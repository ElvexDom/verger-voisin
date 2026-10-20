"""Tests de la logique du contrôle (scripts/verification.py), sans PostgreSQL, Spark ni réseau.

Les trois vérifications réelles (verifier_postgres, verifier_spark, verifier_open_food_facts)
sont remplacées par de faux, pour tester seulement ce qui relève de la spec du brief 2 :
A14 (échec clair, code de sortie non nul, les autres vérifications quand même exécutées),
A15 (aucun mot de passe à l'écran ni dans les journaux) et A17 (lignes datées par vérification).

Le fichier .env n'est pas lu par ce script : il l'est par scripts/_commun.sh (bash). La
fonction charger_env n'existe qu'en bash, elle n'est donc pas testée ici.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

CHEMIN_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verification.py"
SECRET = "mot de passe factice #1"


@pytest.fixture
def verification():
    """Charge scripts/verification.py (qui n'est pas un paquet importable)."""
    spec = importlib.util.spec_from_file_location("verification_sous_test", CHEMIN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def journaux_temporaires(monkeypatch, tmp_path):
    dossier = tmp_path / "journaux"
    monkeypatch.setenv("JOURNAUX_DIR", str(dossier))
    return dossier


def _faux_ok(detail="tout va bien"):
    return lambda: (detail, [])


def _installer_fausses_verifications(monkeypatch, verification, postgres, spark, off):
    monkeypatch.setattr(verification, "verifier_postgres", postgres)
    monkeypatch.setattr(verification, "verifier_spark", spark)
    monkeypatch.setattr(verification, "verifier_open_food_facts", off)


# --- executer ----------------------------------------------------------------------------


def test_executer_succes_retourne_true_et_affiche_ok(verification, capsys):
    journal = MagicMock()

    resultat = verification.executer(1, 3, "PostgreSQL", _faux_ok("connexion établie"), journal)

    sortie = capsys.readouterr().out
    assert resultat is True
    assert "[1/3] PostgreSQL" in sortie
    assert "OK : connexion établie" in sortie


def test_executer_echec_attendu_retourne_false_et_affiche_echec(verification, capsys):
    def echoue():
        raise verification.EchecVerification("le paquet psycopg manque")

    resultat = verification.executer(1, 3, "PostgreSQL", echoue, MagicMock())

    sortie = capsys.readouterr().out
    assert resultat is False
    assert "ÉCHEC : le paquet psycopg manque" in sortie


def test_executer_variable_manquante_est_un_echec_pas_un_plantage(verification, capsys):
    from verger_voisin.config import ConfigurationManquante

    def echoue():
        raise ConfigurationManquante("La variable POSTGRES_DB est absente ou vide")

    resultat = verification.executer(1, 3, "PostgreSQL", echoue, MagicMock())

    assert resultat is False
    assert "POSTGRES_DB" in capsys.readouterr().out


def test_executer_erreur_inattendue_est_un_echec_avec_le_nom_de_lerreur(verification, capsys):
    def echoue():
        raise ConnectionError("refusée\npar le serveur")

    resultat = verification.executer(2, 3, "Spark", echoue, MagicMock())

    assert resultat is False
    assert "ÉCHEC : ConnectionError : refusée par le serveur" in capsys.readouterr().out


def test_executer_affiche_les_avertissements(verification, capsys):
    resultat = verification.executer(
        1, 3, "PostgreSQL", lambda: ("ok", ["écoute sur 0.0.0.0"]), MagicMock()
    )

    assert resultat is True
    assert "ATTENTION : écoute sur 0.0.0.0" in capsys.readouterr().out


def test_executer_journalise_le_demarrage_et_le_resultat(verification):
    journal = MagicMock()

    verification.executer(1, 3, "PostgreSQL", _faux_ok(), journal)

    assert journal.info.call_count == 2  # démarrage, puis résultat
    assert journal.error.call_count == 0


def test_executer_echec_est_journalise_au_niveau_erreur(verification):
    journal = MagicMock()

    def echoue():
        raise verification.EchecVerification("raté")

    verification.executer(1, 3, "PostgreSQL", echoue, journal)

    assert journal.error.call_count == 1


def test_executer_detail_trop_long_est_tronque(verification, capsys):
    long_detail = "x" * (verification.LONGUEUR_MAX_DETAIL + 500)

    verification.executer(1, 3, "Spark", _faux_ok(long_detail), MagicMock())

    sortie = capsys.readouterr().out
    assert "x" * verification.LONGUEUR_MAX_DETAIL + " [...]" in sortie
    assert "x" * (verification.LONGUEUR_MAX_DETAIL + 1) not in sortie


# --- A15 : aucun mot de passe à l'écran ni dans les journaux ----------------------------


def test_executer_masque_le_mot_de_passe_dans_un_echec_a_lecran_et_au_journal(
    verification, monkeypatch, capsys
):
    monkeypatch.setenv("POSTGRES_PASSWORD", SECRET)
    journal = MagicMock()

    def echoue():
        raise RuntimeError(f"authentification refusée avec {SECRET}")

    verification.executer(1, 3, "PostgreSQL", echoue, journal)

    assert SECRET not in capsys.readouterr().out
    assert SECRET not in str(journal.mock_calls)


def test_executer_masque_le_mot_de_passe_dans_un_succes_et_un_avertissement(
    verification, monkeypatch, capsys
):
    monkeypatch.setenv("POSTGRES_PASSWORD", SECRET)
    journal = MagicMock()

    verification.executer(
        1, 3, "PostgreSQL", lambda: (f"détail {SECRET}", [f"attention {SECRET}"]), journal
    )

    assert SECRET not in capsys.readouterr().out
    assert SECRET not in str(journal.mock_calls)


def test_executer_masque_un_mot_de_passe_a_espaces_multiples_dans_une_erreur(
    verification, monkeypatch, capsys
):
    # Comportement attendu par A15 : même un mot de passe contenant deux espaces ou une tabulation
    # ne doit jamais apparaître. ATTENTION : à la lecture du code, executer() réduit les espaces
    # multiples de l'erreur (" ".join(str(erreur).split())) AVANT le masquage, donc le secret
    # ne serait plus reconnu. Ce test devrait échouer si mon analyse est juste (écart signalé).
    secret = "mot  de\tpasse factice"
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    journal = MagicMock()

    def echoue():
        raise RuntimeError(f"authentification refusée avec {secret}")

    verification.executer(1, 3, "PostgreSQL", echoue, journal)

    sortie = capsys.readouterr().out
    assert secret not in sortie
    assert " ".join(secret.split()) not in sortie
    assert " ".join(secret.split()) not in str(journal.mock_calls)


# --- main : A14 et A17 -------------------------------------------------------------------


def test_main_tout_reussit_code_de_sortie_zero(
    verification, monkeypatch, journaux_temporaires, capsys
):
    _installer_fausses_verifications(
        monkeypatch, verification, _faux_ok(), _faux_ok(), _faux_ok()
    )

    code = verification.main()

    assert code == 0
    assert "RÉSULTAT GLOBAL : OK (3 vérifications sur 3)" in capsys.readouterr().out


def test_main_une_verification_en_echec_code_non_nul_et_la_nomme(
    verification, monkeypatch, journaux_temporaires, capsys
):
    def echoue():
        raise verification.EchecVerification("base injoignable")

    _installer_fausses_verifications(
        monkeypatch, verification, echoue, _faux_ok(), _faux_ok()
    )

    code = verification.main()

    sortie = capsys.readouterr().out
    assert code != 0
    assert "RÉSULTAT GLOBAL : ÉCHEC (1 vérification(s) sur 3) : PostgreSQL" in sortie
    assert "base injoignable" in sortie


def test_main_un_echec_nempeche_pas_les_autres_verifications(
    verification, monkeypatch, journaux_temporaires
):
    appelees = []

    def postgres():
        appelees.append("postgres")
        raise verification.EchecVerification("raté")

    def spark():
        appelees.append("spark")
        return "ok", []

    def off():
        appelees.append("off")
        return "ok", []

    _installer_fausses_verifications(monkeypatch, verification, postgres, spark, off)

    verification.main()

    assert appelees == ["postgres", "spark", "off"]


def test_main_plusieurs_echecs_sont_tous_listes(
    verification, monkeypatch, journaux_temporaires, capsys
):
    def echoue():
        raise verification.EchecVerification("raté")

    _installer_fausses_verifications(monkeypatch, verification, echoue, _faux_ok(), echoue)

    code = verification.main()

    sortie = capsys.readouterr().out
    assert code != 0
    assert "(2 vérification(s) sur 3) : PostgreSQL, API Open Food Facts" in sortie


def test_main_erreur_inattendue_dans_une_verification_ne_plante_pas(
    verification, monkeypatch, journaux_temporaires
):
    def plante():
        raise ZeroDivisionError("bug dans la vérification")

    _installer_fausses_verifications(monkeypatch, verification, plante, _faux_ok(), _faux_ok())

    assert verification.main() == 1


def test_main_ecrit_des_lignes_datees_pour_chacune_des_trois_verifications(
    verification, monkeypatch, journaux_temporaires
):
    _installer_fausses_verifications(
        monkeypatch, verification, _faux_ok(), _faux_ok(), _faux_ok()
    )

    verification.main()

    lignes = (journaux_temporaires / "verification.log").read_text(encoding="utf-8").splitlines()
    for nom in ("PostgreSQL", "Spark (mode local)", "API Open Food Facts"):
        lignes_nom = [ligne for ligne in lignes if nom in ligne]
        assert lignes_nom, f"aucune ligne de journal pour {nom}"
        assert all(re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ligne) for ligne in lignes_nom)
        assert any("OK" in ligne for ligne in lignes_nom)


def test_main_journalise_aussi_une_verification_en_echec(
    verification, monkeypatch, journaux_temporaires
):
    def echoue():
        raise verification.EchecVerification("base injoignable")

    _installer_fausses_verifications(monkeypatch, verification, echoue, _faux_ok(), _faux_ok())

    verification.main()

    contenu = (journaux_temporaires / "verification.log").read_text(encoding="utf-8")
    assert re.search(r" ERROR .*PostgreSQL.*ÉCHEC.*base injoignable", contenu)


def test_main_le_mot_de_passe_napparait_ni_a_lecran_ni_dans_le_fichier_de_journal(
    verification, monkeypatch, journaux_temporaires, capsys
):
    monkeypatch.setenv("POSTGRES_PASSWORD", SECRET)

    def echoue():
        raise RuntimeError(f"connexion refusée, mot de passe {SECRET}")

    _installer_fausses_verifications(monkeypatch, verification, echoue, _faux_ok(), _faux_ok())

    verification.main()

    journal_fichier = (journaux_temporaires / "verification.log").read_text(encoding="utf-8")
    assert SECRET not in capsys.readouterr().out
    assert SECRET not in journal_fichier


def test_main_affiche_lemplacement_du_journal(
    verification, monkeypatch, journaux_temporaires, capsys
):
    _installer_fausses_verifications(
        monkeypatch, verification, _faux_ok(), _faux_ok(), _faux_ok()
    )

    verification.main()

    assert str(journaux_temporaires / "verification.log") in capsys.readouterr().out
