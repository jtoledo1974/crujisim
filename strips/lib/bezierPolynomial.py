# A set of functions for using bezier curves to draw polynomicals of up to order 3
# using cubic bezier curves
# This is an alternative to specifying bezier curves in terms of their control points
#
# work sponsored by Greg Wilson
# Christopher Lee 2000

# Primary Interface Functions:

# drawing functions of parameterized curves: v(t) is a vector tracing a curve in 2D
#                                    ^^^^^^
#    cubicCurveToBezierCtrlPts(..)
#
# drawing function of the form y(x) = a x^3 + b x^2 + c x + d
#
#    quadraticToCtrlPts(..)
#    cubicToCtrlPts(..)


################################################################
# function for converting from a polynomial curve representation
# to a bezier control point representation
################################################################

def cubicCurveToBezierCtrlPts(tinterval=(0., 1.0),
                              A=(0.,0.),
                              B=(0.,0.),
                              C=(0.,0.),
                              D=(0.,0.) ):
    """Given a parameterized curve,  W(t) = A t^3 + B t^2 + C t + D,
    where A,B,C,D are 2D vectors and t ranges from tinterval[0] to tinterval[1],
    returns the bezier ctrl points for the curve"""

    coeffs = _cubicCurveReparameterizeT(tinterval[0], tinterval[1],
                                       A, B,C,D)

    return _normalizedCubicCoeff2BezierCtrlPts(coeffs)


def _cubicCurveReparameterizeT(T1,T2, A, B, C, D):
    "Given a curve w(t) = A t^3 + B t^2 + C t + D with t going from T1 to T2,"
    "return coefficients  (a,b,c,d) for the same curve with t going from 0 to 1"
    # start using pythons power operator **
    scale = T2-T1  # temporary variable
    scale2 = scale**2
    scale3 = scale**3
    a = (A[0]* scale3, A[1]* scale3)
    b = ( (B[0] + 3*A[0]) * scale2, (B[1] + 3*A[1]) * scale2)
    
    #  c = C * scale - 2*B* (T1**2) - 3*A* (T1**3) + 2*B*T1*T2 + 3*A* (T1**2) * T2 
    # This is simplier
    c = (C[0] + T1 * (2*B[0] + 3*A[0]*T1)) * scale, (C[1] + T1 * (2*B[1] + 3*A[1]*T1)) * scale
    d = A[0]*(T1**3) + B[0]*(T1**2) + C[0]*T1 + D[0], A[1]*(T1**3) + B[1]*(T1**2) + C[1]*T1 + D[1]
    return (a,b,c,d)
    
def _normalizedCubicCoeff2BezierCtrlPts(coeffs):
    "Given a curve w(t) = a t^3 + b t^2 + c t + d with t going from 0 to 1\n"
    """return the cubic bezier control points for that curve.
    The coofficeints are presumed to be tuples of the form
    coeffs = (a,b,c,d) with
    a = (ax,ay), etc.
    ??? Should I make the return values are suitable for the drawCurve operator in sping
    """
    a,b,c,d = coeffs
    x = [d[0], 0,0,0]
    y = [d[1], 0,0,0]
    v = [x,y]
    for ii in (0, 1): # iterate over vector components 
        v[ii][1] = v[ii][0] + c[ii]/3.0
        v[ii][2] = v[ii][1] + (c[ii]+b[ii])/3.0
        v[ii][3] = v[ii][0] + c[ii] + b[ii] + a[ii]

    return (x[0], y[0],
            x[1], y[1],
            x[2], y[2],
            x[3], y[3])


################################################################
# Functions to draw polynomicals of the form
#           y(x) = a x^3 + b x^2 + c x + d
#
# These are
#   quadraticToCtrlPts(xinterval,  A=0., B=0., C=0.):
#   cubicToCtrlPts(xinterval,  A=0., B=0., C=0., D=0):


def quadraticToCtrlPts(xinterval,  A=0., B=0., C=0.):
    """return the control points for a bezier curve that fits the quadratic function
    y = A x^2 + B x + C.  for the interval along the x-axis given by xinterval=(x0,x1)"""
    # y(x) = A x^2  + B x + C
    # for x \in [ xinterval[0], xinterval[1] ]j
    x0 = float(xinterval[0])
    x3 = float(xinterval[1])
    y0 = A*x0**2 + B*x0 + C  
    ### print 'y0=', y0 DEBUG

    xlen = x3-x0
    # print 'xlen = ', xlen
    cx = xlen  # set x scaling, check if makes sense for xlen <0
    
    # convert to cubic paramaters, adjust for xscaling
    # lower case used for cubic: w(t) = a t^3 + b*t^2 + c* t + w0
    # t: [0,1]
    # parameters are adjusted to accout for x(t) = cx*t+x0 tranformation
    #by <-> A
    #cy <-> B
    a = (0,0)
    b = (0, A*cx*cx )
    c = (cx, B*cx+2*b[1]*x0/cx)
    v0 = (x0,C-(b[1]/(cx*cx)) *x0*x0) ;
    ### print a,b,c,v0
    x = [x0, 0, 0, 0]; y = [y0, 0, 0, 0]
    v = [x, y]
    for ii in (0, 1): # iterate over vector components 
        v[ii][1] = v[ii][0] + c[ii]/3.0
        v[ii][2] = v[ii][1] + (c[ii]+b[ii])/3.0
        v[ii][3] = v[ii][0] + c[ii] + b[ii] + a[ii]

    return (v[0][0], v[1][0],
            v[0][1], v[1][1],
            v[0][2], v[1][2],
            v[0][3], v[1][3])
    
def cubicToCtrlPts(xinterval,  A=0., B=0., C=0., D=0):
    """return the control points for a bezier curve that fits the cubic polynomial
    y = A x^3 + B x^2 + C x + D.  for the interval along the x-axis given by
    xinterval=(xStart,xEnd)"""
    # for x \in [ xinterval[0], xinterval[1] ]
    x0 = float(xinterval[0])
    x3 = float(xinterval[1])

    # y0 = y(x0)
    x0sqrd = x0*x0
    y0 = A*x0* x0sqrd + B * x0sqrd + C * x0  + D 


    xlen = x3-x0
    # print 'xlen = ', xlen
    cx = xlen  # set x scaling, check if makes sense for xlen <0
    
    # convert to cubic paramaters, adjust for xscaling
    # lower case used for cubic: w(t) = a t^3 + b*t^2 + c* t + w0
    # t: [0,1]
    # parameters are adjusted to accout for x(t) = cx*t+x0 tranformation
    #by <-> A
    #cy <-> B
    a = (0,A*cx*cx*cx) 
    b = (0, B*cx*cx+ 3*A*cx*cx*x0 )
    c = (cx, C*cx + 2*B*cx*x0+3*A*cx*x0*x0)
    v0 = (x0,y0) ;
    ### print a,b,c,v0
    x = [x0, 0, 0, 0]; y = [y0, 0, 0, 0]
    v = [x, y]
    for ii in (0, 1): # iterate over vector components 
        v[ii][1] = v[ii][0] + c[ii]/3.0
        v[ii][2] = v[ii][1] + (c[ii]+b[ii])/3.0
        v[ii][3] = v[ii][0] + c[ii] + b[ii] + a[ii]

    return (v[0][0], v[1][0],
            v[0][1], v[1][1],
            v[0][2], v[1][2],
            v[0][3], v[1][3])













