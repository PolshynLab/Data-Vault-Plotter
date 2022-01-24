import sys
import os
import random
from jinja2 import Environment, PackageLoader
from PyQt5.QtGui, QtWidgets import QApplication, QPrinter
from PyQt5.QtWebKit import QWebView

path = sys.path[0]
os.chdir(path)

# Jinja2 template environment
env = Environment(loader=PackageLoader("testPDFTemp", "templates"))
 
 
def render_template(template_file, **kwargs):
	template = env.get_template(template_file)
	return template.render(**kwargs)
 
 
def print_pdf(html, destination):
	#app = QApplication(sys.argv)
 
	web = QWebView()
	web.setHtml(html)
	#app = QApplication.instance()
	#app.processEvents()
 
	printer = QPrinter()
	printer.setPageSize(QPrinter.A4)
	printer.setOutputFormat(QPrinter.PdfFormat)
	printer.setOutputFileName(destination)
	web.print_(printer)
 
	app.exit()
 
 
def main():
	paragraphs = ['This is a paragraph','with multiple lines?']
	dataSet = 'Sample Data'
 
	html = render_template(
		"report.html",
		data_set = dataSet,
		paragraphs = paragraphs
		
	)
 
	print_pdf(html, "file.pdf")
 
 
if __name__ == "__main__":
	main()