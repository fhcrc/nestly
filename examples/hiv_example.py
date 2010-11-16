#!/usr/bin/env python

import sys
sys.path.append("..")
import simpal, os, glob, copy

homedir = "/cs/researcher/matsen/Overbaugh_J/HIV_Data/"

# building our dictionaries
control = {
    "ref" : 
    	simpal.prep(
	  os.path.join(homedir,"sim/old/clean_fullGenomeLANL/"),
	  ["ag.fasta"]),
    "frag" : 
    	simpal.prep(
	  os.path.join(homedir,"sim/beastly/"),
	  ["singly/*/*/*.fasta", "super/*/*/*.fasta"]),
    "beast_template" : 
	simpal.prep(
	  os.path.join(homedir,"scripts/beast_corral/"),
	  ["hky.coalescent.xml"]),
    }

order = [
    "ref",
    "beast_template",
    "frag",
    ]

complete = {
    "control": control,
    "order": order,
    }

simpal.build(complete)

