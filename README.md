
<h1>LINUPDATE</h1>

**linupdate** is a package updater tool for Debian and Redhat based OS.

Using ``apt`` and ``dnf``, it provides basic and avanced update features especially when being managed by a <a href="https://github.com/lbr38/repomanager">Repomanager</a> reposerver:
- update packages
- exclude packages from update
- execute pre or post update actions (e.g: restart services)
- send mail update reports
- register to a **Repomanager** reposerver and get configuration from that server

linupdate is a modular tool. New modules could be added in the future to improve the update experience.

![alt text](https://github.com/user-attachments/assets/a028db13-d7ef-4b1c-9d01-3fd40b0e538e)

<h2>Requirements</h2>

**linupdate** ``3`` is regulary tested and should run fine on following systems with python3 installed:

- Debian 11, 12 and derivatives (Ubuntu, Mint, ...)
- CentOS 8, 9 and derivatives (Rocky, Alma, ...)

Older OS can still run **linupdate** ``2.x.x`` (bash version) but will not be supported anymore:

- Debian 10
- CentOS 7

<h2>Installation and documentation</h2>

Official documentation is available <a href="https://github.com/lbr38/linupdate/wiki">here</a>.

It should help you **installing** and starting using linupdate.


<h2>Parameters</h2>

<pre>
 Available options:

    Name                                         Description
--  -------------------------------------------  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    --help, -h                                   Show help
    --show-config, -sc                           Show raw configuration
    --version, -v                                Show version
    
    Global configuration options
    
    --profile, -p [PROFILE]                      Print current profile or set profile
    --env, -e [ENVIRONMENT]                      Print current environment or set environment
    --mail-enable [true|false]                   Enable or disable mail reports
    --get-mail-recipient                         Get current mail recipient(s)
    --set-mail-recipient [EMAIL]                 Set mail recipient(s) (separated by commas)
    
    Update options
    
    --dist-upgrade, -du                          Enable distribution upgrade when updating packages (Debian based OS only)
    --keep-oldconf                               Keep old configuration files when updating packages (Debian based OS only)
    --assume-yes, -y                             Answer yes to all questions
    --check-updates, -cu                         Only check for updates and exit
    --ignore-exclude, -ie                        Ignore all package exclusions
    --get-update-method                          Get current update method
    --set-update-method [one_by_one|global]      Set update method: one_by_one (update packages one by one, one apt command executed for each package) or global (update all packages at once, one single apt command executed for all packages)
    --exit-on-package-update-error [true|false]  When update method is one_by_one, immediately exit if an error occurs during package update and do not update the remaining packages
    
    Packages exclusion and services restart
    
    --get-exclude                                Get the current list of packages to exclude from update
    --get-exclude-major                          Get the current list of packages to exclude from update (if package has a major version update)
    --get-service-restart                        Get the current list of services to restart after package update
    --exclude [PACKAGE]                          Set packages to exclude from update (separated by commas)
    --exclude-major [PACKAGE]                    Set packages to exclude from update (if package has a major version update) (separated by commas)
    --service-restart [SERVICE]                  Set services to restart after package update (separated by commas)
    
    Modules
    
    --mod-list                                   List available modules
    --mod-enable [MODULE]                        Enable a module
    --mod-disable [MODULE]                       Disable a module

 Usage: linupdate [OPTIONS]
</pre>

<h2>Contact</h2>

- For bug reports, issues or features requests, please open a new issue in the Github ``Issues`` section
- A Discord channel is available <a href="https://discord.gg/Vz9XKQxa">here</a> for any questions or quick help/debugging (English or French spoken)
