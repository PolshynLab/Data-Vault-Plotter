﻿# Data-Vault-Plotter
 
Generates plots from Data Vault files. The software can be used to plot incoming data live or view saved files.  

The live-plotting tool can both look for newly created files in a specified Data Vault directory, or plot from an already active data set and plot new data as it is added to the file. Saved data can be plotted from any directory.
 
The plotter has three main functions, all of which can be accessed from the software's main window:
 
 Setup Listener:
 - Opens a Data Vault explorer that allows the user to specify which Data Vault directory the plotter should listen to. When a new file is created in the speified directory, the software will prompt the user to live plot the data as it comes in
 - 1D live plots can be set to display between 1 and 5 of the most recent traces added to the file
 
 Live Plotting from an existing file:
 - Opens a Data Vault explorer that allows the user to select any existing Data Vault file to live-plot from. Once a data set is selected , the user is prompted to specify any 2D and 1D plots they would like to view as data is added to the file
 
 Plot Saved Data:
 - Allows the user to browse all available data sets in the Vault and select a file to plot from. The user is then prompted to specify any 2D plots they would like to generate from the selected file.
 - Line cuts can be plotted from any 2D plot
 - Both 2D plots and 1D line cuts can be saved as MATLAB files
 - Notes can be added to the plots in an integrated Notepad and the notes, along with either the full 2D plot or a line cut, can be saved as a PDF
