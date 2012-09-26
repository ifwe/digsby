#__LICENSE_GOES_HERE__

"""
A Python module that uses GNTP to post messages
Mostly mirrors the Growl.py file that comes with Mac Growl
http://code.google.com/p/growl/source/browse/Bindings/python/Growl.py
"""
import gntp
import socket

class GrowlNotifier(object):
	applicationName = 'Python GNTP'
	notifications = []
	defaultNotifications = []
	applicationIcon = None
	passwordHash = 'MD5'
	
	#GNTP Specific
	debug = False
	password = None
	hostname = None
	port = 23053
	
	def __init__(self, applicationName=None, notifications=None, defaultNotifications=None, applicationIcon=None, hostname=None, password=None, port=None, debug=False):
		if applicationName:
			self.applicationName = applicationName
		assert self.applicationName, 'An application name is required.'

		if notifications:
			self.notifications = list(notifications)
		assert self.notifications, 'A sequence of one or more notification names is required.'

		if defaultNotifications is not None:
			self.defaultNotifications = list(defaultNotifications)
		elif not self.defaultNotifications:
			self.defaultNotifications = list(self.notifications)

		if applicationIcon is not None:
			self.applicationIcon = self._checkIcon(applicationIcon)
		elif self.applicationIcon is not None:
			self.applicationIcon = self._checkIcon(self.applicationIcon)
		
		#GNTP Specific
		if password:
			self.password = password
		
		if hostname:
			self.hostname = hostname
		assert self.hostname, 'Requires valid hostname'
		
		if port:
			self.port = int(port)
		assert isinstance(self.port,int), 'Requires valid port'
		
		if debug:
			self.debug = debug
		
	def _checkIcon(self, data):
		'''
		Check the icon to see if it's valid
		@param data: 
		@todo Consider checking for a valid URL
		'''
		return data
	
	def register(self):
		'''
		Send GNTP Registration
		'''
		register = gntp.GNTPRegister()
		register.add_header('Application-Name',self.applicationName)
		for notification in self.notifications:
			enabled = notification in self.defaultNotifications
			register.add_notification(notification,enabled)
		if self.applicationIcon:
			register.add_header('Application-Icon',self.applicationIcon)
		if self.password:
			register.set_password(self.password,self.passwordHash)
		response = self.send('register',register.encode())
		if isinstance(response,gntp.GNTPOK): return True
		return response.error()
	
	def notify(self, noteType, title, description, icon=None, sticky=False, priority=None):
		'''
		Send a GNTP notifications
		'''
		assert noteType in self.notifications
		notice = gntp.GNTPNotice()
		notice.add_header('Application-Name',self.applicationName)
		notice.add_header('Notification-Name',noteType)
		notice.add_header('Notification-Title',title)
		if self.password:
			notice.set_password(self.password,self.passwordHash)
		if sticky:
			notice.add_header('Notification-Sticky',sticky)
		if priority:
			notice.add_header('Notification-Priority',priority)
		if icon:
			notice.add_header('Notification-Icon',self._checkIcon(icon))
		if description:
			notice.add_header('Notification-Text',description)
		response = self.send('notify',notice.encode())
		if isinstance(response,gntp.GNTPOK): return True
		return response.error()
	def subscribe(self,id,name,port):
		sub = gntp.GNTPSubscribe()
		sub.add_header('Subscriber-ID',id)
		sub.add_header('Subscriber-Name',name)
		sub.add_header('Subscriber-Port',port)
		if self.password:
			sub.set_password(self.password,self.passwordHash)
		response = self.send('subscribe',sub.encode())
		if isinstance(response,gntp.GNTPOK): return True
		return response.error()
	def send(self,type,data):
		'''
		Send the GNTP Packet
		'''
		if self.debug:
			print 'To: %s:%s <%s>'%(self.hostname,self.port,type)
			print '<Sending>\n',data,'\n</Sending>'
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((self.hostname,self.port))
		s.send(data)
		response = gntp.parse_gntp(s.recv(1024))
		s.close()
		if self.debug:
			print 'From: %s:%s <%s>'%(self.hostname,self.port,response.__class__)
			print '<Recieved>\n',response,'\n</Recieved>'
		return response
