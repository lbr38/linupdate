# coding: utf-8

# Import libraries
import argparse
from colorama import Fore, Style
from tabulate import tabulate

# Import classes
from src.controllers.Exit import Exit
from src.controllers.Module.Reposerver.Config import Config
from src.controllers.Module.Reposerver.Status import Status
from src.controllers.ArgsException import ArgsException

class Args:
    def __init__(self):
        self.exitController   = Exit()
        self.configController = Config()

    #-----------------------------------------------------------------------------------------------
    #
    #   Parse arguments
    #
    #-----------------------------------------------------------------------------------------------
    def parse(self, module_args):
        try:
            # Parse arguments
            parser = argparse.ArgumentParser(add_help=False)

            # Define valid arguments
            # Help
            parser.add_argument("--help", "-h", action="store_true", default="null")
            # URL
            parser.add_argument("--url", action="store", nargs='?', default="null")
            # API key
            parser.add_argument("--api-key", action="store", nargs='?', default="null")
            # IP
            parser.add_argument("--ip", action="store", nargs='?', default="null")

            # Enable or disable packages configuration update
            parser.add_argument("--get-packages-conf-from-reposerver", action="store", nargs='?', default="null")
            # Enable or disable repos update
            parser.add_argument("--get-repos-from-reposerver", action="store", nargs='?', default="null")
            # Enable or disable the removing of existing repos
            parser.add_argument("--remove-existing-repos", action="store", nargs='?', default="null")
            # Source repo format
            parser.add_argument("--source-repo-format", action="store", nargs='?', default="null")

            # Agent enable
            parser.add_argument("--agent-enable", action="store", nargs='?', default="null")
            # Agent listen enable
            parser.add_argument("--agent-listen-enable", action="store", nargs='?', default="null")

            # Register to reposerver
            parser.add_argument("--register", action="store_true", default="null")
            # Unregister from server
            parser.add_argument("--unregister", action="store_true", default="null")

            # Retrieve profile packages configuration from reposerver
            parser.add_argument("--get-profile-packages-conf", action="store_true", default="null")
            # Retrieve profile repositories from reposerver
            parser.add_argument("--get-profile-repos", action="store_true", default="null")

            # Send general info
            parser.add_argument("--send-general-info", action="store_true", default="null")
            # Send packages status
            parser.add_argument("--send-packages-info", action="store_true", default="null")
            # Send all info
            parser.add_argument("--send-all-info", action="store_true", default="null")

            # If no arguments are passed, print help
            if not module_args:
                self.help()
                self.exitController.clean_exit(0, False)

            # Else, parse arguments
            args, remaining_args = parser.parse_known_args(module_args)

            # If there are remaining arguments, print help and raise an exception
            if remaining_args:
                self.help()
                raise ArgsException('Unknown argument(s): ' + str(remaining_args))

        # Catch exceptions
        # Either ArgsException or Exception, it will always raise an ArgsException to the main script, this to avoid sending an email when an argument error occurs
        except ArgsException as e:
            raise ArgsException(str(e))
        except Exception as e:
            raise ArgsException(str(e))

        try:
            #
            # If --url param has been set
            #
            if args.url != "null":
                # If a URL is set (not 'None'), change the app URL
                if args.url:
                    # Set new URL
                    self.configController.setUrl(args.url)

                    # Print URL change
                    print(' Reposerver URL set to ' + Fore.GREEN + args.url + Style.RESET_ALL, end='\n\n')
                # Else print the current URL
                else:
                    print(' Current reposerver URL: ' + Fore.GREEN + self.configController.getUrl() + Style.RESET_ALL, end='\n\n')
                self.exitController.clean_exit(0, False)

            #
            # If --api-key param has been set
            #
            if args.api_key != "null":
                Args.api_key = args.api_key

            #
            # If --ip param has been set
            #
            if args.ip != "null":
                Args.ip = args.ip

            #
            # If --agent-enable param has been set
            #
            if args.agent_enable != "null":
                if args.agent_enable == 'true':
                    self.configController.set_agent_enable(True)
                else:
                    self.configController.set_agent_enable(False)

                self.exitController.clean_exit(0, False)

            #
            # If --agent-listen-enable param has been set
            #
            if args.agent_listen_enable != "null":
                if args.agent_listen_enable == 'true':
                    self.configController.set_agent_listen(True)
                else:
                    self.configController.set_agent_listen(False)

                self.exitController.clean_exit(0, False)

            #
            # If --get-packages-conf-from-reposerver param has been set
            #
            if args.get_packages_conf_from_reposerver != "null":
                if args.get_packages_conf_from_reposerver == 'true':
                    self.configController.set_get_packages_conf_from_reposerver(True)
                else:
                    self.configController.set_get_packages_conf_from_reposerver(False)
                self.exitController.clean_exit(0, False)

            #
            # If --get-repos-from-reposerver param has been set
            #
            if args.get_repos_from_reposerver != "null":
                if args.get_repos_from_reposerver == 'true':
                    self.configController.set_get_repos_from_reposerver(True)
                else:
                    self.configController.set_get_repos_from_reposerver(False)
                self.exitController.clean_exit(0, False)

            #
            # If --remove-existing-repos param has been set
            #
            if args.remove_existing_repos != "null":
                if args.remove_existing_repos == 'true':
                    self.configController.set_remove_existing_repos(True)
                else:
                    self.configController.set_remove_existing_repos(False)
                self.exitController.clean_exit(0, False)

            #
            # If --source-repo-format param has been set
            #
            if args.source_repo_format != "null":
                if not args.source_repo_format:
                    print(' Current source repository format: ' + Fore.GREEN + self.configController.get_source_repo_format() + Style.RESET_ALL, end='\n\n')
                else:
                    # Set the source repo format
                    self.configController.set_source_repo_format(args.source_repo_format)
                    print(' Source repository format set to ' + Fore.GREEN + args.source_repo_format + Style.RESET_ALL, end='\n\n')

                self.exitController.clean_exit(0, False)

            #
            # If --register param has been set
            #
            if args.register != "null" and args.register:
                # Register to the URL with the API key and IP (could be "null" if not set)
                self.configController.register(args.api_key, args.ip)
                self.exitController.clean_exit(0, False)

            #
            # If --unregister param has been set
            #
            if args.unregister != "null" and args.unregister:
                # Unregister from the reposerver
                self.configController.unregister()
                self.exitController.clean_exit(0, False)

            #
            # If --get-profile-packages-conf param has been set
            #
            if args.get_profile_packages_conf != "null" and args.get_profile_packages_conf:
                # Get profile packages configuration
                self.configController.get_profile_packages_conf()
                self.exitController.clean_exit(0, False)

            #
            # If --get-profile-repos param has been set
            #
            if args.get_profile_repos != "null" and args.get_profile_repos:
                # Get profile repositories
                self.configController.get_profile_repos()
                self.exitController.clean_exit(0, False)

            #
            # If --send-general-info param has been set
            #
            if args.send_general_info != "null" and args.send_general_info:
                # Send general info
                status = Status()
                status.send_general_info()
                self.exitController.clean_exit(0, False)

            #
            # If --send-packages-info param has been set
            #
            if args.send_packages_info != "null" and args.send_packages_info:
                # Send packages info
                status = Status()
                status.send_packages_info()
                self.exitController.clean_exit(0, False)

            #
            # If --send-all-info param has been set
            #
            if args.send_all_info != "null" and args.send_all_info:
                # Send full status including general status, available packages status, installed packages status and full history
                status = Status()
                status.send_general_info()
                status.send_packages_info()
                self.exitController.clean_exit(0, False)

        # Catch exceptions
        # Either ArgsException or Exception, it will always raise an ArgsException to the main script, this to avoid sending an email when an argument error occurs
        except ArgsException as e:
            raise ArgsException(str(e))
        except Exception as e:
            raise ArgsException(str(e))

    #-----------------------------------------------------------------------------------------------
    #
    #   Print help
    #
    #-----------------------------------------------------------------------------------------------
    def help(self):
        try:
            table = []
            options = [
                {
                    'args': [
                        '--help',
                        '-h'
                    ],
                    'description': 'Show reposerver module help',
                },
                {
                    'title': 'Configuring reposerver'
                },
                {
                    'args': [
                        '--url',
                    ],
                    'option': 'URL',
                    'description': 'Specify target reposerver URL',
                },
                {
                    'args': [
                        '--api-key',
                    ],
                    'option': 'APIKEY',
                    'description': 'Specify API key to authenticate to the reposerver',
                },
                {
                    'args': [
                        '--ip',
                    ],
                    'option': 'IP',
                    'description': 'Specify an alternative local IP address to use to authenticate to the reposerver (default: will use the public IP address)',
                },
                {
                    'args': [
                        '--register',
                    ],
                    'description': 'Register this host to the reposerver (--api-key required)'
                },
                {
                    'args': [
                        '--unregister',
                    ],
                    'description': 'Unregister this host from the reposerver'
                },
                {
                    'title': 'Configuring retrieval from reposerver (using configured profile)'
                },
                {
                    'args': [
                        '--get-packages-conf-from-reposerver',
                    ],
                    'option': 'true|false',
                    'description': 'If enabled, packages exclusions will be retrieved from the reposerver',
                },
                {
                    'args': [
                        '--get-repos-from-reposerver',
                    ],
                    'option': 'true|false',
                    'description': 'If enabled, repositories configuration will be retrieved from the reposerver',
                },
                {
                    'args': [
                        '--remove-existing-repos',
                    ],
                    'option': 'true|false',
                    'description': 'If enabled, existing repositories will be removed before adding the new ones',
                },
                {
                    'args': [
                        '--source-repo-format'
                    ],
                    'option': 'standard, deb822',
                    'description': 'Specify the source repository format to use under /etc/apt/sources.list.d/ (for Debian based OS only) (default: standard)',
                },
                {
                    'title': 'Retrieving data from reposerver'
                },
                {
                    'args': [
                        '--get-profile-packages-conf',
                    ],
                    'description': 'Get profile packages configuration from reposerver'
                },
                {
                    'args': [
                        '--get-profile-repos',
                    ],
                    'description': 'Get profile repositories from reposerver'
                },
                {
                    'title': 'Sending data to reposerver'
                },
                {
                    'args': [
                        '--send-general-info',
                    ],
                    'description': 'Send host\'s general informations (OS, version, kernel..) to the reposerver'
                },
                {
                    'args': [
                        '--send-packages-info',
                    ],
                    'description': 'Send this host\'s packages informations to the reposerver (available package updates, installed packages)'
                },
                {
                    'args': [
                        '--send-all-info',
                    ],
                    'description': 'Send all of the previous informations to the reposerver'
                },
                {
                    'args': [
                        '--agent-enable',
                    ],
                    'option': 'true|false',
                    'description': 'Enable reposerver module agent. This agent will regularly send informations about this host to reposerver (global informations, packages informations...)',
                },
                {
                    'args': [
                        '--agent-listen-enable',
                    ],
                    'option': 'true|false',
                    'description': 'Enable or disable agent listening for requests coming from the reposerver',
                }
            ]

            # Add options to table
            for option in options:
                # If option is a title, just print it
                if 'title' in option:
                    table.append(['', Style.BRIGHT + '\n' + option['title'] + '\n' + Style.RESET_ALL, ''])
                    continue

                # If option has multiple arguments, join them
                if len(option['args']) > 1:
                    args_str = ', '.join(option['args'])
                else:
                    args_str = option['args'][0]

                if 'option' in option:
                    args_str += Style.DIM + ' [' + option['option'] + ']' + Style.RESET_ALL

                table.append(['', args_str, option['description']])


            print(' Available options:', end='\n\n')

            # Print table
            print(tabulate(table, headers=["", "Name", "Description"], tablefmt="simple"), end='\n\n')

            print(' Usage: linupdate --mod-configure reposerver [OPTIONS]', end='\n\n')
        # Catch exceptions
        # Either ArgsException or Exception, it will always raise an ArgsException to the main script, this to avoid sending an email when an argument error occurs
        except ArgsException as e:
            raise ArgsException('Printing help error: ' + str(e))
        except Exception as e:
            raise ArgsException('Printing help error: ' + str(e))
