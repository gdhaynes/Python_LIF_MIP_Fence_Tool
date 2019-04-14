# RasterManager.py
# ---------------------------------------------------------------------------------
# Developer:
#   Grant Haynes
#
# Purpose:
#   These classes create a collection of raster objects and contains methods
#   to do the following
#       -Get the rasters and related info from input
#       -Store intercept geometry
#       -Plot the "fence"
# ---------------------------------------------------------------------------------

import arcpy, os, traceback

class Raster:
    # Things on instantiation go here
    def __init__(self, path, fenceXcoords = [], fenceYcoords = []):
        # Constructors
        self.path = path
        self.fenceXcoords = fenceXcoords
        self.fenceYcoords = fenceYcoords

class RasterDataCollection():
    # Things on instantiation go here
    def __init__(self):

        # Constructor
        self.rasterDataCollection = []

    # Methods
    def addrasterdata(self, path):
        rasterToAdd = Raster(path)
        self.rasterDataCollection.append(rasterToAdd)                         

    def addrasterfencegeometry(self, path, fenceXcoord, fenceYcoord):
        i = 0
        for raster in self.rasterDataCollection:
            if raster.path == path:
                self.rasterDataCollection[i].fenceXcoords.append(fenceXcoord)
                self.rasterDataCollection[i].fenceYcoords.append(fenceYcoord)
            i += 1

    def plotfencefromraster(self, outputWorspace, outputFeatureName):

        try:
            outFilePath = os.path.join(outputWorspace, outputFeatureName)
            arcpy.CreateFeatureclass_management(outputWorspace, outputFeatureName, "POLYLINE")
            arcpy.AddField_management(outFilePath, "RasterID", "TEXT")

            for rasterDataObject in self.rasterDataCollection:
                rasterName = os.path.basename(rasterDataObject.path)

                tempPoint = os.path.join(arcpy.env.scratchGDB, "TempRasterFencePoint")
                arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB, "TempRasterFencePoint", "POINT")

                tempLine = os.path.join(arcpy.env.scratchGDB, "TempRasterFenceLine")

                i = 0
                for xCoord in rasterDataObject.fenceXcoords:
                    cursor = arcpy.da.InsertCursor(tempPoint, ["SHAPE@XY"])
                    row = (xCoord, rasterDataObject.fenceYcoords[i])
                    cursor.insertRow([row])
                    del cursor
                    i += 1

                arcpy.PointsToLine_management(tempPoint, tempLine)
                arcpy.AddField_management(tempLine, "RasterID", "TEXT")
                arcpy.CalculateField_management(tempLine, "RasterID", rasterName)
                arcpy.CopyFeatures_management(tempLine, outFilePath)

                arcpy.Delete_management(tempLine)
                arcpy.Delete_management(tempPoint)

        except Exception:
            arcpy.AddMessage(traceback.format_exc())
        finally:
            if arcpy.Exists(tempLine):
                arcpy.Delete_management(tempLine)
            if arcpy.Exists(tempPoint):
                arcpy.Delete_management(tempPoint)