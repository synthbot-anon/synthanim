import sys
sys.path.append('../')

import synthrunner.__main__
import traceback

if __name__ == '__main__':
    try:
        synthrunner.__main__.main()
    except Exception as err:
        print(err)
        traceback.print_exc()
    input('Press any key to continue')