
<h1>LINUPDATE</h1>

**linupdate** is a package updater tool for Debian and Redhat based OS.

Using ``apt`` and ``dnf``, it provides basic and avanced update features especially when being managed by a <a href="https://github.com/lbr38/repomanager">Repomanager</a> reposerver:
- update packages
- exclude packages from update
- execute pre or post update actions (e.g: restart services)
- send mail update reports
- register to a **Repomanager** reposerver and get configuration from that server

linupdate is a modular tool. New modules could be added in the future to improve the update experience.

![alt text](https://github.com/user-attachments/assets/f1eed81d-af86-4738-98b5-3e41c5cfe069)

<h2>Requirements</h2>

**linupdate** is regulary tested and should run fine on following systems (python3 required):

- **Debian 11, 12** and derivatives (Ubuntu, Mint, ...)
- **RHEL 9, 10** and derivatives (CentOS, Rocky, Alma, ...)

RHEL 8 and derivatives are not supported anymore.

<h2>Installation and documentation</h2>

Official documentation is available <a href="https://github.com/lbr38/linupdate/wiki">here</a>.

It should help you **installing** and starting using linupdate.


<h2>Parameters</h2>

<pre>
Available options:

    Name                                         Description
--  -------------------------------------------  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    --help, -h                                   Show help
    --show-config, -sc                           Show raw configuration
    --version, -v                                Show version
    --debug                                      Enable debug mode
    
    Global configuration options
    
    --profile, -p [PROFILE]                      Print or set profile
    --env, -e [ENVIRONMENT]                      Print or set environment
    --mail-enable [true|false]                   Enable or disable mail reports
    --mail-recipient [EMAIL]                     Print or set mail recipient(s) (separated by commas)
                                                 Specify "None" to clear the recipient list
    --mail-smtp-host [HOST]                      Print or set mail SMTP host
    --mail-smtp-port [PORT]                      Print or set mail SMTP port
    
    Update options
    
    --update, -u [PACKAGE]                       Update only the specified packages (separated by commas)
    --dist-upgrade, -du                          Enable distribution upgrade when updating packages (Debian based OS only)
    --dry-run                                    Simulate the update process (do not update packages)
    --keep-oldconf                               Keep old configuration files when updating packages (Debian based OS only)
    --assume-yes, -y                             Answer yes to all questions
    --check-updates, -cu                         Only check for updates and exit
    --ignore-exclusions, -ie                     Ignore all package exclusions
    --exit-on-package-update-error [true|false]  Immediately exit if an error occurs during package update and do not update the remaining packages
    
    Packages exclusion and services restart
    
    --exclude [PACKAGE]                          Print or set packages to exclude from update (separated by commas)
                                                 Regex pattern ".*" can be used to match multiple packages. Example: --exclude php.*
                                                 Specify "None" to clear the exclusion list
    --exclude-major [PACKAGE]                    Print or set packages to exclude from update (if package has a major version update) (separated by commas)
                                                 Regex pattern ".*" can be used to match multiple packages. Example: --exclude-major php.*
                                                 Specify "None" to clear the major update exclusion list
    --service-reload [SERVICE]                   Print or set services to reload after package update (separated by commas)
                                                 Specify "None" to clear the service reload list
    --service-restart [SERVICE]                  Print or set services to restart after package update (separated by commas)
                                                 Specify "None" to clear the service restart list
    
    Modules
    
    --mod-list                                   List available modules
    --mod-enable [MODULE]                        Enable a module
    --mod-disable [MODULE]                       Disable a module
    
    Service tuning
    
    --cpu-priority [high, medium, low]           Print or set CPU priority for the linupdate service. Lower priority means less CPU usage but also more time to complete service operations - default is high
    --memory-limit [bytes]                       Print or set memory limit for the linupdate service in bytes - default is 1G
    --oom-score [-1000 to 1000]                  Print or set OOM (Out Of Memory) score for the linupdate service - the higher the value, the more likely the service will be killed by the OOM killer - default is 500

Usage: linupdate [OPTIONS]
</pre>

<h2>Contact</h2>

- For bug reports, issues or features requests, please open a new issue in the Github ``Issues`` section
- A Discord channel is available <a href="https://discord.gg/34yeNsMmkQ">here</a> for any questions or quick help/debugging (English or French spoken)
