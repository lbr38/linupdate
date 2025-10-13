# coding: utf-8

# Import libraries
import json
import requests
from colorama import Fore, Style

# Import classes
from src.controllers.App.Utils import Utils

class HttpRequest:
    def __init__(self):
        self.quiet = False

    #-----------------------------------------------------------------------------------------------
    #
    #   GET request
    #
    #-----------------------------------------------------------------------------------------------
    def get(self, url: str, id: str, token: str, connectionTimeout: int = 5, readTimeout: int = 3):
        # If an Id and a token are provided, add them to the URL
        if id != "" and token != "":
            response = requests.get(url,
                                    headers = {'Authorization': 'Host ' + id + ':' + token},
                                    timeout = (connectionTimeout, readTimeout))
        else:
            response = requests.get(url, timeout = (connectionTimeout, readTimeout))

        # Parse response and return results if 200
        return self.request_parse_result(response)


    #-----------------------------------------------------------------------------------------------
    #
    #   POST request with API key
    #
    #-----------------------------------------------------------------------------------------------
    def post_token(self, url: str, apiKey: str, data, connectionTimeout: int = 5, readTimeout: int = 3):
        # Send POST request to URL with API key
        response = requests.post(url,
                                 data = json.dumps(data),
                                 headers = {'Authorization': 'Bearer ' + apiKey, 'Content-Type': 'application/json'},
                                 timeout = (connectionTimeout, readTimeout))

        del data, apiKey, url

        # Parse response and return results if 200
        return self.request_parse_result(response)


    #-----------------------------------------------------------------------------------------------
    #
    #   PUT request with Id and token
    #
    #-----------------------------------------------------------------------------------------------
    def put(self, url: str, id: str, token: str, data, connectionTimeout: int = 5, readTimeout: int = 3):
        # Send PUT request to URL with Id and token
        response = requests.put(url,
                                data = json.dumps(data),
                                headers = {'Authorization': 'Host ' + id + ':' + token},
                                timeout = (connectionTimeout, readTimeout))

        del data, id, token, url

        # Parse response and return results if 200
        return self.request_parse_result(response)


    #-----------------------------------------------------------------------------------------------
    #
    #   DELETE request with Id and token
    #
    #-----------------------------------------------------------------------------------------------
    def delete(self, url: str, id: str, token: str, connectionTimeout: int = 5, readTimeout: int = 3):
        # Send DELETE request to URL with Id and token
        response = requests.delete(url,
                                   headers = {'Authorization': 'Host ' + id + ':' + token},
                                   timeout = (connectionTimeout, readTimeout))

        del id, token, url

        # Parse response and return results if 200
        return self.request_parse_result(response)


    #-----------------------------------------------------------------------------------------------
    #
    #   Parse request result
    #
    #-----------------------------------------------------------------------------------------------
    def request_parse_result(self, response):
        myUtils = Utils()

        # Check is response is OK (200)
        try:
            response.raise_for_status()

            # Print response message if not quiet
            if not self.quiet:
                # If response is a JSON with a 'message' key, then print it
                if myUtils.is_json(response.text) and 'message' in response.json():
                    for message in response.json()['message']:
                        print('  ' + Fore.GREEN + '✔' + Style.RESET_ALL + ' ' + message)

            # If response is a JSON with a 'results' key, return it
            if myUtils.is_json(response.text) and 'results' in response.json():
                return response.json()['results']

            # Else return response
            return response
        except requests.exceptions.HTTPError as e:
            # If response is a JSON with a 'message_error' key, return it
            if myUtils.is_json(response.text) and 'message_error' in response.json():
                for message in response.json()['message_error']:
                    print('  ' + Fore.YELLOW + '✕' + Style.RESET_ALL + ' ' + message)
                    raise Exception()
            else:
                raise Exception('HTTP request error: ' + str(e))
