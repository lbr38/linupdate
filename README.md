
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

<h2>Installation and documentation</h2>

Official documentation is available <a href="https://github.com/lbr38/linupdate/wiki">here</a>.

It should help you **installing** and starting using linupdate.


<h2>Parameters</h2>

<pre>
 Main:
  --vv|-vv                                     → Enable verbose mode
  --version|-v                                 → Print current version
  --profile|--type|--print-profile PROFILE     → Configure host profile (leave empty to print actual)
  --environment|--env ENV                      → Configure host environment (leave empty to print actual)

 Package update configuration
  --exclude-major|-em PACKAGE                  → Configure packages to exclude on major release update, separated by a comma. Specify 'none' to clean.
  --exclude|-e PACKAGE                         → Configure packages to exclude, separated by a comma. Specify 'none' to clean.

 Package update execution
  --check-updates|-cu                          → Check packages to be updated and quit
  --assume-yes|--force                         → Enable 'assume yes' (answer 'yes' to every confirm prompt)
  --dist-upgrade|-du                           → Enable 'dist-upgrade' for apt (Debian only)
  --keep-oldconf|-ko                           → Keep actual configuration file when attempting to be overwrited by apt during package update (Debian only)
  --ignore-exclude|-ie                         → Ignore all packages minor or major release update exclusions

 Modules
  --mod-enable|-mod-enable|-me MODULE          → Enable specified module
  --mod-disable|-mod-disable|-md MODULE        → Disable specified module
  --mod-configure|-mc|--mod-exec MODULE        → Configure specified module (using module commands, see module help or documentation)
  --mod-configure MODULE --help                → Print module help

 Agent
  --agent-start                                → Start linupdate agent
  --agent-stop                                 → Stop linupdate agent
  --agent-restart                              → Restart linupdate agent
  --agent-enable                               → Enable linupdate agent start on boot
  --agent-disable                              → Disable linupdate agent start on boot
</pre>
