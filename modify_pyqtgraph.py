import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

def add_custom_gradients():
    """Add custom gradients to PyQtGraph."""
    # Define the custom red-blue gradient
    pos = np.array([0.0, 1.0])  # Positions of colors
    color = np.array([
        [255, 0, 0, 255],  # Red
        [0, 0, 255, 255]   # Blue
    ], dtype=np.ubyte)  # Colors corresponding to positions

    # Add the custom color map to the Gradient Editor
    Gradients['red_blue'] = {'ticks': [(0.0, (255, 0, 0, 255)), (1.0, (0, 0, 255, 255))], 'mode': 'rgb'}

def main():
    # Add custom gradients
    add_custom_gradients()

    # Create the application instance
    app = QtWidgets.QApplication([])

    # Create the ImageView widget
    view = pg.ImageView()

    # Create some example data
    image = np.random.normal(size=(100, 100))

    # Create the custom color map
    pos = np.array([0.0, 1.0])  # Positions of colors
    color = np.array([
        [255, 0, 0, 255],  # Red
        [0, 0, 255, 255]   # Blue
    ], dtype=np.ubyte)  # Colors corresponding to positions
    custom_map = pg.ColorMap(pos, color)

    # Set the lookup table for the ImageItem
    view.getImageItem().setLookupTable(custom_map.getLookupTable(256, alpha=False))

    # Display the image with the custom red-blue color map
    view.setImage(image)

    # Show the ImageView widget
    view.show()

    # Start the Qt event loop
    app.exec_()

if __name__ == '__main__':
    main()
    print(Gradients)