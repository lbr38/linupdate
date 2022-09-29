
<h1>LINUPDATE</h1>

**linupdate** is a package updater tool for Debian and Redhat based OS.

Using apt and yum, it provides basic and avanced update features especially when being managed by a <a href="https://github.com/lbr38/repomanager">Repomanager</a> reposerver:
- update packages
- exclude packages from update
- execute pre or post update actions (e.g: restart services)
- receive mail update reports
- register to a **Repomanager** reposerver and get configuration from that server

linupdate is a modular tool. New modules could be added in the future to improve the update experience.

![alt text](https://raw.githubusercontent.com/lbr38/resources/main/screenshots/linupdate/linupdate-1.png)

<h2>Requirements</h2>

<h3>OS</h3>

Linupdate **has been tested and runs fine** on following systems:
- Debian 10, 11
- CentOS 7

It may run on most recent Debian/RHEL systems but haven't been tested yet / maybe needs some code update.

<h2>Installation</h2>

```
git clone https://github.com/lbr38/linupdate.git /tmp/linupdate
cd /tmp/linupdate
./linupdate
```

<h2>Parameters</h2>

<pre>
Main:
--vv|-vv                                     → Enable verbose mode
--version|-v                                 → Print current version
--update|-u                                  → Update linupdate to the last available release on github
--enable-auto-update                         → Enable linupdate automatic update
--disable-auto-update                        → Disable linupdate automatic update
--install|--reinstall|-i                     → Install or reinstall linupdate (/!\ will delete actual configuration)
--profile|--type|--print-profile PROFILE     → Configure host profile (leave empty to print actual)
--environment|--env ENV                    → Configure host environment (leave empty to print actual)

Package update configuration
--exclude-major|-em PACKAGE                  → Configure packages to exclude on major release update, separated by a comma. Specify 'none' to clean.
--exclude|-e PACKAGE                         → Configure packages to exclude, separated by a comma. Specify 'none' to clean.

Update execution
--check-updates|-cu                          → Check packages to be updated and quit
--assume-yes|--force                         → Enable 'assume yes' (answer 'yes' to every confirm prompt)
--dist-upgrade|-du                           → Enable 'dist-upgrade' for apt (Debian only)
--keep-oldconf|-ko                           → Keep actual configuration file when attempting to be overwrited by apt during package update (Debian only)
--ignore-exclude|-ie                         → Ignore all packages minor or major release update exclusions

Modules
--list-modules|--list-mod|-m                 → List available modules
--mod-enable|-mod-enable|-me MODULE          → Enable specified module
--mod-disable|-mod-disable|-md MODULE        → Disable specified module
--mod-configure|-mc|--mod-exec MODULE        → Configure specified module (using module commands, see module help or documentation)
--mod-configure MODULE --help                → Print module help

Agent
--agent-deploy|--deploy-agent                → Deploy linupdate agent
--agent-start|--start-agent                  → Start linupdate agent
--agent-stop|--stop-agent                    → Stop linupdate agent
--agent-restart|--restart-agent              → Restart linupdate agent
--agent-enable|--enable-agent                → Enable linupdate agent start on boot
</pre>

<h2>Modules</h2>

<h3>Linupdate & Repomanager</h3>

The linupdate **reposerver** module provides a connection between linupdate and a <a href="https://github.com/lbr38/repomanager">Repomanager</a> server.

The **Manage hosts** parameter must be enabled on Repomanager's side.

**Managing hosts**

An host executing linupdate can send its system and packages informations to the Repomanager server, especially:
- General information (Hostname, IP, Kernel, OS...)
- Available packages for update
- Installed packages
- Packages events history (installation, updates, uninstallation...)

If enabled, an agent can regulary send those informations to the reposerver.


The **Manage hosts** tab on Repomanager regroup all hosts that have sended their informations:

![alt text](https://github.com/lbr38/resources/raw/main/screenshots/repomanager/repomanager-5.png?raw=true)
![alt text](https://github.com/lbr38/resources/raw/main/screenshots/repomanager/repomanager-3.png?raw=true)


**Managing configuration profiles**

The **Manage profiles** tab on Repomanager provides a way to create configuration profiles for hosts executing linupdate and registered to Repomanager.
A profile can define packages to exclude from an update, services to restart after an update and repos sources configuration for hosts using that profile. It's a convenient way to manage multiple hosts with the same configuration and limit the risks on critical packages updates.

Every time **linupdate** is executed, it gets its profile configuration (including repos conf and packages exclusions) from its reposerver.


**How to register an host executing linupdate to a Repomanager server**

Enable reposerver module:

```
linupdate --mod-enable reposerver
```

Configure target reposerver URL and params:

```
linupdate --mod-configure reposerver --url https://REPOMANAGER_URL --fail-level 3 --allow-conf-update yes --allow-repos-update yes --allow-overwrite no
```

Register this host to Repomanager to retrieve an authentication Id+token.

```
linupdate --mod-configure reposerver --register
```

From here, the host become visible from Repomanager web interface, in **Manage hosts** tab.

Send informations to the server:

```
linupdate --mod-configure reposerver --send-general-status    # send host global informations 
linupdate --mod-configure reposerver --send-full-status       # send host packages inventory and events history
```

Deploy and enable reposerver agent:

```
linupdate --mod-configure reposerver --enable-agent
linupdate --agent-deploy
```

Check that linupdate agent is running:

```
systemctl status linupdate
```