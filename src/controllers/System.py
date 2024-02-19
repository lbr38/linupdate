# coding: utf-8

import os
import platform
import distro

class System:
    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return true if current user is root or sudo
    #
    #-------------------------------------------------------------------------------------------------------------------
    def isRoot(self):
        if os.geteuid() == 0:
            return True

        return False


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Check if the program is running on a supported Linux distribution
    #
    #-------------------------------------------------------------------------------------------------------------------
    def check(self):
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


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return the OS family
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getOsFamily(self):
        if (distro.name() in ['Debian', 'Ubuntu', 'Kubuntu', 'Xubuntu', 'Linux Mint']):
            return 'Debian'
            
        if (distro.name() in ['Centos', 'Fedora', 'Alma Linux', 'Rocky Linux']):
            return 'Redhat'


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return the OS name
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getOSName(self):
        return distro.name()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return the OS version
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getOsVersion(self):
        return distro.version()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return the kernel version
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getKernel(self):
        return platform.release()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return the virtualization type
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getVirtualization(self):
        # Detect virtualization type
        if os.path.isfile("/usr/sbin/virt-what"):
            virt = os.popen('/usr/sbin/virt-what').read().replace('\n', ' ')
            if not virt:
                virt = "No virtualization (bare-metal)"

        return virt
