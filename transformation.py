#!/usr/bin/env python

class transformation:
    def __init__(self, angle=0, vector=(0,0)):
        self.angle=angle
        self.vector=vector

    def __mul__(self, other):
        if isinstance(other, transformation):
	    angle  = self.angle + other.angle
            vector = ( self.matrix()[0][0]*other.vector[0] + self.matrix()[0][1]*other.vector[1] + self.vector[0],
                       self.matrix()[1][0]*other.vector[0] + self.matrix()[1][1]*other.vector[1] + self.vector[1] )

            print " ( %s * %s => %s ) "% (self, other, transformation(angle=angle, vector=vector))
		      
	    return transformation(angle=angle, vector=vector)
	else:
	    raise NotImplementedError, "can only multiply two transformations"

    def matrix(self):
        from math import cos, sin
        return ( ( cos(self.angle), sin(self.angle)), 
	         (-sin(self.angle), cos(self.angle)) )

    def vector(self):
        return self.vector

    def angle(self):
        return self.angle
    
    def translate(self,x,y):
	return self*transformation(vector=(x,y))
	
    def rotate(self,angle):
	return transformation(angle=angle)*self
	
    def __repr__(self):
        return "angle=%f, vector=%s" % (self.angle, self.vector)

class translate(transformation):
    def __init__(self,x,y):
        transformation.__init__(self, vector=(x,y))
   
class rotate(transformation):
    def __init__(self,angle):
        transformation.__init__(self, angle=angle)

if __name__=="__main__":
   from math import pi
#   print rotate(pi/2).rotate(pi/2).rotate(pi/2).rotate(pi/2)
   print translate(1,1).rotate(pi/2).translate(-1,-1)
   print translate(1,1)*rotate(pi/2)*translate(-1,-1)
   print translate(-1,-1)*rotate(pi/2)*translate(1,1)
#   print translate(-1,-1).rotate(pi/2).translate(1,1)
  


# tmatrix = ( ( self.tmatrix[0][0]*other.tmatrix[0][0] + self.tmatrix[0][1]*other.tmatrix[1][0],
#               self.tmatrix[0][0]*other.tmatrix[0][1] + self.tmatrix[0][1]*other.tmatrix[1][1] ),
#             ( self.tmatrix[1][0]*other.tmatrix[0][0] + self.tmatrix[1][1]*other.tmatrix[1][0],
#               self.tmatrix[1][0]*other.tmatrix[0][1] + self.tmatrix[1][1]*other.tmatrix[1][1] )
#           )
