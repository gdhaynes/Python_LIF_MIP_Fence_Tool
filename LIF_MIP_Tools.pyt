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
#   to do analysis. It is also designed to extract depth values from any included
#   raster and include intercept lines from that analysis

# Future additions:
#   Code the ability to read from a lithologic table and create contacts and
#   or seperate the base hydrostatic pressure from the conductivity readings
#   and derive lithology from that
# ---------------------------------------------------------------------------------

# Script Start
# =================================================================================
# Import built in modules 
import arcpy, os, traceback, math
# Import custom modules
import BoringManager, RasterManager

class Toolbox(object):
    def __init__(self):
        #Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
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

        # Important fields from theboring layer
        BoringIDField = arcpy.Parameter(
            displayName="Boring ID Field",
            name="Boring_ID_Field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        BoringElevationField = arcpy.Parameter(
            displayName="Boring Elevation Field",
            name="Boring_Elevation_Field",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # MIP or LIF data directory and column
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

        # Rasters to be intersected
        Surfaces = arcpy.Parameter(
			displayName="Raster Layers",
			name="surfaces",
			datatype= "GPValueTable",
			parameterType="Required",
			direction="Input")
        Surfaces.columns = [["GPRasterLayer", "Input Rasters"]]

        # Output feature dataset
        OutputPointDataSet = arcpy.Parameter(
            displayName="Output Fence",
            name="Output Fence",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        BoringIDField.filter.type = "ValueList"
        BoringIDField.filter.list = ["None"]

        BoringElevationField.filter.type = "ValueList"
        BoringElevationField.filter.list = ["None"]

        params = [CrossSectionLine, Borings, BoringIDField, BoringElevationField, MIP_LIF_Directory, DataColumn, Surfaces, OutputPointDataSet]
        return params

    def isLicensed(self):
        # Set whether tool is licensed to execute.
        return True

    def updateParameters(self, parameters):
        # Update the choice list for bore ID field and the boring elevation field to be a text
        # Field present in the boring dataset
        if parameters[1].value:
            desc = arcpy.Describe(parameters[1].valueAsText)
            fields = desc.fields
            IDfieldList = []
            ElevationFieldList = []
            for field in fields:
                if field.type.upper() in ["STRING", "TEXT"]:
                    IDfieldList.append(field.name)
                elif field.type.upper() in ["DOUBLE", "FLOAT"]:
                    ElevationFieldList.append(field.name) 
            parameters[2].filter.list = IDfieldList
            parameters[3].filter.list = ElevationFieldList
        return

    def updateMessages(self, parameters):
        # Modify the messages created by internal validation for each tool
        # parameter.  This method is called after internal validation.
        return

    def execute(self, parameters, messages):
        try:
            # assign the input borings to a constant so it can be
            # easily referenced anwherere
            inputBorings = parameters[1].valueAsText

            # create instances of the collection classes to hold data and create
            # output geometries
            boringManager = BoringManager.BoringDataCollection()
            rasterManager = RasterManager.RasterDataCollection()
            rasterList = parameters[6].valueAsText.split(';')
            for raster in rasterList:
                rasterManager.addrasterdata(raster)

            arcpy.AddMessage("Reading input features and calculating fence length")
            # use a serach cursor to "walk" down the cross section line and select borings based on
            # the order they were drawn and calculate the cumulative (x) distances of borings along the line
            lineIndex = 0
            cumulativeLength = 0
            xCoord = []
            yCoord = []
            cursor = arcpy.da.SearchCursor(parameters[0].valueAsText, ["SHAPE@"])
            for row in cursor:
                for lines in row:
                    for line in lines:
                        for point in line:
                            # Create a temp point at each vertex along this line
                            xCoord.append(point.X)
                            yCoord.append(point.Y)
                            newPoint = arcpy.PointGeometry(arcpy.Point(xCoord[lineIndex], yCoord[lineIndex]))
                            tempPoint = os.path.join(arcpy.env.scratchGDB, "TempPoint")
                            arcpy.CopyFeatures_management(newPoint, tempPoint)
                            arcpy.MakeFeatureLayer_management(tempPoint, "tempPoint"+str(lineIndex))

                            # Select the point in the input borings that is within 1' of the temp point feature layer
                            arcpy.SelectLayerByLocation_management(inputBorings, "INTERSECT", "tempPoint"+str(lineIndex), "", "NEW_SELECTION", "NOT_INVERT")
                            arcpy.Delete_management(tempPoint)

                            if lineIndex > 0:
                                cumulativeLength += math.sqrt((xCoord[lineIndex] - xCoord[lineIndex-1])**2 + (yCoord[lineIndex] - yCoord[lineIndex-1])**2)
                            
                            if parameters[3].valueAsText is None:
                                cursorI = arcpy.da.SearchCursor(inputBorings, [parameters[2].valueAsText])
                                for row in cursorI:
                                    boringManager.addboring(row[0], cumulativeLength, "0")
                                del cursorI
                            else:
                                cursorII = arcpy.da.SearchCursor(inputBorings, [parameters[2].valueAsText, parameters[3].valueAsText])
                                for row in cursorII:
                                    boringManager.addboring(row[0], cumulativeLength, row[1])
                                del cursorII
                            for surface in rasterManager.rasterDataCollection:
                                rasterElevation = arcpy.GetCellValue_management(surface.path, str(point.X) + " " + str(point.Y)).getOutput(0)
                                if rasterElevation.upper() != "NODATA":
                                    rasterManager.addrasterfencegeometry(surface.path, cumulativeLength, float(rasterElevation))
                                        
                            arcpy.SelectLayerByAttribute_management(inputBorings, "CLEAR_SELECTION")
                            lineIndex += 1
            del cursor

            # Iterate through the data directory and pull the depth and data values to complete
            # the corresponding boring object in the boring collection
            arcpy.AddMessage("Reading data from MIP/LIF data logs")
            for root, dirs, files in os.walk(parameters[4].valueAsText):
                for filename in files:
                    fileNameParts = filename.split('.')
                    if fileNameParts[-1].upper() == "MHP" or fileNameParts[-1].upper() == "TXT":

                        # Remove zero padding    
                        fileBoreID = fileNameParts[0].replace("-0", "-")

                        depths = []
                        data = []
                        with open(os.path.join(root, filename), "r") as lines:
                            for line in lines:
                                lineParts = line.split('\t')
                                if lineParts[0].replace('.','',1).isdigit() and lineParts[int(parameters[5].valueAsText)-1].replace('.','',1).isdigit():
                                    depths.append(float(lineParts[0]))
                                    data.append(lineParts[int(parameters[5].valueAsText)-1]) 

                        # Add the y and data values to the corresponding boring
                        # in the boring collection here
                        boringManager.addboringdata(fileBoreID, depths, data)

            # plot the fence vectors
            arcpy.AddMessage("Plotting fence from MIP/LIFs")
            boringManager.plotboringdatafence(os.path.dirname(parameters[7].valueAsText), os.path.basename(parameters[7].valueAsText) + "_Probe_Data_Points")

            arcpy.AddMessage("Plotting fence from rasters")
            rasterManager.plotfencefromraster(os.path.dirname(parameters[7].valueAsText), os.path.basename(parameters[7].valueAsText) + "_Raster_Lines")
        except Exception:
            arcpy.AddMessage(traceback.format_exc())
        return