# coding: utf-8

import uuid
import hmac
import json
import hashlib
import redis


class SessionData(dict):
	def __init__(self, session_id, hmac_key):
		self.session_id = session_id
		self.hmac_key = hmac_key


class Session(SessionData):
	def __init__(self, session_manager, request_handler):

		self.session_manager = session_manager
		self.request_handler = request_handler

		try:
			current_session = session_manager.get(request_handler)
		except InvalidSessionException:
			current_session = session_manager.get()

		for key, data in current_session.items():
			self[key] = data
		self.session_id = current_session.session_id
		self.hmac_key = current_session.hmac_key

	def save(self):
		self.session_manager.set(self.request_handler, self)

	def clear(self):
		self.session_manager.unset(self.request_handler)

	def acquire(self):
		return self.session_manager.obtain(self.request_handler)


class SessionManager(object):
	def __init__(self, secret, store_options, session_timeout):
		self.secret = secret
		self.session_timeout = session_timeout
		try:
			if store_options['redis_pass']:
				self.redis = redis.StrictRedis(host=store_options['redis_host'], port=store_options['redis_port'], password=store_options['redis_pass'])
			else:
				self.redis = redis.StrictRedis(host=store_options['redis_host'], port=store_options['redis_port'])
		except Exception as e:
			print(e)
			# pass


	def _fetch(self, session_id):
		try:
			session_data = raw_data = self.redis.get(session_id)
			if raw_data != None:
				self.redis.setex(session_id, self.session_timeout, raw_data)
				session_data = json.loads(str(raw_data, 'utf-8'))

			if type(session_data) == type({}):
				return session_data
			else:
				return {}
		except IOError:
			return {}

	def get(self, request_handler = None):
		if (request_handler == None):
			session_id = None
			hmac_key = None
		else:
			if request_handler.get_secure_cookie("session_id"):
				session_id = str(request_handler.get_secure_cookie("session_id"), 'utf-8')
			else:
				session_id = None

			if request_handler.get_secure_cookie("verification"):
				hmac_key = str(request_handler.get_secure_cookie("verification"), 'utf-8')
			else:
				hmac_key = None

		if session_id == None:
			session_exists = False
			session_id = self._generate_id()
			hmac_key = self._generate_hmac(session_id)
		else:
			session_exists = True
		check_hmac = self._generate_hmac(session_id)
		if hmac_key != check_hmac:
			raise InvalidSessionException()

		session = SessionData(session_id, hmac_key)
		if session_exists:
			session_data = self._fetch(session_id)
			for key, data in session_data.items():
				session[key] = data
		return session

	def obtain(self, request_handler):
		if (request_handler.get_secure_cookie("session_id")
			and request_handler.get_secure_cookie("verification")):
			session_id = str(request_handler.get_secure_cookie("session_id"), 'utf-8')
			hmac_key = str(request_handler.get_secure_cookie("verification"), 'utf-8')
			check_hmac = self._generate_hmac(session_id)
			if hmac_key != check_hmac:
				raise InvalidSessionException()
			return session_id
		else:
			return None

	def unset(self, request_handler):
		if (request_handler.get_secure_cookie("session_id")
			and request_handler.get_secure_cookie("verification")):
			session_id = str(request_handler.get_secure_cookie("session_id"), 'utf-8')
			request_handler.clear_cookie("session_id")

			hmac_key = str(request_handler.get_secure_cookie("verification"), 'utf-8')
			request_handler.clear_cookie("verification")

			check_hmac = self._generate_hmac(session_id)
			if hmac_key != check_hmac:
				raise InvalidSessionException()

			self.redis.delete(session_id)

	def set(self, request_handler, session):
		request_handler.set_secure_cookie("session_id", session.session_id)
		request_handler.set_secure_cookie("verification",session.hmac_key)
		session_data = json.dumps(dict(session.items()))
		self.redis.sadd("sessionid", session.session_id)
		self.redis.setex(session.session_id, self.session_timeout, session_data)


	def _generate_id(self):
		hash_value = self.secret + str(uuid.uuid4())
		new_id = hashlib.sha256(hash_value.encode(encoding="utf-8"))
		return new_id.hexdigest()

	def _generate_hmac(self, session_id):
		return hmac.new(session_id.encode(encoding="utf-8"),
						self.secret.encode(encoding="utf-8"),
						hashlib.sha256).hexdigest()



class InvalidSessionException(Exception):
	pass
