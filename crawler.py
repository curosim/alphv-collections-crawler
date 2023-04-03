import requests
import json
import time
from prettytable import PrettyTable
from datetime import datetime
import sqlite3
import shutil
import random
import string
import os

CONFIG = {
	# Filepath of the sqlite database file
	'dbfile':'alphv.db',

	# URL of the main onion service
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

	# Base folder where the downloaded files are stored.
	'downloads_folder':'./downloads',

	# Filename where the list of filepaths is stored (on call of 'filepaths' command)
	'filepaths_filename':'filepaths.txt'
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
			);
		''')
		self.cursor.execute('''
			CREATE TABLE IF NOT EXISTS downloads(
				id INTEGER PRIMARY KEY,
				collection_id INT,
				task_identifier TEXT,
				fpath TEXT,
				downloaded BOOLEAN
			);
		''')
		self.db.commit()

	def check_if_collection_exists(self, collection_id=None, name=None):
		if collection_id == None and name == None:
			# This should actually never be triggered...
			print("Dev... please, check this function (db.check_if_collection_exists) again and implement it correctly.")
		else:
			if collection_id: query = '''SELECT * FROM collections WHERE id={0}'''.format(collection_id)
			else: query = '''SELECT * FROM collections WHERE name="{0}"'''.format(name)

			self.cursor.execute(query)
			collection = self.cursor.fetchone() #retrieve the first row
			if collection == None:
				return False
			else:
				return True

	def create_collection(self, name, url, size, ts):
		""" Create new collection to the database.
		"""
		self.cursor.execute('''
			INSERT INTO collections(name, url, size, ts)
			VALUES(?,?,?,?)''', (name, url, size, ts)
		)
		self.db.commit()

	def get_all_collections(self):
		self.cursor.execute('''SELECT * FROM collections ORDER BY ts DESC''')
		collections = self.cursor.fetchall()
		return collections

	def get_collection_by_id(self, collection_id):
		query = '''SELECT * FROM collections WHERE id={0}'''.format(collection_id)
		self.cursor.execute(query)
		collection = self.cursor.fetchone() #retrieve the first row
		return collection

	def create_download(self, collection_id, fpath, task_identifier):
		""" Creates DB entry for download.
		"""
		self.cursor.execute('''
			INSERT INTO downloads(collection_id, task_identifier, fpath, downloaded)
			VALUES(?,?,?, ?)''', (collection_id, task_identifier, fpath, False)
		)
		self.db.commit()

	def get_unfinished_downloads_by_task_identifier(self, task_identifier):
		""" Returns all unfinished downloads by a task_identifier
		"""
		query = '''SELECT * FROM downloads WHERE downloads.task_identifier="{0}" AND downloads.downloaded={1}'''.format(task_identifier, False)
		self.cursor.execute(query)
		downloads = self.cursor.fetchall()
		return downloads


class AlphvApi():
	""" Class to interact with the Alphv Website.
	"""
	files = []

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

	def generate_file_list(self, collection, path):
		""" This method recursively generates a list of all files in a directory.
		"""
		print("   > Total filepaths collected so far: {0}".format(len(self.files)))
		results = self.navigate_collection_files(collection['url'], path)
		for result in results:
			if result['attrs']['isDirectory'] == True:
				new_files = self.generate_file_list(collection, result['path'])
				self.files = self.files + new_files
			else:
				filepath = result['path']
				self.files.append(filepath)
		return self.files

	def download_file(self, collection, filepath):

		# Prepare some variables for local path creation and download...
		splitted = filepath.rsplit('/', 1)
		local_folder_path = CONFIG['downloads_folder']+'/'+collection['name'].upper()+'/'+splitted[0]
		local_file_path = local_folder_path+'/'+splitted[1]
		
		# Create local folder structure if it doesnt exist yet
		os.makedirs(local_folder_path, exist_ok=True)

		print(" [*] Downloading: {0}".format(filepath))

		# download file in chunks, it should be super fast but bc of TOR it's not really...
		url = collection['url'] + '/' + filepath
		
		try:
			with self.session.get(url, stream=True) as r:
				with open(local_file_path, 'wb') as f:
					shutil.copyfileobj(r.raw, f)
		except:
			return False
		else:
			return True

	def navigate_collection_files(self, url, path):
		""" Returns list of folder structure of requested path.
		"""

		data = '{"path":"%s"}' % path
		url = '{0}/api/ls'.format(url)

		# request data from website
		response = self.session.post(url=url, data=data)

		# the data comes in a strange format (I think it's some kind of object)
		# it has some things in it which corrupts the JSON parsing, but it's handled below
		# it's kinda a hacky way but it works! :)
		new_results = []
		results = response.text.split("{\"path")
		results.pop(0)
		for result in results:
			result = '{"path'+result.split('\x00')[0]
			new_results.append(json.loads(result))

		return new_results


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
		#print(' search [ID] -> Search through collection')
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
			if len(args) != 1:
				print(" [!] Please check the syntax of your command...")
			else:
				collection_id = args[0]
				if self.db.check_if_collection_exists(collection_id=collection_id):
					self.explore_collection(collection_id)
				else:
					print(" [!] No collection with ID '{0}' exists...".format(collection_id))

		elif cmd == 'help':
			self.display_help()

		elif cmd == 'exit':
			print("[*] Quitting application.")
			exit()
		elif cmd == '': pass
		else: print(" [!] Command \'{0}\' not found...".format(cmd))

		self.cli()

	def _display_results_table(self, results):
		""" Displays folder contents in a pretty CLI table.
		"""
		table = PrettyTable()
		table.align = 'l'
		table.field_names = ["#", "Name", "Type", "Size"]

		i = 0
		for result in results:
			if result['attrs']['isDirectory'] == True: rowtype = 'dir'
			else: rowtype = 'file'

			table.add_row([
				i,
				'/'+result['path'],
				rowtype,
				result['attrs']['size']
			])
			i = i+1
		print(table)

	def download_folder(self, collection, path):
		""" Download folder recursively, single files are possible too of course.
		"""
		print(' [*] Generating a list of all file-paths, this can take quite some time.')
		print('     For every directory, a new request over TOR has to be made and that takes some time.')

		self.files = [] # generate list of filepaths...
		file_list = self.api.generate_file_list(collection, path)

		print(' [*] File list generated, total files found: {0}'.format(len(file_list)))
		print(' [*] Preparing downloads...')

		task_identifier = ''.join(random.choice(string.ascii_lowercase) for i in range(20))

		for filepath in file_list:
			self.db.create_download(
					collection_id=collection['id'],
					task_identifier=task_identifier,
					fpath=filepath
				)
		print(' [*] Starting download now.')
		downloads = self.db.get_unfinished_downloads_by_task_identifier(task_identifier=task_identifier)

		for download in downloads:
			success = self.api.download_file(collection, filepath=download['fpath'])
			if success == True: self.db.update_download(download_id=download['id'], downloaded=True)

		print(" [*] All files have been downloaded!")

		# TODO: check here if all downloads have been successful and if not, try again.

	def explore_collection(self, collection_id):
		""" CLI implementation to browse the folder structure of a collection.
		"""
		# TODO: This whole function is quite a mess and not easy to understand at all -> FIX!

		def display_explorer_help():
			""" Show help menu for the explorer-submenu...
			"""
			print('')
			print(' EXPLORER COMMANDS:')
			print(' '+'-'*50)
			print(' ls -> Lists files in current folder')
			print(' cd [ID] -> Change directory')
			print(' download [ID] -> Download file or directory (recursively!)')
			print(' filepaths [ID] -> Generates a list of all files in the directory (recursively!)')
			print(' exit -> Exit collection')
			print(' help -> Shows this help')
			print('')

		collection = self.db.get_collection_by_id(collection_id=collection_id)
		print(" [*] Accessing collection \"{0}\"".format(collection['name']))
		
		display_results = False
		path = '/data/'

		while True:

			results = self.api.navigate_collection_files(url=collection['url'], path=path)

			# Show results table after every cd (so an additional ls command is not needed)
			if display_results == True: self._display_results_table(results)

			user_input = input(' [{0}][{1}]> '.format(collection['name'], path))
			
			if user_input == 'ls':
				display_results = True
			elif user_input.startswith('cd'):
				row_id = user_input.split(' ')[1]
				try:
					if row_id == '..':
						# TODO: needs some fixing, doesnt work reliable...
						if path.count('/') > 1:
							path = path.rsplit('/')[0]
						else:
							path = '/'
					else:
						row_id = int(row_id)
						results[row_id] # triggers IndexError if it doesnt exist
						path = '/'+results[row_id]['path']

					display_results = True
				except ValueError:
					print(" [!] Please check the syntax of your comand..")
				except IndexError:
					print(" [!] No option with ID '{0}' exists...".format(row_id))

			elif user_input.startswith('download'):
				try:
					row_id = int(user_input.split(' ')[1])
					path = results[row_id]['path']
				except:
					print(" [!] Please check the syntax of your command")
				else:
					self.download_folder(collection, path)
				
				display_results = False

			elif user_input.startswith('filepaths'):
				try:
					row_id = int(user_input.split(' ')[1])
					path = results[row_id]['path']
				except:
					print(" [!] Please check the syntax of your command")
				else:
					print(' [*] Generating a list of all file-paths, this can take quite some time.')
					print('     For every directory, a new request over TOR has to be made and that takes some time.')

					file_list = self.api.generate_file_list(collection, path)

					print(' [*] File links crawling finished, total found: {0}'.format(len(file_list)))

					# append base url to each filepath
					urls_list = [collection['url']+'/'+s for s in file_list]

					# write filepaths to file
					print(' [*] Writing file links to file ({0})'.format(CONFIG['filepaths_filename']))
					with open(CONFIG['filepaths_filename'], mode='w') as f:
						f.write('\n'.join(urls_list))

					print(' [*] All filepaths written to file.')
				display_results = False

			elif user_input == 'exit':
				break;
			elif user_input == 'help':
				display_explorer_help()
				display_results = False
			else:
				print(" [!] Command '{0}' not found".format(user_input))
				display_results = False

	def update_collection_mirrors(self):
		""" List all the mirrors of the publicized collections.
		"""
		print("[*] Fetching collections from the main website.")
		collections = self.api.get_collections()
		if collections:
			newly_added = 0

			# Add all yet unknown collections to DB.
			for collection in collections:
				if self.db.check_if_collection_exists(name=collection['title']) == False:
					self.db.create_collection(
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

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print('\n')
		print(' [!] Quitting application (CTRL+C)')