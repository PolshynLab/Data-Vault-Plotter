# Data-Vault-Plotter
 
Generates plots from Data Vault files. The software can be used to plot incoming data live or view saved files.  

The live-plotting tool can both look for newly created files in a specified Data Vault directory, or plot from an already active data set and plot new data as it is added to the file. Saved data can be plotted from any directory.
 
The plotter has three main functions, all of which can be accessed from the software's main window:
 
 Setup Listener:
 - Selects the single Data Vault directory to monitor. New files with a `live_plots` parameter automatically open the requested plots; files without it are ignored
 - Only the main window's directory-selection controls change the monitored directory. Browsing saved files or manually selecting a live file does not change it
 - 1D live plots can be set to display between 1 and 5 of the most recent traces added to the file
 
 Live Plotting from an existing file:
 - Opens a Data Vault explorer that allows the user to select any existing Data Vault file to live-plot from. Once a data set is selected , the user is prompted to specify any 2D and 1D plots they would like to view as data is added to the file
 - Plot titles include the leading Data Vault file number so multiple live plot windows can be matched to their source data set
 
 Plot Saved Data:
 - Allows the user to browse all available data sets in the Vault and select a file to plot from. The user is then prompted to specify any 2D and/or 1D plots they would like to generate from the selected file.
 - Plot titles include the leading Data Vault file number so multiple saved plot windows can be matched to their source data set
 - Line cuts can be plotted from any 2D plot
 - Both 2D plots and 1D line cuts can be saved as MATLAB files
 - Notes can be added to the plots in an integrated Notepad
 
 Plot Setup:
 - 1D and 2D plots can be created directly from one measured quantity, or from an arithmetic operation between two measured quantities
 - Supported operations are addition, subtraction, multiplication, and division
 - An optional gain can be applied to the plotted quantity
 
# Adding Data Vault Parameters to Enable Plotting:

For every independent variable add a range and a number of points using the following syntax replacing #### with your variable name

dv.add_parameter('####_pnts', number of points)
dv.add_parameter('####_rng', (minimum value, maximum value))

where dv is your LabRAD Data Vault connection. For example, for the independent varialbe 'p0' which will take on 100 values between 0 and 5 you should add:
 
dv.add_parameter('p0_pnts', 100)
dv.add_parameter('p0_rng', (0,5))

## Automatic Live Plots

Add `live_plots` to a newly created file in the monitored directory. Its value is an outer tuple of plot specifications:

- 1D trace: `(x_axis, quantity)`
- 2D map: `(x_axis, y_axis, quantity)`

The final `quantity` can be any of the following:

| Quantity | Plotted value |
| --- | --- |
| `'X1'` | X1, unchanged |
| `('X1', 1000.0)` | 1000 * X1 |
| `('X1', '/', 'Y3')` | X1 / Y3 |
| `('X1', '/', 'Y3', 1000.0)` | 1000 * (X1 / Y3) |

Supported operations are `+`, `-`, `*`, and `/`. Gain multiplies the result **after** the operation. Omitted gain means no scaling; explicit `-1` inverts the result and `0` produces zero. The same gain behavior applies to manually configured live plots (leave the gain field blank for no scaling). Division by zero produces zero, as in the existing plotter. Saved-plot gain behavior is unchanged.

Legacy specifications such as `('V', 'X1')` and `('V', 'B', 'X1')` remain supported and can be mixed with extended specifications:

```python
dv.add_parameter('vt_rng', (-1, 1))
dv.add_parameter('vt_pnts', 100)
dv.add_parameter('vb_rng', (0, 5))
dv.add_parameter('vb_pnts', 100)
dv.add_parameter('B_rng', (-1, 1))
dv.add_parameter('B_pnts', 51)
dv.add_parameter('live_plots', (
    ('vt', 'ans_1'),                                % 1D plot of 'ans_1' signal
    ('vt', 'ans_2'),
    ('vt', ('ans_2', '/', 'ans_1')),                % 1D plot of the ratio of two signals
    ('vt', ('ans_2', '/', 'ans_1', 1000.0)),        % 1D plot of the ratio with additional gain of 1000
    ('vt', 'vb', 'ans_2'),                          % 2D plot 
    ('vt', 'vb', ('ans_2', '/', 'ans_1')),          % 2D plot of the ratio with gain of 1000 
    ('vt', 'vb', ('ans_2', '/', 'ans_1', 1000.0)),  % 2D plot of the ratio with gain of 1000 
))
```

For a single plot, retain the outer tuple and trailing comma:
```python
dv.add_parameter('live_plots', (('vt', 'ans_1'),))
```

Variable names must match the dataset's variable names exactly and be unambiguous. Each coordinate axis needs `<axis>_rng` (two finite, distinct endpoints, in either sweep direction) and `<axis>_pnts` (a positive integer). Gain must be a finite real number. Malformed entries are reported in the console without preventing other valid plots from opening.

The automatic path checks metadata immediately and retries every 0.5 seconds for up to 10 seconds after the new-file notification. Each plot opens once its required metadata is available; entries still missing metadata at the deadline are reported in the console. Files without `live_plots` are ignored quietly. Metadata added after this retry window does not trigger automatic plotting; use manual live plotting instead. The interval and timeout are controlled by `AUTO_PLOT_RETRY_INTERVAL` and `AUTO_PLOT_METADATA_TIMEOUT` in the main script.

Manual live plotting does not wait for metadata and does not require `live_plots`. It continues to prompt for any missing axis ranges and point counts. Automatic plotting only reacts to new files created while the listener is active, not existing files when a directory is selected.
