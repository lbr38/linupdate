# coding: utf-8

# Import libraries
from colorama import Fore, Style
import ipaddress
import socket

# Import classes
from src.controllers.Module.Reposerver.Config import Config
from src.controllers.HttpRequest import HttpRequest

class Register:
    def __init__(self):
        self.configController = Config()
        self.httpRequestController = HttpRequest()

    #---------------------------------------------------------------------------------------------------
    #
    #   Register to reposerver
    #
    #---------------------------------------------------------------------------------------------------
    def register(self, api_key: str, ip: str):
        # Get Reposerver URL
        url = self.configController.getUrl()

        # Check if URL is not null
        if url == '':
            raise Exception('you must configure the target reposerver URL [--url <url>]')

        print('  ▪ Registering to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

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
            'hostname': socket.gethostname()
        }

        try:
            results = self.httpRequestController.post_token(url + '/api/v2/host/registering', api_key, data)
        except Exception as e:
            raise Exception('Registering failed')

        # If registration is successful, the server will return an Id and a token, set Id and token in configuration
        self.configController.setId(results['id'])
        self.configController.setToken(results['token'])


    #---------------------------------------------------------------------------------------------------
    #
    #   Unregister from reposerver
    #
    #---------------------------------------------------------------------------------------------------
    def unregister(self):
        # Get Reposerver URL
        url = self.configController.getUrl()

        # Check if URL is not null
        if url == '':
            raise Exception('you must configure the target Reposerver URL [--url <url>]')

        print('  ▪ Unregistering from ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        # Get Id and token from configuration
        id = self.configController.getId()
        token = self.configController.getToken()

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
