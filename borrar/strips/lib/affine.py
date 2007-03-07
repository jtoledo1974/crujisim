
class AffineMatrix:
    "Represents a 2D + 1 affine transformation"
    # use this for transforming points
    # A = [ a c e]
    #     [ b d f]
    #     [ 0 0 1]
    # self.A = [a b c d e f] = " [ A[0] A[1] A[2] A[3] A[4] A[5] ]"
    def __init__(self, init=None):
        if init:
            if len(init) == 6 :
                self.A = init
            if type(init) == type(self): # erpht!!! this seems so wrong
                self.A = init.A
        else:
            self.A = [1.0, 0, 0, 1.0, 0.0, 0.0] # set to identity

    def scale(self, sx, sy):
        self.A = [sx*self.A[0], sx*self.A[1], sy*self.A[2], sy * self.A[3], self.A[4], self.A[5] ]

    def rotate(self, theta):
        "counter clockwise rotation in standard SVG/libart coordinate system"
        # clockwise in postscript "y-upward" coordinate system
        # R = [ c  -s  0 ]
        #     [ s   c  0 ]
        #     [ 0   0  1 ]

        co = math.cos(PI*theta/180.0)
        si = math.sin(PI*theta/180.0)
        self.A = [self.A[0] * co + self.A[2] * si,
                  self.A[1] * co + self.A[3] * si,
                  -self.A[0]* si + self.A[2] * co,
                  -self.A[1]* si + self.A[3] * co,
                  self.A[4],
                  self.A[5] ]

    def translate(self, tx, ty):
        self.A  = [ self.A[0], self.A[1], self.A[2], self.A[3],
                    self.A[0]*tx + self.A[2]*ty + self.A[4],
                    self.A[1]*tx + self.A[3]*ty + self.A[5] ]

    def rightMultiply(self, a, b, c, d, e, f):
        "multiply self.A by matrix M defined by coefficients a,b,c,d,e,f"
        # 

        #             [    m0*a+m2*b,    m0*c+m2*d, m0*e+m2*f+m4]
        #  ctm * M =  [    m1*a+m3*b,    m1*c+m3*d, m1*e+m3*f+m5]
        #             [            0,            0,            1]
        m= self.A
        self.A = [ m[0]*a+m[2]*b,
                   m[1]*a+m[3]*b,
                   m[0]*c+m[2]*d,
                   m[1]*c+m[3]*d,
                   m[0]*e+m[2]*f+m[4],
                   m[1]*e+m[3]*f+m[5] ]

    #########  functions that act on points ##########

    def transformPt(self, pt):
        #                   [
        #  pt = A * [x, y, 1]^T  =  [a*x + c*y+e, b*x+d*y+f, 1]^T
        #
        x,y = pt
        a,b,c,d,e,f = self.A
        return [ a*x + c*y+e, b*x+d*y+f]

    def scaleRotateVector(self, v):
        # scale a vector (translations are not done)
        x, y = v
        a,b,c,d,e,f = self.A
        return [a*x + c*y, b*x+d*y]
        
        
    def transformFlatList(self, seq):
        # transform a (flattened) sequence of points in form [x0,y0, x1,y1,..., x(N-1), y(N-1)]
        N = len(seq) # assert N even

        # would like to reshape the sequence, do w/ a loop for now
        res = []
        for ii in xrange(0,N, 2):
            pt = self.transformPt( (seq[ii], seq[ii+1]) )
            res.extend(pt)

        return res


