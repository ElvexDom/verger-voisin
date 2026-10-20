"""Tests de la lecture de la configuration (src/verger_voisin/config.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from verger_voisin import config

# Racine attendue du dépôt : tests/socle/test_config.py -> on remonte de deux dossiers.
RACINE_ATTENDUE = Path(__file__).resolve().parents[2]


# --- Racine du dépôt ---------------------------------------------------------------------


def test_racine_depot_est_le_dossier_qui_contient_pytest_ini():
    assert config.RACINE_DEPOT == RACINE_ATTENDUE
    assert (config.RACINE_DEPOT / "pytest.ini").is_file()


# --- lire --------------------------------------------------------------------------------


def test_lire_retourne_la_valeur_de_la_variable(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "valeur")
    assert config.lire("VV_TEST_NOM") == "valeur"


def test_lire_variable_absente_retourne_le_defaut(monkeypatch):
    monkeypatch.delenv("VV_TEST_NOM", raising=False)
    assert config.lire("VV_TEST_NOM", "defaut") == "defaut"


def test_lire_variable_absente_sans_defaut_retourne_chaine_vide(monkeypatch):
    monkeypatch.delenv("VV_TEST_NOM", raising=False)
    assert config.lire("VV_TEST_NOM") == ""


def test_lire_variable_vide_retourne_le_defaut(monkeypatch):
    # Cas du .env.example : « NOM= » veut dire « non renseignée ».
    monkeypatch.setenv("VV_TEST_NOM", "")
    assert config.lire("VV_TEST_NOM", "defaut") == "defaut"


def test_lire_variable_faite_despaces_retourne_le_defaut(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "    ")
    assert config.lire("VV_TEST_NOM", "defaut") == "defaut"


def test_lire_retire_les_espaces_autour_de_la_valeur(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "  valeur  ")
    assert config.lire("VV_TEST_NOM") == "valeur"


def test_lire_garde_les_espaces_internes(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "deux mots")
    assert config.lire("VV_TEST_NOM") == "deux mots"


def test_lire_sans_nettoyage_garde_les_espaces_autour(monkeypatch):
    # Cas d'un mot de passe : POSTGRES_PASSWORD est lu avec nettoyer=False.
    monkeypatch.setenv("VV_TEST_NOM", "  valeur  ")
    assert config.lire("VV_TEST_NOM", nettoyer=False) == "  valeur  "


def test_lire_ne_modifie_pas_une_valeur_avec_caracteres_speciaux(monkeypatch):
    valeur = "a=b $HOME #pas-un-commentaire \"cite\" 'autre'"
    monkeypatch.setenv("VV_TEST_NOM", valeur)
    assert config.lire("VV_TEST_NOM") == valeur


# --- lire_obligatoire --------------------------------------------------------------------


def test_lire_obligatoire_retourne_la_valeur(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "valeur")
    assert config.lire_obligatoire("VV_TEST_NOM") == "valeur"


def test_lire_obligatoire_variable_absente_leve_une_erreur(monkeypatch):
    monkeypatch.delenv("VV_TEST_NOM", raising=False)
    with pytest.raises(config.ConfigurationManquante):
        config.lire_obligatoire("VV_TEST_NOM")


def test_lire_obligatoire_variable_vide_leve_une_erreur(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "")
    with pytest.raises(config.ConfigurationManquante):
        config.lire_obligatoire("VV_TEST_NOM")


def test_lire_obligatoire_variable_despaces_leve_une_erreur(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", "   ")
    with pytest.raises(config.ConfigurationManquante):
        config.lire_obligatoire("VV_TEST_NOM")


def test_lire_obligatoire_le_message_nomme_la_variable(monkeypatch):
    monkeypatch.delenv("VV_TEST_NOM", raising=False)
    with pytest.raises(config.ConfigurationManquante, match="VV_TEST_NOM"):
        config.lire_obligatoire("VV_TEST_NOM")


def test_lire_obligatoire_sans_nettoyage_garde_les_espaces(monkeypatch):
    monkeypatch.setenv("VV_TEST_NOM", " mot de passe ")
    assert config.lire_obligatoire("VV_TEST_NOM", nettoyer=False) == " mot de passe "


# --- chemin ------------------------------------------------------------------------------


def test_chemin_variable_vide_retombe_sur_donnees_du_depot(monkeypatch):
    monkeypatch.setenv("DONNEES_DIR", "")
    assert config.chemin("DONNEES_DIR", "donnees") == RACINE_ATTENDUE / "donnees"


def test_chemin_variable_absente_retombe_sur_donnees_du_depot(monkeypatch):
    monkeypatch.delenv("DONNEES_DIR", raising=False)
    assert config.chemin("DONNEES_DIR", "donnees") == RACINE_ATTENDUE / "donnees"


def test_chemin_variable_despaces_retombe_sur_le_defaut(monkeypatch):
    monkeypatch.setenv("JOURNAUX_DIR", "   ")
    assert config.chemin("JOURNAUX_DIR", "journaux") == RACINE_ATTENDUE / "journaux"


def test_chemin_relatif_est_calcule_depuis_la_racine_du_depot(monkeypatch):
    monkeypatch.setenv("DONNEES_DIR", "autre/sous-dossier")
    assert config.chemin("DONNEES_DIR", "donnees") == RACINE_ATTENDUE / "autre" / "sous-dossier"


def test_chemin_relatif_ne_depend_pas_du_dossier_courant(monkeypatch, tmp_path):
    monkeypatch.setenv("DONNEES_DIR", "autre")
    monkeypatch.chdir(tmp_path)
    assert config.chemin("DONNEES_DIR", "donnees") == RACINE_ATTENDUE / "autre"


def test_chemin_par_defaut_ne_depend_pas_du_dossier_courant(monkeypatch, tmp_path):
    monkeypatch.delenv("DONNEES_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert config.chemin("DONNEES_DIR", "donnees") == RACINE_ATTENDUE / "donnees"


def test_chemin_absolu_est_utilise_tel_quel(monkeypatch, tmp_path):
    absolu = tmp_path / "hors-depot" / "donnees"
    monkeypatch.setenv("DONNEES_DIR", str(absolu))
    assert config.chemin("DONNEES_DIR", "donnees") == absolu


def test_chemin_tilde_est_developpe_vers_le_dossier_personnel(monkeypatch, tmp_path):
    # HOME (Linux) et USERPROFILE (Windows) : on couvre les deux pour que le test passe partout.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("DONNEES_DIR", "~/mes-donnees")
    assert config.chemin("DONNEES_DIR", "donnees") == tmp_path / "mes-donnees"


def test_chemin_retire_les_espaces_autour_de_la_valeur(monkeypatch):
    monkeypatch.setenv("DONNEES_DIR", "  autre  ")
    assert config.chemin("DONNEES_DIR", "donnees") == RACINE_ATTENDUE / "autre"


def test_chemin_retourne_un_objet_path(monkeypatch):
    monkeypatch.delenv("DONNEES_DIR", raising=False)
    assert isinstance(config.chemin("DONNEES_DIR", "donnees"), Path)


# --- valeurs_secretes --------------------------------------------------------------------


@pytest.mark.parametrize(
    "nom",
    [
        "POSTGRES_PASSWORD",
        "DB_MOT_DE_PASSE",
        "API_TOKEN",
        "APP_SECRET",
        "SERVICE_API_KEY",
        "CLE_X_CLE",
        "db_password",  # la détection ne dépend pas de la casse du nom
    ],
)
def test_valeurs_secretes_repere_les_variables_secretes(monkeypatch, nom):
    monkeypatch.setenv(nom, "valeur-factice-xyz")
    assert "valeur-factice-xyz" in config.valeurs_secretes()


@pytest.mark.parametrize(
    "nom",
    ["POSTGRES_HOST", "POSTGRES_USER", "LOG_LEVEL", "OFF_API_BASE_URL", "DONNEES_DIR"],
)
def test_valeurs_secretes_ignore_les_variables_non_secretes(monkeypatch, nom):
    monkeypatch.setenv(nom, "valeur-non-secrete")
    assert "valeur-non-secrete" not in config.valeurs_secretes()


def test_valeurs_secretes_ignore_une_variable_secrete_vide(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "")
    assert config.valeurs_secretes() == []


def test_valeurs_secretes_sans_aucune_variable_secrete_retourne_liste_vide():
    # La fixture env_propre a retiré toutes les variables secrètes.
    assert config.valeurs_secretes() == []


def test_valeurs_secretes_ne_repete_pas_une_valeur_partagee(monkeypatch):
    monkeypatch.setenv("A_PASSWORD", "meme-valeur-factice")
    monkeypatch.setenv("B_TOKEN", "meme-valeur-factice")
    assert config.valeurs_secretes() == ["meme-valeur-factice"]


def test_valeurs_secretes_classe_les_plus_longues_en_premier(monkeypatch):
    monkeypatch.setenv("A_PASSWORD", "abc")
    monkeypatch.setenv("B_TOKEN", "abcdef-factice")
    monkeypatch.setenv("C_SECRET", "abcdef")
    assert config.valeurs_secretes() == ["abcdef-factice", "abcdef", "abc"]


def test_valeurs_secretes_garde_la_valeur_exacte_avec_caracteres_speciaux(monkeypatch):
    valeur = 'p$ss #mot "de" passe'
    monkeypatch.setenv("POSTGRES_PASSWORD", valeur)
    assert config.valeurs_secretes() == [valeur]
