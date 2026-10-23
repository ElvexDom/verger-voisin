"""Fixtures communes aux tests du socle (configuration, journalisation, contrôle).

Aucun test ne dépend de PostgreSQL, de Spark ni du réseau. Toutes les valeurs « secrètes »
utilisées dans ces tests sont factices.
"""

from __future__ import annotations

import logging

import pytest

from verger_voisin import config


@pytest.fixture(autouse=True)
def env_propre(monkeypatch):
    """Retire de l'environnement toute variable qui pourrait fausser un test.

    On supprime les variables du projet et toute variable au nom « secret », pour que les
    tests soient identiques sur le poste de ElvexDom, sur le VPS ou ailleurs.
    """
    import os

    noms_projet = (
        "LOG_LEVEL",
        "LOG_FORMAT",
        "JOURNAUX_DIR",
        "DONNEES_DIR",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    )
    for nom in list(os.environ):
        est_secret = any(mot in nom.upper() for mot in config.MOTS_SECRETS)
        if est_secret or nom in noms_projet:
            monkeypatch.delenv(nom, raising=False)


@pytest.fixture(autouse=True)
def journal_propre():
    """Ferme et retire les handlers du logger du projet après chaque test.

    Sans cela, un fichier de journal reste ouvert (blocage sous Windows) et les handlers
    s'empilent d'un test à l'autre.
    """
    yield
    journal = logging.getLogger("verger_voisin")
    for handler in list(journal.handlers):
        journal.removeHandler(handler)
        handler.close()
