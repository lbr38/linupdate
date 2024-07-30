# coding: utf-8

# Import libraries
from pathlib import Path
from colorama import Fore, Style
import yaml
import ipaddress
import shutil

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
        # Quit if the config file already exists
        if Path(self.config_file).is_file():
            return
        
        print(' Generating Reposerver module configuration file')

        # Copy default configuration file
        try:
            shutil.copy2('/opt/linupdate/templates/modules/reposerver.template.yml', '/etc/linupdate/modules/reposerver.yml')
        except Exception as e:
            raise Exception('error while generating reposerver configuration file ' + self.config_file + ': ' + str(e))


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
        
        # Check if reposerver.ip is set
        if 'ip' not in configuration['reposerver']:
            raise Exception('reposerver.ip key not found in ' + self.config_file)

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

        # Check if agent.listen.interface is set
        if 'interface' not in configuration['agent']['listen']:
            raise Exception('agent.listen.interface key not found in ' + self.config_file)
            

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

        print(' Retrieve packages configuration from reposerver set to ' + str(value))


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

        print(' Retrieve repositories configuration from reposerver set to ' + str(value))


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

        print(' Remove existing repositories set to ' + str(value))


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
    #   Get global configuration from reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def get_reposerver_conf(self):
        print('  ▪ Getting reposerver configuration:', end=' ')

        # Get reposerver URL
        url = self.getUrl()

        # Get auth Id and token
        id = self.getId()
        token = self.getToken()
        
        # Do not print message if aknowledge request has been sent successfully
        # self.httpRequestController.quiet = True
        results = self.httpRequestController.get(url + '/api/v2/profile/server-settings', id, token)

        # Parse results

        # Check if IP has been send by the server
        if 'Ip' not in results[0]:
            raise Exception('reposerver did not send its IP address')

        # Check if package type has been send by the server
        if 'Package_type' not in results[0]:
            raise Exception('reposerver did not send its package type')

        # Set server IP
        self.set_server_ip(results[0]['Ip'])

        print('[' + Fore.GREEN + ' OK ' + Style.RESET_ALL + ']')


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
            self.appConfigController.set_exclude()

            # Then, set the new exclude list
            self.appConfigController.set_exclude(results[0]['Package_exclude'])

        # Packages to exclude on major version
        if results[0]['Package_exclude_major'] != "null":
            # First, clear the exclude major list
            self.appConfigController.set_exclude_major()

            # Then, set the new exclude major list
            self.appConfigController.set_exclude_major(results[0]['Package_exclude_major'])

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

            # Insert description at the top of the file, then content
            # Replace __ENV__ with current environment on the fly
            with open(reposRoot + '/' + result['filename'], 'w') as file:
                # Insert description
                file.write('# ' + result['description'] + '\n' + result['content'].replace('__ENV__', env) + '\n')

            # Set permissions
            Path(reposRoot + '/' + result['filename']).chmod(0o660)

            # Clear cache
            self.packageController.clear_cache()

        print('[' + Fore.GREEN + ' OK ' + Style.RESET_ALL + ']')


    #-----------------------------------------------------------------------------------------------
    #
    #   Set reposerver IP in configuration file
    #
    #-----------------------------------------------------------------------------------------------
    def set_server_ip(self, ip):
        # Check that IP is valid
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise Exception('invalid Reposerver IP address ' + ip)

        # Get current configuration
        configuration = self.get_conf()

        # Set server ip
        configuration['reposerver']['ip'] = ip

        # Write config file
        self.write_conf(configuration)

