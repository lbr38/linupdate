# coding: utf-8

"""System information (OS, kernel, hardware, network) and system actions."""

# Import libraries
import os
import subprocess
import platform
import socket
import distro
import psutil
from src.controllers.linupdate_exception import LinupdateException

class System:
    """System information and actions."""
    def is_root(self):
        """Return true if current user is root or sudo"""
        if os.geteuid() == 0:
            return True

        return False


    def check(self):
        """Check if the program is running on a supported Linux distribution"""
        # Check if the program is running on Linux
        if platform.system() != 'Linux':
            raise LinupdateException('This program only works on Linux')

        # Check if the program is running on a supported Linux distribution (will raise an exception if not supported)
        self.get_os_family()


    def get_os_family(self):
        """Return the OS family"""
        if (distro.name() in ['Debian GNU/Linux', 'Debian', 'Ubuntu', 'Kubuntu', 'Xubuntu', 'Linux Mint']):
            return 'Debian'

        if (distro.name() in ['Red Hat Enterprise Linux', 'CentOS Linux', 'CentOS Stream', 'Fedora', 'Fedora Linux', 'AlmaLinux', 'Alma Linux', 'RockyLinux', 'Rocky Linux', 'Oracle Linux Server']):
            return 'Redhat'

        raise LinupdateException('This program does not support your Linux distribution "' + distro.name() + '" yet.')


    def get_os_name(self):
        """Return the OS name"""
        return distro.name()


    def get_os_version(self):
        """Return the OS version"""
        return distro.version()


    def get_kernel(self):
        """Return the kernel version"""
        return platform.release()


    def get_arch(self):
        """Return the architecture"""
        return platform.machine()


    def get_virtualization(self):
        """Return the virtualization type"""
        # Detect virtualization type
        if os.path.isfile("/usr/sbin/virt-what"):
            virt = os.popen('/usr/sbin/virt-what').read().replace('\n', ' ')
            if not virt:
                virt = "Bare-metal"

        return virt


    def get_uptime(self):
        """Return the host uptime in seconds"""
        try:
            return psutil.boot_time()
        except Exception as e:
            raise LinupdateException('could not get system uptime: ' + str(e)) from e


    def get_cpu_info(self):
        """Return the CPU information"""
        cpu_info = 'unknown'

        # Get 'model name' line from /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r', encoding='utf-8') as f:
                for line in f:
                    if 'model name' in line:
                        cpu_info = line.split(':')[1].strip()
                        break
        except Exception as e:
            raise LinupdateException('could not get CPU info: ' + str(e)) from e

        # Get number of CPU cores
        try:
            cpu_cores = os.cpu_count()
            if cpu_cores:
                cpu_info += ' (' + str(cpu_cores) + ' cores)'
        except Exception as e:
            raise LinupdateException('could not get number of CPU cores: ' + str(e)) from e

        return cpu_info


    def get_memory_info(self):
        """Return the total memory in GB"""
        try:
            mem = psutil.virtual_memory()
            total_mem_gb = mem.total / (1024 ** 3)  # Convert bytes to GB
            return f"{total_mem_gb:.2f} GB"
        except Exception as e:
            raise LinupdateException('could not get memory info: ' + str(e)) from e


    def get_network_info(self):
        """Returns a dictionary with network interfaces as keys and their IP and MAC addresses as values."""
        network = {}

        try:
            addrs = psutil.net_if_addrs()

            # Main IP is the source address the kernel would use to reach the Internet
            main_ip = None
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    # UDP connect() sends no packet, it only triggers the route lookup
                    s.connect(('1.1.1.1', 80))
                    main_ip = s.getsockname()[0]
            except OSError:
                pass

            for iface, addr_list in addrs.items():
                network[iface] = {'ipv4': None, 'ipv6': None, 'mac': None, 'main': False}
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        # Do not overwrite the main IP if the interface has several IPv4 addresses
                        if not network[iface]['main']:
                            network[iface]['ipv4'] = addr.address
                        if addr.address == main_ip:
                            network[iface]['main'] = True
                    elif addr.family == socket.AF_INET6:
                        network[iface]['ipv6'] = addr.address
                    elif addr.family == psutil.AF_LINK:
                        network[iface]['mac'] = addr.address
        except Exception as e:
            raise LinupdateException('could not get network info: ' + str(e)) from e

        return network


    def reboot_required(self):
        """Return True if a reboot is required"""
        if self.get_os_family() == 'Debian' and os.path.isfile('/var/run/reboot-required'):
            return True

        if self.get_os_family() == 'Redhat' and os.path.isfile('/usr/bin/needs-restarting'):
            result = subprocess.run(
                ["/usr/bin/needs-restarting", "-r"],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True, # Alias of 'text = True'
                check = False
            )

            if result.returncode != 0:
                return True

        return False


    def reboot(self):
        """Reboot the system"""
        try:
            subprocess.run(
                ['reboot'],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                universal_newlines = True,
                check = True
            )
        except Exception as e:
            raise LinupdateException('Could not reboot the system: ' + str(e)) from e
