#!/usr/bin/env python
#
# ogg2gme.py - Convert a set of *.ogg files into a Tip-Toi *.gme file and a *.png file
#              containing a table of OIDs.
#
# Copyright (C) 2015 by Johannes Overmann <Johannes.Overmann@joov.de>

import optparse
import sys
import glob
import os
import re


def isWindows():
    """Return true iff the hist operating system is Windows.
    """
    return os.name == "nt"


def isdigit(char):
    """Return True iff char is a digit.
    """
    return char.isdigit()
    

def isalpha(char):
    """Return True iff char is a letter.
    """
    return char.isalpha()
    

class Error:
    """
    """
    def __init__(self, message):
        self.message = message
        
        
def writeStringToFile(fileName, s):
    """Write string to file.
    """
    f = open(fileName, "wb")
    f.write(s)
    f.close()
    
    
def readStringFromFile(fileName):
    """Read string from file and return it.
    """
    f = open(fileName, "rb")
    r = f.read()
    f.close()
    return r

def getParentDirName():
    """Return name of the parent directory.
    """
    return os.path.basename(os.getcwd())


def findFileInParentDirs(fileName, notFound):
    """Find file in parent dirs. If not found return notFound.
    """    
    if os.path.exists(fileName):
        return "./" + fileName 

    for i in range(10):
        fileName = "../" + fileName
        if os.path.exists(fileName):
            return fileName
        
    return notFound


def getYamlFileNames():
    """Get filenames of the *.yaml and *.codes.yaml filenames.
    Return (yamlFileName, codesYamlFileName). codesYamlFileName may be None.
    """
    fileList = glob.glob("*.yaml")
    yamlList = [x for x in fileList if not x.endswith(".codes.yaml")]
    codesYamlList = [x for x in fileList if x.endswith(".codes.yaml")]
    if len(yamlList) == 1 and len(codesYamlList) == 1:
        return (yamlList[0], codesYamlList[0])
    if len(yamlList) == 1 and len(codesYamlList) == 0:
        return (yamlList[0], yamlList[0][:-5] + ".codes.yaml")
    if len(yamlList) == 0 and len(codesYamlList) == 0:
        dirname = getParentDirName()
        return ("_" + dirname + ".yaml", "_" + dirname + ".codes.yaml")
    raise Error("Expecting 0, 1 or 2 yaml files (one foo.yaml and optionally one foo.codes.yaml).")


def getProductId():
    """Get and retrn product-id.
    
    The product id is either directly specified by the --product-id option
    or is determined by the name of the current directory which 
    must be of the format 'p900_my_book' for product id 900 for example.
    """
    # If --product-id is specified always use this.
    if options.product_id != 0:
        return options.product_id
    
    # Try to get product id from directory name.
    dirname = getParentDirName()
    if len(dirname) >= 2 and dirname[0] == 'p' and isdigit(dirname[1]):
        end = 1
        while end < len(dirname) and isdigit(dirname[end]):
            end += 1
        productId = int(dirname[1:end])
        return productId
    raise Error("Unable to determine product-id. Either prepend a p<PRODUCTID> prefix to the name of the current directory or specify --product-id.")


def readOrGenerateYaml(yamlFileName, productId):
    """Read *.yaml file. Generate it if it is missing.
    
    Return (usedScriptNames, yamlHead, yamlTail).
    """
    # Generate empty yaml file if necessary.
    if not os.path.exists(yamlFileName):
        if options.verbose:
            print "Generating YAML file %s (Using product-id %d)" % (yamlFileName, productId)
        yaml = """product-id: %u
welcome: _welcome
scripts:
""" % productId
        writeStringToFile(yamlFileName, yaml)
    
    # Read yaml file.
    if options.verbose:
        print "Reading YAML file %s" % (yamlFileName)
    s = readStringFromFile(yamlFileName).replace("\r", "")
    lines = s.splitlines()
    usedScriptNames = []
    yamlHead = []
    yamlTail = []
    
    # Parse part before and including 'scripts:' line.
    while lines and lines[0].rstrip() != "scripts:":
        yamlHead.append(lines.pop(0))
    if lines:
        yamlHead.append(lines.pop(0))

    # Parse scripts.
    while lines and (len(lines[0].strip()) == 0 or lines[0].startswith("  ")):
        line = lines.pop(0)
        yamlHead.append(line)
        scriptName = line.strip()
        if scriptName and scriptName.endswith(":") and isalpha(scriptName[0]):
            usedScriptNames.append(scriptName[:-1])
    if yamlHead:
        yamlHead[-1] += "\n"
        
    # Parse rest.
    yamlTail = lines
    if yamlTail:
        yamlTail[-1] += "\n"
        
    return (usedScriptNames, "\n".join(yamlHead), "\n".join(yamlTail))


def getListOfAudioFiles():
    """Scan current directory and return list of audio (*.ogg) files without 
    filename extension.
    """
    lst = sorted(glob.glob("*.ogg"))
    return lst
    

def appendNewObjectCodesToYaml(yamlFileName, usedScriptNames, audioFileList, yamlHead, yamlTail):
    """Append new object codes to yaml file in the script section. (If any.)
    """
    audioNames = [os.path.splitext(os.path.basename(x))[0] for x in audioFileList if not x.startswith("_")]
    
    # Create new scripts for new audio files which play the audio file.
    appendToScripts = []
    for i in audioNames:
        if i in usedScriptNames:
            continue
        if options.verbose:
            print "Adding", i 
        appendToScripts.append("  " + i + ":\n")
        appendToScripts.append("  - P(" + i + ")\n")
    
    if appendToScripts:
        if options.verbose:
            print "Adding new samples to YAML file %s" % (yamlFileName)
        writeStringToFile(yamlFileName, yamlHead + "".join(appendToScripts) + yamlTail)


def run(cmd):
    """Run command.
    """
    if options.verbose:
        print "Running " + cmd
    if isWindows():
        cmd = cmd.replace("/", "\\")
        cmd = cmd.replace("'", '"')
    if os.system(cmd):
        raise Error("Command failed: " + cmd)

    
def buildGme(yamlFileName, tttool):
    """Invoke tttool and build GME file.
    """
    run(tttool + " assemble " + yamlFileName)

    
def getHighestNamedOid(codesYamlFileName):
    """Read foo.codes.yaml file and detremine highest used code.
    """
    lines = readStringFromFile(codesYamlFileName).splitlines()
    lines = [x for x in lines if x.startswith("  ")]
    max = 0
    for line in lines:
        fields = line.split(":")
        if len(fields) < 2:
            continue
        oid = int(fields[1])
        if oid > max:
            max = oid
    if options.verbose:
        print "Highest used code: %d" % max
    return max
    
    
def generateAdditionalOids(numNamedOids, totalOids, codesYamlFileName, dstdir, tttool):
    """Generate additional oids, beyond the ones which are generated by the YAML file.
    For future extension without re-printing oids.
    """
    if totalOids <= numNamedOids:
        return
    highestNamedOid = getHighestNamedOid(codesYamlFileName)
    start = highestNamedOid + 1
    num = totalOids - numNamedOids
    end = start + num - 1
    if options.verbose:
        print "Generating %d additional ext_* oids into %s" % (num, dstdir)
    run(tttool + " oid-code -d " + options.dpi + " %d-%d" % (start, end))

    
def removeFiles(pattern):
    """Remove files matching glob pattern.
    """
    for f in glob.glob(pattern):
        os.remove(f)
    
        
def mkdir(path):
    """Make directory if it does not yet exist.
    """
    if os.path.isdir(path):
        return
    os.mkdir(path)

    
def rmdir(path):
    """Try to remove empty directory. Do nothing if the directory is not empty or does not exist.
    """
    try:
        os.rmdir(path)
    except:
        pass
    
    
def refParentDirIfNecessary(path):
    """Return ../path if path starts with a dot, else return path.    
    """
    if path.startswith("."):
        return "../" + path
    else:
        return path
        
    
def buildOidTable(yamlFileName, codesYamlFileName, productId, tttool):
    """Generate oid-table PNG.
    """
    columns = options.num_columns
    numOidsPerPage = 16 * columns
    minAdditionalOids = options.num_additional_oids
    oid_orig_dir = "oid_orig"
    oid_box_dir = "oid_box"
    oid_label_dir = "oid_label"
    
    # All lengths in 1/10 mm.
    totalSize = 160
    totalWidth = 1900 / columns
    border = 10
    textSep = 10
    lineSep = 10
    textPointSize = 72
    dpi = 600.0
    if options.dpi.startswith("1200"):
        dpi *= 2
        textPointSize *= 2
    
    toPixel = lambda x : int(x * dpi / 25.4 / 10.0)
    innerSizePixel = toPixel(totalSize - 2 * border)
    borderPixel = toPixel(border)
    totalSizePixel = innerSizePixel + 2 * borderPixel
    centerPixel = totalSizePixel / 2
    totalWidthPixel = toPixel(totalWidth)
    textSepPixel = toPixel(textSep)
    lineSepPixel = toPixel(lineSep)

    mkdir(oid_orig_dir)
    mkdir(oid_box_dir)
    mkdir(oid_label_dir)
    removeFiles(oid_orig_dir + "/oid-*.png")
    removeFiles(oid_box_dir + "/box_oid-*.png")
    removeFiles(oid_label_dir + "/label_oid-*.png")

    # Generate oids from the *.yaml file into oid_orig_dir.
    if options.verbose:
        print "Generating oids into %s" % oid_orig_dir
    os.chdir(oid_orig_dir)
    try:
        run(refParentDirIfNecessary(tttool) + " oid-code -d " + options.dpi + " ../" + yamlFileName)
    finally:
        os.chdir("..")
    
    # Generate additional oids into oid_orig_dir.
    os.chdir(oid_orig_dir)
    try:
        numNamedOids = len(glob.glob("oid-*.png")) + options.num_start_oid - 1
        totalOids = numOidsPerPage
        while numNamedOids + minAdditionalOids > totalOids:
            totalOids += numOidsPerPage
        generateAdditionalOids(numNamedOids, totalOids, "../" + codesYamlFileName, oid_orig_dir, refParentDirIfNecessary(tttool))
    finally:
        os.chdir("..")

    # Get list of orioginal OID files.
    os.chdir(oid_orig_dir)
    try:
        origOidFiles = sorted(glob.glob("oid-*.png"))
    finally:
        os.chdir("..")
        
    # Split into startOidFiles, namedOidFiles and numberedOidFiles and generate label names.
    startOidFiles = []
    namedOidFiles = []
    numberedOidFiles = []
    oidFileNameToName = {}
    for fileName in origOidFiles:
        if re.search("^oid-[0-9]+-START.png$", fileName):
            startOidFiles.append(fileName)
            oidFileNameToName[fileName] = "START"
        else:
            match = re.search("^oid-([0-9]+).png$", fileName)
            if match:
                numberedOidFiles.append(fileName)
                oidFileNameToName[fileName] = "ext_" + match.group(1)
            else:
                match = re.search("^oid-[0-9]+-(.+).png$", fileName)
                if match:
                    namedOidFiles.append(fileName)    
                    oidFileNameToName[fileName] = match.group(1)
                else:
                    print "Ignoring PNG %s" % fileName

    # Generate boxes.
    for origOidFile in origOidFiles:
        origOidFileName = oid_orig_dir + "/" + origOidFile
        boxOidFileName = oid_box_dir + "/box_" + origOidFile
        run("convert %s -crop %dx%d+0+0 +repage -density 600x600 %s" % (origOidFileName, innerSizePixel, innerSizePixel, boxOidFileName))
        if re.search("^oid-[0-9]+-START.png$", origOidFile):
            # Start button: Green circle.
            run("convert %s -bordercolor white -compose Copy -border %d %s" % (boxOidFileName, borderPixel, boxOidFileName))
            run("convert %s -stroke white -strokewidth %d -draw 'fill-opacity 0 circle %d,%d %d,%d' %s" % (boxOidFileName, innerSizePixel / 2, centerPixel, centerPixel, centerPixel, borderPixel / 2 - innerSizePixel / 4, boxOidFileName))
            run("convert %s -stroke green -strokewidth %d -draw 'fill-opacity 0 circle %d,%d %d,%d' %s" % (boxOidFileName, borderPixel, centerPixel, centerPixel, centerPixel, borderPixel / 2, boxOidFileName))
        else:
            # Normal object: Red box.
            run("convert %s -bordercolor red -compose Copy -border %d %s" % (boxOidFileName, borderPixel, boxOidFileName))
        
    # Generate labels.
    for origOidFile in origOidFiles:
        name = oidFileNameToName[origOidFile]
        boxOidFileName = oid_box_dir + "/box_" + origOidFile
        labelOidFileName = oid_label_dir + "/label_" + origOidFile
        run("convert %s -extent %dx%d %s" % (boxOidFileName, totalWidthPixel, totalSizePixel, labelOidFileName))
        run("convert %s -gravity West -stroke none -pointsize %d -annotate +%d+0 %s %s" % (labelOidFileName, textPointSize, totalSizePixel + textSepPixel, name, labelOidFileName))
        run("convert %s -bordercolor white -compose Copy -border %d %s" % (labelOidFileName, lineSepPixel / 2, labelOidFileName))
        
    # Generate label pages.
    allLabels = (startOidFiles * options.num_start_oid) + namedOidFiles + numberedOidFiles
    allLabels = [oid_label_dir + "/label_" + x for x in allLabels]
    for i in range(0, len(allLabels), numOidsPerPage):
        run("montage -border 20 %s -mode Concatenate -tile %dx _oid-table%d.png" % (" ".join(allLabels[i:i + numOidsPerPage]), columns, i / numOidsPerPage))

    removeFiles(oid_label_dir + "/label_oid-*.png")
    rmdir(oid_label_dir)


def main():
    global options
    usage = """Usage: %prog [options]

Convert all *.ogg files found in the current directory into a Tip-Toi *.gme file and
optionally (-t) a _oid-table0.png file which contains the OID labels.

This tool is useful when generating simple OID labels, each associated with one sample.
Example: adding Tip-Toi support to non-Tip-Toi books.

The generated *.yaml file can be edited at any time and is not overwritten by this tool.
This tool always adds samples to the *.yaml file which are not yet in the *.yaml file.

This tool requires:
    - tttool (must be in ../tttool)
    - convert/montage (from ImageMagick, must be on the PATH)
"""
    version = "0.1.2"
    parser = optparse.OptionParser(usage=usage, version=version)
    parser.add_option("-t", "--build-oid-table",  default=False, action="store_true", help="Generate PNG file(s) which contain(s) all oids for this product.")
    parser.add_option("-S", "--num-start-oid",  default=3, type="int", help="For -t/--build-oid-table: Generate N START OIDs (e.g. to re-use the same product id for multiple projects).")
    parser.add_option("-C", "--num-columns",  default=3, type="int", help="For -t/--build-oid-table: Arrange OID labels in N columns on each page. Default is 3.")
    parser.add_option("-N", "--num-additional-oids",  default=10, type="int", help="For -t/--build-oid-table: This tool always fills whole pages with additional OIDs (additional to the OIDs for the named OIDs from the *.yaml file). This parameter sets the minimum amount of additional OIDs. Default is 10.")
    parser.add_option("-d", "--dpi",  default="600d", type="string", help="For -t/--build-oid-table: DPI setting for tttool, used to generate the OIDs. Must be either 600, 600d, 1200 or 1200d. The d variants double the pixel size. Default is 600d.")
    parser.add_option("-p", "--product-id",  type=int, default=0, help="Set product-id. This only has an effect when generating the *.yaml file for the first time. Once the *.yaml file exists please edit the product-id in the *.yaml file directly.")
    parser.add_option("-v", "--verbose",  default=0, action="count", help="Be more verbose.")
    (options, args) = parser.parse_args()

    if len(args) != 0:
	parser.error("Not expecting any non-option args.")

    try:
        if not os.path.exists("_welcome.ogg"):
            raise Error("Did not find a '_welcome.ogg' file. Please create one.")
        
        # Find tttool in parent dirs or PATH.
        tttool = "tttool" if not isWindows() else "tttool.exe"
        tttool = findFileInParentDirs(tttool, tttool)
        
        (yamlFileName, codesYamlFileName) = getYamlFileNames()
        productId = getProductId()
        (usedScriptNames, yamlHead, yamlTail) = readOrGenerateYaml(yamlFileName, productId)
        audioFileList = getListOfAudioFiles()
        appendNewObjectCodesToYaml(yamlFileName, usedScriptNames, audioFileList, yamlHead, yamlTail)
        buildGme(yamlFileName, tttool)
        if options.build_oid_table:
            buildOidTable(yamlFileName, codesYamlFileName, productId, tttool)
            
    except Error as e:
        print "Error:", e.message
        sys.exit(1)

    

# call main()
if __name__ == "__main__":
    main()

