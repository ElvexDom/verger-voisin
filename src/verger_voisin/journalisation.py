"""Configuration de la journalisation.

Le niveau, le format et le dossier des journaux sont réglés par variables d'environnement
(LOG_LEVEL, LOG_FORMAT, JOURNAUX_DIR). Les journaux sont écrits hors de Git.

Règle du projet : ni secret ni donnée personnelle dans les journaux. Un filtre masque donc
la valeur de toute variable secrète (mot de passe, jeton...) si elle apparaissait dans un
message. Ce filtre est une dernière protection : le plus sûr reste de ne jamais journaliser
un secret ou une donnée personnelle.
"""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from verger_voisin.config import chemin, lire, valeurs_secretes

NOM_LOGGER = "verger_voisin"
NIVEAUX = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
FORMATS = ("texte", "json")
FORMAT_TEXTE = "%(asctime)s %(levelname)s %(name)s %(message)s"

# Rotation du fichier : au-delà de cette taille, un nouveau fichier est ouvert et les
# anciens sont conservés (choix de taille arbitraire, sans enjeu pour le lot 1).
TAILLE_MAX_OCTETS = 5_000_000
NB_FICHIERS_CONSERVES = 3


def masquer(texte: str) -> str:
    """Remplace par *** toute valeur secrète présente dans `texte`."""
    for secret in valeurs_secretes():
        texte = texte.replace(secret, "***")
    return texte


class FiltreSecrets(logging.Filter):
    """Masque les valeurs secrètes dans le message et dans la trace d'une exception."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = masquer(record.getMessage())
        except Exception:  # message mal formé : on ne masque rien plutôt que de planter
            record.msg = masquer(str(record.msg))
        record.args = ()
        if record.exc_info:
            trace = logging.Formatter().formatException(record.exc_info)
            record.exc_text = masquer(trace)
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = masquer(record.exc_text)
        return True


class FormatJson(logging.Formatter):
    """Une ligne JSON par événement."""

    def format(self, record: logging.LogRecord) -> str:
        evenement = {
            "horodatage": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "niveau": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_text:
            evenement["exception"] = record.exc_text
        return json.dumps(evenement, ensure_ascii=False)


def configurer_journalisation(
    nom_fichier: str = "verger-voisin.log", console: bool = False
) -> tuple[logging.Logger, Path | None]:
    """Configure et retourne le logger du projet, avec le chemin du fichier de journal.

    Peut être appelée plusieurs fois sans empiler les handlers. Si le dossier des journaux
    n'est pas utilisable, la journalisation continue sans fichier (chemin retourné : None)
    et un avertissement est affiché.
    """
    niveau = lire("LOG_LEVEL", "INFO").upper()
    if niveau not in NIVEAUX:
        print(f"[ATTENTION] LOG_LEVEL='{niveau}' inconnu : INFO utilisé.", file=sys.stderr)
        niveau = "INFO"
    format_choisi = lire("LOG_FORMAT", "texte").lower()
    if format_choisi not in FORMATS:
        print(f"[ATTENTION] LOG_FORMAT='{format_choisi}' inconnu : texte utilisé.", file=sys.stderr)
        format_choisi = "texte"

    formateur: logging.Formatter
    formateur = FormatJson() if format_choisi == "json" else logging.Formatter(FORMAT_TEXTE)

    journal = logging.getLogger(NOM_LOGGER)
    journal.setLevel(getattr(logging, niveau))
    journal.propagate = False
    for ancien in list(journal.handlers):
        journal.removeHandler(ancien)
        ancien.close()

    fichier_journal: Path | None = None
    try:
        dossier = chemin("JOURNAUX_DIR", "journaux")
        dossier.mkdir(parents=True, exist_ok=True)
        fichier_journal = dossier / nom_fichier
        handler_fichier = RotatingFileHandler(
            fichier_journal,
            maxBytes=TAILLE_MAX_OCTETS,
            backupCount=NB_FICHIERS_CONSERVES,
            encoding="utf-8",
        )
        handler_fichier.setFormatter(formateur)
        handler_fichier.addFilter(FiltreSecrets())
        journal.addHandler(handler_fichier)
    except OSError as erreur:
        fichier_journal = None
        print(
            f"[ATTENTION] Journal dans un fichier impossible ({type(erreur).__name__}). "
            "Vérifie JOURNAUX_DIR et les droits du dossier.",
            file=sys.stderr,
        )

    if console or fichier_journal is None:
        handler_console = logging.StreamHandler(sys.stderr)
        handler_console.setFormatter(formateur)
        handler_console.addFilter(FiltreSecrets())
        journal.addHandler(handler_console)

    return journal, fichier_journal
