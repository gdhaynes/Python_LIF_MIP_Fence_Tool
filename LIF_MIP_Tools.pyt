# MIP/LIF Cross Section Tool
# ---------------------------------------------------------------------------------
# Developer:
#   Grant Haynes
# 
# ArcVersion:
#   Developed with Arcmap 10.6
#
# Development Environment:
#   Visual Studio Code
#
# Purpose:
#   This tool is designed to read borings along a cross section line and then
#   read borehole data from MIP/LIF logs and create a point file from the depths 
#   and distances along the line. The data at the point can then be interpolated 
#   to do analysis

# Future additions:
#   Code the ability to read from a lithologic table and create contancts
#   Add the ability to intersect interpolated surfaces at each point

# Script Start
# ================================================================
# Import modules 
import arcpy, os, traceback, math

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        self.label = "LIF MIP Cross Section Tool"
        self.description = "A tool for creating cross sections of downhole probe data"
        self.canRunInBackground = False

    def getParameterInfo(self):

        # Input Geometries
        # ================================================================ 
        CrossSectionLine = arcpy.Parameter(
            displayName="Input cross Section Line",
            name="Input_Cross_Section_Line",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        Borings = arcpy.Parameter(
            displayName="Input MIP or LIF Borings",
            name="Input_MIP_or_LIF_Borings",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        # ================================================================ 

        # Data Directory and data information variables
        # ================================================================
        BoringIDField = arcpy.Parameter(
            displayName="Boring ID Field",
            name="Boring_ID_Field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        MIP_LIF_Directory = arcpy.Parameter(
            displayName="MIP or LIF data directory",
            name="MIP_or_LIF_data_directory",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input")
        DataColumn = arcpy.Parameter(
            displayName="Data Log Column",
            name="Data_Log_Column",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        # ================================================================ 

        # Output feature dataset
        # ================================================================ 
        OutputPointDataSet = arcpy.Parameter(
            displayName="Output Point Dataset",
            name="Output Point Dataset",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        # ================================================================ 

        BoringIDField.filter.type = "ValueList"
        BoringIDField.filter.list = ["<marker>"]

        params = [CrossSectionLine, Borings, BoringIDField, MIP_LIF_Directory, DataColumn, OutputPointDataSet]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        if parameters[1].value:
            desc = arcpy.Describe(parameters[1].valueAsText)
            fields = desc.fields
            fieldList = []
            for field in fields:
                if field.type.upper() in ["STRING", "TEXT"]:
                    fieldList.append(field.name)
            parameters[2].filter.list = fieldList
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        try:
            # Input geometry calculation section
            # ================================================================
            # Variables
            CrossSectionLine = parameters[0].valueAsText
            inputBorings = parameters[1].valueAsText
            inputPointSR = arcpy.Describe(inputBorings).SpatialReference

            # Create a temporary copy of the Borings that lie along the cross section line
            tempBoringLayer = arcpy.env.scratchGDB + r"\TempBoring"
            arcpy.SelectLayerByLocation_management(inputBorings, "INTERSECT", CrossSectionLine)
            arcpy.CopyFeatures_management(inputBorings, tempBoringLayer)
            arcpy.SelectLayerByAttribute_management(inputBorings, "CLEAR_SELECTION")

            # Calculate the cumulative distances of borings along the line
            lineIndex = 0
            cumulativeLength = 0
            xCoord = []
            yCoord = []
            arcpy.MakeFeatureLayer_management(tempBoringLayer, "tempBoringLyr")
            arcpy.AddField_management(tempBoringLayer, "DistanceFromStart", "DOUBLE")

            cursor= arcpy.da.SearchCursor(CrossSectionLine, ["SHAPE@"])
            for row in cursor:
                for lines in row:
                    for line in lines:
                        for point in line:
                            # Create a temp point at each vertex along this line
                            xCoord.append(point.X)
                            yCoord.append(point.Y)
                            rawPoint = arcpy.Point(xCoord[lineIndex], yCoord[lineIndex])
                            point = arcpy.PointGeometry(rawPoint)
                            tempPoint = arcpy.env.scratchGDB + r"\TempPoint"
                            arcpy.CopyFeatures_management(point, tempPoint)
                            arcpy.DefineProjection_management(tempPoint, inputPointSR)

                            # Select the a point on the temp boring layer based on the temp point
                            # this will select the points in the temp point layer by their order on line
                            arcpy.SelectLayerByLocation_management("tempBoringLyr", "INTERSECT", tempPoint, "", "NEW_SELECTION", "NOT_INVERT")

                            if lineIndex > 0:
                                cumulativeLength += math.sqrt((xCoord[lineIndex] - xCoord[lineIndex-1])**2 + (yCoord[lineIndex] - yCoord[lineIndex-1])**2)
                            arcpy.CalculateField_management("tempBoringLyr", "DistanceFromStart", cumulativeLength)
                            arcpy.SelectLayerByAttribute_management("tempBoringLyr", "CLEAR_SELECTION")
                            arcpy.Delete_management(tempPoint)
                            lineIndex += 1
            del cursor
            # ================================================================

            # Classes to create objects to hold boring data
            class Boring:
                def __init__(self, boreID, xValue):
                    self.boreID = boreID
                    self.xValue = xValue

            class BoringData:
                def __init__(self, boreID, xValue, yValues = [], dataValues = []):                
                    self.boreID = boreID
                    self.xValue = xValue    
                    self.yValues = yValues
                    self.dataValues = dataValues

            boringInfo = []
            with arcpy.da.SearchCursor(tempBoringLayer, [parameters[2].valueAsText, "DistanceFromStart"]) as cursor:
                for row in cursor:
                    
                    boring = Boring(row[0], row[1])
                    boringInfo.append(boring)
            
            boringDataObjects = []
            for root, dirs, files in os.walk(parameters[3].valueAsText):
                for filename in files:
                    ext = filename.split(".")
                    if ext[-1].upper() == "MHP":

                        fileBoreID = filename
                        if fileBoreID[4] == "0":
                            fileBoreID = fileBoreID[:4] + fileBoreID[5:]
                            fileBoreID = fileBoreID[:-4]
                        elif fileBoreID[3] == "0":
                            fileBoreID = fileBoreID[:3] + fileBoreID[4:]
                            fileBoreID = fileBoreID[:-4]
                        arcpy.AddMessage("ID from file " + fileBoreID)

                        depths = []
                        data = []
                        with open(os.path.join(root, filename), "r") as lines:
                            for line in lines:
                                lineParts = line.split('\t')
                                if lineParts[0].replace('.','',1).isdigit() and lineParts[int(parameters[4].valueAsText)-1].replace('.','',1).isdigit():
                                    depths.append(lineParts[0])
                                    data.append(lineParts[int(parameters[4].valueAsText)-1]) 
                        i = 0                    
                        while i <= len(boringInfo) - 1:
                            arcpy.AddMessage(boringInfo[i].boreID)
                            if fileBoreID == boringInfo[i].boreID:
                                boringData = BoringData(filename, boringInfo[i].xValue, depths, data)
                                boringDataObjects.append(boringData)
                            i += 1

            # Output data creation section
            # ================================================================

            outputDataset = parameters[5].valueAsText
            outputDirectory = os.path.dirname(os.path.abspath(outputDataset))
            out_file_name = os.path.basename(outputDataset)
            arcpy.CreateFeatureclass_management(outputDirectory, out_file_name, "POINT")
            arcpy.AddField_management(outputDataset, "VALUE", "DOUBLE")

            for boringDataObject in boringDataObjects:
                x = boringDataObject.xValue
                for i in range(len(boringDataObject.yValues)):
                    row = (boringDataObject.dataValues[i], ( x , boringDataObject.yValues[i]))
                    cursor = arcpy.da.InsertCursor(outputDataset,  ["VALUE", "SHAPE@XY"])
                    cursor.insertRow(row)
                    del cursor
            # ================================================================
        except Exception as e:
            arcpy.AddMessage(e)
        finally:
            arcpy.Delete_management(tempBoringLayer)
        return