from PyQt4 import QtGui, QtCore
import sys
import pyqtgraph as pg

class plot2DWindow(QtGui.QWidget):
    def __init__(self, parent = None):
        super(plot2DWindow, self).__init__(parent)
        
        self.layout = QtGui.QGridLayout(self)
        
        self.viewBig = pg.PlotItem(name = "Plot", title = 'Testy Stretchy')
        self.mainPlot = pg.ImageView(view = self.viewBig)
        
        self.layout.addWidget(self.mainPlot, *(0,0))
        self.setLayout(self.layout)
        
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
        self.setPalette(p)
        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = plot2DWindow()
    window.resize(250,150)
    window.move(300,300)
    window.show()
    
    sys.exit(app.exec_())