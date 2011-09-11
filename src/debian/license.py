"""
module debian.license

@author: Ximin Luo <infinity0@gmx.com> 
"""

from collections import namedtuple
from itertools import chain, product
import re


class LicenseSpec(object):

	@staticmethod
	def parse(s):
		"""Parse a LicenseSpec from a string."""

		parts = [s]

		parts = re.split(r",\s*or\b", parts[0])
		if len(parts) > 1:
			return OrSpec(map(LicenseSpec.parse, parts))

		parts = re.split(r",\s*and\b", parts[0])
		if len(parts) > 1:
			return AndSpec(map(LicenseSpec.parse, parts))

		parts = re.split(r"\bor\b", parts[0])
		if len(parts) > 1:
			return OrSpec(map(LicenseSpec.parse, parts))

		parts = re.split(r"\band\b", parts[0])
		if len(parts) > 1:
			return AndSpec(map(LicenseSpec.parse, parts))

		# TODO(infinity0): deal with "with X exception"
		return SimpleSpec.parse(parts[0])

	@staticmethod
	def covered_by_specs(specs, lcc, raise_reason=False):
		"""Check that the licenses cover exactly the SimpleSpecs.
		
		I.e. that every license matches >=1 spec,
		and that every spec is matched by >=1 license.
		
		@param specs: set of SimpleSpecs, e.g. a combo
		@param lcc: licenses, or simple-specs
		"""
		# convert any SimpleSpec objects in lcc to License
		lcc = set(lc.base() for lc in lcc)

		# match exact (non-plus) specs; each can only be matched by 1 license
		exact = set(
		  spec.base()
		  for spec in filter(lambda x: not x.plus, specs))
		non_matched = exact.difference(lcc)
		if non_matched:
			if not raise_reason: return False
			raise ValueError("need license to match-exact: %s" % non_matched)

		# match plus specs
		plus_specs = filter(lambda x: x.plus, specs)

		# for the license that didn't match an exact-spec already,
		# make sure they match >=1 plus-spec
		non_exact_matching = lcc.difference(exact)
		for lc in non_exact_matching:
			if not any(spec.matched_by(lc) for spec in plus_specs):
				if not raise_reason: return False
				raise ValueError("no matched specs: %s" % [lc])

		# check that each plus-spec is matched by >=1 license,
		# including licenses that might have already matched an exact-spec
		for spec in plus_specs:
			if not any(spec.matched_by(lc) for lc in lcc):
				if not raise_reason: return False
				raise ValueError("no matching licenses: %s" % [spec])

		return True

	def is_leaf(self):
		return len(self.leaves()) == 1

	def leaves(self):
		"""Return all component licenses of this license-spec."""
		raise NotImplementedError

	def combo(self):
		"""Generate all valid SimpleSpec combinations.
		
		A valid combination is a set of SimpleSpec that can validly cover the
		entire work for this LicenseSpec
		
		@return: frozenset([ frozenset([ sspecs ]) ])
		"""
		raise NotImplementedError

	def covered_by(self, *lcc):
		"""Check that the licenses cover this LicenseSpec."""
		for specs in self.combo():
			try:
				LicenseSpec.covered_by_specs(specs, lcc, True)
				return True
			except ValueError, e:
				#import traceback
				#traceback.print_exc()
				#print "rejected %s: %r" % (specs, e)
				pass
		return False


class License(namedtuple("License", "name version")):

	def base(self):
		return self


class LicenseVersion(tuple):

	@classmethod
	def from_str(cls, s):
		s = s.strip()
		if not s: return cls([])
		ver = [int(p) for p in s.split(".")]
		while not ver[-1]:
			ver.pop()
		return cls(ver)

	def __str__(self):
		return ".".join(str(v) for v in self)


class SimpleSpec(LicenseSpec, namedtuple(
  "SimpleSpec", License._fields + ("plus",))):

	def base(self):
		return License(self.name, self.version)

	def matched_by(self, lc):
		return self.name == lc.name and \
			(self.version <= lc.version
			 if self.plus else
			 self.version == lc.version)

	def leaves(self):
		return frozenset([self.base()])

	def combo(self):
		return frozenset([frozenset([self])])

	def __str__(self):
		return ("%s%s+" if self.plus else "%s%s") % (
		  self.name, "-%s" % self.version if self.version else "")

	@classmethod
	def parse(cls, s):
		s = s.strip()
		if not s:
			return cls("_anon%s" % id(object()), (), False)

		plus = False
		if s and s[-1] == "+":
			plus = True
			s = s[:-1]

		if "-" in s:
			name, version = s.rsplit("-")
		else:
			name, version = s.strip(), ""

		return cls(name, LicenseVersion.from_str(version), plus)


class CompoundSpec(LicenseSpec):

	def leaves(self):
		return frozenset([leaf
		  for part in self.parts
		  for leaf in part.leaves()])

	def subcombos(self):
		return [part.combo() for part in self.parts]


class AndSpec(CompoundSpec, namedtuple("AndSpec", "parts")):

	def combo(self):
		return frozenset(
		  frozenset(chain(*combos))
		  for combos in product(*self.subcombos())
		  )

	def __str__(self):
		return "(%s)" % " and ".join(str(part) for part in self.parts)


class OrSpec(CompoundSpec, namedtuple("OrSpec", "parts")):

	def combo(self):
		return frozenset(chain(*self.subcombos()))

	def __str__(self):
		return "(%s)" % " or ".join(str(part) for part in self.parts)


if __name__ == "__main__":
	bsd = SimpleSpec.parse("BSD")
	gpl2 = SimpleSpec.parse("GPL-2")
	gpl3 = SimpleSpec.parse("GPL-3")
	gpl2p = SimpleSpec.parse("GPL-2+")
	lc1 = OrSpec([gpl2p, AndSpec([bsd, gpl2, gpl3])])
	lc2 = AndSpec([gpl2p, OrSpec([bsd, gpl2, gpl3])])
	assert LicenseSpec.parse("GPL-2+ or Artistic-2.0, and BSD").covered_by(gpl2, bsd)
	import code
	code.interact(local=locals())
