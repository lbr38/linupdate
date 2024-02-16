# coding: utf-8

import os
import platform
import distro

class System:

    # Return true if current user is root or sudo
    def isRoot():
        if os.geteuid() == 0:
            return True

        return False

    def checkSystem():
        # Check if the program is running on Linux
        if (platform.system() != 'Linux'):
            print('This program only works on Linux')
            exit(1)

        # Check that the OS is supported
        if (distro.name() in ['Debian', 'Ubuntu', 'Kubuntu', 'Xubuntu', 'Linux Mint']):
            OS_FAMILY = 'Debian'
            
        elif (distro.name() in ['Centos', 'Fedora', 'Alma Linux', 'Rocky Linux']):
            OS_FAMILY = 'RedHat'

        else:
            print('This program does not support your Linux distribution "' + distro.name() + '" yet.')
            exit(1)

    # Return the OS family
    def getOsFamily():
        if (distro.name() in ['Debian', 'Ubuntu', 'Kubuntu', 'Xubuntu', 'Linux Mint']):
            return 'Debian'
            
        if (distro.name() in ['Centos', 'Fedora', 'Alma Linux', 'Rocky Linux']):
            return 'RedHat'

