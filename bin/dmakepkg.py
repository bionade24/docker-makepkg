#! /bin/python3 -B

import argparse
import os
import subprocess
import sys
import uuid

class dmakepkg:
	def __init__(self):
		self.pacmanConf="/etc/pacman.conf"
		self.makepkgConf="/etc/makepkg.conf"
		self.pacmanPkgCache="/var/cache/pacman/pkg"

	# From https://stackoverflow.com/questions/17435056/read-bash-variables-into-a-python-script
	# Written by user Taejoon Byun
	def getVar(self, script, varName):
		CMD = 'echo $(source {}, echo ${})'.format(script, varName)
		p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
		return p.stdout.readlines()[0].decode("utf-8").strip()

	# From https://stackoverflow.com/questions/17435056/read-bash-variables-into-a-python-script
	# Written by user Taejoon Byun
	def callFunc(self, script, funcName):
		CMD = 'echo $(source {}; echo $({}))'.format(script, funcName)
		p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
		return p.stdout.readlines()[0].decode("utf-8").strip()

	def main(self):
		self.parser = argparse.ArgumentParser(prog="dmakepkg")
		self.parser.add_argument('-x',
			action='store_true',
			help="Use host system's /etc/pacman.conf"
			)
		self.parser.add_argument('-y',
			action='store_false',
			help="Never use pump mode, even if pump mode capable servers are configured")
		self.parser.add_argument('-z',
			action='store_false',
			help="Do not automatically download missing PGP keys",
			)
		self.parser.add_argument('-e', nargs='?',
			help="Executes the argument as a command in the container after copying the package source")
		namespace, self.rest = self.parser.parse_known_args()

		parameters = [ "--name", "dmakepkg_{}".format(uuid.uuid4())]

		localCacheDir = self.getVar(self.pacmanConf, "CacheDir")
		if not localCacheDir:
			localCacheDir = "/var/cache/pacman/pkg"

		if namespace.x:
			parameters.extend("-v /etc/pacman.conf:/etc/pacman.conf -v {}:{}".format(localCacheDir, localCacheDir).split(" "))
		else:
			parameters.extend("-v {}:{}".format(localCacheDir, self.pacmanPkgCache).split())

		self.usePumpMode = namespace.y
		self.downloadKeys = namespace.z
		self.command = namespace.e
		self.useHostPacman = namespace.x

		
		if os.path.isfile(self.makepkgConf):
			parameters += self.findParameters()
		print("Parameters: ", parameters)

		# set object attributes
		# self.hostPacmanConf = namespace.
		# create first part
		completeCmdLine = "/bin/docker run --rm --net=host -ti --cpu-shares=128 --pids-limit=-1".split(" ")

		if self.useHostPacman:
			completeCmdLine += [ "-v", "/etc/pacman.conf:/etc/pacman.conf" ]

		completeCmdLine += ["-v", "{}:/src".format(os.getcwd())] + parameters + [ "makepkg" ]

		if not self.downloadKeys:
			completeCmdLine.append("-x")
		if not self.usePumpMode:
			completeCmdLine.append("-y")
		completeCmdLine.extend(["-u", str(os.geteuid()), "-g", str(os.getegid())])
		if self.command:
			completeCmdLine.extend(["-e", self.command ])
		completeCmdLine += self.rest

		print("cmdline: ", completeCmdLine)
		dockerProcess = subprocess.Popen(completeCmdLine)
		dockerProcess.wait()


	# this function finds all possible arguments to the docker command line we could need
	# and builds them.
	def findParameters(self):
		parameters=[]
		try:
			lines = open(self.makepkgConf, "r").readlines()
		except:
			# makepkg doesn't exist
			return parameters
	
		parameters.extend("-v /etc/makepkg.conf:/etc/makepkg.conf".split())
		for i in [ "SRCDEST", "PKGDEST", "SRCPKGDEST", "LOGDEST" ]:
			if i in lines and not i.lstrip().startswith('#'):
				tokens=i.lstrip().rstrip("\n").split("=")
				parameters.append("{}:{}".format(tokens[1], tokens[1]))
		return parameters

if __name__ == '__main__':
	dm = dmakepkg()
	dm.main()