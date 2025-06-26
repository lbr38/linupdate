# coding: utf-8

# Import libraries
import os
import subprocess
import platform
import distro

class System:
    #-----------------------------------------------------------------------------------------------
    #
    #   Return true if current user is root or sudo
    #
    #-----------------------------------------------------------------------------------------------
    def is_root(self):
        if os.geteuid() == 0:
            return True

        return False


    #-----------------------------------------------------------------------------------------------
    #
    #   Check if the program is running on a supported Linux distribution
    #
    #-----------------------------------------------------------------------------------------------
    def check(self):
        # Check if the program is running on Linux
        if (platform.system() != 'Linux'):
            raise Exception('This program only works on Linux')

        # Check if the program is running on a supported Linux distribution (will raise an exception if not supported)
        self.get_os_family()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the OS family
    #
    #-----------------------------------------------------------------------------------------------
    def get_os_family(self):
        if (distro.name() in ['Debian GNU/Linux', 'Debian', 'Ubuntu', 'Kubuntu', 'Xubuntu', 'Linux Mint']):
            return 'Debian'

        if (distro.name() in ['Red Hat Enterprise Linux', 'CentOS Linux', 'CentOS Stream', 'Fedora', 'Alma Linux', 'Rocky Linux', 'Oracle Linux Server']):
            return 'Redhat'

        raise Exception('This program does not support your Linux distribution "' + distro.name() + '" yet.')


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the OS name
    #
    #-----------------------------------------------------------------------------------------------
    def get_os_name(self):
        return distro.name()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the OS version
    #
    #-----------------------------------------------------------------------------------------------
    def get_os_version(self):
        return distro.version()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the kernel version
    #
    #-----------------------------------------------------------------------------------------------
    def get_kernel(self):
        return platform.release()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the architecture
    #
    #-----------------------------------------------------------------------------------------------
    def get_arch(self):
        return platform.machine()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the virtualization type
    #
    #-----------------------------------------------------------------------------------------------
    def get_virtualization(self):
        # Detect virtualization type
        if os.path.isfile("/usr/sbin/virt-what"):
            virt = os.popen('/usr/sbin/virt-what').read().replace('\n', ' ')
            if not virt:
                virt = "Bare-metal"

        return virt


    #-----------------------------------------------------------------------------------------------
    #
    #   Return True if a reboot is required
    #
    #-----------------------------------------------------------------------------------------------
    def reboot_required(self):
        if self.get_os_family() == 'Debian' and os.path.isfile('/var/run/reboot-required'):
            return True

        if self.get_os_family() == 'Redhat' and os.path.isfile('/usr/bin/needs-restarting'):
            result = subprocess.run(
                ["/usr/bin/needs-restarting", "-r"],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True # Alias of 'text = True'
            )

            if result.returncode != 0:
                return True

        return False
            