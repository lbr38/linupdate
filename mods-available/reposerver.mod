#!/bin/bash
# Module reposerver
# Module permettant de se ratacher à un serveur de repo exécutant repomanager 

# Fichier de configuration du module
MOD_CONF="${MODULES_CONF_DIR}/reposerver.conf"

#### FONCTIONS ####

# Enregistrement auprès d'un serveur Repomanager
function register {
	# Au préalable, récupération des informations concernant le serveur repomanager
	# Si la configuration est incomplète alors on quitte
	getModConf
	if [ -z "$REPOSERVER_URL" ];then
		echo -e " [$JAUNE ERREUR $RESET] Impossible de s'enregistrer auprès du serveur Repomanager. Vous devez configurer l'url du serveur."
		ERROR_STATUS=1
		clean_exit
	fi

	# On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
	testConn

	# Tentative d'enregistrement
	# Si l'enregistrement fonctionne, on récupère un id et un token
	echo -ne " Enregistrement auprès de ${JAUNE}${REPOSERVER_URL}${RESET} : "
	REGISTER_HOSTNAME=$(hostname -f)
	if [ -z "$REGISTER_HOSTNAME" ];then
		echo -e "[$JAUNE ERREUR $RESET] Impossible de déterminer le nom d'hôte de cette machine"
		ERROR_STATUS=1
		clean_exit
	fi
	# Si on n'a pas précisé d'adresse IP à enregistrer alors on tente de récupérer l'adresse IP publique de cette machine
	if [ -z "$REGISTER_IP" ];then
		REGISTER_IP=$(curl -s -4 ifconfig.co)
		if [ -z "$REGISTER_IP" ];then
			echo -e "[$JAUNE ERREUR $RESET] Impossible de déterminer l'adresse IP de cette machine"
			ERROR_STATUS=1
			clean_exit
		fi
	fi

	CURL=$(curl -s -q -H "Content-Type: application/json" -X POST -d "{\"ip\":\"$REGISTER_IP\",\"hostname\":\"$REGISTER_HOSTNAME\"}" "${REPOSERVER_URL}/api/hosts/add.php" 2> /dev/null)
	REGISTER_ID=$(jq -r '.id' <<< "$CURL")
	REGISTER_TOKEN=$(jq -r '.token' <<< "$CURL")
	REGISTER_RETURN=$(jq -r '.return' <<< "$CURL")
	REGISTER_MESSAGE=$(jq -r '.message' <<< "$CURL")

	# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
	if [ -z "$REGISTER_RETURN" ];then
		echo -e "[$JAUNE ERREUR $RESET] L'enregistrement a échoué, erreur inconnue."
		ERROR_STATUS=1
		clean_exit
	fi
	if [ "$REGISTER_RETURN" != "201" ];then
		echo -e "[$JAUNE ERREUR $RESET] $REGISTER_MESSAGE"
		ERROR_STATUS=1
		clean_exit
	fi

	# Si l'enregistrement a été effectué, on vérifie qu'on a bien pu récupérer un id
	if [ -z "$REGISTER_ID" ] || [ "$REGISTER_ID" == "null" ];then
		echo -e "[$JAUNE ERREUR $RESET] Impossible de récupérer un id suite à l'enregistrement."
		ERROR_STATUS=1
		clean_exit
	fi

	# Si l'enregistrement a été effectué, on vérifie qu'on a bien pu récupérer un token
	if [ -z "$REGISTER_TOKEN" ] || [ "$REGISTER_TOKEN" == "null" ];then
		echo -e "[$JAUNE ERREUR $RESET] Impossible de récupérer un token suite à l'enregistrement."
		ERROR_STATUS=1
		clean_exit
	fi

	# Enfin si tout s'est bien passé jusque là, on ajoute l'id et le token dans le fichier de conf et on affiche un message
	sed -i "s/ID.*/ID=\"$REGISTER_ID\"/g" $MOD_CONF
	sed -i "s/TOKEN.*/TOKEN=\"$REGISTER_TOKEN\"/g" $MOD_CONF
	echo -e "[$VERT OK $RESET]"	
	clean_exit
}

# Suppression de l'enregistrement auprès d'un serveur Repomanager
function unregister {
	# Au préalable, récupération des informations concernant le serveur repomanager
	# Si la configuration est incomplète alors on quitte
	getModConf
	if [ -z "$REPOSERVER_URL" ];then
		echo -e " [$JAUNE ERREUR $RESET] Impossible de supprimer l'enregistrement auprès du serveur Repomanager. Vous devez configurer l'url du serveur."
		ERROR_STATUS=1
		clean_exit
	fi

	# Si pas d'ID configuré alors on quitte
	if [ -z "$HOST_ID" ];then
		echo -e " [$JAUNE ERREUR $RESET] Aucun ID d'authentification n'est configuré sur cet hôte."
		ERROR_STATUS=1
		clean_exit
	fi

	# Si pas de token configuré alors on quitte
	if [ -z "$TOKEN" ];then
		echo -e " [$JAUNE ERREUR $RESET] Aucun token d'authentification n'est configuré sur cet hôte."
		ERROR_STATUS=1
		clean_exit
	fi

	# On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
	testConn

	# Tentative de suppression de l'enregistrement
	echo -ne " Suppression de l'enregistrement auprès de ${JAUNE}${REPOSERVER_URL}${RESET} : "
	CURL=$(curl -s -q -H "Content-Type: application/json" -X DELETE -d "{\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\"}" "${REPOSERVER_URL}/api/hosts/delete.php" 2> /dev/null)
	UNREGISTER_RETURN=$(jq -r '.return' <<< "$CURL")
	UNREGISTER_MESSAGE=$(jq -r '.message' <<< "$CURL")

	# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
	if [ -z "$UNREGISTER_RETURN" ];then
		echo -e "[$JAUNE ERREUR $RESET] La suppression a échouée, erreur inconnue."
		ERROR_STATUS=1
		clean_exit
	fi
	if [ "$UNREGISTER_RETURN" != "201" ];then
		echo -e "[$JAUNE ERREUR $RESET] $UNREGISTER_MESSAGE"
		ERROR_STATUS=1
		clean_exit
	fi

	echo -e "[$VERT OK $RESET]"
	clean_exit
}

function testConn {
	# On teste l'accès à l'url avec un curl pour vérifier que le serveur est joignable
	if ! curl -s -q -H "Content-Type: application/json" -X GET "${REPOSERVER_URL}/api/hosts/get.php" 2> /dev/null;then
		echo -e " [$JAUNE ERREUR $RESET] Impossible de joindre le serveur Repomanager à l'adresse $REPOSERVER_URL"
		ERROR_STATUS=1
		clean_exit
	fi
}

### MODULE ###

# Activation du module
function mod_enable {
	cd ${MODULES_ENABLED_DIR}/ &&
	ln -sfn "../mods-available/${MODULE}.mod" &&
	return 0
}

# Désactivation du module
function mod_disable {
	rm "${MODULES_ENABLED_DIR}/reposerver.mod" -f &&
	return 0
}

# Installation du module
function mod_install {
	# Copie du fichier de configuration
	mkdir -p "${MODULES_CONF_DIR}" &&
	\cp "${MODULES_DIR}/configurations/${MODULE}.conf" ${MODULES_CONF_DIR}/ &&
	
	# Activation du module
	mod_enable &&
	echo -e "Installation du module ${JAUNE}reposerver${RESET} : [$VERT OK $RESET]"
	
	# Configuration du module
	mod_configure
}

# Activation de l'agent reposerver
function enableReposerverAgent {
	cd ${AGENTS_ENABLED_DIR}/ &&
	ln -sfn "../mods-available/agent/reposerver.agent" &&
	echo -e "Agent ${JAUNE}reposerver${RESET} activé"
	return 0
}

# Désactivation de l'agent reposerver
function disableReposerverAgent {
	rm "${AGENTS_ENABLED_DIR}/reposerver.agent" -f &&
	echo -e "Agent ${JAUNE}reposerver${RESET} désactivé"
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
	SEND_AVAILABLE_PACKAGES_STATUS="no"
	SEND_INSTALLED_PACKAGE_STATUS="no"
	SEND_FULL_HISTORY="no"
	SEND_FULL_HISTORY_LIMIT=""

	# Récupération des paramètres passés à la fonction
	set +u
	while [ $# -ge 1 ];do
		case "$1" in
			--from-agent)
				FROM_AGENT="1"
			;;
			--url)
				REPOSERVER_URL="$2"
				shift
			;;
			--fail-level)
				FAILLEVEL="$2"
				shift
			;;
			--allow-conf-update)
				if [ "$2" == "yes" ];then REPOSERVER_ALLOW_CONFUPDATE="yes"; else REPOSERVER_ALLOW_CONFUPDATE="no";fi
				shift
			;;
			--allow-repos-update)
				if [ "$2" == "yes" ];then REPOSERVER_ALLOW_REPOSFILES_UPDATE="yes"; else REPOSERVER_ALLOW_REPOSFILES_UPDATE="no";fi
				shift
			;;
			--allow-overwrite)
				if [ "$2" == "yes" ];then REPOSERVER_ALLOW_OVERWRITE="yes"; else REPOSERVER_ALLOW_OVERWRITE="no";fi
				shift
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
				SEND_AVAILABLE_PACKAGES_STATUS="yes"
				SEND_INSTALLED_PACKAGE_STATUS="yes"
				SEND_FULL_HISTORY="yes"
				send_status
			;;
			--send-general-status)
				# Si on a précisé --generel alors on enverra seulement le status général du serveur (OS..)
				SEND_GENERAL_STATUS="yes"
				send_status
			;;
			--send-packages-status)
				# Si on a précisé --packages alors on enverra seulement le status des paquets
				SEND_AVAILABLE_PACKAGES_STATUS="yes"
				SEND_INSTALLED_PACKAGE_STATUS="yes"
				send_status
			;;
			--send-available-packages-status)
				SEND_AVAILABLE_PACKAGES_STATUS="yes"
				send_status
			;;
			--send-installed-packages-status)
				SEND_INSTALLED_PACKAGE_STATUS="yes"
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
		esac
		shift
	done
	set -u

	# Configuration du fichier /etc/linupdate/modules/reposerver.conf
	# Section [MODULE]
	if [ ! -z "$FAILLEVEL" ];then
		if ! grep -q "^FAILLEVEL" $MOD_CONF;then
			sed -i "/^\[MODULE\]/a FAILLEVEL=\"$FAILLEVEL\"" $MOD_CONF
		else
			sed -i "s/FAILLEVEL.*/FAILLEVEL=\"$FAILLEVEL\"/g" $MOD_CONF
		fi
	fi

	# Section [CLIENT]
	if [ ! -z "$REPOSERVER_ALLOW_CONFUPDATE" ];then
		if ! grep -q "^REPOSERVER_ALLOW_CONFUPDATE" $MOD_CONF;then
			sed -i "/^\[CLIENT\]/a REPOSERVER_ALLOW_CONFUPDATE=\"$REPOSERVER_ALLOW_CONFUPDATE\"" $MOD_CONF
		else
			sed -i "s/REPOSERVER_ALLOW_CONFUPDATE.*/REPOSERVER_ALLOW_CONFUPDATE=\"$REPOSERVER_ALLOW_CONFUPDATE\"/g" $MOD_CONF
		fi
	fi

	if [ ! -z "$REPOSERVER_ALLOW_REPOSFILES_UPDATE" ];then
		if ! grep -q "^REPOSERVER_ALLOW_REPOSFILES_UPDATE" $MOD_CONF;then
			sed -i "/^\[CLIENT\]/a REPOSERVER_ALLOW_REPOSFILES_UPDATE=\"$REPOSERVER_ALLOW_REPOSFILES_UPDATE\"" $MOD_CONF
		else 
			sed -i "s/REPOSERVER_ALLOW_REPOSFILES_UPDATE.*/REPOSERVER_ALLOW_REPOSFILES_UPDATE=\"$REPOSERVER_ALLOW_REPOSFILES_UPDATE\"/g" $MOD_CONF
		fi
	fi

	if [ ! -z "$REPOSERVER_ALLOW_OVERWRITE" ];then
		if ! grep -q "^REPOSERVER_ALLOW_OVERWRITE" $MOD_CONF;then
			sed -i "/^\[CLIENT\]/a REPOSERVER_ALLOW_OVERWRITE=\"$REPOSERVER_ALLOW_OVERWRITE\"" $MOD_CONF
		else 
			sed -i "s/REPOSERVER_ALLOW_OVERWRITE.*/REPOSERVER_ALLOW_OVERWRITE=\"$REPOSERVER_ALLOW_OVERWRITE\"/g" $MOD_CONF
		fi
	fi

	# Section [REPOSERVER]
	if [ ! -z "$REPOSERVER_URL" ];then
		if ! grep -q "^URL" $MOD_CONF;then
			sed -i "/^\[REPOSERVER\]/a URL=\"$REPOSERVER_URL\"" $MOD_CONF
		else
			sed -i "s|URL.*|URL=\"$REPOSERVER_URL\"|g" $MOD_CONF
		fi
	fi
}

# La fonction mod_load() permet de s'assurer que le module est un minimum configuré avant qu'il soit intégré à l'exécution du programme principal
# Retourner 1 si des éléments sont manquants
# Retourner 0 si tout est OK
function mod_load {
	echo -e "  - ${JAUNE}reposerver${RESET}"

	# Si le fichier de configuration du module est introuvable alors on ne charge pas le module
	if [ ! -f "$MOD_CONF" ] || [ ! -s "$MOD_CONF" ];then
		echo -e "    [$JAUNE WARNING $RESET] Le fichier de configuration du module est introuvable. Ce module ne peut pas être chargé."
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

	# Remplacement du fichier de conf par le fichier précédemment construit
	rm -f "$MOD_CONF"
	\cp "$TMP_MOD_CONF" "$MOD_CONF"
	rm -f "$TMP_MOD_CONF"

	# Si l'URL du serveur de repo n'est pas renseignée alors on ne charge pas le module
	if [ -z $(grep "^URL=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g') ];then
		echo -e "     [$JAUNE WARNING $RESET] L'URL du serveur ${JAUNE}reposerver${RESET} n'est pas renseignée. Ce module ne peut pas être chargé."
		return 1
	fi

	LOADED_MODULES+=("reposerver")
	echo -e "  - Module reposerver : ${JAUNE}Activé${RESET}"

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
	REPOSERVER_PROFILES_URL="$(grep "^PROFILES_URL=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_OS_FAMILY="$(grep "^OS_FAMILY=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_OS_NAME="$(grep "^OS_NAME=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_OS_ID="$(grep "^OS_ID=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_OS_VERSION="$(grep "^OS_VERSION=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_PACKAGES_OS_VERSION="$(grep "^PACKAGES_OS_VERSION=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_MANAGE_CLIENTS_CONF="$(grep "^MANAGE_CLIENTS_CONF=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"
	REPOSERVER_MANAGE_CLIENTS_REPOSCONF="$(grep "^MANAGE_CLIENTS_REPOSCONF=" $MOD_CONF | cut -d'=' -f2 | sed 's/"//g')"

	# Récupération du FAILLEVEL pour ce module
	FAILLEVEL=$(grep "^FAILLEVEL=" "$MOD_CONF" | cut -d'=' -f2 | sed 's/"//g')

	# Si on n'a pas pu récupérer le FAILLEVEL dans le fichier de conf alors on le set à 1 par défaut
	# De même si le FAILLEVEL récupéré n'est pas un chiffre alors on le set à 1
	if [ -z "$FAILLEVEL" ];then echo -e "[$JAUNE WARNING $RESET] Paramètre FAILLEVEL non configuré pour ce module → configuré à 1 (arrêt en cas d'erreur mineure ou critique)"; FAILLEVEL="1";fi
	if ! [[ "$FAILLEVEL" =~ ^[0-9]+$ ]];then echo -e "[$JAUNE WARNING $RESET] Paramètre FAILLEVEL non configuré pour ce module → configuré à 1 (arrêt en cas d'erreur mineure ou critique)"; FAILLEVEL="1";fi

	if [ -z "$REPOSERVER_URL" ];then
		echo -e " - Module reposerver : [${JAUNE} ERREUR ${RESET}] URL du serveur de repo inconnue ou vide"
		return 2
	fi

	# Si REPOSERVER_PACKAGES_OS_VERSION n'est pas vide, cela signifie que le serveur distant dispose de miroirs de paquets dont la version est différente de sa propre version
	# Dans ce cas on overwrite la variable REPOSERVER_OS_VERSION
	if [ ! -z "$REPOSERVER_PACKAGES_OS_VERSION" ];then REPOSERVER_OS_VERSION="$REPOSERVER_PACKAGES_OS_VERSION";fi

	return 0
}

function updateModConf {
	# On re-télécharge la conf complète du serveur de repo afin de la mettre à jour dans le fichier de conf
	GET_CONF=$(curl -s "${REPOSERVER_URL}/main.conf")
	if [ -z "$GET_CONF" ];then
		echo -e " [${JAUNE} ERREUR ${RESET}] La configuration du serveur de repo récupérée est vide"
		return 2
	fi

	TMP_FILE="/tmp/.linupdate_${PROCID}_mod_reposerver.tmp"

	# On recrée le fichier de conf
	# Sauvegarde de la partie [MODULE]
	sed -n -e '/\[MODULE\]/,/^$/p' "$MOD_CONF" > "$TMP_FILE"
	
	# Sauvegarde de la partie [CLIENT]
	sed -n -e '/\[CLIENT\]/,/^$/p' "$MOD_CONF" >> "$TMP_FILE"

	# Ajout de la nouvelle conf [REPOSERVER]
	echo -e "$GET_CONF" >> "$TMP_FILE"

	# On remplace alors le fichier de conf actuel par le nouveau
	cat "$TMP_FILE" > "$MOD_CONF"

	# Puis on recharge à nouveau les paramètres
	getModConf
}


function preCheck {
	# Si l'url d'accès aux profils est inconnue alors on ne peut pas continuer
	if [ -z "$REPOSERVER_PROFILES_URL" ];then
		echo -e "   [${JAUNE} ERREUR ${RESET}] L'URL d'accès aux profils est inconnue."
		return 1
	fi

	# Si REPOSERVER_OS_FAMILY, *NAME ou *VERSION diffère du type de serveur sur lequel est exécuté ce module (par exemple le serveur reposerver est un serveur CentOS et nous somme sur un serveur Debian), alors on affiche un warning
	if [ "$REPOSERVER_OS_FAMILY" != "$OS_FAMILY" ];then
		echo -e "   [${JAUNE} ERREUR ${RESET}] Le serveur de repo distant ne gère pas la même famille d'OS que cette machine."
		return 2
	fi

	if [ "$REPOSERVER_OS_ID" != "$OS_NAME" ];then
		echo -e "   [${JAUNE} WARNING ${RESET}] Le serveur de repo distant ne gère pas le même OS que cette machine, les paquets peuvent être incompatibles."
		return 1
	fi

	if [ "$REPOSERVER_OS_VERSION" != "$OS_VERSION" ];then
		echo -e "   [${JAUNE} ERREUR ${RESET}] Le serveur de repo distant ne gère pas la même version d'OS que cette machine."
		return 2
	fi
}


function updateConfFile {
	# Si le serveur reposerver ne gère pas les profils ou que le client refuse d'être mis à jour par son serveur de repo, on quitte la fonction
	echo -ne "  → Mise à jour de la configuration du profil $SERVER_PROFILE : "

	if [ "$REPOSERVER_MANAGE_CLIENTS_CONF" == "no" ] || [ "$REPOSERVER_ALLOW_CONFUPDATE" == "no" ];then
		if [ "$REPOSERVER_MANAGE_CLIENTS_CONF" == "no" ];then
			echo -e "${JAUNE}Désactivé (non pris en charge par le serveur Repomanager)${RESET}"
		fi
		if [ "$REPOSERVER_ALLOW_CONFUPDATE" == "no" ];then
			echo -e "${JAUNE}Désactivé${RESET}"
		fi

		return 1
	fi

	echo -e "${JAUNE}Activé${RESET}"

	# Sinon, on récupère la conf auprès du serveur de repo, PROFILE étant le nom de profil
	# 1er test pour voir la conf est récupérable (et qu'on ne choppe pas une 404 ou autre erreur)
	if ! curl -s -f -o /dev/null "${REPOSERVER_PROFILES_URL}/${SERVER_PROFILE}/config";then
		echo -e "   [$JAUNE ERREUR $RESET] pendant la récupération de la configuration du profil ${JAUNE}${SERVER_PROFILE}${RESET} depuis ${JAUNE}${REPOSERVER_PROFILES_URL}${RESET}"
		return 2
	fi

	# 2ème fois : cette fois on récupère la conf
	GET_CONF=$(curl -s "${REPOSERVER_PROFILES_URL}/${SERVER_PROFILE}/config")
	if [ -z "$GET_CONF" ];then
		echo -e "   [$JAUNE ERREUR $RESET] pendant la récupération de la configuration du profil ${JAUNE}${SERVER_PROFILE}${RESET} depuis ${JAUNE}${REPOSERVER_PROFILES_URL}${RESET}"
		return 2
	fi

	# On applique le nouveau fichier de conf téléchargé
	# D'abord on nettoie la partie [SOFT] du fichier de conf car c'est cette partie qui va être remplacée par la nouvelle conf : 
	sed -i '/^\[SOFTWARE CONFIGURATION\]/,$d' "$CONF" &&

	# Puis on réinjecte avec la nouvelle conf téléchargée :
	echo -e "[SOFTWARE CONFIGURATION]\n${GET_CONF}" >> "$CONF"

	# Enfin on applique la nouvelle conf en récupérant de nouveau les paramètres du fichier de conf :
	getConf
}


function updateReposConfFiles { # Mets à jour les fichiers de conf .repo en allant les récupérer sur le serveur de repo
	# Si on est autorisé à mettre à jour les fichiers de conf de repos et si le serveur de repos le gère
	echo -ne "  → Mise à jour de la configuration des repos : "

	if [ "$REPOSERVER_MANAGE_CLIENTS_REPOSCONF" == "yes" ] && [ "$REPOSERVER_ALLOW_REPOSFILES_UPDATE" == "yes" ];then
		# Création d'un répertoire temporaire pour télécharger les fichiers .repo
		rm -rf /tmp/linupdate/reposconf/ &&
		mkdir -p /tmp/linupdate/reposconf/ && 
		cd /tmp/linupdate/reposconf/ &&

		# Récupération des fichiers depuis le serveur de repo
		if [ "$OS_FAMILY" == "Redhat" ];then
			wget -q -r -np -nH --cut-dirs=3 -A "*.repo" "${REPOSERVER_PROFILES_URL}/${SERVER_PROFILE}/"
			RESULT=$?
		fi

		if [ "$OS_FAMILY" == "Debian" ];then
			wget -q -r -np -nH --cut-dirs=3 -A "*.list" "${REPOSERVER_PROFILES_URL}/${SERVER_PROFILE}/"
			RESULT=$?
		fi

		if [ "$RESULT" -ne "0" ];then
			if [ "$OS_FAMILY" == "Redhat" ];then echo -e "[$JAUNE ERREUR $RESET] lors du téléchargement des fichiers de conf .repo depuis ${REPOSERVER_URL}";fi
			if [ "$OS_FAMILY" == "Debian" ];then echo -e "[$JAUNE ERREUR $RESET] lors du téléchargement des fichiers de conf .list depuis ${REPOSERVER_URL}";fi
			return 2
		fi

		if [ "$OS_FAMILY" == "Redhat" ];then
			# On remplace dedans les occurences __ENV__ par $SERVER_ENV
			sed -i "s|__ENV__|${SERVER_ENV}|g" *.repo &&
			# On crée le répertoire servant à backuper les anciens fichiers .repo
			cd /etc/yum.repos.d/ &&
			mkdir -p backups/ &&
			# Puis on crée un backup archive à la date du jour
			tar czf backup_yum.repos.d_${DATE_AMJ}.tar.gz *.repo &&
			# Qu'on déplace ensuite dans le dossier backups
			mv backup_yum.repos.d_${DATE_AMJ}.tar.gz backups/ &&
			# Suppression des fichiers .repo actuels, qui vont être remplacés par les nouveaux
			rm /etc/yum.repos.d/*.repo -f &&
			# Déplacement des nouveaux fichiers de conf dans /etc/yum.repos.d/
			mv /tmp/linupdate/reposconf/*.repo /etc/yum.repos.d/ &&
			# Application des droits sur les nouveaux fichiers .repo
			chown root:root /etc/yum.repos.d/*.repo && chmod 660 /etc/yum.repos.d/*.repo &&
			# Vidage du cache yum
			yum clean all -q && 
			echo -e "[$VERT OK $RESET]"
		fi

		if [ "$OS_FAMILY" == "Debian" ];then
			# On remplace dedans les occurences __ENV__ par $SERVER_ENV
			sed -i "s|__ENV__|${SERVER_ENV}|g" *.list &&
			# On crée le répertoire servant à backuper les anciens fichiers .list
			cd /etc/apt/sources.list.d/ &&
			mkdir -p backups/ &&
			# Puis on crée un backup archive à la date du jour
			tar czf backup_apt.sourceslist.d_${DATE_AMJ}.tar.gz *.list &&
			# Qu'on déplace ensuite dans le dossier backups
			mv backup_apt.sourceslist.d_${DATE_AMJ}.tar.gz backups/ &&
			# Suppression des fichiers .list actuels, qui vont être remplacés par les nouveaux
			rm /etc/apt/sources.list.d/*.list -f &&
			# Déplacement des nouveaux fichiers de conf dans /etc/apt/sources.list.d/
			mv /tmp/linupdate/reposconf/*.list /etc/apt/sources.list.d/ &&
			# Application des droits sur les nouveaux fichiers .list
			chown root:root /etc/apt/sources.list.d/*.list && chmod 660 /etc/apt/sources.list.d/*.list &&
			# Vidage du cache apt
			apt-get clean && 
			echo -e "[$VERT OK $RESET]"
		fi
	else
		if [ "$REPOSERVER_MANAGE_CLIENTS_REPOSCONF" != "yes" ];then
			echo -e "${JAUNE}Désactivé (non pris en charge par le serveur Repomanager)${RESET}"
			return 1
		fi

		if [ "$REPOSERVER_ALLOW_REPOSFILES_UPDATE" != "yes" ];then
			echo -e "${JAUNE}Désactivé${RESET}"
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
	# Aucune erreur : 	return 0
	# Erreur mineure :  return 1
	# Erreur critique : return 2

	echo -e " Exécution du module ${JAUNE}reposerver${RESET}"

	# On récupère la configuration du module, en l'occurence la configuration du serveur de repo
	getModConf
	RESULT="$?"
	if [ "$FAILLEVEL" -le "2" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi 	# Si FAILLEVEL = 1 ou 2
	if [ "$FAILLEVEL" -eq "3" ] && [ "$RESULT" -gt "0" ];then return 1;fi 	 					# Si FAILLEVEL = 3 et qu'il y a une erreur au chargement de la conf du module alors on quitte le module sans pour autant quitter repomanager (clean_exit)

	# On met à jour la configuration du serveur de repo distant en lui demandant de renvoyer sa conf
	updateModConf
	RESULT="$?"
	if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
	if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi
	if [ "$FAILLEVEL" -eq "3" ] && [ "$RESULT" -gt "0" ];then return 1;fi 						# Si FAILLEVEL = 3 et qu'il y a une erreur au chargement de la conf du module alors on quitte le module sans pour autant quitter repomanager (clean_exit)

	# On vérifie que la configuration du serveur de repo est compatible avec notre OS
	preCheck
	RESULT="$?"
	if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
	if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

	# On met à jour notre configuration à partir du serveur de repo (profils), si cela est autorisé des deux côtés
	updateConfFile
	RESULT="$?"
	if [ "$FAILLEVEL" -eq "1" ] && [ "$RESULT" -gt "0" ];then (( MOD_ERROR++ )); clean_exit;fi
	if [ "$FAILLEVEL" -eq "2" ] && [ "$RESULT" -ge "2" ];then (( MOD_ERROR++ )); clean_exit;fi

	# On met à jour notre configuration des repos à partir du serveurs de repo (profils), si cela est autorisé des deux côtés
	updateReposConfFiles
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
	UPDATE_REQUEST_STATUS="done"
	update_request_status

	# On renvoie les 2 derniers historique d'évènements au serveur reposerver
	/opt/linupdate/linupdate --mod-configure reposerver --from-agent --send-full-history 2
	/opt/linupdate/linupdate --mod-configure reposerver --from-agent --send-available-packages-status

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
	testConn

	# Envoi du récapitulatif de toutes les mises à jour effectuées à partir du fichier historique

	# Si on n'a pas d'ID ou de token alors on ne peut pas effectuer cette opération
	if [ -z "$HOST_ID" ];then
		echo -e "[$JAUNE ERREUR $RESET] L'ID de cette machine est manquant"
		ERROR_STATUS=1
		clean_exit
	fi
	if [ -z "$TOKEN" ];then
		echo -e "[$JAUNE ERREUR $RESET] Le token de cette machine est manquant"
		ERROR_STATUS=1
		clean_exit
	fi

	# Exécution des sous-fonctions

	# Général
	if [ "$SEND_GENERAL_STATUS" == "yes" ];then
		send_general_status
	fi

	# Paquets disponibles sur cet hôte
	if [ "$SEND_AVAILABLE_PACKAGES_STATUS" == "yes" ];then
		send_available_packages_status
	fi

	# Paquets installés sur cet hôte
	if [ "$SEND_INSTALLED_PACKAGE_STATUS" == "yes" ];then
		send_installed_packages_status
	fi

	# Historique des évènements apt ou yum
	if [ "$SEND_FULL_HISTORY" == "yes" ];then  
		genFullHistory
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

	CURL_PARAMS="\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\", \"set_update_request_type\":\"$UPDATE_REQUEST_TYPE\", \"set_update_request_status\":\"$UPDATE_REQUEST_STATUS\""

	CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts/update.php" 2> /dev/null)
	UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")

	# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
	if [ -z "$UPDATE_RETURN" ];then
		echo -e "[$JAUNE ERREUR $RESET] L'envoi des mises à jour a échouée, erreur inconnue."
		ERROR_STATUS=1
		return
	fi

	# Récupération et affichage des messages

	# Si il y a eu des messages d'erreur on les affiche
	if echo "$CURL" | grep -q "message_error";then
		UPDATE_MESSAGE_ERROR=($(jq -r '.message_error[]' <<< "$CURL")) # array

		# $UPDATE_MESSAGE_ERROR est un array pouvant contenir plusieurs messages d'erreurs
		for MESSAGE in "${UPDATE_MESSAGE_ERROR[@]}"; do
			echo -e "[$JAUNE ERREUR $RESET] $MESSAGE"
		done
		ERROR_STATUS=1
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
		CURL_PARAMS+=", \"os\":\"$OS_NAME\", \"os_version\":\"$OS_VERSION\""
	fi
	if [ ! -z "$SERVER_PROFILE" ];then
		CURL_PARAMS+=", \"profile\":\"$SERVER_PROFILE\""
	fi
	if [ ! -z "$SERVER_ENV" ];then
		CURL_PARAMS+=", \"env\":\"$SERVER_ENV\""
	fi

	# Fin de construction des paramètres curl puis envoi.

	# Envoi des données :
	echo -e " Envoi du status à ${JAUNE}${REPOSERVER_URL}${RESET} : "
	CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts/update.php" 2> /dev/null)
	UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")

	# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
	if [ -z "$UPDATE_RETURN" ];then
		echo -e "[$JAUNE ERREUR $RESET] L'envoi des mises à jour a échouée, erreur inconnue."
		ERROR_STATUS=1
		return
	fi

	# Récupération et affichage des messages

	# Si il y a eu des messages d'erreur on les affiche
	if echo "$CURL" | grep -q "message_error";then
		UPDATE_MESSAGE_ERROR=($(jq -r '.message_error[]' <<< "$CURL")) # array

		# $UPDATE_MESSAGE_ERROR est un array pouvant contenir plusieurs messages d'erreurs
		for MESSAGE in "${UPDATE_MESSAGE_ERROR[@]}"; do
			echo -e "[$JAUNE ERREUR $RESET] $MESSAGE"
		done
		ERROR_STATUS=1

		UPDATE_REQUEST_STATUS="error"
	fi

	# Si il y a eu des message de succès on les affiche
	if echo "$CURL" | grep -q "message_success";then
		UPDATE_MESSAGE_SUCCESS=($(jq -r '.message_success[]' <<< "$CURL")) # array

		# $UPDATE_MESSAGE_SUCCESS est un array pouvant contenir plusieurs messages d'erreurs
		for MESSAGE in "${UPDATE_MESSAGE_SUCCESS[@]}"; do
			echo -e "[$VERT OK $RESET] $MESSAGE"
		done

		UPDATE_REQUEST_STATUS="done"
	fi

	update_request_status
}

# Envoi au serveur Repomanager de la liste des paquets installés sur l'hôte
function send_installed_packages_status {
	INSTALLED_PACKAGES=""
	UPDATE_MESSAGE_SUCCESS=""
	UPDATE_MESSAGE_ERROR=""

	UPDATE_REQUEST_TYPE="installed-packages-status-update"
	UPDATE_REQUEST_STATUS="running"
	update_request_status

	# Paramètres concernant les paquets installés sur le système (tous les paquets)
	echo "Construction de la liste des paquets installés sur le système..."

	INSTALLED_PACKAGES_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_installed_pkgs.tmp"

	# Construction de la liste des paquets
	# Cas Redhat
	if [ "$OS_FAMILY" == "Redhat" ];then
		repoquery -a --installed --qf="%{name} %{version}-%{release}.%{arch}" > "$INSTALLED_PACKAGES_TMP"
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
		fi
		if [ "$OS_FAMILY" == "Debian" ];then
			PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}' | sed 's/:amd64//g' | sed 's/:i386//g' | sed 's/:armhf//g')
			PACKAGE_ACT_VERSION=$(echo "$LINE" | awk '{print $2}' | sed 's/"//g' | sed "s/'//g")
			# awk récupère de la 5ème à la dernière colonne pour obtenir la description entière :
			# Description désactivée car provoque des pb à l'import en BDD
			#PACKAGE_DESCRIPTION=$(echo "$LINE" | awk '{for(i=5;i<=NF;++i)printf $i""FS ; print ""}' | sed 's/"//g' | sed "s/'//g" | sed "s/|//g" | sed "s/,//g") 
		fi

		# Si le nom du paquet est vide, on passe au suivant
		if [ -z "$PACKAGE_NAME" ];then continue;fi
				
		# Ajout du nom du paquet, sa version actuelle et sa version disponible à l'array $INSTALLED_PACKAGES
		#INSTALLED_PACKAGES+="${PACKAGE_NAME}|${PACKAGE_ACT_VERSION}|${PACKAGE_DESCRIPTION}, "
		INSTALLED_PACKAGES+="${PACKAGE_NAME}|${PACKAGE_ACT_VERSION},"
	done

	# Suppression de la dernière virgule :
	INSTALLED_PACKAGES=$(echo "${INSTALLED_PACKAGES::-1}")
	
	# Construction des paramètres curl à envoyer
	CURL_PARAMS="$CURL_PARAMS, \"packages_installed\":\"$INSTALLED_PACKAGES\""

	# Envoi des données :
	echo -ne " Envoi des informations à ${JAUNE}${REPOSERVER_URL}${RESET} : "
	CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts/update.php" 2> /dev/null)
	UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")

	# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
	if [ -z "$UPDATE_RETURN" ];then
		echo -e "[$JAUNE ERREUR $RESET] L'envoi des mises à jour a échouée, erreur inconnue."
		ERROR_STATUS=1

		UPDATE_REQUEST_STATUS="error"
	fi

	# Récupération et affichage des messages

	# Si il y a eu des messages d'erreur on les affiche
	if echo "$CURL" | grep -q "message_error";then
		UPDATE_MESSAGE_ERROR=($(jq -r '.message_error[]' <<< "$CURL")) # array

		# $UPDATE_MESSAGE_ERROR est un array pouvant contenir plusieurs messages d'erreurs
		for MESSAGE in "${UPDATE_MESSAGE_ERROR[@]}"; do
			echo -e "[$JAUNE ERREUR $RESET] $MESSAGE"
		done
		ERROR_STATUS=1

		UPDATE_REQUEST_STATUS="error"
	fi

	# Si il y a eu des message de succès on les affiche
	if echo "$CURL" | grep -q "message_success";then
		UPDATE_MESSAGE_SUCCESS=($(jq -r '.message_success[]' <<< "$CURL")) # array

		# $UPDATE_MESSAGE_SUCCESS est un array pouvant contenir plusieurs messages d'erreurs
		for MESSAGE in "${UPDATE_MESSAGE_SUCCESS[@]}"; do
			echo -e "[$VERT OK $RESET] $MESSAGE"
		done

		UPDATE_REQUEST_STATUS="done"
	fi

	rm "$INSTALLED_PACKAGES_TMP" -f

	update_request_status
}

# Envoi au serveur Repomanager de la liste des paquets disponibles pour mettre à jour
function send_available_packages_status {
	AVAILABLE_PACKAGES=""

	UPDATE_REQUEST_TYPE="available-packages-status-update"
	UPDATE_REQUEST_STATUS="running"
	update_request_status

	# Paramètres d'authentification (id et token)
	CURL_PARAMS="\"id\":\"$HOST_ID\", \"token\":\"$TOKEN\""

	# Paramètres concernant les paquets (paquets disponibles...)

	echo "Construction de la liste des paquets disponibles..."

	# Récupération des paquets disponibles
	AVAILABLE_PACKAGES_TMP="/tmp/.linupdate_${PROCID}_mod_reposerver_available_pkgs.tmp"

	# Cas Redhat
	if [ "$OS_FAMILY" == "Redhat" ];then
		# Récupération des paquets disponibles pour mise à jour
		repoquery -q -a --qf="%{name} %{version}-%{release}.%{arch} %{repoid}" --pkgnarrow=updates > "$AVAILABLE_PACKAGES_TMP"
	fi
	# Cas Debian
	if [ "$OS_FAMILY" == "Debian" ];then
		# Récupération des paquets disponibles pour mise à jour
		#apt-get --just-print dist-upgrade | grep "^Inst " | awk '{print $2, $3, $4}' > "$AVAILABLE_PACKAGES_TMP"
		aptitude -F"%p %v %V" --disable-columns search ~U > "$AVAILABLE_PACKAGES_TMP"
	fi
	
	# Si le fichier généré est vide, alors il n'y a aucun paquet à mettre à jour, on n'envoit rien à Repomanager
	if [ ! -s "$AVAILABLE_PACKAGES_TMP" ];then
		echo -e "[$JAUNE OK $RESET] Il n'y aucun paquet à mettre à jour. Rien n'a été transmis à ${JAUNE}${REPOSERVER_URL}${RESET}"

		UPDATE_REQUEST_STATUS="done"
	else
		# Sinon on parcourt toutes les lignes du fichiers pour lister les paquets disponibles
		for LINE in $(cat "$AVAILABLE_PACKAGES_TMP");do
			if [ "$OS_FAMILY" == "Redhat" ];then
				PACKAGE_NAME=$(echo "$LINE" | awk '{print $1}')
				PACKAGE_AVL_VERSION=$(echo "$LINE" | awk '{print $2}')
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
	
		# Construction des paramètres curl à envoyer
		CURL_PARAMS="$CURL_PARAMS, \"available_packages\":\"$AVAILABLE_PACKAGES\""

		# Envoi des données :
		echo -ne " Envoi du status à ${JAUNE}${REPOSERVER_URL}${RESET} : "
		CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d "{$CURL_PARAMS}" "${REPOSERVER_URL}/api/hosts/update.php" 2> /dev/null)
		UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")

		# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
		if [ -z "$UPDATE_RETURN" ];then
			echo -e "[$JAUNE ERREUR $RESET] L'envoi des mises à jour a échouée, erreur inconnue."
			ERROR_STATUS=1
			UPDATE_REQUEST_STATUS="error"
		fi

		# Récupération et affichage des messages

		# Si il y a eu des messages d'erreur on les affiche
		if echo "$CURL" | grep -q "message_error";then
			UPDATE_MESSAGE_ERROR=($(jq -r '.message_error[]' <<< "$CURL")) # array

			# $UPDATE_MESSAGE_ERROR est un array pouvant contenir plusieurs messages d'erreurs
			for MESSAGE in "${UPDATE_MESSAGE_ERROR[@]}"; do
				echo -e "[$JAUNE ERREUR $RESET] $MESSAGE"
			done
			ERROR_STATUS=1
			UPDATE_REQUEST_STATUS="error"
		fi

		# Si il y a eu des message de succès on les affiche
		if echo "$CURL" | grep -q "message_success";then
			UPDATE_MESSAGE_SUCCESS=($(jq -r '.message_success[]' <<< "$CURL")) # array

			# $UPDATE_MESSAGE_SUCCESS est un array pouvant contenir plusieurs messages d'erreurs
			for MESSAGE in "${UPDATE_MESSAGE_SUCCESS[@]}"; do
				echo -e "[$VERT OK $RESET] $MESSAGE"
			done
			UPDATE_REQUEST_STATUS="done"
		fi
	fi

	rm "$AVAILABLE_PACKAGES_TMP" -f

	update_request_status
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
		PACKAGES_INSTALLED_LIST=$(cat "$TMP_EVENT_FILE" | grep "Install " | grep -Ev "Dep-Install|Installed|Installing" | awk '{print $2}')
		DEPENDENCIES_INSTALLED_LIST=$(cat "$TMP_EVENT_FILE" | grep "Dep-Install " | grep -Ev "Installed|Installing" | awk '{print $2}')
		PACKAGES_UPGRADED_LIST=$(cat "$TMP_EVENT_FILE" | egrep "Updated |Update " | grep -v "Installing" | awk '{print $2}')
		PACKAGES_REMOVED_LIST=$(cat "$TMP_EVENT_FILE" | grep "Erase " | awk '{print $2}')
		PACKAGES_DOWNGRADED_LIST=$(cat "$TMP_EVENT_FILE" | grep "Downgrade " | awk '{print $2}')
		PACKAGES_REINSTALLED_LIST=$(cat "$TMP_EVENT_FILE" | grep "Reinstall " | awk '{print $2}')
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
		PACKAGES_UPGRADED_LIST=""
		PACKAGES_REMOVED_LIST=""
		PACKAGES_DOWNGRADED_LIST=""
		PACKAGES_REINSTALLED_LIST=""

		PACKAGES_INSTALLED=""
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

# Envoi des données :
echo -ne " Envoi de l'historique à ${JAUNE}${REPOSERVER_URL}${RESET} : "
CURL=$(curl -s -q -H "Content-Type: application/json" -X PUT -d @${TMP_FILE} "${REPOSERVER_URL}/api/hosts/update.php" 2> /dev/null)
UPDATE_RETURN=$(jq -r '.return' <<< "$CURL")

# Si une erreur est survenue (code de retour différent de 201 ou vide), on tente d'afficher le message retourné par le serveur
if [ -z "$UPDATE_RETURN" ];then
	echo -e "[$JAUNE ERREUR $RESET] L'envoi des données de mise à jour a échouée, erreur inconnue."
fi

# Récupération et affichage des messages

# Si il y a eu des messages d'erreur on les affiche
if echo "$CURL" | grep -q "message_error";then
	UPDATE_MESSAGE_ERROR=($(jq -r '.message_error[]' <<< "$CURL")) # array

	# UPDATE_MESSAGE_ERROR est un array pouvant contenir plusieurs messages d'erreurs
	for MESSAGE in "${UPDATE_MESSAGE_ERROR[@]}"; do
		echo -e "[$JAUNE ERREUR $RESET] $MESSAGE"
	done
	ERROR_STATUS=1

	UPDATE_REQUEST_STATUS="error"
fi

# Si il y a eu des message de succès on les affiche
if echo "$CURL" | grep -q "message_success";then
	UPDATE_MESSAGE_SUCCESS=($(jq -r '.message_success[]' <<< "$CURL")) # array

	# UPDATE_MESSAGE_SUCCESS est un array pouvant contenir plusieurs messages d'erreurs
	for MESSAGE in "${UPDATE_MESSAGE_SUCCESS[@]}"; do
		echo -e "[$VERT OK $RESET] $MESSAGE"
	done

	UPDATE_REQUEST_STATUS="done"
fi

update_request_status

rm "$TMP_FILE" -f

IFS=$OLD_IFS
}