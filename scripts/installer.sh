#!/usr/bin/env bash
# Installation de l'environnement de Verger Voisin avec Docker (Ubuntu 26.04 LTS).
#
# Depuis la racine du dépôt, SANS sudo (le script appelle sudo lui-même quand il le faut) :
#
#     bash scripts/installer.sh
#
# Ce que fait le script (la même procédure est décrite pas à pas dans docs/installation.md) :
#   1. vérifie que Docker et Docker Compose sont présents (il n'installe rien sur le serveur) ;
#   2. crée le fichier .env à partir de .env.example s'il manque (sans y écrire de secret),
#      puis contrôle les variables indispensables ;
#   3. crée les dossiers de données et de journaux sur le serveur ;
#   4. construit l'image de l'environnement de travail (Python, Java, PySpark) ;
#   5. démarre la base PostgreSQL dans son conteneur et attend qu'elle soit prête ;
#   6. synchronise le mot de passe de l'utilisateur de la base avec le .env et crée la base si
#      elle manque ;
#   7. affiche les versions réellement installées dans les conteneurs.
#
# Le script peut être relancé autant de fois que nécessaire :
#   - ce qui existe déjà n'est pas recréé ;
#   - il ne supprime JAMAIS rien : ni conteneur, ni volume, ni dossier, ni donnée ;
#   - seul le mot de passe de l'utilisateur de la base est remis à la valeur du .env.
# Aucun secret n'est écrit dans un fichier suivi par Git, ni affiché à l'écran.

set -Eeuo pipefail
# shellcheck source=scripts/_commun.sh
source "$(dirname "${BASH_SOURCE[0]}")/_commun.sh"

trap 'erreur "Arrêt à la ligne $LINENO. Corrige le problème (voir « Dépannage » dans docs/installation.md) puis relance : bash scripts/installer.sh"' ERR

# Écrit NOM=valeur dans .env (remplace la ligne si elle existe, sinon l'ajoute) et dans
# l'environnement du script. Réservé à des valeurs non secrètes composées de chiffres.
definir_variable_env() {
    local nom="$1" valeur="$2"
    [[ "$valeur" =~ ^[0-9]+$ ]] || echec "Valeur inattendue pour $nom (un nombre est attendu)."
    if grep -q "^${nom}=" "$RACINE/.env"; then
        sed -i "s/^${nom}=.*/${nom}=${valeur}/" "$RACINE/.env"
    else
        printf '%s=%s\n' "$nom" "$valeur" >> "$RACINE/.env"
    fi
    # Docker Compose donne la priorité aux variables du shell sur le .env : on met les deux à jour.
    export "$nom=$valeur"
}

# psql dans le conteneur de la base, avec l'utilisateur du .env (connexion locale du conteneur).
# On se connecte à la base « postgres », qui existe toujours, pour pouvoir créer la nôtre.
psql_conteneur() {
    compose exec -T postgres psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres "$@"
}

# --- Étape 0 : contrôles préalables ------------------------------------------------------------

echo "=== Installation de Verger Voisin (Docker) ==="
info "Dépôt : $RACINE"

[ "$(id -u)" -ne 0 ] || echec "Ne lance pas ce script en root ni avec sudo : les fichiers créés appartiendraient à root. Lance-le avec ton utilisateur, il appellera sudo lui-même pour Docker si c'est nécessaire."

if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    if [ "${ID:-}" != "ubuntu" ] || [ "${VERSION_ID:-}" != "26.04" ]; then
        avertir "Système détecté : ${PRETTY_NAME:-inconnu}. La procédure est prévue pour Ubuntu 26.04 LTS avec Docker : à tes risques."
    else
        ok "Système : ${PRETTY_NAME}"
    fi
fi

# --- Étape 1 : Docker et Docker Compose --------------------------------------------------------

choisir_docker
ok "$("${DOCKER[@]}" --version)"
ok "$("${DOCKER[@]}" compose version)"

# --- Étape 2 : le .env -------------------------------------------------------------------------

if [ ! -f "$RACINE/.env" ]; then
    [ -f "$RACINE/.env.example" ] || echec "Le modèle .env.example est introuvable dans le dépôt."
    cp "$RACINE/.env.example" "$RACINE/.env"
    ok "Fichier .env créé à partir de .env.example (aucun secret n'y est écrit par le script)."
fi
chmod 600 "$RACINE/.env"
charger_env "$RACINE/.env"
ok "Fichier .env lu (droits restreints à ton utilisateur)."

manquantes=()
for variable in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
    [ -n "${!variable:-}" ] || manquantes+=("$variable")
done
if [ "${#manquantes[@]}" -gt 0 ]; then
    echec "Variable(s) vide(s) dans .env : ${manquantes[*]}. Ouvre le fichier (nano .env), renseigne-les, puis relance : bash scripts/installer.sh"
fi
# Les noms sont insérés dans des commandes SQL : on n'accepte que des caractères sûrs.
[[ "$POSTGRES_DB" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || echec "POSTGRES_DB doit contenir seulement des minuscules, chiffres et _ (63 caractères au plus, sans commencer par un chiffre)."
[[ "$POSTGRES_USER" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || echec "POSTGRES_USER doit contenir seulement des minuscules, chiffres et _ (63 caractères au plus, sans commencer par un chiffre)."
# Docker Compose relit le .env : $, guillemets, # et espaces y seraient interprétés.
[[ "$POSTGRES_PASSWORD" =~ ^[A-Za-z0-9._+=:,-]+$ ]] || echec "POSTGRES_PASSWORD ne doit contenir que des lettres, des chiffres et les symboles . _ + = : , - (pas de \$, de guillemets, de # ni d'espace), pour être lu correctement par Docker Compose."
if [ "${#POSTGRES_PASSWORD}" -lt 12 ]; then
    avertir "POSTGRES_PASSWORD fait moins de 12 caractères : un mot de passe plus long est préférable."
fi

# Identifiants de l'utilisateur du conteneur : ceux de l'utilisateur qui lance le script.
[ -n "${CONTENEUR_UID:-}" ] || definir_variable_env CONTENEUR_UID "$(id -u)"
[ -n "${CONTENEUR_GID:-}" ] || definir_variable_env CONTENEUR_GID "$(id -g)"
[[ "$CONTENEUR_UID" =~ ^[0-9]+$ && "$CONTENEUR_UID" -ne 0 ]] || echec "CONTENEUR_UID doit être un nombre différent de 0 (le conteneur ne tourne jamais en root)."
[[ "$CONTENEUR_GID" =~ ^[0-9]+$ && "$CONTENEUR_GID" -ne 0 ]] || echec "CONTENEUR_GID doit être un nombre différent de 0."
ok "Utilisateur du conteneur de travail : uid $CONTENEUR_UID, gid $CONTENEUR_GID."

# --- Étape 3 : dossiers de données et de journaux sur le serveur -------------------------------

for variable in DONNEES_HOTE JOURNAUX_HOTE; do
    case "${!variable:-}" in
        "~"*) echec "$variable ne doit pas commencer par ~ : écris un chemin absolu (/...) ou relatif (./...)." ;;
    esac
done
donnees_hote="$(chemin_absolu "${DONNEES_HOTE:-./donnees}")"
journaux_hote="$(chemin_absolu "${JOURNAUX_HOTE:-./journaux}")"
mkdir -p "$donnees_hote/export" "$donnees_hote/parquet" "$donnees_hote/sorties" "$journaux_hote"
ok "Dossier des données : $donnees_hote (sous-dossiers export, parquet, sorties)"
ok "Dossier des journaux : $journaux_hote"
case "$donnees_hote" in
    "$RACINE"/*) info "Le dossier des données est dans le dépôt : son contenu est ignoré par Git (.gitignore)." ;;
    *) info "Le dossier des données est hors du dépôt : Git ne le voit pas." ;;
esac

# --- Étape 4 : image de l'environnement de travail ---------------------------------------------

# Contrôle de la syntaxe de compose.yaml avant tout (n'affiche rien : la sortie contiendrait le mot de passe).
compose --profile travail config --quiet
ok "compose.yaml est valide."

info "Construction de l'image de travail (Python, Java, PySpark) : la première fois, cela peut prendre plusieurs minutes..."
compose build travail
ok "Image de travail construite (ou déjà à jour)."

# --- Étape 5 : base PostgreSQL ----------------------------------------------------------------

info "Démarrage de PostgreSQL (conteneur) et attente qu'il soit prêt (2 minutes au plus)..."
compose up -d --wait --wait-timeout 120 postgres
ok "PostgreSQL répond (conteneur « postgres » en bonne santé)."

# --- Étape 6 : utilisateur et base -------------------------------------------------------------

# Au tout premier démarrage, l'image crée la base et l'utilisateur du .env. Aux démarrages
# suivants, elle ignore un mot de passe modifié dans le .env : on le resynchronise ici.
if ! sortie="$(printf "ALTER ROLE \"%s\" PASSWORD '%s';\n" "$POSTGRES_USER" "$POSTGRES_PASSWORD" | psql_conteneur 2>&1)"; then
    erreur "Connexion à PostgreSQL impossible avec l'utilisateur « $POSTGRES_USER ». Message (mot de passe masqué) :"
    printf '%s\n' "${sortie//"$POSTGRES_PASSWORD"/***}" >&2
    echec "Si le volume de la base a été créé avec un autre POSTGRES_USER, remets ce nom dans .env (voir « Dépannage » dans docs/installation.md). Le script ne supprime jamais de volume."
fi
ok "Le mot de passe de l'utilisateur « $POSTGRES_USER » est synchronisé avec le .env."

base_existe="$(psql_conteneur -tA -c "SELECT 1 FROM pg_database WHERE datname = '${POSTGRES_DB}'")"
if [ "$base_existe" = "1" ]; then
    ok "La base « $POSTGRES_DB » existe : elle n'est pas touchée."
else
    psql_conteneur -c "CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\""
    ok "Base « $POSTGRES_DB » créée (propriétaire : $POSTGRES_USER)."
fi

# --- Récapitulatif --------------------------------------------------------------------------------

echo
echo "=== Récapitulatif (versions réellement installées dans les conteneurs) ==="
versions_travail="$(compose run --rm --no-deps -T travail sh -c 'python --version 2>&1; java -version 2>&1 | sed -n "1p"; printf "PySpark %s\n" "$(pip show pyspark 2>/dev/null | sed -n "s/^Version: //p")"')"
while IFS= read -r ligne; do info "Travail    : $ligne"; done <<< "$versions_travail"
info "PostgreSQL : $(psql_conteneur -tA -c 'SHOW server_version')"
info "Port publié par la base sur le serveur : aucun (voir « docker compose ps » : la colonne PORTS ne doit pas contenir de flèche « -> »)."
avertir "Vérifie que cette version de Java est bien compatible avec cette version de PySpark (documentation de PySpark). Sinon, change JAVA_PAQUET (ou IMAGE_PYTHON) dans .env et relance."
echo
ok "Installation terminée."
info "Étape suivante : bash scripts/verifier.sh"
