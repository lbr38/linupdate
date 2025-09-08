# coding: utf-8

# Import libraries
import os
import subprocess
import platform
import distro
import psutil

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
    #   Return the host uptime in seconds
    #
    #-----------------------------------------------------------------------------------------------
    def get_uptime(self):
        try:
            return psutil.boot_time()
        except Exception as e:
            raise Exception('could not get system uptime: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the CPU information
    #
    #-----------------------------------------------------------------------------------------------
    def get_cpu_info(self):
        cpu_info = 'unknown'

        # Get 'model name' line from /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        cpu_info = line.split(':')[1].strip()
                        break
        except Exception as e:
            raise Exception('could not get CPU info: ' + str(e))

        # Get number of CPU cores
        try:
            cpu_cores = os.cpu_count()
            if cpu_cores:
                cpu_info += ' (' + str(cpu_cores) + ' cores)'
        except Exception as e:
            raise Exception('could not get number of CPU cores: ' + str(e))

        return cpu_info
    

    #-----------------------------------------------------------------------------------------------
    #
    #   Return the total memory in GB
    #
    #-----------------------------------------------------------------------------------------------
    def get_memory_info(self):
        try:
            mem = psutil.virtual_memory()
            total_mem_gb = mem.total / (1024 ** 3)  # Convert bytes to GB
            return f"{total_mem_gb:.2f} GB"
        except Exception as e:
            raise Exception('could not get memory info: ' + str(e))


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
            