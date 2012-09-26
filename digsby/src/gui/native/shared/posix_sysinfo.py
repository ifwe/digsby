import commands
import os
import statvfs
import sys

def free_bytes(path): 
    stats = os.statvfs(path) 
    return stats[statvfs.F_FRSIZE] * stats[statvfs.F_BFREE] 

def total_bytes(path):
    stats = os.statvfs(path)
    return stats[statvfs.F_FRSIZE] * stats[statvfs.F_BLOCKS]

def avail_bytes(path): 
    stats = os.statvfs(path) 
    return stats[statvfs.F_FRSIZE] * stats[statvfs.F_BAVAIL]
    
def system_ram_info():
    d = {}
    sample_arg = "-n 1"
    if sys.platform.startswith("darwin"):
        sample_arg = "-l 1"
    output = commands.getoutput("top " + sample_arg).split("\n")
    for line in output:
        if line.startswith("PhysMem:"):
            fields = line[8:].split(",")
            for field in fields:
                field = field.strip()
                amount, type = field.split(" ")
                type = type.replace(".", "")
                d[type] = amount
            break
    return d
    
def digsby_ram_info():
    output = commands.getoutput("ps %s -o psz" % os.getpid())
    return int(output[1])

def volume_info(root="/"):
    d = dict(drive=root,
             freeuser = free_bytes(root),
             total = total_bytes(root),
             free  = avail_bytes(root))
    return d