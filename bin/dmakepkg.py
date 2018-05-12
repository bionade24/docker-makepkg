#! /bin/python -B

import argparse
import os
import subprocess
import sys
import uuid

class dmakepkg:
	pacmanConf="/etc/pacman.conf"
	makepkgConf="/etc/makepkg.conf"
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

		if namespace.x:
			parameters.extend("-v /etc/pacman.conf:/etc/pacman.conf".split(" "))

		self.usePumpMode = namespace.y
		self.downloadKeys = namespace.z
		self.command = namespace.e

		parameters.extend(self.findParameters())
		print("Parameters: ", parameters)

		# set object attributes
		# self.hostPacmanConf = namespace.
		# create first part
		completeCmdLine = "/bin/docker run --rm --net=host -ti".split(" ")
		completeCmdLine += ["-v", "{}:/src".format(os.getcwd())] + parameters + [ "makepkg" ]
		#completeCmdLine.extend(parameters)

		if self.downloadKeys:
			completeCmdLine.append("-x")
		if self.usePumpMode:
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
			pass
		else:
			parameters.extend("-v /etc/makepkg.conf:/etc/makepkg.conf".split())
			for i in [ "SRCDEST", "PKGDEST", "SRCPKGDEST", "LOGDEST" ]:
				if i in lines and not i.lstrip().startswith('#'):
					tokens=i.lstrip().rstrip("\n").split("=")
					parameters.append("{}:{}".format(tokens[1], tokens[1]))
		return parameters

if __name__ == '__main__':
	dm = dmakepkg()
	dm.main()