import requests
import json
import time
from prettytable import PrettyTable
from datetime import datetime

CONFIG = {
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

class AlphvNavigator():
	""" Wrapper of the API class to provide a CLI and additional functions.
	"""

	def __init__(self):
		self.api = AlphvApi(
				onion_address=CONFIG['url'],
				tor_socks_port=CONFIG['tor_socks_proxy_port']
			)

	def banner(self):
		print('     _    _     ____  _   ___     __   ____      _ _           _   _                 ')
		print('    / \\  | |   |  _ \\| | | \\ \\   / /  / ___|___ | | | ___  ___| |_(_) ___  _ __  ___ ')
		print('   / _ \\ | |   | |_) | |_| |\\ \\ / /  | |   / _ \\| | |/ _ \\/ __| __| |/ _ \\| \'_ \\/ __|')
		print('  / ___ \\| |___|  __/|  _  | \\ V /   | |__| (_) | | |  __/ (__| |_| | (_) | | | \\__ \\')
		print(' /_/   \\_\\_____|_|   |_| |_|  \\_/     \\____\\___/|_|_|\\___|\\___|\\__|_|\\___/|_| |_|___/')
		print('')

	def list_collection_mirrors(self):
		""" List all the mirrors of the publicized collections.
		"""
		print("[*] Fetching collection mirrors from the main website.")
		collections = self.api.get_collections()
		if collections:
			table = PrettyTable()
			table.align = 'l'
			table.field_names = ["Name", "Size", "URL", "Released (D.M.Y)",]
			for dataset in collections:
				size_in_gb = f"{dataset['size']/(1<<30):,.0f} GB"
				release_date = datetime.fromtimestamp(int(dataset['dt'])/1000)
				table.add_row([dataset['title'], size_in_gb, dataset['url'], release_date.strftime("%d.%m.%Y %H:%M")])
			print(table)
			return collections
		else:
			self.renew_authentication_cookies_warning()
			return None

	def renew_authentication_cookies_warning(self):
		""" This warning will be printed if the server is under heavy load and expects a JS task to be solved...
		"""
		print("[!] Currently there's high load on the server, either manually renew the cookies or try again later.")
		print("    Automatic verification is not supported yet.")

def main():
	alphv = AlphvNavigator()
	alphv.banner()
	collections = alphv.list_collection_mirrors()

	# Writing the results to a file.
	if collections:
		with open(CONFIG['results_file'], 'w') as f:
			f.write(json.dumps(collections, indent=4))
		print("[*] Results written to file: {0}".format(CONFIG['results_file']))

if __name__ == '__main__':
	main()
