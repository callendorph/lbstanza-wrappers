import os
from setuptools import setup

__version__ = "0.3.0"

def read(fname):
	try:
		return open(os.path.join(os.path.dirname(__file__), fname)).read()
	except:
		return "No Long Description"

setup(
	name="lbstanza-wrappers",
	version=__version__,
	description="Utility to create lbstanza wrappers from C headers",
	long_description=read("long_description.rst"),
	license="GPLv3",
	keywords="lbstanza wrappers utility",
	author="Carl Allendorph",
	url="https://github.com/callendorph/lbstanza-wrappers",
	packages=["lbstanza_wrappers"],
	install_requires=[
		"pycparser>=2.0",
		"pycparser-fake-libc>=2.0",
	],
	scripts=[
		"convert2stanza.py",
		"dump-c-header.py"
	],
	classifiers=[
		"Development Status :: 3 - Alpha",
		"Topic :: Utilities",
	],
)
