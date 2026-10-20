#!/usr/bin/env bash
# Fonctions communes aux scripts de Verger Voisin.
# Ce fichier est chargé par installer.sh et verifier.sh (via « source »), il ne se lance pas seul.
# Ces scripts tournent sur l'hôte (le serveur) : ils pilotent Docker Compose, ils ne lancent
# jamais Python, Java ni PostgreSQL directement.

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info()     { printf '[INFO]      %s\n' "$*"; }
ok()       { printf '[ OK ]      %s\n' "$*"; }
avertir()  { printf '[ATTENTION] %s\n' "$*" >&2; }
erreur()   { printf '[ERREUR]    %s\n' "$*" >&2; }
echec()    { erreur "$*"; exit 1; }

# Charge un fichier .env dans l'environnement SANS l'exécuter comme un script :
# chaque ligne NOM=valeur est lue telle quelle (les symboles $, #, espaces sont donc sans danger
# dans un mot de passe). Les lignes vides et les lignes commençant par # sont ignorées.
# Les guillemets simples ou doubles qui entourent toute la valeur sont retirés.
# Les valeurs du .env l'emportent sur les variables déjà présentes dans l'environnement.
charger_env() {
    local fichier="$1" ligne cle valeur
    local re_double='^"(.*)"$' re_simple="^'(.*)'\$"
    while IFS= read -r ligne || [ -n "$ligne" ]; do
        ligne="${ligne%$'\r'}"                       # fins de ligne Windows
        ligne="${ligne#"${ligne%%[![:space:]]*}"}"   # espaces de début de ligne
        case "$ligne" in
            ''|'#'*) continue ;;
        esac
        if [[ "$ligne" != *=* ]]; then
            avertir "Ligne ignorée dans $(basename "$fichier") (pas de signe =)."
            continue
        fi
        cle="${ligne%%=*}"
        valeur="${ligne#*=}"
        cle="${cle%"${cle##*[![:space:]]}"}"         # espaces de fin du nom
        if [[ ! "$cle" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            avertir "Ligne ignorée dans $(basename "$fichier") (nom de variable invalide)."
            continue
        fi
        if [[ "$valeur" =~ $re_double ]]; then
            valeur="${BASH_REMATCH[1]}"
        elif [[ "$valeur" =~ $re_simple ]]; then
            valeur="${BASH_REMATCH[1]}"
        fi
        export "$cle=$valeur"
    done < "$fichier"
}

# --- Docker -------------------------------------------------------------------------------------

# Commande Docker à utiliser : « docker », ou « sudo docker » tant que ton utilisateur n'est pas
# dans le groupe « docker ». Remplie par choisir_docker.
DOCKER=()

# Vérifie que Docker et Docker Compose sont présents et que le démon répond, puis remplit DOCKER.
# N'installe rien et ne modifie rien.
choisir_docker() {
    command -v docker >/dev/null 2>&1 \
        || echec "La commande docker est introuvable. Docker doit être installé sur le serveur (voir docs/installation.md, section 2)."
    if docker info >/dev/null 2>&1; then
        DOCKER=(docker)
    else
        command -v sudo >/dev/null 2>&1 \
            || echec "Docker ne répond pas pour ton utilisateur et sudo est introuvable. Ajoute ton utilisateur au groupe docker ou installe sudo."
        info "Ton utilisateur n'est pas dans le groupe « docker » (ou le démon est arrêté) : les commandes Docker passent par sudo. Le mot de passe de ton utilisateur peut être demandé."
        sudo -v || echec "sudo a été refusé."
        sudo docker info >/dev/null 2>&1 \
            || echec "Le démon Docker ne répond pas. Regarde : sudo systemctl status docker"
        DOCKER=(sudo docker)
    fi
    "${DOCKER[@]}" compose version >/dev/null 2>&1 \
        || echec "Le plugin Docker Compose est introuvable (la commande « docker compose version » échoue)."
}

# Lance « docker compose » sur le fichier compose.yaml de ce dépôt, d'où que le script soit lancé.
# Le fichier .env de la racine du dépôt est lu automatiquement par Docker Compose.
compose() {
    "${DOCKER[@]}" compose --project-directory "$RACINE" -f "$RACINE/compose.yaml" "$@"
}

# Transforme un chemin en chemin absolu : un chemin relatif est calculé depuis la racine du dépôt.
chemin_absolu() {
    case "$1" in
        /*)   printf '%s' "$1" ;;
        "~")  printf '%s' "$HOME" ;;
        "~/"*) printf '%s/%s' "$HOME" "${1#"~/"}" ;;
        *)    printf '%s/%s' "$RACINE" "$1" ;;
    esac
}
