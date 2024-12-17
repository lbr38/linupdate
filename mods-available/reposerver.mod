#!/usr/bin/env bash
# Module reposerver
# Module permettant de se ratacher à un serveur de repo exécutant repomanager 

# Fichier de configuration du module
MOD_CONF="${MODULES_CONF_DIR}/reposerver.conf"

#### FONCTIONS ####

# Enregistrement auprès d'un serveur Repomanager
function register
{
    # Check that API key is set
    if [ -z "$REPOSERVER_API_KEY" ];then
        echo -e " [$YELLOW ERROR $RESET] Cannot register to reposerver. You must specify an API key from a Repomanager user account."
        ERROR_STATUS=1
        clean_exit
    fi

    # Au préalable, récupération des informations concernant le serveur repomanager
    # Si la configuration est incomplète alors on quitte
    getModConf

    if [ -z "$REPOSERVER_URL" ];then
        echo -e " [$YELLOW ERROR $RESET] Cannot register to reposerver. You must configure target reposerver URL."
        ERROR_STATUS=1
        clean_exit
    fi

    # On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
    testConnection

    # Tentative d'enregistrement
    # Si l'enregistrement fonctionne, on récupère un id et un token
    echo -ne " Registering to ${YELLOW}${REPOSERVER_URL}${RESET}: "
    REGISTER_HOSTNAME=$(hostname -f)

    if [ -z "$REGISTER_HOSTNAME" ];then
        echo -e "[$YELLOW ERROR $RESET] Cannot determine this host's hostname."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si on n'a pas précisé d'adresse IP à enregistrer alors on tente de récupérer l'adresse IP publique de cette machine
    if [ -z "$REGISTER_IP" ];then
        REGISTER_IP=$(curl -s -4 ifconfig.io)
        if [ -z "$REGISTER_IP" ];then
            echo -e "[$YELLOW ERROR $RESET] Cannot determine this host's IP address."
            ERROR_STATUS=1
            clean_exit
        fi
    fi

    CURL=$(curl -L --post301 -s -q -H "Authorization: Bearer $REPOSERVER_API_KEY" -H "Content-Type: application/json" -X POST -d "{\"ip\":\"$REGISTER_IP\",\"hostname\":\"$REGISTER_HOSTNAME\"}" "${REPOSERVER_URL}/api/v2/host/registering" 2> /dev/null)

    # Parsage de la réponse et affichage des messages si il y en a
    curl_result_parse

    # Si il y a eu des erreurs suite à la requete alors on quitte
    if [ "$CURL_ERROR" -gt "0" ];then
        clean_exit
    fi

    # Le serveur a dû renvoyer un id et token d'identification qu'on récupère
    REGISTER_ID=$(jq -r '.results.id' <<< "$CURL")
    REGISTER_TOKEN=$(jq -r '.results.token' <<< "$CURL")

    # Si l'enregistrement a été effectué, on vérifie qu'on a bien pu récupérer un id
    if [ -z "$REGISTER_ID" ] || [ "$REGISTER_ID" == "null" ];then
        echo -e "[$YELLOW ERROR $RESET] Unable to retrieve an authentication Id from registering."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si l'enregistrement a été effectué, on vérifie qu'on a bien pu récupérer un token
    if [ -z "$REGISTER_TOKEN" ] || [ "$REGISTER_TOKEN" == "null" ];then
        echo -e "[$YELLOW ERROR $RESET] Unable to retrieve an authentication token from registering."
        ERROR_STATUS=1
        clean_exit
    fi

    # Enfin si tout s'est bien passé jusque là, on ajoute l'id et le token dans le fichier de conf et on affiche un message
    sed -i "s/^ID.*/ID=\"$REGISTER_ID\"/g" $MOD_CONF
    sed -i "s/^TOKEN.*/TOKEN=\"$REGISTER_TOKEN\"/g" $MOD_CONF 
    clean_exit
}

# Suppression de l'enregistrement auprès d'un serveur Repomanager
function unregister
{
    # Au préalable, récupération des informations concernant le serveur repomanager
    # Si la configuration est incomplète alors on quitte
    getModConf

    if [ -z "$REPOSERVER_URL" ];then
        echo -e " [$YELLOW ERROR $RESET] Cannot delete registering from reposerver. You must configure target reposerver URL."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si pas d'ID configuré alors on quitte
    if [ -z "$HOST_ID" ];then
        echo -e " [$YELLOW ERROR $RESET] This host has no authentication Id."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si pas de token configuré alors on quitte
    if [ -z "$TOKEN" ];then
        echo -e " [$YELLOW ERROR $RESET] This host has no authentication token."
        ERROR_STATUS=1
        clean_exit
    fi

    # On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
    testConnection

    # Tentative de suppression de l'enregistrement
    echo -ne " Unregistering from ${YELLOW}${REPOSERVER_URL}${RESET}: "
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -H "Content-Type: application/json" -X DELETE "${REPOSERVER_URL}/api/v2/host/registering" 2> /dev/null)
 
    # Parsage de la réponse et affichage des messages si il y en a
    curl_result_parse

    # Si il y a eu des erreurs suite à la requete alors on quitte
    if [ "$CURL_ERROR" -gt "0" ];then
        clean_exit
    fi

    clean_exit
}

# Teste la connexion au serveur Repomanager
function testConnection
{
    if [ ! -z "$REPOSERVER_API_KEY" ];then
        AUTH_HEADER="Authorization: Bearer $REPOSERVER_API_KEY"
    fi

    if [ ! -z "$HOST_ID" ] && [ ! -z "$TOKEN" ];then
        AUTH_HEADER="Authorization: Host $HOST_ID:$TOKEN"
    fi

    if ! curl -L --post301 -s -q -H "$AUTH_HEADER" -H "Content-Type: application/json" -X GET "${REPOSERVER_URL}/api/v2/status" > /dev/null;then
        echo -e " [$YELLOW ERROR $RESET] Cannot reach reposerver from ${YELLOW}${REPOSERVER_URL}${RESET}"
        ERROR_STATUS=1
        clean_exit
    fi
}

# Analyse le retour d'une requête curl et affiche les éventuels message d'erreurs / de succès rencontrés
function curl_result_parse
{
    CURL_ERROR="0";
    UPDATE_RETURN=""

    # On récupère le code retour si il y en a un
    if echo "$CURL" | grep -q ".return";then
        UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")
    fi

    # Si le code retour est vide il y a probablement eu une erreur côté serveur.
    if [ -z "$UPDATE_RETURN" ];then
        echo -e "[$YELLOW ERROR $RESET] Reposerver has sent no return code, unknown error."
        ERROR_STATUS=1
        CURL_ERROR=1
        return
    fi

    # Récupération et affichage des messages

    OLD_IFS=$IFS
    IFS=$'\n'    

    # Si il y a eu des messages d'erreur on les affiche
    if echo "$CURL" | grep -q "message_error";then
        # array
        UPDATE_MESSAGE_ERROR=($(jq -r '.message_error[]' <<< "$CURL"))

        # $UPDATE_MESSAGE_ERROR est un array pouvant contenir plusieurs messages d'erreurs
        for MESSAGE in "${UPDATE_MESSAGE_ERROR[@]}"; do
            echo -e "[$YELLOW ERROR $RESET] $MESSAGE"
        done
        ERROR_STATUS=1
        CURL_ERROR=2
    fi

    # Si il y a eu des message de succès on les affiche
    if echo "$CURL" | grep -q '"message"';then
        # array
        UPDATE_MESSAGE_SUCCESS=($(jq -r '.message[]' <<< "$CURL"))

        # $UPDATE_MESSAGE_SUCCESS est un array pouvant contenir plusieurs messages d'erreurs
        for MESSAGE in "${UPDATE_MESSAGE_SUCCESS[@]}"; do
            echo -e "[$GREEN OK $RESET] $MESSAGE"
        done
    fi

    IFS=$OLD_IFS
}

# Aide
function mod_help
{
    echo -e "${YELLOW}reposerver${RESET} module params:\n\n"
    echo -e " Main:"
    echo -e "  --url http(s)://...           → Configure target reposerver URL"
    echo -e "  --fail-level 1|2|3            → Configure module criticality (between 1 and 3)"
    echo -e "                                  1: linupdate stops no matter the module error (disabled module, the target reposerver does not handle the same package type, minor or critical error...)"
    echo -e "                                  2: linupdate stops on module critical error (continues on minor error)"
    echo -e "                                  3: linupdate continues even in case of module critical error"
    echo -e "  --register                    → Register this host to reposerver"
    echo -e "  --unregister                  → Unregister this host from reposerver"
    echo -e "  --get-server-conf             → Get reposerver global configuration."
    echo -e "  --get-profile-packages-conf   → Get profile packages excludes configurtion from reposerver."
    echo -e "  --get-profile-repos           → Get repos sources configuration from reposerver."
    echo -e "  --send-general-status         → Send host global informations to reposerver (OS, version, kernel..)"
    echo -e "  --send-full-history           → Send host packages events history to reposerver (installation, update, uninstallation...)"
    echo -e "  --send-packages-status        → Send host packages informations (installed, available) to reposerver"
    echo -e "  --send-full-status            → Execute the tree previous parameters"
    echo -e ""
    echo -e " Agent:"
    echo -e "  --enable-agent                → Enable reposerver module agent"
    echo -e "                                  This agent will regularly send informations about this host to reposerver (global informations, packages informations...)"
    echo -e "  --disable-agent               → Disable reposerver module agent"
    echo -e "  --agent-watch-enable          → Enable reposerver requests watching"
    echo -e "  --agent-watch-disable         → Disable reposerver requests watching"
    echo -e "  --agent-watch-int             → Specify the network interface on which to watch requests comming from reposerver"
    echo -e ""
}

# Activation du module
function mod_enable
{
    cd ${MODULES_ENABLED_DIR}/ &&
    ln -sfn "../mods-available/${MODULE}.mod" &&
    return 0
}

# Désactivation du module
function mod_disable
{
    rm "${MODULES_ENABLED_DIR}/reposerver.mod" -f &&
    return 0
}

# Installation du module
function mod_install
{
    # Copie du fichier de configuration
    mkdir -p "${MODULES_CONF_DIR}" &&
    \cp "${MODULES_DIR}/configurations/${MODULE}.conf" ${MODULES_CONF_DIR}/ &&
    
    # Activation du module
    mod_enable &&
    echo -e "Installing ${YELLOW}reposerver${RESET} module: [$GREEN OK $RESET]"
    
    # Configuration du module
    mod_configure
}

# Activation de l'agent reposerver
function enableReposerverAgent
{
    cd ${AGENTS_ENABLED_DIR}/ &&
    ln -sfn "../mods-available/agent/reposerver.agent" &&
    echo -e "${YELLOW}reposerver${RESET} agent enabled"
    return 0
}

# Désactivation de l'agent reposerver
function disableReposerverAgent
{
    rm "${AGENTS_ENABLED_DIR}/reposerver.agent" -f &&
    echo -e "${YELLOW}reposerver${RESET} agent disabled"
    return 0
}

# Configuration du module
function mod_configure
{
    # Si il n'y a aucun fichier de configuration pour ce module, on lance l'installation
    if [ ! -f "$MOD_CONF" ];then
        mod_install
    fi

    REGISTER_HOSTNAME=""
    REGISTER_IP=""

    # Configuration du module reposerver.mod (fichier de configuration reposerver.conf)
    REPOSERVER_URL=""
    FAILLEVEL=""
    GET_PROFILE_PKG_CONF_FROM_REPOSERVER=""
    GET_PROFILE_REPOS_FROM_REPOSERVER=""

    # Variables de status
    SEND_GENERAL_STATUS="false"
    SEND_PACKAGES_STATUS="false"
    SEND_FULL_HISTORY="false"
    SEND_FULL_HISTORY_LIMIT=""

    # Défini le status de l'agent linupdate (démarré, arrêté)
    if systemctl is-active --quiet linupdate.service;then
        AGENT_STATUS="running"
    else
        AGENT_STATUS="stopped"
    fi
    # Cependant si le module d'agent reposerver n'est pas activé alors on défini le status de l'agent à 'disabled'
    if [ ! -f "${AGENTS_ENABLED_DIR}/reposerver.agent" ];then
        AGENT_STATUS="disabled"
    fi

    # Récupération des paramètres passés à la fonction
    while [ $# -ge 1 ];do
        case "$1" in
            --help)
                mod_help
                clean_exit
            ;;
            --api-key)
                REPOSERVER_API_KEY="$2"
                shift

                # Check that provided API key name is valid (must start with "ak_")
                if ! echo "$REPOSERVER_API_KEY" | grep -q "^ak_";then
                    ERROR_STATUS=1
                    echo "Invalid API key name, must start with 'ak_'"
                fi
            ;;
            --agent-watch-int)
                WATCH_INTERFACE="$2"
                shift
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^WATCH_INTERFACE" $MOD_CONF;then
                    sed -i "/^\[AGENT\]/a WATCH_INTERFACE=\"$WATCH_INTERFACE\"" $MOD_CONF
                else
                    sed -i "s|WATCH_INTERFACE=.*|WATCH_INTERFACE=\"$WATCH_INTERFACE\"|g" $MOD_CONF
                fi
            ;;
            --agent-watch-enable)
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^WATCH_FOR_REQUEST" $MOD_CONF;then
                    sed -i "/^\[AGENT\]/a WATCH_FOR_REQUEST=\"enabled\"" $MOD_CONF
                else
                    sed -i "s|WATCH_FOR_REQUEST=.*|WATCH_FOR_REQUEST=\"enabled\"|g" $MOD_CONF
                fi
            ;;
            --agent-watch-disable)
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^WATCH_FOR_REQUEST" $MOD_CONF;then
                    sed -i "/^\[AGENT\]/a WATCH_FOR_REQUEST=\"disabled\"" $MOD_CONF
                else
                    sed -i "s|WATCH_FOR_REQUEST=.*|WATCH_FOR_REQUEST=\"disabled\"|g" $MOD_CONF
                fi
            ;;
            --url)
                REPOSERVER_URL="$2"
                shift
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^URL" $MOD_CONF;then
                    sed -i "/^\[REPOSERVER\]/a URL=\"$REPOSERVER_URL\"" $MOD_CONF
                else
                    sed -i "s|URL=.*|URL=\"$REPOSERVER_URL\"|g" $MOD_CONF
                fi
            ;;
            --fail-level)
                FAILLEVEL="$2"
                shift
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^FAILLEVEL" $MOD_CONF;then
                    sed -i "/^\[MODULE\]/a FAILLEVEL=\"$FAILLEVEL\"" $MOD_CONF
                else
                    sed -i "s/FAILLEVEL=.*/FAILLEVEL=\"$FAILLEVEL\"/g" $MOD_CONF
                fi
            ;;
            --allow-conf-update|--get-packages-conf-from-reposerver)
                if [ "$2" == "yes" ];then
                    GET_PROFILE_PKG_CONF_FROM_REPOSERVER="true"
                else
                    GET_PROFILE_PKG_CONF_FROM_REPOSERVER="false"
                fi
                shift

                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^GET_PROFILE_PKG_CONF_FROM_REPOSERVER" $MOD_CONF;then
                    sed -i "/^\[CLIENT\]/a GET_PROFILE_PKG_CONF_FROM_REPOSERVER=\"$GET_PROFILE_PKG_CONF_FROM_REPOSERVER\"" $MOD_CONF
                else
                    sed -i "s/GET_PROFILE_PKG_CONF_FROM_REPOSERVER=.*/GET_PROFILE_PKG_CONF_FROM_REPOSERVER=\"$GET_PROFILE_PKG_CONF_FROM_REPOSERVER\"/g" $MOD_CONF
                fi
            ;;
            --allow-repos-update|--get-repos-from-reposerver)
                if [ "$2" == "yes" ];then
                    GET_PROFILE_REPOS_FROM_REPOSERVER="true"
                else
                    GET_PROFILE_REPOS_FROM_REPOSERVER="false"
                fi
                shift

                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^GET_PROFILE_REPOS_FROM_REPOSERVER" $MOD_CONF;then
                    sed -i "/^\[CLIENT\]/a GET_PROFILE_REPOS_FROM_REPOSERVER=\"$GET_PROFILE_REPOS_FROM_REPOSERVER\"" $MOD_CONF
                else 
                    sed -i "s/GET_PROFILE_REPOS_FROM_REPOSERVER=.*/GET_PROFILE_REPOS_FROM_REPOSERVER=\"$GET_PROFILE_REPOS_FROM_REPOSERVER\"/g" $MOD_CONF
                fi
            ;;
            # Récupération de la configuration complète du serveur Repomanager distant
            --get-server-conf|--server-get-conf)
                getModConf
                getServerConf
                clean_exit
            ;;
            # --get-profile-conf|--profile-get-conf)
            #     getModConf
            #     getProfileConf
            #     clean_exit
            # ;;
            --get-profile-packages-conf)
                getModConf
                getProfilePackagesConf
                clean_exit
            ;;
            --get-profile-repos|--profile-get-repos)
                getModConf
                getProfileRepos
                clean_exit
            ;;
            --register)
                # Si une adresse IP est précisée alors on enregistrera cette adresse IP
                if [ "$2" == "--ip" ] && [ ! -z "$3" ];then
                    REGISTER_IP="$3"
                fi
                register
            ;;
            --unregister)
                unregister
            ;;
            --enable-agent)
                enableReposerverAgent
                clean_exit
            ;;
            --disable-agent)
                disableReposerverAgent
                clean_exit
            ;;
            --send-full-status)
                # Envoi du status complet du serveur
                SEND_GENERAL_STATUS="true"
                SEND_PACKAGES_STATUS="true"
                send_status
            ;;
            --send-general-status)
                # Envoi du status général du serveur (OS, kernel..)
                SEND_GENERAL_STATUS="true"
                send_status
            ;;
            --send-packages-status)
                SEND_PACKAGES_STATUS="true"
                send_status
            ;;
            --send-full-history)
                # Si un chiffre est précisé alors il définira le nombre maximum d'évènements à envoyer
                if [ ! -z "$2" ];then
                    SEND_FULL_HISTORY_LIMIT="$2"
                fi
                SEND_FULL_HISTORY="true"
                send_status
            ;;
            # *)
            #     echo "Paramètre de module inconnu: $1"
            #     clean_exit
            # ;;
        esac
        shift
    done
}

# La fonction mod_load() permet de s'assurer que le module est un minimum configuré avant qu'il soit intégré à l'exécution du programme principal
# Retourner 1 si des éléments sont manquants
# Retourner 0 si tout est OK
function mod_load
{
    # Patch 2.2.12
    if [ -f "$MOD_CONF" ];then
        # Remove REPOSERVER_MANAGE_CLIENT_CONF
        sed -i '/REPOSERVER_MANAGE_CLIENT_CONF/d' "$MOD_CONF"
        # Remove REPOSERVER_MANAGE_CLIENT_REPOS
        sed -i '/REPOSERVER_MANAGE_CLIENT_REPOS/d' "$MOD_CONF"
        # Remove GET_PROFILE_PARAMS_OVERWRITE
        sed -i '/GET_PROFILE_PARAMS_OVERWRITE/d' "$MOD_CONF"
    fi

    echo -e "  - ${YELLOW}reposerver${RESET}"

    # Si le fichier de configuration du module est introuvable alors on ne charge pas le module
    if [ ! -f "$MOD_CONF" ] || [ ! -s "$MOD_CONF" ];then
        echo -e "    [$YELLOW WARNING $RESET] Module config file is missing. Module cannot be loaded."
        return 1
    fi

    # Vérification du contenu du fichier de conf
    # On utilise un fichier temporaire pour vérifier et rajouter les éventuels paramètres manquants
    TMP_MOD_CONF="/tmp/.linupdate_${PROCID}_mod_reposerver_conf.tmp"

    # Section MODULE
    echo -e "[MODULE]" > "$TMP_MOD_CONF"

    # Si le paramètre FAILLEVEL est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^FAILLEVEL=" "$MOD_CONF";then
        echo "FAILLEVEL=\"3\"" >> "$TMP_MOD_CONF"
    else
        grep "^FAILLEVEL=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Section CLIENT
    echo -e "\n[CLIENT]" >> "$TMP_MOD_CONF"
    
    # Si le paramètre ID est manquant alors on l'ajoute avec une valeur par défaut (vide)
    if ! grep -q "^ID=" "$MOD_CONF";then
        echo "ID=\"\"" >> "$TMP_MOD_CONF"
    else
        grep "^ID=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Si le paramètre TOKEN est manquant alors on l'ajoute avec une valeur par défaut (vide)
    if ! grep -q "^TOKEN=" "$MOD_CONF";then
        echo "TOKEN=\"\"" >> "$TMP_MOD_CONF"
    else
        grep "^TOKEN=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Si le paramètre GET_PROFILE_PKG_CONF_FROM_REPOSERVER est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^GET_PROFILE_PKG_CONF_FROM_REPOSERVER=" "$MOD_CONF";then
        echo "GET_PROFILE_PKG_CONF_FROM_REPOSERVER=\"false\"" >> "$TMP_MOD_CONF"
    else
        grep "^GET_PROFILE_PKG_CONF_FROM_REPOSERVER=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Si le paramètre GET_PROFILE_REPOS_FROM_REPOSERVER est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^GET_PROFILE_REPOS_FROM_REPOSERVER=" "$MOD_CONF";then
        echo "GET_PROFILE_REPOS_FROM_REPOSERVER=\"false\"" >> "$TMP_MOD_CONF"
    else
        grep "^GET_PROFILE_REPOS_FROM_REPOSERVER=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Section REPOSERVER
    echo -e "\n[REPOSERVER]" >> "$TMP_MOD_CONF"
    
    # Si le paramètre URL est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^URL=" "$MOD_CONF";then
        echo "URL=\"\"" >> "$TMP_MOD_CONF"
    else
        grep "^URL=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    if grep -q "^IP=" "$MOD_CONF";then
        grep "^IP=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    if grep -q "^PACKAGE_TYPE=" "$MOD_CONF";then
        grep "^PACKAGE_TYPE=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Section [AGENT]
    echo -e "\n[AGENT]" >> "$TMP_MOD_CONF"
    if ! grep -q "^WATCH_FOR_REQUEST=" "$MOD_CONF";then
        echo "WATCH_FOR_REQUEST=\"enabled\"" >> "$TMP_MOD_CONF"
    else
        grep "^WATCH_FOR_REQUEST=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi
    if ! grep -q "^WATCH_INTERFACE=" "$MOD_CONF";then
        echo "WATCH_INTERFACE=\"auto\"" >> "$TMP_MOD_CONF"
    else
        grep "^WATCH_INTERFACE=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Remplacement du fichier de conf par le fichier précédemment construit
    cat "$TMP_MOD_CONF" > "$MOD_CONF"
    rm -f "$TMP_MOD_CONF"

    # Si l'URL du serveur de repo n'est pas renseignée alors on ne charge pas le module
    if [ -z $(grep "^URL=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g') ];then
        echo -e "     [$YELLOW WARNING $RESET] ${YELLOW}reposerver${RESET} URL is not defined. Module cannot be loaded."
        return 1
    fi

    LOADED_MODULES+=("reposerver")
    echo -e "  - reposerver module: ${YELLOW}Enabled${RESET}"

    return 0
}

# Récupération de la configuration complète du module, dans son fichier de conf
function getModConf
{
    # Configuration client (section [CLIENT])
    HOST_ID="$(grep "^ID=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    TOKEN="$(grep "^TOKEN=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    GET_PROFILE_PKG_CONF_FROM_REPOSERVER="$(grep "^GET_PROFILE_PKG_CONF_FROM_REPOSERVER=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    GET_PROFILE_REPOS_FROM_REPOSERVER="$(grep "^GET_PROFILE_REPOS_FROM_REPOSERVER=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"

    # Configuration serveur (section [REPOSERVER])
    REPOSERVER_URL="$(grep "^URL=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"

    # Récupération du FAILLEVEL pour ce module
    FAILLEVEL=$(grep "^FAILLEVEL=" "$MOD_CONF" | cut -d'=' -f2 | sed 's/"//g')

    # Si on n'a pas pu récupérer le FAILLEVEL dans le fichier de conf alors on le set à 1 par défaut
    # De même si le FAILLEVEL récupéré n'est pas un chiffre alors on le set à 1
    if [ -z "$FAILLEVEL" ];then
        echo -e "    [$YELLOW WARNING $RESET] FAILLEVEL parameter is not defined for this module → default to 1 (stops on critical or minor error)"
        FAILLEVEL="1"
    fi
    if ! [[ "$FAILLEVEL" =~ ^[1-3]+$ ]];then
        echo -e "    [$YELLOW WARNING $RESET] FAILLEVEL parameter is not properly defined for this module (must be a numeric value) → default to 1 (stops on critical or minor error)"
        FAILLEVEL="1"
    fi

    if [ -z "$REPOSERVER_URL" ] || [ "$REPOSERVER_URL" == "null" ];then
        echo -e "    [$YELLOW ERROR $RESET] reposerver URL is not defined"
        return 2
    fi

    return 0
}

# Récupération de la configuration générale du serveur de repos
function getServerConf
{
    TMP_FILE_MODULE="/tmp/.linupdate_${PROCID}_mod_reposerver_section_module.tmp"
    TMP_FILE_CLIENT="/tmp/.linupdate_${PROCID}_mod_reposerver_section_client.tmp"
    TMP_FILE_AGENT="/tmp/.linupdate_${PROCID}_mod_reposerver_section_agent.tmp"
    TMP_FILE_REPOSERVER="/tmp/.linupdate_${PROCID}_mod_reposerver_section_reposerver.tmp"

    # On charge les paramètres du module
    getModConf

    # Demande de la configuration auprès du serveur de repos
    # Ce dernier renverra la configuration au format JSON
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -X GET "${REPOSERVER_URL}/api/v2/profile/server-settings" 2> /dev/null)
    curl_result_parse

    # Si il y a eu une erreur lors de la requête on quitte la fonction
    if [ "$CURL_ERROR" != "0" ];then
        return 2
    fi

    # Puis on récupère la configuration transmise par le serveur au format JSON
    # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
    # On remplace à la volée l'environnement dans le contenu récupéré
    for ROW in $(echo "${CURL}" | jq -r '.results[] | @base64'); do
        _jq() {
            echo ${ROW} | base64 --decode | jq -r ${1}
        }

        REPOSERVER_IP=$(_jq '.Ip')
        REPOSERVER_URL=$(_jq '.Url')
    done

    # Retrieve the server IP address from the server URL
    i="1"
    REPOSERVER_IP=$(echo "$REPOSERVER_URL" | sed 's/https\?:\/\///g' | cut -d'/' -f1)

    # Some DNS servers return multiple IP addresses for a single domain name or a CNAME value
    # Loop until we get a real single IP address
    while [[ ! "$REPOSERVER_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]];do
        REPOSERVER_IP=$(dig +short "$REPOSERVER_IP" | head -n${i} | tail -n1)
        (( i++ ))

        # If we can't retrieve the IP address after 10 tries, stop the loop
        if [ "$i" -gt 10 ];then
            echo -e "  [$YELLOW ERROR $RESET] Unable to retrieve the IP address of the reposerver"
        fi
    done

    # Sauvegarde de la partie [MODULE]
    sed -n -e '/\[MODULE\]/,/^$/p' "$MOD_CONF" > "$TMP_FILE_MODULE"
    # Ajout d'un saut de ligne car chaque section doit être correctement séparée
    echo "" >> "$TMP_FILE_MODULE"
    
    # Sauvegarde de la partie [CLIENT]
    sed -n -e '/\[CLIENT\]/,/^$/p' "$MOD_CONF" > "$TMP_FILE_CLIENT"
    # Ajout d'un saut de ligne car chaque section doit être correctement séparée
    echo "" >> "$TMP_FILE_CLIENT"

    # Sauvegarde de la partie [AGENT] si existe
    sed -n -e '/\[AGENT\]/,/^$/p' "$MOD_CONF" > "$TMP_FILE_AGENT"
    # Ajout d'un saut de ligne car chaque section doit être correctement séparée
    echo "" >> "$TMP_FILE_AGENT"

    # Nouvelle conf [REPOSERVER]
    echo "[REPOSERVER]" >> "$TMP_FILE_REPOSERVER"
    echo "URL=\"$REPOSERVER_URL\"" >> "$TMP_FILE_REPOSERVER"
    echo "IP=\"$REPOSERVER_IP\"" >> "$TMP_FILE_REPOSERVER"
    echo "PACKAGE_TYPE=\"\"" >> "$TMP_FILE_REPOSERVER"
    echo "" >> "$TMP_FILE_REPOSERVER"

    # On reconstruit le fichier de configuration
    cat "$TMP_FILE_MODULE" > "$MOD_CONF"
    cat "$TMP_FILE_CLIENT" >> "$MOD_CONF"
    cat "$TMP_FILE_REPOSERVER" >> "$MOD_CONF"
    cat "$TMP_FILE_AGENT" >> "$MOD_CONF"

    # Suppression des doubles saut de ligne si il y en a
    sed -i '/^$/N;/^\n$/D' "$MOD_CONF"

    # Suppression des fichiers temporaires
    rm "$TMP_FILE_MODULE" -f
    rm "$TMP_FILE_CLIENT" -f
    rm "$TMP_FILE_AGENT" -f
    rm "$TMP_FILE_REPOSERVER" -f

    # Puis on recharge à nouveau les paramètres
    getModConf
}

# Fonction exécutée pre-mise à jour
function preCheck
{
    return
}

# Get profile general configuration from reposerver
# function getProfileConf
# {
#     # Si le serveur reposerver ne gère pas les profils ou que le client refuse d'être mis à jour par son serveur de repo, on quitte la fonction
#     echo -ne "  → Getting ${YELLOW}${PROFILE}${RESET} profile configuration: "

#     # Demande de la configuration des repos auprès du serveur de repos
#     # Ce dernier renverra la configuration au format JSON
#     CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -X GET "${REPOSERVER_URL}/api/v2/profile/${PROFILE}" 2> /dev/null)
#     curl_result_parse

#     # Si il y a eu une erreur lors de la requête on quitte la fonction
#     if [ "$CURL_ERROR" != "0" ];then
#         return 2
#     fi

#     # Puis on récupère la configuration transmise par le serveur au format JSON
#     # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
#     # On remplace à la volée l'environnement dans le contenu récupéré
#     for ROW in $(echo "${CURL}" | jq -r '.results[] | @base64'); do
#         _jq() {
#             echo ${ROW} | base64 --decode | jq -r ${1}
#         }

#         GET_PROFILE_PKG_CONF_FROM_REPOSERVER=$(_jq '.Linupdate_get_pkg_conf')
#         GET_PROFILE_REPOS_FROM_REPOSERVER=$(_jq '.Linupdate_get_repos_conf')
#     done

#     if [ "$GET_PROFILE_PKG_CONF_FROM_REPOSERVER" == "null" ];then
#         echo -e "[$YELLOW ERROR $RESET] Server sent ${YELLOW}null${RESET} data"
#         return 2
#     fi

#     if [ "$GET_PROFILE_REPOS_FROM_REPOSERVER" == "null" ];then
#         echo -e "[$YELLOW ERROR $RESET] Server sent ${YELLOW}null${RESET} data"
#         return 2
#     fi

#     # converting to boolean
#     if [ "$GET_PROFILE_PKG_CONF_FROM_REPOSERVER" == "no" ];then
#         GET_PROFILE_PKG_CONF_FROM_REPOSERVER="false"
#     fi
#     if [ "$GET_PROFILE_PKG_CONF_FROM_REPOSERVER" == "yes" ];then
#         GET_PROFILE_PKG_CONF_FROM_REPOSERVER="true"
#     fi
#     if [ "$GET_PROFILE_REPOS_FROM_REPOSERVER" == "no" ];then
#         GET_PROFILE_REPOS_FROM_REPOSERVER="false"
#     fi
#     if [ "$GET_PROFILE_REPOS_FROM_REPOSERVER" == "yes" ];then
#         GET_PROFILE_REPOS_FROM_REPOSERVER="true"
#     fi

#     # On applique la nouvelle configuration récupérée
#     sed -i "s/GET_PROFILE_PKG_CONF_FROM_REPOSERVER.*/GET_PROFILE_PKG_CONF_FROM_REPOSERVER=\"$GET_PROFILE_PKG_CONF_FROM_REPOSERVER\"/g" "$MOD_CONF"
#     sed -i "s/GET_PROFILE_REPOS_FROM_REPOSERVER.*/GET_PROFILE_REPOS_FROM_REPOSERVER=\"$GET_PROFILE_REPOS_FROM_REPOSERVER\"/g" "$MOD_CONF"

#     echo -e "[${GREEN} OK ${RESET}]"

#     # Enfin on applique la nouvelle conf en récupérant de nouveau les paramètres du fichier de conf :
#     getConf
# }

# Get profile packages configuratin (packages excludes)
function getProfilePackagesConf
{
    echo -ne "  → Getting ${YELLOW}${PROFILE}${RESET} profile packages configuration: "

    # Demande de la configuration des paquets auprès du serveur de repos
    # Ce dernier renverra la configuration au format JSON
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -X GET "${REPOSERVER_URL}/api/v2/profile/${PROFILE}/excludes" 2> /dev/null)
    curl_result_parse

    # Si il y a eu une erreur lors de la requête on quitte la fonction
    if [ "$CURL_ERROR" != "0" ];then
        return 2
    fi

    if [ "$GET_PROFILE_PKG_CONF_FROM_REPOSERVER" == "false" ];then
        echo -e "${YELLOW}Disabled${RESET}"
        return 1
    fi

    # Puis on récupère la configuration transmise par le serveur au format JSON
    # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
    # On remplace à la volée l'environnement dans le contenu récupéré
    for ROW in $(echo "${CURL}" | jq -r '.results[] | @base64'); do
        _jq() {
            echo ${ROW} | base64 --decode | jq -r ${1}
        }

        EXCLUDE_MAJOR=$(_jq '.Package_exclude_major')
        EXCLUDE=$(_jq '.Package_exclude')
        SERVICE_RESTART=$(_jq '.Service_restart')
    done

    # Si la valeur des paramètres == null alors cela signifie qu'il n'y a aucune exclusion de paquet
    if [ "$EXCLUDE_MAJOR" == "null" ];then
        EXCLUDE_MAJOR=""
    fi
    if [ "$EXCLUDE" == "null" ];then
        EXCLUDE=""
    fi
    if [ "$SERVICE_RESTART" == "null" ];then
        SERVICE_RESTART=""
    fi

    # On applique la nouvelle configuration récupérée
    # D'abord on nettoie la partie [SOFT] du fichier de conf car c'est cette partie qui va être remplacée par la nouvelle conf : 
    sed -i '/^\[SOFTWARE CONFIGURATION\]/,$d' "$CONF" &&

    # Puis on injecte la nouvelle conf récupérée
    echo -e "[SOFTWARE CONFIGURATION]\nEXCLUDE_MAJOR=\"${EXCLUDE_MAJOR}\"\nEXCLUDE=\"${EXCLUDE}\"\nSERVICE_RESTART=\"${SERVICE_RESTART}\"" >> "$CONF"

    echo -e "[${GREEN} OK ${RESET}]"

    # Enfin on applique la nouvelle conf en récupérant de nouveau les paramètres du fichier de conf :
    getConf
}


# Récupération de la configuration des repos du profil de l'hôte, auprès du serveur de repos
function getProfileRepos
{
    # Si on est autorisé à mettre à jour les fichiers de conf de repos et si le serveur de repos le gère
    echo -ne "  → Getting ${YELLOW}${PROFILE}${RESET} profile repositories: "

    # Demande de la configuration des repos auprès du serveur de repos
    # Ce dernier renverra la configuration au format JSON
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -X GET "${REPOSERVER_URL}/api/v2/profile/${PROFILE}/repos" 2> /dev/null)
    curl_result_parse

    # Si il y a eu une erreur lors de la requête on quitte la fonction
    if [ "$CURL_ERROR" != "0" ];then
        return 2
    fi

    # Sinon on récupère les configurations de repos que la requête a renvoyé
    # On s'assure que le paramètre 'configuraiton' fait bien partie de la réponse JSON renvoyée par le serveur
    # Ce paramètre peut être vide toutefois si la configuration du profil côté serveur n'a aucun repo de configuré
    if ! echo "$CURL" | grep -q "results";then
        echo -e "[$YELLOW ERROR $RESET] $PROFILE profile repos sources configuration have not been sent by reposerver."
        return 2
    fi

    if [ "$GET_PROFILE_REPOS_FROM_REPOSERVER" == "false" ];then
        echo -e "${YELLOW}Disabled${RESET}"
        return 1
    fi

    # Si le paramètre existe alors on peut continuer le traitement
    # D'abord on vide les fichiers .repo ou .list présents sur l'hôte car ils seront remplacés par la configuration transférée par le serveur.
    if [ "$OS_FAMILY" == "Redhat" ];then
        rm /etc/yum.repos.d/*.repo -f
    fi
    if [ "$OS_FAMILY" == "Debian" ];then
        echo -n> /etc/apt/sources.list
        rm /etc/apt/sources.list.d/*.list -f
    fi

    # Puis on récupère la configuration des nouveaux fichiers .repo ou .list transmis par le serveur au format JSON
    # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
    # On remplace à la volée l'environnement dans le contenu récupéré
    IFS=$'\n'
    for ROW in $(echo "${CURL}" | jq -r '.results[] | @base64'); do
        _jq() {
            echo ${ROW} | base64 --decode | jq -r ${1}
        }

        FILENAME=$(_jq '.filename')
        DESCRIPTION=$(_jq '.description')
        CONTENT=$(_jq '.content' | sed "s/__ENV__/${ENV}/g")

        if [ "$OS_FAMILY" == "Redhat" ];then
            FILENAME_PATH="/etc/yum.repos.d/$FILENAME"
        fi

        if [ "$OS_FAMILY" == "Debian" ];then
            FILENAME_PATH="/etc/apt/sources.list.d/$FILENAME"
        fi

        # Si le fichier n'existe pas déjà on insert la description en début de fichier
        if [ ! -f "$FILENAME_PATH" ];then
            echo "# $DESCRIPTION" > "$FILENAME_PATH"
        fi

        # Puis on insert le contenu
        echo -e "${CONTENT}\n" >> "$FILENAME_PATH"
    done

    # Set permissions and reload cache
    if [ "$OS_FAMILY" == "Redhat" ];then
        if ls -A /etc/yum.repos.d/ | grep -q "\.repo";then
            chown root:root /etc/yum.repos.d/*.repo
            chmod 660 /etc/yum.repos.d/*.repo
        fi

        checkYumLock
        yum clean all -q
    fi
    if [ "$OS_FAMILY" == "Debian" ];then
        if ls -A /etc/apt/sources.list.d/ | grep -q "\.list";then
            chown root:root /etc/apt/sources.list.d/*.list
            chmod 660 /etc/apt/sources.list.d/*.list
        fi

        apt-get clean
    fi

    echo -e "[$GREEN OK $RESET]"
}

# Exécution pre-mise à jour des paquets
function pre
{
    # Fail-level :
    # 1 = quitte à la moindre erreur (module désactivé, le serveur ne gère pas le même OS, erreur mineure, critique)
    # 2 = quitte seulement en cas d'erreur critique
    # 3 = continue même en cas d'erreur critique (ex : impossible de récupérer la conf du serveur de repo), la machine se mettra à jour selon la conf actuellement en place dans son fichier de conf

    # Codes de retour :
    # Aucune erreur :   return 0
    # Erreur mineure :  return 1
    # Erreur critique : return 2

    echo -e "  → Executing ${YELLOW}reposerver${RESET} module"

    # On récupère la configuration du module, en l'occurence la configuration du serveur de repo
    getModConf
    RESULT="$?"
    if [ "$FAILLEVEL" -le "2" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi     # Si FAILLEVEL = 1 ou 2
    if [ "$FAILLEVEL" -eq "3" ] && [ "$RESULT" -gt "0" ];then return 1;fi                          # Si FAILLEVEL = 3 et qu'il y a une erreur au chargement de la conf du module alors on quitte le module sans pour autant quitter repomanager (clean_exit)

    # On met à jour la configuration du serveur de repo distant en lui demandant de renvoyer sa conf
    getServerConf
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "3" ] && [ "$RESULT" -gt "0" ];then return 1;fi                          # Si FAILLEVEL = 3 et qu'il y a une erreur au chargement de la conf du module alors on quitte le module sans pour autant quitter repomanager (clean_exit)

    # On vérifie que la configuration du serveur de repo est compatible avec notre OS
    preCheck
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    # On met à jour notre configuration à partir du serveur de repo (profils), si cela est autorisé des deux côtés
    # getProfileConf
    # RESULT="$?"
    # if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    # if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    getProfilePackagesConf
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    # On met à jour notre configuration des repos à partir du serveurs de repo (profils), si cela est autorisé des deux côtés
    getProfileRepos
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    return 0
}

# Exécution post-mise à jour des paquets
function post
{
    # Si il y a eu des paquets à mettre à jour lors de cette exécution alors on exécute les actions suivantes
    if [ "$SOMETHING_TO_UPDATE" == "true" ];then
        # Généralement les paquets "*-release" sur Redhat/CentOS remettent en place des fichiers .repo. Du coup on remet à jour la configuration des repos à partir du serveurs de repo (profils), si cela est autorisé des deux côtés
        getProfileRepos

        # On renvoie les 4 derniers historique d'évènements au serveur reposerver
        /opt/linupdate/linupdate --mod-configure reposerver --from-agent --send-full-history 4
    fi

    return 0
}

## Envoi de status (API) ##

# Envoi au serveur Repomanager l'état actuel de l'hôte
# Fonction principale
function send_status
{
    # Au préalable, récupération des informations concernant le serveur repomanager
    # Si la configuration est incomplète alors on quitte
    getModConf

    OLD_IFS=$IFS
    IFS=$'\n'

    # On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
    testConnection

    # Envoi du récapitulatif de toutes les mises à jour effectuées à partir du fichier historique

    # Si on n'a pas d'ID ou de token alors on ne peut pas effectuer cette opération
    if [ -z "$HOST_ID" ];then
        echo -e "[$YELLOW ERROR $RESET] Host Id not defined"
        ERROR_STATUS=1
        clean_exit
    fi
    if [ -z "$TOKEN" ];then
        echo -e "[$YELLOW ERROR $RESET] Host token not defined"
        ERROR_STATUS=1
        clean_exit
    fi

    # Exécution des sous-fonctions

    # Général
    if [ "$SEND_GENERAL_STATUS" == "true" ];then
        send_general_status
    fi

    # Paquets
    if [ "$SEND_PACKAGES_STATUS" == "true" ];then
        send_packages_status
    fi

    # Historique des évènements apt ou yum
    if [ "$SEND_FULL_HISTORY" == "true" ];then  
        genFullHistory
    fi

    IFS="$OLD_IFS"

    clean_exit
}

# Envoi au serveur Repomanager l'état général de l'hôte (son os, version, profil, env)
function send_general_status
{
    UPDATE_MESSAGE_SUCCESS=""
    UPDATE_MESSAGE_ERROR=""
    FQDN=$(hostname -f)

    # Check if reboot is needed
    checkRebootNeeded

    CURL_PARAMS=""

    # Paramètres généraux (os, version, profil...)
    if [ ! -z "$FQDN" ];then
        CURL_PARAMS+="\"hostname\":\"$FQDN\","
    fi
    if [ ! -z "$OS_NAME" ];then
        CURL_PARAMS+="\"os\":\"$OS_NAME\","
    fi
    if [ ! -z "$OS_VERSION" ];then
        CURL_PARAMS+="\"os_version\":\"$OS_VERSION\","
    fi
    if [ ! -z "$OS_FAMILY" ];then
        CURL_PARAMS+="\"os_family\":\"$OS_FAMILY\","
    fi
    if [ ! -z "$VIRT_TYPE" ];then
        CURL_PARAMS+="\"type\":\"$VIRT_TYPE\","
    fi
    if [ ! -z "$KERNEL" ];then
        CURL_PARAMS+="\"kernel\":\"$KERNEL\","
    fi
    if [ ! -z "$ARCH" ];then
        CURL_PARAMS+="\"arch\":\"$ARCH\","
    fi
    if [ ! -z "$PROFILE" ];then
        CURL_PARAMS+="\"profile\":\"$PROFILE\","
    fi
    if [ ! -z "$ENV" ];then
        CURL_PARAMS+="\"env\":\"$ENV\","
    fi
    if [ ! -z "$AGENT_STATUS" ];then
        CURL_PARAMS+="\"agent_status\":\"$AGENT_STATUS\","
    fi
    if [ ! -z "$VERSION" ];then
        CURL_PARAMS+="\"linupdate_version\":\"$VERSION\","
    fi
    if [ ! -z "$REBOOT_REQUIRED" ];then
        CURL_PARAMS+="\"reboot_required\":\"$REBOOT_REQUIRED\","
    fi

    # Delete the last comma
    CURL_PARAMS=$(echo "${CURL_PARAMS::-1}")

    # Fin de construction des paramètres curl puis envoi.

    # Envoi des données :
    echo -e "→ Sending status to ${YELLOW}${REPOSERVER_URL}${RESET}: "
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/v2/host/status" 2> /dev/null)

    # Récupération et affichage des messages
    curl_result_parse
}

# Envoi du status des paquets (installés, disponibles)
function send_packages_status
{
    INSTALLED_PACKAGES=""
    UPDATE_MESSAGE_SUCCESS=""
    UPDATE_MESSAGE_ERROR=""

    # Exécution des différentes fonctions
    genFullHistory
    send_available_packages_status
    send_installed_packages_status
}

# Envoi au serveur Repomanager de la liste des paquets installés sur l'hôte
function send_installed_packages_status
{
    INSTALLED_PACKAGES=""
    UPDATE_MESSAGE_SUCCESS=""
    UPDATE_MESSAGE_ERROR=""

    # Paramètres concernant les paquets installés sur le système (tous les paquets)
    echo "Building installed packages list..."

    INSTALLED_PACKAGES_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_installed_pkgs.tmp"

    # Construction de la liste des paquets
    # Cas Redhat
    if [ "$OS_FAMILY" == "Redhat" ];then
        if [ -f "/usr/bin/dnf" ];then
            dnf repoquery -q -a --installed --qf="%{name} %{epoch}:%{version}-%{release}.%{arch}" > "$INSTALLED_PACKAGES_TMP"
        else
            repoquery -a --installed --qf="%{name} %{epoch}:%{version}-%{release}.%{arch}" > "$INSTALLED_PACKAGES_TMP"
        fi
    fi
    # Cas Debian
    if [ "$OS_FAMILY" == "Debian" ];then
        dpkg-query -W -f='${Status}\t${package}\t${version}\t\n' | grep "^install ok installed" | awk '{print $4, $5}' > "$INSTALLED_PACKAGES_TMP"
    fi

    # Parsage des lignes des fichiers splités
    for LINE in $(cat "$INSTALLED_PACKAGES_TMP");do

        if [ "$OS_FAMILY" == "Redhat" ];then
            PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}')
            PACKAGE_ACT_VERSION=$(echo "$LINE" | awk '{print $2}')
            # On retire l'epoch si celui-ci vaut 0: (epoch : https://docs.fedoraproject.org/en-US/Fedora_Draft_Documentation/0.1/html/RPM_Guide/ch09s03.html)
            PACKAGE_ACT_VERSION=$(echo "$PACKAGE_ACT_VERSION" | sed 's/^0://g')
        fi
        if [ "$OS_FAMILY" == "Debian" ];then
            PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
            PACKAGE_ACT_VERSION=$(echo "$LINE" | awk '{print $2}' | sed 's/"//g' | sed "s/'//g")
        fi

        # Si le nom du paquet est vide, on passe au suivant
        if [ -z "$PACKAGE_NAME" ];then
            continue
        fi
                
        # Ajout du nom du paquet, sa version actuelle et sa version disponible à l'array $INSTALLED_PACKAGES
        INSTALLED_PACKAGES+="${PACKAGE_NAME}|${PACKAGE_ACT_VERSION},"
    done

    rm "$INSTALLED_PACKAGES_TMP" -f

    # Suppression de la dernière virgule :
    INSTALLED_PACKAGES=$(echo "${INSTALLED_PACKAGES::-1}")
    
    # Construction des paramètres curl à envoyer
    CURL_PARAMS="\"installed_packages\":\"$INSTALLED_PACKAGES\""

    # Envoi des données :
    echo -ne "→ Sending data to ${YELLOW}${REPOSERVER_URL}${RESET}: "
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/v2/host/packages/installed" 2> /dev/null)
    
    # Récupération et affichage des messages
    curl_result_parse

    if [ "$CURL_ERROR" -eq "0" ];then
        return 0

    else 
        return 1
    fi
}

# Envoi au serveur Repomanager de la liste des paquets disponibles pour mettre à jour
function send_available_packages_status
{
    AVAILABLE_PACKAGES=""

    # Paramètres concernant les paquets (paquets disponibles...)

    echo "Building available packages list..."

    # Récupération des paquets disponibles
    AVAILABLE_PACKAGES_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_available_pkgs.tmp"

    # Cas Redhat
    if [ "$OS_FAMILY" == "Redhat" ];then
        # Récupération des paquets disponibles pour mise à jour
        if [ -f "/usr/bin/dnf" ];then
            dnf repoquery -q --upgrades --latest-limit 1 -a --qf="%{name} %{epoch}:%{version}-%{release}.%{arch}" --upgrades > "$AVAILABLE_PACKAGES_TMP"
        else
            repoquery -a --qf="%{name} %{epoch}:%{version}-%{release}.%{arch}" --pkgnarrow=updates > "$AVAILABLE_PACKAGES_TMP"
        fi
    fi
    # Cas Debian
    if [ "$OS_FAMILY" == "Debian" ];then
        # Récupération des paquets disponibles pour mise à jour
        aptitude -F"%p %v %V" --disable-columns search ~U > "$AVAILABLE_PACKAGES_TMP"
    fi
    
    # Si le fichier généré est vide, alors il n'y a aucun paquet à mettre à jour, on n'envoit rien à Repomanager
    if [ ! -s "$AVAILABLE_PACKAGES_TMP" ];then
        AVAILABLE_PACKAGES="none"

    else
        # Sinon on parcourt toutes les lignes du fichiers pour lister les paquets disponibles
        for LINE in $(cat "$AVAILABLE_PACKAGES_TMP");do
            if [ "$OS_FAMILY" == "Redhat" ];then
                PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}')
                PACKAGE_AVL_VERSION=$(echo "$LINE" | awk '{print $2}')
                # On retire l'epoch si celui-ci vaut 0:
                PACKAGE_AVL_VERSION=$(echo "$PACKAGE_AVL_VERSION" | sed 's/^0://g')
            fi
            if [ "$OS_FAMILY" == "Debian" ];then
                PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}')
                PACKAGE_AVL_VERSION=$(echo "$LINE" | awk '{print $3}')
            fi

            # Si le nom du paquet est vide alors on passe au suivant
            if [ -z "$PACKAGE_NAME" ];then
                continue
            fi

            # Ajout du nom du paquet, sa version actuelle et sa version disponible à l'array $AVAILABLE_PACKAGES
            AVAILABLE_PACKAGES+="${PACKAGE_NAME}|${PACKAGE_AVL_VERSION},"
        done

        # Suppression de la dernière virgule :
        AVAILABLE_PACKAGES=$(echo "${AVAILABLE_PACKAGES::-1}")
    fi

    rm "$AVAILABLE_PACKAGES_TMP" -f

    # Construction des paramètres curl à envoyer
    CURL_PARAMS="\"available_packages\":\"$AVAILABLE_PACKAGES\""

    # Envoi des données :
    echo -ne "→ Sending data to ${YELLOW}${REPOSERVER_URL}${RESET}: "
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/v2/host/packages/available" 2> /dev/null)
    
    # Récupération et affichage des messages
    curl_result_parse

    if [ "$CURL_ERROR" -eq "0" ];then
        return 0

    else 
        return 1
    fi
}

# Envoi au serveur repomanager l'historique des opérations effectuées sur les paquets (installation, mises à jour, suppression...)
# Se base sur les historiques de yum et d'apt
function genFullHistory
{
    # Contiendra la liste de tous les évènements
    EVENTS_JSON=""
    IGNORE_EVENT=""

    # Le paramètre SEND_FULL_HISTORY_LIMIT défini le nb maximum d'évènements à envoyer, cela permet 
    # d'éviter d'envoyer inutilement l'historique complet du serveur dans certains cas.
    # Si ce paramètre est laissé vide alors il n'y a aucune limite, on le set par défaut à 99999999.
    if [ -z "$SEND_FULL_HISTORY_LIMIT" ];then
        SEND_FULL_HISTORY_LIMIT="99999999"
        # Dans le cas où on n'a pas précisé de limite alors il faudra traiter les évènements à partir du plus ancien au plus récent
        HISTORY_START="oldest"
    else
        # Dans le cas où on a précisé une limite alors il faudra traiter les évènements à partir du plus récent au plus ancien
        HISTORY_START="newest"
    fi
    # On initialise une variable à 0 qui sera incrémentée jusqu'à atteindre la limite SEND_FULL_HISTORY_LIMIT.
    HISTORY_LIMIT_COUNTER="0"

    # Fichier JSON final qui sera envoyé au serveur Repomanager
    JSON_FILE="/tmp/.linupdate_${PROCID}_mod_reposerver_events_history.json"

    OLD_IFS=$IFS

    if [ "$OS_FAMILY" == "Redhat" ];then
        echo "Building yum events history..."

        checkYumLock

        # Récupération de tous les ID d'évènements dans la base de données de yum
        if [ "$HISTORY_START" == "newest" ];then
            if [ -f "/usr/bin/dnf" ];then
                YUM_HISTORY_IDS=$(dnf history list | tail -n +3 | awk '{print $1}' | grep -v "history")
            else
                YUM_HISTORY_IDS=$(yum history list all | tail -n +4 | awk '{print $1}' | grep -v "history")
            fi
        fi
        if [ "$HISTORY_START" == "oldest" ];then
            if [ -f "/usr/bin/dnf" ];then
                YUM_HISTORY_IDS=$(dnf history list | tail -n +3 | awk '{print $1}' | grep -v "history" | tac)
            else
                YUM_HISTORY_IDS=$(yum history list all | tail -n +4 | awk '{print $1}' | grep -v "history" | tac)
            fi
        fi

        # Pour chaque évènement on peut récupérer la date et l'heure de début et la date et l'heure de fin
        for YUM_HISTORY_ID in $(echo "$YUM_HISTORY_IDS");do
            # On sort de la boucle si on a atteint la limite d'évènement à envoyer fixée par l'utilisateur
            if [ "$HISTORY_LIMIT_COUNTER" == "$SEND_FULL_HISTORY_LIMIT" ];then
                break
            fi

            # Parsage de l'évènement
            yumHistoryParser

            if [ ! -z "$YUM_HISTORY_PARSER_RETURN" ];then
                # Récupération du retour de la fonction yumHistoryParser
                EVENTS_JSON+="$YUM_HISTORY_PARSER_RETURN"

                # Ajout d'une virgule pour séparer chaque évènement
                EVENTS_JSON+=","
            fi    

            (( HISTORY_LIMIT_COUNTER++ ))
        done
    fi

    # Cas Debian
    if [ "$OS_FAMILY" == "Debian" ];then
        echo "Building apt events history..."

        if [ "$HISTORY_START" == "newest" ];then
            APT_HISTORY_FILES=$(ls -t1 /var/log/apt/history.log*)
        fi
        if [ "$HISTORY_START" == "oldest" ];then
            APT_HISTORY_FILES=$(ls -t1 /var/log/apt/history.log* | tac)
        fi

        # On va traiter tous les fichiers d'historique d'apt, même ceux compréssés
        for APT_LOG_FILE in $APT_HISTORY_FILES;do
            IFS=$'\n'

            # On traite chaque évènement trouvé dans le fichier de log
            for START_DATE in $(zgrep "^Start-Date:*" "$APT_LOG_FILE");do
                # On sort de la boucle si on a atteint la limite d'évènement à envoyer fixée par l'utilisateur
                if [ "$HISTORY_LIMIT_COUNTER" == "$SEND_FULL_HISTORY_LIMIT" ];then
                    break
                fi

                # Parsage de l'évènement
                aptHistoryParser

                if [ ! -z "$APT_HISTORY_PARSER_RETURN" ];then
                    # Récupération du retour de la fonction yumHistoryParser
                    EVENTS_JSON+="$APT_HISTORY_PARSER_RETURN"

                    # Ajout d'une virgule pour séparer chaque évènement
                    EVENTS_JSON+=","
                fi    

                (( HISTORY_LIMIT_COUNTER++ ))
            done
        done
    fi

    # Suppression de la dernière virgule après le dernier array de date ajouté (},<= ici)
    EVENTS_JSON=$(echo "${EVENTS_JSON::-1}")

    # Construction du JSON final
    echo "{\"events\" : [$EVENTS_JSON]}" | jq . > "$JSON_FILE"

    IFS=$OLD_IFS

    # Envoi des données :
    echo -ne "→ Sending history to ${YELLOW}${REPOSERVER_URL}${RESET}: "
    CURL=$(curl -L --post301 -s -q -H "Authorization: Host $HOST_ID:$TOKEN" -H "Content-Type: application/json" -X PUT -d @${JSON_FILE} "${REPOSERVER_URL}/api/v2/host/packages/event" 2> /dev/null)

    # Récupération et affichage des messages
    curl_result_parse

    rm "$JSON_FILE" -f

    if [ "$CURL_ERROR" -eq "0" ];then
        return 0
    else 
        return 1
    fi
}