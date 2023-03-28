import requests
import json
import time
from prettytable import PrettyTable
from datetime import datetime
import sqlite3

CONFIG = {
	# Filepath of the sqlite database file
	'dbfile':'alphv.db',

	# URL of the Onion service
	'url':'alphvmmm27o3abo3r2mlmjrpdmzle3rykajqc5xsj7j7ejksbpsa36ad.onion',

	# Tor socks proxy port
	'tor_socks_proxy_port':9050,

	# Website cookies
	# These are only neccessary if the website is under heavy load.
	# In that case, verify the browser manually and use the same cookie values here...
	'alphv_cookies':{
		'_dsi':'15581012852154583851',
		'_dsk':'17886788305705742769'
	},

	# File where query results are saved to
	'results_file':'results.json',
}

def get_tor_session(port):
	""" Returns a requests session with the tor service set as socks proxy.
	"""
	session = requests.session()

	# It's important to use the protocol 'socks5h' in order to enable remote DNS resolving
	session.proxies['http'] = 'socks5h://localhost:{0}'.format(port)
	session.proxies['https'] = 'socks5h://localhost:{0}'.format(port)
	return session

class Database(object):
	"""
	"""
	def __init__(self, dbfile):
		super(Database, self).__init__()
		self.init_connection(dbfile)

	def init_connection(self, dbfile):
		""" Initialize DB connection.
		"""
		self.db = sqlite3.connect(dbfile)
		self.db.row_factory = sqlite3.Row
		self.cursor = self.db.cursor()
		self.create_tables()

	def create_tables(self):
		""" Create database tables if they dont exist yet.
		"""
		self.cursor.execute('''
			CREATE TABLE IF NOT EXISTS collections(
				id INTEGER PRIMARY KEY,
				name TEXT,
				url TEXT,
				size INT,
				ts TEXT
			)
		''')
		self.db.commit()

	def check_if_collection_exists(self, name):
		self.cursor.execute('''SELECT * FROM collections WHERE name=?''', (name,))
		collection = self.cursor.fetchone() #retrieve the first row
		if collection == None:
			return False
		else:
			return True

	def add_collection(self, name, url, size, ts):
		""" Adds new collection to the database.
		"""
		self.cursor.execute('''
			INSERT INTO collections(name, url, size, ts)
			VALUES(?,?,?,?)''', (name, url, size, ts)
		)
		self.db.commit()

	def get_all_collections(self):
		self.cursor.execute('''SELECT * FROM collections''')
		collections = self.cursor.fetchall() #retrieve the first row
		return collections

class AlphvApi():
	""" Class to interact with the Alphv Website.
	"""

	def __init__(self, onion_address, tor_socks_port):
		self.hidden_service_url = 'http://{0}'.format(onion_address)
		self._set_tor_session(tor_socks_port)

	def _set_tor_session(self, port):
		""" Create requests session with TOR as proxy.
		"""
		self.session = get_tor_session(port)

	def get_collections(self):
		cookies = CONFIG['alphv_cookies']
		response = self.session.get(
			'{0}{1}'.format(self.hidden_service_url, '/api/collections'),
			cookies=cookies
		)
		try:
			data = json.loads(response.text)
			return data
		except Exception as e:
			return None

	def navigate_collection_files(self, url, path):
		"""
		"""

		data = '{"path":"/data/Coolebavisllp"}'
		response = requests.post(
			'http://{0}{1}'.format(url, path),
			data=data,
		)
		print(response.text)


class AlphvNavigator():
	""" Wrapper of the API class to provide a CLI and additional functions.
	"""

	def __init__(self, banner=True):
		self.db = Database(CONFIG['dbfile'])
		self.api = AlphvApi(
				onion_address=CONFIG['url'],
				tor_socks_port=CONFIG['tor_socks_proxy_port']
			)
		if banner == True: self.banner()

	def banner(self):
		print('     _    _     ____  _   ___     __   ____      _ _           _   _                 ')
		print('    / \\  | |   |  _ \\| | | \\ \\   / /  / ___|___ | | | ___  ___| |_(_) ___  _ __  ___ ')
		print('   / _ \\ | |   | |_) | |_| |\\ \\ / /  | |   / _ \\| | |/ _ \\/ __| __| |/ _ \\| \'_ \\/ __|')
		print('  / ___ \\| |___|  __/|  _  | \\ V /   | |__| (_) | | |  __/ (__| |_| | (_) | | | \\__ \\')
		print(' /_/   \\_\\_____|_|   |_| |_|  \\_/     \\____\\___/|_|_|\\___|\\___|\\__|_|\\___/|_| |_|___/')
		print('')

	def display_help(self):
		print('')
		print(' COMMANDS:')
		print(' '+'-'*50)
		print(' list -> Lists collections')
		print(' update -> Updates collections')
		print(' explore [ID] -> Traverse collection folder structure')
		print(' search [ID] -> Search through collection')
		print(' help -> Shows this help')
		print(' exit -> Quit application')
		print('')

	def cli(self):
		user_input = input(' $> ')

		# convert input to lowercase and remove whitespaces at start and end
		user_input = user_input.lower().strip(' ')

		# split user input by whitespaces
		cmd_parts = user_input.split(' ')
		
		# get first word, which is the command what to do
		cmd = cmd_parts[0]

		# remove it from list in order to have a list of arguments for the command...
		cmd_parts.remove(cmd)
		args = cmd_parts
		
		if cmd == 'list':
			self.list_collections()

		elif cmd == 'update':
			self.update_collection_mirrors()

		elif cmd == 'explore':
			print("to be implemented...")

		elif cmd == 'search':
			print("to be implemented...")

		elif cmd == 'help':
			self.display_help()

		elif cmd == 'exit':
			print("[*] Quitting application.")
			exit()

		else:
			print("[!] Command \'{0}\' not found...".format(cmd))
		
		self.cli()

	def update_collection_mirrors(self):
		""" List all the mirrors of the publicized collections.
		"""
		print("[*] Fetching collections from the main website.")
		collections = self.api.get_collections()
		if collections:
			newly_added = 0

			# Add all yet unknown collections to DB.
			for collection in collections:
				if self.db.check_if_collection_exists(collection['title']) == False:
					self.db.add_collection(
							name=collection['title'],
							url=collection['url'],
							size=collection['size'],
							ts=collection['dt']
						)
					newly_added = newly_added+1
			
			# Let the user know what changed (if and how many new collections were added)
			if newly_added == 0:
				if len(collections) > 0:
					print("[*] No new collections added... ({0} fetched but they already exist)".format(len(collections)))
				else:
					print("[*] No new collections added... ")
			elif newly_added == 1:
				print("[*] Added 1 new collection to DB!")
			else:
				print("[*] Added {0} new collections to DB!".format(newly_added))

			return True
		else:
			# This warning will be printed if the server is under heavy load and expects a JS task to be solved...
			print("[!] Currently there's high load on the server, either manually renew the cookies or try again later.")
			print("    Automatic verification is not supported yet.")
			return False

	def list_collections(self):
		""" Displays collections in a CLI table.
		"""
		collections = self.db.get_all_collections()
		table = PrettyTable()
		table.align = 'l'
		table.field_names = ["ID", "Name", "Size", "URL", "Released (D.M.Y)",]
		for collection in collections:
			size_in_gb = f"{collection['size']/(1<<30):,.0f} GB"
			release_date = datetime.fromtimestamp(int(collection['ts'])/1000)
			table.add_row([
				collection['id'],
				collection['name'],
				size_in_gb,
				collection['url'],
				release_date.strftime("%d.%m.%Y %H:%M")
			])
		print(table)
		return collections

def main():
	alphv = AlphvNavigator()
	alphv.display_help()
	alphv.cli()

	"""
	alphv.navigate_collection_files(
		url='zyb7j23sfsert574hii342lwnz7qeyw2kb7zom74wjabwhifhpoknaqd.onion',
		path='/data/Coolebavisllp'
	)
	exit()

	# Writing the results to a file.
	if collections:
		with open(CONFIG['results_file'], 'w') as f:
			f.write(json.dumps(collections, indent=4))
		print("[*] Results written to file: {0}".format(CONFIG['results_file']))

	"""

if __name__ == '__main__':
	main()
