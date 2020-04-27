Developed by: 
	Grant Haynes

Development notes:
	This is a python toolbox that was developed in VS code with python 2.7. It was tested successfully in ArcMap 10.6.
	
Version:
	I, Spring 2019
	
Purpose:
	This tool's purpose is to select and translate the depth measurements of TSV files related to a point GIS dataset along a line of interest into y coordinates and plot each data point along with a data value of interest. This 
	then opens the dataset up to traditional interpolation techniques that are difficult to achieve in 3D. It also intersects raster datasets and plots the translated intersects which are connected into a line representing a 
	"slice" through that raster dataset along the line of interest.
	
	This tool utilizes the following data:
		GIS:
			A line featureclass, representing the path of the geo fence that is desired
			A point featureclass, representing MIP/LIF borings, the borings should have the following attributes:
				A text based identifying field (required), this is used to match the file with the boring
				A numeric elevation field (optional), this measurement will be used to shift the plotted data to account for topography
		Flat Files:
			A directory with the TSV data files of the MIP/LIF GIS dataset. 1 point will have one corresponding data file. Each data file contains rows of data about that point.
	
	This tool produces the following data:
		A vector dataset with the plotted points and raster intersection
		
Known Issues and idiosyncrasies:
	The input line must be snapped to the points desired in the cross section, otherwise the points will not be selected during the "walk" down the line
	No output spatial reference set on the output coordinates, map must us a PCS
	No inherent measurement standardization, all input measurements and map units must be the same
	Additional input validation and error handling will be needed if the tool is to be used by others
	
Future work:
	Intersection of additional vector layers including:
		Building footprints
		Monitor Wells
		Lithologic Soil Borings
	Drawing of lithologic features, that data will come from:
		An some kind of database
		Conductivity readings from the MIP/LIF
	