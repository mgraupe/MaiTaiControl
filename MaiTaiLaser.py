# -*- coding: utf-8 -*-
#from acq4.devices.Laser import *
from driver import *
from MaiTaiDevGui import MaiTaiDevGui
from util.Mutex import Mutex
from util.Thread import Thread
import util.debug as debug
import time
from PyQt5 import QtCore, QtGui
import sys
import socket
import select

class MaiTaiLaser(QtCore.QObject):

    sigOutputPowerChanged = QtCore.Signal(object)
    sigSamplePowerChanged = QtCore.Signal(object)
    sigRelativeHumidityChanged = QtCore.Signal(object)
    sigPumpPowerChanged = QtCore.Signal(object)
    sigPulsingStateChanged = QtCore.Signal(object)
    sigWavelengthChanged = QtCore.Signal(object)
    sigModeChanged = QtCore.Signal(object)
    sigP2OptimizationChanged = QtCore.Signal(object)
    sigHistoryBufferChanged = QtCore.Signal(object)
    sigHistoryBufferPumpLaserChanged = QtCore.Signal(object)
    
    def __init__(self):
        
        super(MaiTaiLaser,self).__init__()

        self.port = 2 #config['port']-1  ## windows com ports start at COM1, pyserial ports start at 0
        self.baud = 38400 #9600 # config.get('baud', 9600)
        self.alignmentPower = 0.2 # config.get('alignmentPower',0.2)
        
        self.dataSize = 1024 # size of data-packages sent back and forth
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create a socket object
        self.host = '172.20.61.234' #172.20.61.88' #params.host #socket.gethostname() #Get the local machine name
        self.socketPort = 6666 # params.port # Reserve a port for your service
        self.sock.bind((self.host,self.socketPort)) #Bind to the port
        #self.sock.settimeout(10)
        
        
        
        self.driver = MaiTai(self.port)
        self.driverLock = Mutex(QtCore.QMutex.Recursive)  ## access to low level driver calls
        
        self.maiTaiLock = Mutex(QtCore.QMutex.Recursive)  ## access to self.attributes
        self.maiTaiPower = 0.
        self.maiTaiWavelength = 0
        self.maiTaiHumidity = 0.
        self.maiTaiPumpPower = 0.
        self.maiTaiPulsing = False
        self.maiTaiP2Optimization = False
        self.maiTaiMode = None
        self.maiTaiHistory = None
            
        self.gui = MaiTaiDevGui(self)
        self.gui.setWindowTitle('MaiTai Control')
        self.gui.setGeometry(20, 40,600,450)
        
        self.gui.show()
        
        self.mThread = MaiTaiThread(self, self.driver, self.driverLock)
        self.mThread.sigPowerChanged.connect(self.powerChanged)
        self.mThread.sigWLChanged.connect(self.wavelengthChanged)
        self.mThread.sigRelHumidityChanged.connect(self.humidityChanged)
        self.mThread.sigPPowerChanged.connect(self.pumpPowerChanged)
        self.mThread.sigPulsingSChanged.connect(self.pulsingStateChanged)
        self.mThread.sigMoChanged.connect(self.modeChanged)
        self.mThread.sigP2OChanged.connect(self.p2OptimizationChanged)
        self.mThread.sigHChanged.connect(self.historyBufferChanged)
        self.mThread.sigHPLChanged.connect(self.historyBufferPumpLaserChanged)
        self.mThread.start()
        
        
        #Laser.__init__(self, dm, config, name)
        
        self.hasShutter = True
        self.hasTunableWavelength = True
        
        #if self.hasExternalSwitch:
        #    if not self.getInternalShutter():
        #        self.setChanHolding('externalSwitch', 1)
        
        #dm.sigAbortAll.connect(self.closeInternalShutter)
        
    def isLaserOn(self):
       with self.driverLock:
           return self.driver.isLaserOn()
       
    def switchLaserOn(self):
        with self.driverLock:
            self.driver.turnLaserOn()

    def switchLaserOff(self):
        with self.driverLock:
            self.driver.turnLaserOff()
            
    def powerChanged(self, power):
        with self.maiTaiLock:
            self.maiTaiPower = power
            #self.setParam(currentPower=power)
            #powerOk = self.checkPowerValidity(power)
            self.sigOutputPowerChanged.emit(power)
                
    def wavelengthChanged(self, wl):
        with self.maiTaiLock:
            self.maiTaiWavelength = wl
            self.sigWavelengthChanged.emit(wl)
    
    def humidityChanged(self,hum):
        with self.maiTaiLock:
            self.maiTaiHumidity = hum
            self.sigRelativeHumidityChanged.emit(hum)
            
    def pumpPowerChanged(self,pP):
        with self.maiTaiLock:
            self.maiTaiPumpPower = pP
            self.sigPumpPowerChanged.emit(pP)
    
    def pulsingStateChanged(self, pulse):
        with self.maiTaiLock:
            self.maiTaiPulsing = pulse
            self.sigPulsingStateChanged.emit(pulse)
    
    def p2OptimizationChanged(self, p2):
        with self.maiTaiLock:
            self.maiTaiP2Optimization = p2
            self.sigP2OptimizationChanged.emit(p2)
    
    def historyBufferChanged(self, hist):
        with self.maiTaiLock:
            self.maiTaiHistory = hist
            self.sigHistoryBufferChanged.emit(hist)
    
    def historyBufferPumpLaserChanged(self, histPL):
        with self.maiTaiLock:
            self.maiTaiPumpLaserHistory = histPL
            self.sigHistoryBufferPumpLaserChanged.emit(histPL)
    
    def humidity(self):
        with self.maiTaiLock:
            return self.maiTaiHumidity 
    
    def pulsing(self):
        with self.maiTaiLock:
            return self.maiTaiPulsing 
    
    def modeChanged(self,mode):
        with self.maiTaiLock:
            self.maiTaiMode = mode
            self.sigModeChanged.emit(mode)
    
    def outputPower(self):
        with self.maiTaiLock:
            return self.maiTaiPower
    
    def getPumpPower(self):
        with self.maiTaiLock:
            return self.maiTaiPumpPower
    
    def getWavelength(self):
        with self.driverLock:
            return self.driver.getWavelength()*1e-9
        
    def setWavelength(self, wl):
        with self.driverLock:
            self.driver.setWavelength(wl*1e9)
            
    def getWavelengthRange(self):
        with self.driverLock:
            bounds = self.driver.getWavelengthRange()
        return bounds[0]*1e-9, bounds[1]*1e-9
    
    def openInternalShutter(self):
        with self.driverLock:
            self.driver.setShutter(True)
        
    def closeInternalShutter(self):
        with self.driverLock:
            self.driver.setShutter(False)
        
    def getInternalShutter(self):
        with self.driverLock:
            return self.driver.getShutter()
    
    def externalSwitchON(self):
        if self.hasExternalSwitch:
            self.setChanHolding('externalSwitch', 1)
    
    def externalSwitchOFF(self):
        if self.hasExternalSwitch:
            self.setChanHolding('externalSwitch', 0)
    
    def acitvateAlignmentMode(self):
        """ during alignment mode : switch off p2 opitimization, switch to green power, and reduce power to 200 mW """
        with self.driverLock:
            self.driver.setP2Status(False)
            self.greenPowerInIRMode = self.driver.getLastCommandedPumpLaserPower()
            self.driver.setPumpMode('Green Power')
        self.mThread.alignmentMode = True
        
    def deactivateAlignmentMode(self):
        with self.driverLock:
            self.driver.setPumpLaserPower(self.greenPowerInIRMode)
            self.driver.setPumpMode('IR Power')
            self.driver.setP2Status(True)
        self.mThread.alignmentMode = False
    
    def createTask(self, cmd, parentTask):
        return MaiTaiTask(self, cmd, parentTask)

    def deviceInterface(self, win):
        return MaiTaiDevGui(self)
    
    def socket_connect(self):
        self.sock.listen(1)
        print 'after listen'
        self.connection,self.remoteAddr = self.sock.accept()
        print 'established connection with ',self.remoteAddr
        #return self.c

    def socket_monitor_activity(self):
        r, _, _ = select.select([self.connection], [], [])
        #data = self.c.recv(1024)
        #print r
        return bool(r)

    def socket_read_data(self):
        return self.connection.recv(self.dataSize)

    def socket_send_data(self,data):
        self.connection.send(data)

    def socket_close_connection(self):
        self.connection.close()
    
    def closeConnections(self):
        
        print 'closing connections to hardware',
        
        self.mThread.stop()
        
        # trick to stop socket.accept() call
        try:
            self.socketClose = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #create a socket object
            self.socketClose.connect((self.host,self.socketPort))
            self.socketClose.send('disconnect')
            self.socketClose.close()
        except socket.error:
            pass
        
        self.sock.close()
        
        #try : 
        #    self.driver
        #except AttributeError:
        #    pass
        #else:
        #    self.driver.close()
        
        print 'Ciao!'


class MaiTaiThread(Thread):

    sigPowerChanged = QtCore.Signal(object)
    sigWLChanged = QtCore.Signal(object)
    sigRelHumidityChanged = QtCore.Signal(object)
    sigPPowerChanged = QtCore.Signal(object)
    sigPulsingSChanged = QtCore.Signal(object)
    sigMoChanged = QtCore.Signal(object)
    sigP2OChanged = QtCore.Signal(object)
    sigHChanged = QtCore.Signal(object)
    sigHPLChanged = QtCore.Signal(object)
    sigError = QtCore.Signal(object)

    def __init__(self, dev, driver, lock):
        Thread.__init__(self)
        self.lock = Mutex(QtCore.QMutex.Recursive)
        self.dev = dev
        self.driver = driver
        self.driverLock = lock
        self.cmds = {}
        self.alignmentMode = False
        
    def setWavelength(self, wl):
        pass
        
    def setShutter(self, opened):
        wait = QtCore.QWaitCondition()
        cmd = ['setShutter', opened]
        with self.lock:
            self.cmds.append(cmd)
    def adjustPumpPower(self,currentPower):
        """ keeps laser output power between alignmentPower value and  alignmentPower + 25%"""
        lastCommandedPP = self.driver.getLastCommandedPumpLaserPower()
        if self.dev.alignmentPower*1.25 < currentPower:
            newPP = round(lastCommandedPP*0.98,2) # decrease pump power by 2 % 
            self.driver.setPumpLaserPower(newPP)
        elif self.dev.alignmentPower > currentPower:
            newPP = round(lastCommandedPP*1.01,2) # increase pump power by 1 % 
            self.driver.setPumpLaserPower(newPP)
        #newCommandedPP = self.driver.getLastCommandedPumpLaserPower()
        #print 'pump laser power - before : new : after , ', lastCommandedPP, newPP, newCommandedPP
        #print 'laser output power : ', currentPower
        
        
    def run(self):
        self.stopThread = False
        with self.driverLock:
            self.sigWLChanged.emit(self.driver.getWavelength()*1e-9)
        while True:
            try:
                with self.driverLock:
                    power = self.driver.getPower()
                    wl = self.driver.getWavelength()*1e-9
                    hum = self.driver.getRelativeHumidity()
                    pumpPower = self.driver.getPumpPower()
                    isPulsing = self.driver.checkPulsing()
                    mode = self.driver.getPumpMode()
                    p2Optimization = self.driver.getP2Status()
                    status = self.driver.getHistoryBuffer()
                    statusPumpLaser = self.driver.getHistoryBufferPumpLaser()
                    if self.alignmentMode:
                        self.adjustPumpPower(power)
                    
                self.sigPowerChanged.emit(power)
                self.sigWLChanged.emit(wl)
                self.sigRelHumidityChanged.emit(hum)
                self.sigPPowerChanged.emit(pumpPower)
                self.sigPulsingSChanged.emit(isPulsing)
                self.sigMoChanged.emit(mode)
                self.sigP2OChanged.emit(p2Optimization)
                self.sigHChanged.emit(status)
                self.sigHPLChanged.emit(statusPumpLaser)
                time.sleep(0.5)
            except:
                debug.printExc("Error in MaiTai laser communication thread:")
                
            self.lock.lock()
            if self.stopThread:
                self.lock.unlock()
                break
            self.lock.unlock()
            time.sleep(0.02)

        self.driver.close()
    
    def stop(self, block=False):
        with self.lock:
            self.stopThread = True
        if block:
            if not self.wait(10000):
                raise Exception("Timed out while waiting for thread exit!")
    
##########################################################
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    form = MaiTaiLaser()
    #form.show()
    app.exec_()        
