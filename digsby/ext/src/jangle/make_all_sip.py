#__LICENSE_GOES_HERE__

import sys
import os
sys.path.append('../../../lib')
from path import path

def main():
    self = path(__file__)

    dot_sips = sorted(set(self.parent.glob('*/*.sip') + self.parent.glob('*/*/*.sip')))

    with open(self.parent / 'all.sip', 'w') as f:
        f.write('\n')
        for sip_file in dot_sips:
            f.write('%Include ' + os.path.relpath(sip_file, self.parent).replace('\\', '/') + '\n')
        f.write('\n')

if __name__ == "__main__":
    main()