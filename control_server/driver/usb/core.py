# -*- coding: utf-8 -*-

import platform, serial, serial.tools.list_ports, time
from ctypes import c_ushort


__author__    = 'Kazuyuki TAKASE'
__author__    = 'Yugo KAJIWARA'
__copyright__ = 'PLEN Project Company Ltd., and all authors.'
__license__   = 'The MIT License'


class Core:
	def __init__(self, device_map):
		self._serial     = None
		self._DEVICE_MAP = device_map
		self._values     = [ 0 for x in range(24) ]


	def apply(self, device, value):
		if self._serial == None:
			return False

		cmd = "$AN%02x%03x" % (self._DEVICE_MAP[device], (c_ushort(value).value & 0xFFF))
		self._serial.write(cmd)
		time.sleep(0.01)

		return True


	def applyDiff(self, device, value):
		if self._serial == None:
			return False

		cmd = "$AD%02x%03x" % (self._DEVICE_MAP[device], (c_ushort(value).value & 0xFFF))
		self._serial.write(cmd)
		time.sleep(0.01)

		return True


	def setMin(self, device, value):
		if self._serial == None:
			return False

		cmd = ">MI%02x%03x" % (self._DEVICE_MAP[device], (c_ushort(value).value & 0xFFF))
		self._serial.write(cmd)

		return True


	def setMax(self, device, value):
		if self._serial == None:
			return False

		cmd = ">MA%02x%03x" % (self._DEVICE_MAP[device], (c_ushort(value).value & 0xFFF))
		self._serial.write(cmd)

		return True


	def setHome(self, device, value):
		if self._serial == None:
			return False

		cmd = ">HO%02x%03x" % (self._DEVICE_MAP[device], (c_ushort(value).value & 0xFFF))
		self._serial.write(cmd)

		return True


	def play(self, slot):
		if self._serial == None:
			return False

		cmd = "$PM%02x" % slot
		self._serial.write(cmd)

		return True


	def stop(self):
		if self._serial == None:
			return False

		cmd = "$SM"
		self._serial.write(cmd)

		return True


	def install(self, json):
		if self._serial == None:
			return False

		# コマンドの指定
		cmd = ">IN"

		# スロット番号の指定
		cmd += "%02x" % (json["slot"])
		
		# モーション名の指定
		if len(json["name"]) < 20:
			cmd += json["name"].ljust(20)
		else:
			cmd += json["name"][:19]

		# 制御機能の指定
		if (len(json["codes"]) != 0):
			for code in json["codes"]:
				if (code["func"] == "loop"):
					cmd += "01%02x%02x" % (code["args"][0], code["args"][1])
					break

				if (code["func"] == "jump"):
					cmd += "02%02x00" % (code["args"][0])
					break
		else:
			cmd += "000000"

		# フレーム数の指定
		cmd += "%02x" % (len(json["frames"]))
		
		# フレーム構成要素の指定
		for frame in json["frames"]:
			# 遷移時間の指定
			cmd += "%04x" % (frame["transition_time_ms"])

			for output in frame["outputs"]:
				self._values[self._DEVICE_MAP[output["device"]]] = c_ushort(output["value"]).value

			for value in self._values:
				cmd += "%04x" % value

		# Divide command length by payload size.
		block   = len(cmd) // 20
		surplus = len(cmd) % 20

		for index in range(block):
			self._serial.write(map(ord, cmd[20 * index: 20 * (index + 1)]))
			time.sleep(0.01)

		self._serial.write(map(ord, cmd[-surplus:]))
		time.sleep(0.01)

		return True


	def connect(self):
		com = None

		for device in list(serial.tools.list_ports.comports()):
			if 'Arduino Micro' in device[1]:
				com = device[0]

		# Fix for old version mac.
		if (  ( (com == None)
			and (platform.system() == 'Darwin') )
		):
			for device in list(serial.tools.list_ports.comports()):
				if ( ( ('/dev/tty.usbmodem'  in device[0])
					or ('/dev/tty.usbserial' in device[0])
					or ('/dev/cu.usbmodem'   in device[0])
					or ('/dev/cu.usbserial'  in device[0]) )
				):
					try:
						openable = serial.Serial(port = device[0])
						openable.close()

						com = device[0]

					except serial.SerialException:
						pass

		if com == None:
			return False

		self.disconnect()

		if self._serial == None:
			self._serial = serial.Serial(port = com, baudrate = 2000000, timeout = 1)
			self._serial.flushInput()
			self._serial.flushOutput()

		return True


	def disconnect(self):
		if self._serial == None:
			return False

		self._serial.close()
		self._serial = None

		return True