# coding: utf-8

# Import libraries
from pathlib import Path
import shutil
import yaml
from colorama import Style

# Import classes
from src.controllers.Yaml import Yaml

class Config:
    def __init__(self):
        self.config_file = '/etc/linupdate/linupdate.yml'

    #-----------------------------------------------------------------------------------------------
    #
    #   Return linupdate configuration from config file
    #
    #-----------------------------------------------------------------------------------------------
    def get_conf(self):
        # Open main YAML config file:
        with open('/etc/linupdate/linupdate.yml') as stream:
            try:
                # Read YAML and return configuration
                main = yaml.safe_load(stream)

            except yaml.YAMLError as e:
                raise Exception(str(e))

        # Open update YAML config file:
        with open('/etc/linupdate/update.yml') as stream:
            try:
                # Read YAML and return configuration
                update = yaml.safe_load(stream)

            except yaml.YAMLError as e:
                raise Exception(str(e))

        # Merge and return both configurations
        configuration = {**main, **update}

        return configuration


    #-----------------------------------------------------------------------------------------------
    #
    #   Check if the config file exists and if it contains the required parameters
    #
    #-----------------------------------------------------------------------------------------------
    def check_conf(self):
        try:
            # Check if main config file exists
            if not Path(self.config_file).is_file():
                raise Exception('configuration file ' + self.config_file + ' is missing')

            # Check if update config file exists
            if not Path(self.config_file).is_file():
                raise Exception('configuration file ' + self.config_file + ' is missing')

            # Retrieve configuration
            configuration = self.get_conf()

            # Check if main is set
            if 'main' not in configuration:
                raise Exception('main key is missing in ' + self.config_file)

            # Check if main.profile is set
            if 'profile' not in configuration['main']:
                raise Exception('main.profile key is missing in ' + self.config_file)

            # Check if main.profile is not empty
            if configuration['main']['profile'] == None:
                raise Exception('main.profile key is empty in ' + self.config_file)

            # Check if main.environment is set
            if 'environment' not in configuration['main']:
                raise Exception('main.environment key is missing in ' + self.config_file)

            # Check if main.environment is not empty
            if configuration['main']['environment'] == None:
                raise Exception('main.environment key is empty in ' + self.config_file)

            # Check if main.mail is set
            if 'mail' not in configuration['main']:
                raise Exception('main.mail key is missing in ' + self.config_file)

            # Check if main.mail.enabled is set
            if 'enabled' not in configuration['main']['mail']:
                raise Exception('main.mail.enabled key is missing in ' + self.config_file)

            # Check if main.mail.enabled is set to True or False
            if configuration['main']['mail']['enabled'] not in [True, False]:
                raise Exception('main.mail.enabled key must be set to true or false in ' + self.config_file)

            # Check if main.mail.recipient is set
            if 'recipient' not in configuration['main']['mail']:
                raise Exception('main.mail.recipient key is missing in ' + self.config_file)

            # Check if modules is set
            if 'modules' not in configuration:
                raise Exception('modules key is missing in ' + self.config_file)

            # Check if modules.enabled is set
            if 'enabled' not in configuration['modules']:
                raise Exception('modules.enabled key is missing in ' + self.config_file)

            # Check if update is set
            if 'update' not in configuration:
                raise Exception('update key is missing in ' + self.config_file)

            # Check if update.exit_on_package_update_error is set
            if 'exit_on_package_update_error' not in configuration['update']:
                raise Exception('update.exit_on_package_update_error key is missing in ' + self.config_file)

            # Check if update.exit_on_package_update_error is set to True or False
            if configuration['update']['exit_on_package_update_error'] not in [True, False]:
                raise Exception('update.exit_on_package_update_error key must be set to true or false in ' + self.config_file)

            # Check if update.packages is set
            if 'packages' not in configuration['update']:
                raise Exception('update.packages key is missing in ' + self.config_file)

            # Check if update.packages.exclude section is set
            if 'exclude' not in configuration['update']['packages']:
                raise Exception('update.packages.exclude key is missing in ' + self.config_file)

            # Check if update.packages.exclude.always is set
            if 'always' not in configuration['update']['packages']['exclude']:
                raise Exception('update.packages.exclude.always key is missing in ' + self.config_file)

            # Check if update.packages.exclude.on_major_update is set
            if 'on_major_update' not in configuration['update']['packages']['exclude']:
                raise Exception('update.packages.exclude.on_major_update key is missing in ' + self.config_file)

            # Check if post_update.services section is set
            if 'services' not in configuration['post_update']:
                raise Exception('post_update.services key is missing in ' + self.config_file)

            # Check if post_update.services.restart is set in
            if 'restart' not in configuration['post_update']['services']:
                raise Exception('post_update.services.restart key is missing in ' + self.config_file)

        except Exception as e:
            raise Exception('Fatal configuration file error: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Generate config files if not exist
    #
    #-----------------------------------------------------------------------------------------------
    def generate_conf(self):
        # If main config file does not exist, generate it
        if not Path('/etc/linupdate/linupdate.yml').is_file():
            # Copy default configuration file
            try:
                shutil.copy2('/opt/linupdate/templates/linupdate.template.yml', '/etc/linupdate/linupdate.yml')
            except Exception as e:
                raise Exception('Could not generate configuration file /etc/linupdate/linupdate.yml: ' + str(e))

        # If update config file does not exist, generate it
        if not Path('/etc/linupdate/update.yml').is_file():
            # Copy default configuration file
            try:
                shutil.copy2('/opt/linupdate/templates/update.template.yml', '/etc/linupdate/update.yml')
            except Exception as e:
                raise Exception('Could not generate configuration file /etc/linupdate/update.yml: ' + str(e))
        
        # TODO: to remove in some time
        # If old linupdate (bash version) config file exists, migrate it
        if Path('/etc/linupdate/linupdate.conf').is_file():
            self.migrate_conf()


    #-----------------------------------------------------------------------------------------------
    #
    #   Write linupdate configuration to config file
    #
    #-----------------------------------------------------------------------------------------------
    def write_conf(self, configuration):
        # Use custom Yaml class to keep the order of the keys
        yaml = Yaml()

        main_config = {
            'main': {
                **configuration['main']
            },
            'modules': {
                **configuration['modules']
            }
        }

        update_config = {
            'update': {
                **configuration['update']
            },
            'post_update': {
                **configuration['post_update']
            }
        }

        # Write to main config file
        try:
            # TODO: When OS based on RHEL8 will not be used anymore, use 'sort_keys=False' to keep the order of the keys when writing the file
            # e.g. yaml.dump(main_config, file, default_flow_style=False, sort_keys=False)
            # But for now use the custom Yaml class to keep the order of the keys, and dict(main_config) to convert it back to a dict, because python3-yaml on RHEL8 does not support sort_keys=False
            yaml.write(main_config, '/etc/linupdate/linupdate.yml')
        except Exception as e:
            raise Exception('Could not write configuration file /etc/linupdate/linupdate.yml: ' + str(e))

        # Write to update config file
        try:
            yaml.write(update_config, '/etc/linupdate/update.yml')
        except Exception as e:
            raise Exception('Could not write configuration file /etc/linupdate/update.yml: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Print linupdate configuration to console (yaml format)
    #
    #-----------------------------------------------------------------------------------------------
    def show_config(self):
        try:
            # Open main YAML config file:
            with open('/etc/linupdate/linupdate.yml') as stream:
                try:
                    # Read YAML and return configuration
                    main = yaml.safe_load(stream)

                except yaml.YAMLError as e:
                    raise Exception(str(e))

            # Open update YAML config file:
            with open('/etc/linupdate/update.yml') as stream:
                try:
                    # Read YAML and return configuration
                    update = yaml.safe_load(stream)

                except yaml.YAMLError as e:
                    raise Exception(str(e))

            print(Style.BRIGHT + 'Global configuration: ' + Style.RESET_ALL, end='\n\n')

            try:
                print(yaml.dump(main, default_flow_style=False, sort_keys=False))
            except TypeError:
                print(yaml.dump(main, default_flow_style=False))
        
            print(Style.BRIGHT + 'Update configuration: ' + Style.RESET_ALL, end='\n\n')

            try:
                print(yaml.dump(update, default_flow_style=False, sort_keys=False))
            except TypeError:
                print(yaml.dump(update, default_flow_style=False))

            # If there are modules config files, print them
            if 'modules' in main:
                if 'enabled' in main['modules']:
                    for module in main['modules']['enabled']:
                        try:
                            print(Style.BRIGHT + 'Module ' + module + ' configuration: ' + Style.RESET_ALL, end='\n\n')

                            with open('/etc/linupdate/modules/' + module + '.yml') as stream:
                                try:
                                    module_conf = yaml.safe_load(stream)

                                except yaml.YAMLError as e:
                                    raise Exception(str(e))

                            try:
                                print(yaml.dump(module_conf, default_flow_style=False, sort_keys=False))
                            except TypeError:
                                print(yaml.dump(module_conf, default_flow_style=False))

                        except FileNotFoundError:
                            print('No configuration file found for module ' + module)
        
        except Exception as e:
            raise Exception('Could not show configuration: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Return linupdate profile from config file
    #
    #-----------------------------------------------------------------------------------------------
    def get_profile(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['main']['profile']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set linupdate profile in config file
    #
    #-----------------------------------------------------------------------------------------------
    def set_profile(self, profile):
        # Get current configuration
        configuration = self.get_conf()

        # Set profile
        configuration['main']['profile'] = profile

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Return linupdate environment from config file
    #
    #-----------------------------------------------------------------------------------------------
    def get_environment(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['main']['environment']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set linupdate environment in config file
    #
    #-----------------------------------------------------------------------------------------------
    def set_environment(self, environment):
        # Get current configuration
        configuration = self.get_conf()

        # Set environment
        configuration['main']['environment'] = environment

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable mail alert
    #
    #-----------------------------------------------------------------------------------------------
    def set_mail_enable(self, enabled: bool):
        # Get current configuration
        configuration = self.get_conf()

        # Set environment
        configuration['main']['mail']['enabled'] = enabled

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get mail alert status
    #
    #-----------------------------------------------------------------------------------------------
    def get_mail_enabled(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['main']['mail']['enabled']


    #-----------------------------------------------------------------------------------------------
    #
    #   Get mail recipient(s)
    #
    #-----------------------------------------------------------------------------------------------
    def set_mail_recipient(self, recipient: str = None):
        # Get current configuration
        configuration = self.get_conf()

        # If no recipient to set, set empty list
        if not recipient:
            configuration['main']['mail']['recipient'] = []

        else:
            # For each recipient, append it to the list if not already in
            for item in recipient.split(","):
                if item not in configuration['main']['mail']['recipient']:
                    # Append recipient
                    configuration['main']['mail']['recipient'].append(item)

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get mail recipient(s)
    #
    #-----------------------------------------------------------------------------------------------
    def get_mail_recipient(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['main']['mail']['recipient']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set mail smtp host
    #
    #-----------------------------------------------------------------------------------------------
    def set_mail_smtp_host(self, smtp_host: str):
        # Get current configuration
        configuration = self.get_conf()

        # Set smtp host
        configuration['main']['mail']['smtp_host'] = smtp_host

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get mail smtp host
    #
    #-----------------------------------------------------------------------------------------------
    def get_mail_smtp_host(self):
        smtp_host = 'localhost'

        # Get current configuration
        configuration = self.get_conf()

        # Get smtp host, if any, otherwise use localhost
        if 'smtp_host' in configuration['main']['mail']:
            smtp_host = configuration['main']['mail']['smtp_host']

        return smtp_host


    #-----------------------------------------------------------------------------------------------
    #
    #   Set mail smtp host port
    #
    #-----------------------------------------------------------------------------------------------
    def set_mail_smtp_port(self, smtp_port: int):
        # Get current configuration
        configuration = self.get_conf()

        # Set smtp port
        configuration['main']['mail']['smtp_port'] = smtp_port

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get mail smtp host port
    #
    #-----------------------------------------------------------------------------------------------
    def get_mail_smtp_port(self):
        smtp_port = 25

        # Get current configuration
        configuration = self.get_conf()

        # Get smtp port, if any, otherwise use 25
        if 'smtp_port' in configuration['main']['mail']:
            smtp_port = configuration['main']['mail']['smtp_port']

        return smtp_port


    #-----------------------------------------------------------------------------------------------
    #
    #   Set exit on package update error
    #
    #-----------------------------------------------------------------------------------------------
    def set_exit_on_package_update_error(self, exit_on_package_update_error: bool):
        # Get current configuration
        configuration = self.get_conf()

        # Set exit on package update error
        configuration['update']['exit_on_package_update_error'] = exit_on_package_update_error

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Return linupdate packages exclude list from config file
    #
    #-----------------------------------------------------------------------------------------------
    def get_exclusion(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['update']['packages']['exclude']['always']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set linupdate packages exclude list in config file
    #
    #-----------------------------------------------------------------------------------------------
    def set_exclusion(self, exclude: str = None):
        # Get current configuration
        configuration = self.get_conf()

        # If no package to exclude, set empty list
        if not exclude:
            configuration['update']['packages']['exclude']['always'] = []

        else:
            # For each package to exclude, append it to the list if not already in
            for item in exclude.split(","):
                if item not in configuration['update']['packages']['exclude']['always']:
                    # Append exclude
                    configuration['update']['packages']['exclude']['always'].append(item)

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Return linupdate packages exclude list on major update from config file
    #
    #-----------------------------------------------------------------------------------------------
    def get_major_exclusion(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['update']['packages']['exclude']['on_major_update']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set linupdate packages exclude list on major update in config file
    #
    #-----------------------------------------------------------------------------------------------
    def set_major_exclusion(self, exclude: str = None):
        # Get current configuration
        configuration = self.get_conf()

        # If no package to exclude, set empty list
        if not exclude:
            configuration['update']['packages']['exclude']['on_major_update'] = []

        else:
            # For each package to exclude, append it to the list if not already in
            for item in exclude.split(","):
                if item not in configuration['update']['packages']['exclude']['on_major_update']:
                    # Append exclude
                    configuration['update']['packages']['exclude']['on_major_update'].append(item)

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Get services to restart
    #
    #-----------------------------------------------------------------------------------------------
    def get_service_to_restart(self):
        # Get current configuration
        configuration = self.get_conf()

        return configuration['post_update']['services']['restart']


    #-----------------------------------------------------------------------------------------------
    #
    #   Set services to restart
    #
    #-----------------------------------------------------------------------------------------------
    def set_service_to_restart(self, services: str = None):
        # Get current configuration
        configuration = self.get_conf()

        # If no service to restart, set empty list
        if not services:
            configuration['post_update']['services']['restart'] = []

        else:
            # For each service to restart, append it to the list if not already in
            for item in services.split(","):
                if item not in configuration['post_update']['services']['restart']:
                    # Append service
                    configuration['post_update']['services']['restart'].append(item)

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Append a module to the enabled list
    #
    #-----------------------------------------------------------------------------------------------
    def append_module(self, module):
        # Get current configuration
        configuration = self.get_conf()

        # Add module to enabled list
        configuration['modules']['enabled'].append(module)

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Remove a module from the enabled list
    #
    #-----------------------------------------------------------------------------------------------
    def remove_module(self, module):
        # Get current configuration
        configuration = self.get_conf()

        # Remove module from enabled list
        configuration['modules']['enabled'].remove(module)

        # Write config file
        self.write_conf(configuration)


    #-----------------------------------------------------------------------------------------------
    #
    #   Migration of old linupdate configuration file
    #
    #-----------------------------------------------------------------------------------------------
    def migrate_conf(self):
        # Old config file are like ini file

        print(' Detected old configuration file /etc/linupdate/linupdate.conf, migrating...')

        try:
            # Open old config file
            with open('/etc/linupdate/linupdate.conf', 'r') as file:
                lines = file.readlines()

                for line in lines:
                    # If profile is set, set it in the new config file
                    if 'PROFILE=' in line:
                        profile = line.split('=')[1].replace('"', '').strip()
                        self.set_profile(profile)

                    # If environment is set, set it in the new config file
                    if 'ENV=' in line:
                        environment = line.split('=')[1].replace('"', '').strip()
                        self.set_environment(environment)

                    # If mail alert is enabled, set it in the new config file
                    if 'MAIL_ENABLED=' in line:
                        mail_alert = line.split('=')[1].replace('"', '').strip()
                        if (mail_alert in ['true', 'True']):
                            self.set_mail_enable(True)
                        else:
                            self.set_mail_enable(False)

                    # If mail recipient is set, set it in the new config file
                    if 'MAIL_RECIPIENT=' in line:
                        mail_recipient = line.split('=')[1].replace('"', '').strip()
                        self.set_mail_recipient(mail_recipient)
                
                    # If exclude major is set, set it in the new config file
                    if 'EXCLUDE_MAJOR=' in line:
                        major_exclusion = line.split('=')[1].replace('"', '').strip()
                        self.set_major_exclusion(major_exclusion)

                    # If exclude is set, set it in the new config file
                    if 'EXCLUDE=' in line:
                        exclusion = line.split('=')[1].replace('"', '').strip()
                        self.set_exclusion(exclusion)

                    # If services to restart are set, set them in the new config file
                    if 'SERVICE_RESTART=' in line:
                        services = line.split('=')[1].replace('"', '').strip()
                        self.set_service_to_restart(services)

                # Move old file
                shutil.move('/etc/linupdate/linupdate.conf', '/etc/linupdate/linupdate.conf.migrated')
        
        except Exception as e:
            raise Exception('Could not migrate configuration file /etc/linupdate/linupdate.conf: ' + str(e))
