#!/bin/bash
usage() {
	cat <<-EOF
	usage: $(basename "$0") [OPTIONS] [makepkg parameters]

	This wrapper for makepkg will default to running with '--force --syncdeps --noconfirm'.
	Any unrecognized parameters will be passed directly through to makepkg.

	OPTIONS:
	-h	Display this help
	-p	Run a pacman -Syu before building
	-u	UID to own any created package
	-g	GID to own any created package (Ignored unless UID is also provided)
	-e  CMD to run the command after the source directory was copied
	-z  Do not automatically download missing PGP keys
	EOF
}

autoDownload=true
usePump=true

set +e
TEMP=$(getopt -n "$name" -o "xyze:" -- "$@")
set -e

if [ $? -ne 0 ]
then
	echo 'Terminating...' >&2
	exit 1
fi

eval set -- "$TEMP"
unset TEMP

while true
do
	case "$1" in
		'-g')
			group=$OPTARG
			continue
			;;
		'-h')
			usage
			exit 0
			;;
		'-p')
			update=true
			continue
			;;
		'-u')
			user="$OPTARG"
			continue
			;;
		'-e')
			CMD="$OPTARG"
			continue
			;;
		'-z')
			autoDownload=false
			continue
			;;
		'-y')
			usePump=false
			continue
			;;
		'--')
			shift
			break
			;;
		*)
			echo 'Internal error!' >&2
			exit 1
		esac
done

if ! [[ -f /src/PKGBUILD ]]
then
	echo "No PKGBUILD file found! Aborting."
	exit 1
fi


# cp errors if there is a directory, even though we don't want to copy directories
cp /src/* /build 2> /dev/null
set -e
chown -R build-user. /build

$CMD

if [[ -n $update ]]
then
	pacman -Syu
else
	pacman -Sy
	if [[ -n $@ ]]
	then
		flags=$@
	else
		flags='--force --syncdeps --noconfirm'
	fi
fi

if [ $autoDownload ]
then
	mkdir ~build-user/.gnupg
	chown -R build-user:build-user ~build-user/.gnupg
	chmod -R 700 ~build-user/.gnupg
	echo "keyserver-options auto-key-retrieve" >>  ~build-user/.gnupg/gpg.conf
fi
# check if any servers in DISTCC_HOSTS contain ",cpp"
# If they do, use pump mode by default
source /etc/makepkg.conf

export DISTCC_HOSTS

if [[ "$DISTCC_HOSTS" =~ ",cpp" && "$usePump" = true ]]
then
	su build-user -p -s /bin/bash -c "pump makepkg $flags"
else
	su build-user -p -s /bin/bash -c "makepkg $flags"
fi

if [[ -n $user ]]
then
	chown="$user"
	if [[ -n $group ]]
	then
		chown="${chown}:${group}"
	fi
	chown -R $chown /build
fi

# Don't fail if there is no pkg but custom flags were specified. i.e. -cors will only test, but not create a package
cp /build/*pkg.tar* /src &>/dev/null || [[ -n $@ ]]
