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
#   Code the ability to read from a lithologic table and create contacts
#   Add the ability to intersect interpolated surfaces at each point e.g
#   elevations from a DEM and GW elevation from a GW raster
# ---------------------------------------------------------------------------------

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
            parameterType="Required",
            direction="Input")
        DataColumn = arcpy.Parameter(
            displayName="Data Log Column",
            name="Data_Log_Column",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        # ================================================================ 

        # Output feature dataset
        # ================================================================ 
        OutputPointDataSet = arcpy.Parameter(
            displayName="Output Point Dataset",
            name="Output Point Dataset",
            datatype="GPFeatureLayer",
            parameterType="Required",
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
        # Update the choice list for bore ID fields to be a text
        # Field present in the boring dataset
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
        # Modify the messages created by internal validation for each tool
        # parameter.  This method is called after internal validation.
        return

    def execute(self, parameters, messages):

        # Classes to create objects to hold boring data
        class Boring:
            def __init__(self, boreID, xValue, yValues = [], dataValues = []):
                # Constructors
                self.boreID = boreID
                self.xValue = xValue
                self.yValues = yValues
                self.dataValues = dataValues

        class BoringCollection:
            # Things on instantiation go here
            def __init__(self):

                # Constructors
                self.boringCollection = []

            # Methods
            def addboring(self, boreID, xValue):
                boringToAdd = Boring(boreID, xValue)
                self.boringCollection.append(boringToAdd)
                arcpy.AddMessage(len(self.boringCollection))                           

            def addboringdata(self,boreID, yValues = [], dataValues = []):
                i = 0
                for boring in self.boringCollection:
                    if boring.boreID == boreID:
                        self.boringCollection[i].yValues = yValues
                        self.boringCollection[i].dataValues = dataValues
                    i += 1 
        #try:
        # Input geometry calculation section
        # ================================================================
        # Variables
        CrossSectionLine = parameters[0].valueAsText
        inputBorings = parameters[1].valueAsText
        inputPointSR = arcpy.Describe(inputBorings).SpatialReference

        # Create a temporary copy of the Borings that lie along the cross section line
        tempBoringLayer = os.path.join(arcpy.env.scratchGDB, "TempBoring")
        arcpy.SelectLayerByLocation_management(inputBorings, "INTERSECT", CrossSectionLine)
        arcpy.CopyFeatures_management(inputBorings, tempBoringLayer)
        arcpy.SelectLayerByAttribute_management(inputBorings, "CLEAR_SELECTION")

        # Calculate the cumulative distances of borings along the line
        lineIndex = 0
        cumulativeLength = 0
        xCoord = []
        yCoord = []
        arcpy.AddField_management(tempBoringLayer, "DistanceFromStart", "DOUBLE")
        arcpy.MakeFeatureLayer_management(tempBoringLayer, "tempBoringLyr")

        # create an instance of boing collection to create a collection of boring information
        boringCollection = BoringCollection()

        # use a serach cursor to "walk" down the cross section line and select borings based on
        # the order they were drawn
        cursor = arcpy.da.SearchCursor(CrossSectionLine, ["SHAPE@"])
        for row in cursor:
            for lines in row:
                for line in lines:
                    for point in line:
                        # Create a temp point at each vertex along this line
                        xCoord.append(point.X)
                        yCoord.append(point.Y)
                        rawPoint = arcpy.Point(xCoord[lineIndex], yCoord[lineIndex])
                        point = arcpy.PointGeometry(rawPoint)
                        tempPoint = os.path.join(arcpy.env.scratchGDB, "TempPoint")
                        arcpy.CopyFeatures_management(point, tempPoint)
                        arcpy.MakeFeatureLayer_management(tempPoint, "tempPoint"+str(lineIndex))

                        # Select the point on the temp boring layer based on the temp point
                        # this will select the points in the temp point layer by their order on line
                        arcpy.SelectLayerByLocation_management("tempBoringLyr", "INTERSECT", "tempPoint"+str(lineIndex), "", "NEW_SELECTION", "NOT_INVERT")
                        arcpy.Delete_management(tempPoint)

                        if lineIndex > 0:
                            cumulativeLength += math.sqrt((xCoord[lineIndex] - xCoord[lineIndex-1])**2 + (yCoord[lineIndex] - yCoord[lineIndex-1])**2)

                        cursor = arcpy.da.SearchCursor("tempBoringLyr", parameters[2].valueAsText)
                        i = 0
                        for row in cursor:
                            i += 1
                            boringCollection.addboring(row[0], cumulativeLength)
                        arcpy.SelectLayerByAttribute_management("tempBoringLyr", "CLEAR_SELECTION")
                        lineIndex += 1
        del cursor

        # Iterate through the data directory and pull the depth and data values to complete
        # the corresponding boring object in the boring collection
        arcpy.AddMessage("Reading data from MIP/LIF data logs")
        for root, dirs, files in os.walk(parameters[3].valueAsText):
            for filename in files:
                ext = filename.split(".")
                if ext[-1].upper() == "MHP" or ext[-1].upper() == "TXT":

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
                                depths.append(float(lineParts[0])*-1)
                                data.append(lineParts[int(parameters[4].valueAsText)-1]) 

                    # Add the y and data values to the corresponding boring
                    # in the boring collection here
                    boringCollection.addboringdata(fileBoreID, depths, data)


        # Output data creation section
        # ================================================================

        outputDataset = parameters[5].valueAsText
        outputDirectory = os.path.dirname(os.path.abspath(outputDataset))
        out_file_name = os.path.basename(outputDataset)
        arcpy.CreateFeatureclass_management(outputDirectory, out_file_name, "POINT")
        arcpy.AddField_management(outputDataset, "BOREID", "TEXT")
        arcpy.AddField_management(outputDataset, "VALUE", "DOUBLE")

        for boringDataObject in boringCollection.boringCollection:
            x = boringDataObject.xValue
            boreID = boringDataObject.boreID
            for i in range(len(boringDataObject.yValues)):
                row = (boringDataObject.dataValues[i], boreID, (x , boringDataObject.yValues[i]))
                cursor = arcpy.da.InsertCursor(outputDataset,  ["VALUE", "BOREID", "SHAPE@XY"])
                cursor.insertRow(row)
                del cursor
        # ================================================================
        #except Exception as e:
            #arcpy.AddMessage(e)
        #finally:
        arcpy.Delete_management(tempBoringLayer)
        return