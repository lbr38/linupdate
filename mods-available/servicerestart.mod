#!/bin/bash
# Redémarrage des services post-mise à jour

MOD_CONF="${MODULES_CONF_DIR}/servicerestart.conf"

#### FONCTIONS ####

# Installation du module
install() {
	cd ${MODULES_ENABLED_DIR}/ &&
	ln -sfn ../mods-available/${MODULE}.mod 10_servicerestart.mod &&
	mkdir -p "${MODULES_CONF_DIR}" &&
	\cp "${TMP_DIR}/mods-available/configurations/${MODULE}.conf" ${MODULES_CONF_DIR}/ &&
	echo -e "Installation du module ${JAUNE}servicerestart${RESET} : [$VERT OK $RESET]"
	configure
}


configure() {
	# Configuration du module servicerestart.mod (fichier de configuration servicerestart.conf)
	echo -ne " → Niveau de Fail-level à attribuer à ce module [1-3] : "; read -p "" FAILLEVEL
	if [ -z "$FAILLEVEL" ];then FAILLEVEL="3";fi

	echo -e "[MODULE]" > $MOD_CONF
	echo -e "FAILLEVEL=\"$FAILLEVEL\"" >> $MOD_CONF
	#echo -e "\n[REPOSERVER]" >> $MOD_CONF
	#echo -e "URL=\"${REPOSERVER_URL}\"" >> $MOD_CONF

	# Configuration de linupdate (fichier de configuration linupdate.conf)
	# Ajout des paramètres si n'existe pas
#	if ! grep -q "^REPOSERVER_ALLOW_CONFUPDATE" "$CONF";then
#		echo -ne " → Autoriser le serveur ${JAUNE}${REPOSERVER_URL}${RESET} à mettre à jour la configuration de linupdate (yes/no) : "; read -p "" CONFIRM
#		if [ "$CONFIRM" == "yes" ] || [ "$CONFIRM" == "y" ];then
#			echo "REPOSERVER_ALLOW_CONFUPDATE=\"yes\"" >> "$CONF"
#		fi
#	fi
#	if ! grep -q "^REPOSERVER_ALLOW_REPOSFILES_UPDATE" "$CONF";then
#		echo -ne " → Autoriser le serveur ${JAUNE}${REPOSERVER_URL}${RESET} à mettre à jour la configuration des repos sur cette machine (yes/no) : "; read -p "" CONFIRM
#		if [ "$CONFIRM" == "yes" ] || [ "$CONFIRM" == "y" ];then
#			echo "REPOSERVER_ALLOW_REPOSFILES_UPDATE=\"yes\"" >> "$CONF"
#		fi
#	fi
#	if ! grep -q "^REPOSERVER_ALLOW_OVERWRITE" "$CONF";then
#		echo -ne " → Autoriser le serveur ${JAUNE}${REPOSERVER_URL}${RESET} à forcer les deux paramètres précédents à ${JAUNE}yes${RESET} si ceux-ci sont paramétrés à ${JAUNE}no${RESET} (yes/no) : "; read -p "" CONFIRM
#		if [ "$CONFIRM" == "yes" ] || [ "$CONFIRM" == "y" ];then
#			echo "REPOSERVER_ALLOW_OVERWRITE=\"yes\"" >> "$CONF"
#		fi
#	fi
}


loadModule() {
	# Si le fichier de configuration du module est introuvable alors on le configure
	if [ ! -f "$MOD_CONF" ] || [ ! -s "$MOD_CONF" ];then
		configure
	fi

	echo -e " - Module servicerestart : ${JAUNE}Activé${RESET}"
}

main() {
	echo test
}
#
#
#RESTART_APACHE=0
#RESTART_NGINX=0
#RESTART_PHPFPM=0
#RESTART_MYSQL=0
#RESTART_NRPE=0
#RESTART_MUNIN=0
#RESTART_NETDATA=0
#RESTART_NEWRELIC=0
#RESTART_FAIL2BAN=0
#RESTART_SERVICE=0
#RESTART_SERVICE_NAME=""
#RESTART_AUTRE_SERVICE=0
#RESTART_AUTRE_SERVICE_CMD="commande de redémarrage"	# Commande de redémarrage d'un autre service
#
#service_restart() {	# Fonction gérant les redémarrage de services post-maj
#if [ ! -z "$MAJ_NEED_RESTART" ];then 	# Si $MAJ_NEED_RESTART contient des paquets nécessitant un redémarrage, on traite
#	IFS=" ";for PAQUET in ${MAJ_NEED_RESTART};do # On injecte dans PAQUETS, la liste des paquets nécessitant un redémarrage renseignés dans le fichier yum-update.conf
#		if [ "$PAQUET" == "httpd" ];then
#			RESTART_APACHE="1"
#		elif [ "$PAQUET" == "nginx" ];then
#			RESTART_NGINX="1"
#		elif [ "$PAQUET" == "mysql" ];then
#			RESTART_MYSQL="1"
#		elif [ "$PAQUET" == "php-fpm" ];then
#			RESTART_PHPFPM="1"
#		elif [ "$PAQUET" == "nrpe" ];then
#			RESTART_NRPE="1"
#		elif [ "$PAQUET" == "netdata" ];then
#			RESTART_NETDATA="1"
#		elif [ "$PAQUET" == "newrelic" ];then
#			RESTART_NEWRELIC="1"
#		elif [ "$PAQUET" == "newrelic-daemon" ];then
#			RESTART_NEWRELIC="1"
#		elif [ "$PAQUET" == "munin-node" ];then
#			RESTART_MUNIN="1"
#		elif [ "$PAQUET" == "fail2ban" ];then
#			RESTART_FAIL2BAN="1"
#		fi
#	done
#fi
#
#
## Si le paramètre --restart-apache a été passé, on redémarre apache après les maj 
#if [ "$RESTART_APACHE" -eq "1" ];then
#    droits_apache &&	# D'abord on remets en place les droits sinon apache pourrait ne pas redémarrer
#	echo -e "→ Redémarrage d'Apache / service httpd : "
#	/usr/sbin/apachectl configtest && /sbin/service httpd restart	# Test de la configuration puis redémarrage
#fi
#
## Si le paramètre --restart-nginx a été passé, on redémarre nginx après les maj
#if [ "$RESTART_NGINX" -eq "1" ];then
#    droits_nginx &&		# D'abord on remets en place les droits sinon nginx pourrait ne pas redémarrer
#    echo -e "[$VERT OK $RESET]"
#	echo -e "→ Redémarrage de Nginx : "
#	/usr/sbin/nginx -t && /sbin/service nginx restart		# Test de la configuration puis redémarrage
#fi
#
## Si le paramètre --restart-mysql a été passé, on redémarre mysql après les maj
#if [ "$RESTART_MYSQL" -eq "1" ];then
#	echo -e "→ Redémarrage de Mysql : "
#	/sbin/service mysqld restart
#fi
#
## Si le paramètre --restart-phpfpm a été passé, on redémarre php-fpm après les maj
#if [ "$RESTART_PHPFPM" -eq "1" ];then
#	echo -e "→ Redémarrage de PHP-FPM : "
#	/sbin/service php-fpm restart
#fi
#
#if [ "$RESTART_NRPE" -eq "1" ];then
#	echo -e "→ Redémarrage de Nrpe : "
#	/sbin/service nrpe restart
#fi
#
#if [ "$RESTART_NETDATA" -eq "1" ];then
#	echo -e "→ Redémarrage de Netdata : "
#	chown netdata:netdata /usr/share/netdata/web -R
#fi
#
#if [ "$RESTART_MUNIN" -eq "1" ];then
#	echo -e "→ Redémarrage de Munin : "
#	/sbin/service munin-node restart
#fi
#
#if [ "$RESTART_NEWRELIC" -eq "1" ];then
#	echo -e "→ Redémarrage de newrelic (= redémarrage de php ou php-fpm)"
#	if [ -f /usr/sbin/php-fpm ];then
#		/sbin/service php-fpm reload
#	elif [ -f /usr/sbin/httpd ];then
#		/sbin/service httpd reload
#	fi
#fi
#
#if [ "$RESTART_FAIL2BAN" -eq "1" ];then
#    echo -e "→ Redémarrage de fail2ban : "
#    /sbin/service fail2ban restart
#fi
#
## Si le paramètre --restart-service a été passé, on redémarre un service défini 
#if [ "$RESTART_SERVICE" -eq "1" ];then
#	echo -e "→ Redémarrage du service $RESTART_SERVICE_NAME : "
#	/sbin/service "$RESTART_SERVICE_NAME" restart
#fi
#
## Si le paramètre --restart-autre a été passé, on redémarre un service (défini en début de script) après les maj
#if [ "$RESTART_AUTRE_SERVICE" -eq "1" ];then
#    echo -e "→ Redémarrage d'un service : "
#    eval "$RESTART_AUTRE_SERVICE_CMD"	# Appel de la commande de redémarrage du service
#fi
#}
