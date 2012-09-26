from jabber import jbuddy, jabber_util
from util import Timer, callsback
from common import pref, profile
from common.actions import action
from .objects import ip, pagetime
from pyxmpp.presence import Presence
from jabber.JabberResource import JabberResource
jbuddy_caps = jbuddy.caps

import logging; log = logging.getLogger('digsby.buddy')

def no_widgets(self, *a, **k):
    return not self.iswidget

class DigsbyResource(JabberResource):
    away_is_idle = True

class DigsbyBuddy(jbuddy):

    away_is_idle = True
    resource_class = DigsbyResource

    def __init__(self, jabber_, jid, rosteritem = None):
        jbuddy.__init__(self, jabber_, jid, rosteritem)

        from digsby.widgets.widget import iswidget
        self.iswidget = iswidget(self)
        self.ip = None
        self.online_time = None

        # digsby buddies don't get watched
        p = profile()
        if p:
            p.account_manager.buddywatcher.unregister(self)

    @property
    def supports_group_chat(self):
        return self.protocol.supports_group_chat and not self.iswidget

    @property
    def is_video_widget(self):
        node = self.jid.node
        return node and node.startswith('video.')

    @action()
    @callsback
    def remove(self, callback=None):
        ret = jbuddy.remove(self, callback = callback)
        if self.iswidget:
            def goaway():
                try:
                    pres = Presence(stanza_type="unavailable", status='Logged Out', to_jid=self.jid)
                    self.protocol.stream.send(pres)
                except (AttributeError, Exception):
                    pass
            Timer(3, goaway).start()
        return ret

    @property
    def caps(self):
        cs = []

        from common import caps
        if self.id in self.protocol.bots:
            cs.append(caps.BOT)

        if self.iswidget:
            # widgets can only IM
            cs.extend([caps.INFO, caps.IM])
        else:
            cs.extend(jbuddy.get_caps(self))

        return cs

    @property
    def service(self):
        return 'digsby'

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.digsby') if not self.iswidget else skin.get('serviceicons.widget')

    def update_presence(self, presence, buddy=None):
        groups = jabber_util.xpath_eval(presence.xmlnode, 'd:group',{'d':"digsby:setgroup"})
        if groups:
            try:
                self.widget_to_group(groups[0].getContent())
            except Exception: pass

        ips = jabber_util.xpath_eval(presence.xmlnode, 'i:ip',{'i':ip.IP_NS})
        if ips:
            try:
                self.ip = ip.Ip(ips[0]).ip
            except Exception: pass

        pagetimes = jabber_util.xpath_eval(presence.xmlnode, 'p:pagetime',{'p':pagetime.PAGETIME_NS})
        if pagetimes:
            try:
                self.online_time = pagetime.PageTime(pagetimes[0]).pagetime/1000
            except Exception: pass

        jbuddy.update_presence(self, presence, buddy=buddy)

    @action(needs = ((unicode, "Group name"),))
    @callsback
    def widget_to_group(self, groupname, callback = None):
        log.info('%s add_to_group %s', self, groupname)
        pending = self.pending_adds

        # Prevent excessive add requests.
        if groupname in pending:
            log.info('ignoring request.')
        else:
            pending.add(groupname)

        item = self.protocol.roster.get_item_by_jid(self.id).clone()

        if groupname not in item.groups:
            item.groups[:] = [groupname]
            query = item.make_roster_push()

            def onsuccess(_s):
                pending.discard(groupname)
                callback.success()

            def onerror(_s = None):
                pending.discard(groupname)
                log.warning("error adding %r to %s", self.id, groupname)
                callback.error()

            self.protocol.send_cb(query, success = onsuccess, error = onerror, timeout = onerror)

    icon_disabled = property(lambda *a: True, lambda *a: None)

    def cache_icon(self, *a, **k):
        if not self.icon_disabled:
            return super(DigsbyBuddy, self).cache_icon(*a, **k)

    @property
    def _disk_cacheable(self):
        return not self.iswidget
