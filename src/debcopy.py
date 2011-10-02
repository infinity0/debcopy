#!/usr/bin/python

import sys
import os
from debian.copyright import DebianCopyright, DebianCopyrightMeta, get_license_for_file


def main(prog, fn, *args):
	pp = DebianCopyrightMeta(os.path.join(os.path.dirname(fn), "changelog"))
	cr = DebianCopyright.load(fn, pp)
	cr.save(fn + ".re")
	#cr.inspect()
	#print cr.pretty()
	for arg in args:
		print arg
		print get_license_for_file(cr, arg)


if __name__ == "__main__":
	sys.exit(main(*sys.argv))
