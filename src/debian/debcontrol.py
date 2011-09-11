"""
module debian.debcontrol

@author: Ximin Luo <infinity0@gmx.com> 
"""

from itertools import chain
from debian.debutil import cont_check, cont_test
from debian.util import itercut, uninvert_idx, freq
from debian.parse import MKVCParser, LeafParser
from collections import namedtuple


class ItemCstr(namedtuple(
	"ItemCstr", "head min")):

	def check(self, items):
		items = iter(items)
		try:
			first = next(items)
			if self.head and first != self.head:
				raise SyntaxError(
				  "unexpected head '%s', should be '%s'" % (first, self.head))

			q = freq(chain([first], items))
		except StopIteration:
			q = freq([])

		for k, m in self.min.iteritems():
			c = q.get(k, 0)
			if c < m:
				raise SyntaxError(
				  "minimum expected count %s for %s not reached: %s" % (m, k, c))
		return True

	@classmethod
	def Simple(cls, req, opt):
		return cls.SimpleWithHead(None, req, opt)

	@classmethod
	def SimpleWithHead(cls, head, req, opt):
		return cls(head,
		  dict([(r, 1) for r in req] + [(o, 0) for o in opt]))


def extraPparagraph(chunk, was_block):
	if not chunk or chunk.isspace():
		return True
	elif not was_block and extraPcomment(chunk, was_block):
		return True
	else:
		return False

def extraPcomment(chunk, was_block):
	return chunk.lstrip().startswith('#')

def blockPnever(chunk, was_block):
	return not was_block

def blockPcolon(chunk, was_block):
	if ':' in chunk:
		return True
	else:
		cont_check(chunk)
		return False

def keyXcolon(block):
	s, pri0 = block[0].split(':', 1)
	pri, aux = itercut(cont_test, block[1:])
	return s, [pri0] + pri, aux

def keyUcolon(s, pri, aux):
	return ["%s:%s" % (s, pri[0])] + pri[1:] + aux

class _BaseLCParser(MKVCParser):
	def cstrKeys(self, con):
		check_pre = lambda keystr, primary, keyidx, extras: \
			con.check(uninvert_idx(keyidx))
		return self.add_check_pre(check_pre)

BaseLCParser = _BaseLCParser(
	lambda x: x, lambda _: LeafParser,
	None, None,
	lambda s: s.strip().lower(),
	None, None,
	(), (),
)

ColonParser = BaseLCParser.use(
	keyX=keyXcolon,
	keyU=keyUcolon,
)

ParagraphParser = ColonParser.use(
	extraP=extraPcomment,
	blockP=blockPcolon,
)

ControlParser = ColonParser.use(
	extraP=extraPparagraph,
	blockP=blockPnever,
)

def SimpleControlBlock(model, req, opt):
	combo = dict(opt.items() + req.items())
	return ParagraphParser.use(omaker=model).cstrKeys(
	  ItemCstr.Simple(req.keys(), opt.keys())
	).use(
	  pselect=lambda k: LeafParser.use(omaker=combo.get(k))
	)
