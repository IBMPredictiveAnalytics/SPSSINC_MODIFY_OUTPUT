# custom functions for use with SPSSINC MODIFY OUTPUT extension command
#Licensed Materials - Property of IBM
#IBM SPSS Products: Statistics General
#(c) Copyright IBM Corp. 2011, 2020
#US Government Users Restricted Rights - Use, duplication or disclosure 
#restricted by GSA ADP Schedule Contract with IBM Corp.

# author: JKP, IBM SPSS

import SpssClient
import os.path
try:
    from spssaux import FileHandles  # user might have too old an spssaux module
except:
    pass

# The custom argument is a dictionary holding the parameters of the call along with
# _first, which is initially True
# _designatedOutput, which holds the designated output window (needed for some apis)

# history
# 28-apr-2012 excelexport function added
# 18-feb-2013 add file handle support to excelexport

def aligntitle(obj, custom):
    """Left align a table
    
    No parameters are expected, and obj must be a pivot table"""
    
    try:
        tbl = obj.GetSpecificType()
        tbl.ClearSelection()
        tbl.SelectTitle()
        tbl.SetHAlign(SpssClient.SpssHAlignTypes.SpssHAlLeft)
    except:
        pass

# MODIFY OUTPUT includes a keyword for inserting page breaks before titles
# This function can be used to set a page break before any item selected by
# the command.  Example:
#SPSSINC MODIFY OUTPUT  TABLES 
#/IF ITEMTITLESTART="a long table"
#/CUSTOM FUNCTION="customoutputfunctions.breakbeforeitem".

def breakbeforeitem(obj):
    "insert page break before selected item"
    obj.SetPageBreak(True)

# debugging
# makes debug apply only to the current thread
#try:
    #import wingdbstub
    #if wingdbstub.debugger != None:
        #import time
        #wingdbstub.debugger.StopDebug()
        #time.sleep(2)
        #wingdbstub.debugger.StartDebug()
    #import thread
    #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
    ## for V19 use
    ##    ###SpssClient._heartBeat(False)
#except:
    #pass
    
imagekwds = {"emf": SpssClient.ChartExportFormat.emf,
    "eps": SpssClient.ChartExportFormat.eps,
    "jpg": SpssClient.ChartExportFormat.jpg,
    "png": SpssClient.ChartExportFormat.png,
    "tiff": SpssClient.ChartExportFormat.tiff,
    "bmp": SpssClient.ChartExportFormat.bmp
    }

# This function exports selected items to Excel.
# Examples:

# Export a custom table from the most recent command to a new Excel file.
#SPSSINC MODIFY OUTPUT TABLES 
#/IF SUBTYPE="'Custom Table'" PROCESS=PRECEDING
#/CUSTOM FUNCTION="customoutputfunctions.excelexport(file='c:/temp/extest.xls')".

# Export all the custom tables in the Viewer to separate sheets named table1, table2, ...
#SPSSINC MODIFY OUTPUT TABLES 
#/IF SUBTYPE="'Custom Table'" PROCESS=ALL
#/CUSTOM FUNCTION="customoutputfunctions.excelexport(file='c:/temp/extest.xls',
#  sheet='table#',action='CreateWorksheet')".

# Export all custom tables to separate files named extest1,xls, extest2, ...
#SPSSINC MODIFY OUTPUT TABLES 
#/IF SUBTYPE="'Custom Table'" PROCESS=ALL
#/CUSTOM FUNCTION="customoutputfunctions.excelexport(file='c:/temp/extest#.xls')

# If charts, models, or tree images are included in the selction, they will go to separate files
# with base name filename_sheetname modified as with other items by use of # in either part.

# This function differs from the OUTPUT EXPORT command in being able to select items
# via the criteria of the command and in how the output files are structured.  Also, it cannot
# put graphical items into the target spreadsheet.  They are written to separate files

def excelexport(obj, custom):
    """Export selected output items to Excel
    
    parameters:
    file - filespec for output (required)
    sheet - sheetname.  Default is "Sheet"
    action - "CreateWorkbook" | "Create Worksheet" | "ModifyWorksheet"
    location - "OverwriteAtCellRef" | "AddColumns" | "AddRows"
    startingCell - starting cell if location is overwrite.  Default is "A1"
    image - image format - "jpg" | "png" | "tiff" | "eps" | "emf" | "bmp"
    
    See OUTPUT EXPORT help for information on these options
    
    Use # in the file or sheet string to insert a sequential number on each
    save operation to avoid overwriting.
    
    The first value listed is the default if there is one.
    
    If an item would overwrite another item in the same command, an error is raised"""
    
    if custom["_first"]:
        custom["_first"] = False
        custom["number"] = 0
        # set defaults
        custom["sheet"] = custom.get("sheet", "Sheet")
        custom["action"] = custom.get("action", "CreateWorkbook")
        custom["location"] = custom.get("location", "OverwriteAtCellRef")
        custom["startingCell"] = custom.get("startingCell", "A1")
        image = custom.get("image", "jpg")
        if not image in list(imagekwds.keys()):
            raise ValueError(_("""Invalid image format: %s""" % image))
        custom["image"] = imagekwds[image]
        
        if not "file" in custom:
            raise ValueError(_("""file parameter must be specified"""))
        # user might have too old a version for file handle support
        try:
            custom["file"] = FileHandles().resolve(custom["file"])
        except:
            pass
        count = custom["file"].count("#") + custom["sheet"].count("#")
        if count > 1:
            raise ValueError(_("""Only one "#" may appear in file and sheet parameters together"""))
        custom["wouldoverwrite"] = (count == 0 and custom["location"] == "OverwriteAtCellRef") or \
            (custom["file"].count("#") == 0 and custom["action"] == "CreateWorkbook")
        
        # desout is the designated output window
        desout = custom["_designatedOutput"]
        # error checking is left to the apis
        desout.SetOutputOptions(SpssClient.DocExportOption.ExcelOperationOptions, custom["action"])
        desout.SetOutputOptions(SpssClient.DocExportOption.ExcelStartingCell, custom["startingCell"])        
        desout.SetOutputOptions(SpssClient.DocExportOption.ExcelLocationOptions, custom["location"])
        
    # Process the current object    
    # check for overwrite
    if custom["wouldoverwrite"] and custom["number"] > 0:
        raise ValueError(_("""Exporting stopped: multiple items would overwrite each other"""))
    
    filename = custom["file"].replace("#", str(custom["number"]))
    sheetname = custom["sheet"].replace("#", str(custom["number"]))
    desout = custom["_designatedOutput"]
    desout.SetOutputOptions(SpssClient.DocExportOption.ExcelSheetNames, sheetname)
    
    # Write graphics objects to separate files named by file and sheet name
    # since ExportToDocument api can't do images
    if obj.GetType() in [SpssClient.OutputItemType.CHART, SpssClient.OutputItemType.TREEMODEL,
        SpssClient.OutputItemType.MODEL]:
        name = os.path.splitext(filename)[0] + "_" + sheetname
        obj.ExportToImage(name, custom["image"])
    else:
        obj.ExportToDocument(filename, SpssClient.DocExportFormat.SpssFormatXls)
    custom["number"] = custom["number"] + 1

    