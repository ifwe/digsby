import gui.native.shared.posix_sysinfo as sysinfo

class SystemInformation:

    def _ram(self):
        return sysinfo.system_ram_info()

    def _disk_c(self):
        return sysinfo.volume_info(root="/")

    def _digsby_ram(self):
        return sysinfo.digsby_ram_info()
