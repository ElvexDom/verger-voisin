# Dockerfile : environnement de travail de Verger Voisin (Python + Java + PySpark).
#
# Cette image contient les outils et les dépendances, PAS le code : le code (src/, scripts/,
# tests/) est monté dans le conteneur par compose.yaml. Elle ne se reconstruit donc que si les
# versions ci-dessous ou les fichiers requirements*.txt changent.
#
# Les versions viennent de variables (arguments de construction) : compose.yaml les lit dans
# le fichier .env, voir .env.example. Elles se changent sans toucher à ce fichier.
#
# HYPOTHÈSES À VÉRIFIER SUR LE SERVEUR (aucune n'a été testée par Octet, qui n'exécute rien) :
#   - l'étiquette python:3.12-slim-trixie existe sur Docker Hub (image officielle Python 3.12,
#     système Debian « trixie ») ;
#   - le paquet openjdk-21-jre-headless existe dans ce Debian (apt-cache policy dans l'image) ;
#   - la version de PySpark installée par pip accepte Python 3.12 et Java 21 (documentation de
#     PySpark, page « Installation » / « Requirements » de la version installée) ;
#   - les paquets de requirements.txt ont des versions installables avec Python 3.12.
# Si l'une est fausse, change la variable correspondante dans .env et reconstruis l'image.

ARG IMAGE_PYTHON=python:3.12-slim-trixie
FROM ${IMAGE_PYTHON}

# Les ARG déclarés avant FROM ne sont pas visibles après : on déclare ceux dont on a besoin ici.
ARG JAVA_PAQUET=openjdk-21-jre-headless
# Identifiants de l'utilisateur du conteneur (non root). Ils doivent être ceux de ton
# utilisateur sur le serveur, pour que le conteneur puisse écrire dans les dossiers
# de données et de journaux montés depuis l'hôte (scripts/installer.sh les renseigne).
ARG CONTENEUR_UID=1000
ARG CONTENEUR_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Java (nécessaire à Spark). Pas de recommandations apt, liste des paquets effacée ensuite.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates "${JAVA_PAQUET}" \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur non root, et dossiers de travail (code, données, journaux).
RUN groupadd --gid "${CONTENEUR_GID}" verger \
    && useradd --uid "${CONTENEUR_UID}" --gid "${CONTENEUR_GID}" --create-home --shell /bin/bash verger \
    && mkdir -p /app /donnees /journaux \
    && chown verger:verger /app /donnees /journaux

# Dépendances Python (couche séparée : elle n'est refaite que si les fichiers changent).
COPY requirements.txt requirements-dev.txt /tmp/dependances/
RUN pip install -r /tmp/dependances/requirements-dev.txt \
    && rm -rf /tmp/dependances

USER verger
WORKDIR /app

# Par défaut, l'image lance le contrôle de bon fonctionnement.
CMD ["python", "scripts/verification.py"]
