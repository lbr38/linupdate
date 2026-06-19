# coding: utf-8

# Import libraries
import os
import tempfile
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
        temp_file_path = None

        try:
            target_dir = os.path.dirname(file) or '.'

            with tempfile.NamedTemporaryFile('w', dir=target_dir, delete=False) as yaml_file:
                temp_file_path = yaml_file.name

                try:
                    yaml.dump(data, yaml_file, default_flow_style=False, sort_keys=False)

                except TypeError:
                    yaml.dump(data, yaml_file, default_flow_style=False)

                # Ensure content is persisted before replacing destination
                yaml_file.flush()
                os.fsync(yaml_file.fileno())

            # Atomic replace on same filesystem
            os.replace(temp_file_path, file)

        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

            raise Exception(e)
