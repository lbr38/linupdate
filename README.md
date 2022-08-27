
<h1>LINUPDATE</h1>

<b>linupdate</b> is a package updater tool for Debian and Redhat based OS.

Using apt and yum, it provides basic and avanced update features, especially being managed by a Repomanager reposerver:
- update packages
- exclude packages from update
- execute pre or post update actions (e.g: restart services)
- receive mail update reports
- register to a <b>Repomanager</b> reposerver and get configuration from that server

linupdate is a modular tool. New modules could be added in the future to improve the update experience.

![alt text](https://github.com/lbr38/repomanager-docs/blob/main/screenshots/linupdate/linupdate-1.png?raw=true)

<h1>Installation</h1>

```
git clone https://github.com/lbr38/linupdate.git /tmp/linupdate
cd /tmp/linupdate
./linupdate
```

<h1>Parameters</h1>

<pre>
Main:
--vv|-vv                                     → Enable verbose mode
--version|-v                                 → Print current version
--update|-u                                  → Update linupdate to the last available release on github
--enable-auto-update                         → Enable linupdate automatic update
--disable-auto-update                        → Disable linupdate automatic update
--install|--reinstall|-i                     → Install or reinstall linupdate (/!\ will delete actual configuration)
--profile|--type|--print-profile PROFILE     → Configure host profile (leave empty to print actual)
--environnement|--env ENV                    → Configure host environment (leave empty to print actual)

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

<h1>Modules</h1>

<h2>Linupdate & Repomanager</h2>

The linupdate <b>reposerver</b> module provides a connection between linupdate and a Repomanager server. 'Managing hosts' must be enabled on Repomanager's side.

<b>Managing hosts</b>

Host executing linupdate can send its system and packages information to the Repomanager server, especially:
- General information (Hostname, IP, Kernel, OS...)
- Available packages for update
- Installed packages
- Packages events history (installation, updates, uninstallation...)

An agent allows to regulary send those informations to the reposerver.


The <b>Manage hosts</b> tab on Repomanager regroup all hosts that have sended their informations:

![alt text](https://github.com/lbr38/repomanager-docs/blob/main/screenshots/linupdate/linupdate-repomanager-4.png?raw=true)


<b>Managing configuration profiles</b>

The <b>Manage profiles</b> tab on Repomanager allows to create configuration profiles for hosts executing linupdate and registered to Repomanager.
Profile can define packages to exclude, services to restart after an update and repos sources configuration for hosts using that profile. It's a convenient way to manage multiple hosts with the same configuration.

On each <b>linupdate</b> execution, it will get its profile configuration (including repos conf and packages exclusions) from its reposerver (linupdate reposerver module must be enabled and configured).


<b>Configuration</b>

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

From here, the host become visible from Repomanager web interface, in <b>Manage hosts</b> tab.

Send informations to the server:

```
linupdate --mod-configure reposerver --send-general-status    # send global informations 
linupdate --mod-configure reposerver --send-full-status       # send packages inventory and events history
```

Enable reposerver agent:

```
linupdate --mod-configure reposerver --enable-agent
linupdate --restart-agent
```

Check that linupdate agent is running:

```
systemctl status linupdate
```