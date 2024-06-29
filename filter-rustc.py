#!/usr/bin/env python3
#
# Reduces Rust compiler warning verbosity where I find it detrimental.
#
# The usage of this script is unfortunately not very straightforward. You need to see
# the `dotfiles/bin/ck` script in this repository to see how to invoke this and show the results.
#
# Development note to self:
# * `cd` to the cargo workspace folder you are debugging, and run `ck check debug`.
# * Modify this script to print something when `args.debug` is True.
#   * You can start with `jqPrint(item)` and check modification results with `print(item["rendered"])`.
# * Finally run `ck check` to see how your modifications changed the full filter output.

import json
import re
import subprocess
import sys

RE_ERROR_CODE = re.compile(r"E\d\d\d\d")
RE_ERROR_EXPLANATIONS = re.compile(r"Some errors have detailed explanations: (.*)\.")

# Print a Python object using `jq`.
# Uses a temporary file to avoid character escaping issues.
def jqPrint(j):
  import tempfile
  # TODO Should work with tempfile, but doesn't (only in some cases?).
  # with tempfile.NamedTemporaryFile(mode="w") as tempFile:
  with open("/tmp/filter-rustc", "w") as tempFile:
    s = json.dumps(j)
    tempFile.write(s)

  with open("/tmp/filter-rustc") as tempFile:
    content = tempFile.read()
    # -C: color
    out = subprocess.check_output(f"cat {tempFile.name} | jq -C .", shell=True).decode('utf-8').strip()
  print(out)

# Print the error as it will show in the rustc output.
def print_rustc_rendered(item):
  if not "rendered" in item: return
  print(item["rendered"])

def readJson(filePath):
  with open(filePath) as f:
    return json.load(f)

# One nice reference: <https://stackoverflow.com/a/21786287>
def colorWarning(s):    return "\x1b[33m" + s + "\x1b[0m"
def colorSuggestion(s): return "\x1b[32m" + s + "\x1b[0m"
def colorError(s):      return "\x1b[31m" + s + "\x1b[0m"
def colorMeta(s):       return "\x1b[37m" + s + "\x1b[0m"

def printWarning(item):
  item = item.copy()
  del item["rendered"]
  print(json.dumps(item, indent=4))

def replaceRendered(item, s, error=False):
  if error: item["rendered"] = colorError(s)
  else: item["rendered"] = colorWarning(s)

def getCodeLocations(item):
  locs = {}
  for i, span in enumerate(item["spans"]):
    name = span["file_name"]
    line = span["line_start"]
    if not name in locs: locs[name] = []
    if line in locs[name]: continue
    locs[name].append(line)

  s = ""
  i = 0
  for name, lines in locs.items():
    if i > 0: s += ", "
    i += 1
    s += name
    for j, line in enumerate(lines):
      if j > 0: s += " "
      s += f":{line}"
  return s

def render(item, locations, message):
  if item["level"] == "error": s = colorError(locations)
  else: s = colorWarning(locations)
  s += f": {message}"
  item["rendered"] = s

# Generic compression that shows the plain "message" field.
def compress(item, compressTypes=True):
  locations = getCodeLocations(item)
  s = "{}".format(item["message"])
  if compressTypes:
    s = s.replace("interner::_::_serde::Deserialize<'_>", "Deserialize")
    s = s.replace("interner::_::_serde::Serialize", "Serialize")
    s = s.replace("std::cmp::Eq", "Eq")
    s = s.replace("std::cmp::PartialEq", "PartialEq")
    s = s.replace("std::hash::Hash", "Hash")

  if len(s) > 100: s += "\n"
  replaceRendered(item, s, item["level"] == "error")
  render(item, locations, s)

def filterMismatchedTypes(item):
  if len(item["spans"]) == 0: return
  if "label" not in item["spans"][0]: return
  s = item["spans"][0]["label"]
  if s .startswith("expected"):
    locations = getCodeLocations(item)
    render(item, locations, s)

def filterWrongNumberOfArguments(item):
  locations = getCodeLocations(item)
  s = ""
  found = False
  for span in item["spans"]:
    if span["label"] is not None:
      s += span["label"]
      found = True
  assert(found)
  s += ". Expected these arguments:"
  child = item["children"][0];
  for span in child["spans"]:
    if span["label"] is None: continue
    s += "\n    " + span["text"][0]["text"].strip()
  s += "\n"
  render(item, locations, s)

def filterValueTypo(item):
  for child in item["children"]:
    for span in child["spans"]:
      if not "suggested_replacement" in span: continue
      item["message"] = colorWarning("Typo? -> {}".format(span["suggested_replacement"]))
      compress(item)

# Eg when you try use a container method but the contained type does not implement the necessary
# traits and you just need to stick to it some derive attributes to fix it.
def filterMissingDerives(item):
  s = item["message"]
  found = False

  for child in item["children"]:
    lead = "the following trait bounds were not satisfied"
    if child["message"].startswith(lead):
      s += child["message"].replace(lead, "").replace("\n", "\n  ")
      found = True
      break
    for span in child["spans"]:
      if not "suggested_replacement" in span: continue
      found = True
      s += ". Try adding these derives:\n  "
      s += colorSuggestion(span["suggested_replacement"].strip())
      if "text" in span and len(span["text"]) > 0 and "text" in span["text"][0]:
        s += "\n  {}".format(span["text"][0]["text"])

  # Missing trait bounds error cannot always be solved by derives, so this check
  # is bound to fail sometimes. Leaving this as a note to self.
  # Could instead just return without doing anything, then the original error is
  # shown without the "meta" failure message.
  if not found:
    raise Exception("Failed to match filterMissingDerives.")

  s += "\n"
  locations = getCodeLocations(item)
  render(item, locations, s)

def filter(args, item):
  m = item["message"]
  codeStr = None
  codeNum = None
  if "code" in item and isinstance(item["code"], dict):
    codeStr = item["code"]["code"]
    # Fails when the error code is a not numeric.
    try: codeNum = int(codeStr[1:])
    except: pass

  # TODO Testing if this is always true.
  assert("spans" in item)
  assert("children" in item)

  if m.startswith("cannot find value"):
    filterValueTypo(item)

  # NoSuchEnumVariant. TODO Multiple errors use this same code? Need to make the condition more specific.
  # if codeNum == 599:
  #   compress(item)

  # Generic one-line compression.
  for filterCode, subStrings in [
    (4, ["non-exhaustive patterns"]),
    (63, ["missing field"]),
    (412, ["cannot find type"]),
    (384, ["cannot assign twice to immutable variable"]),
    (609, ["no field", "on type"]),
    ("unused_variables", []),
    ("dead_code", []),
  ]:
    if isinstance(filterCode, int) and codeNum != filterCode: continue
    if isinstance(filterCode, str) and codeStr != filterCode: continue
    if not all([s in m for s in subStrings]): continue
    compress(item)

  if codeNum == 61 and m.startswith("this function takes"):
    filterWrongNumberOfArguments(item)

  if codeNum == 277 and "the trait bound" in m and "is not satisfied" in m:
    compress(item, compressTypes=True)

  if codeNum == 308 and "mismatched types" in m:
    filterMismatchedTypes(item)

  if codeNum == 599 and "but its trait bounds were not satisfied" in m:
    filterMissingDerives(item)

  # Compress advice about errors into copy-paste ready commands.
  # The formatting is different depending on whether there is one or more errors.
  if m.startswith("For more information about an error"):
    return None

  if m.startswith("For more information about this error"):
    match = RE_ERROR_CODE.search(m)
    s = f"Help: rustc --explain {match.group(0)}"
    replaceRendered(item, s)

  if m.startswith("aborting due to"):
    item["rendered"] = item["rendered"].strip()

  match = RE_ERROR_EXPLANATIONS.match(m)
  if match:
    tokens = match.group(1).split(",")
    s = "Help: "
    for i, token in enumerate(tokens):
      if i > 0: s += "; "
      s += f"rustc --explain {token.strip()}"
    replaceRendered(item, s)

  return item

def main(args):
  with args.input as f:
    content = f.read()
  if args.disable:
    return content

  data = json.loads(content)

  output = []
  for item in data:
    try:
      item = filter(args, item)
    except Exception as e:
      if args.debug:
        raise
      if item is not None:
        output.append({
          "rendered": colorMeta("filter-rustc failed to process a message, showing the original:"),
        })

    if item is None: continue
    if item["rendered"] in [o["rendered"] for o in output]: continue
    output.append(item)

  if args.debug:
    pass
  else:
    print(json.dumps(output, separators=(',', ':')))

if __name__ == "__main__":
  import argparse
  p = argparse.ArgumentParser(__doc__)
  p.add_argument(
      '--input',
      type=argparse.FileType('r'),
      default=sys.stdin,
      help="Path to input file or else use stdin.",
  )
  p.add_argument("--debug", action="store_true", help="Do not print rendered output and enable other debugging helpers")
  p.add_argument("--disable", action="store_true", help="Show the compiler output without any filtering")
  args = p.parse_args()
  main(args)
