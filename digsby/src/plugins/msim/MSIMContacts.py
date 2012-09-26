'''
Types to provide a digsby interface to contacts and groups on the Myspace IM protocol.
Note that MSIM buddies are the same as MSIM contacts - this is not how things usually are in digsby.
'''
import logging

import util
import common
import contacts

log = logging.getLogger('msim.contacts')


class MSIM_Group(contacts.Group):
    GroupName = GroupID = GroupFlag = Position = None

    def __init__(self, group_info, proto, *contents):
        #[{'GroupName': 'IM Friends', 'GroupID': '10815', 'GroupFlag': '131073', 'Position': '1'},

        self.update_info(group_info)
        contacts.Group.__init__(self, self.GroupName, proto, self.GroupID, *contents)

    def update_info(self, info):
        self._pending_info_request = False
        for k in info.keys():
            v = info[k]

            if isinstance(v, bytes):
                v = v.decode('fuzzy utf8')
            setattr(self, k, v)

    def _get_name(self):
        return self.GroupName

    def _set_name(self, val):
        self.GroupName = val

    name = property(_get_name, _set_name)

    def get_infodict(self):
        return dict(GroupName=self.GroupName,
                    GroupID=self.GroupID,
                    GroupFlag=str(self.GroupFlag),
                    Position=str(self.Position),
                    )

    def __cmp__(self, other):
        other_id = getattr(other, 'GroupID', None)
        id_cmp = cmp(self.GroupID, other_id)

        if id_cmp == 0:
            return 0
        else:
            try:
                return cmp(int(self.Position), int(getattr(other, 'Position', -1)))
            except Exception:
                return -1


class MSIM_Buddy(contacts.Contact, common.buddy):
    _renderer = 'Contact'

    HIDDEN_CONTACTS = [u'myspaceim', '78744676']

    Position = GroupName = Visibility = ShowAvatar = AvatarURL = ImageURL = \
    NickName = IMName = NameSelect = OfflineMsg = Headline = LastLogin = UserID = \
    ContactID = SkyStatus = UserName = RealName = DisplayName = BandName = \
    SongName = ContactType = Gender = RoomLastLogin = None

    _settable_properties = ['Visibility', 'Position', 'GroupName', 'NameSelect', 'NickName']
    _all_properties = ['Position', 'GroupName', 'Visibility', 'ShowAvatar',
                       'AvatarURL', 'ImageURL', 'NickName', 'IMName',
                       'NameSelect', 'OfflineMsg', 'Headline', 'LastLogin',
                       'SkyStatus', 'UserName', 'RealName', 'DisplayName',
                       'BandName', 'SongName', 'ContactType', 'Gender',
                       'RoomLastLogin']

    def __init__(self, info, proto):
        self._status_message = None
        self.status = 'unknown'
        self.id = self.ContactID = self.UserID = info.get('ContactID', info.get('UserID'))
        common.buddy.__init__(self, self.id, proto)

        self.UserName = info.get('UserName')  # from social info
        self.RealName = info.get('RealName')  # from social info
        self.DisplayName = info.get('DisplayName')  # from social info
        self.IMName = info.get('IMName')  # 'display name', nameselect = 2
        self.NickName = info.get('NickName')  # nick name, nameselect = 3
        self.NameSelect = info.get('NameSelect', '1')

        self.OfflineMsg = info.get('OfflineMsg')
        self.Headline = info.get('Headline')
        self.LastLogin = info.get('LastLogin', '0')

        self.ShowAvatar = info.get('ShowAvatar', 'False')
        self.AvatarURL = info.get('AvatarURL')
        self.ImageURL = info.get('ImageURL')

        self.SkyStatus = info.get('SkyStatus')
        self.Visibility = info.get('Visibility')

        self.Position = info.get('Position', '0')
        self.GroupName = info.get('GroupName')

        contacts.Contact.__init__(self, self, self.id)

    @property
    def visible(self):
        visible = False
        try:
            visible = int(self.Visibility)
        except (ValueError, TypeError):
            # Could be None, or non-int-like string.
            pass

        return visible and \
                self.UserName not in self.HIDDEN_CONTACTS and \
                self.id not in self.HIDDEN_CONTACTS

    def _get_icon_hash(self):
        return self.AvatarURL or self.ImageURL

    def _set_icon_hash(self, val):
        self.AvatarURL = self.ImageURL = val

    icon_hash = property(_get_icon_hash, _set_icon_hash)

    def _get__use_icon(self):
        return self.ShowAvatar == 'True'

    def _set__use_icon(self, val):
        if val:
            self.ShowAvatar = 'True'
        else:
            self.ShowAvatar = 'False'

    _use_icon = property(_get__use_icon, _set__use_icon)

    def get_infodict(self, id_key='ContactID', settable_only=True):
        if settable_only:
            keys = self._settable_properties[:]
        else:
            keys = self._all_properties[:]

        keys.append(id_key)

        d = {}
        for key in keys:
            val = getattr(self, key, None)
            if val is not None:
                d[key] = val

        return d

    def __repr__(self):
        return common.buddy.__repr__(self)

    def __getattr__(self, attr):
        return object.__getattribute__(self, attr)

    def _get__notify_dirty(self):
        return self._notify_dirty_

    def _set__notify_dirty(self, val):
        self._notify_dirty_ = val

    _notify_dirty = property(_get__notify_dirty, _set__notify_dirty)

    def _get_GroupName(self):
        group = self.protocol.get_group(self.GroupID)
        if group is None:
            return None
        else:
            return group.GroupName

    def _set_GroupName(self, val):
        group = self.protocol.get_group(val)
        if group is None:
            self.GroupID = None
        else:
            self.GroupID = group.GroupID

    GroupName = property(_get_GroupName, _set_GroupName)

    @property
    def blocked(self):
        return False

    @common.action(lambda *a, **k: None)
    def block(self, block=True, **k):
        return

    unblock = block

    def update_info(self, info, info_type=None):
        for k in info.keys():
            is_name = k in ['NickName', 'IMName', 'RealName', 'UserName', 'DisplayName']

            newval = info.get(k, '').decode('utf8').decode('xml')

            # Don't set the attribute if it's a name and it's empty.
            if (is_name and newval.strip()) or not is_name:
                setattr(self, k, newval)

        self.notify()

    def get_icon_hash(self):
        return self.icon_hash

    def _get_status_message(self):
        if self.online:
            return self._status_message
        else:
            return self.OfflineMsg

    def _set_status_message(self, val):
        if isinstance(val, bytes):
            val, _val = val.decode('fuzzy utf8'), val

        self._status_message = val

    status_message = property(_get_status_message, _set_status_message)

    @property
    def idle(self):
        return self.status == 'idle'

    @property
    def mobile(self):
        return False

    @property
    def away(self):
        return self.status == 'away'

    @property
    def online(self):
        return self.status not in ('unknown', 'offline', 'hidden')

    @property
    def remote_alias(self):
        alias = None
        try:
            ns = int(self.NameSelect)
        except Exception:
            ns = -1

        if 1 <= ns <= 3:
            alias = [self.DisplayName, self.IMName, self.NickName][ns - 1]

        if not alias:
            # does this protocol have enough aliases?
            alias = self.RealName or self.DisplayName or self.UserName or self.IMName or self.NickName

        if not alias and not getattr(self, '_pending_info_request', False):
            util.Timer(common.pref('msim.contact_info.request_timeout', type=int, default=5),
                       lambda: setattr(self, '_pending_info_request', False)).start()
            self._pending_info_request = True
            self.protocol.request_buddy_info(self.id)

        if isinstance(alias, bytes):
            return alias.decode('utf8')

        return alias

    def __cmp__(self, other):
        other_id = getattr(other, 'id', None)
        id_cmp = cmp(self.id, other_id)

        if id_cmp == 0:
            return 0
        else:
            try:
                return cmp(int(self.Position), int(getattr(other, 'Position', -1)))
            except Exception:
                return -1
