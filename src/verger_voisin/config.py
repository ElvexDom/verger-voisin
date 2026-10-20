"""Lecture de la configuration depuis les variables d'environnement.

Toute la configuration passe par des variables d'environnement (voir .env.example).
Les scripts shell (scripts/verifier.sh) chargent le fichier .env avant de lancer Python.
Aucune valeur n'est écrite dans le code.
"""

from __future__ import annotations

import os
from pathlib import Path

# Racine du dépôt : src/verger_voisin/config.py -> on remonte de deux dossiers.
RACINE_DEPOT = Path(__file__).resolve().parents[2]

# Une variable dont le nom contient un de ces mots est considérée comme secrète :
# sa valeur est masquée dans les journaux et à l'écran.
MOTS_SECRETS = ("PASSWORD", "MOT_DE_PASSE", "TOKEN", "SECRET", "_KEY", "_CLE")


class ConfigurationManquante(Exception):
    """Une variable obligatoire est absente ou vide."""


def lire(nom: str, defaut: str = "", nettoyer: bool = True) -> str:
    """Retourne la valeur de la variable `nom`, ou `defaut` si elle est absente ou vide."""
    valeur = os.environ.get(nom, "")
    if nettoyer:
        valeur = valeur.strip()
    return valeur if valeur != "" else defaut


def lire_obligatoire(nom: str, nettoyer: bool = True) -> str:
    """Comme `lire`, mais lève ConfigurationManquante si la variable est vide."""
    valeur = lire(nom, "", nettoyer)
    if valeur == "":
        raise ConfigurationManquante(
            f"La variable {nom} est absente ou vide : renseigne-la dans le fichier .env."
        )
    return valeur


def chemin(nom: str, defaut_relatif: str) -> Path:
    """Retourne un dossier lu dans la variable `nom`.

    - variable vide : `defaut_relatif`, calculé depuis la racine du dépôt ;
    - chemin relatif : calculé depuis la racine du dépôt (pas depuis le dossier courant) ;
    - chemin absolu ou commençant par ~ : utilisé tel quel.
    """
    valeur = lire(nom, defaut_relatif)
    dossier = Path(valeur).expanduser()
    if not dossier.is_absolute():
        dossier = RACINE_DEPOT / dossier
    return dossier


def valeurs_secretes() -> list[str]:
    """Liste des valeurs non vides des variables secrètes présentes dans l'environnement."""
    secrets = []
    for nom, valeur in os.environ.items():
        if valeur and any(mot in nom.upper() for mot in MOTS_SECRETS):
            secrets.append(valeur)
    # Les plus longues d'abord, pour qu'un secret contenant un autre soit masqué en entier.
    return sorted(set(secrets), key=len, reverse=True)
