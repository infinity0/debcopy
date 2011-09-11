#!/usr/bin/python

import sys
from debian.copyright import DebianCopyright


def main(prog, fn, *args):
	cr = DebianCopyright.load(fn)
	cr.save(fn + ".re")
	#cr.inspect()
	print cr.pretty()


if __name__ == "__main__":
	sys.exit(main(*sys.argv))
