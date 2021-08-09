#!/usr/bin/env python3
"""
* Copyright (c) 2009, Jeffrey Tchang
*
* All rights reserved.
*
*
* THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY
* EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import sys
import getopt
import logging

from ldif import LDIFParser, LDIFWriter
import string
import argparse

"""
Known Issues

The python ldif.py module does not like distinguished names that have
an unescaped comma. Example would be:

dn: cn=Bill, Kim and Family,mail=abc@example.com

To fix this, the comma needs to be escaped with a backslash like so:

dn: cn=Bill\, Kim and Family,mail=abc@example.com

"""


# The main issue with turning an LDIF into a CSV are multivalued attributes
# The first problem is figuring out if an attribute is multivalued. If it is, you have
# no way of knowing how many values it may have. This poses a problem as with CSVs you
# can only have a single column.

# My solution to this is to parse through the entire LDIF file twice. The first pass
# figures out how many columns you will need to ensure a full extraction of the data.
# The second pass actually outputs the CSV. Obviously this is 2*O(n).

# One of the issues with this is that a lot of spreadsheet programs will only support
# a maximum number of columns. Suppose a multivalued attribute had 200 or so values.
# This would eat up 200 columns. OpenOffice's maximum number of columns is 1024.


# A handler that simply throws away any logging messages sent to it
class NullHandler(logging.Handler):
    def emit(self, record):
        pass


# This class handles reading the attributes and storing them into a list. It is used
# for the first pass of the LDIF file
class LDIFAttributeParser(LDIFParser):

    attributeDictionary = dict()

    def __init__(self, input):
        LDIFParser.__init__(self, input)
        self.attributeDictionary = dict()

    # This function is called whenever an entry is parsed out
    def handle(self, dn, entry):

        # Always add the dn attribute with cardinality 1
        self.attributeDictionary["dn"] = 1

        # Loop through each of the attribute names
        for attributeName in entry.keys():

            # Add the name to the dictionary if it is not already there. Set the value to the cardinality of the
            # of the attribute (the number of values that the attribute has)
            if attributeName not in self.attributeDictionary:
                self.attributeDictionary[attributeName] = len(entry[attributeName])

            # If the attribute name is already in the dictionary, update the cardinality if it is bigger than the
            # one I can currently have stored
            else:
                if len(entry[attributeName]) > self.attributeDictionary[attributeName]:
                    self.attributeDictionary[attributeName] = len(entry[attributeName])


class LDIFCSVParser(LDIFParser):

    attributeDictionary = dict()
    attributeList = []
    fieldSeparatorCharacter = ","
    textDelimiter = '"'
    maximumColumns = 5
    defaultOutput = sys.stdout

    def __init__(self, input, attributeDictionary, output):
        LDIFParser.__init__(self, input)
        self.attributeDictionary = attributeDictionary
        self.defaultOutput = output

    # This function is called whenever an entry is parsed out
    def handle(self, dn, entry):

        # Get a list of all the attributes in the entire LDIF and sort them
        allAttributeNames = list(self.attributeDictionary.keys())
        allAttributeNames.sort()

        # Loop through each of the attributes
        for attributeName in allAttributeNames:

            # If the attribute is present in the entry print up to a maximum of
            # maximumColumns or self.attributeDictionary[attributeName]
            # Whichever is larger
            numberOfTimesToPrint = self.attributeDictionary[attributeName]

            # This will result in a truncation of the data
            if numberOfTimesToPrint > self.maximumColumns:
                numberOfTimesToPrint = self.maximumColumns

            if attributeName in entry:
                i = 0
                while i < numberOfTimesToPrint:

                    if i < len(entry[attributeName]):

                        if self.check_printable(entry[attributeName][i]):
                            self.defaultOutput.write(
                                self.textDelimiter
                                + entry[attributeName][i]
                                + self.textDelimiter
                                + self.fieldSeparatorCharacter
                            )
                        else:
                            self.defaultOutput.write(
                                self.textDelimiter
                                + repr(entry[attributeName][i])
                                + self.textDelimiter
                                + self.fieldSeparatorCharacter
                            )
                    else:
                        self.defaultOutput.write(
                            self.textDelimiter
                            + self.textDelimiter
                            + self.fieldSeparatorCharacter
                        )

                    i = i + 1

            # If the attribute name is dn, print the fully qualified distinguished name
            elif attributeName == "dn":
                self.defaultOutput.write(
                    self.textDelimiter
                    + str(dn)
                    + self.textDelimiter
                    + self.fieldSeparatorCharacter
                )

            # If the attribute name is not in the entry print fieldSeparatorCharacter(s)
            else:
                i = 0
                while i < numberOfTimesToPrint:
                    self.defaultOutput.write(
                        self.textDelimiter
                        + self.textDelimiter
                        + self.fieldSeparatorCharacter
                    )
                    i = i + 1

        # Print a newline
        self.defaultOutput.write("\n")

    def check_printable(self, message):
        for char in message:
            if ord(char) > 126 or ord(char) < 32:
                return False
        return True


# Parses an LDIF file to find out all the attribute names as well as how many of each kind of attribute
# are in the file. Returns a dictionary of attributes and the maximum number of times that value appears.
def parseLDIFAttributes(filename):
    # Open the LDIF file for reading
    LDIFFile = open(filename, "rb")
    primaryLogger.debug("Opened <%s> for reading" % filename)

    # Create an instance of the attribute parser which will handle LDIF entries
    attributeParser = LDIFAttributeParser(LDIFFile)

    # Perform the actual parsing using the AttributeParser
    # This first pass is only to obtain the attributes
    primaryLogger.debug("Parsing <%s> for attributes" % filename)
    attributeParser.parse()

    # Close the file
    LDIFFile.close()
    primaryLogger.debug("Closed file <%s>" % filename)

    # Return the dictionary of attributes. The key is the attribute name. The value is the
    # maximum number of times that value appears
    return attributeParser.attributeDictionary


def generateCSV(
    attributeDictionary,
    filename,
    output,
    fieldSeparatorCharacter=",",
    textDelimiter='"',
    maximumColumns=5,
):
    # Open the LDIF file for reading
    LDIFFile = open(filename, "rb")
    primaryLogger.debug("Opened <%s> for reading" % filename)

    # Create an instance of the attribute parser which will handle LDIF entries
    CSVParser = LDIFCSVParser(LDIFFile, attributeDictionary, output)
    CSVParser.fieldSeparatorCharacter = fieldSeparatorCharacter
    CSVParser.textDelimiter = textDelimiter
    CSVParser.maximumColumns = maximumColumns

    # Print out the CSV header sorted
    headerValues = list(attributeDictionary.keys())
    headerValues.sort()

    # Count of the number of columns this CSV will have
    numberOfColumns = 0

    for columnName in headerValues:
        numberOfTimesToPrint = attributeDictionary[columnName]

        # This will result in a truncation of the data
        if numberOfTimesToPrint > maximumColumns:
            numberOfTimesToPrint = maximumColumns

        i = 0
        while i < numberOfTimesToPrint:
            output.write(
                textDelimiter + columnName + textDelimiter + fieldSeparatorCharacter
            )
            numberOfColumns = numberOfColumns + 1
            i = i + 1

    # Write a newline after the header
    output.write("\n")

    # Print out the main CSV data
    CSVParser.parse()

    # Write a newline to end the file
    output.write("\n")
    LDIFFile.close()


def setupLogging(logfilename=""):
    # Create the primaryLogger as a global variable
    global primaryLogger
    primaryLogger = logging.Logger("primaryLogger", logging.DEBUG)

    # Create a handler to print to the log
    if logfilename != "":
        fileHandler = logging.FileHandler(logfilename, "w", encoding=None, delay=0)
    else:
        fileHandler = NullHandler()

    # Set how the handler will print the pretty log events
    primaryLoggerFormat = logging.Formatter(
        "[%(asctime)s][%(funcName)s] - %(message)s", "%m/%d/%y %I:%M%p"
    )
    fileHandler.setFormatter(primaryLoggerFormat)

    # Append handler to the primaryLoggyouer
    primaryLogger.addHandler(fileHandler)


# Primary function call
def main():

    # Setup logging to /dev/null incase no log file is specified
    setupLogging()

    # Variables to extract from command line (set the defaults here)
    outputFilename = ""
    fieldSeparatorCharacter = ","
    textDelimiter = '"'
    maximumColumns = 5

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        nargs="?",
        default=sys.stdout,
        help="File to write output. By default this is set to sys.stdout",
    )
    parser.add_argument(
        "-l",
        "--logging",
        type=str,
        nargs="?",
        help="File to write logging output. By default there is no logging.",
    )
    parser.add_argument(
        "-F",
        "--fieldsep",
        type=str,
        nargs="?",
        default=",",
        help='Character to separate the fields by. By default this is a comma. i.e. -F","',
    )
    parser.add_argument(
        "-D",
        "--delimiter",
        type=str,
        nargs="?",
        default='""',
        help='Character to delimit the text value by. By default this is a double quote. i.e. -D"""',
    )
    parser.add_argument(
        "-M",
        "--maxcols",
        type=int,
        nargs="?",
        default=5,
        help="The maximum number of columns a multivalued attribute should take up (default: 5). This is common with the objectClass attribute where it can have over 20 values. Do you want to have 20 columns each with the same heading objectClass or do you want to limit it",
    )
    parser.add_argument(
        "-i", "--input", type=str, nargs="?", required=True, help="LDIF file to read"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="increase verbosity"
    )
    args = parser.parse_args()

    # Setup logging
    if args.logging:
        setupLogging(logfilename=args.logging)
        if args.verbose:
            primaryLogger.debug("Logging initiated")
    
    inputFilename = args.input
    outputFilename = args.output
    fieldSeparatorCharacter = args.fieldsep
    textDelimiter = args.delimiter
    maximumColumns = args.maxcols

    if args.verbose:
        primaryLogger.debug("outputFilename: %s" % outputFilename)
        primaryLogger.debug("fieldSeparatorCharacter: %s" % fieldSeparatorCharacter)
        primaryLogger.debug("textDelimiter: %s" % textDelimiter)
        primaryLogger.debug("maximumColumns: %d" % maximumColumns)


    # First pass obtains the attributes inside the LDIF
    attributeDictionary = parseLDIFAttributes(inputFilename)
    if args.verbose:
        primaryLogger.debug("Parsed attribute dictionary: " + repr(attributeDictionary))

    # Default output is stdout
    output = sys.stdout

    if outputFilename != "":
        output = open(outputFilename, "w")

    # Second pass generates the actual CSV
    generateCSV(
        attributeDictionary,
        inputFilename,
        output,
        fieldSeparatorCharacter,
        textDelimiter,
        maximumColumns,
    )

    # Close the file
    output.close()


# Main entry point of program
if __name__ == "__main__":
    main()
