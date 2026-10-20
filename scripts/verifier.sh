#!/usr/bin/env bash
# Contrôle de bon fonctionnement : UNE seule commande, depuis la racine du dépôt :
#
#     bash scripts/verifier.sh
#
# Le script lance scripts/verification.py DANS le conteneur de travail (service « travail » de
# compose.yaml). Docker Compose démarre la base PostgreSQL si elle ne tourne pas, attend qu'elle
# soit prête, puis passe les variables du .env au conteneur. Le contrôle vérifie PostgreSQL
# (joint par le nom du service Compose), Spark et l'API Open Food Facts.
# Code de sortie : 0 si tout est OK, différent de 0 sinon.
#
# Équivalent à la main (avec sudo tant que ton utilisateur n'est pas dans le groupe docker) :
#     sudo docker compose run --rm -T travail python scripts/verification.py

set -euo pipefail
# shellcheck source=scripts/_commun.sh
source "$(dirname "${BASH_SOURCE[0]}")/_commun.sh"

[ -f "$RACINE/.env" ] || echec "Le fichier .env est absent. Lance d'abord : bash scripts/installer.sh"

choisir_docker
cd "$RACINE"

# Pas de « exec » : le code de sortie du contrôle est simplement renvoyé tel quel.
# --rm : le conteneur de travail est supprimé après le contrôle (la base, elle, reste).
# -T : pas de terminal, la sortie reste identique même redirigée vers un fichier.
compose run --rm -T travail python scripts/verification.py
