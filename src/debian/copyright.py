"""
module debian.copyright

@author: Ximin Luo <infinity0@gmx.com>
"""

from debian.debutil import (v_single, v_list, v_text, v_text_synop, v_words)
from debian.debcontrol import SimpleControlBlock, ControlParser, \
	ItemCstr
from debian.license import LicenseSpec
from itertools import chain


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
	simple = []
	compound = []
	# TODO(infinity0): redo this section
	# - error when a {multi-license without full text} does not
	#   have license blocks for any of its components
	# - warn against multiple full texts for same license
	# - warn against {multi-license with full text}, instead
	#   recommend full texts be split
	# - warn non-native package, but no separate debian/* clause

	for li_block in [state.get("format")] + state.getall("files"):
		lcinfo = li_block.get("license")
		if not lcinfo: continue
		spec, text = lcinfo.model()
		if spec.is_leaf():
			simple.append(spec.base())
		else:
			compound.append(spec)

	for lc_block in state.getall("license"):
		spec, text = lc_block.model()
		if spec.is_leaf():
			simple.append(spec.base())
		else:
			raise SyntaxError("Can only specify non-compound License blocks: %s" % spec)

	referred = set(chain(*(spec.leaves() for spec in compound)))
	simple = set(simple)
	dangling = referred - simple
	if dangling:
		raise SyntaxError("Licenses without stand-alone full text: %s" % dangling)


DebianCopyright = ControlParser.cstrKeys(
  ItemCstr.SimpleWithHead("format", [], ["files", "license"])
).add_check_post(
	copyright_check_post
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
