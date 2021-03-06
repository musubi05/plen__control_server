# -*- coding: utf-8 -*-

import os, sys, platform, socket, json
from argparse import ArgumentParser
from bottle import Bottle, request, response, Response, template, static_file
from gevent.pywsgi import WSGIServer
from geventwebsocket.websocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler

__author__    = 'Kazuyuki TAKASE'
__author__    = 'Yugo KAJIWARA'
__copyright__ = 'PLEN Project Company Ltd., and all authors.'
__license__   = 'The MIT License'


# Create global instances.
# ==============================================================================
server = Bottle()
driver = None


# Create enable CORS decorator.
# ==============================================================================
def enable_cors(function):
	def _enable_cors(*args, **kwargs):
		response.headers['Access-Control-Allow-Origin']  = '*'
		response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
		response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

		if request.method != 'OPTIONS':
			# actual request; reply with the actual response
			return function(*args, **kwargs)

	return _enable_cors


# Routing for GUI interface.
# ==============================================================================
@server.route('/')
def gui():
	return template('gui')


# Routing for static files.
# ==============================================================================
@server.route('/assets/<file_path:path>')
def assets(file_path):
	return static_file(file_path, root = './assets')

@server.route('/angularjs/<file_path:path>')
def angularjs(file_path):
	return static_file(file_path, root = './angularjs')


# Provide command-line stream on WebSocket.
# ==============================================================================
# The method is able to do command lines below.
# - apply
# - applyDiff
# - setMin
# - setMax
# - setHome
# ==============================================================================
@server.route('/cmdstream')
def cmdstream():
	wsock = request.environ.get('wsgi.websocket')

	if not wsock:
		abort(400, 'Expected WebSocket request.')

	if driver.connect():
		while True:
			try:
				messages = wsock.receive().split('/')

				result = getattr(driver, messages[0])(messages[1], int(messages[2]))

				wsock.send(str(result))

			except:
				driver.disconnect()

				break


# Web API for "Play" command.
# ==============================================================================
@server.route("/play/<SLOT:int>", method = ['OPTIONS', 'GET'])
@enable_cors
def play(SLOT):
	data = {
		"command" : "Play",
		"slot"    : SLOT,
		"result"  : None
	}

	data["result"] = driver.play(SLOT)

	response = Response(json.dumps(data, sort_keys = True, indent = 4))
	response.mimetype = "server/json"

	return response


# Web API for "Stop" command.
# ==============================================================================
@server.route("/stop", method = ['OPTIONS', 'GET'])
@enable_cors
def stop():
	data = {
		"command" : "Stop",
		"result"  : None
	}

	data["result"] = driver.stop()

	response = Response(json.dumps(data, sort_keys = True, indent = 4))
	response.mimetype = "server/json"

	return response


# Web API for "Install" command.
# ==============================================================================
@server.post("/install", method = ['OPTIONS', 'POST'])
@enable_cors
def install():
	data = {
		"command" : "Install",
		"result"  : None
	}

	data["result"] = driver.install(request.json)

	response = Response(json.dumps(data, sort_keys = True, indent = 4))
	response.mimetype = "server/json"

	return response


# Web API for "Connect" command.
# ==============================================================================
@server.route("/connect", method = ['OPTIONS', 'GET'])
@enable_cors
def connect():
	data = {
		"command" : "Connect",
		"result"  : None
	}

	data["result"] = driver.connect()

	response = Response(json.dumps(data, sort_keys = True, indent = 4))
	response.mimetype = "server/json"

	return response


# Web API for "Disconnect" command.
# ==============================================================================
@server.route("/disconnect", method = ['OPTIONS', 'GET'])
@enable_cors
def disconnect():
	data = {
		"command" : "Disconnect",
		"result"  : None
	}

	data["result"] = driver.disconnect()

	response = Response(json.dumps(data, sort_keys = True, indent = 4))
	response.mimetype = "server/json"

	return response


# Application entry point.
# ==============================================================================
def main(args):
	# Get device map.
	if os.path.isfile('device_map.json'):
		with open('device_map.json', 'r') as fin:
			DEVICE_MAP = json.load(fin)
	else:
		print 'Error : "device_map.json" is not found!'
		print '==============================================================================='

		sys.exit()

	# Create a driver instance.
	global driver

	if args.driver == 'usb':
		import driver.usb.core as USBDriver
		driver = USBDriver.Core(DEVICE_MAP)

	if args.driver == 'bled112':
		if platform.system() != 'Windows':
			print 'Error : "BLED112Driver.Core" is not supported your OS!'
			print '==============================================================================='

			sys.exit()

		import driver.bled112.core as BLED112Driver
		driver = BLED112Driver.Core(DEVICE_MAP)

	if args.driver == 'ble':
		if platform.system() != 'Darwin':
			print 'Error : "BLEDriver.Core" is not supported your OS!'
			print '==============================================================================='

			sys.exit()
		import driver.ble.core as BLEDriver
		driver = BLEDriver.Core(DEVICE_MAP, mac=args.mac)

	# Print server configurations.
	ip = socket.gethostbyname(socket.gethostname())
	print '"PLEN - Control Server" is on "%s:%d".' % (ip, args.port)

	if args.mac != '':
		print 'Connect only "%s".' % (args.mac)

	print '==============================================================================='
	sys.stdout.flush()

	# Run the HTTP Server.
	if args.driver != 'ble':
		wsgi = WSGIServer(('localhost', args.port), server, handler_class = WebSocketHandler)
		wsgi.serve_forever()

	else:
		driver.run(server.run, host = 'localhost', port = args.port)


# Purse command-line option(s).
# ==============================================================================
if __name__ == "__main__":
	description = """
===============================================================================
 ______    ________________________________________________________________
/      `  |                                                                |
| @  @ | <  "PLEN - Control Server" is a HTTP server for controlling PLEN. |
`:====:'  |________________________________________________________________|
===============================================================================
"""[1:-1]
	print description

	arg_parser = ArgumentParser()
	arg_parser.add_argument(
		'-p', '--port',
		dest    = 'port',
		type    = int,
		default = 17264,
		metavar = '<PORT NO.>',
		help    = 'default value is "17264".'
	)
	arg_parser.add_argument(
		'-d', '--driver',
		dest    = 'driver',
		choices = ('usb', 'bled112', 'ble'),
		default = 'usb',
		metavar = '<DRIVER>',
		help    = 'please choose "usb" (default), "bled112" (win only), or "ble" (mac only).'
	)
	arg_parser.add_argument(
		'--mac',
		dest    = 'mac',
		default = '',
		metavar = '<MAC ADDR.>',
		help    = "please set your PLEN's MAC address."
	)

	args = arg_parser.parse_args()
	main(args)