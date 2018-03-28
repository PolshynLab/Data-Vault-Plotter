from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import copy
import datetime as dt
import subprocess
from subprocess import *



path = sys.path[0]

sys.path.append(sys.path[0] + '\Resources')
import dvPlotterResources_rc

mainWinGUI = path + r"\startPlotter.ui"
plotExtentGUI = path + r"\extentPrompt.ui"
dvExplorerGUI = path + r"\dvExplorer.ui"
dirExplorerGUI = path + r"\dirExplorer.ui"
editInfoGUI = path + r"\editDatasetInfo.ui"
plotSetupUI = path + r"\plotSetup.ui"

Ui_MainWin, QtBaseClass = uic.loadUiType(mainWinGUI)
Ui_ExtPrompt, QtBaseClass = uic.loadUiType(plotExtentGUI)
Ui_DataVaultExp, QtBaseClass = uic.loadUiType(dvExplorerGUI)
Ui_DirExp, QtBaseClass = uic.loadUiType(dirExplorerGUI)
Ui_EditDataInfo, QtBaseClass = uic.loadUiType(editInfoGUI)
Ui_PlotSetup, QtBaseClass = uic.loadUiType(plotSetupUI)

ID_NEWDATA = 999

class dvPlotter(QtGui.QMainWindow, Ui_MainWin):
	def __init__(self, reactor, parent = None):
		super(dvPlotter, self).__init__(parent)
		QtGui.QMainWindow.__init__(self)
		
		self.setupUi(self)
		self.reactor = reactor
		
		self.moveDefault()
		self.initReact(self.reactor)
		
		self.plotSavedBtn.clicked.connect(self.plotSavedDataFunc)
		self.listen.clicked.connect(self.setupListener)
		self.closeWin.clicked.connect(self.closePlotter)
		self.plotLive.clicked.connect(self.plotLiveData)
		
		self.changeDir.setEnabled(False)
		
		self.listStatus = False
		
		self.allowPlot = False
		
		self.listenTo = ['']
		
	def moveDefault(self):
		self.move(25,25)
		
	@inlineCallbacks
	def initReact(self, c):
		from labrad.wrappers import connectAsync
		try:
			self.cxn = yield connectAsync(name = 'dvPlotter')
			self.dv = yield self.cxn.data_vault
			self.man = yield self.cxn.manager
			yield self.man.expire_all()
		except:
			print 'Either no LabRad connection or DataVault connection.'
		
	@inlineCallbacks
	def initListener(self, c):
		if self.listStatus == False:
			self.listen.clicked.disconnect()
			self.changeDir.clicked.connect(self.setupListener)
		
		try:
			yield self.dv.signal__new_dataset(00001)
			yield self.dv.addListener(listener=self.open_dataset, source=None, ID=00001)

			yield self.dv.cd(self.listenTo)

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
			print 'Either no LabRad connection or DataVault connection.'

	@inlineCallbacks
	def update(self, c):
		yield self.sleep(0.5)
		
	def open_dataset(self, c, signal):
		print signal
		self.listenPlotFile =  signal
		setupListenPlot = plotSetup(self.reactor, signal, self.listenTo, self.cxn, self.dv, 0, self)
		setupListenPlot.show()
	
	def update_params(self):
		pass
		
	def setListenDir(self, dir, list):
		self.listenDir.setText(str(dir))
		self.listenDir.setStyleSheet("QLabel#listenDir {color: rgb(131,131,131);}")
		self.listenTo = list
		
	@inlineCallbacks
	def openLivePlots(self, twoPlots, onePlots, fresh, c = None):
		try: 
			x0, y0 = 450, 25
			for plot in twoPlots:
				self.new2DPlot = plot2DWindow(self.reactor, twoPlots[plot], self.listenTo, self.listenPlotFile, x0, y0, fresh, self)
				self.new2DPlot.show()
				yield self.sleep(1)
				y0 += 50
			x0, y0 = 1250, 25
			for plot in onePlots:
				self.new1DPlot = plot1DWindow(self.reactor, onePlots[plot], self.listenTo, self.listenPlotFile, x0, y0, fresh, self)
				self.new1DPlot.show()
				yield self.sleep(1)
				y0 += 50
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno
		self.allowPlot = True
			
	def openSavedPlots(self, file, dir, twoPlots):
		x0, y0 = 450, 25
		for index in range(0, len(twoPlots)):
			self.thing = plotSavedWin(self.reactor, file, dir, twoPlots[index], x0, y0)
			self.thing.show()	 
			y0 += 50

	def plotLiveData(self):
		dvExplorer = dataVaultExplorer(self.reactor, 'live', self)
		dvExplorer.show()
		
	def setupListener(self):
		self.listen.setEnabled(False)
		self.changeDir.setEnabled(False)
		drcExplorer = dirExplorer(self.reactor, self.listStatus, self)
		drcExplorer.show()
		
	def plotSavedDataFunc(self):

		dvExplorer = dataVaultExplorer(self.reactor, 'saved', self)
		dvExplorer.show()
		
	def sleep(self,secs):
		d = Deferred()
		self.reactor.callLater(secs,d.callback,'Sleeping')
		return d
		
	def closePlotter(self, e):
		self.close()

	def closeEvent(self, e):
		self.reactor.stop()
		self.cxn.disconnect()
		print 'Reactor shut down.'
		
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
		min.setTextColor(QtGui.QColor(131,131,131))
		max.setText('Maximum Value')
		max.setTextColor(QtGui.QColor(131,131,131))
		pts.setText('Number of Points')
		pts.setTextColor(QtGui.QColor(131,131,131))

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
			print errCell
			for ii in range(0, len(errCell)):
				self.extTable.item(errCell[ii][0], errCell[ii][1]).setBackgroundColor(QtGui.QColor(250,190,160))
				
	def closeEvent(self, e):
		self.reject()
		
class plot2DWindow(QtGui.QDialog):
	def __init__(self, reactor, plotInfo, dir, file, x0, y0, fresh, parent = None):
		try: 
			super(plot2DWindow, self).__init__(parent)
			self.plotInfo = plotInfo
			self.reactor = reactor
			self.mainWin = parent
			self.dir = dir
			self.fileName = file
			#fresh specifies if the dataset to be plotted already has data (1) or is empty (0)
			self.fresh = fresh
			
			self.xIndex = self.plotInfo['x index']
			self.yIndex = self.plotInfo['y index']
			self.zIndex = self.plotInfo['z index']
			
			print '------------------------------'
			print 'Plot parameters: '
			print file
			print plotInfo
			print fresh
			print dir

			self.pX, self.pY = x0, y0
			self.extents = [self.plotInfo['x range'][0], self.plotInfo['x range'][1], self.plotInfo['y range'][0], self.plotInfo['y range'][1]]
			self.pxsize = [self.plotInfo['x points'], self.plotInfo['y points']]
			

			self.Data = np.array([])
			
			self.setupPlot()
			self.setupListener(self.reactor)
			self.isData = False
			
			
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
		
	@inlineCallbacks
	def setupListener(self, c):
		try: 
			cxnName = 'plot' + str(self.id)
			from labrad.wrappers import connectAsync
			self.cxn = yield connectAsync(name = cxnName)
			self.dv = yield self.cxn.data_vault
			yield self.dv.cd(self.dir)
			yield self.dv.open(self.fileName)

			yield self.addListen(self.reactor)
			newData = yield self.dv.get()

			if len(newData) != 0:
				inx = np.delete(np.arange(0, len(newData[0])), [self.xIndex, self.yIndex, self.zIndex])
				newData = np.delete(np.asarray(newData), inx, axis = 1)
				x_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.xIndex)[0][0]
				y_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.yIndex)[0][0]
				z_ind = np.where(np.sort([self.xIndex, self.yIndex, self.zIndex]) == self.zIndex)[0][0]
				newData[::, x_ind] = np.digitize(newData[::, x_ind], self.xBins) - 1
				newData[::, y_ind] = np.digitize(newData[::, y_ind], self.yBins) - 1


				for pt in newData:
					self.plotData[int(pt[x_ind]), int(pt[y_ind])] = pt[z_ind]
				
				self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[np.min([self.extents[0],self.extents[1]]), np.min([self.extents[2],self.extents[3]])],scale=[self.xscale, self.yscale])
				self.isData = True

			
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
	@inlineCallbacks
	def addListen(self, c):
		yield self.dv.signal__data_available(self.id)
		yield self.dv.addListener(listener=self.updatePlot, ID=self.id)
		print '2D listener added with ID: ' + str(self.id)


		
	def setupPlot(self):
		global ID_NEWDATA
		print 'setting up plot............', ID_NEWDATA
		self.id = ID_NEWDATA
		ID_NEWDATA = ID_NEWDATA + 1
		try: 
			self.resize(700,550)
			self.move(self.pX,self.pY)
			p = self.palette()
			p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
			self.setPalette(p)
		
			self.layout = QtGui.QGridLayout(self)
			
			self.viewBig = pg.PlotItem(name = "Plot", title = self.plotInfo['title'])
			self.viewBig.showAxis('top', show = True)
			self.viewBig.showAxis('right', show = True)
			self.viewBig.setLabel('left', self.plotInfo['y axis'])
			self.viewBig.setLabel('bottom', self.plotInfo['x axis'])
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

			self.layout.addWidget(self.mainPlot, *(0,0))
			self.setLayout(self.layout)
			
			self.plotData = np.zeros([self.pxsize[0], self.pxsize[1]])
			
			self.xscale, self.yscale = np.absolute((self.extents[1] - self.extents[0])/self.pxsize[0]), np.absolute((self.extents[3] - self.extents[2])/self.pxsize[1])
			self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[np.min([self.extents[0],self.extents[1]]), np.min([self.extents[2],self.extents[3]])],scale=[self.xscale, self.yscale])
			
			if self.extents[0] < self.extents[1]:
				self.xBins = np.linspace(self.extents[0] - 0.5 * self.xscale, self.extents[1] + 0.5 * self.xscale, self.pxsize[0]+1)
			else:
				self.xBins = np.linspace(self.extents[0] + 0.5 * self.xscale, self.extents[1] - 0.5 * self.xscale, self.pxsize[0]+1)
			
			if self.extents[2] < self.extents[3]:
				self.yBins = np.linspace(self.extents[2] - 0.5 * self.yscale, self.extents[3] + 0.5 * self.yscale, self.pxsize[1]+1)
			else:
				self.yBins = np.linspace(self.extents[2] + 0.5 * self.yscale, self.extents[3] - 0.5 * self.yscale, self.pxsize[1]+1)
		
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
			
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
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
	@inlineCallbacks
	def plotMore(self, newData, x_ind, y_ind, z_ind, c):
		yield self.sleep(0.1)

		for pt in newData:
				self.plotData[int(pt[x_ind]), int(pt[y_ind])] = pt[z_ind]

		self.mainPlot.setImage(self.plotData, autoRange = False , autoLevels = False, pos=[np.min([self.extents[0],self.extents[1]]), np.min([self.extents[2],self.extents[3]])],scale=[self.xscale, self.yscale])

		
		

	def closeEvent(self, e):
		self.cxn.disconnect()
		self.close()

class plot1DWindow(QtGui.QDialog):
	def __init__(self, reactor, plotInfo, dir, file, x0, y0, fresh, parent = None):
		super(plot1DWindow, self).__init__(parent)

		self.reactor = reactor
		self.mainWin = parent
		self.dir = dir
		self.fileName = file
		self.plotInfo = plotInfo
		self.fresh = fresh
		
		self.pX, self.pY = x0, y0
		
		self.isData = False
		self.Data = np.array([])
		
		self.xIndex = self.plotInfo['x index']
		self.yIndex = self.plotInfo['y index']
		
		self.extents = [self.plotInfo['x range'][0], self.plotInfo['x range'][1]]
		self.pxsize = self.plotInfo['x points']
		
		self.setupPlot()
		self.setupListener(self.reactor)
		
	def setupPlot(self):
		global ID_NEWDATA
		print 'setting up plot............', ID_NEWDATA
		self.id = ID_NEWDATA
		ID_NEWDATA = ID_NEWDATA + 1
		
		self.colorWheel = [(0,114,189), (216,83,25), (237,177,32), (126,47,142), (119,172,48)]
		self.penColor = self.colorWheel[int(self.id)%5]
		self.resize(600,320)
		self.move(self.pX,self.pY)
		p = self.palette()
		p.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
		self.setPalette(p)
	
		self.layout = QtGui.QGridLayout(self)
		
		self.plot1D = pg.PlotWidget(title = self.plotInfo['title'])
		self.plot1D.showAxis('right', show = True)
		self.plot1D.showAxis('top', show = True)
		self.plot1D.setLabel('left', self.plotInfo['y axis'])
		self.plot1D.setLabel('bottom', self.plotInfo['x axis'])
		self.plot1D.enableAutoRange(enable = True)
		
		self.layout.addWidget(self.plot1D, *(0,0))
		self.setLayout(self.layout)
		
		self.xScale = np.absolute((self.extents[1] - self.extents[0])/ self.pxsize)
		if self.extents[0] < self.extents[1]:
			self.xBins = np.linspace(self.extents[0] - 0.5*self.xScale, self.extents[1] + 0.5*self.xScale, self.pxsize + 1)
		else:
			self.xBins = np.linspace(self.extents[0] + 0.5*self.xScale, self.extents[1] - 0.5*self.xScale, self.pxsize + 1)
	
	@inlineCallbacks
	def setupListener(self, c):
		try: 
			cxnName = 'plot' + str(self.id)
			from labrad.wrappers import connectAsync
			self.cxn = yield connectAsync(name = cxnName)
			self.dv = yield self.cxn.data_vault
			yield self.dv.cd(self.dir)
			yield self.dv.open(self.fileName)

			yield self.addListen(self.reactor)

			newData = yield self.dv.get()

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
			self.plot1D.plot(x = xVals, y = yVals, pen =pg.mkPen(color=self.penColor))
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
			
	@inlineCallbacks
	def addListen(self, c):
		yield self.dv.signal__data_available(self.id)
		yield self.dv.addListener(listener=self.updatePlot, ID=self.id)
		print '1D listener added with ID: ' + str(self.id)

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
					xVals = self.Data[p[-1][0]+1::, x_ind]
					yVals = self.Data[p[-1][0]+1::, y_ind]
				else:
					xVals, yVals = self.Data[::, x_ind], self.Data[::, y_ind]
				
			else:
				xVals, yVals = self.Data[::, x_ind], self.Data[::, y_ind]

			self.plot1D.clear()
			self.plot1D.plot(x = xVals, y = yVals, pen =pg.mkPen(color=self.penColor))
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
	def sleep(self,secs):
		d = Deferred()
		self.reactor.callLater(secs,d.callback,'Sleeping')
		return d

	def closeEvent(self, e):
		self.cxn.disconnect()
		self.close()

'''
class plotSavedWin(QtGui.QMainWindow):
	def __init__(self, reactor, file, dir, plotInfo, x0, y0, parent = None):
		super(plotSavedWin, self).__init__(parent)


		self.reactor = reactor
		self.file = str(file)
		self.dir = dir
		self.plotInfo = plotInfo
		self.mainWin = parent
		self.pX, self.pY = x0, y0
		
		self.extents = [self.plotInfo[0][2][0], self.plotInfo[0][2][1], self.plotInfo[1][2][0], self.plotInfo[1][2][1]]
		self.pxsize = [self.plotInfo[0][3], self.plotInfo[0][3]]

		self.moveDefault()
		
		self.xIndex = self.plotInfo[0][0]
		self.yIndex = self.plotInfo[1][0]
		self.zIndex = self.plotInfo[2][0]
				
		self.setupPlot()
		self.connect(self.reactor)

	def moveDefault(self):
		self.move(self.pX, self.pY)
		
	def setupPlot(self):		
		self.viewBig = pg.PlotItem(name = "Plot")
		self.viewBig.showAxis('top', show = True)
		self.viewBig.showAxis('right', show = True)
		self.viewBig.setLabel('left', self.plotInfo[1][1])
		self.viewBig.setLabel('bottom', self.plotInfo[0][1])
		self.viewBig.setAspectLocked(lock = False, ratio = 1)
		self.mainPlot = pg.ImageView(parent = self.plot2DFrame, view = self.viewBig)
		self.mainPlot.setGeometry(QtCore.QRect(0, 0, 700, 550))
		self.mainPlot.ui.menuBtn.hide()
		self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
		self.mainPlot.ui.roiBtn.hide()
		self.mainPlot.ui.menuBtn.hide()
		self.viewBig.setAspectLocked(False)
		self.viewBig.invertY(False)
		self.viewBig.setXRange(-1, 1)
		self.viewBig.setYRange(-1, 1)
		
		self.plotData = np.zeros([self.pxsize[0], self.pxsize[1]])
		
		self.xscale, self.yscale = np.absolute((self.extents[1] - self.extents[0])/self.pxsize[0]), np.absolute((self.extents[3] - self.extents[2])/self.pxsize[1])
		self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.extents[0], self.extents[2]],scale=[self.xscale, self.yscale])
		

		self.xBins = np.linspace(self.extents[0] - 0.5 * self.xscale, self.extents[1] + 0.5 * self.xscale, self.pxsize[0]+1)
		self.yBins = np.linspace(self.extents[2] - 0.5 * self.yscale, self.extents[3]+0.5 * self.yscale, self.pxsize[1]+1)

	@inlineCallbacks
	def connect(self, c):
		from labrad.wrappers import connectAsync

		self.cxnS = yield connectAsync(name = 'name')
		self.dv = yield self.cxnS.data_vault
		self.initPlot(self.reactor)
		
	@inlineCallbacks
	def initPlot(self, c):
		yield self.dv.cd(self.dir)
		yield self.dv.open(self.file)
		print 'loading data'
		self.loadData(self.reactor)

	@inlineCallbacks
	def loadData(self, c):
		getFlag = True
		self.Data = np.array([])
		while getFlag == True:
			line = yield self.dv.get(1000L)

			try:
				if len(self.Data) != 0 and len(line) > 0:
					self.Data = np.vstack((self.Data, line))						
				elif len(self.Data) == 0 and len(line) > 0:
					self.Data = np.asarray(line)
				else:
					getFlag = False
			except:
				getFlag = False
		print 'got all data'
		inx = np.delete(np.arange(0, len(self.Data[0])), [self.xIndex, self.yIndex, self.zIndex])
		self.Data = np.delete(self.Data, inx, axis = 1)
		self.Data[::, 0] = np.digitize(self.Data[::, 0], self.xBins) - 1
		self.Data[::, 1] = np.digitize(self.Data[::, 1], self.yBins) - 1
		print 'digitized'
		for pt in self.Data:
			self.plotData[int(pt[0]), int(pt[1])] = pt[2]
		print 'plotting it all'
		self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.extents[0], self.extents[2]],scale=[self.xscale, self.yscale])	
		print 'plotting complete'
		
	def sleep(self,secs):
		d = Deferred()
		self.reactor.callLater(secs,d.callback,'Sleeping')
		return d
		
	def closeEvent(self, e):
		print 'closing window why?'
'''

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
		self.moveDefault()
		
		self.formFlag = True
		self.setupTables()
	
		self.cancel.clicked.connect(self.closeWindow)
		self.ok.clicked.connect(self.initPlot)
		
		self.add1D.clicked.connect(self.add1DPlot)
		self.add2D.clicked.connect(self.add2DPlot)
		
		self.rmv1D.clicked.connect(self.rmv1DPlot)
		self.rmv2D.clicked.connect(self.rmv2DPlot)
		
		print "file: ", self.file
		print "dir: ", self.dir
		
		self.plot2DInfo = {}
		self.plot1DInfo = {}
		self.num1Plots, self.num2Plots = 0, 0
		
		self.popAxes(self.reactor)
		
	def moveDefault(self):
		self.move(400,25)
		
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
		num1.setTextColor(QtGui.QColor(131,131,131))
		num2.setText('Plot')
		num2.setTextColor(QtGui.QColor(131,131,131))
		
		lbl1.setText('Plot Title')
		lbl1.setTextColor(QtGui.QColor(131,131,131))
		lbl2.setText('Plot Title')
		lbl2.setTextColor(QtGui.QColor(131,131,131))
		
		x1.setText('X Axis')
		x1.setTextColor(QtGui.QColor(131,131,131))
		y1.setText('Y Axis')
		y1.setTextColor(QtGui.QColor(131,131,131))
		
		x2.setText('X Axis')
		x2.setTextColor(QtGui.QColor(131,131,131))
		y2.setText('Y Axis')
		y2.setTextColor(QtGui.QColor(131,131,131))
		z2.setText('Z Axis')
		z2.setTextColor(QtGui.QColor(131,131,131))
		
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
						self.onePlots.item(r, c).setTextColor(QtGui.QColor(131,131,131))
						if c != 0:
							self.onePlots.item(r, c).setFlags(QtCore.Qt.NoItemFlags)
						elif c == 0 and r != 0:
							
							item = self.onePlots.item(r, c)
							if item.text() == '':
								item.setText(self.backtext1)
							item.setBackgroundColor(QtGui.QColor(100,100,150))
							item.setTextColor(QtGui.QColor(0,0,0))
		elif num ==2:
			for c in range(0, 4):
				for r in range(0, self.twoPlots.rowCount()):
					if self.twoPlots.item(r, c) != None:
						self.twoPlots.item(r, c).setBackground(QtGui.QColor(0,0,0))
						self.twoPlots.item(r, c).setTextColor(QtGui.QColor(131,131,131))	
						if c != 0:
							self.twoPlots.item(r, c).setFlags(QtCore.Qt.NoItemFlags)
						elif c == 0 and r != 0:
							
							item = self.twoPlots.item(r, c)
							if item.text() == '':
								item.setText(self.backtext2)
							item.setBackgroundColor(QtGui.QColor(100,100,150))
							item.setTextColor(QtGui.QColor(0,0,0))
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
		vars =	  yield self.dv.variables()
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
					print params
					
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
				
				#print needExtents
				if needExtents != []:
					#If nonzero number needed, prompt for them manually
					extPrompt = extentPrompt(self.reactor, needExtents, 450, 25, self)
					extPrompt.exec_()

				#print '2D Info: ', self.plot2DInfo
				#print '1D Info: ', self.plot1DInfo
				#print self.extents
				#print self.pxsize

				if needExtents == [] or extPrompt.accepted:
					#print 'Moving on'
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
					
					print '2D Info: ', self.plot2DInfo
					print '1D Info: ', self.plot1DInfo
					if self.fresh == 0 or self.fresh == 1:
						yield self.mainWin.openLivePlots(copy.copy(self.plot2DInfo), copy.copy(self.plot1DInfo), copy.copy(self.fresh))
						yield self.sleep(0.5)
						self.close()
					elif self.fresh == 2:
						yield self.mainWin.openSavedPlots(copy.copy(self.file), copy.copy(self.dir), copy.copy(self.plot2DInfo))
						yield self.sleep(0.5)
						self.close()
						
		except Exception as inst:
			print 'Following error was thrown: '
			print inst
			print 'Error thrown on line: '
			print sys.exc_traceback.tb_lineno 
			
	def sleep(self,secs):
		d = Deferred()
		self.reactor.callLater(secs,d.callback,'Sleeping')
		return d
			
	def closeWindow(self):
		yield self.sleep(1)
		self.close()

	def closeEvent(self, e):
		print 'closing the window'
		self.close()


class dirExplorer(QtGui.QDialog, Ui_DirExp):
	def __init__(self, reactor, status, parent = None):
		super(dirExplorer, self).__init__(parent)
		QtGui.QDialog.__init__(self)

		self.reactor = reactor
		self.setupUi(self)
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
			print 'Either no LabRad connection or DataVault connection.'
		self.popDirs(self.reactor)
		

	@inlineCallbacks
	def popDirs(self, c = None):
		self.dirList.clear()
		self.fileList.clear()
		l = yield self.dv.dir()
		for i in l[0]:
			self.dirList.addItem(i)
			self.dirList.item(self.dirList.count() - 1).setTextColor(QtGui.QColor(131,131,131))
		for i in l[1]:
			self.fileList.addItem(i)
			self.fileList.item(self.fileList.count() - 1).setTextColor(QtGui.QColor(131,131,131))
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
	def __init__(self, reactor, source, parent = None):
		super(dataVaultExplorer, self).__init__(parent)
		QtGui.QDialog.__init__(self)

		self.reactor = reactor
		self.source = source
		self.setupUi(self)
		self.moveDefault()
		
		self.mainWin = parent


		self.connect(self.reactor)
		

		self.selectedFile = ''
		self.selectedDir = ['']
		self.currentDir = ['']

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
			print 'Either no LabRad connection or DataVault connection.'
		self.popDirs(self.reactor)

	@inlineCallbacks
	def popDirs(self, c = None):
		self.dirList.clear()
		self.fileList.clear()
		l = yield self.dv.dir()
		for i in l[0]:
			self.dirList.addItem(i)
			self.dirList.item(self.dirList.count() - 1).setTextColor(QtGui.QColor(131,131,131))
		for i in l[1]:
			self.fileList.addItem(i)
			self.fileList.item(self.fileList.count() - 1).setTextColor(QtGui.QColor(131,131,131))
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
				savedPlot = plotSetup(self.reactor,self.selectedFile, self.selectedDir, self.cxn, self.dv, 2, self.mainWin)
				self.accept()
				savedPlot.show()
			else:
				pass
		elif self.source == 'live':
			if self.selectedFile != '':
				self.mainWin.listenPlotFile = str(self.selectedFile)
				self.mainWin.listenTo = self.selectedDir
				print 'Doing this'
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

if __name__ == "__main__":
	app = QtGui.QApplication([])
	from qtreactor import pyqt4reactor
	pyqt4reactor.install()
	from twisted.internet import reactor
	window = dvPlotter(reactor)
	window.show()
	reactor.run()
