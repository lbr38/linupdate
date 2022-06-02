#!/bin/bash
# Module reposerver
# Module permettant de se ratacher à un serveur de repo exécutant repomanager 

# Fichier de configuration du module
MOD_CONF="${MODULES_CONF_DIR}/reposerver.conf"

#### FONCTIONS ####

# Enregistrement auprès d'un serveur Repomanager
function register
{
    # Au préalable, récupération des informations concernant le serveur repomanager
    # Si la configuration est incomplète alors on quitte
    getModConf
    if [ -z "$REPOSERVER_URL" ];then
        echo -e " [$YELLOW ERREUR $RESET] Impossible de s'enregistrer auprès du serveur Repomanager. Vous devez configurer l'url du serveur."
        ERROR_STATUS=1
        clean_exit
    fi

    # On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
    testConnection

    # Tentative d'enregistrement
    # Si l'enregistrement fonctionne, on récupère un id et un token
    echo -ne " Enregistrement auprès de ${YELLOW}${REPOSERVER_URL}${RESET} : "
    REGISTER_HOSTNAME=$(hostname -f)
    if [ -z "$REGISTER_HOSTNAME" ];then
        echo -e "[$YELLOW ERREUR $RESET] Impossible de déterminer le nom d'hôte de cette machine"
        ERROR_STATUS=1
        clean_exit
    fi
    # Si on n'a pas précisé d'adresse IP à enregistrer alors on tente de récupérer l'adresse IP publique de cette machine
    if [ -z "$REGISTER_IP" ];then
        REGISTER_IP=$(curl -s -4 ifconfig.co)
        if [ -z "$REGISTER_IP" ];then
            echo -e "[$YELLOW ERREUR $RESET] Impossible de déterminer l'adresse IP de cette machine"
            ERROR_STATUS=1
            clean_exit
        fi
    fi

    CURL=$(curl -s -q -H "Content-Type: application/json" -X POST -d "{\"ip\":\"$REGISTER_IP\",\"hostname\":\"$REGISTER_HOSTNAME\"}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
   
    # Parsage de la réponse et affichage des messages si il y en a
    curl_result_parse

    # Si il y a eu des erreurs suite à la requete alors on quitte
    if [ "$CURL_ERROR" -gt "0" ];then
        clean_exit
    fi

    # Le serveur a dû renvoyer un id et token d'identification qu'on récupère
    REGISTER_ID=$(jq -r '.id' <<< "$CURL")
    REGISTER_TOKEN=$(jq -r '.token' <<< "$CURL")

    # Si l'enregistrement a été effectué, on vérifie qu'on a bien pu récupérer un id
    if [ -z "$REGISTER_ID" ] || [ "$REGISTER_ID" == "null" ];then
        echo -e "[$YELLOW ERREUR $RESET] Impossible de récupérer un id d'authentification suite à l'enregistrement."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si l'enregistrement a été effectué, on vérifie qu'on a bien pu récupérer un token
    if [ -z "$REGISTER_TOKEN" ] || [ "$REGISTER_TOKEN" == "null" ];then
        echo -e "[$YELLOW ERREUR $RESET] Impossible de récupérer un token suite à l'enregistrement."
        ERROR_STATUS=1
        clean_exit
    fi

    # Enfin si tout s'est bien passé jusque là, on ajoute l'id et le token dans le fichier de conf et on affiche un message
    sed -i "s/^ID.*/ID=\"$REGISTER_ID\"/g" $MOD_CONF
    sed -i "s/^TOKEN.*/TOKEN=\"$REGISTER_TOKEN\"/g" $MOD_CONF
    echo -e "[$GREEN OK $RESET]"  
    clean_exit
}

# Suppression de l'enregistrement auprès d'un serveur Repomanager
function unregister
{
    # Au préalable, récupération des informations concernant le serveur repomanager
    # Si la configuration est incomplète alors on quitte
    getModConf
    if [ -z "$REPOSERVER_URL" ];then
        echo -e " [$YELLOW ERREUR $RESET] Impossible de supprimer l'enregistrement auprès du serveur Repomanager. Vous devez configurer l'url du serveur."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si pas d'ID configuré alors on quitte
    if [ -z "$HOST_ID" ];then
        echo -e " [$YELLOW ERREUR $RESET] Aucun ID d'authentification n'est configuré sur cet hôte."
        ERROR_STATUS=1
        clean_exit
    fi

    # Si pas de token configuré alors on quitte
    if [ -z "$TOKEN" ];then
        echo -e " [$YELLOW ERREUR $RESET] Aucun token d'authentification n'est configuré sur cet hôte."
        ERROR_STATUS=1
        clean_exit
    fi

    # On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
    testConnection

    # Tentative de suppression de l'enregistrement
    echo -ne " Suppression de l'enregistrement auprès de ${YELLOW}${REPOSERVER_URL}${RESET} : "
    CURL=$(curl -s -q -H "Content-Type: application/json" -X DELETE -d "{\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\"}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
 
    # Parsage de la réponse et affichage des messages si il y en a
    curl_result_parse

    # Si il y a eu des erreurs suite à la requete alors on quitte
    if [ "$CURL_ERROR" -gt "0" ];then
        clean_exit
    fi

    echo -e "[$GREEN OK $RESET]"
    clean_exit
}

# Teste la connexion au serveur Repomanager
function testConnection
{
    # On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
    # if ! curl -s -q -H "Content-Type: application/json" -X GET "${REPOSERVER_URL}/api/hosts/get.php" 2> /dev/null;then
    if ! curl -s -q -H "Content-Type: application/json" -X GET -d "{\"status\":\"\"}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null;then
        echo -e " [$YELLOW ERREUR $RESET] Impossible de joindre le serveur Repomanager à l'adresse $REPOSERVER_URL"
        ERROR_STATUS=1
        clean_exit
    fi
}

# Analyse le retour d'une requête curl et affiche les éventuels message d'erreurs / de succès rencontrés
function curl_result_parse
{
    CURL_ERROR="0";

    # On récupère le code retour si il y en a un
    if ! echo "$CURL" | grep -q ".return";then
        UPDATE_RETURN=""
    else
        UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")
    fi

    # Si le code retour est vide il y a probablement eu une erreur côté serveur.
    if [ -z "$UPDATE_RETURN" ];then
        echo -e "[$YELLOW ERREUR $RESET] Le serveur n'a renvoyé aucun code retour, erreur inconnue."
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
            echo -e "[$YELLOW ERREUR $RESET] $MESSAGE"
        done
        ERROR_STATUS=1
        CURL_ERROR=2
    fi

    # Si il y a eu des message de succès on les affiche
    if echo "$CURL" | grep -q "message_success";then

        # array
        UPDATE_MESSAGE_SUCCESS=($(jq -r '.message_success[]' <<< "$CURL"))

        # $UPDATE_MESSAGE_SUCCESS est un array pouvant contenir plusieurs messages d'erreurs
        for MESSAGE in "${UPDATE_MESSAGE_SUCCESS[@]}"; do
            echo -e "[$GREEN OK $RESET] $MESSAGE"
        done
    fi

    IFS=$OLD_IFS
}

### MODULE ###

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
    echo -e "Installation du module ${YELLOW}reposerver${RESET} : [$GREEN OK $RESET]"
    
    # Configuration du module
    mod_configure
}

# Activation de l'agent reposerver
function enableReposerverAgent {
    cd ${AGENTS_ENABLED_DIR}/ &&
    ln -sfn "../mods-available/agent/reposerver.agent" &&
    echo -e "Agent ${YELLOW}reposerver${RESET} activé"
    return 0
}

# Désactivation de l'agent reposerver
function disableReposerverAgent {
    rm "${AGENTS_ENABLED_DIR}/reposerver.agent" -f &&
    echo -e "Agent ${YELLOW}reposerver${RESET} désactivé"
    return 0
}

# Configuration du module
function mod_configure {
    # Si il n'y a aucun fichier de configuration pour ce module, on lance l'installation
    if [ ! -f "$MOD_CONF" ];then
        mod_install
    fi

    # Defini si le module est exécuté par l'agent ou non
    FROM_AGENT="0"

    REGISTER_HOSTNAME=""
    REGISTER_IP=""

    # Configuration du module reposerver.mod (fichier de configuration reposerver.conf)
    REPOSERVER_URL=""
    FAILLEVEL=""
    REPOSERVER_ALLOW_CONFUPDATE=""
    REPOSERVER_ALLOW_REPOSFILES_UPDATE=""
    REPOSERVER_ALLOW_OVERWRITE=""

    # Variables de status
    UPDATE_REQUEST_TYPE=""
    UPDATE_REQUEST_STATUS=""
    SEND_GENERAL_STATUS="no"
    SEND_PACKAGES_STATUS="no"
    SEND_FULL_HISTORY="no"
    SEND_FULL_HISTORY_LIMIT=""

    # Récupération des paramètres passés à la fonction
    set +u
    while [ $# -ge 1 ];do
        case "$1" in
            --from-agent)
                FROM_AGENT="1"
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
            --allow-conf-update)
                if [ "$2" == "yes" ];then REPOSERVER_ALLOW_CONFUPDATE="yes"; else REPOSERVER_ALLOW_CONFUPDATE="no";fi
                shift
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^REPOSERVER_ALLOW_CONFUPDATE" $MOD_CONF;then
                    sed -i "/^\[CLIENT\]/a REPOSERVER_ALLOW_CONFUPDATE=\"$REPOSERVER_ALLOW_CONFUPDATE\"" $MOD_CONF
                else
                    sed -i "s/REPOSERVER_ALLOW_CONFUPDATE=.*/REPOSERVER_ALLOW_CONFUPDATE=\"$REPOSERVER_ALLOW_CONFUPDATE\"/g" $MOD_CONF
                fi
            ;;
            --allow-repos-update)
                if [ "$2" == "yes" ];then REPOSERVER_ALLOW_REPOSFILES_UPDATE="yes"; else REPOSERVER_ALLOW_REPOSFILES_UPDATE="no";fi
                shift
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^REPOSERVER_ALLOW_REPOSFILES_UPDATE" $MOD_CONF;then
                    sed -i "/^\[CLIENT\]/a REPOSERVER_ALLOW_REPOSFILES_UPDATE=\"$REPOSERVER_ALLOW_REPOSFILES_UPDATE\"" $MOD_CONF
                else 
                    sed -i "s/REPOSERVER_ALLOW_REPOSFILES_UPDATE=.*/REPOSERVER_ALLOW_REPOSFILES_UPDATE=\"$REPOSERVER_ALLOW_REPOSFILES_UPDATE\"/g" $MOD_CONF
                fi
            ;;
            --allow-overwrite)
                if [ "$2" == "yes" ];then REPOSERVER_ALLOW_OVERWRITE="yes"; else REPOSERVER_ALLOW_OVERWRITE="no";fi
                shift
                # Ajout du paramètre dans le fichier de conf
                if ! grep -q "^REPOSERVER_ALLOW_OVERWRITE" $MOD_CONF;then
                    sed -i "/^\[CLIENT\]/a REPOSERVER_ALLOW_OVERWRITE=\"$REPOSERVER_ALLOW_OVERWRITE\"" $MOD_CONF
                else 
                    sed -i "s/REPOSERVER_ALLOW_OVERWRITE=.*/REPOSERVER_ALLOW_OVERWRITE=\"$REPOSERVER_ALLOW_OVERWRITE\"/g" $MOD_CONF
                fi
            ;;
            # Récupération de la configuration complète du serveur Repomanager distant
            --get-server-conf)
                getServerConf
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
                # Si on a précisé --full alors on enverra le status complet du serveur
                SEND_GENERAL_STATUS="yes"
                SEND_PACKAGES_STATUS="yes"
                send_status
            ;;
            --send-general-status)
                # Si on a précisé --generel alors on enverra seulement le status général du serveur (OS..)
                SEND_GENERAL_STATUS="yes"
                send_status
            ;;
            --send-packages-status)
                SEND_PACKAGES_STATUS="yes"
                send_status
            ;;
            --send-full-history)
                # Si un chiffre est précisé alors il définira le nombre maximum d'évènements à envoyer
                if [ ! -z "$2" ];then
                    SEND_FULL_HISTORY_LIMIT="$2"
                fi
                SEND_FULL_HISTORY="yes"
                send_status
            ;;
            # *)
            #     echo "Paramètre de module inconnu: $1"
            #     clean_exit
            # ;;
        esac
        shift
    done
    # set -u
}

# La fonction mod_load() permet de s'assurer que le module est un minimum configuré avant qu'il soit intégré à l'exécution du programme principal
# Retourner 1 si des éléments sont manquants
# Retourner 0 si tout est OK
function mod_load {
    echo -e "  - ${YELLOW}reposerver${RESET}"

    # Si le fichier de configuration du module est introuvable alors on ne charge pas le module
    if [ ! -f "$MOD_CONF" ] || [ ! -s "$MOD_CONF" ];then
        echo -e "    [$YELLOW WARNING $RESET] Le fichier de configuration du module est introuvable. Ce module ne peut pas être chargé."
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

    # Si le paramètre REPOSERVER_ALLOW_CONFUPDATE est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^REPOSERVER_ALLOW_CONFUPDATE=" "$MOD_CONF";then
        echo "REPOSERVER_ALLOW_CONFUPDATE=\"no\"" >> "$TMP_MOD_CONF"
    else
        grep "^REPOSERVER_ALLOW_CONFUPDATE=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi
    # Si le paramètre REPOSERVER_ALLOW_OVERWRITE est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^REPOSERVER_ALLOW_OVERWRITE=" "$MOD_CONF";then
        echo "REPOSERVER_ALLOW_OVERWRITE=\"no\"" >> "$TMP_MOD_CONF"
    else
        grep "^REPOSERVER_ALLOW_OVERWRITE=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi
    # Si le paramètre REPOSERVER_ALLOW_REPOSFILES_UPDATE est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^REPOSERVER_ALLOW_REPOSFILES_UPDATE=" "$MOD_CONF";then
        echo "REPOSERVER_ALLOW_REPOSFILES_UPDATE=\"no\"" >> "$TMP_MOD_CONF"
    else
        grep "^REPOSERVER_ALLOW_REPOSFILES_UPDATE=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Section REPOSERVER
    echo -e "\n[REPOSERVER]" >> "$TMP_MOD_CONF"
    
    # Si le paramètre URL est manquant alors on l'ajoute avec une valeur par défaut
    if ! grep -q "^URL=" "$MOD_CONF";then
        echo "URL=\"\"" >> "$TMP_MOD_CONF"
    else
        grep "^URL=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    fi

    # Section [AGENT]
    echo -e "\n[AGENT]" >> "$TMP_MOD_CONF"
    grep "^WATCH_FOR_REQUEST=" "$MOD_CONF" >> "$TMP_MOD_CONF"
    grep "^WATCH_INTERFACE=" "$MOD_CONF" >> "$TMP_MOD_CONF"

	# Remplacement du fichier de conf par le fichier précédemment construit
	cat "$TMP_MOD_CONF" > "$MOD_CONF"
	rm -f "$TMP_MOD_CONF"

    # Si l'URL du serveur de repo n'est pas renseignée alors on ne charge pas le module
    if [ -z $(grep "^URL=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g') ];then
        echo -e "     [$YELLOW WARNING $RESET] L'URL du serveur ${YELLOW}reposerver${RESET} n'est pas renseignée. Ce module ne peut pas être chargé."
        return 1
    fi

    LOADED_MODULES+=("reposerver")
    echo -e "  - Module reposerver : ${YELLOW}Activé${RESET}"

    return 0
}

# Récupération de la configuration complète du module, dans son fichier de conf
function getModConf {
    # Configuration client (section [CLIENT])
    HOST_ID="$(grep "^ID=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    TOKEN="$(grep "^TOKEN=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_ALLOW_CONFUPDATE="$(grep "^REPOSERVER_ALLOW_CONFUPDATE=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_ALLOW_OVERWRITE="$(grep "^REPOSERVER_ALLOW_OVERWRITE=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_ALLOW_REPOSFILES_UPDATE="$(grep "^REPOSERVER_ALLOW_REPOSFILES_UPDATE=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"

    # Configuration serveur (section [REPOSERVER])
    REPOSERVER_URL="$(grep "^URL=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_OS_FAMILY="$(grep "^OS_FAMILY=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_OS_NAME="$(grep "^OS_NAME=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_OS_ID="$(grep "^OS_ID=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_OS_VERSION="$(grep "^OS_VERSION=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_PACKAGES_OS_VERSION="$(grep "^PACKAGES_OS_VERSION=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_MANAGE_CLIENT_CONF="$(grep "^MANAGE_CLIENTS_CONF=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
    REPOSERVER_MANAGE_CLIENT_REPOS="$(grep "^MANAGE_CLIENTS_REPOSCONF=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"

    # Récupération du FAILLEVEL pour ce module
    FAILLEVEL=$(grep "^FAILLEVEL=" "$MOD_CONF" | cut -d'=' -f2 | sed 's/"//g')

    # Si on n'a pas pu récupérer le FAILLEVEL dans le fichier de conf alors on le set à 1 par défaut
    # De même si le FAILLEVEL récupéré n'est pas un chiffre alors on le set à 1
    if [ -z "$FAILLEVEL" ];then echo -e "[$YELLOW WARNING $RESET] Paramètre FAILLEVEL non configuré pour ce module → configuré à 1 (arrêt en cas d'erreur mineure ou critique)"; FAILLEVEL="1";fi
    if ! [[ "$FAILLEVEL" =~ ^[0-9]+$ ]];then echo -e "[$YELLOW WARNING $RESET] Paramètre FAILLEVEL non configuré pour ce module → configuré à 1 (arrêt en cas d'erreur mineure ou critique)"; FAILLEVEL="1";fi

    if [ -z "$REPOSERVER_URL" ];then
        echo -e " - Module reposerver : [${YELLOW} ERREUR ${RESET}] URL du serveur de repo inconnue ou vide"
        return 2
    fi

    # Si REPOSERVER_PACKAGES_OS_VERSION n'est pas vide, cela signifie que le serveur distant dispose de miroirs de paquets dont la version est différente de sa propre version
    # Dans ce cas on overwrite la variable REPOSERVER_OS_VERSION
    if [ ! -z "$REPOSERVER_PACKAGES_OS_VERSION" ];then REPOSERVER_OS_VERSION="$REPOSERVER_PACKAGES_OS_VERSION";fi

    return 0
}

# Récupération de la configuration générale du serveur de repos
function getServerConf {

    TMP_FILE_MODULE="/tmp/.linupdate_${PROCID}_mod_reposerver_section_module.tmp"
    TMP_FILE_CLIENT="/tmp/.linupdate_${PROCID}_mod_reposerver_section_client.tmp"
    TMP_FILE_AGENT="/tmp/.linupdate_${PROCID}_mod_reposerver_section_agent.tmp"
    TMP_FILE_REPOSERVER="/tmp/.linupdate_${PROCID}_mod_reposerver_section_reposerver.tmp"

    # On charge les paramètres du module
    getModConf

    # Demande de la configuration auprès du serveur de repos
    # Ce dernier renverra la configuration au format JSON
    CURL=$(curl -s -q -H "Content-Type: application/json" -X GET -d "{\"getConfiguration\":\"server\"}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
    curl_result_parse

    # Si il y a eu une erreur lors de la requête on quitte la fonction
    if [ "$CURL_ERROR" != "0" ];then
        return 2
    fi

    # Puis on récupère la configuration transmise par le serveur au format JSON
    # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
    # On remplace à la volée l'environnement dans le contenu récupéré
    for ROW in $(echo "${CURL}" | jq -r '.configuration | @base64'); do
        _jq() {
            echo ${ROW} | base64 --decode | jq -r ${1}
        }

        REPOSERVER_IP=$(_jq '.Ip')
        REPOSERVER_URL=$(_jq '.Url')
        REPOSERVER_OS_FAMILY=$(_jq '.Os_family')
        REPOSERVER_OS_NAME=$(_jq '.Os_name')
        REPOSERVER_OS_ID=$(_jq '.Os_id')
        REPOSERVER_OS_VERSION=$(_jq '.Os_version')
        REPOSERVER_PACKAGE_TYPE=$(_jq '.Package_type')
        REPOSERVER_PACKAGE_OS_VERSION=$(_jq '.Package_os_version')
        REPOSERVER_MANAGE_CLIENT_CONF=$(_jq '.Manage_client_conf')
        REPOSERVER_MANAGE_CLIENT_REPOS=$(_jq '.Manage_client_repos')
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
    echo "IP=\"$REPOSERVER_IP\"" >> "$TMP_FILE_REPOSERVER"
    echo "URL=\"$REPOSERVER_URL\"" >> "$TMP_FILE_REPOSERVER"
    echo "OS_FAMILY=\"$REPOSERVER_OS_FAMILY\"" >> "$TMP_FILE_REPOSERVER"
    echo "OS_NAME=\"$REPOSERVER_OS_NAME\"" >> "$TMP_FILE_REPOSERVER"
    echo "OS_ID=\"$REPOSERVER_OS_ID\"" >> "$TMP_FILE_REPOSERVER"
    echo "OS_VERSION=\"$REPOSERVER_OS_VERSION\"" >> "$TMP_FILE_REPOSERVER"
    echo "PACKAGE_TYPE=\"$REPOSERVER_PACKAGE_TYPE\"" >> "$TMP_FILE_REPOSERVER"
    echo "PACKAGE_OS_VERSION=\"$REPOSERVER_PACKAGE_OS_VERSION\"" >> "$TMP_FILE_REPOSERVER"
    echo "MANAGE_CLIENTS_CONF=\"$REPOSERVER_MANAGE_CLIENT_CONF\"" >> "$TMP_FILE_REPOSERVER"
    echo "MANAGE_CLIENTS_REPOSCONF=\"$REPOSERVER_MANAGE_CLIENT_REPOS\"" >> "$TMP_FILE_REPOSERVER"
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
function preCheck {
    # Si REPOSERVER_OS_FAMILY, *NAME ou *VERSION diffère du type de serveur sur lequel est exécuté ce module (par exemple le serveur reposerver est un serveur CentOS et nous somme sur un serveur Debian), alors on affiche un warning
    if [ "$REPOSERVER_OS_FAMILY" != "$OS_FAMILY" ];then
        echo -e "   [${YELLOW} ERREUR ${RESET}] Le serveur de repo distant ne gère pas la même famille d'OS que cette machine."
        return 2
    fi

    if [ "$REPOSERVER_OS_ID" != "$OS_NAME" ];then
        echo -e "   [${YELLOW} WARNING ${RESET}] Le serveur de repo distant ne gère pas le même OS que cette machine, les paquets peuvent être incompatibles."
        return 1
    fi

    if [ "$REPOSERVER_OS_VERSION" != "$OS_VERSION" ];then
        echo -e "   [${YELLOW} ERREUR ${RESET}] Le serveur de repo distant ne gère pas la même version d'OS que cette machine."
        return 2
    fi
}

# Récupération de la configuration générale du profil de l'hôte, auprès du serveur de repos
function getProfileConf {
    # Si le serveur reposerver ne gère pas les profils ou que le client refuse d'être mis à jour par son serveur de repo, on quitte la fonction
    echo -ne "  → Mise à jour de la configuration du profil $PROFILE : "

    if [ "$REPOSERVER_MANAGE_CLIENT_CONF" == "no" ] || [ "$REPOSERVER_ALLOW_CONFUPDATE" == "no" ];then
        if [ "$REPOSERVER_MANAGE_CLIENT_CONF" == "no" ];then
            echo -e "${YELLOW}Désactivé (non pris en charge par le serveur Repomanager)${RESET}"
        fi
        if [ "$REPOSERVER_ALLOW_CONFUPDATE" == "no" ];then
            echo -e "${YELLOW}Désactivé${RESET}"
        fi

        return 1
    fi

    # Demande de la configuration des repos auprès du serveur de repos
    # Ce dernier renverra la configuration au format JSON
    CURL=$(curl -s -q -H "Content-Type: application/json" -X GET -d "{\"id\":\"$HOST_ID\",\"token\":\"$TOKEN\",\"profile\":\"$PROFILE\",\"getConfiguration\":\"general\"}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
    curl_result_parse

    # Si il y a eu une erreur lors de la requête on quitte la fonction
    if [ "$CURL_ERROR" != "0" ];then
        return 2
    fi

    # Puis on récupère la configuration transmise par le serveur au format JSON
    # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
    # On remplace à la volée l'environnement dans le contenu récupéré
    for ROW in $(echo "${CURL}" | jq -r '.configuration | @base64'); do
        _jq() {
        echo ${ROW} | base64 --decode | jq -r ${1}
        }

        EXCLUDE_MAJOR=$(_jq '.Package_exclude_major')
        EXCLUDE=$(_jq '.Package_exclude')
        NEED_RESTART=$(_jq '.Service_restart')
    done

    # Si la valeur des paramètres == null alors cela signifie qu'il n'y a aucune exclusion de paquet
    if [ "$EXCLUDE_MAJOR" == "null" ];then
        EXCLUDE_MAJOR=""
    fi
    if [ "$EXCLUDE" == "null" ];then
        EXCLUDE=""
    fi
    if [ "$NEED_RESTART" == "null" ];then
        NEED_RESTART=""
    fi

    # On applique la nouvelle configuration récupérée
    # D'abord on nettoie la partie [SOFT] du fichier de conf car c'est cette partie qui va être remplacée par la nouvelle conf : 
    sed -i '/^\[SOFTWARE CONFIGURATION\]/,$d' "$CONF" &&

    # Puis on injecte la nouvelle conf récupérée
    echo -e "[SOFTWARE CONFIGURATION]\nEXCLUDE_MAJOR=\"${EXCLUDE_MAJOR}\"\nEXCLUDE=\"${EXCLUDE}\"\nNEED_RESTART=\"${NEED_RESTART}\"" >> "$CONF"

    echo -e "[${GREEN} OK ${RESET}]"

    # Enfin on applique la nouvelle conf en récupérant de nouveau les paramètres du fichier de conf :
    getConf
}

# Récupération de la configuration des repos du profil de l'hôte, auprès du serveur de repos
function getProfileRepos {
    # Si on est autorisé à mettre à jour les fichiers de conf de repos et si le serveur de repos le gère
    echo -ne "  → Mise à jour de la configuration des repos : "

    if [ "$REPOSERVER_MANAGE_CLIENT_REPOS" == "yes" ] && [ "$REPOSERVER_ALLOW_REPOSFILES_UPDATE" == "yes" ];then

        # Demande de la configuration des repos auprès du serveur de repos
        # Ce dernier renverra la configuration au format JSON
        CURL=$(curl -s -q -H "Content-Type: application/json" -X GET -d "{\"id\":\"$HOST_ID\",\"token\":\"$TOKEN\",\"profile\":\"$PROFILE\",\"getConfiguration\":\"repos\"}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
        curl_result_parse

        # Si il y a eu une erreur lors de la requête on quitte la fonction
        if [ "$CURL_ERROR" != "0" ];then
            return 2
        fi

        # Sinon on récupère les configurations de repos que la requête a renvoyé
        # On s'assure que le paramètre 'configuraiton' fait bien partie de la réponse JSON renvoyée par le serveur
        # Ce paramètre peut être vide toutefois si la configuration du profil côté serveur n'a aucun repo de configuré
        if ! echo "$CURL" | grep -q "configuration";then
            echo -e "[$YELLOW ERREUR $RESET] La configuration des repos du profil $PROFILE n'a pas été transmise par le serveur."
            return 2
        fi

        # Si le paramètre existe alors on peut continuer le traitement
        # D'abord on vide les fichiers .repo ou .list présents sur l'hôte car ils seront remplacés par la configuration transférée par le serveur.
        if [ "$OS_FAMILY" == "Redhat" ];then
            rm /etc/yum.repos.d/*.repo -f
        fi
        if [ "$OS_FAMILY" == "Debian" ];then
            rm /etc/apt/sources.list.d/*.list -f
        fi

        # Puis on récupère la configuration des nouveaux fichiers .repo ou .list transmis par le serveur au format JSON
        # On parcourt chaque configuration et on récupère le nom du fichier à créer, la description et le contenu à insérer
        # On remplace à la volée l'environnement dans le contenu récupéré
        for ROW in $(echo "${CURL}" | jq -r '.configuration[] | @base64'); do
            _jq() {
            echo ${ROW} | base64 --decode | jq -r ${1}
            }

            FILENAME=$(_jq '.filename')
            DESCRIPTION=$(_jq '.description')
            CONTENT=$(_jq '.content' | sed "s/__ENV__/${SERVER_ENV}/g")

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

        if [ "$OS_FAMILY" == "Redhat" ];then
            # Application de permissions et vidage du cache yum
            chown root:root /etc/yum.repos.d/*.repo
            chmod 660 /etc/yum.repos.d/*.repo
            yum clean all -q
        fi

        if [ "$OS_FAMILY" == "Debian" ];then
            # Application de permissions et vidage du cache apt
            chown root:root /etc/apt/sources.list.d/*.list
            chmod 660 /etc/apt/sources.list.d/*.list
            apt-get clean
        fi

        echo -e "[$GREEN OK $RESET]"

    else
        if [ "$REPOSERVER_MANAGE_CLIENT_REPOS" != "yes" ];then
            echo -e "${YELLOW}Désactivé (non pris en charge par le serveur Repomanager)${RESET}"
            return 1
        fi

        if [ "$REPOSERVER_ALLOW_REPOSFILES_UPDATE" != "yes" ];then
            echo -e "${YELLOW}Désactivé${RESET}"
            return 1
        fi
    fi
    echo ""
}

# Exécution pre-mise à jour des paquets
function pre {
    # Fail-level :
    # 1 = quitte à la moindre erreur (module désactivé, le serveur ne gère pas le même OS, erreur mineure, critique)
    # 2 = quitte seulement en cas d'erreur critique
    # 3 = continue même en cas d'erreur critique (ex : impossible de récupérer la conf du serveur de repo), la machine se mettra à jour selon la conf actuellement en place dans son fichier de conf

    # Codes de retour :
    # Aucune erreur :   return 0
    # Erreur mineure :  return 1
    # Erreur critique : return 2

    echo -e " Exécution du module ${YELLOW}reposerver${RESET}"

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
    if [ "$FAILLEVEL" -eq "3" ] && [ "$RESULT" -gt "0" ];then return 1;fi                         # Si FAILLEVEL = 3 et qu'il y a une erreur au chargement de la conf du module alors on quitte le module sans pour autant quitter repomanager (clean_exit)

    # On vérifie que la configuration du serveur de repo est compatible avec notre OS
    preCheck
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    # On met à jour notre configuration à partir du serveur de repo (profils), si cela est autorisé des deux côtés
    getProfileConf
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    # On met à jour notre configuration des repos à partir du serveurs de repo (profils), si cela est autorisé des deux côtés
    getProfileRepos
    RESULT="$?"
    if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
    if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

    # Aquittement du status auprès du serveur reposerver
    UPDATE_REQUEST_TYPE="packages-update"
    UPDATE_REQUEST_STATUS="running"
    update_request_status

    return 0
}

# Exécution post-mise à jour des paquets
function post {
    # Aquittement du status auprès du serveur reposerver
    UPDATE_REQUEST_TYPE="packages-update"
    if [ "$UPDATE_ERROR" -gt "0" ];then
        UPDATE_REQUEST_STATUS="error"
    else 
        UPDATE_REQUEST_STATUS="done"
    fi
    update_request_status

    # Si il y a eu des paquets à mettre à jour lors de cette exécution alors on exécute les actions suivantes
    if [ "$SOMETHING_TO_UPDATE" == "yes" ];then
        # Généralement les paquets "*-release" sur Redhat/CentOS remettent en place des fichiers .repo. Si un paquet de ce type a été mis à jour alors on remets à jour la configuration des repos à partir du serveurs de repo (profils), si cela est autorisé des deux côtés
        if echo "${PACKAGES[*]}" | grep -q "-release";then
            getProfileRepos
        fi

        # On renvoie les 4 derniers historique d'évènements au serveur reposerver
        /opt/linupdate/linupdate --mod-configure reposerver --from-agent --send-full-history 4
        /opt/linupdate/linupdate --mod-configure reposerver --from-agent --send-available-packages-status
    fi

    return 0
}

## Envoi de status (API) ##

# Envoi au serveur Repomanager l'état actuel de l'hôte
# Fonction principale
function send_status {
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
        echo -e "[$YELLOW ERREUR $RESET] L'ID de cette machine est manquant"
        ERROR_STATUS=1
        clean_exit
    fi
    if [ -z "$TOKEN" ];then
        echo -e "[$YELLOW ERREUR $RESET] Le token de cette machine est manquant"
        ERROR_STATUS=1
        clean_exit
    fi

    # Exécution des sous-fonctions

    # Général
    if [ "$SEND_GENERAL_STATUS" == "yes" ];then
        send_general_status
    fi

    # Paquets
    if [ "$SEND_PACKAGES_STATUS" == "yes" ];then
        send_packages_status
    fi

    # Historique des évènements apt ou yum
    if [ "$SEND_FULL_HISTORY" == "yes" ];then  
        genFullHistory
    fi

    # Paquets disponibles sur cet hôte
    if [ "$SEND_AVAILABLE_PACKAGES_STATUS" == "yes" ];then
        send_available_packages_status
    fi

    # Paquets installés sur cet hôte
    if [ "$SEND_INSTALLED_PACKAGE_STATUS" == "yes" ];then
        send_installed_packages_status
    fi

    IFS="$OLD_IFS"

    clean_exit
}

# Mettre à jour le status d'une demande initialisée par le serveur repomanager
function update_request_status {
    if [ -z "$UPDATE_REQUEST_TYPE" ];then
        return
    fi
    if [ -z "$UPDATE_REQUEST_STATUS" ];then
        return
    fi

    if [ "$VERBOSE" -gt "0" ];then
        echo -ne " Acquittement auprès du serveur Repomanager : "
    fi

    CURL_PARAMS="\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\", \"set_update_request_type\":\"$UPDATE_REQUEST_TYPE\", \"set_update_request_status\":\"$UPDATE_REQUEST_STATUS\""

    CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)

    # On n'affiche les message d'erreur et de succès uniquement si la verbosité est supérieur à 0
    if [ "$VERBOSE" -gt "0" ];then
        curl_result_parse
    fi
}

# Envoi au serveur Repomanager l'état général de l'hôte (son os, version, profil, env)
function send_general_status {
    UPDATE_REQUEST_TYPE="general-status-update"
    UPDATE_REQUEST_STATUS="running"
    update_request_status

    UPDATE_MESSAGE_SUCCESS=""
    UPDATE_MESSAGE_ERROR=""

    # Paramètres d'authentification (id et token)
    CURL_PARAMS="\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\""

    # Paramètres généraux (os, version, profil...)
    if [ ! -z "$OS_NAME" ] && [ ! -z "$OS_VERSION" ];then
        CURL_PARAMS+=", \"os\":\"$OS_NAME\", \"os_version\":\"$OS_VERSION\", \"os_family\":\"$OS_FAMILY\", \"type\":\"$VIRT_TYPE\", \"kernel\":\"$KERNEL\", \"arch\":\"$ARCH\""
    fi
    if [ ! -z "$PROFILE" ];then
        CURL_PARAMS+=", \"profile\":\"$PROFILE\""
    fi
    if [ ! -z "$SERVER_ENV" ];then
        CURL_PARAMS+=", \"env\":\"$SERVER_ENV\""
    fi

    # Fin de construction des paramètres curl puis envoi.

    # Envoi des données :
    echo -e " Envoi du status à ${YELLOW}${REPOSERVER_URL}${RESET} : "
    CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
    UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")

    # Récupération et affichage des messages
    curl_result_parse

    if [ "$CURL_ERROR" -eq "0" ];then
        UPDATE_REQUEST_STATUS="done"
    else 
        UPDATE_REQUEST_STATUS="error"
    fi

    update_request_status
}

function send_packages_status {
    INSTALLED_PACKAGES=""
    UPDATE_MESSAGE_SUCCESS=""
    UPDATE_MESSAGE_ERROR=""

    UPDATE_REQUEST_TYPE="packages-status-update"
    UPDATE_REQUEST_STATUS="running"
    update_request_status

    # Exécution des différentes fonctions

    # Sauf si il y a une erreur, le status sera done
    UPDATE_REQUEST_STATUS="done"

    genFullHistory
    if [ "$?" -ne "0" ];then
        UPDATE_REQUEST_STATUS="error"
    fi

    send_available_packages_status
    if [ "$?" -ne "0" ];then
        UPDATE_REQUEST_STATUS="error"
    fi

    send_installed_packages_status
    if [ "$?" -ne "0" ];then
        UPDATE_REQUEST_STATUS="error"
    fi

    update_request_status
}

# Envoi au serveur Repomanager de la liste des paquets installés sur l'hôte
function send_installed_packages_status {
    INSTALLED_PACKAGES=""
    UPDATE_MESSAGE_SUCCESS=""
    UPDATE_MESSAGE_ERROR=""

    # Paramètres concernant les paquets installés sur le système (tous les paquets)
    echo "Construction de la liste des paquets installés sur le système..."

    INSTALLED_PACKAGES_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_installed_pkgs.tmp"

    # Construction de la liste des paquets
    # Cas Redhat
    if [ "$OS_FAMILY" == "Redhat" ];then
        repoquery -a --installed --qf="%{name} %{epoch}:%{version}-%{release}.%{arch}" > "$INSTALLED_PACKAGES_TMP"
    fi
    # Cas Debian
    if [ "$OS_FAMILY" == "Debian" ];then
        dpkg-query -W -f='${Status}\t${package}\t${version}\t\n' | grep "^install ok installed" | awk '{print $4, $5}' > "$INSTALLED_PACKAGES_TMP"
    fi

    # Paramètres d'authentification (id et token)
    CURL_PARAMS="\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\""

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
        if [ -z "$PACKAGE_NAME" ];then continue;fi
                
        # Ajout du nom du paquet, sa version actuelle et sa version disponible à l'array $INSTALLED_PACKAGES
        INSTALLED_PACKAGES+="${PACKAGE_NAME}|${PACKAGE_ACT_VERSION},"
    done

    rm "$INSTALLED_PACKAGES_TMP" -f

    # Suppression de la dernière virgule :
    INSTALLED_PACKAGES=$(echo "${INSTALLED_PACKAGES::-1}")
    
    # Construction des paramètres curl à envoyer
    CURL_PARAMS="$CURL_PARAMS, \"installed_packages\":\"$INSTALLED_PACKAGES\""

    # Envoi des données :
    echo -ne " Envoi des informations à ${YELLOW}${REPOSERVER_URL}${RESET} : "
    CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
    
    # Récupération et affichage des messages
    curl_result_parse

    if [ "$CURL_ERROR" -eq "0" ];then
        UPDATE_REQUEST_STATUS="done"
        return 0

    else 
        UPDATE_REQUEST_STATUS="error"
        return 1
    fi
}

# Envoi au serveur Repomanager de la liste des paquets disponibles pour mettre à jour
function send_available_packages_status {
    AVAILABLE_PACKAGES=""

    # Paramètres d'authentification (id et token)
    CURL_PARAMS="\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\""

    # Paramètres concernant les paquets (paquets disponibles...)

    echo "Construction de la liste des paquets disponibles..."

    # Récupération des paquets disponibles
    AVAILABLE_PACKAGES_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_available_pkgs.tmp"

    # Cas Redhat
    if [ "$OS_FAMILY" == "Redhat" ];then
        # Récupération des paquets disponibles pour mise à jour
        repoquery -q -a --qf="%{name} %{epoch}:%{version}-%{release}.%{arch}" --pkgnarrow=updates > "$AVAILABLE_PACKAGES_TMP"
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
            if [ -z "$PACKAGE_NAME" ];then continue;fi

            # Ajout du nom du paquet, sa version actuelle et sa version disponible à l'array $AVAILABLE_PACKAGES
            AVAILABLE_PACKAGES+="${PACKAGE_NAME}|${PACKAGE_AVL_VERSION},"
        done

        # Suppression de la dernière virgule :
        AVAILABLE_PACKAGES=$(echo "${AVAILABLE_PACKAGES::-1}")
    fi

    rm "$AVAILABLE_PACKAGES_TMP" -f

    # Construction des paramètres curl à envoyer
    CURL_PARAMS="$CURL_PARAMS, \"available_packages\":\"$AVAILABLE_PACKAGES\""

    # Envoi des données :
    echo -ne " Envoi du status à ${YELLOW}${REPOSERVER_URL}${RESET} : "
    CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts" 2> /dev/null)
    
    # Récupération et affichage des messages
    curl_result_parse

    if [ "$CURL_ERROR" -eq "0" ];then
        UPDATE_REQUEST_STATUS="done"
        return 0

    else 
        UPDATE_REQUEST_STATUS="error"
        return 1
    fi
}

# Fonction de parsage d'un évènement
# Appelée par la fonction genFullHistory
function event_parser {
    if [ "$OS_FAMILY" == "Redhat" ];then
        # On extrait tout le contenu de l'évènement dans un fichier
        TMP_EVENT_FILE="/tmp/.linupdate_${PROCID}_mod_reposerver_yum_event.tmp"
        LC_ALL="en_US.UTF-8" yum history info "$YUM_HISTORY_ID" > "$TMP_EVENT_FILE"
        # Extrait la date et l'heure au format : Thu Mar 25 10:40:37 2021
        EVENT_DATE=$(grep "^Begin time" "$TMP_EVENT_FILE" | sed 's/  //g' | sed 's/Begin time : //g')
        # Extrait la date de la chaine précédemment récupéréé
        DATE_START=$(date -d "$EVENT_DATE" +'%Y-%m-%d')
        # Extrait l'heure de la chaine précédemment récupéréé
        TIME_START=$(date -d "$EVENT_DATE" +'%H:%M:%S')
        #DATE_END=$(echo "$EVENT" | grep "^End-Date:" | awk '{print $2}')
        #TIME_END=$(echo "$EVENT" | grep "^End-Date:" | awk '{print $3}')

        # On reformate le fichier temporaire pour être sûr de ne garder que les paquets traités
        sed -i -n '/Packages Altered/,$p' "$TMP_EVENT_FILE"

        # On peut également récupérer la liste des paquets installés, mis à jour jour, supprimés...
        PACKAGES_INSTALLED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "^ +Install " | grep -Ev "Dep-Install|Installed|Installing" | awk '{print $2}')
        DEPENDENCIES_INSTALLED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "^ +Dep-Install " | grep -Ev "Installed|Installing" | awk '{print $2}')
        PACKAGES_UPGRADED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "^ +Updated |^ +Update " | grep -v "Installing" | awk '{print $2}')
        PACKAGES_REMOVED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "^ +Erase " | awk '{print $2}')
        PACKAGES_DOWNGRADED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "^ +Downgrade " | awk '{print $2}')
        PACKAGES_REINSTALLED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "^ +Reinstall " | awk '{print $2}')
    fi

    if [ "$OS_FAMILY" == "Debian" ];then
        # On récupère tout le bloc de l'évènement en cours : à partir de la date de début (START_DATE) et jusqu'à rencontrer un saut de ligne
        # Si le fichier est compréssé, on doit utiliser zcat pour le lire
        if echo "$LOG" | egrep -q ".gz";then
            EVENT=$(zcat "$LOG" | sed -n "/$START_DATE/,/^$/p")
        # Si le fichier n'est pas compréssé on peut utiliser sed directement
        else
            EVENT=$(sed -n "/$START_DATE/,/^$/p" "$LOG")
        fi

        # A partir du bloc de l'évènement récupéré, on peut récupérer la date et l'heure de début et la date et l'heure de fin
        DATE_START=$(echo "$EVENT" | grep "^Start-Date:" | awk '{print $2}')
        TIME_START=$(echo "$EVENT" | grep "^Start-Date:" | awk '{print $3}')
        DATE_END=$(echo "$EVENT" | grep "^End-Date:" | awk '{print $2}')
        TIME_END=$(echo "$EVENT" | grep "^End-Date:" | awk '{print $3}')
        # On peut également récupérer la liste des paquets installés, mis à jour jour, supprimés...
        PACKAGES_INSTALLED_LIST=$(echo "$EVENT" | grep "^Install:" | sed 's/Install: //g')
        PACKAGES_UPGRADED_LIST=$(echo "$EVENT" | grep "^Upgrade:" | sed 's/Upgrade: //g')
        PACKAGES_REMOVED_LIST=$(echo "$EVENT" | grep "^Remove:" | sed 's/Remove: //g')
        PACKAGES_PURGED_LIST="$(echo "$EVENT" | grep "^Purge:" | sed 's/Purge: //g')"
        PACKAGES_DOWNGRADED_LIST=$(echo "$EVENT" | grep "^Downgrade:" | sed 's/Downgrade: //g')
        PACKAGES_REINSTALLED_LIST="$(echo "$EVENT" | grep "^Reinstall:" | sed 's/Reinstall: //g')"
    fi

    rm "$TMP_EVENT_FILE" -f
}

# Fonction de parsage de multiples évènements ayant lieu à la même date et heure
# Debian (apt) uniquement
function multiple_event_parser {
    # Si le fichier temporaire est vide alors on ne traite pas
    if [ ! -s "$MULTIPLE_EVENTS_TMP" ];then
        return
    fi

    # Sur les multiples dates et heures affichées dans le fichier, on n'en garde qu'une seule
    DATE_START=$(grep "^Start-Date:" "$MULTIPLE_EVENTS_TMP" | awk '{print $2}' | head -n1)
    TIME_START=$(grep "^Start-Date:" "$MULTIPLE_EVENTS_TMP" | awk '{print $3}' | head -n1)
    DATE_END=$(grep "^End-Date:" "$MULTIPLE_EVENTS_TMP" | awk '{print $2}' | tail -n1)
    TIME_END=$(grep "^End-Date:" "$MULTIPLE_EVENTS_TMP" | awk '{print $3}' | tail -n1)

    # On traite tous les Install qu'il y a eu à ces évènements communs
    if grep -q "^Install:" "$MULTIPLE_EVENTS_TMP";then
        for OCCURENCE in $(grep "^Install:" "$MULTIPLE_EVENTS_TMP");do
            PACKAGES_INSTALLED_LIST+=$(echo "$OCCURENCE" | sed 's/Install: //g')", "
        done
        # Suppression de la dernière virgule :
        PACKAGES_INSTALLED_LIST=$(echo "${PACKAGES_INSTALLED_LIST::-2}")
    fi

    # On traite tous les Upgrade qu'il y a eu à ces évènements communs
    if grep -q "^Upgrade:" "$MULTIPLE_EVENTS_TMP";then
        for OCCURENCE in $(grep "^Upgrade:" "$MULTIPLE_EVENTS_TMP");do
            PACKAGES_UPGRADED_LIST+=$(echo "$OCCURENCE" | sed 's/Upgrade: //g')", "
        done
        # Suppression de la dernière virgule :
        PACKAGES_UPGRADED_LIST=$(echo "${PACKAGES_UPGRADED_LIST::-2}")
    fi

    # On traite tous les Remove qu'il y a eu à ces évènements communs
    if grep -q "^Remove:" "$MULTIPLE_EVENTS_TMP";then
        for OCCURENCE in $(grep "^Remove:" "$MULTIPLE_EVENTS_TMP");do
            PACKAGES_REMOVED_LIST+=$(echo "$OCCURENCE" | sed 's/Remove: //g')", "
        done
        # Suppression de la dernière virgule :
        PACKAGES_REMOVED_LIST=$(echo "${PACKAGES_REMOVED_LIST::-2}")
    fi

    # On traite tous les Purge qu'il y a eu à ces évènements communs
    if grep -q "^Purge:" "$MULTIPLE_EVENTS_TMP";then
        for OCCURENCE in $(grep "^Purge:" "$MULTIPLE_EVENTS_TMP");do
            PACKAGES_PURGED_LIST+=$(echo "$OCCURENCE" | sed 's/Purge: //g')", "
        done
        # Suppression de la dernière virgule :
        PACKAGES_PURGED_LIST=$(echo "${PACKAGES_PURGED_LIST::-2}")
    fi

    # On traite tous les Downgrade qu'il y a eu à ces évènements communs
    if grep -q "^Downgrade:" "$MULTIPLE_EVENTS_TMP";then
        for OCCURENCE in $(grep "^Downgrade:" "$MULTIPLE_EVENTS_TMP");do
            PACKAGES_DOWNGRADED_LIST+=$(echo "$OCCURENCE" | sed 's/Downgrade: //g')", "
        done
        # Suppression de la dernière virgule :
        PACKAGES_DOWNGRADED_LIST=$(echo "${PACKAGES_DOWNGRADED_LIST::-2}")
    fi

    # On traite tous les Reinstall qu'il y a eu à ces évènements communs
    if grep -q "^Reinstall:" "$MULTIPLE_EVENTS_TMP";then
        for OCCURENCE in $(grep "^Reinstall:" "$MULTIPLE_EVENTS_TMP");do
            PACKAGES_REINSTALLED_LIST+=$(echo "$OCCURENCE" | sed 's/Reinstall: //g')", "
        done
        # Suppression de la dernière virgule :
        PACKAGES_REINSTALLED_LIST=$(echo "${PACKAGES_REINSTALLED_LIST::-2}")
    fi
}

# Envoi au serveur repomanager l'historique des opérations effectuées sur les paquets (installation, mises à jour, suppression...)
# Se base sur les historiques de yum et d'apt
function genFullHistory {
# Contiendra la liste de tous les évènements
EVENTS=""
IGNORE_EVENT=""

UPDATE_REQUEST_TYPE="full-history-update"
UPDATE_REQUEST_STATUS="running"
update_request_status

# Le paramètre SEND_FULL_HISTORY_LIMIT défini le nb maximum d'évènements à envoyer, cela permet d'éviter d'envoyer inutilement l'historique complet du serveur dans certains cas.
# Si ce paramètre est laissé vide alors il n'y a aucune limite, on le set à 99999999.
if [ -z "$SEND_FULL_HISTORY_LIMIT" ];then
    SEND_FULL_HISTORY_LIMIT="99999999"
fi
# On initialise une variable à 0 qui sera incrémentée jusqu'à atteindre la limite SEND_FULL_HISTORY_LIMIT.
HISTORY_LIMIT_COUNTER="0"

TMP_FILE="/tmp/.linupdate_${PROCID}_mod_reposerver_events_history.json"

# Préparation d'un fichier JSON dans lequel il restera à insérer chaque évènement (1 évènement = une date+heure trouvée dans le fichier de log)
cat <<EOF > /tmp/.linupdate_${PROCID}_mod_reposerver_events_history.json
{
    "id" : "$HOST_ID",
    "token" : "$TOKEN",
    "events" : [
        __INSERT_EVENTS__        
    ]
}
EOF

OLD_IFS=$IFS

if [ "$OS_FAMILY" == "Redhat" ];then
    echo "Construction de l'historique des évènements yum..."

    # Récupération de tous les ID d'évènements dans la base de données de yum
    YUM_HISTORY_IDS=$(yum history list all | tail -n +4 | awk '{print $1}' | grep -v "history" | tac)

    # Pour chaque évènement on peut récupérer la date et l'heure de début et la date et l'heure de fin
    for YUM_HISTORY_ID in $(echo "$YUM_HISTORY_IDS");do
        # On sort de la boucle si on a atteint la limite d'évènement à envoyer fixée par l'utilisateur
        if [ "$HISTORY_LIMIT_COUNTER" == "$SEND_FULL_HISTORY_LIMIT" ];then
            break
        fi

        PACKAGES_INSTALLED_LIST=""
        DEPENDENCIES_INSTALLED_LIST=""
        PACKAGES_UPGRADED_LIST=""
        PACKAGES_REMOVED_LIST=""
        PACKAGES_DOWNGRADED_LIST=""
        PACKAGES_REINSTALLED_LIST=""

        PACKAGES_INSTALLED=""
        DEPENDENCIES_INSTALLED=""
        PACKAGES_UPGRADED=""
        PACKAGES_REMOVED=""
        PACKAGES_DOWNGRADED=""
        PACKAGES_REINSTALLED=""

        event_parser

        # Traitement de la liste des paquets installés à cette date et heure
        if [ ! -z "$PACKAGES_INSTALLED_LIST" ];then
            for LINE in $(echo "$PACKAGES_INSTALLED_LIST");do
                PACKAGE_NAME=$(echo "$LINE" | sed 's/-[0-9].*//g')
                PACKAGE_VERSION=$(echo "$LINE" | sed "s/$PACKAGE_NAME//g" | sed 's/^-//g')
                PACKAGES_INSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
            done

            # Suppression de la dernière virgule :
            PACKAGES_INSTALLED=$(echo "${PACKAGES_INSTALLED::-1}")
            # Création de l'array contenant les paquets installés, au format JSON
            PACKAGES_INSTALLED="\"installed\":[$PACKAGES_INSTALLED],"
        fi

        # Traitement de la liste des dépendances installées à cette date et heure
        if [ ! -z "$DEPENDENCIES_INSTALLED_LIST" ];then
            for LINE in $(echo "$DEPENDENCIES_INSTALLED_LIST");do
                PACKAGE_NAME=$(echo "$LINE" | sed 's/-[0-9].*//g')
                PACKAGE_VERSION=$(echo "$LINE" | sed "s/$PACKAGE_NAME//g" | sed 's/^-//g')
                DEPENDENCIES_INSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
            done

            # Suppression de la dernière virgule :
            DEPENDENCIES_INSTALLED=$(echo "${DEPENDENCIES_INSTALLED::-1}")
            # Création de l'array contenant les paquets installés, au format JSON
            DEPENDENCIES_INSTALLED="\"dep_installed\":[$DEPENDENCIES_INSTALLED],"
        fi

        # Traitement de la liste des paquets mis à jour à cette date et heure
        if [ ! -z "$PACKAGES_UPGRADED_LIST" ];then
            for LINE in $(echo "$PACKAGES_UPGRADED_LIST");do
                # Dans le cas d'une mise à jour, le numéro de version installé se trouve sur la ligne en dessous du paquet mis à jour, ex :
                # netdata-1.29.3-1.el7.x86_64 @epel
                #         1.33.1-1.el7.x86_64 @epel
                # Du coup si la ligne en cours de traitement commence par un chiffre alors on ne la traite pas directement (il s'agit de la seconde ligne contenant la version)
                if echo "$LINE" | grep -q "^[0-9]";then
                    continue
                fi
                PACKAGE_NAME=$(echo "$LINE" | sed 's/-[0-9].*//g')
                # Pour rappel, le numéro de version installé se trouve sur la ligne qui suit le nom du paquet
                PACKAGE_VERSION=$(echo "$PACKAGES_UPGRADED_LIST" | sed  -n "/^${LINE}/{n;p}")
                PACKAGES_UPGRADED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
            done

            # Suppression de la dernière virgule :
            PACKAGES_UPGRADED=$(echo "${PACKAGES_UPGRADED::-1}")
            # Création de l'array contenant les paquets mis à jour, au format JSON
            PACKAGES_UPGRADED="\"upgraded\":[$PACKAGES_UPGRADED],"
        fi

        # Traitement de la liste des paquets supprimés à cette date et heure
        if [ ! -z "$PACKAGES_REMOVED_LIST" ];then
            for LINE in $(echo "$PACKAGES_REMOVED_LIST");do
                PACKAGE_NAME=$(echo "$LINE" | sed 's/-[0-9].*//g')
                PACKAGE_VERSION=$(echo "$LINE" | sed "s/$PACKAGE_NAME//g" | sed 's/^-//g')
                PACKAGES_REMOVED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
            done

            # Suppression de la dernière virgule :
            PACKAGES_REMOVED=$(echo "${PACKAGES_REMOVED::-1}")
            # Création de l'array contenant les paquets supprimés, au format JSON
            PACKAGES_REMOVED="\"removed\":[$PACKAGES_REMOVED],"
        fi

        # Traitement de la liste des paquets rétrogradés à cette date et heure
        if [ ! -z "$PACKAGES_DOWNGRADED_LIST" ];then
            for LINE in $(echo "$PACKAGES_DOWNGRADED_LIST");do
                PACKAGE_NAME=$(echo "$LINE" | sed 's/-[0-9].*//g')
                PACKAGE_VERSION=$(echo "$LINE" | sed "s/$PACKAGE_NAME//g" | sed 's/^-//g')
                PACKAGES_DOWNGRADED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
            done

            # Suppression de la dernière virgule :
            PACKAGES_DOWNGRADED=$(echo "${PACKAGES_DOWNGRADED::-1}")
            # Création de l'array contenant les paquets rétrogradés, au format JSON
            PACKAGES_DOWNGRADED="\"downgraded\":[$PACKAGES_DOWNGRADED],"
        fi

        # Traitement de la liste des paquets réinstallés à cette date et heure
        if [ ! -z "$PACKAGES_REINSTALLED_LIST" ];then
            for LINE in $(echo "$PACKAGES_REINSTALLED_LIST");do
                PACKAGE_NAME=$(echo "$LINE" | sed 's/-[0-9].*//g')
                PACKAGE_VERSION=$(echo "$LINE" | sed "s/$PACKAGE_NAME//g" | sed 's/^-//g')
                PACKAGES_REINSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
            done

            # Suppression de la dernière virgule :
            PACKAGES_REINSTALLED=$(echo "${PACKAGES_REINSTALLED::-1}")
            # Création de l'array contenant les paquets rétrogradés, au format JSON
            PACKAGES_REINSTALLED="\"reinstalled\":[$PACKAGES_REINSTALLED],"
        fi

        # Construction de l'évènement au format JSON :
        # D'abord on renseigne la date et l'heure de début / fin
        JSON="{\"date_start\":\"$DATE_START\",\"date_end\":\"$DATE_END\",\"time_start\":\"$TIME_START\",\"time_end\":\"$TIME_END\","

        # Puis on ajoute les paquets installés si il y en a eu
        if [ ! -z "$PACKAGES_INSTALLED" ];then
            JSON+="$PACKAGES_INSTALLED"
        fi

        # Puis on ajoute les dépendances installées si il y en a eu
        if [ ! -z "$DEPENDENCIES_INSTALLED" ];then
            JSON+="$DEPENDENCIES_INSTALLED"
        fi

        # Puis on ajoute les paquets mis à jour si il y en a eu
        if [ ! -z "$PACKAGES_UPGRADED" ];then
            JSON+="$PACKAGES_UPGRADED"
        fi
        # Puis on ajoute les paquets supprimés si il y en a eu
        if [ ! -z "$PACKAGES_REMOVED" ];then
            JSON+="$PACKAGES_REMOVED"
        fi
        # Puis on ajoute les paquets rétrogradés si il y en a eu
        if [ ! -z "$PACKAGES_DOWNGRADED" ];then
            JSON+="$PACKAGES_DOWNGRADED"
        fi
        # Puis on ajoute les paquets réinstallés si il y en a eu
        if [ ! -z "$PACKAGES_REINSTALLED" ];then
            JSON+="$PACKAGES_REINSTALLED"
        fi

        # Suppression de la dernière virgule après le dernier array ajouté ( ], <= ici)
        JSON=$(echo "${JSON::-1}")
        # Fermeture de l'évènement en cours avant de passer au suivant (début de la boucle FOR)
        JSON+="},"
        # On ajoute l'évènement en cours à la liste des tous les évènements, avant de passer au suivant
        EVENTS+="$JSON"

        (( HISTORY_LIMIT_COUNTER++ ))
    done
fi

# Cas Debian
if [ "$OS_FAMILY" == "Debian" ];then
    echo "Construction de l'historique des évènements apt..."

    # On va traiter tous les fichiers d'historique d'apt, même ceux compréssés
    for LOG in $(ls -t1 /var/log/apt/history.log* | tac);do
        IFS=$'\n'

        # On traite chaque évènement trouvé dans le fichier de LOG
        for START_DATE in $(zgrep "^Start-Date:*" "$LOG");do
            # On sort de la boucle si on a atteint la limite d'évènement à envoyer fixée par l'utilisateur
            if [ "$HISTORY_LIMIT_COUNTER" == "$SEND_FULL_HISTORY_LIMIT" ];then
                break
            fi
            # On passe à l'évènement suivant si l'évènement en cours doit être ignoré
            if [ ! -z "$IGNORE_EVENT" ] && [ "$IGNORE_EVENT" == "$START_DATE" ];then
                continue
            fi

            PACKAGES_INSTALLED_LIST=""
            PACKAGES_UPGRADED_LIST=""
            PACKAGES_REMOVED_LIST=""
            PACKAGES_PURGED_LIST=""
            PACKAGES_DOWNGRADED_LIST=""
            PACKAGES_REINSTALLED_LIST=""

            PACKAGES_INSTALLED=""
            PACKAGES_UPGRADED=""
            PACKAGES_REMOVED=""
            PACKAGES_PURGED=""
            PACKAGES_DOWNGRADED=""
            PACKAGES_REINSTALLED=""

            # Avant de commencer à parser, on vérifie qu'il n'y a pas eu plusieurs évènements exactement à la même date et à la même heure
            COUNT_EVENT=$(zgrep "$START_DATE" "$LOG" | wc -l)
            # Si il y a plusieurs évènements, on récupère leur contenu complet dans un fichier temporaire
            if [ "$COUNT_EVENT" -gt "1" ];then
                # echo "Plusieurs évènements pour : $START_DATE"
                # continue
                MULTIPLE_EVENTS_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_multiple_events_history.tmp"

                # Si le fichier de log est compréssé, on doit utiliser zcat pour le lire
                if echo "$LOG" | egrep -q ".gz";then
                    zcat "$LOG" | sed -n "/$START_DATE/,/^$/p" > "$MULTIPLE_EVENTS_TMP"
                # Si le fichier n'est pas compréssé on peut utiliser sed directement
                else
                    sed -n "/$START_DATE/,/^$/p" "$LOG" > "$MULTIPLE_EVENTS_TMP"
                fi

                # On traite tous les évènements à la même date avec la fonction suivante
                multiple_event_parser

                # Enfin comme on a traité plusieurs mêmes évènements du fichier de log, on ignore tous les prochaines évènements qui seraient à la même date (pour ne pas qu'ils soient traités deux fois)
                IGNORE_EVENT="$START_DATE"
            else
                event_parser
            fi

            # Traitement de la liste des paquets installés à cette date et heure
            if [ ! -z "$PACKAGES_INSTALLED_LIST" ];then
                for LINE in $(echo "$PACKAGES_INSTALLED_LIST");do

                    # Si plusieurs paquets sur la même ligne
                    if echo "$LINE" | grep -q "), ";then
                        LINE=$(echo "$LINE" | sed 's/), /\n/g')
                        for FORMATTED_LINE in $(echo "$LINE");do
                            PACKAGE_NAME=$(echo "$FORMATTED_LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                            PACKAGE_VERSION=$(echo "$FORMATTED_LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                            PACKAGES_INSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                        done
                    else
                        PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                        PACKAGE_VERSION=$(echo "$LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                        PACKAGES_INSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                    fi
                done

                # Suppression de la dernière virgule :
                PACKAGES_INSTALLED=$(echo "${PACKAGES_INSTALLED::-1}")

                # Création de l'array contenant les paquets installés, au format JSON
                PACKAGES_INSTALLED="\"installed\":[$PACKAGES_INSTALLED],"
            fi

            # Traitement de la liste des paquets mis à jour à cette date et heure
            if [ ! -z "$PACKAGES_UPGRADED_LIST" ];then
                for LINE in $(echo "$PACKAGES_UPGRADED_LIST");do

                    # Si plusieurs paquets sur la même ligne
                    if echo "$LINE" | grep -q "), ";then
                        LINE=$(echo "$LINE" | sed 's/), /\n/g')
                        for FORMATTED_LINE in $(echo "$LINE");do
                            PACKAGE_NAME=$(echo "$FORMATTED_LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                            PACKAGE_VERSION=$(echo "$FORMATTED_LINE" | awk '{print $3}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                            PACKAGES_UPGRADED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                        done
                    else
                        PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                        PACKAGE_VERSION=$(echo "$LINE" | awk '{print $3}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                        PACKAGES_UPGRADED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                    fi
                done

                # Suppression de la dernière virgule :
                PACKAGES_UPGRADED=$(echo "${PACKAGES_UPGRADED::-1}")

                # Création de l'array contenant les paquets mis à jour, au format JSON
                PACKAGES_UPGRADED="\"upgraded\":[$PACKAGES_UPGRADED],"
            fi

            # Traitement de la liste des paquets supprimés à cette date et heure
            if [ ! -z "$PACKAGES_REMOVED_LIST" ];then
                for LINE in $(echo "$PACKAGES_REMOVED_LIST");do

                    # Si plusieurs paquets sur la même ligne
                    if echo "$LINE" | grep -q "), ";then
                        LINE=$(echo "$LINE" | sed 's/), /\n/g')
                        for FORMATTED_LINE in $(echo "$LINE");do
                            PACKAGE_NAME=$(echo "$FORMATTED_LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                            PACKAGE_VERSION=$(echo "$FORMATTED_LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                            PACKAGES_REMOVED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                        done
                    else
                        PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                        PACKAGE_VERSION=$(echo "$LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                        PACKAGES_REMOVED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                    fi
                done

                # Suppression de la dernière virgule :
                PACKAGES_REMOVED=$(echo "${PACKAGES_REMOVED::-1}")

                # Création de l'array contenant les paquets supprimés, au format JSON
                PACKAGES_REMOVED="\"removed\":[$PACKAGES_REMOVED],"
            fi

            # Traitement de la liste des paquets purgés à cette date et heure
            if [ ! -z "$PACKAGES_PURGED_LIST" ];then
                for LINE in $(echo "$PACKAGES_PURGED_LIST");do

                    # Si plusieurs paquets sur la même ligne
                    if echo "$LINE" | grep -q "), ";then
                        LINE=$(echo "$LINE" | sed 's/), /\n/g')
                        for FORMATTED_LINE in $(echo "$LINE");do
                            PACKAGE_NAME=$(echo "$FORMATTED_LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                            PACKAGE_VERSION=$(echo "$FORMATTED_LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                            PACKAGES_PURGED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                        done
                    else
                        PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                        PACKAGE_VERSION=$(echo "$LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                        PACKAGES_PURGED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                    fi
                done

                # Suppression de la dernière virgule :
                PACKAGES_PURGED=$(echo "${PACKAGES_PURGED::-1}")

                # Création de l'array contenant les paquets purgés, au format JSON
                PACKAGES_PURGED="\"purged\":[$PACKAGES_PURGED],"
            fi

            # Traitement de la liste des paquets rétrogradés à cette date et heure
            if [ ! -z "$PACKAGES_DOWNGRADED_LIST" ];then
                for LINE in $(echo "$PACKAGES_DOWNGRADED_LIST");do

                    # Si plusieurs paquets sur la même ligne
                    if echo "$LINE" | grep -q "), ";then
                        LINE=$(echo "$LINE" | sed 's/), /\n/g')
                        for FORMATTED_LINE in $(echo "$LINE");do
                            PACKAGE_NAME=$(echo "$FORMATTED_LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                            PACKAGE_VERSION=$(echo "$FORMATTED_LINE" | awk '{print $3}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                            PACKAGES_DOWNGRADED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                        done
                    else
                        PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                        PACKAGE_VERSION=$(echo "$LINE" | awk '{print $3}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                        PACKAGES_DOWNGRADED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                    fi
                done

                # Suppression de la dernière virgule :
                PACKAGES_DOWNGRADED=$(echo "${PACKAGES_DOWNGRADED::-1}")

                # Création de l'array contenant les paquets rétrogradés, au format JSON
                PACKAGES_DOWNGRADED="\"downgraded\":[$PACKAGES_DOWNGRADED],"
            fi

            # Traitement de la liste des paquets réinstallés à cette date et heure
            if [ ! -z "$PACKAGES_REINSTALLED_LIST" ];then
                for LINE in $(echo "$PACKAGES_REINSTALLED_LIST");do

                    # Si plusieurs paquets sur la même ligne
                    if echo "$LINE" | grep -q "), ";then
                        LINE=$(echo "$LINE" | sed 's/), /\n/g')
                        for FORMATTED_LINE in $(echo "$LINE");do
                            PACKAGE_NAME=$(echo "$FORMATTED_LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                            PACKAGE_VERSION=$(echo "$FORMATTED_LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                            PACKAGES_REINSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                        done
                    else
                        PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
                        PACKAGE_VERSION=$(echo "$LINE" | awk '{print $2}' | sed 's/,//g' | sed 's/(//g' | sed 's/)//g' | sed 's/ //g')
                        PACKAGES_REINSTALLED+="{\"name\":\"${PACKAGE_NAME}\",\"version\":\"${PACKAGE_VERSION}\"},"
                    fi
                done

                # Suppression de la dernière virgule :
                PACKAGES_REINSTALLED=$(echo "${PACKAGES_REINSTALLED::-1}")

                # Création de l'array contenant les paquets réinstallés, au format JSON
                PACKAGES_REINSTALLED="\"reinstalled\":[$PACKAGES_REINSTALLED],"
            fi

            # Construction de l'évènement au format JSON :
            # D'abord on renseigne la date et l'heure de début / fin
            JSON="{\"date_start\":\"$DATE_START\",\"date_end\":\"$DATE_END\",\"time_start\":\"$TIME_START\",\"time_end\":\"$TIME_END\","

            # Puis on ajoute les paquets installés si il y en a eu
            if [ ! -z "$PACKAGES_INSTALLED" ];then
                JSON+="$PACKAGES_INSTALLED"
            fi
            # Puis on ajoute les paquets mis à jour si il y en a eu
            if [ ! -z "$PACKAGES_UPGRADED" ];then
                JSON+="$PACKAGES_UPGRADED"
            fi
            # Puis on ajoute les paquets supprimés si il y en a eu
            if [ ! -z "$PACKAGES_REMOVED" ];then
                JSON+="$PACKAGES_REMOVED"
            fi
            # Puis on ajoute les paquets purgés si il y en a eu
            if [ ! -z "$PACKAGES_PURGED" ];then
                JSON+="$PACKAGES_PURGED"
            fi
            # Puis on ajoute les paquets rétrogradés si il y en a eu
            if [ ! -z "$PACKAGES_DOWNGRADED" ];then
                JSON+="$PACKAGES_DOWNGRADED"
            fi
            # Puis on ajoute les paquets réinstallés si il y en a eu
            if [ ! -z "$PACKAGES_REINSTALLED" ];then
                JSON+="$PACKAGES_REINSTALLED"
            fi

            # Suppression de la dernière virgule après le dernier array ajouté ( ], <= ici)
            JSON=$(echo "${JSON::-1}")
            # Fermeture de l'évènement en cours avant de passer au suivant (début de la boucle FOR)
            JSON+="},"
            # On ajoute l'évènement en cours à la liste des tous les évènements, avant de passer au suivant
            EVENTS+="$JSON"

            (( HISTORY_LIMIT_COUNTER++ ))
        done
    done
fi

# Suppression de la dernière virgule après le dernier array de date ajouté (},<= ici)
EVENTS=$(echo "${EVENTS::-1}")

# Insertion de tous les évènements dans le fichier JSON prévu au début
sed -i "s/__INSERT_EVENTS__/$EVENTS/g" "$TMP_FILE"

# Mise en forme finale du JSON afin qu'il soit plus lisible si besoin de debug
jq . "$TMP_FILE" > "${TMP_FILE}.final"

IFS=$OLD_IFS

# Envoi des données :
echo -ne " Envoi de l'historique à ${YELLOW}${REPOSERVER_URL}${RESET} : "
CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d @${TMP_FILE}.final "${REPOSERVER_URL}/api/hosts" 2> /dev/null)

# Récupération et affichage des messages
curl_result_parse

if [ "$CURL_ERROR" -eq "0" ];then
    UPDATE_REQUEST_STATUS="done"
else 
    UPDATE_REQUEST_STATUS="error"
fi

update_request_status

rm "$TMP_FILE" -f
rm "${TMP_FILE}.final" -f


if [ "$UPDATE_REQUEST_STATUS" == "error" ];then
    return 1
fi

return 0
}