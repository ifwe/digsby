from common import profile
from util import RepeatTimer, default_timer

class DigsbyBot(RepeatTimer):
    def __init__(self, seconds=60, max_emails=24, max_email_time=60*60*4):
        self.seconds = seconds
        self.max_emails = max_emails
        self.max_email_time = max_email_time
        self.errorno = 0
        self.errortime = None
        self.mail_times = []
        RepeatTimer.__init__(self, seconds, self.do_bot_check)

    def do_bot_check(self):
        import random
        self.order = profile.account_manager.order[:]
        random.shuffle(self.order)
        profile.connection.set_accounts(order=self.order,
                                        success = self.success,
                                        error = self.error)

    def error(self, *a, **k):
        print 'bot error'
        self.errorno += 1
        if self.errorno % 10 == 1:
            self.send_error_mail()

    def check_can_send(self):
        now = default_timer()
        recent = filter((lambda x: now - self.max_email_time > x),
                        self.mail_times)
        self.mail_times = recent
        if len(recent) >= self.max_emails:
            return False
        return True

    def send_error_mail(self):
        if not self.check_can_send():
            return
        self.mail_times.append(default_timer())
        mail = profile.emailaccounts[0]
        server = profile.connection.server #.split('.')[0]
        mail.send_email(to='jeffrey.rogiers+911@gmail.com',
                        subject='500 911 ' + server,
                        body='500 911 ' + server)

    def send_success_mail(self):
        if not self.check_can_send():
            return
        self.mail_times.append(default_timer())
        mail = profile.emailaccounts[0]
        server = profile.connection.server #.split('.')[0]
        mail.send_email(to='jeffrey.rogiers+911@gmail.com',
                        subject='200 911 ' + server,
                        body='200 911 ' + server)

    def success(self, *a, **k):
        if self.errorno:
            self.send_success_mail()
        self.errorno = 0
        self.errortime = None
        profile.account_manager.order_set(self.order)

bot = DigsbyBot
