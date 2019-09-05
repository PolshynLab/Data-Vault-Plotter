from __future__ import division
import sys
import os
import os.path
from pathlib import Path
import twisted
from PyQt5 import QtCore, QtGui, QtTest, uic, QtWidgets, QtPrintSupport
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QApplication
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWebEngineWidgets import QWebEngineView
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
#import exceptions
import time
import copy
import datetime as dt
import scipy.io as sio
import scipy.stats as spst
try:
    from jinja2 import Environment, PackageLoader
except:
    print("--------------jinja2 not installed... Create PDF function disabled--------------")
try:
    from PyPDF2 import PdfFileMerger, PdfFileReader
except:
    print("--------------PyPDF2 not installed... Merge PDF function disabled--------------")


path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(path, 'Resources'))
import dvPlotterResources_rc

mainWinGUI = os.path.join(path, 'startPlotter.ui')
plotExtentGUI = os.path.join(path, 'extentPrompt.ui')
dvExplorerGUI = os.path.join(path, 'dvExplorer.ui')
dirExplorerGUI = os.path.join(path, 'dirExplorer.ui')
editInfoGUI = os.path.join(path, 'editDatasetInfo.ui')
plotSetupUI = os.path.join(path, 'plotSetup.ui')
helpWindowUI = os.path.join(path, 'helpWindow.ui')

guiIconPath = os.path.join(path, 'hex.svg')

Ui_MainWin, QtBaseClass = uic.loadUiType(mainWinGUI)
Ui_ExtPrompt, QtBaseClass = uic.loadUiType(plotExtentGUI)
Ui_DataVaultExp, QtBaseClass = uic.loadUiType(dvExplorerGUI)
Ui_DirExp, QtBaseClass = uic.loadUiType(dirExplorerGUI)
Ui_EditDataInfo, QtBaseClass = uic.loadUiType(editInfoGUI)
Ui_PlotSetup, QtBaseClass = uic.loadUiType(plotSetupUI)
Ui_HelpWindow, QtBaseClass = uic.loadUiType(helpWindowUI)

ID_NEWDATA = 999

    
class dvPlotter(QtGui.QMainWindow, Ui_MainWin):
    def __init__(self, reactor, parent = None):
        super(dvPlotter, self).__init__(parent)
        QtGui.QMainWindow.__init__(self)
        
        self.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(guiIconPath))
        self.setWindowIcon(icon)
        self.reactor = reactor
        
        self.moveDefault()
        self.initReact(self.reactor)
        
        self.plotSavedBtn.clicked.connect(self.plotSavedDataFunc)
        self.listen.clicked.connect(self.setupListener)
        self.closeWin.clicked.connect(self.closePlotter)
        self.plotLive.clicked.connect(self.plotLiveData)
        
        self.helpBtn.clicked.connect(self.openHelpWindow)
        
        self.changeDir.setEnabled(False)
        self.plotLive.setEnabled(False)
        
        self.plotSavedBtn.setEnabled(True)
        
        self.listStatus = False
        
        self.allowPlot = False
        
        self.savePlotList = []
        self.existing2DPlotDict = {}
        self.existing1DPlotDict = {}
        
        self.listenTo = ['']
        
    def moveDefault(self):
        self.move(25,25)
        
    def openHelpWindow(self):
        self.helpWindowDlg = helpTextWindow(self)
        self.helpWindowDlg.show()
        self.helpBtn.setEnabled(False)
        
    @inlineCallbacks
    def initReact(self, c):
        from labrad.wrappers import connectAsync
        try:
            self.cxn = yield connectAsync(name = 'dvPlotter')
            self.dv = yield self.cxn.data_vault

        except:
            print("Either no LabRad connection or DataVault connection.")
        
    @inlineCallbacks
    def initListener(self, c):
        if self.listStatus == False:
            self.listen.clicked.disconnect()
            self.changeDir.clicked.connect(self.setupListener)
        
        try:
            yield self.dv.signal__new_dataset(1)
            yield self.dv.addListener(listener=self.open_dataset, source=None, ID=1)
            yield self.dv.cd(self.listenTo)
            self.plotLive.setEnabled(True)
            self.listen.setText('Listening!')
            self.changeDir.setEnabled(True)
            self.listStatus = True
            
            reg = "QPushButton#listen"
            press = "QPushButton:pressed#listen"
            regStr = reg + "{color: rgb(10,200,30);background-color:rgb(0,0,0);border: 2px solid rgb(10,200,30);border-radius: 5px}"
            pressStr = press + "{color: rgb(0,0,0); background-color:rgb(10,200,30);border: 2px solid rgb(10,200,30);border-radius: 5px}" 
            style = regStr + " " + pressStr
            self.listen.setStyleSheet(style)    
            
            reg = "QPushButton#changeDir"
            press = "QPushButton:pressed#changeDir"
            regStr = reg + "{color: rgb(200,60,0);background-color:rgb(0,0,0);border: 2px solid rgb(200,60,0);border-radius: 5px}"
            pressStr = press + "{color: rgb(0,0,0); background-color:rgb(200,60,0);border: 2px solid rgb(200,60,0);border-radius: 5px}" 
            style = regStr + " " + pressStr
            self.changeDir.setStyleSheet(style)
        except:
            print("Either no LabRad connection or DataVault connection.")

    @inlineCallbacks
    def update(self, c):
        yield self.sleep(0.5)
        
    def renumPlotDicts(self, dim):
        if dim == 1:
            ii = 0
            for plt in self.existing1DPlotDict:
                windowName = '1DPlot_' + str(ii)
                self.existing1DPlotDict[windowName] = self.existing1DPlotDict[plt]
                ii += 1
        elif dim == 2:
            ii = 0
            for plt in self.existing2DPlotDict:
                windowName = '2DPlot_' + str(ii)
                self.existing2DPlotDict[windowName] = self.existing2DPlotDict[plt]
                ii += 1
            
        
    @inlineCallbacks
    def open_dataset(self, c, signal):
        print("signal: ", signal)
        self.listenPlotFile =  signal
        yield self.dv.open(str(self.listenPlotFile))
        yield self.sleep(0.5)
        params = yield self.dv.get_parameters()
        vars = yield self.dv.variables()
        if params != None:
            params = dict((x,y) for x,y in params)  
            parKeys = params.keys()
            if 'live_plots' in parKeys:
                self.initLivePlotting(params, vars)
            else:
                pass
        else:
            pass
            
    @inlineCallbacks
    def initLivePlotting(self, params, vars, c = None):
        plot1DDict, plot2DDict = {}, {}
        missingInfo = False
        toPlot = params['live_plots']
        indVars, depVars = [x[0] for x in vars[0]], [x[0] for x in vars[1]]
        for plot in toPlot:
            if len(plot) == 2:
                try:
                    title = str(plot[1]) + ' vs. ' + str(plot[0])
                    x_axis, y_axis = str(plot[0]), str(plot[1])
                    if (x_axis in indVars): 
                        x_index, y_index = indVars.index(x_axis), depVars.index(y_axis)+len(indVars)
                    else:
                        x_index, y_index = depVars.index(x_axis)+len(indVars), depVars.index(y_axis)+len(indVars)
                    x_rng = params[x_axis + '_rng']
                    x_pnts = params[x_axis + '_pnts']
                    plot1DDict[title] = {'title' : title, 'x axis' : x_axis, 'y axis' : y_axis, 'x index' : x_index, 'y index' : y_index, 'x range' : x_rng, 'x points' : x_pnts}
                    
                except:
                    print("Missing info on plot: ", plot)
                    missingInfo = True
            elif len(plot) == 3:
                try:
                    title = str(plot[2]) + ' vs. ' + str(plot[0]) + ' and ' + str(plot[1])
                    x_axis, y_axis, z_axis = str(plot[0]), str(plot[1]), str(plot[2])
                    if (x_axis in indVars): 
                        x_index = indVars.index(x_axis)
                    else:
                        x_index = depVars.index(x_axis)+len(indVars)
                    if (y_axis in indVars): 
                        y_index = indVars.index(y_axis)
                    else:
                        y_index = depVars.index(y_axis)+len(indVars)
                    z_index = depVars.index(z_axis)+len(indVars)
                    x_rng = params[x_axis + '_rng']
                    x_pnts = params[x_axis + '_pnts']
                    y_rng = params[y_axis + '_rng']
                    y_pnts = params[y_axis + '_pnts']
                    plot2DDict[title] = {'title' : title, 'x axis' : x_axis, 'y axis' : y_axis, 'z axis' : z_axis, 'x index' : x_index, 'y index' : y_index, 'z index' : z_index , 'x range' : x_rng, 'x points' : x_pnts, 'y range' : y_rng, 'y points' : y_pnts}
                except:
                    print("Missing info on plot: ", plot)
                    missingInfo = True
            else:
                pass
        if missingInfo == False:
            yield self.openLivePlots(plot2DDict, plot1DDict, 0, self.reactor)
            yield self.sleep(0.5)

        else:
            print("Missing plot info...")

    
    def update_params(self):
        pass
        
    def setListenDir(self, dir, list):
        self.listenDir.setText(str(dir))
        self.listenDir.setStyleSheet("QLabel#listenDir {color: rgb(131,131,131);}")
        self.listenTo = list
        
    @inlineCallbacks
    def openLivePlots(self, twoPlots, onePlots, fresh, c = None):
        if fresh == 0:
            i1, i2 = 0, 0
            #close extra plot windows
            try:
                if len(twoPlots) < len(self.existing2DPlotDict):
                    for jj in range(len(twoPlots), len(self.existing2DPlotDict)):
                        windowName = '2DPlot_' + str(jj)
                        windowObj = getattr(self, windowName)
                        windowObj.cxn.disconnect()
                        windowObj.close()

                if len(onePlots) < len(self.existing1DPlotDict):
                    for jj in range(len(onePlots), len(self.existing1DPlotDict)):
                        windowName = '1DPlot_' + str(jj)
                        windowObj = getattr(self, windowName)
                        windowObj.cxn.disconnect()
                        windowObj.close()

            except Exception as inst:
                print("Following error was thrown: ")
                print(str(inst))
                print("Error thrown on line: ")
                print(sys.exc_info()[2])
            plt1, plt2 = len(self.existing1DPlotDict), len(self.existing2DPlotDict)
            
            try: 
                x0, y0 = 450, 25
                for plot in twoPlots:
                    new2DPlotName = '2DPlot_' + str(i2)                     
                    if i2 < plt2:           
                        windowObj = getattr(self, new2DPlotName)
                        windowObj.restartPlotting(twoPlots[plot], self.listenTo, self.listenPlotFile)
                    else:
                        setattr(self, new2DPlotName, plot2DWindow(self.reactor, twoPlots[plot], self.listenTo, self.listenPlotFile, x0, y0, fresh, new2DPlotName, self))
                        windowObj = getattr(self, new2DPlotName)
                        windowObj.show()
                        self.existing2DPlotDict[new2DPlotName] = windowObj
                        yield self.sleep(1)
                        y0 += 50
                    i2 += 1
                    yield self.sleep(1)
                x0, y0 = 1250, 25
                for plot in onePlots:
                    new1DPlotName = '1DPlot_' + str(i1) 
                    if i1 < plt1:
                        windowObj = getattr(self, new1DPlotName)
                        windowObj.restartPlotting(onePlots[plot], self.listenTo, self.listenPlotFile)
                    else:
                        setattr(self, new1DPlotName, plot1DWindow(self.reactor, onePlots[plot], self.listenTo, self.listenPlotFile, x0, y0, fresh, new1DPlotName, self))
                        windowObj = getattr(self, new1DPlotName)
                        windowObj.show()
                        self.existing1DPlotDict[new1DPlotName] = windowObj
                        yield self.sleep(1)
                        y0 += 50                        
                    i1 += 1
                    yield self.sleep(1)
            except Exception as inst:
                print("Following error was thrown: ")
                print(str(inst))
                print("Error thrown on line: ")
                print(sys.exc_info()[2])
        elif fresh == 1:
            try: 
                x0, y0 = 450, 25
                for plot in twoPlots:
                    num2Plots = len(self.existing2DPlotDict)
                    new2DPlotName = '2DPlot_' + str(num2Plots)  
                    setattr(self, new2DPlotName,  plot2DWindow(self.reactor, twoPlots[plot], self.listenTo, self.listenPlotFile, x0, y0, fresh, new2DPlotName, self))
                    windowObj = getattr(self, new2DPlotName)
                    windowObj.show()
                    self.existing2DPlotDict[new2DPlotName] = windowObj
                    yield self.sleep(1)
                    y0 += 50
                x0, y0 = 1250, 25
                for plot in onePlots:
                    num1Plots = len(self.existing1DPlotDict)
                    new1DPlotName = '1DPlot_' + str(num2Plots)  
                    setattr(self, new1DPlotName, plot1DWindow(self.reactor, onePlots[plot], self.listenTo, self.listenPlotFile, x0, y0, fresh, new1DPlotName, self))
                    windowObj = getattr(self, new1DPlotName)
                    windowObj.show()
                    self.existing1DPlotDict[new1DPlotName] = windowObj
                    yield self.sleep(1)
                    y0 += 50
            except Exception as inst:
                print("Following error was thrown: ")
                print(str(inst))
                print("Error thrown on line: ")
                print(sys.exc_info()[2])
        
        self.allowPlot = True
            
    def openSavedPlots(self, file, dir, allPlots, dim):
        color0 = 0
        x0, y0 = 450, 25
        if dim == 2:
            for plot in allPlots:
                try:
                    thing = plotSaved2DWindow(self.reactor, file, dir, allPlots[plot], y0)
                    thing.show()
                    self.savePlotList.append(thing)
                    y0 += 50
                except Exception as inst:
                    print("Following error was thrown: ")
                    print(str(inst))
                    print("Error thrown on line: ")
                    print(sys.exc_info()[2]) 
        elif dim == 1:
            for plot in allPlots:
                try:
                    thing = plotSaved1DWindow(self.reactor, file, dir, allPlots[plot], y0, color0)
                    thing.show()
                    self.savePlotList.append(thing)
                    y0 += 50
                    color0 += 1
                except Exception as inst:
                    print("Following error was thrown: ")
                    print(str(inst))
                    print("Error thrown on line: ")
                    print(sys.exc_info()[2])                      

    def plotLiveData(self):
        self.dvExplorer = dataVaultExplorer(self.reactor, 'live', self.listenTo, self)
        self.dvExplorer.show()
        
    def setupListener(self):
        self.listen.setEnabled(False)
        self.changeDir.setEnabled(False)
        drcExplorer = dirExplorer(self.reactor, self.listStatus, self)
        drcExplorer.show()
        
    def plotSavedDataFunc(self):
        self.dvExplorer = dataVaultExplorer(self.reactor, 'saved', self.listenTo, self)
        self.dvExplorer.show()
        
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
    def closePlotter(self):
        self.reactor.stop()
        self.cxn.disconnect()
        self.close()

    def closeEvent(self, e):
        self.reactor.stop()
        self.cxn.disconnect()
        print("Reactor shut down.")
        
    def sleep(self, secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class extentPrompt(QtGui.QDialog, Ui_ExtPrompt):
    def __init__(self, reactor, plotInfo, x0, y0, parent = None):
        super(extentPrompt, self).__init__(parent)
        QtGui.QDialog.__init__(self)
        
        self.reactor = reactor
        self.plotInfo = plotInfo
        self.mainWin = parent
        self.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(guiIconPath))
        self.setWindowIcon(icon)
        
        self.x0, self.y0 = x0, y0
        self.moveDefault()
        
        self.setupTable()
        
        self.ok.clicked.connect(self.checkExt)
    
    def editExt(self, r, c):
        self.extTable.item(r, c).setText('')
        self.extTable.editItem(self.extTable.item(r, c))
        
    def setupTable(self):
        self.extTable.horizontalHeader().hide()
        self.extTable.verticalHeader().hide()
        self.extTable.cellDoubleClicked.connect(self.editExt)

        self.extTable.setColumnCount(4)
        self.extTable.setRowCount(len(self.plotInfo) + 1)

        min, max, pts = QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), 
        
        headers = [min, max, pts]
        
        min.setText('Minimum Value')        
        min.setForeground(QBrush(QColor(131,131,131)))
        max.setText('Maximum Value')
        max.setForeground(QBrush(QColor(131,131,131)))
        pts.setText('Number of Points')
        pts.setForeground(QBrush(QColor(131,131,131)))

        for ii in range(0, 3):
            self.extTable.setItem(0, ii+1, headers[ii])
            self.extTable.item(0, ii+1).setFont(QtGui.QFont("MS Shell Dlg 2",weight=QtGui.QFont.Bold))
            self.extTable.item(0, ii+1).setFlags(QtCore.Qt.NoItemFlags)

        self.extTable.setColumnWidth(0, 100)
        self.extTable.setColumnWidth(1, 125)
        self.extTable.setColumnWidth(2, 125)
        self.extTable.setColumnWidth(3, 125)
        
        for ii in range(0, len(self.plotInfo)):
            item = QtGui.QTableWidgetItem()
            item.setText(self.plotInfo[ii])
            item.setFont(QtGui.QFont("MS Shell Dlg 2",weight=QtGui.QFont.Bold))
            self.extTable.setItem(ii+1, 0, item)
            self.extTable.item(ii+1, 0).setFlags(QtCore.Qt.NoItemFlags)
        for r in range(1, len(self.plotInfo) + 1):
            for c in range(1, 4):
                item = QtGui.QTableWidgetItem()
                self.extTable.setItem(r, c, item)
                self.extTable.item(r, c).setBackgroundColor(QtGui.QColor(255,255,255))

    def moveDefault(self):
        self.move(self.x0, self.y0)
        
    def checkExt(self):
        extents , pxsize = {}, {}
        errCell = []
        
        for r in range(1, len(self.plotInfo) + 1):
            for c in range(1, 4):
                self.extTable.item(r, c).setBackgroundColor(QtGui.QColor(255,255,255))
        
        for r in range(1, self.extTable.rowCount()):
            try:
                extents[str(self.extTable.item(r, 0).text())] = [float(self.extTable.item(r, 1).text()), float(self.extTable.item(r, 2).text())]
                if float(self.extTable.item(r, 1).text()) == float(self.extTable.item(r, 2).text()):
                    errCell.append([r,1])
                    errCell.append([r,2])
            except:
                errCell.append([r,1])
                errCell.append([r,2])

            try:
                pxsize[str(self.extTable.item(r, 0).text())] = int(self.extTable.item(r, 3).text())
                if int(self.extTable.item(r, 3).text()) == 0:
                    errCell.append([r,3])
            except:
                errCell.append([r,3])

        if len(errCell) == 0:
            self.mainWin.extents = extents
            self.mainWin.pxsize = pxsize
            self.accept()
        else:
            for ii in range(0, len(errCell)):
                self.extTable.item(errCell[ii][0], errCell[ii][1]).setBackgroundColor(QtGui.QColor(250,190,160))
                
    def closeEvent(self, e):
        self.reject()

class plot2DWindow(QtGui.QDialog):
    def __init__(self, reactor, plotInfo, dir, file, x0, y0, fresh, windowID, parent = None):
        super(plot2DWindow, self).__init__(parent)
        self.plotInfo = plotInfo
        self.reactor = reactor
        self.plotWinID = windowID
        self.mainWin = parent
        self.pX, self.pY = x0, y0
            
        self.dir = dir
        self.fileName = file
        self.resize(850,763)
        self.move(self.pX,self.pY)
        #fresh specifies if the dataset to be plotted already has data (1) or is empty (0)
        self.fresh = fresh
        self.connect(QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL+ QtCore.Qt.Key_C), self), QtCore.SIGNAL('activated()'),self.copyPlotToClip)
        self.autoLevelMainplot = True
        self.cxnName = None
        self.definePlotParams()
    
    def definePlotParams(self, state = None):
        self.xIndex = self.plotInfo['x index']
        self.yIndex = self.plotInfo['y index']
        self.zIndex = self.plotInfo['z index']
        
        self.extents = [self.plotInfo['x range'][0], self.plotInfo['x range'][1], self.plotInfo['y range'][0], self.plotInfo['y range'][1]]
        self.pxsize = [self.plotInfo['x points'], self.plotInfo['y points']]
        self.plotTitle = self.plotInfo['title']
        if self.plotTitle[0:5] == 'Plot ':
            self.plotTitle = str(self.fileName) + ': ' + self.plotInfo['z axis'] + ' vs. ' + self.plotInfo['x axis'] + ' and ' + self.plotInfo['y axis']

        else:
            self.plotTitle = str(self.fileName) + ': ' + self.plotTitle
        self.setWindowTitle(self.plotTitle)
        self.Data = np.array([])
        
        self.setupPlot(state)
        self.setupListener(self.reactor)
        self.isData = False 
        
    def restartPlotting(self, newPlotInfo, listenDir, listenFile):
        self.plotInfo = newPlotInfo
        self.dir = listenDir
        self.fileName = listenFile  
        self.definePlotParams(0)
                        
    def copyPlotToClip(self):
        r = self.mainPlot.ui.histogram.region.getRegion()
        self.mainPlot.ui.histogram.vb.setYRange(*r)
        #create ImageExpoerters:
        mainExp = pg.exporters.ImageExporter(self.viewBig)
        colorAxisExp = pg.exporters.ImageExporter(self.mainPlot.ui.histogram.axis)
        colorBarExp = pg.exporters.ImageExporter(self.mainPlot.ui.histogram.gradient)
        #create QImages:
        main =mainExp.export(toBytes=True)
        colorAxis =colorAxisExp.export(toBytes=True)
        colorBar = colorBarExp.export(toBytes=True)
        #define teh size:
        x = main.width() + colorAxis.width() + colorBar.width()
        y = main.height()
        #to get everything in the same height:
        yOffs = [0,0.5*(y-colorAxis.height()),0.5*(y-colorBar.height())]
        result = QtGui.QImage(x, y ,QtGui.QImage.Format_RGB32)
        painter = QtGui.QPainter(result)
        posX = 0
        for img,y in zip((main,colorAxis,colorBar),yOffs):
                #draw every part in different positions:
                painter.drawImage(posX, y, img)
                posX += img.width()
        painter.end()
        #save to file
        QApplication.clipboard().setImage(result)
        
    @inlineCallbacks
    def setupListener(self, c):
        try: 
            if self.cxnName == None:
                self.cxnName = 'plot' + str(self.id)
                from labrad.wrappers import connectAsync
                self.cxn = yield connectAsync(name = self.cxnName)
                self.dv = yield self.cxn.data_vault
            yield self.dv.cd(self.dir)
            yield self.dv.open(self.fileName)
            yield self.addListen(self.reactor)
            newData = yield self.dv.get()

            if len(newData) == 0 or len(newData[0]) == 0:
                pass
            else:
                inx = np.delete(np.arange(0, len(newData[0])), [self.xIndex, self.yIndex, self.zIndex])
                newData = np.delete(np.asarray(newData), inx, axis = 1)
                x_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.xIndex)[0][0]
                y_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.yIndex)[0][0]
                z_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.zIndex)[0][0]
                newData[::, x_ind] = np.digitize(newData[::, x_ind], self.xBins) - 1
                newData[::, y_ind] = np.digitize(newData[::, y_ind], self.yBins) - 1

                for pt in newData:
                    self.plotData[int(pt[x_ind]), int(pt[y_ind])] = pt[z_ind]

                r0 = np.where(np.all(self.plotData == self.randFill, axis = 0))[0]
                c0 = np.where(np.all(self.plotData == self.randFill, axis = 1))[0]
                self.tmp = np.delete(np.delete(self.plotData, r0, axis = 1), c0, axis = 0)
                argX = np.min([self.extents[0],self.extents[1]]) + self.xscale * np.max(np.append(c0, -1) + 1)
                argY = np.min([self.extents[2],self.extents[3]]) + self.yscale * np.max(np.append(r0, -1) + 1)
                self.mainPlot.setImage(self.tmp, autoRange = False ,     autoLevels = False, pos=[argX, argY],scale=[self.xscale, self.yscale])
                if self.autoLevelMainplot:
                    self.mainPlot.autoLevels()


                self.isData = True
            
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2]) 
    @inlineCallbacks
    def addListen(self, c):
        yield self.dv.signal__data_available(self.id)
        yield self.dv.addListener(listener=self.updatePlot, ID=self.id)
        
    def setupPlot(self, state = None):
        global ID_NEWDATA
        self.id = ID_NEWDATA
        ID_NEWDATA = ID_NEWDATA + 1

        if state is None:
            p = self.palette()
            p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
            self.setPalette(p)
            
            self.noCutWidget = QtGui.QWidget()
            self.vCutWidget = QtGui.QWidget()
            self.hCutWidget = QtGui.QWidget()
            self.vhCutWidget = QtGui.QWidget()
        self.defPlots(state)
        
        if state is None:
            self.layoutList = [self.layout, self.vLayout, self.hLayout, self.vhLayout]
            self.stackLayout = QtGui.QStackedWidget(self)
            
            self.plotTitleLbl = QtGui.QLabel()
            self.selectLbl = QtGui.QLabel()
            self.posLbl = QtGui.QLabel()
            self.autoHistChk = QtGui.QCheckBox()
            self.autoHistLbl = QtGui.QLabel()
            self.lineCutBox = QtGui.QComboBox()
            self.posBox = QtGui.QDoubleSpinBox()
            
            self.autoHistChk.setCheckState(2)
            self.autoHistChk.stateChanged.connect(self.autoHistFunc)

            
            self.plotTitleLbl.setText(self.plotTitle)
            self.plotTitleLbl.setObjectName('plotTitleLbl')
            self.plotTitleLbl.setStyleSheet("QLabel#plotTitleLbl {background-color: 'black'; color: rgb(131,131,131); font: 11pt;}")

            self.autoHistLbl.setText('Autorange Histogram')
            self.autoHistLbl.setObjectName('autoHistLbl')
            self.autoHistLbl.setStyleSheet("QLabel#autoHistLbl {background-color: 'black'; color: rgb(131,131,131); font: 9pt;}")           
            
            self.selectLbl.setText('Select Line Cut')
            self.selectLbl.setObjectName('selectLbl')
            self.selectLbl.setStyleSheet("QLabel#selectLbl {background-color: 'black'; color: rgb(131,131,131); font: 9pt;}")
            
            self.lineCutBox.setObjectName('lineCutBox')
            self.lineCutBox.setStyleSheet("QComboBox#lineCutBox{width: 20px; color: rgb(131,131,131); background-color: 'balck';    border: 2px solid rgb(131,131,131); border-radius: 5px;}")
            self.lineCutBox.insertItem(0, 'None')
            self.lineCutBox.insertItem(1, 'Vertical')
            self.lineCutBox.insertItem(2, 'Horizontal')
            self.lineCutBox.insertItem(3, 'Both')

            self.lineCutBox.currentIndexChanged.connect(self.setIndex)
            self.lineCutBox.setMinimumWidth(85)
        
            self.stackLayout.addWidget(self.noCutWidget)
            self.stackLayout.addWidget(self.vCutWidget)
            self.stackLayout.addWidget(self.hCutWidget)
            self.stackLayout.addWidget(self.vhCutWidget)
            
            self.mainLayout = QtGui.QGridLayout(self)
            self.mainLayout.addWidget(self.stackLayout, *(1,0, 1, 6))
            self.mainLayout.addWidget(self.plotTitleLbl, *(0,0))
            self.mainLayout.addWidget(self.autoHistLbl, *(0,2))
            self.mainLayout.addWidget(self.autoHistChk, *(0,3), alignment = QtCore.Qt.AlignLeft)
            self.mainLayout.addWidget(self.selectLbl, *(0,4), alignment = QtCore.Qt.AlignRight)
            self.mainLayout.addWidget(self.lineCutBox, *(0,5), alignment = QtCore.Qt.AlignLeft)
            self.setLayout(self.mainLayout)
            self.startIndex = 0
            self.stackLayout.setCurrentIndex(0)
        else:
            self.plotTitleLbl.setText(self.plotTitle)
            self.plotTitleLbl.setStyleSheet("QLabel#plotTitleLbl {background-color: 'black'; color: rgb(131,131,131); font: 11pt;}")

    
    def autoHistFunc(self, state):
        try:
            
            if state == 0:
                self.autoLevelMainplot = False

            elif state == 2:
                self.autoLevelMainplot = True


        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2])
    
    def toggleTraceFunc(self):
        jj = self.i % 2
        self.stackLayout.setCurrentIndex(jj)
        if jj % 2 == 0:
            self.layout2.removeWidget(self.mainPlot)
            self.layout1.addWidget(self.mainPlot, *(0,0))
        else:
            self.layout1.removeWidget(self.mainPlot)
            self.layout2.addWidget(self.mainPlot, *(0,0))
        self.i += 1
    
    def testHist(self, autoLevel=False, autoRange=False):
        histTmp = self.tmp - self.randFill
        w = np.absolute(np.divide(histTmp, histTmp, out = np.zeros_like(histTmp), where = histTmp != 0))
        step = (int(np.ceil(w.shape[0] / 200)),
                    int(np.ceil(w.shape[1] / 200)))
        if np.isscalar(step):
            step = (step, step)
        stepW = w[::step[0], ::step[1]]
        stepW = stepW[np.isfinite(stepW)]
        h = self.mainImage.getHistogram(weights = stepW)
        if h[0] is None:
            return
        self.mainPlot.ui.histogram.plot.setData(*h)
        if autoLevel:
            mn = h[0][0]
            mx = h[0][-1]
            self.mainPlot.ui.histogram.region.setRegion([mn, mx])

    
    def defPlots(self, state = None):
        if state is None:
            self.vTraceLine = pg.InfiniteLine(pos = self.extents[0], angle = 90, movable = True)
            self.hTraceLine = pg.InfiniteLine(pos = self.extents[2], angle = 0, movable = True)
            self.vTraceLine.sigPositionChangeFinished.connect(self.updateVCutPlot)
            self.hTraceLine.sigPositionChangeFinished.connect(self.updateHCutPlot)
            self.viewBig = pg.PlotItem(name = "Plot")
            self.viewBig.showAxis('top', show = True)
            self.viewBig.showAxis('right', show = True)
            self.viewBig.setLabel('left', self.plotInfo['y axis'])
            self.viewBig.setLabel('bottom', self.plotInfo['x axis'])
            self.viewBig.setAspectLocked(lock = False, ratio = 1)
            self.mainImage = pg.ImageItem()
            self.mainPlot = pg.ImageView(view = self.viewBig, imageItem = self.mainImage)
            self.mainImage.sigImageChanged.connect(self.testHist)
            self.mainPlot.ui.menuBtn.hide()
            self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
            self.mainPlot.ui.roiBtn.hide()
            self.mainPlot.ui.menuBtn.hide()
            self.viewBig.setXRange(np.min([self.extents[0],self.extents[1]]), np.max([self.extents[0],self.extents[1]]))
            self.viewBig.setYRange(np.min([self.extents[2],self.extents[3]]), np.max([self.extents[2],self.extents[3]]))
            self.viewBig.setAspectLocked(False)
            self.viewBig.invertY(False)
        else:
            self.mainPlot.clear()
            self.viewBig.removeItem(self.rect)
    
        self.randFill = np.random.random() * 1e-3
        self.plotData = np.full([self.pxsize[0], self.pxsize[1]], self.randFill)
        self.rect = QtGui.QGraphicsRectItem(np.min([self.extents[0], self.extents[1]]), np.min([self.extents[2], self.extents[3]]), np.absolute(self.extents[1] - self.extents[0]), np.absolute(self.extents[3] - self.extents[2]))
        self.rect.setBrush(QtGui.QColor('transparent'))
        self.viewBig.addItem(self.rect)
        
        self.xscale, self.yscale = np.absolute((self.extents[1] - self.extents[0])/self.pxsize[0]), np.absolute((self.extents[3] - self.extents[2])/self.pxsize[1])
        
        if self.extents[0] < self.extents[1]:
            self.xBins = np.linspace(self.extents[0] - 0.5 * self.xscale, self.extents[1] + 0.5 * self.xscale, self.pxsize[0]+1)
        else:
            self.xBins = np.linspace(self.extents[1] - 0.5 * self.xscale, self.extents[0] + 0.5 * self.xscale, self.pxsize[0]+1)
        
        if self.extents[2] < self.extents[3]:
            self.yBins = np.linspace(self.extents[2] - 0.5 * self.yscale, self.extents[3] + 0.5 * self.yscale, self.pxsize[1]+1)
        else:
            self.yBins = np.linspace(self.extents[3] - 0.5 * self.yscale, self.extents[2] + 0.5 * self.yscale, self.pxsize[1]+1)
        

        
        if state is None:
            self.plot1DV = pg.PlotWidget()
            self.plot1DV.showAxis('right', show = True)
            self.plot1DV.showAxis('top', show = True)
            
            self.plot1DH = pg.PlotWidget()
            self.plot1DH.showAxis('right', show = True)
            self.plot1DH.showAxis('top', show = True)   
        else:
            self.plot1DH.clear()
            self.plot1DV.clear()
        
        
        self.plot1DV.setLabel('left', self.plotInfo['y axis'])
        self.plot1DV.setLabel('bottom', self.plotInfo['z axis'])    


        self.plot1DH.setLabel('left', self.plotInfo['z axis'])
        self.plot1DH.setLabel('bottom', self.plotInfo['x axis'])    
        
        if state is None:
            self.setVHCutWidget()
            self.setHCutWidget()
            self.setVCutWidget()    
            self.setNoCutWidget()
        
    def updateHCutPlot(self):
        pos = self.hTraceLine.value()
        index = np.absolute(int(self.pxsize[1] * (pos - np.min([self.extents[2], self.extents[3]]))/(self.extents[3] - self.extents[2])))
        self.plot1DH.clear()
        if pos < np.max([self.extents[2], self.extents[3]]) and pos > np.min([self.extents[2], self.extents[3]]): 
            xVals = np.linspace(np.min([self.extents[0], self.extents[1]]), np.max([self.extents[0], self.extents[1]]), self.pxsize[0])
            yVals = self.plotData[::, index]
            self.plot1DH.plot(x = xVals, y = yVals, pen = 0.5)
        
        
    def updateVCutPlot(self):
        pos = self.vTraceLine.value()
        index = np.absolute(int(self.pxsize[0] * (pos - np.min([self.extents[0], self.extents[1]]))/(self.extents[1] - self.extents[0])))
        self.plot1DV.clear()
        if pos < np.max([self.extents[0], self.extents[1]]) and pos > np.min([self.extents[0], self.extents[1]]): 
            yVals = np.linspace(np.min([self.extents[2], self.extents[3]]), np.max([self.extents[2], self.extents[3]]), self.pxsize[1])
            xVals = self.plotData[index, ::]
            self.plot1DV.plot(x = xVals, y = yVals, pen = 0.5)
    
    def setNoCutWidget(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.mainPlot, *(0,0))
        self.noCutWidget.setLayout(self.layout)
        
        
    def setVCutWidget(self):
        self.vLayout = QtGui.QGridLayout()
        self.vLayout.addWidget(self.plot1DV, *(0, 0, 1, 1), alignment = QtCore.Qt.AlignVCenter)
        self.vLayout.addWidget(self.mainPlot,*(0, 1, 1, 1))
        self.vLayout.setColumnStretch(0,2)
        self.vLayout.setColumnStretch(1,5)
        self.vCutWidget.setLayout(self.vLayout)
        
    def setHCutWidget(self):
        self.hLayout = QtGui.QGridLayout()
        self.hLayout.addWidget(self.plot1DH, *(1, 0, 1, 7))
        self.hLayout.addWidget(self.mainPlot,*(0, 0, 1, 8))
        self.hLayout.setRowStretch(0,5)
        self.hLayout.setRowStretch(1,2)
        self.hCutWidget.setLayout(self.hLayout)
        
    def setVHCutWidget(self):
        self.vhLayout = QtGui.QGridLayout()
        self.vhLayout.addWidget(self.plot1DH, *(1, 1, 1, 1))
        self.vhLayout.addWidget(self.plot1DV, *(0, 0, 1, 1))
        self.vhLayout.addWidget(self.mainPlot,*(0, 1, 1, 2))
        self.vhLayout.setRowStretch(0,5)
        self.vhLayout.setRowStretch(1,2)
        self.vhLayout.setColumnStretch(0,6)
        self.vhLayout.setColumnStretch(1,14)
        self.vhLayout.setColumnStretch(2,2)
        self.vhCutWidget.setLayout(self.vhLayout)
        
        self.mainPlotPosList = [(0,0), (0,1, 1, 1), (0,0, 1, 8), (0,1,1,2)]

    def setIndex(self, jj):
        self.layoutList[self.startIndex].removeWidget(self.mainPlot)
        startHeight = self.height()
        startWidth = self.width()
        xPos, yPos =  self.x(), self.y()
        plotH, plotW = self.viewBig.height(), self.viewBig.width()
        if self.startIndex == 1:
            self.vLayout.removeWidget(self.plot1DV)
        elif self.startIndex == 2:
            self.hLayout.removeWidget(self.plot1DH)
        elif self.startIndex == 3:
            self.vhLayout.removeWidget(self.plot1DV)
            self.vhLayout.removeWidget(self.plot1DH)
        if jj == 1:
            self.vLayout.addWidget(self.plot1DV, *(0, 0, 1, 1))

            if self.startIndex == 0:
                self.viewBig.addItem(self.vTraceLine, ignoreBounds = True)
                self.resize(int(1.386 * startWidth), int(startHeight))
                
            elif self.startIndex == 2:
                self.viewBig.removeItem(self.hTraceLine)
                self.viewBig.addItem(self.vTraceLine, ignoreBounds = True)
                self.resize(int(1.385099* startWidth), int(0.730246*startHeight))
            elif self.startIndex == 3:
                self.viewBig.removeItem(self.hTraceLine)
                self.resize(int(1.0203 * startWidth), int(0.73105 * startWidth))        

        elif jj == 2:
            self.hLayout.addWidget(self.plot1DH, *(1, 0, 1, 7))
            if self.startIndex == 0:
                self.viewBig.addItem(self.hTraceLine, ignoreBounds = True)
                
                self.resize(startWidth, int(1.37776 * startHeight))
            elif self.startIndex == 1:
                self.viewBig.addItem(self.hTraceLine, ignoreBounds = True)
                self.viewBig.removeItem(self.vTraceLine)
                self.resize(int(0.72197*startWidth), int(1.3694*startHeight))
            elif self.startIndex == 3:
                self.viewBig.removeItem(self.vTraceLine)
                self.resize(int(0.73128 * startWidth), int(startHeight))        
        elif jj == 3:
            self.vhLayout.addWidget(self.plot1DV, *(0, 0, 1, 1))
            self.vhLayout.addWidget(self.plot1DH, *(1, 1, 1, 1))
            if self.startIndex == 0:
                self.viewBig.addItem(self.hTraceLine, ignoreBounds = True)
                self.viewBig.addItem(self.vTraceLine, ignoreBounds = True)
                self.resize(int(1.3498 *startWidth), int(1.3533*startHeight))
            elif self.startIndex == 1:
                self.viewBig.addItem(self.hTraceLine, ignoreBounds = True)
                self.resize(int(0.9801*startWidth), int(1.3679*startHeight))
            elif self.startIndex == 2:
                self.viewBig.addItem(self.vTraceLine, ignoreBounds = True)
                self.resize(int(1.36746*startWidth), int(startHeight))
        elif jj == 0:
            if self.startIndex == 1:
                self.viewBig.removeItem(self.vTraceLine)
                self.resize(int(0.7215*startWidth),int(startHeight))
            elif self.startIndex == 2:
                self.viewBig.removeItem(self.hTraceLine)
                self.resize(int(startWidth), int(0.72582 * startHeight))
            elif self.startIndex == 3:
                self.viewBig.removeItem(self.vTraceLine)
                self.viewBig.removeItem(self.hTraceLine)
                self.resize(int(0.74085 * startWidth), int(0.7389 * startHeight))
        self.layoutList[jj].addWidget(self.mainPlot, *self.mainPlotPosList[jj])
        self.stackLayout.setCurrentIndex(jj)
        self.startIndex = jj
        

        
            
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        

    
    @inlineCallbacks    
    def updatePlot(self, c, signal):

        try: 
            newData = yield self.dv.get()
            if len(newData) != 0:
                inx = np.delete(np.arange(0, len(newData[0])), [self.xIndex, self.yIndex, self.zIndex])
                newData = np.delete(np.asarray(newData), inx, axis = 1)
                
                x_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.xIndex)[0][0]
                y_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.yIndex)[0][0]
                z_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.zIndex)[0][0]

                newData[::, x_ind] = np.digitize(newData[::, x_ind], self.xBins)-1
                newData[::, y_ind] = np.digitize(newData[::, y_ind], self.yBins)-1
                yield self.plotMore(newData, x_ind, y_ind, z_ind, self.reactor)
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2]) 
    @inlineCallbacks
    def plotMore(self, newData, x_ind, y_ind, z_ind, c):
        yield self.sleep(0.1)

        for pt in newData:
                self.plotData[int(pt[x_ind]), int(pt[y_ind])] = pt[z_ind]

        r0 = np.where(np.all(self.plotData == self.randFill, axis = 0))[0]
        c0 = np.where(np.all(self.plotData == self.randFill, axis = 1))[0]
        self.tmp = np.delete(np.delete(self.plotData, r0, axis = 1), c0, axis = 0)
        argX = np.min([self.extents[0],self.extents[1]]) + self.xscale * np.max(np.append(c0, -1) + 1)
        argY = np.min([self.extents[2],self.extents[3]]) + self.yscale * np.max(np.append(r0, -1) + 1)
        self.mainPlot.setImage(self.tmp, autoRange = False , autoLevels = False, pos=[argX, argY],scale=[self.xscale, self.yscale])
        if self.autoLevelMainplot:
            self.mainPlot.autoLevels()
        pctComplete = int(100 * (self.tmp.shape[0] * self.tmp.shape[1]) / (self.plotData.shape[0] * self.plotData.shape[1]))
        self.setWindowTitle(self.plotTitle + ' (' + str(pctComplete) + '% Complete)')
        

    def closeEvent(self, e):
        self.mainWin.existing2DPlotDict.pop(self.plotWinID)
        self.mainWin.renumPlotDicts(2)
        self.cxn.disconnect()
        self.close()

class plot1DWindow(QtGui.QDialog):
    def __init__(self, reactor, plotInfo, dir, file, x0, y0, fresh, windowID, parent = None):
        super(plot1DWindow, self).__init__(parent)

        self.reactor = reactor
        self.mainWin = parent
        self.dir = dir
        self.fileName = file
        self.plotInfo = plotInfo
        self.plotWinID = windowID
        self.fresh = fresh
        self.cxnName = None
        
        self.pX, self.pY = x0, y0
        self.resize(600,320)
        self.move(self.pX,self.pY)
        
        self.definePlotParams()
        
        
    def definePlotParams(self, state = None):
        self.isData = False
        self.traceCnt = 0
        self.numLines = 0
        self.Data = np.array([])
        self.plotTitle = self.plotInfo['title']
        if self.plotTitle[0:5] == 'Plot ':
            self.plotTitle = str(self.fileName) + ': ' + self.plotInfo['y axis'] + ' vs. ' + self.plotInfo['x axis']
        else:
            self.plotTitle = str(self.fileName) + ': ' + self.plotTitle
        self.setWindowTitle(self.plotTitle)
        self.xIndex = self.plotInfo['x index']
        self.yIndex = self.plotInfo['y index']
        
        self.extents = [self.plotInfo['x range'][0], self.plotInfo['x range'][1]]
        self.pxsize = self.plotInfo['x points']
        
        self.setupPlot(state)
        self.setupListener(self.reactor)
        
    def restartPlotting(self, newPlotInfo, listenDir, listenFile):
        print("restarting plot.....................  ", str(listenFile))
        self.dir = listenDir
        self.fileName = listenFile
        self.plotInfo = newPlotInfo
        print("redefining plot parameters")
        self.definePlotParams(0)
        
    def setupPlot(self, state = None):
        global ID_NEWDATA
        if state is None:
            self.id = ID_NEWDATA
        ID_NEWDATA = ID_NEWDATA + 1
        
        self.colorWheel = [(0,114,189), (216,83,25), (237,177,32), (126,47,142), (119,172,48)]
        self.QColorWheel = [QtGui.QColor(0,114,189), QtGui.QColor(216,83,25), QtGui.QColor(237,177,32), QtGui.QColor(126,47,142), QtGui.QColor(119,172,48)]
        self.penColor = self.colorWheel[int(self.id)%5]
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
        self.setPalette(p)
    
        self.layout = QtGui.QGridLayout(self)
        if  state is None:
            self.plot1D = pg.PlotWidget()
            self.plot1D.showAxis('right', show = True)
            self.plot1D.showAxis('top', show = True)
            self.traceCntBox = QtGui.QComboBox()
            self.traceCntBox.setObjectName('traceCntBox')
            

            self.currentTraceColor = str(self.colorWheel[int(self.id)%5])
            self.traceCntStyle = "QComboBox#traceCntBox{width: 20px; color: rgb(131,131,131); background-color: 'balck';  border: 2px solid rgb(131,131,131); border-radius: 5px;  "
            self.styleColorTxt = 'color: rgb'+self.currentTraceColor+';}'
            self.traceCntBox.setStyleSheet(self.traceCntStyle+self.styleColorTxt)
            self.traceCntBox.insertItem(0, '1')
            self.traceCntBox.insertItem(1, '2')
            self.traceCntBox.insertItem(2, '3')
            self.traceCntBox.insertItem(3, '4')
            self.traceCntBox.insertItem(4, '5')
            self.traceCntBox.setItemData(0, self.QColorWheel[int(self.id)%5], QtCore.Qt.TextColorRole)
            self.traceCntBox.setItemData(1, self.QColorWheel[int(self.id + 1)%5], QtCore.Qt.TextColorRole)
            self.traceCntBox.setItemData(2, self.QColorWheel[int(self.id + 2)%5], QtCore.Qt.TextColorRole)
            self.traceCntBox.setItemData(3, self.QColorWheel[int(self.id + 3)%5], QtCore.Qt.TextColorRole)
            self.traceCntBox.setItemData(4, self.QColorWheel[int(self.id + 4)%5], QtCore.Qt.TextColorRole)
            self.traceCntBox.setItemData(0, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
            self.traceCntBox.setItemData(1, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
            self.traceCntBox.setItemData(2, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
            self.traceCntBox.setItemData(3, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
            self.traceCntBox.setItemData(4, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
            
            self.traceCntBox.currentIndexChanged.connect(self.alterColor)

            self.plotTitleLbl = QtGui.QLabel()
            self.plotTitleLbl.setText(self.plotTitle)
            self.plotTitleLbl.setObjectName('plotTitleLbl')
            self.plotTitleLbl.setStyleSheet("QLabel#plotTitleLbl {color: rgb(131,131,131); font: 11pt;}")
            self.traceCntLbl = QtGui.QLabel()
            self.traceCntLbl.setText('Plot Previous Traces:')
            self.traceCntLbl.setObjectName('traceCntLbl')
            self.traceCntLbl.setStyleSheet("QLabel#traceCntLbl {color: rgb(131,131,131); font: 10pt;}")
            
            self.layout.addWidget(self.plot1D, *(1,0, 1, 50))
            self.layout.addWidget(self.traceCntBox, *(0,43))
            self.layout.addWidget(self.traceCntLbl, *(0,42))
            self.layout.addWidget(self.plotTitleLbl, *(0,2))
            self.setLayout(self.layout)
        else:
            self.plot1D.clear()
            self.plotTitleLbl.setText(self.plotTitle)
            self.plotTitleLbl.setStyleSheet("QLabel#plotTitleLbl {color: rgb(131,131,131); font: 11pt;}")
        self.plot1D.setLabel('left', self.plotInfo['y axis'])
        self.plot1D.setLabel('bottom', self.plotInfo['x axis'])
        self.plot1D.enableAutoRange(enable = True)
        self.traceCntBox.setCurrentIndex(0)
    
        self.xScale = np.absolute((self.extents[1] - self.extents[0])/ self.pxsize)
        if self.extents[0] < self.extents[1]:
            self.xBins = np.linspace(self.extents[0] - 0.5*self.xScale, self.extents[1] + 0.5*self.xScale, self.pxsize + 1)
        else:
            self.xBins = np.linspace(self.extents[0] + 0.5*self.xScale, self.extents[1] - 0.5*self.xScale, self.pxsize + 1)
        self.XplotData, self.YplotData = {}, {}
        self.back0, self.back1, self.back2, self.back3, self.back4 = pg.PlotCurveItem(), pg.PlotCurveItem(), pg.PlotCurveItem(), pg.PlotCurveItem(), pg.PlotCurveItem()
        self.oldTraces = [self.back0, self.back1, self.back2, self.back3, self.back4]
            
    def alterColor(self):
        i = self.traceCntBox.currentIndex()
        oldTC = self.traceCnt
        self.traceCnt = int(i)
        self.currentTraceColor = str(self.colorWheel[int(self.id + i)%5])
        self.styleColorTxt = 'color: rgb'+self.currentTraceColor+';}'
        self.traceCntBox.setStyleSheet(self.traceCntStyle+self.styleColorTxt)
        if int(i) > oldTC:
            for j in range(oldTC + 1, int(i)+1):
                if j < self.numLines: 
                    self.plot1D.addItem(self.oldTraces[j])
        elif int(i) < oldTC:
            for j in range(int(i)+1, oldTC+1):
                if j < self.numLines: 
                    self.oldTraces[j].setData(x = [], y = [])
                    self.plot1D.removeItem(j)

        


        
    
    @inlineCallbacks
    def setupListener(self, c):
        try: 
            if self.cxnName is None:
                cxnName = 'plot' + str(self.id)
                from labrad.wrappers import connectAsync
                self.cxn = yield connectAsync(name = cxnName)
                self.dv = yield self.cxn.data_vault
            yield self.dv.cd(self.dir)
            yield self.dv.open(self.fileName)

            yield self.addListen(self.reactor)

            newData = yield self.dv.get()
            
            if len(newData) == 0 or len(newData[0]) == 0:
                pass
            else:
                inx = np.delete(np.arange(0, len(newData[0])), [self.xIndex, self.yIndex])
                newData = np.delete(np.asarray(newData), inx, axis = 1)
                
                x_ind = np.where(np.sort([self.xIndex, self.yIndex]) == self.xIndex)[0][0]
                y_ind = np.where(np.sort([self.xIndex, self.yIndex]) == self.yIndex)[0][0]

                self.Data = newData
                self.isData = True
                self.binned = np.digitize(newData[::, x_ind], self.xBins) - 1

                if len(self.binned) > 2:
                    p = np.argwhere(np.diff(self.binned) != np.diff(self.binned)[0])
                    if len(p) != 0:
                        xVals = newData[p[-1][0]+1::, x_ind]
                        yVals = newData[p[-1][0]+1::, y_ind]
                    else:
                        xVals, yVals = newData[::, x_ind], newData[::, y_ind]
                    
                else:
                    xVals, yVals = newData[::, x_ind], newData[::, y_ind]

                self.plot1D.clear()
                self.oldTraces[0].setData(x = xVals, y = yVals, pen =pg.mkPen(color=self.penColor))
                self.plot1D.addItem(self.oldTraces[0])
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2])
            
    @inlineCallbacks
    def addListen(self, c):
        yield self.dv.signal__data_available(self.id)
        yield self.dv.addListener(listener=self.updatePlot, ID=self.id)

    @inlineCallbacks
    def updatePlot(self, c, signal):

        newData = yield self.dv.get()
        inx = np.delete(np.arange(0, len(newData[0])), [self.xIndex, self.yIndex])
        newData = np.delete(np.asarray(newData), inx, axis = 1)
        
        x_ind = np.where(np.sort([self.xIndex, self.yIndex]) == self.xIndex)[0][0]
        y_ind = np.where(np.sort([self.xIndex, self.yIndex]) == self.yIndex)[0][0]

        
        if self.isData != False:
            self.Data = np.vstack((self.Data, newData))
        else:
            self.Data = newData
            self.isData = True
        self.binned = np.digitize(self.Data[::, x_ind], self.xBins) - 1
        yield self.plotMore(x_ind, y_ind, self.reactor)

    @inlineCallbacks
    def plotMore(self, x_ind, y_ind, c):
        try:
            yield self.sleep(0.1)
            if len(self.binned) > 2:
                p = np.argwhere(np.diff(self.binned) != np.diff(self.binned)[0])
                if len(p) != 0:
                    if len(p) == self.numLines:
                        xVals = self.Data[p[-1][0]+1::, x_ind]
                        yVals = self.Data[p[-1][0]+1::, y_ind]
                    else:
                        xVals = self.Data[p[-1][0]+1::, x_ind]
                        yVals = self.Data[p[-1][0]+1::, y_ind]
                        if len(p) > 5:
                            i = 1
                            while i <= np.amin((len(p), 5)):
                                self.XplotData[(i)%5] = self.Data[p[-i - 1][0] + 1:p[-i][0] + 1, x_ind]
                                self.YplotData[(i)%5] = self.Data[p[-i - 1][0] + 1:p[-i][0] + 1, y_ind]
                                i += 1
                        else:
                            for i in range(1, len(p)):
                                self.XplotData[(i)%5] = self.Data[p[-i - 1][0]+1:p[-i][0] + 1, x_ind]
                                self.YplotData[(i)%5] = self.Data[p[-i - 1][0]+1:p[-i][0] + 1, y_ind]
                            self.XplotData[len(p)] = self.Data[0:p[-len(p)][0] + 1, x_ind]
                            self.YplotData[len(p)] = self.Data[0:p[-len(p)][0] + 1, y_ind]
                        self.numLines = len(p)
                else:
                    xVals, yVals = self.Data[::, x_ind], self.Data[::, y_ind]
                
            else:
                xVals, yVals = self.Data[::, x_ind], self.Data[::, y_ind]


            self.plot1D.clear()
            self.oldTraces[0].setData(x = xVals, y = yVals, pen = pg.mkPen(color=self.penColor))
            self.plot1D.addItem(self.oldTraces[0])
            i = 1
            while i <= self.traceCnt and i  <= self.numLines:
                self.oldTraces[i].setData(x = self.XplotData[(i)%5], y = self.YplotData[(i)%5], pen = pg.mkPen(color = self.colorWheel[int(self.id+i)%5]))
                self.plot1D.addItem(self.oldTraces[i])
                i += 1
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2]) 
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def closeEvent(self, e):
        self.mainWin.existing1DPlotDict.pop(self.plotWinID)
        self.mainWin.renumPlotDicts(1)
        self.cxn.disconnect()
        self.close()

class plotSaved1DWindow(QtGui.QWidget):
    def __init__(self, reactor, file, dir, plotInfo, yMovePos, pencolor):
        super(plotSaved1DWindow, self).__init__()

        self.reactor = reactor
        self.file = file
        self.dir = dir
        self.plotInfo = plotInfo
        
        self.xIndex = self.plotInfo['x index']
        self.yIndex = self.plotInfo['y index']
        
        self.colorWheel = [(0,114,189), (216,83,25), (237,177,32), (126,47,142), (119,172,48)]
        self.QColorWheel = [QtGui.QColor(0,114,189), QtGui.QColor(216,83,25), QtGui.QColor(237,177,32), QtGui.QColor(126,47,142), QtGui.QColor(119,172,48)]
        self.penColor = self.colorWheel[int(pencolor)%5]

        
        self.xAxis = self.plotInfo['x axis']
        self.yAxis = self.plotInfo['y axis']

        self.notes = ''
        self.plotTitle = self.plotInfo['title']
        if self.plotTitle[0:5] == 'Plot ':
            self.plotTitle = str(self.file) + ': ' + self.yAxis + ' vs. ' + self.xAxis
        else:
            self.plotTitle = str(self.file) + ': ' + self.plotTitle
        self.setWindowTitle(self.plotTitle)
        self.pdfNum = 1
        
        self.resize(675,330)
        self.move(450, yMovePos)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
        self.setPalette(p)

        self.layout = QtGui.QGridLayout(self)
        
        
        self.plot1D = pg.PlotWidget()
        self.plot1D.showAxis('right', show = True)
        self.plot1D.showAxis('top', show = True)
        self.plot1D.setLabel('left', self.yAxis)
        self.plot1D.setLabel('bottom', self.xAxis)
        self.plot1D.enableAutoRange(enable = True)
        
        
        self.saveMATBtn = QtGui.QPushButton()
        self.savePDFBtn = QtGui.QPushButton()
        self.editNotesBtn = QtGui.QPushButton()
        self.openDVBtn = QtGui.QPushButton()
        self.backBtn = QtGui.QPushButton()
        self.backBtn1 = QtGui.QPushButton()
        
        self.saveMATBtn.clicked.connect(self.save1DMAT)
        self.savePDFBtn.clicked.connect(self.savePDF)
        self.editNotesBtn.clicked.connect(self.openNotepad)
        
        self.saveMATBtn.setToolTip('Save plot as .mat file')
        self.savePDFBtn.setToolTip('Save plot and notes as PDF')
        self.openDVBtn.setToolTip('View data vault parameters and comments')
        self.editNotesBtn.setToolTip('Edit plot notes')
        
        self.titleLbl = QtGui.QLabel()

        self.titleLbl.setObjectName('titleLbl')
        self.titleLbl.setText(self.plotTitle)
        self.titleLbl.setStyleSheet("QLabel#titleLbl {background-color: 'black';color: rgb(131,131,131); font: 11pt; }")
        
        self.saveLbl = QtGui.QLabel()
        self.notesLbl = QtGui.QLabel()
        self.saveLbl.setObjectName('saveLbl')
        self.saveLbl.setText('Save Plot')
        self.saveLbl.setStyleSheet("QLabel#saveLbl {background-color: 'black';color: rgb(131,131,131); font: 10pt; }")
        self.notesLbl.setObjectName('notesLbl')
        self.notesLbl.setText('Add Notes')
        self.notesLbl.setStyleSheet("QLabel#notesLbl {background-color: 'black'; color: rgb(131,131,131); font: 10pt;}")
        
        self.backBtn.setObjectName("backBtn")
        self.backBtn.setStyleSheet("QPushButton#backBtn {color:rgb(131,131,131);background-color:black;border: 2px solid rgb(131,131,131);border-radius: 5px; height: 40px; width: 70px}")
        self.backBtn1.setObjectName("backBtn1")
        self.backBtn1.setStyleSheet("QPushButton#backBtn1 {color:rgb(131,131,131);background-color:black;border: 2px solid rgb(131,131,131);border-radius: 5px; height: 38px; width: 70px}")
        
        self.saveMATBtn.setObjectName('saveMATBtn')
        self.saveMATBtn.setStyleSheet("QPushButton#saveMATBtn {image:url(:/dvPlotter/Pictures/saveMATLAB.png);background-color: transparent; height: 23px; width: 23px;}")
        self.savePDFBtn.setObjectName('savePDFBtn')
        self.savePDFBtn.setStyleSheet("QPushButton#savePDFBtn {image:url(:/dvPlotter/Pictures/savePDF.png);background-color: transparent; height: 23px; width: 23px;}")
        self.editNotesBtn.setObjectName('editNotesBtn')
        self.editNotesBtn.setStyleSheet("QPushButton#editNotesBtn {image:url(:/dvPlotter/Pictures/editNotes.png);background-color: transparent; height: 15px; width: 23px;}")
        self.openDVBtn.setObjectName('openDVBtn')
        self.openDVBtn.setStyleSheet("QPushButton#openDVBtn {image:url(:/dvPlotter/Pictures/browse.png); background-color: transparent; height: 18px; width: 18px;}")
        
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1,5)
        self.layout.setColumnStretch(2,1)
        self.layout.setColumnStretch(3,1)
        self.layout.setColumnStretch(4,1)
        self.layout.setColumnStretch(5,1)
        self.layout.setColumnStretch(6,1)
        self.layout.setColumnStretch(7,1)
        
        self.layout.addWidget(self.plot1D, *(1, 0, 1, 15))
        self.layout.addWidget(self.titleLbl, *(0, 1, 1, 1))
        

        self.layout.addWidget(self.saveMATBtn, *(0, 8, 1, 1), alignment = QtCore.Qt.AlignRight)
        self.layout.addWidget(self.savePDFBtn, *(0, 9, 1, 1), alignment = QtCore.Qt.AlignRight)
        self.layout.addWidget(self.editNotesBtn, *(0, 10, 1, 1), alignment =QtCore.Qt.AlignRight) 


        self.setLayout(self.layout)
        
        self.backBtn.lower()
        self.backBtn1.lower()
        self.notesLbl.resize(100, 100)
        
        self.openFile(self.reactor)
        
    @inlineCallbacks
    def openFile(self, c):
        from labrad.wrappers import connectAsync

        self.cxnS = yield connectAsync()
        self.dv = yield self.cxnS.data_vault
        yield self.dv.cd(self.dir)
        yield self.dv.open(self.file)
        self.loadData(self.reactor)
    
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    @inlineCallbacks
    def loadData(self, c):
        getFlag = True
        self.Data = np.array([])
        while getFlag == True:
            line = yield self.dv.get(1000)

            try:
                if len(self.Data) != 0 and len(line) > 0:
                    self.Data = np.vstack((self.Data, line))                        
                elif len(self.Data) == 0 and len(line) > 0:
                    self.Data = np.asarray(line)
                else:
                    getFlag = False
            except:
                getFlag = False

        inds =[self.xIndex, self.yIndex]
        inx = np.delete(np.arange(0, len(self.Data[0])), inds)
        self.Data = np.delete(self.Data, inx, axis = 1)
        self.x_ind = np.argwhere(np.sort(inds) == inds[0])[0][0]
        self.y_ind = np.argwhere(np.sort(inds) == inds[1])[0][0]
        self.xVals, self.yVals = self.Data[::, self.x_ind], self.Data[::, self.y_ind]
        
        self.plot1D.plot(x = self.xVals, y = self.yVals, pen =pg.mkPen(color=self.penColor))
        
    def save1DMAT(self):
        fold  = self.getSaveData('mat')
        yData = np.asarray(self.xVals)
        xData = np.asarray(self.yVals)
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
        
    def getSaveData(self, ext):
        if ext == 'pdf':
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "PDF Document (*.pdf)"))
            if fold:
                return fold
        elif ext == 'mat':
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                return fold     
        
    @inlineCallbacks
    def savePDF(self, plot):
        
        
        #gets the file/folder for the PDF to be saved
        fold = self.getSaveData('pdf')
        try:
            folder = '/'.join(fold.split("/")[0:-1]) + '/'
            file = fold #fold.split("/")[-1]
        except:
            folder = os.getcwd()
            file = str(self.plotTitle) + time.strftime("%Y-%m-%d_%H:%M") + '.pdf'
        self.pdfFile = folder + '//tmp' + str(time.time()) + '.png'
        init_loc = os.getcwd()
        os.chdir(folder)
        if os.path.isfile(file):
            os.remove(file)
        if os.path.isfile(self.pdfFile):
            os.remove(self.pdfFile)
        yield self.sleep(.5)
        self.pdfNum += 1
        yield self.exportPng(init_loc, folder, file)
        
    @inlineCallbacks
    def exportPng(self, init_loc, folder, file, c = None):
        exporter = pg.exporters.ImageExporter(self.plot1D.plotItem)
        exporter.export(self.pdfFile)
        header = self.plotTitle

        os.chdir(init_loc)
        yield self.sleep(1)
        #generates the PDF
        yield self.genPDF(folder, file, header)
        self.pdfNum += 1
        

    def render_template(self, template_file, **kwargs):
        env = Environment(loader=PackageLoader("testPDFTemp", "templates"))
        template = env.get_template(template_file)
        return template.render(**kwargs)

    def print_pdf(self, html, destination):
        global app
        web = QWebView()
        web.setHtml(html)
        application = app.instance()
        application.processEvents()
     
        printer = QPrinter()
        printer.setPageSize(QPrinter.A4)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(destination)
        web.print_(printer)
        
     
    @inlineCallbacks
    def genPDF(self, folder, file, header):
        yield self.sleep(0.5)
        temp_loc = ''
        params = yield self.dv.get_parameters()
        parList = []
        if params != None:
            for i in range(0, len(params)):
                    parList.append([str(params[i][0]), str(params[i][1])])
        init_loc = os.getcwd()
        os.chdir(folder)
        temp_loc = "file://localhost/" + self.pdfFile.replace(' ', '%20')
        try:
            prgs = str(self.noteEdits.textEditor.toPlainText()).splitlines()
        except:
            prgs = []
        dataSet = header
        dateTime = time.strftime("%Y-%m-%d %H:%M")
        
        html = self.render_template(
            "report.html",
            data_set = dataSet,
            date_time = dateTime,
            parameters = parList,
            paragraphs = prgs,
            tmp_loc = temp_loc
            
        )



        self.pdfNum += 1
        self.print_pdf(html, str(file))
        if os.path.isfile(self.pdfFile):
            os.remove(self.pdfFile)
        tmp_loc = ''
        os.chdir(init_loc)
        
    def openNotepad(self):
        self.noteEdits = noteEditor(self.notes)

        self.noteEdits.exec_()
        if self.noteEdits.accepted:
            self.notes = self.noteEdits.textEditor.toPlainText()
        
class plotSaved2DWindow(QtWidgets.QWidget):
    def __init__(self, reactor, fileDV, dir, plotInfo, yMovePos ):
        super(plotSaved2DWindow, self).__init__()

        self.reactor = reactor
        self.file = fileDV
        self.dir = dir
        self.plotInfo = plotInfo

        self.xIndex = self.plotInfo['x index']
        self.yIndex = self.plotInfo['y index']
        self.zIndex = self.plotInfo['z index']
        
        self.xAxis = self.plotInfo['x axis']
        self.yAxis = self.plotInfo['y axis']
        self.zAxis = self.plotInfo['z axis']
        
        self.connect(QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL+ QtCore.Qt.Key_C), self), QtCore.SIGNAL('activated()'),self.copyPlotToClip)

        self.notes = ''
        self.plotTitle = self.plotInfo['title']
        if self.plotTitle[0:5] == 'Plot ':
            self.plotTitle = str(self.file) + ': ' + self.zAxis + ' vs. ' + self.xAxis + ' and ' + self.yAxis
        else:
            self.plotTitle = str(self.file) + ': ' + self.plotTitle
        self.setWindowTitle(self.plotTitle)
        self.pdfNum = 1
        
        self.resize(800,800)
        self.move(450, yMovePos)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
        self.setPalette(p)

        self.layout = QtGui.QGridLayout(self)
        
        self.viewBig = pg.PlotItem(name = "Plot 2D", title = self.plotTitle)
        self.viewBig.showAxis('top', show = True)
        self.viewBig.showAxis('right', show = True)
        self.viewBig.setLabel('left', self.yAxis)
        self.viewBig.setLabel('bottom', self.xAxis)
        self.viewBig.setAspectLocked(lock = False, ratio = 1)
        self.mainPlot = pg.ImageView(view = self.viewBig)
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.mainPlot.ui.roiBtn.hide()
        self.mainPlot.ui.menuBtn.hide()
        self.viewBig.setAspectLocked(False)
        self.viewBig.invertY(False)
        self.viewBig.setXRange(-1, 1)
        self.viewBig.setYRange(-1, 1)

        
        self.xLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.yLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.viewBig.addItem(self.xLine, ignoreBounds = True)
        self.viewBig.addItem(self.yLine, ignoreBounds =True)
        self.xLine.sigPositionChangeFinished.connect(self.updateXLineBox)
        self.yLine.sigPositionChangeFinished.connect(self.updateYLineBox)
        
        
        self.plot1D = pg.PlotWidget()
        self.plot1D.showAxis('right', show = True)
        self.plot1D.showAxis('top', show = True)
        self.plot1D.setLabel('left', self.zAxis)
        self.plot1D.setLabel('bottom', self.xAxis)
        self.plot1D.enableAutoRange(enable = True)
        
        self.xySelectBox = QtGui.QComboBox()
        self.xySelectBox.setObjectName('xySelectBox')
        self.xySelectBox.setStyleSheet("QComboBox#xySelectBox{width: 20px; color: rgb(131,131,131); background-color: 'balck';  border: 2px solid rgb(131,131,131); border-radius: 5px;}")
        self.xySelectBox.insertItem(0, 'Horizontal')
        self.xySelectBox.insertItem(1, 'Vertical')
        self.xySelectBox.currentIndexChanged.connect(self.toggleXYTrace)
        
        self.xySelectLbl = QtGui.QLabel()
        self.xySelectLbl.setObjectName('xySelectLbl')
        self.xySelectLbl.setText('Line Cut Direction:')
        self.xySelectLbl.setStyleSheet('QLabel#xySelectLbl {color: rgb(131,131,131); font: 10pt;}')
        self.xySelectBox.setItemData(0, QtGui.QColor(131,131,131), QtCore.Qt.TextColorRole)
        self.xySelectBox.setItemData(1, QtGui.QColor(131,131,131), QtCore.Qt.TextColorRole)
        self.xySelectBox.setItemData(0, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
        self.xySelectBox.setItemData(1, QtGui.QColor('black'), QtCore.Qt.BackgroundRole)
        
        self.tracePosLbl = QtGui.QLabel()
        self.tracePosLbl.setObjectName('tracePosLbl')
        self.tracePosLbl.setText('Line Cut Position:')
        self.tracePosLbl.setStyleSheet('QLabel#tracePosLbl {color: rgb(131,131,131); font: 10pt;}')
        
        self.tracePosBox = QtGui.QDoubleSpinBox()
        self.tracePosBox.setObjectName('tracePosBox')
        self.tracePosBox.setButtonSymbols(2)
        self.tracePosBox.setValue(0)
        
        self.tracePosBox.setDecimals(3)
        self.tracePosBox.valueChanged.connect(self.updateTrace)
        
        
        self.saveMATBtn = QtGui.QPushButton()
        self.savePDFBtn = QtGui.QPushButton()
        self.editNotesBtn = QtGui.QPushButton()
        self.openDVBtn = QtGui.QPushButton()
        self.backBtn = QtGui.QPushButton()
        self.backBtn1 = QtGui.QPushButton()
        
        self.saveMatMenu = QtGui.QMenu()
        save1D = QtGui.QAction("Save 1D trace", self)
        save2D = QtGui.QAction("Save 2D plot", self)
        save1D.triggered.connect(self.save1DMAT)
        save2D.triggered.connect(self.save2DMAT)
        self.saveMatMenu.addAction(save2D)
        self.saveMatMenu.addAction(save1D)
        self.saveMATBtn.setMenu(self.saveMatMenu)
        
        self.savePDFMenu = QtGui.QMenu()
        pdf1D = QtGui.QAction("Save 1D trace", self)
        pdf2D = QtGui.QAction("Save 2D plot", self)
        append2D = QtGui.QAction("Append 2D plot", self)
        append1D = QtGui.QAction("Append 1D plot", self)
        pdf1D.triggered.connect(lambda: self.savePDF(1))
        pdf2D.triggered.connect(lambda: self.savePDF(2))
        append2D.triggered.connect(lambda: self.savePDF(3))
        append1D.triggered.connect(lambda: self.savePDF(4))
        self.savePDFMenu.addAction(pdf2D)
        self.savePDFMenu.addAction(pdf1D)
        self.savePDFMenu.addAction(append2D)
        self.savePDFMenu.addAction(append1D)
        self.savePDFBtn.setMenu(self.savePDFMenu)
        
        self.editNotesBtn.clicked.connect(self.openNotepad)
        
        self.saveMATBtn.setToolTip('Save plot as .mat file')
        self.savePDFBtn.setToolTip('Save plot and notes as PDF')
        self.openDVBtn.setToolTip('View data vault parameters and comments')
        self.editNotesBtn.setToolTip('Edit plot notes')
        
        self.saveLbl = QtGui.QLabel()
        self.notesLbl = QtGui.QLabel()
        self.saveLbl.setObjectName('saveLbl')
        self.saveLbl.setText('Save Plot')
        self.saveLbl.setStyleSheet("QLabel#saveLbl {background-color: 'black';color: rgb(131,131,131); font: 10pt; }")
        self.notesLbl.setObjectName('notesLbl')
        self.notesLbl.setText('Add Notes')
        self.notesLbl.setStyleSheet("QLabel#notesLbl {background-color: 'black'; color: rgb(131,131,131); font: 10pt;}")
        
        self.backBtn.setObjectName("backBtn")
        self.backBtn.setStyleSheet("QPushButton#backBtn {color:rgb(131,131,131);background-color:black;border: 2px solid rgb(131,131,131);border-radius: 5px; height: 40px; width: 70px}")
        self.backBtn1.setObjectName("backBtn1")
        self.backBtn1.setStyleSheet("QPushButton#backBtn1 {color:rgb(131,131,131);background-color:black;border: 2px solid rgb(131,131,131);border-radius: 5px; height: 38px; width: 70px}")
        
        self.saveMATBtn.setObjectName('saveMATBtn')
        self.saveMATBtn.setStyleSheet("QPushButton#saveMATBtn {image:url(:/dvPlotter/Pictures/saveMATLAB.png);background-color: transparent; height: 23px; width: 23px;}")
        self.savePDFBtn.setObjectName('savePDFBtn')
        self.savePDFBtn.setStyleSheet("QPushButton#savePDFBtn {image:url(:/dvPlotter/Pictures/savePDF.png);background-color: transparent; height: 23px; width: 23px;}")
        self.editNotesBtn.setObjectName('editNotesBtn')
        self.editNotesBtn.setStyleSheet("QPushButton#editNotesBtn {image:url(:/dvPlotter/Pictures/editNotes.png);background-color: transparent; height: 15px; width: 23px;}")
        self.openDVBtn.setObjectName('openDVBtn')
        self.openDVBtn.setStyleSheet("QPushButton#openDVBtn {image:url(:/dvPlotter/Pictures/browse.png); background-color: transparent; height: 18px; width: 18px;}")
        
        

        self.layout.setRowStretch(0, 500)
        self.layout.setRowStretch(1,1)
        self.layout.setRowStretch(2,1)
        self.layout.setRowStretch(3,1)
        self.layout.setRowStretch(4,1)
        self.layout.setRowStretch(5,1)
        self.layout.setRowStretch(6,1)
        self.layout.setRowStretch(7,1)
        self.layout.setRowStretch(8,1)
        self.layout.setRowStretch(9,1)
        self.layout.setRowStretch(10,1)
        self.layout.setRowStretch(11,1)
        self.layout.setRowStretch(12,1)
        
        self.layout.setColumnStretch(0, 18)
        self.layout.setColumnStretch(1,8)
        self.layout.setColumnStretch(2,2)
        self.layout.setColumnStretch(3,2)
        
        self.layout.addWidget(self.mainPlot, *(0, 0, 1, 4))
        self.layout.addWidget(self.plot1D, *(1,0, 12, 2))
        self.layout.addWidget(self.xySelectLbl, *(2,2, 1, 2), alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.xySelectBox, *(3,2, 1, 2), alignment = QtCore.Qt.AlignTop)
        
        self.layout.addWidget(self.tracePosLbl, *(4,2, 1, 2), alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.tracePosBox, *(5,2, 1, 2), alignment = QtCore.Qt.AlignTop)
        
        self.layout.addWidget(self.saveLbl, *(7,2, 1, 2), alignment = QtCore.Qt.AlignHCenter| QtCore.Qt.AlignBottom)
        self.layout.addWidget(self.backBtn, *(7,2, 2, 2), alignment = QtCore.Qt.AlignBottom)
        self.layout.addWidget(self.saveMATBtn, *(8, 2, 1, 1), alignment = QtCore.Qt.AlignRight)
        self.layout.addWidget(self.savePDFBtn, *(8, 3, 1, 1), alignment = QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.backBtn1, *(9,2, 2, 2), alignment = QtCore.Qt.AlignBottom)
        self.layout.addWidget(self.notesLbl, *(9,2, 1, 2), alignment = QtCore.Qt.AlignHCenter| QtCore.Qt.AlignBottom)
        self.layout.addWidget(self.editNotesBtn, *(10, 3, 1, 1), alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop) 
        self.layout.addWidget(self.openDVBtn, *(10, 2, 1, 1), alignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)

        self.setLayout(self.layout)
        
        self.backBtn.lower()
        self.backBtn1.lower()
        self.notesLbl.resize(100, 100)

        
        self.openFile(self.reactor)
        
    def copyPlotToClip(self):
        r = self.mainPlot.ui.histogram.region.getRegion()
        self.mainPlot.ui.histogram.vb.setYRange(*r)
        #create ImageExpoerters:
        mainExp = pg.exporters.ImageExporter(self.viewBig)
        colorAxisExp = pg.exporters.ImageExporter(self.mainPlot.ui.histogram.axis)
        colorBarExp = pg.exporters.ImageExporter(self.mainPlot.ui.histogram.gradient)
        #create QImages:
        main =mainExp.export(toBytes=True)
        colorAxis =colorAxisExp.export(toBytes=True)
        colorBar = colorBarExp.export(toBytes=True)
        #define teh size:
        x = main.width() + colorAxis.width() + colorBar.width()
        y = main.height()
        #to get everything in the same height:
        yOffs = [0,0.5*(y-colorAxis.height()),0.5*(y-colorBar.height())]
        result = QtGui.QImage(x, y ,QtGui.QImage.Format_RGB32)
        painter = QtGui.QPainter(result)
        posX = 0
        for img,y in zip((main,colorAxis,colorBar),yOffs):
                #draw every part in different positions:
                painter.drawImage(posX, y, img)
                posX += img.width()
        painter.end()
        #save to file
        QApplication.clipboard().setImage(result)

        
    def updateTrace(self):
        pos = self.tracePosBox.value()
        if self.xySelectBox.currentIndex() == 1:
            self.yLine.setValue(pos)
            self.updatePlot1D(pos,'y')
        elif self.xySelectBox.currentIndex() == 0:
            self.xLine.setValue(pos)
            self.updatePlot1D(pos,'x')
            
        
    @inlineCallbacks
    def openFile(self, c):
        from labrad.wrappers import connectAsync
        self.cxnS = yield connectAsync()
        self.dv = yield self.cxnS.data_vault
        yield self.dv.cd(self.dir)
        yield self.dv.open(self.file)
        self.loadData(self.reactor)
    
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    @inlineCallbacks
    def loadData(self, c):
        getFlag = True
        self.Data = np.array([])
        while getFlag == True:
            line = yield self.dv.get(1000)

            try:
                if len(self.Data) != 0 and len(line) > 0:
                    self.Data = np.vstack((self.Data, line))                        
                elif len(self.Data) == 0 and len(line) > 0:
                    self.Data = np.asarray(line)
                else:
                    getFlag = False
            except:
                getFlag = False

        inds =[self.xIndex, self.yIndex, self.zIndex]
        inx = np.delete(np.arange(0, len(self.Data[0])), inds)
        self.Data = np.delete(self.Data, inx, axis = 1)
        self.x_ind = np.argwhere(np.sort(inds) == inds[0])[0][0]
        self.y_ind = np.argwhere(np.sort(inds) == inds[1])[0][0]
        self.z_ind = np.argwhere(np.sort(inds) == inds[2])[0][0]

        params = yield self.dv.get_parameters()
                    
        if params != None:
            params = dict((x,y) for x,y in params)      
            x_rng, x_pnts = self.xAxis + '_rng', self.xAxis + '_pnts'
            y_rng, y_pnts = self.yAxis + '_rng', self.yAxis + '_pnts'
            
            gotX, gotY = False, False
            
            if x_rng in params and x_pnts in params:
                xMin, xMax = np.amin(params[x_rng]), np.amax(params[x_rng])
                xPnts = params[x_pnts]
                gotX = True
                
            if y_rng in params and y_pnts in params:
                yMin, yMax = np.amin(params[y_rng]), np.amax(params[y_rng])
                yPnts = params[y_pnts]
                gotY = True
            if gotX == True and gotY == True:
                self.extents = [xMin, xMax, yMin, yMax]
                self.numPts = [int(xPnts), int(yPnts)]
            else:
                pass
    
        else:
            dsX = np.diff(np.sort(self.Data[::, self.x_ind]))
            dsY = np.diff(np.sort(self.Data[::, self.y_ind]))
            xJumps = np.diff(np.argwhere(dsX > np.average(dsX) +0.5* np.std(dsX)).flatten())
            yJumps = np.diff(np.argwhere(dsY > np.average(dsY) + 0.5* np.std(dsY)).flatten())
            yPts = spst.mode(xJumps)[0][0]
            xPts = spst.mode(yJumps)[0][0]
            self.extents = [np.amin(self.Data[::, self.x_ind]), np.amax(self.Data[::, self.x_ind]), np.amin(self.Data[::, self.y_ind]), np.amax(self.Data[::, self.y_ind])]
            self.numPts = [int(xPts), int(yPts)]

        self.x0, self.y0 = self.extents[0], self.extents[2]
        self.xscale = float((self.extents[1] - self.extents[0])/self.numPts[0])
        self.yscale = float((self.extents[3] - self.extents[2])/self.numPts[1])


        if self.extents[0] < self.extents[1]:
            self.xBins = np.linspace(self.extents[0] - 0.5*self.xscale, self.extents[1] + 0.5*self.xscale, self.numPts[0] + 1)
        else:
            self.xBins = np.linspace(self.extents[1] - 0.5*self.xscale, self.extents[0] + 0.5*self.xscale, self.numPts[0] + 1)
        if self.extents[2] < self.extents[3]:
            self.yBins = np.linspace(self.extents[2] - 0.5*self.yscale, self.extents[3] + 0.5*self.yscale, self.numPts[1] + 1)
        else:
            self.yBins = np.linspace(self.extents[3] - 0.5*self.yscale, self.extents[2] + 0.5*self.yscale, self.numPts[1] + 1)
        self.plotData = np.zeros([self.numPts[0], self.numPts[1]])

        try:
            self.Data[::, self.x_ind] = np.digitize(self.Data[::, self.x_ind], self.xBins)-1
            self.Data[::, self.y_ind] = np.digitize(self.Data[::, self.y_ind], self.yBins)-1
            
            for cell in self.Data:
                self.plotData[int(cell[self.x_ind]), int(cell[self.y_ind])] = cell[self.z_ind]
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2])
        
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        
    
    def updateXLineBox(self):

        if self.xySelectBox.currentIndex() == 0:
            pos = self.xLine.value()
            self.tracePosBox.setValue(float(pos))
            self.updatePlot1D(pos, 'x')
    def updateYLineBox(self):

        if self.xySelectBox.currentIndex() == 1:
            pos = self.yLine.value()
            self.tracePosBox.setValue(float(pos))
            self.updatePlot1D(pos,'y')
    
    def toggleXYTrace(self, i):
        if i == 0:
            self.updateXLineBox()
        elif i == 1:
            self.updateYLineBox()
        else:
            print("this is impossible!")
            
    def updatePlot1D(self, pos, axis):
        #self.extents = [xMin, xMax, yMin, yMax]
        if axis =='y':
            if pos < self.extents[1] and pos > self.extents[0]:
                index = int((pos - self.extents[0]) / self.xscale)
                yVals = self.plotData[index, ::]
                xVals = np.linspace(self.extents[2], self.extents[3], self.numPts[1])
                self.lineXVals, self.lineYVals = xVals, yVals
                self.plot1D.clear()
                self.plot1D.plot(x = xVals, y = yVals, pen = 0.5)
                self.plot1D.setLabel('bottom', self.yAxis)
        elif axis == 'x':
            if pos < self.extents[3] and pos > self.extents[2]:
                index = int((pos - self.extents[2]) / self.yscale)
                yVals = self.plotData[::, index]
                xVals = np.linspace(self.extents[0], self.extents[1], self.numPts[0])
                self.lineXVals, self.lineYVals = xVals, yVals
                self.plot1D.clear()
                self.plot1D.plot(x = xVals, y = yVals, pen = 0.5)
                self.plot1D.setLabel('bottom', self.xAxis)
        else:
            print("you have entered another dimension")
            
    def getSaveData(self, ext):
        if ext == 'pdf':
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "PDF Document (*.pdf)"))
            if fold:
                return fold
        elif ext == 'mat':
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                return fold

    def save1DMAT(self):
        fold  = self.getSaveData('mat')
        yData = np.asarray(self.lineYVals)
        xData = np.asarray(self.lineXVals)
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
        
    def save2DMAT(self):
        fold  = self.getSaveData('mat')
        xVals = np.linspace(self.extents[0], self.extents[1], int(self.numPts[0]))
        yVals = np.linspace(self.extents[2], self.extents[3], int(self.numPts[1]))
        xInd, yInd = np.linspace(0,  self.numPts[0] - 1,  int(self.numPts[0])), np.linspace(0,  self.numPts[1] - 1, int(self.numPts[1]))
        zX, zY, zXI, zYI = np.ones([1,int(self.numPts[1])]), np.ones([1,int(self.numPts[0])]), np.ones([1,int(self.numPts[1])]), np.ones([1,int(self.numPts[0])])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.plotData.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
        
    @inlineCallbacks
    def savePDF(self, plot, c = None):
        
        
        #gets the file/folder for the PDF to be saved
        fold = self.getSaveData('pdf')
        try:
            folder = '/'.join(fold.split("/")[0:-1]) + '/'
            file = fold #fold.split("/")[-1]
        except:
            folder = os.getcwd()
            file = str(self.plotTitle) + time.strftime("%Y-%m-%d_%H:%M") + '.pdf'
        self.pdfFile = folder + '//tmp' + str(time.time()) + '.png'

        init_loc = os.getcwd()
        os.chdir(folder)
        yield self.sleep(0.5)
        self.pdfNum += 1

        yield self.exportPng(init_loc, folder, file, plot)
        
    @inlineCallbacks
    def exportPng(self, init_loc, folder, file, plot, c = None):
        if plot == 2 or plot == 3:
            #creates a .png file of the 2D plot window
            self.xLine.hide()
            self.yLine.hide()
            #exporter = pg.exporters.ImageExporter(self.viewBig)
            #exporter.export(self.pdfFile)
            
            r = self.mainPlot.ui.histogram.region.getRegion()
            self.mainPlot.ui.histogram.vb.setYRange(*r)
            #create ImageExpoerters:
            mainExp = pg.exporters.ImageExporter(self.viewBig)
            colorAxisExp = pg.exporters.ImageExporter(self.mainPlot.ui.histogram.axis)
            colorBarExp = pg.exporters.ImageExporter(self.mainPlot.ui.histogram.gradient)
            #create QImages:
            main =mainExp.export(toBytes=True)
            colorAxis =colorAxisExp.export(toBytes=True)
            colorBar = colorBarExp.export(toBytes=True)
            #define teh size:
            x = main.width() + colorAxis.width() + colorBar.width()
            y = main.height()
            #to get everything in the same height:
            yOffs = [0,0.5*(y-colorAxis.height()),0.5*(y-colorBar.height())]
            result = QtGui.QImage(x, y ,QtGui.QImage.Format_RGB32)
            painter = QtGui.QPainter(result)
            posX = 0
            for img,y in zip((main,colorAxis,colorBar),yOffs):
                    #draw every part in different positions:
                    painter.drawImage(posX, y, img)
                    posX += img.width()
            painter.end()
            #save to file
            result.save(self.pdfFile)       
            
            self.xLine.show()
            self.yLine.show()
            header = str(self.file) + ': ' + self.plotTitle
        elif plot == 1 or plot == 4:
            #creates a .png file of the 2D plot window
            exporter = pg.exporters.ImageExporter(self.plot1D.plotItem)
            exporter.export(self.pdfFile)
            header = str(self.file) + ': ' + self.plotTitle
                


        os.chdir(init_loc)
        yield self.sleep(0.5)
        #generates the PDF
        yield self.genPDF(folder, file, header, plot)
        self.pdfNum += 1
        

    def render_template(self, template_file, **kwargs):
        env = Environment(loader=PackageLoader("testPDFTemp", "templates"))
        template = env.get_template(template_file)
        return template.render(**kwargs)

    def print_pdf(self, html, destination):
        global app
        web = QWebView()
        web.setHtml(html)
        application = app.instance()
        application.processEvents()
     
        printer = QPrinter()
        printer.setPageSize(QPrinter.A4)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(destination)
        web.print_(printer)
        
     
    @inlineCallbacks
    def genPDF(self, folder, fileName, header, plot):
        print("generating pdf")
        yield self.sleep(1)
        params = yield self.dv.get_parameters()
        parList = []
        if params != None:
            for i in range(0, len(params)):
                if str(params[i][0]) != 'live_plots':
                    parList.append([str(params[i][0]), str(params[i][1])])
        init_loc = os.getcwd()
        os.chdir(folder)
        temp_loc = "file://localhost/" + self.pdfFile.replace(' ', '%20')
        try:
            prgs = str(self.noteEdits.textEditor.toPlainText()).splitlines()
        except:
            prgs = []
        dataSet = header
        dateTime = time.strftime("%Y-%m-%d %H:%M")
        try:
            html = self.render_template(
                "report.html",
                data_set = dataSet,
                date_time = dateTime,
                parameters = parList,
                paragraphs = prgs,
                tmp_loc = temp_loc
                
            )
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2])
        
        if plot < 3:
            self.print_pdf(html, str(fileName))
        else:
            tmp_pdf = folder + str(time.time()) + 'tmp_pdf.pdf'
            toMerge = str(fileName)
            self.print_pdf(html, str(tmp_pdf))
            merger = PdfFileMerger()
            try:
                merger.append(PdfFileReader(file(toMerge, 'rb')))
                merger.append(PdfFileReader(file(tmp_pdf, 'rb')))

                merger.write(toMerge)   
            except Exception as inst:
                print("Following error was thrown: ")
                print(str(inst))
                print("Error thrown on line: ")
                print(sys.exc_info()[2])
        tmp_loc = ''
        yield self.sleep(0.5)
        try:
            if os.path.isfile(self.pdfFile):
                os.remove(self.pdfFile)
            if plot >= 3 and os.path.isfile(tmp_pdf):
                os.remove(tmp_pdf)
        except Exception as inst:
            print("Following error was thrown: ")
            print(str(inst))
            print("Error thrown on line: ")
            print(sys.exc_info()[2])
        os.chdir(init_loc)
        
        
        
    def openNotepad(self):
        self.noteEdits = noteEditor(self.notes)

        self.noteEdits.exec_()
        if self.noteEdits.accepted:
            self.notes = self.noteEdits.textEditor.toPlainText()

class noteEditor(QtGui.QDialog):
    def __init__(self, notes):
        super(noteEditor, self).__init__()
        self.notes = notes
        

        self.textEditor = textEditor()
        self.textEditor.setPlainText(self.notes)
        
        self.resize(400,400)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
        self.setPalette(p)
        
        self.okBtn = QtGui.QPushButton()
        self.okBtn.setObjectName('okBtn')
        self.okBtn.setText('OK')
        self.okBtn.setStyleSheet("QPushButton#okBtn {color:rgb(131,131,131);background-color:black;border: 2px solid rgb(131,131,131);border-radius: 5px; width: 25px; font: 11pt}")
        self.okBtn.clicked.connect(self.closeEdit)

        self.layout = QtGui.QGridLayout(self)
        self.layout.addWidget(self.textEditor, *(0, 0))
        self.layout.addWidget(self.okBtn, *(1, 0), alignment = QtCore.Qt.AlignHCenter)
        self.setLayout(self.layout)

    def closeEdit(self):
        self.accept()
        self.hide()
        
    def closeEvent(self, e):
        self.reject()
        self.close()

class LineNumberArea(QtGui.QWidget):

    def __init__(self, editor):
        super(QtGui.QWidget, self).__init__(editor)
        self.myeditor = editor

    def sizeHint(self):
        return QtCore.QSize(self.myeditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.myeditor.lineNumberAreaPaintEvent(event)

class textEditor(QtGui.QPlainTextEdit):
    def __init__(self, parent = None):
        super(QtGui.QPlainTextEdit, self).__init__(parent)
        
        self.lineNumberArea = LineNumberArea(self)

        self.connect(self, QtCore.SIGNAL('blockCountChanged(int)'), self.updateLineNumberAreaWidth)
        self.connect(self, QtCore.SIGNAL('updateRequest(QRect,int)'), self.updateLineNumberArea)
        self.connect(self, QtCore.SIGNAL('cursorPositionChanged()'), self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)

    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space


    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    def updateLineNumberArea(self, rect, dy):

        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(),
                       rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)


    def resizeEvent(self, event):
        super(QtGui.QPlainTextEdit, self).resizeEvent(event)

        cr = self.contentsRect();
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(),
                    self.lineNumberAreaWidth(), cr.height()))


    def lineNumberAreaPaintEvent(self, event):
        mypainter = QtGui.QPainter(self.lineNumberArea)

        mypainter.fillRect(event.rect(), QtCore.Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Just to make sure I use the right font
        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                mypainter.setPen(QtCore.Qt.black)
                mypainter.drawText(0, top, self.lineNumberArea.width(), height,
                 QtCore.Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QtGui.QTextEdit.ExtraSelection()

            #TODO Edit color
            lineColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

class plotSetup(QtGui.QDialog, Ui_PlotSetup):
    def __init__(self, reactor, file, dir, cxn, dv, fresh, parent = None):
        #Fresh numbers
        #0 comes from listener
        #1 comes from live
        #2 comes from saved
        
        super(plotSetup, self).__init__(parent)
        QtGui.QDialog.__init__(self)

        self.reactor = reactor
        self.file = str(file)
        self.dir = dir
        self.cxn = cxn
        self.dv = dv
        self.fresh = fresh
        
        self.mainWin = parent
        
        self.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(guiIconPath))
        self.setWindowIcon(icon)
        self.moveDefault()
        
        self.formFlag = True
        self.setupTables()
    
        self.cancelBtn.clicked.connect(self.closeWindow)
        self.ok.clicked.connect(self.initPlot)
        
        self.add1D.clicked.connect(self.add1DPlot)
        self.add2D.clicked.connect(self.add2DPlot)
        
        self.rmv1D.clicked.connect(self.rmv1DPlot)
        self.rmv2D.clicked.connect(self.rmv2DPlot)
        self.plt2DSetBox.hide()
        self.plt1DSetBox.hide()
        self.plt2DSetLbl.hide()
        self.plt1DSetLbl.hide()
        
        self.plot2DInfo = {}
        self.plot1DInfo = {}
        self.num1Plots, self.num2Plots = 0, 0
        
        self.popAxes(self.reactor)
        
        
    def moveDefault(self):
        self.move(400,25)
        
    def set1D(self):
        self.plt1DSetBox.stateChanged.disconnect(self.set1D)
        self.plt2DSetBox.stateChanged.disconnect(self.set1D)        
        if self.dataSetType == 2:
            self.dataSetType = 1
            self.plt1DSetBox.setCheckState(2)
            self.plt2DSetBox.setCheckState(0)
        elif self.dataSetType == 1:
            self.dataSetType = 2
            self.plt2DSetBox.setCheckState(2)
            self.plt1DSetBox.setCheckState(0)
        self.plt1DSetBox.stateChanged.connect(self.set1D)
        self.plt2DSetBox.stateChanged.connect(self.set1D)

            
    def editLabel1(self, r, c):
        if c == 0:
            self.backtext1 = str(self.onePlots.item(r, c).text())
            item = self.onePlots.item(r, c)
            item.setText('')
            self.onePlots.editItem(self.onePlots.item(r, c))

    def editLabel2(self, r, c):
        if c == 0:
            self.backtext2 = str(self.twoPlots.item(r, c).text())
            item = self.twoPlots.item(r, c)
            item.setText('')
            self.twoPlots.editItem(self.twoPlots.item(r, c))

    def setupTables(self):
        
        self.onePlots.horizontalHeader().hide()
        self.onePlots.verticalHeader().hide()
        self.twoPlots.horizontalHeader().hide()
        self.twoPlots.verticalHeader().hide()
        
        self.onePlots.cellDoubleClicked.connect(self.editLabel1)
        self.twoPlots.cellDoubleClicked.connect(self.editLabel2)
        self.onePlots.itemSelectionChanged.connect(lambda: self.formatTable(1))
        self.twoPlots.itemSelectionChanged.connect(lambda: self.formatTable(2))

        self.onePlots.setColumnCount(4)
        self.twoPlots.setColumnCount(4)
        
        self.onePlots.insertRow(0)
        self.twoPlots.insertRow(0)
        num1, num2, lbl1, lbl2, x1, y1, x2, y2, z2 = QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem()
        
        headers = [lbl1, x1, y1, lbl2, x2, y2, z2]
        
        num1.setText('Plot')
        num1.setForeground(QBrush(QColor(131,131,131)))
        num2.setText('Plot')
        num2.setForeground(QBrush(QColor(131,131,131)))
        
        lbl1.setText('Plot Title')
        lbl1.setForeground(QBrush(QColor(131,131,131)))
        lbl2.setText('Plot Title')
        lbl2.setForeground(QBrush(QColor(131,131,131)))
        
        x1.setText('X Axis')
        x1.setForeground(QBrush(QColor(131,131,131)))
        y1.setText('Y Axis')
        y1.setForeground(QBrush(QColor(131,131,131)))
        
        x2.setText('X Axis')
        x2.setForeground(QBrush(QColor(131,131,131)))
        y2.setText('Y Axis')
        y2.setForeground(QBrush(QColor(131,131,131)))
        z2.setText('Z Axis')
        z2.setForeground(QBrush(QColor(131,131,131)))
        
        for ii in range(0, 3):
            self.onePlots.setItem(0, ii, headers[ii])
            self.onePlots.item(0, ii).setFont(QtGui.QFont("MS Shell Dlg 2",weight=QtGui.QFont.Bold))
            self.onePlots.item(0, ii).setFlags(QtCore.Qt.NoItemFlags)
        for ii in range(3, 7):
            self.twoPlots.setItem(0, ii - 3, headers[ii])
            self.twoPlots.item(0, ii - 3).setFont(QtGui.QFont("MS Shell Dlg 2",weight=QtGui.QFont.Bold))
            self.twoPlots.item(0, ii - 3).setFlags(QtCore.Qt.NoItemFlags)
            
        self.onePlots.setColumnWidth(0, 98)
        self.onePlots.setColumnWidth(1, 100)
        self.onePlots.setColumnWidth(2, 100)
        self.onePlots.setColumnWidth(3, 100)
        
        self.twoPlots.setColumnWidth(1, 100)
        self.twoPlots.setColumnWidth(2, 100)
        self.twoPlots.setColumnWidth(3, 100)
        self.twoPlots.setColumnWidth(0, 98)
        
    def formatTable(self, num = None):
        if num == 1:
            for c in range(0, 4):
                for r in range(0, self.onePlots.rowCount()):
                    if self.onePlots.item(r, c) != None:
                        self.onePlots.item(r, c).setBackground(QtGui.QColor(0,0,0))
                        self.onePlots.item(r, c).setForeground(QBrush(QColor(131,131,131)))
                        if c != 0:
                            self.onePlots.item(r, c).setFlags(QtCore.Qt.NoItemFlags)
                        elif c == 0 and r != 0:
                            
                            item = self.onePlots.item(r, c)
                            if item.text() == '':
                                item.setText(self.backtext1)
                            item.setBackground(QBrush(QColor(100,100,150)))
                            item.setForeground(QBrush(QColor(0,0,0)))
        elif num ==2:
            for c in range(0, 4):
                for r in range(0, self.twoPlots.rowCount()):
                    if self.twoPlots.item(r, c) != None:
                        self.twoPlots.item(r, c).setBackground(QtGui.QColor(0,0,0))
                        self.twoPlots.item(r, c).setForeground(QBrush(QColor(131,131,131)))    
                        if c != 0:
                            self.twoPlots.item(r, c).setFlags(QtCore.Qt.NoItemFlags)
                        elif c == 0 and r != 0:
                            
                            item = self.twoPlots.item(r, c)
                            if item.text() == '':
                                item.setText(self.backtext2)
                            item.setBackground(QBrush(QColor(100,100,150)))
                            item.setForeground(QBrush(QColor(0,0,0)))
        else:
            pass
        self.formFlag = True
        
    def add1DPlot(self):
        lbl, xAx, yAx = QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem()
        self.onePlots.insertRow(self.onePlots.rowCount())
        
        self.num1Plots += 1
        title = 'Plot '+ str(self.num1Plots)
        
        lbl.setText(title)
        xAx.setText(self.x1.currentText())
        yAx.setText(self.y1.currentText())
        
        newItems = [lbl, xAx, yAx]
        
        plotInfo = {'title': title,
                    'x axis': str(self.x1.currentText()), 
                    'x index': self.x1.currentIndex(),
                    'y axis': str(self.y1.currentText()), 
                    'y index': self.y1.currentIndex()
                    }
        
        self.plot1DInfo[self.num1Plots] = plotInfo
        
        for i in range(0, 3):
            self.onePlots.setItem(self.onePlots.rowCount() - 1, i, newItems[i])
        self.formatTable(1)
        
    def add2DPlot(self):
        lbl, xAx, yAx, zAx = QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem(), QtGui.QTableWidgetItem()
        self.twoPlots.insertRow(self.twoPlots.rowCount())
        
        self.num2Plots += 1
        title = 'Plot '+ str(self.num2Plots)
        
        lbl.setText(title)
        xAx.setText(self.x2.currentText())
        yAx.setText(self.y2.currentText())
        zAx.setText(self.z2.currentText())
        
        newItems = [lbl, xAx, yAx, zAx]
        
        plotInfo = {'title': title,
                    'x axis': str(self.x2.currentText()), 
                    'x index': self.x2.currentIndex(),
                    'y axis': str(self.y2.currentText()), 
                    'y index': self.y2.currentIndex(),
                    'z axis': str(self.z2.currentText()), 
                    'z index': self.z2.currentIndex(),
                    }
        
        self.plot2DInfo[self.num2Plots] = plotInfo
        
        for i in range(0, 4):
            self.twoPlots.setItem(self.twoPlots.rowCount() - 1, i, newItems[i])
        self.formatTable(2)
        
    def rmv1DPlot(self):
        r = int(self.onePlots.currentRow())
        self.plot1DInfo.pop(r, None)
        self.onePlots.removeRow(r)
        if r != self.num1Plots:
            for i in range(r+1, self.num1Plots+1):
                self.plot1DInfo[i - 1] = self.plot1DInfo.pop(i)
        self.num1Plots -= 1
        
    def rmv2DPlot(self):
        r = int(self.twoPlots.currentRow())
        self.plot2DInfo.pop(r, None)
        self.twoPlots.removeRow(r)
        if r != self.num2Plots:
            for i in range(r+1, self.num2Plots+1):
                self.plot2DInfo[i - 1] = self.plot2DInfo.pop(i)
        self.num2Plots -= 1
        
    @inlineCallbacks
    def popAxes(self, c = None):
        yield self.dv.cd(self.dir)
        yield self.dv.open(self.file)
        vars = yield self.dv.variables()
        self.indVars = vars[0]
        self.depVars = vars[1]
        
        for var in self.indVars:
            self.x2.addItem(str(var[0]))
            self.y2.addItem(str(var[0]))
            self.x1.addItem(str(var[0]))
            
            self.z2.addItem(str(var[0]))
            self.y1.addItem(str(var[0]))
        
        for var in self.depVars:
            self.x2.addItem(str(var[0]))
            self.y2.addItem(str(var[0]))
            self.x1.addItem(str(var[0]))

            self.z2.addItem(str(var[0]))
            self.y1.addItem(str(var[0]))
            
    @inlineCallbacks
    def initPlot(self, c = None):
        
        for r in range(1, self.onePlots.rowCount()):
            self.plot1DInfo[r]['title'] = str(self.onePlots.item(r, 0).text())
            self.plot1DInfo[str(self.onePlots.item(r, 0).text())] = self.plot1DInfo.pop(r)
        for r in range(1, self.twoPlots.rowCount()):
            self.plot2DInfo[r]['title'] = str(self.twoPlots.item(r, 0).text())
            self.plot2DInfo[str(self.twoPlots.item(r, 0).text())] = self.plot2DInfo.pop(r)
        if self.fresh == 0 or self.fresh == 1:
            try:
                self.extents, self.pxsize = {},{}
                
                #As long as plots of some kind are being request
                if self.plot2DInfo != {} or self.plot1DInfo != {}:
                    #First check if the extents are in datavault
                    #Note, this requires having added the extents and points
                    #parameters into the datavault file with format
                    #"axisname_rng" and "axisname_pnts"
                    #For example, for capacitance we have n0 and p0, these would be
                    #n0_rng and n_pnts, and p0_rng and p0_pnts
                    
                    params = yield self.dv.get_parameters()
                    
                    if params != None:
                        params = dict((x,y) for x,y in params)
                        for plot2D in self.plot2DInfo:
                            x_axis = self.plot2DInfo[plot2D]['x axis']
                            y_axis = self.plot2DInfo[plot2D]['y axis']
                            
                            x_rng, x_pnts = x_axis + '_rng', x_axis + '_pnts'
                            y_rng, y_pnts = y_axis + '_rng', y_axis + '_pnts'
                            
                            if x_rng in params and x_pnts in params:
                                self.plot2DInfo[plot2D]['x range'] = params[x_rng]
                                self.plot2DInfo[plot2D]['x points'] = params[x_pnts]
                            if y_rng in params and y_pnts in params:
                                self.plot2DInfo[plot2D]['y range'] = params[y_rng]
                                self.plot2DInfo[plot2D]['y points'] = params[y_pnts]
                                
                        for plot1D in self.plot1DInfo:
                            x_axis = self.plot1DInfo[plot1D]['x axis']
                            x_rng, x_pnts = x_axis + '_rng', x_axis + '_pnts'
                            
                            if x_rng in params and x_pnts in params:
                                self.plot1DInfo[plot1D]['x range'] = params[x_rng]
                                self.plot1DInfo[plot1D]['x points'] = params[x_pnts]
                        
                        
                    #See which axes do not have any associated extents. 
                    #Prompt for those manually
                    
                    #First determine which axes extents are needed
                    needExtents = []
                    for plot2D in self.plot2DInfo:
                        if not 'x range' in self.plot2DInfo[plot2D]:
                            if not self.plot2DInfo[plot2D]['x axis'] in needExtents:
                                needExtents.append(self.plot2DInfo[plot2D]['x axis'])
                        if not 'y range' in self.plot2DInfo[plot2D]:
                            if not self.plot2DInfo[plot2D]['y axis'] in needExtents:
                                needExtents.append(self.plot2DInfo[plot2D]['y axis'])              
                    
                    for plot1D in self.plot1DInfo:
                        if not 'x range' in self.plot1DInfo[plot1D]:
                            if not self.plot1DInfo[plot1D]['x axis'] in needExtents:
                                needExtents.append(self.plot1DInfo[plot1D]['x axis'])
                    

                    if needExtents != []:
                        #If nonzero number needed, prompt for them manually
                        extPrompt = extentPrompt(self.reactor, needExtents, 450, 25, self)
                        extPrompt.exec_()

                    if needExtents == [] or extPrompt.accepted:
                        if needExtents != []:
                            for plot2D in self.plot2DInfo:
                                for key in self.extents:
                                    if key == self.plot2DInfo[plot2D]['x axis']:
                                        self.plot2DInfo[plot2D]['x range'] = self.extents[key]
                                        self.plot2DInfo[plot2D]['x points'] = self.pxsize[key]
                                    if key == self.plot2DInfo[plot2D]['y axis']:
                                        self.plot2DInfo[plot2D]['y range'] = self.extents[key]
                                        self.plot2DInfo[plot2D]['y points'] = self.pxsize[key]
                                        
                            for plot1D in self.plot1DInfo:
                                for key in self.extents:
                                    if key == self.plot1DInfo[plot1D]['x axis']:
                                        self.plot1DInfo[plot1D]['x range'] = self.extents[key]
                                        self.plot1DInfo[plot1D]['x points'] = self.pxsize[key]
                        
                        print("2D Info: ", self.plot2DInfo)
                        print("1D Info: ", self.plot1DInfo)
                        if self.fresh == 0 or self.fresh == 1:
                            yield self.mainWin.openLivePlots(copy.copy(self.plot2DInfo), copy.copy(self.plot1DInfo), copy.copy(self.fresh))
                            yield self.sleep(0.5)
                            self.close()
            except Exception as inst:
                print("Following error was thrown: ")
                print(str(inst))
                print("Error thrown on line: ")
                print(sys.exc_info()[2]) 
        elif self.fresh == 2:
            print("2D Info: ", self.plot2DInfo)
            print("1D Info: ", self.plot1DInfo)
            if self.plot2DInfo == {} and self.plot1DInfo == {}:
                pass
            elif self.plot1DInfo == {}:
                yield self.mainWin.openSavedPlots(copy.copy(self.file), copy.copy(self.dir), copy.copy(self.plot2DInfo), 2)
            elif self.plot2DInfo == {}:
                yield self.mainWin.openSavedPlots(copy.copy(self.file), copy.copy(self.dir), copy.copy(self.plot1DInfo), 1)
            else:
                pass
            yield self.sleep(0.5)
            self.close()

            
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
            
    def closeWindow(self):
        
        self.close()

    def closeEvent(self, e):
        self.close()

class dirExplorer(QtGui.QDialog, Ui_DirExp):
    def __init__(self, reactor, status, parent = None):
        super(dirExplorer, self).__init__(parent)
        QtGui.QDialog.__init__(self)

        self.reactor = reactor
        self.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(guiIconPath))
        self.setWindowIcon(icon)
        self.moveDefault()
        
        self.mainWin = parent
        self.status = status
        
        self.connect(self.reactor)
        

        self.selectedFile = ''
        self.selectedDir = ['']
        self.currentDir = ['']

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.back.clicked.connect(lambda: self.backUp(self.reactor))
        self.home.clicked.connect(lambda: self.goHome(self.reactor))
        self.addDir.clicked.connect(lambda: self.makeDir(self.reactor))
        self.select.clicked.connect(lambda: self.selectFile(self.reactor))
        self.cancel.clicked.connect(self.closeWindow)
        
        
    def moveDefault(self):
        self.move(400,25)


    @inlineCallbacks
    def connect(self, c = None):
        from labrad.wrappers import connectAsync
        try:
            self.cxn = yield connectAsync(name = 'dirExplorer')
            self.dv = yield self.cxn.data_vault
        except:
            print("Either no LabRad connection or DataVault connection.")
        self.popDirs(self.reactor)
        

    @inlineCallbacks
    def popDirs(self, c = None):
        self.dirList.clear()
        self.fileList.clear()
        l = yield self.dv.dir()
        for i in l[0]:
            self.dirList.addItem(i)
            self.dirList.item(self.dirList.count() - 1).setForeground(QBrush(QColor(131,131,131)))
        for i in l[1]:
            self.fileList.addItem(i)
            self.fileList.item(self.fileList.count() - 1).setForeground(QBrush(QColor(131,131,131)))
        if self.currentDir[-1] == '':
            
            self.dirName.setText('Root')
            self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")
        else:
            
            self.dirName.setText(self.currentDir[-1])
            self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")
        if self.currentDir[-1] != '':
            self.currentDrc.setText(self.currentDir[-1])
        else:
            self.currentDrc.setText('(Root)')
        

    @inlineCallbacks
    def updateDirs(self, subdir):
        subdir = str(subdir.text())
        self.currentDir.append(subdir)
        yield self.dv.cd(subdir, False)
        yield self.popDirs(self.reactor)

    @inlineCallbacks
    def backUp(self, c = None):
        if self.currentDir[-1] == '':
            pass
        else:
            direct = yield self.dv.cd()
            back = direct[0:-1]
            self.currentDir.pop(-1)
            yield self.dv.cd(back)
            yield self.popDirs(self.reactor)

    @inlineCallbacks
    def goHome(self, c = None):
        yield self.dv.cd('')
        self.currentDir = ['']
        yield self.popDirs(self.reactor)

    @inlineCallbacks
    def makeDir(self, c = None):
        direct, ok = QtGui.QInputDialog.getText(self, "Make directory", "Directory Name: " )
        if ok:
            yield self.dv.mkdir(str(direct))
            yield self.popDirs(self.reactor)
            
            
    @inlineCallbacks
    def selectFile(self, c = None):
        self.mainWin.setListenDir(self.currentDrc.text(), self.currentDir)
        yield self.sleep(0.5)
        yield self.mainWin.initListener(self.reactor)
        self.close()
        
    def sleep(self,secs):
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

        
        
    def closeWindow(self):
        if self.status == False:
            self.mainWin.listen.setEnabled(True)
        else:
            self.mainWin.changeDir.setEnabled(True)
        self.close()

    def closeEvent(self, e):
        if self.status == False:
            self.mainWin.listen.setEnabled(True)
        else:
            self.mainWin.changeDir.setEnabled(True)

class dataVaultExplorer(QtGui.QDialog, Ui_DataVaultExp):
    def __init__(self, reactor, source, listenDir, parent = None):
        super(dataVaultExplorer, self).__init__(parent)
        QtGui.QDialog.__init__(self)

        self.reactor = reactor
        self.source = source
        self.listenDir = listenDir
        self.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(guiIconPath))
        self.setWindowIcon(icon)
        self.moveDefault()
        
        self.mainWin = parent


        self.connect(self.reactor)
        

        self.selectedFile = ''
        self.selectedDir = ['']
        self.currentDir = self.listenDir
        print("Setting directory: ", self.currentDir)

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.fileList.itemClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.fileSelectselectFile)
        self.back.clicked.connect(lambda: self.backUp(self.reactor))
        self.home.clicked.connect(lambda: self.goHome(self.reactor))
        self.addDir.clicked.connect(lambda: self.makeDir(self.reactor))
        self.select.clicked.connect(self.selectFile)
        self.cancel.clicked.connect(self.closeWindow)
        
    def moveDefault(self):
        self.move(400,25)

    @inlineCallbacks
    def connect(self, c = None):
        from labrad.wrappers import connectAsync
        try:
            self.cxn = yield connectAsync(name = 'dvExplorer')
            self.dv = yield self.cxn.data_vault
        except:
            print("Either no LabRad connection or DataVault connection.")
        self.popDirs(self.listenDir, self.reactor)

    @inlineCallbacks
    def popDirs(self, initDir = None, c = None):
        self.dirList.clear()
        self.fileList.clear()
        if initDir != None:
            yield self.dv.cd(initDir)
        l = yield self.dv.dir()
        for i in l[0]:
            self.dirList.addItem(i)
            self.dirList.item(self.dirList.count() - 1).setForeground(QBrush(QColor(131,131,131)))
        for i in l[1]:
            self.fileList.addItem(i)
            self.fileList.item(self.fileList.count() - 1).setForeground(QBrush(QColor(131,131,131)))
        if self.currentDir[-1] == '':
            
            self.dirName.setText('Root')
            self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")
        else:
            
            self.dirName.setText(self.currentDir[-1])
            self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")


    @inlineCallbacks
    def updateDirs(self, subdir):
        subdir = str(subdir.text())
        self.currentDir.append(subdir)
        yield self.dv.cd(subdir, False)
        yield self.popDirs(None, self.reactor)

    @inlineCallbacks
    def backUp(self, c = None):
        if self.currentDir[-1] == '':
            pass
        else:
            direct = yield self.dv.cd()
            back = direct[0:-1]
            self.currentDir.pop(-1)
            yield self.dv.cd(back)
            yield self.popDirs(None, self.reactor)

    @inlineCallbacks
    def goHome(self, c = None):
        yield self.dv.cd('')
        self.currentDir = ['']
        yield self.popDirs(None, self.reactor)

    @inlineCallbacks
    def makeDir(self, c = None):
        direct, ok = QtGui.QInputDialog.getText(self, "Make directory", "Directory Name: " )
        if ok:
            yield self.dv.mkdir(str(direct))
            yield self.popDirs(None, self.reactor)

    def fileSelectselectFile(self):
        self.fileSelect()
        self.selectFile()

    def fileSelect(self):
        file = self.fileList.currentItem()
        self.selectedFile = file.text()
        
        self.selectedDir = self.currentDir
        self.currentFile.setText(file.text())
        
    def selectFile(self):
        if self.source == 'saved':
            if self.selectedFile != '':
                self.savedPlot = plotSetup(self.reactor,self.selectedFile, self.selectedDir, self.cxn, self.dv, 2, self.mainWin)
                self.accept()
                self.savedPlot.show()
            else:
                pass
        elif self.source == 'live':
            if self.selectedFile != '':
                self.mainWin.listenPlotFile = str(self.selectedFile)
                self.mainWin.listenTo = self.selectedDir
                self.livePlot = plotSetup(self.reactor,self.selectedFile, self.selectedDir, self.cxn, self.dv, 1, self.mainWin)
                self.accept()
                self.livePlot.show()
            else:
                pass
        else:
            pass
            
    def closeWindow(self):
        self.close()

    def closeEvent(self, e):
        self.close()

class helpTextWindow(QtGui.QMainWindow, Ui_HelpWindow):
    def __init__(self, parent = None):
        super(helpTextWindow, self).__init__(parent)
        QtGui.QMainWindow.__init__(self)
        self.window = parent
        self.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(guiIconPath))
        self.setWindowIcon(icon)
        
    def closeEvent(self, e):
        self.window.helpBtn.setEnabled(True)
        self.close()
        
if __name__ == "__main__":
    global app
    app = QtGui.QApplication([])
    import qt5reactor
    qt5reactor.install()
    from twisted.internet import reactor
    window = dvPlotter(reactor)
    window.show()
    reactor.run()
