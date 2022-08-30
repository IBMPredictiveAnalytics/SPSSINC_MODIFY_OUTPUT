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

"implementation of SPSSINC MODIFY OBJECTS"



__version__ = '1.3.3'
__author__ = "SPSS, JKP"

# Note: This module requires at least SPSS 17.0.0

# history
# 01-sep-2008 original version
# 29-oct-2008  clean up any white space and outer quotes in subtype list
# 19-dec-2009 enable localization
#  27-jan-2010 page titles
# 11-jun-2010 support for lightweight objects
#  23-jun-2010 translatable proc name
#  13-jun-2012 add control over first pagebreak

import spss, SpssClient
from extension import floatex, _isseq
import re, copy,locale
import functools, inspect   # used for custom functions


class ClientSession(object):
        """Manager for the SpssClient start/stop state

        This class assumes that all client sessions are handled via with ClientSession."""

        # ref counting client session calls keeps the client alive until the outermost caller
        # terminates
        count = 0
        def __enter__(self):
                """initialization for with statement"""
                if ClientSession.count == 0:
                        try:
                                SpssClient.StartClient()
                        except:
                                raise RuntimeError(_("SpssClient.StartClient failed."))
                ClientSession.count += 1
                return self

        def __exit__(self, type, value, tb):
                ClientSession.count -= 1
                if ClientSession.count <= 0:
                        SpssClient.StopClient()
                return False


# Types returned by outputitem.GetType()
# Lightweight types are new in 19 and are referenced by number so that the following
# structure will be valid in earlier releases even though these types will not occur

itemtypes = dict([
        (SpssClient.OutputItemType.CHART.name, "charts"),
        (SpssClient.OutputItemType.HEAD.name, "headings"),
        (SpssClient.OutputItemType.LOG.name, "logs"),
        (SpssClient.OutputItemType.NOTE.name, "notes"),
        (SpssClient.OutputItemType.PIVOT.name, "tables"),
        (SpssClient.OutputItemType.TEXT.name, "texts"),
        (SpssClient.OutputItemType.WARNING.name, "warnings"),
        (SpssClient.OutputItemType.TITLE.name, "titles"),
        (SpssClient.OutputItemType.TREEMODEL.name, "trees"),
        (SpssClient.OutputItemType.PAGETITLE.name, "pagetitles"),
        (SpssClient.OutputItemType.MODEL.name, "models")])
try:
        itemtypes[SpssClient.OutputItemType.LIGHTPIVOT.name] = "lwtables"
        itemtypes[SpssClient.OutputItemType.LIGHTNOTE.name] = "lwnotes"
        itemtypes[SpssClient.OutputItemType.LIGHTWARNING.name] = "lwwarnings"
except:   # these items undefined if version < 19
        pass

CUSTOMPARAMS={}  # for custom function parameters


def modify(select=None, command=None, subtype=None, process="preceding", visibility=True,
           outlinetitle=None, outlinetitlestart=None, outlinetitleregexp=None, 
           outlinetitleend=None, itemtitle=None, itemtitlestart=None, itemtitleregexp=None, itemtitleend=None,
           repoutlinetitle=None, repitemtitle=None, repoutlinetitleregexp=None,
           repitemtitleregexp=None, sequencestart=None, sequencetype="", visible="asis",
           customfunction=None, ignore=None, breakbeforetitles=False, titlelevel="top", breakfirst=True):
        """Execute SPSSINC MODIFY OUTPUT command.  See SPSSINC_MODIFY_OUTPUT.py
for argument definitions."""

        # ensure localization function is defined.  po file must be named SPSSINC_MODIFY_OUTPUT.pot
        global _
        try:
                _("---")
        except:
                def _(msg): return msg

        ##debugging
        # debugging
                        # makes debug apply only to the current thread
        try:
                import wingdbstub
                import threading
                wingdbstub.Ensure()
                wingdbstub.debugger.SetDebugThreads({threading.get_ident(): 1})
        except:
                pass

        #if not customfunction is None:
                #customfunction = [resolvestr(f) for f in customfunction] 

        for arg in [select, command, subtype]:
                if arg is None:
                        arg = []

        info = NonProcPivotTable("INFORMATION", tabletitle=_("Information"))
        try:
                with ClientSession():
                        global desout
                        desout = SpssClient.GetDesignatedOutputDoc()
                        if not customfunction is None:
                                customfunction = [resolvestr(f) for f in customfunction]                         
                        items = desout.GetOutputItems()
                        itemkt = items.Size()
                        start = 1  #do not process the root
                        if process == "preceding":   # work back until level 1 item found, ignoring logs.
                                for i in range(itemkt-1, 0, -1):
                                        item = items.GetItemAt(i)
                                        if item.GetType() == SpssClient.OutputItemType.LOG:
                                                itemkt -= 1
                                                continue
                                        if item.GetTreeLevel() == 1:
                                                start = i
                                                break;

                        filter = ItemFilter(select, command, subtype, outlinetitle, outlinetitlestart, outlinetitleregexp,
                                            outlinetitleend, itemtitle, itemtitlestart, itemtitleregexp, itemtitleend, breakbeforetitles, info)
                        processor = ItemProcessor(repoutlinetitle, repitemtitle, repoutlinetitleregexp, repitemtitleregexp,
                                                  filter.outlinetitleregexp, filter.itemtitleregexp, sequencestart, sequencetype, breakbeforetitles,
                                                  titlelevel, breakfirst)
                        if visible == "delete":
                                desout.ClearSelection()  

                        for itemnumber in range(start, itemkt):
                                item = items.GetItemAt(itemnumber)
                                isVisible = item.IsVisible()
                                # visibility criterion can be "true", "false", or "all"
                                if (isVisible and not visibility == "false") or (not isVisible and not visibility == "true"):
                                        if filter.filter(item):
                                                processor.apply(item)
                                                if visible == "true":
                                                        item.SetVisible(True)
                                                elif visible == "false":
                                                        item.SetVisible(False)
                                                elif visible == "delete":
                                                        item.SetSelected(True)
                                                        continue
                                                if not customfunction is None:
                                                        for f in customfunction:
                                                                f(item)
                        if visible == "delete":   # items to be deleted are (the only ones) selected
                                desout.Delete()
        finally:
                info.generate()

class ItemFilter(object):
        """Filter output items according to various criteria."""

        def __init__(self, select, command, subtype, outlinetitle, outlinetitlestart, outlinetitleregexp, outlinetitleend,
                     itemtitle, itemtitlestart, itemtitleregexp, itemtitleend, breakbeforetitles, info):
                attributesFromDict(locals())  # copy parameters
                # clean up subtypes list - remove whitespace and matching outer quotes
                if not self.subtype is None:
                        self.subtype = ["".join(st.lower().split()) for st in self.subtype]
                        self.subtype = [re.sub(r"""^('|")(.*)\1$""", r"""\2""", st) for st in self.subtype]
                if outlinetitle and (outlinetitlestart or outlinetitleregexp or outlinetitleend):
                        raise ValueError(_("OUTLINETITLE cannot be combined with other outline criteria on IF"))
                if itemtitle and (itemtitlestart or itemtitleregexp or itemtitleend):
                        raise ValueError(_("ITEMTITLE cannot be combined with other outline criteria on IF"))
                if outlinetitleregexp and (outlinetitlestart or outlinetitleend):
                        raise ValueError(_("OUTLINETITLEREGEXP cannot be combined with start or end criteria on IF"))
                if itemtitleregexp and (itemtitlestart or itemtitleend):
                        raise ValueError(_("ITEMTITLEREGEXP cannot be combined with start or end criteria on IF"))
                if select is None:
                        raise ValueError(_("At least one item type or ALL must be specified"))
                self.types = set(select)
                self.all = "all" in self.types
                if breakbeforetitles and not ("titles" in self.types or "all" in self.types):
                        info.addrow( _("BREAKBEFORETITLES is ignored, because Title objects are not selected"))
                for regexp in ['outlinetitleregexp', 'itemtitleregexp']:
                        if getattr(self, regexp):
                                setattr(self, regexp, re.compile(getattr(self, regexp), flags=(re.LOCALE|re.IGNORECASE|re.UNICODE)))
                for t in ['outlinetitle', 'outlinetitlestart', 'outlinetitleend', 'itemtitle', 'itemtitlestart', 'itemtitleend']:
                        if not getattr(self, t) is None:
                                setattr(self, t,  getattr(self,t).lower())

        def filter(self, item):
                """Return True or False according to whether the item is selected.

                If there are no criteria, every item (of the appropriate type) will be selected.
                This is not related to an item's selected state in the Viewer."""

                itemtype = itemtypes.get(item.GetType().name, "")
                # item type screen
                if not self.all and not itemtype in self.types:
                        return False
                command = item.GetProcedureName().lower()
                if self.command and not command in self.command:
                        return False
                subtype = "".join(item.GetSubType().lower().split())
                ###if self.subtype and  itemtype == SpssClient.OutputItemType.PIVOT and subtype not in self.subtype:
                if self.subtype and  (itemtype == "tables" or itemtype == "lwtables") and subtype not in self.subtype:
                        return False
                outlinetitle = item.GetDescription()
                if not self.evaltext(outlinetitle, "outline"):
                        return False
                if itemtype in ["titles", "texts", "pagetitles"]:
                        itemtitle = item.GetSpecificType().GetTextContents()
                elif itemtype == "tables":
                        itemtitle = item.GetSpecificType().GetTitleText()
                else:
                        itemtitle = None
                return self.evaltext(itemtitle, "item")

        def evaltext(self, title, textsource):
                """Return True if title meets selection criteria.

                title is the outline or item text
                textsource is "outline" or "item" 
                If the title is None, it always fails."""

                if textsource == "outline":
                        stitle, stitlestart, stitleend, stitleregexp = self.outlinetitle, self.outlinetitlestart, self.outlinetitleend, self.outlinetitleregexp
                else:
                        stitle, stitlestart, stitleend, stitleregexp = self.itemtitle, self.itemtitlestart, self.itemtitleend, self.itemtitleregexp

                if not title is None:
                        title = title.lower()
                try:
                        if stitle and not title ==stitle:
                                return False
                        if stitlestart and not title.startswith(stitlestart):
                                return False
                        if stitleend and not title.endswith(stitleend):
                                return False
                        if stitleregexp and not re.search(stitleregexp, title):
                                return False
                        return True
                except:
                        return False     #item types that do not have a title may pass None


class ItemProcessor(object):
        """Apply requested changes to object"""

        def __init__(self, repoutlinetitle, repitemtitle, repoutlinetitleregexp, repitemtitleregexp,
                     outlinetitleregexp, itemtitleregexp,
                     sequencestart, sequencetype, breakbeforetitles, titlelevel, breakfirst):
                attributesFromDict(locals())
                self.seqinc = Incrementer(sequencestart, sequencetype)
                self.lastitemtype = None
                self.firstbreakapply = True  # indicates first opportunity to apply page break

        def apply(self, item):
                """Apply requested changes to outline and item titles, where applicable.

                item is the output item"""

                # If the replacement is a simple string, it is used after substituting the old title for "\\1" in the new string
                # If the replacement is a regular expression,  it is processed using the regexp version of the search string, if any
                # If no regexp was supplied in search, the existing title is used as the regexp
                # Substitutions are case insensitive, locale aware, and use Unicode properties.

                # If last item was a title and this item is not a title, do not increment.
                itemtype = item.GetType()
                if itemtype == SpssClient.OutputItemType.TITLE or self.lastitemtype != SpssClient.OutputItemType.TITLE:
                        self.nextvalue = self.seqinc.nextvalue()
                self.lastitemtype = itemtype

                # For title objects, if breaks are requested and outline item level matches, insert a page break.
                if self.breakbeforetitles and itemtype == SpssClient.OutputItemType.TITLE:
                        if self.titlelevel == "any" or item.GetTreeLevel() == 2:
                                if self.breakfirst or not self.firstbreakapply:
                                        item.SetPageBreak(True)
                                self.firstbreakapply = False

                if not self.repoutlinetitle is None:   # simple substitution but allowing for "\\1"
                        item.SetDescription(self.makeNewTitle(self.repoutlinetitle, item.GetDescription(), self.nextvalue))
                elif not self.repoutlinetitleregexp is None:   # regular expression replacement
                        pat = self.makeNewRegexp(self.outlinetitleregexp, item.GetDescription)
                        newdesc = re.sub(pat, self.repoutlinetitleregexp, item.GetDescription())
                        newdesc = re.sub(r"\\0", self.nextvalue, newdesc)
                        item.SetDescription(newdesc)

                # The item.  Only some item types support a title

                if self.repitemtitle or self.repitemtitleregexp:
                        specificitem = item.GetSpecificType()   # only valid for titles, text, and pivot tables
                        # not valid for lw types
                        if itemtype in [SpssClient.OutputItemType.TITLE, SpssClient.OutputItemType.TEXT,
                                        SpssClient.OutputItemType.PAGETITLE]:
                                getter = specificitem.GetTextContents
                                setter = specificitem.SetTextContents
                        elif itemtype == SpssClient.OutputItemType.PIVOT:
                                getter = specificitem.GetTitleText
                                setter = specificitem.SetTitleText
                        else:
                                return
                        if not self.repitemtitle is None:    # simple substitution allowing for "\\1"
                                newtitle = self.makeNewTitle(self.repitemtitle, getter(), self.nextvalue)
                        elif not self.repitemtitleregexp is None:   #regexp substitution
                                pat = self.makeNewRegexp(self.itemtitleregexp, getter)
                                newtitle = re.sub(pat, self.repitemtitleregexp, getter())
                                newtitle = re.sub(r"\\0", self.nextvalue, newtitle)
                        setter(newtitle)

        def makeNewTitle(self, reptitle, oldtitle, nextvalue):
                """Return new title.

                reptitle is the replacement title, possibly including "\\1" indicating that the old title
                should be inserted at that point.
                if \\0 occurs in reptitle, it is replaced by the nextvalue in the sequence (or "" if no such value)
                oldtitle is the title being replaced."""

                if oldtitle is None:
                        oldtitle=""
                reptitle = re.sub(r"\\0", nextvalue, reptitle)
                return re.sub(r"\\1", oldtitle, reptitle)

        def makeNewRegexp(self, title, getter):
                """Return title converted into regular expression if there was none.

                title is the search regular expression or None.
                getter is the function to retrieve the existing title."""

                if not title is None:
                        return title
                else:
                        return re.compile("(" + re.escape(getter()) + ")", flags=(re.IGNORECASE|re.LOCALE|re.UNICODE))


class Incrementer(object):
        "Provide a sequence of letters or numbers for labeling output"
        def __init__(self, start, sequencetype):
                """start is a numerical or string value (up to four letters) to begin the sequence"""

                self.sequencetype = sequencetype
                self.romancase = sequencetype == "romanlower" and "lower" or "upper"
                if start is None:
                        self.value = 1
                else:
                        try:
                                self.value = int(start)
                        except:    #nonnumeric sequencing
                                if sequencetype.startswith("roman"):
                                        raise ValueError(_("Cannot combine ROMAN SEQUENCETYPE with nonnumeric start value"))
                                start = list(start)[:4]
                                self.value = 4*[-1]
                                if start[0].islower():
                                        self.letters = "abcdefghijklmnopqrstuvwxyz"
                                else:
                                        self.letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

                                for i in range(len(start)):
                                        v = self.letters.index(start.pop())
                                        self.value[3-i] = v

        def nextvalue(self):
                """Return the next numerical value or letter in the sequence"""

                if isinstance(self.value, int):
                        retvalue = self.value
                        self.value += 1
                        if self.sequencetype.startswith("roman"):
                                return roman(retvalue, case=self.romancase).result
                        else:
                                return str(retvalue)
                else:
                        retvalue = []
                        for i in range(4):
                                if self.value[i] >=0:
                                        retvalue.append(self.letters[self.value[i]])

                        self.value[3] += 1
                        for i  in range(3, 0, -1):
                                if self.value[i] > 25:
                                        self.value[i] = 0
                                        self.value[i-1] += 1
                        if self.value[0] > 25:
                                self.value[0] = 0
                        return "".join(retvalue)

class roman(object):
        romanvals=["M", "CM","D","CD","C","XC","L", "XL","X","IX","V","IV","I"]
        decvals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        assert(len(romanvals) == len(decvals))

        def __init__(self, value, case='upper'):
                value = int(value)
                if not (0 < value < 5000):
                        raise ValueError(_("Roman number sequence value must be between 1 and 5000"))
                self.result = self.convert(value, "", roman.decvals, roman.romanvals)
                if case == "lower":
                        self.result = self.result.lower()

        def convert(self, value, result, decvals, romanvals):
                """Convert decimal value to roman numeral notation.

                value is the value to convert.
                result is the result so far
                romanvals and decvals are the lists so far"""

                if not decvals:
                        return result
                else:
                        if value < decvals[0]:
                                return self.convert(value, result, decvals[1:], romanvals[1:])
                        else:
                                return self.convert(value-decvals[0], result+romanvals[0], decvals, romanvals)


def attributesFromDict(d):
        """build self attributes from a dictionary d."""

        # based on Python Cookbook, 2nd edition 6.18

        self = d.pop('self')
        for name, value in list(d.items()):
                setattr(self, name, value)

def resolvestr(afunc):
        """Return a callable for afunc and build its parameters

        afunc may be a callable object or a string in the form module.func
        or module.func(parm=value,...)to be imported.
        a parameter, _first is always created with value True if afunc is a string.
        """
        global CUSTOMPARAMS
        f, p = factor(afunc)
        CUSTOMPARAMS[f] = p   # add to parameter dictionary using module.function as the key

        if callable(f):
                return afunc   # no parameters
        else:
                bf = f.split(".")
                if len(bf) != 2:
                        raise ValueError(_("function reference not valid: %s") % f)
                try:
                        exec("from %s import %s" % (bf[0], bf[1]))
                        customfunction = locals()[bf[1].strip()]
                except:
                        raise ImportError(_("Import failure.  function: %s, module: %s") % (bf[1], bf[0]))
                argspec = inspect.getfullargspec(customfunction)[0]
                nargs = len(argspec)
                if nargs < 1 or nargs > 2:
                        raise ValueError(_("Invalid custom function signature.\nToo few arguments: %s") % ", ".join(argspec))
                elif nargs > 1:       # indicates function provides for custom params
                        customfunction = functools.partial(customfunction, custom=CUSTOMPARAMS[f])
                return customfunction		

def factor(afunc):
        """decompose the string m.f or m.f(parms) and return function and parameter dictionary

        afunc has the form xxx or xxx(p1=value, p2=value,...)
        create a dictionary from the parameters consisting of at least _first:True.
        parameter must have the form name=value, name=value,... or name:value, name:value,...
        """

        mo = re.match(r"([^(]+)(\(.+\)$)", afunc)
        if not mo is None:       # parameters found, make a dictionary of them
                params = eval("dict" + mo.group(2).replace(r"\u", "/u"))
                f = mo.group(1)
        else:
                params = {}
                f = afunc
        params["_first"] = True
        params["_designatedOutput"] = desout
        # basic sanity check for parameter expression
        if '(' in f or ')' in f or '=' in f or ',' in f:
                if not isinstance(afunc, str):
                        afunc = str(afunc, locale.getlocale()[1])
                raise ValueError(_("Invalid customfunction parameter expression: %s") % afunc)
        return f, params

class NonProcPivotTable(object):
        """Accumulate an object that can be turned into a basic pivot table once a procedure state can be established"""

        def __init__(self, omssubtype, outlinetitle="", tabletitle="", caption="", rowdim="", coldim="", columnlabels=[],
                     procname="Messages"):
                """omssubtype is the OMS table subtype.
                caption is the table caption.
                tabletitle is the table title.
                columnlabels is a sequence of column labels.
                If columnlabels is empty, this is treated as a one-column table, and the rowlabels are used as the values with
                the label column hidden

                procname is the procedure name.  It must not be translated."""

                attributesFromDict(locals())
                self.rowlabels = []
                self.columnvalues = []
                self.rowcount = 0

        def addrow(self, rowlabel=None, cvalues=None):
                """Append a row labelled rowlabel to the table and set value(s) from cvalues.

                rowlabel is a label for the stub.
                cvalues is a sequence of values with the same number of values are there are columns in the table."""

                if cvalues is None:
                        cvalues = []
                self.rowcount += 1
                if rowlabel is None:
                        self.rowlabels.append(str(self.rowcount))
                else:
                        self.rowlabels.append(rowlabel)
                if not _isseq(cvalues):
                        cvalues = [cvalues]
                self.columnvalues.extend(cvalues)

        def generate(self):
                """Produce the table assuming that a procedure state is now in effect if it has any rows."""

                privateproc = False
                if self.rowcount > 0:
                        try:
                                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
                        except:
                                StartProcedure(_("Messages"), self.procname)
                                privateproc = True
                                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
                        if self.caption:
                                table.Caption(self.caption)
                        # Note: Unicode strings do not work as cell values in 18.0.1 and probably back to 16
                        if self.columnlabels != []:
                                table.SimplePivotTable(self.rowdim, self.rowlabels, self.coldim, self.columnlabels, self.columnvalues)
                        else:
                                table.Append(spss.Dimension.Place.row,"rowdim",hideName=True,hideLabels=True)
                                table.Append(spss.Dimension.Place.column,"coldim",hideName=True,hideLabels=True)
                                colcat = spss.CellText.String("Message")
                                for r in self.rowlabels:
                                        cellr = spss.CellText.String(r)
                                        table[(cellr, colcat)] = cellr
                        if privateproc:
                                spss.EndProcedure()
def _isseq(obj):
        """Return True if obj is a sequence, i.e., is iterable.

        Will be False if obj is a string or basic data type"""

        if isinstance(obj, str):
                return False
        else:
                try:
                        iter(obj)
                except:
                        return False
                return True

def StartProcedure(procname, omsid):
        """Start a procedure

        procname is the name that will appear in the Viewer outline.  It may be translated
        omsid is the OMS procedure identifier and should not be translated.

        Statistics versions prior to 19 support only a single term used for both purposes.
        For those versions, the omsid will be use for the procedure name.

        While the spss.StartProcedure function accepts the one argument, this function
        requires both."""

        try:
                spss.StartProcedure(procname, omsid)
        except TypeError:  #older version
                spss.StartProcedure(omsid)