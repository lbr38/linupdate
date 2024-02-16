# coding: utf-8

# Import libraries
import yaml

# Custom class to handle yaml files and keep the order of the keys when writing the file
# Modern version of python3-yaml comes with 'sort_keys=False' option to keep the order of the keys, but
# this is not available on RHEL8 based OS (python3-yaml is too old)
# So this class is a workaround to keep the order of the keys when writing the file

# Yaml inherits from dict
class Yaml():
    #-----------------------------------------------------------------------------------------------
    #
    #   Write data to a yaml file
    #
    #-----------------------------------------------------------------------------------------------
    def write(self, data, file: str):
        try:
            with open(file, 'w') as yaml_file:
                try:
                    yaml.dump(data, yaml_file, default_flow_style=False, sort_keys=False)

                except TypeError:
                    yaml.dump(data, yaml_file, default_flow_style=False)
        except Exception as e:
            raise Exception(e)
