#!/usr/bin/env python

import sys, os
sys.path.append(".")
sys.path.append("..")
from simpal import *

homedir = "/cs/researcher/matsen/Overbaugh_J/HIV_Data/"
refdir = os.path.join(homedir,"sim/old/clean_fullGenomeLANL/")
fragdir = os.path.join(homedir,"sim/beastly/frags")
corraldir = os.path.join(homedir,"scripts/beast_corral/")

# building our dictionaries
control = {
	#"ref": 
	#    all_choices(file_nv, homedir, ["ag.fasta"]),
	"beast_template": 
	    all_choices(file_nv, corraldir, ["hky.coalescent.xml"]),
	"is_superinf": 
	    all_globs(dir_nv, fragdir, ["*"]),
	"length": 
	    (lambda(c): map(dir_nv, collect_globs(c["is_superinf"], "*"))),
	"locus": 
	    (lambda(c): map(dir_nv, collect_globs(c["length"], "*"))),
	"frag": 
	    (lambda(c): map(file_nv, collect_globs(c["locus"], "*"))),
	}

order = [
	"beast_template",
	"is_superinf",
	"length",
 	"locus",
	"frag",
    ]

complete = {
    "control": control,
    "order": order,
    }

build(complete)


#	  ["singly/*/*/*.fasta", "super/*/*/*.fasta"]),

