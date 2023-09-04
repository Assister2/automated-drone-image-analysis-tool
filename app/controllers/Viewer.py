import logging
import qimage2ndarray
import piexif
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui import QFontDatabase, QFont, QIcon, QColor, QImage, QPainterPath
from PyQt5.QtCore import Qt, QFile, QTextStream, QTranslator, QLocale, QThread, pyqtSlot, QRect, QSize
from PyQt5.QtWidgets import QApplication, QMainWindow, QColorDialog, QFileDialog, QMessageBox, QHBoxLayout

from views.Viewer_ui import Ui_Viewer
from views.components.QtImageViewer import QtImageViewer
from services.KMLService import KMLService
from helpers.ColorUtils import ColorUtils
from helpers.XmlLoader import XmlLoader
from helpers.LocationInfo import LocationInfo

class Viewer(QMainWindow, Ui_Viewer):
	def __init__(self, output_dir, images = None):
		QMainWindow.__init__(self)
		self.setupUi(self)
		self.output_dir = output_dir
		if images is None:
			xmlLoader = XmlLoader(output_dir+"ADIAT_Data.xml")
			_, self.images = xmlLoader.parseFile()
		else:
			self.images = images
		self.current_image = 0
		self.loadInitialImage()
		self.previousImageButton.clicked.connect(self.previousImageButtonClicked)
		self.nextImageButton.clicked.connect(self.nextImageButtonClicked)
		self.KmlButton.clicked.connect(self.KmlButtonClicked)

	def loadInitialImage(self):
		try:
			image = self.images[self.current_image]
			self.placeholderImage.deleteLater()
			self.mainImage = QtImageViewer(self.centralwidget)
			self.mainImage.setGeometry(QRect(0, 40, 650, 650))
			self.mainImage.setObjectName("mainImage")
			self.mainImage.aspectRatioMode = Qt.KeepAspectRatio
			self.mainImage.canZoom = True
			self.mainImage.canPan = True
			img = QImage(self.output_dir+image['name'])
			self.mainImage.setImage(img)
			#self.horizontalLayout.addWidget(self.mainImage)
			self.horizontalLayout.replaceWidget(self.placeholderImage, self.mainImage)
			self.fileNameLabel.setText(image['name'])
			self.loadAreasofInterest(image)
			gps_coords = LocationInfo.getGPS(self.output_dir+image['name'])
			self.statusbar.showMessage("GPS Coordinates: "+gps_coords['latitude']+", "+gps_coords['longitude'])
		except Exception as e:
			logging.exception(e)
			#self.mainImage.show()

	def loadImage(self):
		image = self.images[self.current_image]
		img = QImage(self.output_dir+image['name'])
		self.mainImage.setImage(img)
		self.fileNameLabel.setText(image['name'])
		self.loadAreasofInterest(image)
		self.mainImage.resetZoom()

	def loadAreasofInterest(self, image):
		self.unloadAreasOfInterest();
		img_arr = qimage2ndarray.imread(self.output_dir+image['name'])
		img_width = img_arr.shape[1] - 1
		img_height = img_arr.shape[0] - 1
		count = 0
		cur_pos = 0;
		self.highlights = []
		for area_of_interest in image['areas_of_interest']:
			center = area_of_interest['center']
			radius = area_of_interest['radius']+10
			crop_arr = self.crop_image(img_arr, center[0]-radius, center[1] - radius, center[0]+radius, center[1]+radius)
			highlight = QtImageViewer(self.scrollAreaWidgetContents, center, True)
			highlight.setObjectName("highlight"+str(count))
			highlight.setMinimumSize(QSize(190, 190))
			highlight.aspectRatioMode = Qt.KeepAspectRatio
			img = qimage2ndarray.array2qimage(crop_arr)
			highlight.setImage(img)
			highlight.canZoom = False
			highlight.canPan = False
			self.verticalLayout_2.addWidget(highlight)
			self.highlights.append(highlight)
			highlight.leftMouseButtonPressed.connect(self.area_of_interest_click)
			count += 1
		#self.mainImage.show()

	def previousImageButtonClicked(self):
		if self.current_image == 0:
			self.current_image = len(self.images) -1
		else:
			self.current_image -= 1
		self.loadImage()

	def nextImageButtonClicked(self):
		if (self.current_image == len(self.images) -1):
			self.current_image = 0
		else:
			self.current_image += 1
		self.loadImage()

	def area_of_interest_click(self, x, y, img):
		self.mainImage.zoomToArea(img.center,4)

	def unloadAreasOfInterest(self):
		for i in reversed(range(self.verticalLayout_2.count())): 
			self.verticalLayout_2.itemAt(i).widget().deleteLater()
	def KmlButtonClicked(self):
		fileName, _ = QFileDialog.getSaveFileName(self, "Save KML File", "", "KML files (*.kml)")
		self.generateKml(fileName)
		
	def generateKml(self, output_path):
		kml = KMLService();
		kml_points = list()
		for image in self.images:
			gps_coords = LocationInfo.getGPS(self.output_dir+image['name'])
			point = dict()
			point["name"] = image['name']
			point["long"] = gps_coords['longitude']
			point["lat"] = gps_coords['latitude']
			kml_points.append(point)
		kml.addPoints(kml_points)
		kml.saveKml(output_path)
			
	def crop_image(self,img_arr,startx,starty, endx, endy):
		sx = startx
		if sx < 0:
			sx = 0
		sy = starty
		if sy < 0:
			sy = 0

		img_width = img_arr.shape[1] - 1
		img_height = img_arr.shape[0] - 1
		ex = endx
		if ex > img_width:
			ex = img_width
		ey = endy
		if ey > img_height:
			ey = img_height	
		return img_arr[sy:ey,sx:ex]