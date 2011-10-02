"""
module debian.copyright

@author: Ximin Luo <infinity0@gmx.com>
"""

from debian.debutil import (v_single, v_list, v_text, v_text_synop, v_words)
from debian.debcontrol import SimpleControlBlock, ControlParser, \
	ItemCstr
from debian.license import LicenseSpec
from debian.parse import PresetRootParser
from debian.changelog import Changelog
from itertools import chain
import sys


def warn(fmtstr, args=(), desc=None):
	print >>sys.stderr, "W:", fmtstr % args
	if desc:
		print >>sys.stderr, " :", desc


def lcspec_text_synop(lines):
	syn, desc = v_text_synop(lines)
	return LicenseSpec.parse(syn), desc


EXACT, MATCH_ONE, MATCH_ANY = range(3)

def _match1char(c, pattern_, path):
	return path and c == path[0] and globDEP5(pattern_, path[1:])

def _poptoken(pattern):
	c, pattern = pattern[0], pattern[1:]
	if c == "\\":
		c, pattern = pattern[0], pattern[1:]
		if c in "\\*?":
			return (EXACT, c), pattern
		else:
			raise SyntaxError("can only escape [\\*?]: %s" % c)
	elif c == "*":
		return (MATCH_ANY, None), pattern
	elif c == "?":
		return (MATCH_ONE, None), pattern
	else:
		return (EXACT, c), pattern

def globDEP5(pattern, path):
	#print repr((pattern, path))
	if not pattern: return not path
	(t, c), pattern = _poptoken(pattern)

	if t == EXACT:
		return _match1char(c, pattern, path)
	elif t == MATCH_ONE:
		return path and globDEP5(pattern, path[1:])
	elif t == MATCH_ANY:
		'''
		return any(
		  globDEP5(pattern, path[i:])
		  for i in xrange(0, len(path) + 1))
		'''
		# optimisation of the above naive algorithm; this
		# makes e.g. globDEP5("********a", "zzzzzzzzzzzzzzzzzzzzzzzb")
		# run in a sane amount of time
		while t == MATCH_ANY:
			if not pattern: return True
			(t, c), pattern = _poptoken(pattern)
			if t == EXACT:
				cand = filter(lambda x: x[1] == c, enumerate(path))
				ii = [i for i, _ in cand]
				return any(
				  globDEP5(pattern, path[i + 1:])
				  for i in ii)
			elif t == MATCH_ONE:
				if not path: return False
				path = path[1:]
	raise AssertionError

def copyright_check_post(state):
	licenses = {}  # { License : [ ( LicenseSpec, has_full_text, standalone ) ] }

	for li_block in [state.get("format")] + state.getall("files"):
		lcinfo = li_block.get("license")
		if not lcinfo: continue
		spec, text = lcinfo.model()
		has_text = not not "".join(text).strip()
		leaves = [spec.base()] if spec.is_leaf() else spec.leaves()
		for leaf in leaves:
			refs = licenses.setdefault(leaf, [])
			refs.append((spec, has_text, False))

	for lc_block in state.getall("license"):
		spec, text = lc_block.model()
		has_text = not not "".join(text).strip()
		if spec.is_leaf():
			refs = licenses.setdefault(spec.base(), [])
			refs.append((spec, has_text, True))
		else:
			raise SyntaxError("Can only specify non-compound License blocks: %s" % spec)

	def _no_standalone_no_text(ref):
		spec, has_text, standalone = ref
		return not standalone and not has_text

	def _standalone_with_text(ref):
		spec, has_text, standalone = ref
		return standalone and has_text

	def _compound_no_standalone_with_text(ref):
		spec, has_text, standalone = ref
		return not spec.is_leaf() and not standalone and has_text

	def _has_text(ref):
		spec, has_text, standalone = ref
		return has_text

	# - error when a {file/format license without full text} does not
	#   have license blocks for any of its components
	# - specified by DEP-5
	error_lc_block = filter(
		lambda lc: filter(_no_standalone_no_text, licenses[lc])
			and not filter(_standalone_with_text, licenses[lc]),
		licenses)
	if error_lc_block:
		raise SyntaxError("License in File/Format block with neither full text nor License block: %s" % error_lc_block)

	# - warn on {compound file/format license with full text}, instead
	#   recommend full texts be split
	no_standalone_with_text = filter(
		lambda lc: not not filter(_compound_no_standalone_with_text, licenses[lc]),
		licenses)
	if no_standalone_with_text:
		warn("Full text for compound License in File/Format block: %s", no_standalone_with_text,
			("This is permitted by DEP-5, but we believe it is clearer to split the full text of "
			 "each license into separate License blocks. If you need to clarify exactly how these "
			 "licenses are combined, please use the Comment field for that purpose. "))

	# - warn on multiple full texts for same license
	multi_text = filter(
		lambda lc: len(filter(_has_text, licenses[lc])) > 1,
		licenses)
	if multi_text:
		warn("Licenses with multiple full texts: %s", multi_text,
			("This is permitted by DEP-5, but we believe it is clearer to refactor these into a "
			 "single License block. If the usage of each License differs for each occurence, "
			 "please use the Comment field for that purpose. "))

	# - warn when non-native package, but no separate debian/* clause
	meta = state.model()
	globs = [glob
		for fi_block in state.getall("files")
		for glob in fi_block.model()]
	if "changelog" in meta and \
	  meta["changelog"].get_version().debian_revision is not None and \
	  all(not glob.startswith("debian/") for glob in globs):
		warn("Non-native package without debian/[etc] glob: %s", globs,
			("Non-native packages usually have different upstream author and debian maintainer. "
			 "In such cases the copyrights will be different for each set of files. "
			 "If they are the case, you may ignore this warning, but it may be clearer to "
			 "split the glob patterns even so, in case this arrangement ceases in the future. "))

	#for k, vv in licenses.iteritems():
	#	print k
	#	for v in vv:
	#		print "\t", v


DebianCopyright = ControlParser.cstrKeys(
  ItemCstr.SimpleWithHead("format", [], ["files", "license"])
).add_check_post(
	copyright_check_post
).use(omaker=lambda chunks:
	{"changelog": Changelog(chunks)} if chunks else {}
).use(pselect={
	"format" : SimpleControlBlock(v_single, {}, {
		"upstream-name": v_single,
		"upstream-contact": v_list,
		"source": v_text,
		"disclaimer": v_text,
		"copyright": v_list,
		"license": lcspec_text_synop,
	}),
	"files" : SimpleControlBlock(v_words, {
		"copyright": v_list,
		"license": lcspec_text_synop,
	}, {
		"comment": v_text,
	}),
	"license" : SimpleControlBlock(lcspec_text_synop, {}, {
		"location": v_single,
	}),
}.get)


def DebianCopyrightMeta(fn):
	with open(fn) as fp:
		return PresetRootParser(fp.readlines())


def get_license_for_file(state, fn):
	for fi_block in state.getall("files").__reversed__():
		for glob in fi_block.model().__reversed__():
			if globDEP5(glob, fn):
				return fi_block

def get_full_text_for_license(state, lc):
	for fi_block in state.getall("files"):
		lcinfo = fi_block.get("license")
		spec, text = lcinfo.model()
		# TODO(infinity0): rethink, either return one or all?
		# and what about where full text belongs to a compound license?


