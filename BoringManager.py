# BoringManager.py
# ---------------------------------------------------------------------------------
# Developer:
#   Grant Haynes
#
# Purpose:
#   These classes create a collection of boring objects and contains methods
#   to do the following
#       -Get the boring information from the GIS data
#       -Match additional information to the GIS data to be plotted later
#       -Plot the boring "fence"
# ---------------------------------------------------------------------------------

import arcpy, os, traceback

class Boring:
    def __init__(self, boreID, xValue, elevationValue, yValues = [], dataValues = []):
        # Constructors
        self.boreID = boreID
        self.xValue = xValue
        self.elevationValue = elevationValue
        self.yValues = yValues
        self.dataValues = dataValues

class BoringDataCollection():
    # Things on instantiation go here
    def __init__(self):

        # Constructor
        self.boringCollection = []

    # Methods
    def addboring(self, boreID, xValue, elevationValue):
        boringToAdd = Boring(boreID, float(xValue), float(elevationValue))
        self.boringCollection.append(boringToAdd)                         

    def addboringdata(self, boreID, yValues = [], dataValues = []):
        i = 0
        for boring in self.boringCollection:
            if boring.boreID == boreID:
                self.boringCollection[i].yValues = yValues
                self.boringCollection[i].dataValues = dataValues
            i += 1

    def plotboringdatafence(self, outputWorspace, outputFeatureName):
        try:
            arcpy.CreateFeatureclass_management(outputWorspace, outputFeatureName, "POINT")
            outputFeatures = os.path.join(outputWorspace, outputFeatureName)
            arcpy.AddField_management(outputFeatures, "BOREID", "TEXT")
            arcpy.AddField_management(outputFeatures, "VALUE", "DOUBLE")

            for boring in self.boringCollection:
                x = boring.xValue
                elevationValue = boring.elevationValue
                boreID = boring.boreID
                for i in range(len(boring.yValues)):
                    cursor = arcpy.da.InsertCursor(outputFeatures,  ["VALUE", "BOREID", "SHAPE@XY"])
                    y = elevationValue-boring.yValues[i]
                    row = (boring.dataValues[i], boreID, (x, y))
                    cursor.insertRow(row)
                    del cursor
        except Exception:
            arcpy.AddMessage(traceback.format_exc())      