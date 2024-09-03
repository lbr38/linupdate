# coding: utf-8

# Import libraries
from pathlib import Path
from colorama import Fore, Style
import yaml
import ipaddress
import shutil
import socket

# Import classes
from src.controllers.System import System
from src.controllers.App.Config import Config as appConfig
from src.controllers.Package.Package import Package
from src.controllers.HttpRequest import HttpRequest
from src.controllers.Yaml import Yaml

class Config:
    def __init__(self):
        self.config_file = '/etc/linupdate/modules/reposerver.yml'
        self.systemController = System()
        self.appConfigController = appConfig()
        self.packageController = Package()
        self.httpRequestController = HttpRequest()

    #-----------------------------------------------------------------------------------------------
    #
    #   Generate reposerver config file if not exist
    #
    #-----------------------------------------------------------------------------------------------
    def generate_conf(self):
        # Generate configuration file if not exists
        if not Path(self.config_file).is_file():
            # Copy default configuration file
            try:
                shutil.copy2('/opt/linupdate/templates/modules/reposerver.template.yml', '/etc/linupdate/modules/reposerver.yml')
            except Exception as e:
                raise Exception('error while generating reposerver configuration file ' + self.config_file + ': ' + str(e))

        # TODO: to remove in some time
        # If old linupdate (bash version) config file exists, migrate it
        if Path('/etc/linupdate/modules/reposerver.conf').is_file():
            self.migrate_conf()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return current reposerver URL
    #
    #-----------------------------------------------------------------------------------------------
    def getUrl(self):
        # Get current configuration
        configuration = self.get_conf()

        # Check if url exists in configuration and is not empty
        if 'url' not in configuration['reposerver']:
            raise Exception('reposerver URL not found in ' + self.config_file)
        
        if configuration['reposerver']['url'] == '':
            raise Exception('no reposerver URL set. Please set a URL with --url <url> option')

        # Return URL
        return configuration['reposerver']['url']
        

    #-----------------------------------------------------------------------------------------------
    #
    #   Set reposerver URL
    #
    #-----------------------------------------------------------------------------------------------
    def setUrl(self, url):
        # Check that url is valid (start with http(s)://)
        if not url.startswith('http://') and not url.startswith('https://'):
            raise Exception('reposerver URL must start with http:// or https://')

        # Get current configuration
        configuration = self.get_conf()

        # Remove final slash if exists
        if url.endswith('/'):
            url = url[:-1]

        # Set url
        configuration['reposerver']['url'] = url

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Return reposerver configuration
    #
    #-----------------------------------------------------------------------------------------------
    def get_conf(self):
        # Checking that a configuration file exists for reposerver module
        if not Path(self.config_file).is_file():
            raise Exception('reposerver configuration file ' + self.config_file + ' does not exist')

        # Open YAML config file
        with open(self.config_file, 'r') as stream:
            try:
                # Read YAML and return profile
                return yaml.safe_load(stream)

            except yaml.YAMLError as e:
                raise Exception('error while reading reposerver configuration file ' + self.config_file + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Write reposerver configuration to config file
    #
    #-----------------------------------------------------------------------------------------------
    def write_conf(self, configuration):
        yaml = Yaml()

        try:
            yaml.write(configuration, self.config_file)
        except Exception as e:
            raise Exception('error while writing to reposerver configuration file ' + self.config_file + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Check if the config file exists and if it contains the required parameters
    #
    #-----------------------------------------------------------------------------------------------
    def check_conf(self):
        if not Path(self.config_file).is_file():
            raise Exception('reposerver module configuration file not found ' + self.config_file)

        # Retrieve configuration
        configuration = self.get_conf()

        # Check if reposerver is set
        if 'reposerver' not in configuration:
            raise Exception('reposerver key not found in ' + self.config_file)
        
        # Check if reposerver.url is set
        if 'url' not in configuration['reposerver']:
            raise Exception('reposerver.url key not found in ' + self.config_file)

        # Check if client is set
        if 'client' not in configuration:
            raise Exception('client key not found in ' + self.config_file)
        
        # Check if client.auth is set
        if 'auth' not in configuration['client']:
            raise Exception('client.auth key not found in ' + self.config_file)

        # Check if client.auth.id is set
        if 'id' not in configuration['client']['auth']:
            raise Exception('client.auth.id key not found in ' + self.config_file)
        
        # Check if client.auth.token is set
        if 'token' not in configuration['client']['auth']:
            raise Exception('client.auth.token key not found in ' + self.config_file)
        
        # Check if client.get_packages_conf_from_reposerver is set
        if 'get_packages_conf_from_reposerver' not in configuration['client']:
            raise Exception('client.get_packages_conf_from_reposerver key not found in ' + self.config_file)
        
        # Check if client.get_packages_conf_from_reposerver.enabled is set
        if 'enabled' not in configuration['client']['get_packages_conf_from_reposerver']:
            raise Exception('client.get_packages_conf_from_reposerver.enabled key not found in ' + self.config_file)
        
        # Check if client.get_packages_conf_from_reposerver.enabled is set (True or False)
        if configuration['client']['get_packages_conf_from_reposerver']['enabled'] not in [True, False]:
            raise Exception('client.get_packages_conf_from_reposerver.enabled key must be set to true or false')

        # Check if client.get_repos_from_reposerver is set
        if 'get_repos_from_reposerver' not in configuration['client']:
            raise Exception('client.get_repos_from_reposerver key not found in ' + self.config_file)

        # Check if client.get_repos_from_reposerver.enabled is set
        if 'enabled' not in configuration['client']['get_repos_from_reposerver']:
            raise Exception('client.get_repos_from_reposerver.enabled key not found in ' + self.config_file)
        
        # Check if client.get_repos_from_reposerver.enabled is set (True or False)
        if configuration['client']['get_repos_from_reposerver']['enabled'] not in [True, False]:
            raise Exception('client.get_repos_from_reposerver.enabled key must be set to true or false')

        # Check if client.get_repos_from_reposerver.remove_existing_repos is set
        if 'remove_existing_repos' not in configuration['client']['get_repos_from_reposerver']:
            raise Exception('client.get_repos_from_reposerver.remove_existing_repos key not found in ' + self.config_file)
        
        # Check if client.get_repos_from_reposerver.remove_existing_repos is set (True or False)
        if configuration['client']['get_repos_from_reposerver']['remove_existing_repos'] not in [True, False]:
            raise Exception('client.get_repos_from_reposerver.remove_existing_repos key must be set to true or false')
        
        # Check if agent is set
        if 'agent' not in configuration:
            raise Exception('agent key not found in ' + self.config_file)
        
        # Check if agent.enabled is set and is set (True or False)
        if 'enabled' not in configuration['agent']:
            raise Exception('agent.enabled key not found in ' + self.config_file)

        # Check if agent.enabled is set and is set (True or False)
        if configuration['agent']['enabled'] not in [True, False]:
            raise Exception('agent.enabled key must be set to true or false')
        
        # Check if agent.listen is set
        if 'listen' not in configuration['agent']:
            raise Exception('agent.listen key not found in ' + self.config_file)
        
        # Check if agent.listen.enabled is set
        if 'enabled' not in configuration['agent']['listen']:
            raise Exception('agent.listen.enabled key not found in ' + self.config_file)
        
        # Check if agent.listen.enabled is set (True or False)
        if configuration['agent']['listen']['enabled'] not in [True, False]:
            raise Exception('agent.listen.enabled key must be set to true or false')
            

    #-----------------------------------------------------------------------------------------------
    #
    #   Register to reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def register(self, api_key: str, ip: str):
        # Get Reposerver URL
        url = self.getUrl()

        # Check if URL is not null
        if url == '':
            raise Exception('you must configure the target reposerver URL [--url <url>]')

        print(' Registering to ' + url + ':')

        # Check if API key is not null
        if api_key == 'null':
            raise Exception('you must specify an API key from a Repomanager user account [--register --api-key <api-key>]')

        # If no IP has been specified (null), then retrieve the public IP of the host
        if ip == 'null':
            try:
                ip = self.httpRequestController.get('https://api.ipify.org', '', '', 2).text
            except Exception as e:
                raise Exception('failed to retrieve public IP from https://api.ipify.org (resource might be temporarily unavailable): ' + str(e))

        # Check that the IP is valid
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise Exception('invalid IP address ' + ip)

        # Register to server using API key and IP (POST)
        data = {
            'ip': ip,
            'hostname': socket.getfqdn()
        }

        try:
            results = self.httpRequestController.post_token(url + '/api/v2/host/registering', api_key, data)
        except Exception as e:
            raise Exception('Registering failed')

        # If registration is successful, the server will return an Id and a token, set Id and token in configuration
        self.setId(results['id'])
        self.setToken(results['token'])


    #-----------------------------------------------------------------------------------------------
    #
    #   Unregister from reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def unregister(self):
        # Get Reposerver URL
        url = self.getUrl()

        # Check if URL is not null
        if url == '':
            raise Exception('you must configure the target Reposerver URL [--url <url>]')

        print(' Unregistering from ' + Fore.GREEN + url + Style.RESET_ALL + ':')

        # Get Id and token from configuration
        id = self.getId()
        token = self.getToken()

        # Check if Id and token are not null
        if id == '':
            raise Exception('no auth Id found in configuration')
        
        if token == '':
            raise Exception('no auth token found in configuration')
        
        try:
            # Unregister from server using Id and token (DELETE)
            self.httpRequestController.delete(url + '/api/v2/host/registering', id, token)
        except Exception as e:
            raise Exception('Unregistering failed')


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable configuration update from reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def set_get_packages_conf_from_reposerver(self, value: bool):
        # Get current configuration
        configuration = self.get_conf()

        # Set get_packages_conf_from_reposerver
        configuration['client']['get_packages_conf_from_reposerver']['enabled'] = value

        # Write config file
        self.write_conf(configuration)

        if value == True:
            print(' Retrieving packages configuration from reposerver is ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
        else:
            print(' Retrieving packages configuration from reposerver is ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL, end='\n\n')


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable repositories configuration update from reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def set_get_repos_from_reposerver(self, value: bool):
        # Get current configuration
        configuration = self.get_conf()

        # Set get_repos_from_reposerver
        configuration['client']['get_repos_from_reposerver']['enabled'] = value

        # Write config file
        self.write_conf(configuration)

        if value == True:
            print(' Retrieving repositories configuration from reposerver is ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
        else:
            print(' Retrieving repositories configuration from reposerver is ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL, end='\n\n')


    #-----------------------------------------------------------------------------------------------
    #
    #   Set remove existing repositories
    #
    #-----------------------------------------------------------------------------------------------
    def set_remove_existing_repos(self, value: bool):
        # Get current configuration
        configuration = self.get_conf()

        # Set remove_existing_repos
        configuration['client']['get_repos_from_reposerver']['remove_existing_repos'] = value

        # Write config file
        self.write_conf(configuration)

        if value == True:
            print(' Removing existing repositories is ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
        else:
            print(' Removing existing repositories is ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL, end='\n\n')


    #-----------------------------------------------------------------------------------------------
    #
    #   Get authentication id
    #
    #-----------------------------------------------------------------------------------------------
    def getId(self):
        # Get current configuration
        configuration = self.get_conf()

        # Return Id
        return configuration['client']['auth']['id']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set authentication id
    #
    #-----------------------------------------------------------------------------------------------
    def setId(self, id: str):
        # Get current configuration
        configuration = self.get_conf()

        # Set Id
        configuration['client']['auth']['id'] = id

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get authentication token
    #
    #-----------------------------------------------------------------------------------------------
    def getToken(self):
        # Get current configuration
        configuration = self.get_conf()

        # Return Token
        return configuration['client']['auth']['token']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set authentication token
    #
    #-----------------------------------------------------------------------------------------------
    def setToken(self, token: str):
        # Get current configuration
        configuration = self.get_conf()

        # Set Token
        configuration['client']['auth']['token'] = token

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get profile packages configuration (exclusions) from reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def get_profile_packages_conf(self):
        # Get current configuration
        configuration = self.get_conf()

        # Get reposerver URL
        url = self.getUrl()

        # Get current profile, auth Id and token
        profile = self.appConfigController.get_profile()
        id = self.getId()
        token = self.getToken()

        print('  ▪ Getting ' + Fore.YELLOW + profile + Style.RESET_ALL + ' profile packages configuration:', end=' ')

        # Check if getting profile packages configuration from reposerver is enabled
        if configuration['client']['get_packages_conf_from_reposerver']['enabled'] == False:
            print(Fore.YELLOW + 'Disabled' + Style.RESET_ALL)
            return

        # Check if profile is not empty
        if not profile:
            raise Exception('no profile set. Please set a profile with --profile <profile> option')
        
        # Check if Id and token are not empty
        if not id or not token:
            raise Exception('no auth Id or token found in configuration')

        # Retrieve configuration from reposerver
        results = self.httpRequestController.get(url + '/api/v2/profile/' + profile + '/excludes', id, token, 2)

        # Parse results

        # Packages to exclude no matter the version
        if results[0]['Package_exclude'] != "null":
            # First, clear the exclude list
            self.appConfigController.set_exclusion()

            # Then, set the new exclude list
            self.appConfigController.set_exclusion(results[0]['Package_exclude'])

        # Packages to exclude on major version
        if results[0]['Package_exclude_major'] != "null":
            # First, clear the exclude major list
            self.appConfigController.set_major_exclusion()

            # Then, set the new exclude major list
            self.appConfigController.set_major_exclusion(results[0]['Package_exclude_major'])

        # Service to restart after an update
        if results[0]['Service_restart'] != "null":
            # First clear the services to restart
            self.appConfigController.set_service_to_restart()
            
            # Then set the new services to restart
            self.appConfigController.set_service_to_restart(results[0]['Service_restart'])

        print('[' + Fore.GREEN + ' OK ' + Style.RESET_ALL + ']')


    #-----------------------------------------------------------------------------------------------
    #
    #   Get profile repositories configuration from reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def get_profile_repos(self):
        # Get current configuration
        configuration = self.get_conf()

        # Get reposerver URL
        url = self.getUrl()

        # Get current profile, auth Id and token
        profile = self.appConfigController.get_profile()
        env = self.appConfigController.get_environment()
        id = self.getId()
        token = self.getToken()

        print('  ▪ Getting ' + Fore.YELLOW + profile + Style.RESET_ALL + ' profile repositories:', end=' ')

        # Check if getting profile packages configuration from reposerver is enabled
        if configuration['client']['get_repos_from_reposerver']['enabled'] == False:
            print(Fore.YELLOW + 'Disabled' + Style.RESET_ALL)
            return

        # Check if profile is not empty
        if not profile:
            raise Exception('no profile set. Please set a profile with --profile <profile> option')
        
        # Check if environment is not empty
        if not env:
            raise Exception('no environment set. Please set an environment with --env <environment> option')
        
        # Check if Id and token are not empty
        if not id or not token:
            raise Exception('no auth Id or token found in configuration')

        # Retrieve configuration from reposerver
        results = self.httpRequestController.get(url + '/api/v2/profile/' + profile + '/repos', id, token, 2)

        # Parse results

        # Quit if no results
        if not results:
            print(Fore.YELLOW + 'No repositories configured ' + Style.RESET_ALL)
            return
        
        # Remove current repositories files if enabled
        if configuration['client']['get_repos_from_reposerver']['remove_existing_repos']:
            # Debian
            if self.systemController.get_os_family() == 'Debian':
                # Clear /etc/apt/sources.list
                with open('/etc/apt/sources.list', 'w') as file:
                    file.write('')
                
                # Delete all files in /etc/apt/sources.list.d
                for file in Path('/etc/apt/sources.list.d/').glob('*.list'):
                    file.unlink()

            # Redhat
            if self.systemController.get_os_family() == 'Redhat':
                # Delete all files in /etc/yum.repos.d
                for file in Path('/etc/yum.repos.d/').glob('*.repo'):
                    file.unlink()

        # Create each repo file
        for result in results:
            # Depending on the OS family, the repo files are stored in different directories

            # Debian
            if self.systemController.get_os_family() == 'Debian':
                reposRoot = '/etc/apt/sources.list.d'

            # Redhat
            if self.systemController.get_os_family() == 'Redhat':
                reposRoot = '/etc/yum.repos.d'

            # Target repo file
            repo_file = reposRoot + '/' + result['filename']

            # If the file does not exist, create it and insert description at the top of the file, then content
            if not Path(repo_file).is_file():
                with open(repo_file, 'w') as file:
                    # Insert description
                    file.write('# ' + result['description'] + '\n')

            # Add content to the file, if not already in it
            with open(repo_file, 'r+') as file:
                # Replace __ENV__ with current environment on the fly
                content = result['content'].replace('__ENV__', env)

                # If the content is not already in the file, add it
                if content not in file.read():
                    file.write(content + '\n')

            # Set file permissions
            Path(repo_file).chmod(0o660)

        print('[' + Fore.GREEN + ' OK ' + Style.RESET_ALL + ']')


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable agent
    #
    #-----------------------------------------------------------------------------------------------
    def set_agent_enable(self, value: bool):
        try:
            # Get current configuration
            configuration = self.get_conf()

            # Set agent enable
            configuration['agent']['enabled'] = value

            # Write config file
            self.write_conf(configuration)

            if value:
                print(' Reposerver agent ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
            else:
                print(' Reposerver agent ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL, end='\n\n')
        except Exception as e:
            raise Exception('could not set agent enable to ' + str(value) + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable agent listening
    #
    #-----------------------------------------------------------------------------------------------
    def set_agent_listen(self, value: bool):
        try:
            # Get current configuration
            configuration = self.get_conf()

            # Set agent listening enable
            configuration['agent']['listen']['enabled'] = value

            # Write config file
            self.write_conf(configuration)

            if value:
                print(' Agent listening ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
            else:
                print(' Agent listening ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL, end='\n\n')
        except Exception as e:
            raise Exception('could not set agent listening enable to ' + str(value) + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Migration of old reposerver configuration file
    #
    #-----------------------------------------------------------------------------------------------
    def migrate_conf(self):
        # Old config file are like ini file
    
        print(' Detected old configuration file /etc/linupdate/modules/reposerver.conf, migrating...')

        try:
            # Open old config file
            with open('/etc/linupdate/modules/reposerver.conf', 'r') as file:
                lines = file.readlines()

                for line in lines:
                    # If url is set
                    if 'URL' in line:
                        url = line.split('=')[1].replace('"', '').strip()
                        self.setUrl(url)
   
                    # If id is set
                    if 'ID' in line:
                        id = line.split('=')[1].replace('"', '').strip()
                        self.setId(id)

                    # If token is set
                    if 'TOKEN' in line:
                        token = line.split('=')[1].replace('"', '').strip()
                        self.setToken(token)

                    # If get_packages_conf_from_reposerver is set
                    if 'GET_PROFILE_PKG_CONF_FROM_REPOSERVER' in line:
                        get_packages_conf_from_reposerver = line.split('=')[1].replace('"', '').strip()
                        self.set_get_packages_conf_from_reposerver(True if get_packages_conf_from_reposerver == 'true' else False)
                    
                    # If get_repos_from_reposerver is set
                    if 'GET_PROFILE_REPOS_FROM_REPOSERVER' in line:
                        get_repos_from_reposerver = line.split('=')[1].replace('"', '').strip()
                        self.set_get_repos_from_reposerver(True if get_repos_from_reposerver == 'true' else False)

                # Move old file
                Path('/etc/linupdate/modules/reposerver.conf').rename('/etc/linupdate/modules/reposerver.conf.migrated')

        except Exception as e:
            raise Exception('error while migrating old reposerver configuration file: ' + str(e))
