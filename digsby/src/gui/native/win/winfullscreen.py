# http://msdn2.microsoft.com/en-us/library/bb762533(VS.85).aspx

from ctypes import c_int, byref, WinError, windll

try:
    SHQueryUserNotificationState = windll.shell32.SHQueryUserNotificationState
except AttributeError:
    enabled = False
else:
    '''
    typedef enum tagQUERY_USER_NOTIFICATION_STATE {
        QUNS_NOT_PRESENT = 1,
        QUNS_BUSY = 2,
        QUNS_RUNNING_D3D_FULL_SCREEN = 3,
        QUNS_PRESENTATION_MODE = 4,
        QUNS_ACCEPTS_NOTIFICATIONS = 5
        QUNS_QUIET_TIME = 6              //win7 and later, new windows user.
    } QUERY_USER_NOTIFICATION_STATE;
    '''

    enabled = True

    last_state = False

    def get_accepts_notifications():
        '''
        Returns True if the program should display notifications.

        VISTA ONLY.

        May raise WinError.
        '''
        state = c_int()
        if SHQueryUserNotificationState(byref(state)):
            raise WinError()
        val = state.value
        global last_state
        last_state = val
        return val not in (1,2,3,4)

if __name__ == '__main__':
    print get_accepts_notifications()
