'''
        if False and sys.TRACK_RAM_STATS:
            def log_ram_stats(**k):
                from sysinfo_hack import memory_info
                from path import path
                from operator import itemgetter
                import time

                d = path(r'c:\ramstats')
                if not d.isdir():
                    d.makedirs()

                ramstats = sorted(sys.ramstats, key=itemgetter(2))

                stats_file = d / 'ram_%s.csv' % time.time()
                with open(stats_file, 'w') as f:
                    write = f.write

                    write('name,time,delta,wss\n')
                    for entry in ramstats:
                        write(','.join(str(s) for s in entry) + '\n')

                import gc
                gc.enable()

            self.BuddyListShown.append(lambda **k: setattr(self, 'timer', wx.CallLater(2000, log_ram_stats)))#lambda: setattr(self, 'timer', wx.CallLater(2000, log_ram_stats))

'''
