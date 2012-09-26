import gui.native.shared.posix_sysinfo as sysinfo

class SystemInformation:

    def _ram(self):
        return sysinfo.system_ram_info()

    def _disk_c(self):
        return sysinfo.volume_info(root="/")
