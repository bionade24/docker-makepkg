#! /bin/python3 -B

import argparse
import glob
import os
import os.path
import pwd
import subprocess
import shutil
import shlex
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class dmakepkgContainer:
    __restDefaults = "--nosign --force --syncdeps --noconfirm"

    # From https://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth/12514470
    # Written by user atzz
    def copytree(self, src, dst, symlinks=False, ignore=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

    # to not change either gid or uid, set that value to -1.
    # From https://stackoverflow.com/questions/2853723/what-is-the-python-way-for-recursively-setting-file-permissions
    # Written by user "too much php"
    def changeUserOrGid(self, uid, gid, path):
        for root, dirs, files in os.walk(path):
            for momo in dirs:
                os.chown(os.path.join(root, momo), uid, gid)
            for momo in files:
                os.chown(os.path.join(root, momo), uid, gid)

    # From https://www.tutorialspoint.com/How-to-change-the-permission-of-a-directory-using-Python
    # Written by Rajendra Dharmkar
    def changePermissionsRecursively(self, path, mode):
        for root, dirs, files in os.walk(path, topdown=False):
            for dir in [os.path.join(root,d) for d in dirs]:
                os.chmod(dir, mode)
            for file in [os.path.join(root, f) for f in files]:
                os.chmod(file, mode)

    def appendToFile(self, path, content):
        with open(path, "a+") as f:
            f.seek(0,2)
            f.write(content)

    # From https://stackoverflow.com/questions/17435056/read-bash-variables-into-a-python-script
    # Written by user Taejoon Byun
    def getVar(self, script, varName):
        CMD = 'echo $(source "{}"; echo ${{{}[@]}})'.format(script, varName)
        p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
        return p.stdout.readlines()[0].decode("utf-8").strip()

    # From https://stackoverflow.com/questions/17435056/read-bash-variables-into-a-python-script
    # Written by user Taejoon Byun
    def callFunc(self, script, funcName):
        CMD = 'echo $(source "{}"; echo $({}))'.format(script, funcName)
        p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
        return p.stdout.readlines()[0].decode("utf-8").strip()

    def checkForPumpMode(self):
        distccHosts = self.getVar("/etc/makepkg.conf", "DISTCC_HOSTS")
        if ",cpp" in distccHosts and self.usePumpMode:
            return True
        return False

    def main(self):
        self.parser = argparse.ArgumentParser(prog="dmakepkgContainer")
        self.parser.add_argument('-e',
            nargs='?',
            help="CMD to run the command after the source directory was copied")
        self.parser.add_argument('-g',
            nargs='?',
            help="The GID to own any created package (Ignored unless UID is also provided")
        self.parser.add_argument('-p',
            action='store_true',
            help="Run a pacman -Syu before building")
        self.parser.add_argument('-u',
            nargs='?',
            help="UID to own any created package")
        self.parser.add_argument('-y',
            action='store_false',
            help="Do not use pump mode.")
        self.parser.add_argument('-z',
            action='store_false',
            help="Do not automatically download missing PGP keys")

        namespace, self.rest = self.parser.parse_known_args()

        if not os.path.isfile("/src/PKGBUILD") or os.path.islink("/src/PKGBUILD"):
            eprint("No PKGBUILD file found! Aborting.")
            sys.exit(1)

        self.command = namespace.e
        self.group = int(namespace.g)
        self.runPacmanSyu = namespace.p
        self.user = int(namespace.u)
        self.usePumpMode = namespace.y
        self.downloadKeys = namespace.z
        buildUserUid = pwd.getpwnam("build-user").pw_uid
        buildUserGid = pwd.getpwnam("build-user").pw_gid
        self.copytree("/src/", "/build")
        self.changeUserOrGid(buildUserUid, buildUserGid, "/build")

        

        if self.runPacmanSyu:
            arguments = "pacman --noconfirm -Syu".split()
            pacmanProcess = subprocess.Popen(arguments)
            pacmanProcess.wait()
        else:
            arguments = "pacman --noconfirm -Sy".split()
            pacmanProcess = subprocess.Popen(arguments)
            pacmanProcess.wait()
        flags = None

        if len(self.rest) == 0:
            flags = self.__restDefaults.split()
        else:
            # translate list object to space seperated arguments
            flags = self.rest

        if self.downloadKeys:
            gnupg = os.path.expanduser("~build-user/.gnupg")
            os.makedirs(gnupg, mode=0o700, exist_ok=True)
            self.changeUserOrGid(buildUserUid, pwd.getpwnam("build-user").pw_gid, "/build")
            self.changePermissionsRecursively(gnupg, 0o700)
            self.appendToFile(gnupg + "/gpg.conf", "keyserver-options auto-key-retrieve\n")
            self.changePermissionsRecursively(gnupg + "/gpg.conf", 0o600)

        # if a command is specified in -e, then run it
        if self.command:
            args = shlex.split(self.command)
            subprocess.run(args)

        # su resets PATH, so distcc doesn't find the distcc directory
        if self.checkForPumpMode():
            bashFileContents="#! /bin/bash\n"
            "pump makepkg {}\n".format(" ".join(flags))
            with open("/buildScript.sh", "w") as f:
                f.write(bashFileContents)
            self.changePermissionsRecursively("/buildScript.sh", 0o555)
            arguments = [ 'su', '-c' ] +  [ 'DISTCC_HOSTS="{}" DISTCC_LOCATION={} pump makepkg {}'.format(self.getVar("/etc/makepkg.conf", "DISTCC_HOSTS"),
                "/usr/bin",
                " ".join(flags)) ] + [ '-s', '/bin/bash', 'build-user' ]
            makepkgProcess = subprocess.run(arguments)

            # while makepkgProcess.poll() == None:
            #     outs, errs = makepkgProcess.communicate(input="")
            #     if outs:
            #         print(outs)
            #     if errs:
            #         eprint(errs)
        else:
            arguments = [ 'su', '-c'] +  [ 'makepkg {}'.format(" ".join(flags)) ] + [ '-s', '/bin/bash', '-l', 'build-user']
            makepkgProcess = subprocess.Popen(arguments)
            while makepkgProcess.poll() == None:
                outs, errs = makepkgProcess.communicate(input="")
                if outs:
                    print(outs)
                if errs:
                    eprint(errs)

        if self.user and not self.group:
            self.changeUserOrGid(self.user, self.group, "/build")
        elif self.user:
            self.changeUserOrGid(self.user, -1, "/build")

        # copy any packages
        # use globbing to get all packages
        for i in glob.iglob("/build/*pkg.tar*"):
            shutil.copy(i, "/src")
        else:
            if not len(flags):
                eprint("No packages were built!")
                sys.exit(2)
        sys.exit(0)

if __name__ == "__main__":
    containerEntrypoint = dmakepkgContainer()
    containerEntrypoint.main()

#"PATH" : self.getVar("~build-user/.bashrc", "PATH")
