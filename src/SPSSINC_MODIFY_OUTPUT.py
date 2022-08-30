#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989, 2020
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/

# SPSSINC MODIFY OUTPUT extension command

"""This module implements the SPSS MODIFY OUTPUT extension command.
It delegates the implementation to the modifyoutput.py module."""

__author__ = "SPSS, JKP"
__version__ = "1.3.2"


from extension import Template, Syntax, processcmd

import modifyoutput

helptext=r"""SPSS MODIFY OUTPUT itemtypes
[/IF [COMMAND=commands] [SUBTYPE=subtypes ] [VISIBILITY={TRUE* | FALSE | ALL}]
[OUTLINETITLE=titletext] [OUTLINETITLESTART=text] [OUTLINETITLEEND=text]
[OUTLINETITLEREGEXP=regular expression]
[ITEMTITLE=titletext] [ITEMTITLESTART=text] [ITEMTITLEEND=text]
[ITEMTITLEREGEXP=regular expression]
[PROCESS={PRECEDING* | ALL}]

[/REPLACE OUTLINETITLE=text ITEMTITLE=text
[OUTLINETITLEREGEXP=regular expression] [ITEMTITLEREGEXP=regular expression]
[SEQUENCESTART=number or string]] [SEQUENCETYPE=ROMANUPPER|ROMANLOWER]

[/VISIBILITY VISIBLE={ASIS* | FALSE| DELETE}]
[/PAGEBREAKS BREAKBEFORETITLES={TRUE| FALSE*}] TITLELEVEL={TOP*|ANY} FIRST={YES*|NO}

[CUSTOMFUNCTION="module.function" ...]

[/HELP].
 
Modify the outline and item titles of objects in the Viewer.

Specify the item types to be modified.  Use ALL or one or more of
CHARTS, HEADINGS, LOGS, NOTES, PAGE TITLES, TABLES, TEXTS, WARNINGS, 
TITLES, TREES, MODELS.  For V19 or later, LWTABLES, LWNOTES, and
LWWARNINGS can also be used.  These are ignored for earlier versions.

The IF subcommand selects the particular instances of items to be modified.  
If a property does not apply to a particular item type, the property is ignored in filtering.  
The VISIBILITY keyword determines whether only visible items are processed 
(the default), or only invisible items are processed, or all items are processed
regardless of whether or not they are visible.  YES and NO are synonyms for
TRUE and FALSE.
 
SUBTYPE is one or more OMS table subtypes and applies only to tables.
It specifies which types of tables to process.
You can find the table subtype by right clicking in the outline on an instance 
or from Utilities/OMS identifiers.  The subtype name should be in quotes.
Case and white space do not matter.  Multiple subtypes can be specified.
Omit SUBTYPE to process all table types (If ALL or TABLES is specified).

COMMAND is a list of one or more commands whose output is to be processed.
Multi-word command names must be enclosed in quotes.  The command name
is the OMS identifier.  That can be found from Utilities>OMS Identifiers or by
right-clicking in the outline.

Items can be filtered based on the outline text and, for text, titles, 
and table items, on the item title that appears in the right pane of the Viewer.  
All of these criteria are case insensitive.  Text should be in quotes.
Titles can be specified as whole items - OUTLINETITLE, ITEMTITLE, 
or by their starting or ending text - OUTLINETITLESTART, ITEMTITLESTART, 
OUTLINETITLEEND, ITEMTITLEEND.

In addition, you can use powerful regular expressions both for filtering and for 
transforming titles with OUTLINETITLEREGEXP and ITEMTITLEREGEXP.  
Regular expressions are not explained here.
One reference is http://www.amk.ca/python/howto/regex.

You can use only one type of title filtering for each of the outline and item text.
For text objects, the item title is considered to be the text of the item.
If an item has html or rtf formatting applied, the formatting is ignored when selecting.

By default, the immediately preceding procedure output is processed.  Specify
PROCESS=ALL to process all existing items in the Viewer according to the 
selection criteria.

The REPLACE subcommand is used to modify the title text of the selected objects.
Use OUTLINETITLE and ITEMTITLE to change the text or
OUTLINEREGEXP and ITEMREGEXP to apply a regular expression substitution.

When specifying OUTLINETITLE and ITEMTITLE replacement text, you can use 
"\\1" to stand for the old text.  For example, if an item has title "Descriptive Statistics"
ITEMTITLE="Table: \\1"
would result in
"Table: Descriptive Statistics"

For text , title, and page title objects, you can include HTML or RTF formatting in the replacement 
item text.  For example,
ITEMTITLE="<html><i>Table:</i> \\1</html>"
would put "Table:" in italics.
This does not apply to pivot table titles.  The \\1 text does NOT include 
any existing formatting.

You can sequentially number or letter the selected items by including "\\0" in the 
replacement text where the number should appear.

Use SEQUENCESTART=value to set the initial value.  If value is a number, the selected
objects are numbered.  If the value is a quoted letter or letters (up to 4), the sequencing 
is by letters matching the case of the first character.  For example, 
SEQUENCESTART="A" 
would result in the sequence
A, B, ..., Z, AA, AB,...
SEQUENCETYPE=ROMANUPPER or ROMANLOWER can be used to produce
sequence numbers in roman numerals.  SEQUENCESTART must be numeric
in this case.

The sequence  value is incremented for each selected item except for the first
item after a TITLE (unless it is another title).  Selecting TITLES and TABLES
is often a good choice for numbering.

Regular expression substitution can be carried out with OUTLINETITLEREGEXP and
ITEMTITLEREGEXP.  Parenthesized groups are numbered according to the regexp 
specified on the IF subcommand, so you can rearrange the text at will.  If a regular 
expression was not used for selection, the
entire old text, without formatting, is considered to be group 1 and can be referenced
as \1 in the replacement expression.

You can set the visibility of selected items with the VISIBILITY subcommand.  
VISIBILITY=DELETE is the ultimate invisibility as it removes the selected items
completely.  This subcommand is an action specification not to be confused with
the VISIBILITY keyword that is a selection specification.

If an item is being deleted, any customfunction specification for it is ignored.

If BREAKBEFORETITLES is True, a page break will be generated immediately before
each selected title.  If title objects are not selected, no breaks will be created.  Titles
can be top level or any.  If FIRST=NO, however, the page break is not applied
to the first item where it would otherwise be applied.

For Python programmers, the CUSTOM subcommand can specify one or more
 Python modules and functions as quoted strings in the form 
 "modulename.functionname"  to be called for each selected item.  
 The function will be passed the output item as the only parameter.
Custom functions can have user-specified parameters written in Python notation.  For example,
"myfuncs.decorate(p1=100, p2='xyz')"
specifies parameters p1 and p2 with values 100 and 'xyz'.  Parameters are passed as a dictionary
as the second argument to the function, which must be named "custom".  
A special parameter named __FIRST__ is always
included and set initially to True.

Following is an example of a custom function that prints the title text and
the parameter values
def echoNameAndParms(obj, custom):
    'obj is the current item, and parms are the custom parameters'
    
    try:
        print obj.GetSpecificType().GetTextContents()
        for key, value in custom.items():
            print key, value
    except:
        pass


/HELP displays this text and does nothing else.

Example:
SPSSINC MODIFY OUTPUT TABLES
/IF SUBTYPE="custom table"
/REPLACE ITEMTEXT = "Table \\0: \\1".

SPSSINC MODIFY OUTPUT TEXTS
/IF OUTLINETEXT="active dataset"
/VISIBILITY VISIBLE=FALSE.

"""
def Run(args):
    """Execute the MODIFY TABLES extension command"""

    args = args[list(args.keys())[0]]
    ###print args   #debug

    # ITEMS keyword is just there to allow dialog to always generate a nonempty command.
    oobj = Syntax([
        Template("", subc="",  ktype="str", var="select", islist=True),
        Template("SUBTYPE", subc="IF",  ktype="str", var="subtype", islist=True),
        Template("PROCESS", subc="IF", ktype="str", var="process", islist=False),
        Template("VISIBILITY", subc="IF", ktype="str", var="visibility", islist=False),
        Template("COMMAND", subc="IF", ktype="str", var="command", islist=True),
        Template("OUTLINETITLE", subc="IF", ktype="str", var="outlinetitle", islist=False),
        Template("OUTLINETITLESTART", subc="IF", ktype="str", var="outlinetitlestart", islist=False),
        Template("OUTLINETITLEREGEXP", subc="IF", ktype="literal", var="outlinetitleregexp", islist=False),
        Template("OUTLINETITLEEND", subc="IF", ktype="str", var="outlinetitleend", islist=False),
        Template("ITEMTITLE", subc="IF", ktype="str", var="itemtitle", islist=False),
        Template("ITEMTITLESTART", subc="IF", ktype="str", var="itemtitlestart", islist=False),
        Template("ITEMTITLEREGEXP", subc="IF", ktype="str", var="itemtitleregexp", islist=False),
        Template("ITEMTITLEEND", subc="IF", ktype="str", var="itemtitleend", islist=False),
        Template("OUTLINETITLE", subc="REPLACE", ktype="literal", var="repoutlinetitle"),
        Template("ITEMTITLE", subc="REPLACE", ktype="literal", var="repitemtitle"),
        Template("OUTLINETITLEREGEXP", subc="REPLACE", ktype="literal", var="repoutlinetitleregexp"),
        Template("ITEMTITLEREGEXP", subc="REPLACE", ktype="literal", var="repitemtitleregexp"),
        Template("SEQUENCESTART", subc="REPLACE", ktype="literal", var="sequencestart", islist=False),
        Template("SEQUENCETYPE", subc="REPLACE", ktype="str", var="sequencetype", islist=False),
        Template("ITEMS", subc="REPLACE", ktype="bool", var="ignore"),
        Template("VISIBLE", subc="VISIBILITY", ktype="str", var="visible", islist=False),
        Template("BREAKBEFORETITLES", subc="PAGEBREAKS", ktype="bool", var="breakbeforetitles"),
        Template("FIRST", subc="PAGEBREAKS", ktype="bool", var="breakfirst"),
        Template("TITLELEVEL", subc="PAGEBREAKS", ktype="str", var="titlelevel", vallist=["top", "any"]),
        Template("FUNCTION", subc="CUSTOM", ktype="literal", var="customfunction", islist=True),
        Template("HELP", subc="", ktype="bool")])
    
    # A HELP subcommand overrides all else
    if "HELP" in args:
        #print helptext
        helper()
    else:
        processcmd(oobj, args, modifyoutput.modify)

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print(("Help file not found:" + helpspec))
try:    #override
    from extension import helper
except:
    pass
