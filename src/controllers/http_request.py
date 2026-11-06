# coding: utf-8

"""HTTP requests to the reposerver API."""

# Import libraries
import json
import requests
import urllib3
from colorama import Fore, Style

# Import classes
from src.controllers.app.utils import Utils
from src.controllers.linupdate_exception import LinupdateException

class HttpRequest:
    """Send HTTP requests and parse the JSON responses."""
    def __init__(self, verify_ssl: bool = True):
        self.quiet = False
        self.verify_ssl = verify_ssl

        # If SSL verification is disabled, disable warnings
        if not self.verify_ssl:
            urllib3.disable_warnings()

    def get(self, url: str, auth_id: str, token: str, connection_timeout: int = 5, read_timeout: int = 3):
        """GET request"""
        # If an Id and a token are provided, add them to the URL
        if auth_id != "" and token != "":
            response = requests.get(url,
                                    headers = {'Authorization': 'Host ' + auth_id + ':' + token},
                                    timeout = (connection_timeout, read_timeout),
                                    verify = self.verify_ssl)
        else:
            response = requests.get(url, timeout = (connection_timeout, read_timeout), verify = self.verify_ssl)

        # Parse response and return results if 200
        return self.request_parse_result(response)


    def post_token(self, url: str, api_key: str, data, connection_timeout: int = 5, read_timeout: int = 3):
        """POST request with API key"""
        # Send POST request to URL with API key
        response = requests.post(url,
                                 data = json.dumps(data),
                                 headers = {'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'},
                                 timeout = (connection_timeout, read_timeout),
                                 verify = self.verify_ssl)

        del data, api_key, url

        # Parse response and return results if 200
        return self.request_parse_result(response)

    def put(self, url: str, auth_id: str, token: str, data, connection_timeout: int = 5, read_timeout: int = 3):
        """PUT request with Id and token"""
        # Send PUT request to URL with Id and token

        response = requests.put(url,
                                data = json.dumps(data),
                                headers = {'Authorization': 'Host ' + auth_id + ':' + token},
                                timeout = (connection_timeout, read_timeout),
                                verify = self.verify_ssl)

        del data, auth_id, token, url

        # Parse response and return results if 200
        return self.request_parse_result(response)


    def delete(self, url: str, auth_id: str, token: str, connection_timeout: int = 5, read_timeout: int = 3):
        """DELETE request with Id and token"""
        # Send DELETE request to URL with Id and token
        response = requests.delete(url,
                                   headers = {'Authorization': 'Host ' + auth_id + ':' + token},
                                   timeout = (connection_timeout, read_timeout),
                                   verify = self.verify_ssl)

        del auth_id, token, url

        # Parse response and return results if 200
        return self.request_parse_result(response)


    def download(self, url: str, path: str, connection_timeout: int = 5, read_timeout: int = 3):
        """Download file from URL"""
        # Send GET request to URL
        response = requests.get(url, timeout = (connection_timeout, read_timeout), verify = self.verify_ssl)

        # Parse response and return results if 200
        self.request_parse_result(response)

        # Write content to file
        with open(path, 'wb') as file:
            file.write(response.content)

        del path, url, response


    def request_parse_result(self, response):
        """Parse request result"""
        my_utils = Utils()

        # Check is response is OK (200)
        try:
            response.raise_for_status()

            # Print response message if not quiet
            if not self.quiet:
                # If response is a JSON with a 'message' key, then print it
                if my_utils.is_json(response.text) and 'message' in response.json():
                    for message in response.json()['message']:
                        print('  ' + Fore.GREEN + '✔' + Style.RESET_ALL + ' ' + message)

            # If response is a JSON with a 'results' key, return it
            if my_utils.is_json(response.text) and 'results' in response.json():
                return response.json()['results']

            # Else return response
            return response
        except requests.exceptions.HTTPError as e:
            # If response is a JSON with a 'message_error' key, return it
            if my_utils.is_json(response.text) and 'message_error' in response.json():
                for message in response.json()['message_error']:
                    print('  ' + Fore.YELLOW + '✕' + Style.RESET_ALL + ' ' + message)
                    raise LinupdateException() from e
            else:
                raise LinupdateException('HTTP request error: ' + str(e)) from e
