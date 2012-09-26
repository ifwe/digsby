
class MockMetaContact(list):

    _renderer = 'Contact'

    def __init__(self, name, *contacts):
        list.__init__(self,contacts)

    @property
    def away(self):
        return self.status=='away'

    @property
    def alias(self):
        return self.name

    @property
    def service(self):
        return self[0].service

    @property
    def idle(self):
        return self.status == 'idle'

    def __hash__(self):
        return hash(self.name)

    @property
    def stripped_msg(self):
        from util import strip_html2
        return strip_html2(self.status_message)

    @property
    def online(self):
        return True

    @property
    def num_online(self):
        return int(self.online)
    @property
    def name(self):
        for contact in self:
            if contact.status=='available':
                return contact.name

        for contact in self:
            if contact.status=='away':
                return contact.name

        return self[0].name


    @property
    def protocol(self):
        for contact in self:
            if contact.status=='available':
                return contact.protocol

        for contact in self:
            if contact.status=='away':
                return contact.protocol

        return self[0].protocol

    @property
    def icon(self):
        for contact in self:
            if contact.status=='available':
                return contact.icon

        for contact in self:
            if contact.status=='away':
                return contact.icon

        return self[0].icon
    @property
    def status_message(self):
        for contact in self:
            if contact.status=='available':
                return contact.status_message

        for contact in self:
            if contact.status=='away':
                return contact.status_message

        return self[0].status_message

    @property
    def status_orb(self):
        return self.status

    @property
    def status(self):
        for contact in self:
            if contact.status=='available':
                return contact.status

        for contact in self:
            if contact.status=='away':
                return contact.status

        return self[0].status

    @property
    def first_online(self):
        for contact in self:
            if contact.status=='available':
                return contact

        for contact in self:
            if contact.status=='away':
                return contact

        return self[0]

    def chat(self):
        print 'wut?'
