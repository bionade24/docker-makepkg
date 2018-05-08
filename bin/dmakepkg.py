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

		# set object attributes
		# self.hostPacmanConf = namespace.
		# create first part
		completeCmdLine = "/bin/docker --rm --net=host -ti ".split(" ").extend(
			["-v", "{}:/src".format(os.getcwd())])
		completeCmdLine.extend(parameters)
		completeCmdLine.append("makepkg")

		if self.dontDownloadKeys:
			completeCmdLine.append("-x")
		if self.usePumpMode:
			completeCmdLine.append("-y")
		completeCmdLine.extend(["-u", os.geteuid(), "-g", os.getegid(), rest])

		print("cmdline: ", completeCmdLine)
		dockerProcess = subprocess.Popen(completeCmdLine)
		dockerProcess.wait()


	# this function finds all possible arguments to the docker command line we could need
	# and builds them.
	def findParameters(self):
		parameters=[]
		try:
			lines = open(self.makepkgConf, "r").readlines()
			print("Lines: ", lines)
		except:
			# makepkg doesn't exist
			pass
		else:
			parameters.append("-v /etc/makepkg.conf:/etc/makepkg.conf".split())
			for i in [ "SRCDEST", "PKGDEST", "SRCPKGDEST", "LOGDEST" ]:
				if i in lines and not i.lstrip().startswith('#'):
					print("Line: ", i)
					tokens=i.lstrip().rstrip("\n").split("=")
					parameters.append("{}:{}".format(tokens[1], tokens[1]))
		return parameters





if __name__ == '__main__':
	dm = dmakepkg()
	dm.main()