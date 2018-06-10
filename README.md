# Data-Vault-Plotter
 
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
 
# Adding Data Vault Parameters to Enable Plotting:

For every independent variable add a range and a number of points using the following syntax replacing #### with your variable name

dv.add_parameter('####_pnts', number of points)
dv.add_parameter('####_rng', (minimum value, maximum value))

where dv is your LabRAD Data Vault connection. For example, for the independent varialbe 'p0' which will take on 100 values between 0 and 5 you should add:
 
dv.add_parameter('p0_pnts', 100)
dv.add_parameter('p0_rng', (0,5))

Adding Data Vault Parameter to Auto-start Plotting
To auto-start plots when your Data Vault file is created, add a parameter 'live_plots' followed by a list of tuples where each tuple is a list of variable names you want to plot on each axis. For a 2D plot, add (x_axis, y_axis, z_axis). For a 1D trace add (x_axis, y_axis). 

For example, the following line will autostart a 2D plot of 'C_v' vs. 'n0' and 'p0', a 2D plot of 'V' vs. 'p0' and 'n0', and a 1D plot of 'T' vs. 'p0':

dv.add_parameter('live_plots', (('n0', 'p0', 'C_v'), ('p0', 'T'), ('p0', 'n0', 'V')))

If you want to only auto-start 1 plot, place the tuple inside a list with brackets []. For instance if you ONLY want to plot 'C_v' vs. 'n0' and 'p0' add the parameter

dv.add_parameter('live_plots', [('n0', 'p0', 'C_v')])
