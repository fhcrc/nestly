import json, os, glob

homedir = "/cs/researcher/matsen/Overbaugh_J/HIV_Data/"

# functions
def path_list_of_pathpair(path, filel):
  return([os.path.join(path, x) for x in filel])

def nonempty_glob(g):
  globbed = glob.glob(g)
  if globbed == []:
    raise IOError("empty glob: "+g)
  else:
    return(globbed)

def nonempty_glob_pathpair(path, globl):
  return(sum([nonempty_glob(g) for g in path_list_of_pathpair(path, globl)], []))

def json_of_file(fname):
  with open(fname, 'r') as ch:
    return(json.load(ch))

def json_to_file(fname, d):
  with open(fname, 'w') as ch:
    ch.write(json.dumps(d, indent=4))

# building our dictionaries

control = {
    "lineage" : "",
    "ref" : "REF",
    "frag" : "FRAG",
    "beast_template" : "TEMPLATE"
    }

repl = {
    "REF": 
    	nonempty_glob_pathpair(
	  os.path.join(homedir,"sim/old/clean_fullGenomeLANL/"),
	  ["ag.fasta"]),
    "TEMPLATE": 
	nonempty_glob_pathpair(
	  os.path.join(homedir,"scripts/beast_corral/"),
	  ["hky.coalescent.xml"]),
    "FRAG": 
    	nonempty_glob_pathpair(
	  os.path.join(homedir,"sim/beastly/"),
	  ["singly/*", "super/*"]),
    }

order = [
    "REF",
    "TEMPLATE",
    "FRAG",
    ]

complete = {
    "control": control,
    "repl": repl,
    "order": order,
    }

json_to_file("complete.json", complete)
