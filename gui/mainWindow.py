#!/usr/bin/env python
# This work is licensed under the Creative Commons Attribution-NonCommercial-
# ShareAlike 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

import re

from os.path import basename, splitext
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import materials
import plothandler
from coating import Coating
#from plottypes import plottypes
from config import Config
from utils import block_signals
from materialDialog import MaterialDialog


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.config = Config.Instance()
        self.config.load('default.cgp')
        self.materials = materials.MaterialLibrary.Instance()
        uic.loadUi('gui/ui_mainWindow.ui', self)
 
        self.plotHandle = self.pltMain.figure.add_subplot(111)
        cid = self.pltMain.figure.canvas.mpl_connect('motion_notify_event', 
            lambda ev: self.mpl_on_mouse_move(ev))

        self.update_title('untitled')
        self.config.modified.connect(self.handle_modified)

        self.empty_plotoptions_widget = self.gbPlotWidget.layout().itemAt(0).widget()
        self.plots = plothandler.collect_plots()

        self.initialise_plotoptions()
        self.initialise_materials()
        self.initialise_stack()

        self.stbStatus.showMessage('Coating GUI v1.0')

    def update_title(self, filename=None, changed=False):
        if changed:
            flag = '*'
            self.modified = True
        else:
            flag = ''
            self.modified = False
        if filename:
            self.filename = filename

        self.setWindowTitle('Coating GUI - {0}{1}'.format(self.filename, flag))

    def initialise_materials(self):
        self.materials.load_materials()
        self.update_material_list()

    def initialise_plotoptions(self):
        with block_signals(self.cbPlotType) as cb:
            cb.clear()
            for plot in self.plots.iterkeys():
                cb.addItem(plot)
            setplot = self.config.get('plot.plottype')
            cb.setCurrentIndex(cb.findText(setplot))
            self.update_plot_widget(setplot)
        
        ### return for now for widget plot options testing!!! <========================
        return

    def initialise_stack(self):
        with block_signals(self.cbSuperstrate) as cb:
            m = self.config.get('coating.superstrate')
            if cb.findText(m) < 0:
                cb.insertItem(0, m)
            cb.setCurrentIndex(cb.findText(m))
        with block_signals(self.cbSubstrate) as cb:
            m = self.config.get('coating.substrate')
            if cb.findText(m) < 0:
                cb.insertItem(0, m)
            cb.setCurrentIndex(cb.findText(m))
        self.txtLambda0.setText(str(self.config.get('coating.lambda0')))
        self.txtAOI.setText(str(self.config.get('coating.AOI')))

        layers = self.config.get('coating.layers')
        self.tblStack.setRowCount(len(layers))
        self.tblStack.setColumnCount(2)
        self.prototype = QTableWidgetItem('0')
        self.prototype.setTextAlignment(Qt.AlignRight)
        self.tblStack.setItemPrototype(self.prototype)
        with block_signals(self.tblStack) as tbl:
            for ii in range(len(layers)):
                tt = QTableWidgetItem(str(layers[ii][1]))
                it = QTableWidgetItem(str(layers[ii][0]))
                tt.setTextAlignment(Qt.AlignRight)
                it.setTextAlignment(Qt.AlignRight)
                tbl.setItem(ii,1,tt)
                tbl.setItem(ii,0,it)

    def get_layers(self):
        stack_d = []
        stack_n = []
        for row in range(self.tblStack.rowCount()):
            item_d = self.tblStack.item(row, 1)
            item_n = self.tblStack.item(row, 0)
            if item_d and item_n:
                try:
                    stack_d.append(float(item_d.text()))
                    stack_n.append(str(item_n.text()))
                except ValueError:
                    self.float_conversion_error(str(item_d.text()))
        return map(list, zip(stack_n, stack_d))

    def build_coating(self):
        substrate = str(self.cbSubstrate.currentText())
        superstrate = str(self.cbSuperstrate.currentText())
        
        return Coating(superstrate, substrate, self.get_layers())
        
    def closeEvent(self, event):
        if self.modified and not self.config.get('do_not_ask_on_quit'):
            reply = QMessageBox.question(self, 'Unsaved Changes',
                        'You have unsaved changes, do you really want to discard those and quit?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()

    def float_conversion_error(self, text):
        QMessageBox.critical(self, 'Conversion Error',
            'The input "{0}" could not be converted to a floating point number.'.format(text))
    
    ### SLOTS - GENERIC

    @pyqtSlot()
    def handle_modified(self):
        self.update_title(changed=True)

    # matplotlib slot
    def mpl_on_mouse_move(self, event):
        if event.xdata and event.ydata:
            yformat = self.plotHandle.yaxis.get_major_formatter()
            xformat = self.plotHandle.xaxis.get_major_formatter()
            self.stbStatus.showMessage(u'x={:} y={:}'.format(xformat.format_data_short(event.xdata),
                                                             yformat.format_data_short(event.ydata)))    
    
    ### SLOTS - PLOT WINDOW

    @pyqtSlot()
    def on_btnUpdate_clicked(self):
        try:
            coating = self.build_coating()
        except materials.MaterialNotDefined as e:
            QMessageBox.critical(self, 'Material Error', str(e))
            return
        plot = str(self.cbPlotType.currentText())
        
        self.pltMain.figure.clear()
        self.plotHandle = self.pltMain.figure.add_subplot(111)
        klass = self.plots[plot]['plotter']
        plot = klass(self.plotHandle)
        plot.plot(coating)
        self.pltMain.draw()

    @pyqtSlot(str)
    def update_plot_widget(self, plot):
        # if plot has it's own widget, then load it
        # TODO: these widgets should have their own class, so that they can 
        # load and save config stuff etc, and can easily interact with the
        # plotting
        klass = self.plots[plot]['options']
        if klass:
            widget = klass(self.gbPlotWidget)
        else:
            widget = self.empty_plotoptions_widget

        old_widget = self.gbPlotWidget.layout().takeAt(0).widget()
        old_widget.setParent(None)
        self.gbPlotWidget.layout().addWidget(widget)
        
    ### SLOTS - STACK TAB

    @pyqtSlot()
    def on_btnRemoveLayer_clicked(self):
        self.tblStack.removeRow(self.tblStack.currentRow())
        self.config.set('coating.layers', self.get_layers())

    @pyqtSlot()
    def on_btnAddLayer_clicked(self):
        row = self.tblStack.currentRow()+1
        self.tblStack.insertRow(row)

    @pyqtSlot(str)
    def on_cbPlotType_currentIndexChanged(self, plot):
        plot = str(plot)
        self.update_plot_widget(plot) 
        self.config.set('plot.plottype', plot)

    @pyqtSlot(str)
    def on_cbSuperstrate_currentIndexChanged(self, text):
        self.config.set('coating.superstrate', text)

    @pyqtSlot(str)
    def on_cbSubstrate_currentIndexChanged(self, text):
        self.config.set('coating.substrate', text)
    
    @pyqtSlot()
    def on_txtLambda0_editingFinished(self):
        text = self.txtLambda0.text()
        try:
            self.config.set('coating.lambda0', float(text))
        except ValueError:
            self.float_conversion_error(text)
    
    @pyqtSlot()
    def on_txtAOI_editingFinished(self):
        text = self.txtAOI.text()
        try:
            self.config.set('coating.AOI', float(text))
        except ValueError:
            self.float_conversion_error(text)

    @pyqtSlot(int, int)
    def on_tblStack_cellChanged(self, row, col):
        txt = self.tblStack.item(row, col).text()
        if col == 1:
            # auto-convert L/x or l/x to lambda/x thicknesses
            m = re.match('^[Ll]?/(\d+)$', txt)
            if m:
                lox = int(m.groups()[0])
                mat = self.tblStack.item(row, col-1).text()
                try:
                    mat = self.materials.get_material(str(mat))
                    lambda0 = self.config.get('coating.lambda0')
                    t_lox = lambda0/(mat.n(lambda0) * lox)
                    with block_signals(self.tblStack) as tbl:
                        tbl.item(row, col).setText('{:.1f}'.format(t_lox))
                except materials.MaterialNotDefined:
                    pass

        self.config.set('coating.layers', self.get_layers())

    @pyqtSlot()
    def on_btnWizard_clicked(self):
        QMessageBox.information(self, 'Preparing for O.W.L.',
            'Sorry, the wizard is not available yet.')

    ### SLOTS - PLOT OPTIONS TAB

    ### SLOTS - MATERIALS TAB

    @pyqtSlot()
    def update_material_list(self):
        # save selection
        sub = str(self.cbSubstrate.currentText())
        sup = str(self.cbSuperstrate.currentText())
        materials = [m for m in self.materials.list_materials()]
        self.lstMaterials.clear()
        self.cbSuperstrate.clear()
        self.cbSubstrate.clear()
        self.lstMaterials.addItems(materials)
        with block_signals(self.cbSubstrate) as cbsub, block_signals(self.cbSuperstrate) as cbsup:
            cbsub.addItems(sorted(materials))
            cbsup.addItems(sorted(materials))
            # if user added a numeric refractive index value, copy that back in
            if sub and not sub in materials:
                cbsub.addItem(sub)
            if sup and not sup in materials:
                cbsup.addItem(sup)
            # restore selection
            cbsub.setCurrentIndex(self.cbSubstrate.findText(sub))
            cbsup.setCurrentIndex(self.cbSuperstrate.findText(sup))

    @pyqtSlot()
    def on_btnAddMaterial_clicked(self):
        dlg = MaterialDialog(self)
        dlg.load_material()
        if dlg.exec_() == QDialog.Accepted:
            dlg.save_material()
            self.update_material_list()

    @pyqtSlot()
    def on_btnEditMaterial_clicked(self):
        row = self.lstMaterials.currentRow()
        if row >= 0:
            material = str(self.lstMaterials.item(row).text())
            dlg = MaterialDialog(self)
            dlg.load_material(material)
            if dlg.exec_() == QDialog.Accepted:
                dlg.save_material()

    @pyqtSlot()
    def on_btnDeleteMaterial_clicked(self):
        row = self.lstMaterials.currentRow()
        if row >= 0:
            material = str(self.lstMaterials.item(row).text())
            materials.MaterialLibrary.Instance().unregister(material)
            self.lstMaterials.takeItem(row)
            self.cbSuperstrate.removeItem(self.cbSuperstrate.findText(material))
            self.cbSubstrate.removeItem(self.cbSubstrate.findText(material))


    ### SLOTS - MENU

    @pyqtSlot()
    def on_actionExport_triggered(self):
        filename = QFileDialog.getSaveFileName(self, 'Export Plot',
                            splitext(self.filename)[0]+'.pdf', 'PDF (*.pdf)');
        if filename:
            self.pltMain.figure.savefig(str(filename))

    @pyqtSlot()
    def on_actionSave_triggered(self):
        filename = str(QFileDialog.getSaveFileName(self, 'Save Coating Project',
                            self.filename, 'Coating Project Files (*.cgp)'))
        if filename:
            self.config.save(filename)
            self.update_title(basename(filename))

    @pyqtSlot()
    def on_actionOpen_triggered(self):
        if self.modified:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                        'You have unsaved changes, do you really want to discard those?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        filename = str(QFileDialog.getOpenFileName(self, 'Open Coating Project',
                            '.', 'Coating Project Files (*.cgp)'))
        if filename:
            self.config.load(filename)
            self.update_title(basename(filename))
            self.initialise_plotoptions()
            self.initialise_materials()
            self.initialise_stack()
