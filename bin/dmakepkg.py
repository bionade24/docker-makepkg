#! /bin/python3 -B

import argparse
import os
import subprocess
import sys
import uuid

class dmakepkg:
	__eDefaults = "--nosign --force --syncdeps --noconfirm"
	def __init__(self):
		self.pacmanConf="/etc/pacman.conf"
		self.makepkgConf="/etc/makepkg.conf"
		self.pacmanPkgCache="/var/cache/pacman/pkg"

	# From https://stackoverflow.com/questions/17435056/read-bash-variables-into-a-python-script
	# Written by user Taejoon Byun
	def getVar(self, script, varName):
		CMD = 'echo $(source "{}"; echo ${{{}[@]}})'.format(script, varName)
		p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
		return p.stdout.readlines()[0].decode("utf-8").strip()

	# From https://stackoverflow.com/questions/17435056/read-bash-variables-into-a-python-script
	# Written by user Taejoon Byun
	def callFunc(self, script, funcName):
		CMD = 'echo $(source {}; echo $({}))'.format(script, funcName)
		p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
		return p.stdout.readlines()[0].decode("utf-8").strip()

	def signPackages(self):
		args = [ "/bin/gpg", "--batch", "--yes", "--detach-sign" ]
		key = self.getVar(self.makepkgConf, "GPGKEY")
		if key:
			args.extend(["-u", key])
		f = []
		for (dirpath, dirnames, filenames) in os.walk(os.getcwd()):
			f.extend(filenames)
			break
		
		for i in f:
			if ".pkg." in i and not i.endswith("sig"):
				g = []
				g.extend(args)
				g.append(i)
				subprocess.run(g)



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

		self.parser.add_argument('rest', nargs=argparse.REMAINDER,
			help="The arguments that are passed to the call to pacman in its executions in the container. They default to \"--nosign --force --syncdeps --noconfirm\".")

		namespace = self.parser.parse_args()

		parameters = [ "--name", "dmakepkg_{}".format(uuid.uuid4())]

		# pacman.conf is not a bash file, so this doesn't work.
		# localCacheDir = self.getVar(self.pacmanConf, "CacheDir")
		# if not localCacheDir:
		#	localCacheDir = "/var/cache/pacman/pkg"
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

		# set object attributes
		# self.hostPacmanConf = namespace.
		# create first part
		completeCmdLine = "/bin/docker run --rm -ti --cpu-shares=128 --pids-limit=-1".split(" ")


		completeCmdLine += ["-v", "{}:/src".format(os.getcwd())] + parameters + [ "makepkg" ]

		if not self.downloadKeys:
			completeCmdLine.append("-x")
		if not self.usePumpMode:
			completeCmdLine.append("-y")
		completeCmdLine.extend(["-u", str(os.geteuid()), "-g", str(os.getegid())])
		if self.command:
			completeCmdLine.extend(["-e", self.command])
		completeCmdLine += namespace.rest
		print("Cmdline: ", completeCmdLine)

		dockerProcess = subprocess.Popen(completeCmdLine)
		dockerProcess.wait()

		for i in self.getVar(self.makepkgConf, "BUILDENV").split():
			if "sign" in i:
				if not i.startswith("!"):
					self.signPackages()

	# this function finds all possible arguments to the docker command line we could need
	# and builds them.
	def findParameters(self):
		parameters=[ "-v", "/etc/makepkg.conf:/etc/makepkg.conf:ro" ]

		for i in [ "SRCDEST", "PKGDEST", "SRCPKGDEST", "LOGDEST" ]:
			value =  self.getVar(self.makepkgConf, i)
			if value != "":
				parameters.extend([ "-v",  "{}:{}".format(i, value)])
		return parameters

if __name__ == '__main__':
	dm = dmakepkg()
	dm.main()