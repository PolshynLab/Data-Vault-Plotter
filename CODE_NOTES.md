# Data Vault Live Plotter Code Notes

This repository implements a PyQt5 desktop plotter for LabRAD Data Vault datasets. The main executable file in this checkout is `dataVaultLivePlotter.py`; the user-facing description refers to `dataVaultPlotter.py`, which appears to mean the same main application file or an older name for it.

The program has two related jobs:

1. Plot live measurement data while a LabRAD Data Vault dataset is being written.
2. Open saved Data Vault datasets later, build 1D or 2D plots, inspect line cuts, add notes, and export data or reports.

## Runtime Model

The application combines PyQt5, Twisted, and LabRAD:

- PyQt5 provides the GUI windows and dialogs.
- `qt5reactor` integrates the Twisted reactor with the Qt event loop.
- LabRAD async connections are made through `labrad.wrappers.connectAsync`.
- Twisted `@inlineCallbacks` methods allow GUI actions and Data Vault calls to run asynchronously without blocking the interface.
- `pyqtgraph` renders both line plots and image-style 2D plots.

The `__main__` block creates a `QApplication`, installs `qt5reactor`, constructs `dvPlotter`, shows it, and starts `reactor.run()`.

## Main Window: `dvPlotter`

`dvPlotter` is the main `QMainWindow`. It loads `startPlotter.ui` and wires the main buttons:

- `Setup Listener`: choose a Data Vault directory and listen for newly created datasets.
- `Live Plotting`: choose an existing Data Vault dataset and plot new data as it arrives.
- `Plot Saved Data`: choose an existing dataset and plot its already-stored contents.
- `Close`: stop the Twisted reactor, disconnect LabRAD, and close the app.

On startup, `initReact()` connects to LabRAD as `dvPlotter`, stores the Data Vault server as `self.dv`, stores the LabRAD manager as `self.man`, and expires old manager state with `expire_all()`.

When listener mode is enabled, `initListener()` registers for Data Vault `new_dataset` signals in the selected directory. When a new dataset appears, `open_dataset()` opens it, reads its variables and parameters, and checks for the optional `live_plots` parameter. If `live_plots` exists, `initLivePlotting()` converts that parameter into plot definitions and starts plots automatically.

## Data Vault Metadata Expected by the Plotter

The plotter depends heavily on Data Vault variable names and optional parameters.

For each plotted independent axis, the preferred metadata is:

```python
dv.add_parameter("<axis>_rng", (minimum, maximum))
dv.add_parameter("<axis>_pnts", number_of_points)
```

For example, an axis named `p0` can be described by `p0_rng` and `p0_pnts`.

Automatic live plotting is configured by:

```python
dv.add_parameter("live_plots", ...)
```

Each entry in `live_plots` is interpreted as either:

- `(x_axis, y_axis)` for a 1D trace.
- `(x_axis, y_axis, z_axis)` for a 2D image plot.

If required range or point-count metadata is missing during manual live setup, the code opens `extentPrompt` so the user can provide minimum, maximum, and number of points for the needed axes.

## Plot Setup Dialog: `plotSetup`

`plotSetup` is the main configuration dialog for selecting what to plot. It is used for live plots and saved plots, with a `fresh` flag indicating where the request came from:

- `0`: listener-created live plot.
- `1`: live plot from an existing dataset.
- `2`: saved-data plot.

The dialog asks the Data Vault dataset for variables via `dv.variables()`, then fills axis-selection combo boxes. It maintains two dictionaries:

- `plot1DInfo`: definitions for line plots.
- `plot2DInfo`: definitions for image plots.

Each plot definition records:

- Plot title.
- Axis names and Data Vault column indexes.
- Optional second dependent variable.
- Operation between dependent variables: `+`, `-`, `*`, or `/`.
- Optional gain multiplier.
- Axis range and point-count metadata where available.

When the user confirms the dialog, `initPlot()` either starts live plot windows through `dvPlotter.openLivePlots()` or saved plot windows through `dvPlotter.openSavedPlots()`.

## Live 2D Plot Window: `plot2DWindow`

`plot2DWindow` displays incoming 2D data as an image using `pyqtgraph.ImageView`.

Important behavior:

- It opens a separate LabRAD connection for the plot window.
- It registers a unique Data Vault `data_available` listener ID.
- It initializes `plotData` as a NumPy array with shape `[x_points, y_points]`.
- It computes axis bin edges from the axis ranges and point counts.
- Incoming rows are read with `dv.get()`.
- X and Y values are converted to pixel indexes with `np.digitize()`.
- The selected Z value, optional Z operation, and optional gain are written into `plotData`.
- The image is refreshed by calling `setImage()` on the `ImageView`.

This means live 2D plotting assumes that incoming rows contain coordinates that can be binned onto a known rectangular grid.

## Live 1D Plot Window: `plot1DWindow`

`plot1DWindow` displays live line traces using `pyqtgraph.PlotWidget`.

Important behavior:

- Like the 2D live window, it opens its own LabRAD connection and registers a `data_available` listener.
- It builds X-axis bins from the selected range and point count.
- Incoming rows are filtered down to the selected X, Y, and optional second Y column.
- If a second Y column is selected, the configured operation is applied.
- If a gain is provided, the result is multiplied by that gain.
- The plot detects trace boundaries from changes in the binned X step pattern.
- A combo box allows displaying 1 to 5 recent traces with different colors.

The trace-boundary logic is useful for repeated sweeps where the same X axis is scanned multiple times and the user wants recent sweep traces rather than one continuous line.

## Saved 1D Plot Window: `plotSaved1DWindow`

`plotSaved1DWindow` is used for existing datasets. It reads the whole dataset in chunks of 1000 rows using repeated `dv.get(1000)` calls until no more rows are returned.

After loading, it:

- Keeps only the selected columns.
- Applies the optional second Y operation.
- Applies optional gain.
- Plots the resulting X/Y arrays.

It also supports:

- Saving the plotted data as a MATLAB `.mat` file through `scipy.io.savemat`.
- Opening a note editor.
- Exporting a plot image for a PDF-style report workflow.

There are signs that PDF output is incomplete or partly outdated: the code contains commented PyQt WebKit printing logic, while PyQt5 no longer includes the same `QWebView` path by default.

## Saved 2D Plot Window: `plotSaved2DWindow`

`plotSaved2DWindow` reads an entire saved dataset and renders it as a 2D image. It is richer than the live 2D view because it also provides line-cut tools.

Important behavior:

- It loads the dataset in chunks.
- It keeps only selected X, Y, Z, and optional second Z columns.
- It tries to get grid extents and point counts from Data Vault parameters.
- If parameters are missing, it tries to infer grid dimensions from spacing/jumps in the sorted data.
- It fills a NumPy image array from the loaded rows.
- It shows the image with `pyqtgraph.ImageView` using the `inferno` gradient.
- It adds movable horizontal and vertical `InfiniteLine` cursors.
- It extracts and plots a 1D line cut from the current cursor position.

Exports include:

- 1D line-cut `.mat` files.
- 2D flattened `.mat` files containing grid indexes, physical X/Y coordinates, and Z values.
- PDF/report workflow stubs that export plot PNGs and feed HTML templates.

## Directory and Dataset Browsing

Two Data Vault browser dialogs are implemented:

- `dirExplorer`: chooses a directory to listen to for new datasets.
- `dataVaultExplorer`: chooses a specific dataset for live plotting or saved plotting.

Both dialogs use Data Vault directory commands:

- `dv.dir()` to list subdirectories and files.
- `dv.cd()` to move through the Data Vault hierarchy.
- `dv.mkdir()` to create a new directory.

The selected directory is stored as a list path, starting from `['']` for root.

## Notes Editor

`noteEditor` wraps a custom `textEditor`, which is a `QPlainTextEdit` with a line-number gutter implemented by `LineNumberArea`.

Saved plot windows can open this editor and retain the resulting text in `self.notes`. The report-generation code attempts to include those notes in an HTML template when producing PDF-style output.

## Resource and UI Files

The GUI layout is split across Qt Designer `.ui` files:

- `startPlotter.ui`
- `plotSetup.ui`
- `extentPrompt.ui`
- `dvExplorer.ui`
- `dirExplorer.ui`
- `editDatasetInfo.ui`
- `helpWindow.ui`

Image resources are stored under `Resources/Pictures`, and Qt resource bindings are represented by `Resources/dvPlotterResources_rc.py`. The main file currently comments out the import of that resource module, even though several buttons refer to resource URLs such as `:/dvPlotter/Pictures/savePDF.png`. Those icons may require the resource import to be active at runtime.

## Overall User Flow

Typical live-listener flow:

1. Start the app.
2. Choose `Setup Listener`.
3. Select a Data Vault directory.
4. The app registers for `new_dataset` signals in that directory.
5. When a dataset is created, the app opens it.
6. If `live_plots` metadata exists, the app starts the requested plots automatically.
7. Each plot window registers for `data_available` and refreshes as rows arrive.

Typical live-existing-dataset flow:

1. Choose `Live Plotting`.
2. Browse to an existing dataset.
3. Configure 1D and/or 2D plots in `plotSetup`.
4. Provide missing extents if Data Vault parameters are absent.
5. The app opens live plot windows and listens for new rows.

Typical saved-data flow:

1. Choose `Plot Saved Data`.
2. Browse to an existing dataset.
3. Configure desired 1D or 2D plots.
4. The app reads the full dataset.
5. The user can inspect plots, take line cuts for 2D data, add notes, and export `.mat` data or report assets.

## Main Functional Elements at a Glance

- `dvPlotter`: main application window and top-level workflow controller.
- `plotSetup`: plot-selection and axis-operation setup dialog.
- `extentPrompt`: manual range/point-count entry when metadata is missing.
- `plot2DWindow`: live 2D image plot.
- `plot1DWindow`: live 1D trace plot.
- `plotSaved2DWindow`: saved 2D image plot with line cuts and export controls.
- `plotSaved1DWindow`: saved 1D line plot with export controls.
- `dirExplorer`: Data Vault directory selector for listener mode.
- `dataVaultExplorer`: Data Vault dataset selector for live or saved plotting.
- `noteEditor`, `textEditor`, `LineNumberArea`: plot-note editing support.
- `add_custom_gradients`: adds extra pyqtgraph color gradients.

## Observations for Future Maintenance

- The code is functionally organized by window class, but much of the data-processing logic is duplicated between live/saved and 1D/2D paths.
- Several `except:` blocks suppress errors and only print debug messages, which can make failures hard to diagnose during measurements.
- Some code appears to be Python 2/PyQt4-era or transition-era code, especially `sys.exc_traceback`, `QtGui.QPushButton`, old signal syntax, and commented WebKit PDF printing.
- PDF generation appears incomplete in PyQt5 because the actual `print_pdf()` implementation is commented out.
- The main file comments out `dvPlotterResources_rc`, but stylesheet image URLs depend on Qt resources.
- `dataVaultLivePlotter.py` is the actual main file present in the repository; if external docs or launch scripts refer to `dataVaultPlotter.py`, they may need to be updated or an alias file may be needed.
