#! /bin/python3 -B

import atexit
import ipaddress
import netifaces
import os
import subprocess
import sys

## Dockerfile generator
class dmakepkgBuilder:
	head = """FROM archimg/base:latest\nLABEL tool=docker-makepkg\nRUN echo -e "[multilib]\\nInclude = /etc/pacman.d/mirrorlist" >> /etc/pacman.conf"""
	tail = ("""RUN pacman -Syuq --noconfirm --needed gcc base-devel distcc python git mercurial bzr subversion openssh && rm -rf /var/cache/pacman/pkg/*\n"""
	"RUN useradd -m -d /build -s /bin/bash build-user\n"
	"ADD sudoers /etc/sudoers\n"
	"""WORKDIR /build\n"""
	"""VOLUME "/src\"\n"""
	"ADD run.py /run.py\n"
	"""ENTRYPOINT ["/run.py"]\n""")


	def __init__(self):
		self.pacmanCacheDir = "/var/cache/pacman/pkg"
		self.pacmanCachePort = "8990"
		self.cache = True

	def getdocker0Address(self):
		try:
			addresses = netifaces.ifaddresses('docker0')
		except:
			eprint("No docker0 interface exists. Looks like you don't run docker?")
			# we could actually theoretically use an IP from any interface, but I want
			# to make sure to not make any holes into existing rule sets that protect other interfaces.
			sys.exit(1)
		else:
			# check for IPv4 and IPv6 addresses. We can't use link-local ones though,
			# because the address specified for those needs to contain the name 
			# of the interface that needs to be used to reach the destination address and I don't know of a way to predict it
			# in docker.
			for (family, addressList) in addresses.items():
				if family == netifaces.AF_INET:
					for addressDict in addressList:
						return ipaddress.ip_address(addressDict["addr"])
				elif family == netifaces.AF_INET6:
					for addressDict in addressList:
						ipv6Address = ipaddress.ip_address(addressDict["addr"])
						if not ipv6Address.is_link_local():
							return ipaddress.ip_address(addressDict["addr"])
			eprint("No suitable address found for the local cache. Therefore the local cache is disabled.")
			return None

	def pacmanCacheExists(self):
		return os.path.exists(self.pacmanCacheDir)

	def createDockerfile(self):
		if self.cache:
			complete = self.head + "\nRUN /bin/bash -c 'cat <(echo Server = http://{}:{}) /etc/pacman.d/mirrorlist > foobar && mv foobar /etc/pacman.d/mirrorlist'\n" \
			.format(self.pacmanCacheIp.compressed, self.pacmanCachePort) +  self.tail
		else:
			complete = self.head + self.tail
		# write file
		scriptLocation = os.path.realpath(__file__)

		with open(os.path.join(os.path.dirname(scriptLocation), "Dockerfile"), "w") as dockerFile:
			dockerFile.write(complete)

	def startDockerBuild(self):

		args = [ "/bin/docker", "build", "--pull", "--no-cache", "--tag=makepkg", os.path.dirname(os.path.realpath(__file__)) ]

		dockerBuild = subprocess.run(args)


	def startLocalCache(self):
		# runs darkhttpd
		args = ["/usr/bin/darkhttpd", self.pacmanCacheDir, "--port", self.pacmanCachePort ]
		self.darkhttpdProcess = subprocess.Popen(args)

	def stopLocalCache(self):
		self.darkhttpdProcess.terminate()

	def insertIptablesRules(self):
		comm = {
			4 : "/bin/iptables",
			6 : "/bin/ip6tables"
		}[self.pacmanCacheIp.version]
		args = "{} -w 5 -W 2000 -I INPUT -p tcp --dport 8990 -i docker0 -d {} -j ACCEPT".format(comm, self.pacmanCacheIp.compressed).split()
		subprocess.run(args)

	def deleteIptablesRules(self):
		comm = {
			4 : "/bin/iptables",
			6 : "/bin/ip6tables"
		}[self.pacmanCacheIp.version]
		args = "{} -w 5 -W 2000 -D INPUT -p tcp --dport 8990 -i docker0 -d {} -j ACCEPT".format(comm, self.pacmanCacheIp.compressed).split()
		subprocess.run(args)
	
	def main(self):
		# check the docker0 address
		ip = self.getdocker0Address()

		if not ip or not self.pacmanCacheExists():
			self.cache = False
		self.pacmanCacheIp = ip

		# create and write Dockerfile
		self.createDockerfile()

		# start darkhttpd
		self.startLocalCache()
		# make sure it gets stopped if the script exits
		atexit.register(self.stopLocalCache)

		# insert iptables rule
		self.insertIptablesRules()
		
		# make sure it gets cleaned up if the script exits
		atexit.register(self.deleteIptablesRules)

		self.startDockerBuild()
		sys.exit(0)

if __name__ == "__main__":
	builder = dmakepkgBuilder()
	builder.main()