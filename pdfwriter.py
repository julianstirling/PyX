#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
#
#
# Copyright (C) 2005 J�rg Lehmann <joergl@users.sourceforge.net>
# Copyright (C) 2005 Andr� Wobst <wobsta@users.sourceforge.net>
#
# This file is part of PyX (http://pyx.sourceforge.net/).
#
# PyX is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# PyX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyX; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import copy, warnings
import pykpathsea, unit, resource, style
from t1strip import fullfont
try:
    import zlib
    haszlib = 1
except:
    haszlib = 0


class PDFregistry:

    def __init__(self):
        self.resources = []
        self.types = {}
        self.merged = {} # contains merged resources, where refno's need to be injected
                         # (this is necessary, since some components, which depend on a
                         # given resource might want to lookup the refno, so it needs to
                         # be available even for objects, which have been removed due to
                         # merging)

    def add(self, resource):
        resources = self.types.setdefault(resource.type, {})
        if resources.has_key(resource.id):
            resources[resource.id].merge(resource)
            self.merged.setdefault(resource.type, []).append(resource)
        else:
            self.resources.append(resource)
            resources[resource.id] = resource

    def merge(self, registry):
        for resource in registry.resources:
            self.add(resource)

    def setrefno(self, refno):
        for resource in self.resources:
            refno = resource.setrefno(refno)
        for type, resources in self.merged.items():
            for resource in resources:
                resource.refno = self.types[type][resource.id].refno
        return refno

    def outputPDFobjects(self, file, writer, context):
        for resource in self.resources:
            resource.outputPDFobjects(file, writer, context)

    def outputPDFxref(self, file):
        for resource in self.resources:
            resource.outputPDFxref(file)


class PDFobject:

    def __init__(self, childs=[]):
        self.childs = childs

    def merge(self, other):
        pass

    def setrefno(self, refno):
        self.refno = refno
        refno += 1
        for child in self.childs:
            refno = child.setrefno(refno)
        return refno

    def outputPDFobjects(self, file, writer, context):
        self.outputPDFobject(file, writer, context)
        for child in self.childs:
            child.outputPDFobjects(file, writer, context)

    def outputPDFobject(self, file, writer, context):
        self.filepos = file.tell()
        file.write("%i 0 obj\n" % self.refno)
        self.outputPDF(file, writer, context)
        file.write("endobj\n")

    def outputPDF(self, file, writer, context):
        raise NotImplementedError("outputPDF method has to be provided by PDFobject subclass")

    def outputPDFxref(self, file):
        file.write("%010i 00000 n \n" % self.filepos)
        for child in self.childs:
            child.outputPDFxref(file)


class PDFcatalog(PDFobject):

    def __init__(self, document):
        self.PDFpages = PDFpages(document)
        self.registry = PDFregistry()
        for page in self.PDFpages.PDFpagelist:
            self.registry.merge(page.registry)
        PDFobject.__init__(self, [self.PDFpages])

    def setrefno(self, refno):
        refno = PDFobject.setrefno(self, refno)
        return self.registry.setrefno(refno)

    def outputPDFobjects(self, file, writer, context):
        PDFobject.outputPDFobjects(self, file, writer, context)
        self.registry.outputPDFobjects(file, writer, context)

    def outputPDF(self, file, writer, context):
        file.write("<<\n"
                   "/Type /Catalog\n"
                   "/Pages %i 0 R\n"
                   ">>\n" % self.PDFpages.refno)

    def outputPDFxref(self, file):
        PDFobject.outputPDFxref(self, file)
        self.registry.outputPDFxref(file)


class PDFpages(PDFobject):

    def __init__(self, document):
        self.PDFpagelist = []
        for page in document.pages:
            self.PDFpagelist.append(PDFpage(page, self))
        PDFobject.__init__(self, self.PDFpagelist)

    def outputPDF(self, file, writer, context):
        file.write("<<\n"
                   "/Type /Pages\n"
                   "/Kids [%s]\n"
                   "/Count %i\n"
                   ">>\n" % (" ".join(["%i 0 R" % page.refno
                                       for page in self.PDFpagelist]),
                             len(self.PDFpagelist)))


class PDFpage(PDFobject):

    def __init__(self, page, PDFpages):
        self.PDFpages = PDFpages
        self.page = page
        self.bbox = page.canvas.bbox()
        self.bbox.enlarge(page.bboxenlarge)
        self.pagetrafo = page.pagetrafo(self.bbox)
        if self.pagetrafo:
            self.bbox.transform(self.pagetrafo)
        self.PDFcontent = PDFcontent(page.canvas, self.pagetrafo)
        self.registry = PDFregistry()
        for resource in page.canvas.resources():
            resource.PDFregister(self.registry)
        PDFobject.__init__(self, [self.PDFcontent])

    def outputPDF(self, file, writer, context):
        file.write("<<\n"
                   "/Type /Page\n"
                   "/Parent %i 0 R\n" % self.PDFpages.refno)
        paperformat = self.page.paperformat
        file.write("/MediaBox [0 0 %d %d]\n" % (unit.topt(paperformat.width), unit.topt(paperformat.height)))
        file.write("/CropBox " )
        self.bbox.outputPDF(file, writer, context)
        if self.registry.types["font"]:
            file.write("/Resources << /ProcSet [ /PDF /Text ]\n")
        else:
            file.write("/Resources << /ProcSet [ /PDF ]\n")
        if self.registry.types.has_key("font"):
            file.write("/Font << %s >>" % " ".join(["/%s %i 0 R" % (font.fontname, font.refno)
                                                    for font in self.registry.types["font"].values()]))
        file.write(">>\n")
        file.write("/Contents %i 0 R\n"
                   ">>\n" % (self.PDFcontent.refno))


class _compressstream:

    def __init__(self, file, compresslevel):
        self.file = file
        self.compressobj = zlib.compressobj(writer.compresslevel)

    def write(self, string):
        self.file.write(self.compressobj.compress(string))

    def flush(self):
        self.file.write(self.compressobj.flush())


class PDFcontent(PDFobject):

    def __init__(self, canvas, pagetrafo):
        self.canvas = canvas
        self.pagetrafo = pagetrafo
        self.PDFcontentlength = PDFcontentlength()
        PDFobject.__init__(self, [self.PDFcontentlength])

    def outputPDF(self, file, writer, context):
        file.write("<<\n"
                   "/Length %i 0 R\n" % (self.PDFcontentlength.refno))
        if writer.compress:
            file.write("/Filter /FlateDecode\n")
        file.write(">>\n")
        file.write("stream\n")
        beginstreampos = file.tell()

        if writer.compress:
            stream = _compressstream(file, writer.compresslevel)
        else:
            stream = file

        # apply a possible global transformation
        if self.pagetrafo:
            self.pagetrafo.outputPDF(stream, writer, context)
        style.linewidth.normal.outputPDF(stream, writer, context)

        self.canvas.outputPDF(stream, writer, context)
        if writer.compress:
            stream.flush()

        self.PDFcontentlength.contentlength = file.tell() - beginstreampos
        file.write("endstream\n")


class PDFcontentlength(PDFobject):

    def outputPDF(self, file, writer, context):
        # initially we do not know about the content length
        # -> it has to be written into the instance later on
        file.write("%d\n" % self.contentlength)


class PDFfont(PDFobject):

    def __init__(self, fontname, basepsname, font):
        self.type = "font"
        self.id = self.fontname = fontname
        self.basepsname = basepsname
        self.fontwidths = PDFfontwidths(font)
        self.fontdescriptor = PDFfontdescriptor(font)
        PDFobject.__init__(self, [self.fontwidths, self.fontdescriptor])

    def register(self, registry):
        registry.addresource(registry.fonts, self)

    def outputPDF(self, file, writer, context):
        file.write("<<\n"
                   "/Type /Font\n"
                   "/Subtype /Type1\n"
                   "/Name /%s\n"
                   "/BaseFont /%s\n"
                   "/FirstChar 0\n"
                   "/LastChar 255\n"
                   "/Widths %d 0 R\n"
                   "/FontDescriptor %d 0 R\n"
                   "/Encoding /StandardEncoding\n" # FIXME
                   ">>\n" % (self.fontname, self.basepsname,
                             self.fontwidths.refno, self.fontdescriptor.refno))

class PDFfontwidths(PDFobject):

    def __init__(self, font):
        self.type = "fontwidth"
        self.font = font
        PDFobject.__init__(self)

    def register(self, registry):
        registry.addresource(registry.fontwidths, self)

    def outputPDF(self, file, writer, context):
        file.write("[\n")
        for i in range(256):
            try:
                width = self.font.getwidth_pt(i)*1000/self.font.getsize_pt()
            except:
                width = 0
            file.write("%f\n" % width)
        file.write("]\n")


class PDFfontdescriptor(PDFobject):

    def __init__(self, font):
        self.type = "fontdescriptor"
        self.font = font
        path = pykpathsea.find_file(font.getfontfile(), pykpathsea.kpse_type1_format)
        self.fontfile = PDFfontfile(path)
        PDFobject.__init__(self, [self.fontfile])

    def register(self, registry):
        registry.addresource(registry.fontdescriptors, self)

    def arrange(self, refno):
        return PDFobject.arrangeselfandchilds(self, refno, self.fontfile)

    def outputPDF(self, file, writer, context):
        file.write("<<\n"
                   "/Type /FontDescriptor\n"
                   "/FontName /%s\n"
                   "/Flags 4\n" # FIXME
                   "/FontBBox [-10 -10 1000 1000]\n" # FIXME
                   "/ItalicAngle 0\n" # FIXME
                   "/Ascent 20\n" # FIXME
                   "/Descent -5\n" # FIXME
                   "/CapHeight 15\n" # FIXME
                   "/StemV 3\n" # FIXME
                   "/FontFile %d 0 R\n" # FIXME
                   # "/CharSet \n" # fill in when stripping
                   ">>\n" % (self.font.getbasepsname(), self.fontfile.refno))

class PDFfontfile(PDFobject):

    def __init__(self, path):
        self.type = "fontfile"
        self.path = path
        PDFobject.__init__(self)

    def register(self, registry):
        registry.addresource(registry.fontfiles, self)

    def outputPDF(self, file, writer, context):
        fontfile = open(self.path)
        fontdata = fontfile.read()
        fontfile.close()
        if fontdata[0:2] != fullfont._PFB_ASCII:
            raise RuntimeError("PFB_ASCII mark expected")
        length1 = fullfont.pfblength(fontdata[2:6])
        if fontdata[6+length1:8+length1] != fullfont._PFB_BIN:
            raise RuntimeError("PFB_BIN mark expected")
        length2 = fullfont.pfblength(fontdata[8+length1:12+length1])
        if fontdata[12+length1+length2:14+length1+length2] != fullfont._PFB_ASCII:
            raise RuntimeError("PFB_ASCII mark expected")
        length3 = fullfont.pfblength(fontdata[14+length1+length2:18+length1+length2])
        if fontdata[18+length1+length2+length3:20+length1+length2+length3] != fullfont._PFB_DONE:
            raise RuntimeError("PFB_DONE mark expected")
        if len(fontdata) != 20 + length1 + length2 + length3:
            raise RuntimeError("end of pfb file expected")

        # we might be allowed to skip the third part ...
        if fontdata[18+length1+length2:18+length1+length2+length3].replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "") == "0"*512 + "cleartomark":
            length3 = 0

        if length3:
            data = fontdata[6:6+length1] + fontdata[12+length1:12+length1+length2] + fontdata[18+length1+length2:18+length1+length2+length3]
        else:
            data = fontdata[6:6+length1] + fontdata[12+length1:12+length1+length2]
        if writer.compress:
            data = zlib.compress(data)

        file.write("<<\n"
                   "/Length %d\n"
                   "/Length1 %d\n"
                   "/Length2 %d\n"
                   "/Length3 %d\n" % (len(data), length1, length2, length3))
        if writer.compress:
            file.write("/Filter /FlateDecode\n")
        file.write(">>\n"
                   "stream\n")
        file.write(data)
        file.write("endstream\n")


class PDFwriter:

    def __init__(self, document, filename, compress=1, compresslevel=6):
        warnings.warn("writePDFfile is experimental and supports only a subset of PyX's features")

        if filename[-4:] != ".pdf":
            filename = filename + ".pdf"
        try:
            self.file = open(filename, "wb")
        except IOError:
            raise IOError("cannot open output file")

        if compress and not haszlib:
            compress = 0
            warnings.warn("compression disabled due to missing zlib module")
        self.compress = compress
        self.compresslevel = compresslevel

        self.file.write("%%PDF-1.4\n%%%s%s%s%s\n" % (chr(195), chr(182), chr(195), chr(169)))

        # the PDFcatalog class automatically builds up the pdfobjects from a document
        catalog = PDFcatalog(document)
        pdfobjects = catalog.setrefno(1)

        # objects
        catalog.outputPDFobjects(self.file, self, context())

        # xref
        xrefpos = self.file.tell()
        self.file.write("xref\n"
                        "0 %d\n"
                        "0000000000 65535 f \n" % pdfobjects)
        catalog.outputPDFxref(self.file)

        # trailer
        self.file.write("trailer\n"
                        "<<\n"
                        "/Size %i\n"
                        "/Root %i 0 R\n"
                        ">>\n"
                        "startxref\n"
                        "%i\n"
                        "%%%%EOF\n" % (pdfobjects, catalog.refno, xrefpos))
        self.file.close()


class context:

    def __init__(self):
        self.linewidth_pt = None
        self.colorspace = None
        self.strokeattr = 1
        self.fillattr = 1

    def __call__(self, **kwargs):
        newcontext = copy.copy(self)
        for key, value in kwargs.items():
            setattr(newcontext, key, value)
        return newcontext