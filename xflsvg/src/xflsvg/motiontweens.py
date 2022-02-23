import numpy
import math

def adobe_decomposition(a):
  """ Factor a matrix into a rotation, a shear, and a scale (x and y).

  The order comes from what Adobe Animate's UI does. It applies a scale to the
  original shape, a skew to the scaled result, and a rotation to the skewed
  result.

  These parameters come from what someone else reverse engineered of Direct2D's
  transformation.
    https://stackoverflow.com/questions/45159314/decompose-2d-transformation-matrix
  
  The main difference is in how the scale_y parameter is handled. In Direct2D,
  there is a cos(shear) factor in scale_y. In Animate, that factor is included
  in the shear matrix and is interpolated as part of shear.

  The shear angle here is the negative of the Direct2D shear. That makes the
  resulting shear matrix consistent with standard CSS skewX matrix. The shear
  angle also needs to be mapped to (-pi, pi). Without that, the skew might get
  interpolated in the wrong direction. Shear values of pi and -pi should both
  be disallowed since it results in infinite values.
  """
  rotation = math.atan2(a[1,0], a[0,0])
  shear = (math.pi/2 + rotation - math.atan2(a[1,1], a[0,1])) % (math.pi*2)
  if math.cos(shear) < 0:
    shear -= 2 * math.pi
  scale_x = math.sqrt(a[0,0]**2 + a[1,0]**2)
  scale_y = math.sqrt(a[0,1]**2 + a[1,1]**2)
  
  return rotation, shear, scale_x, scale_y
  
  return rotation, shear, scale_x, scale_y

def adobe_matrix(rotation, shear, scale_x, scale_y):
  """ Creates a matrix that performs the given rotation, shear, and scale.

  This is the inverse of adobe_decomposition. It creates a sequence of three
  linear operations-- rotation, skew, scale-- and multiplies them together.
  The rotation matrix is standard. The shearing matrix the CSS skewX matrix with
  the y co-vector is multiplied by cos(shear). The scaling matrix is standard.

  You can find the overall matrix through algebraic manipulations of the
  Direct2D equations.

  rotation = arctan(a10 / a00)
  shear = pi/2 + rotation - arctan(a11 / a01)
  scale_x = sqrt(a00^2 + a10^2)
  scale_y = sqrt(a01^2 + a11^2) * cos(shear)
  """

  rotation_matrix = numpy.array([
    [math.cos(rotation), -math.sin(rotation)],
    [math.sin(rotation), math.cos(rotation)]
  ])
  
  # Solving for the skew matrix elements...

  # The Direct2D equations:
  #   tan(rotation) = a10 / a00
  #   tan(shear - pi/2 - rotation) = a11 / a01
  #   scale_x^2 = a00^2 + a10^2
  #   scale_y^2 / cos(shear)^2 = a01^2 + a11^2

  # Solving for a00 and a10...
  #   a10 = tan(rotation) * a00
  #   scale_x^2 = a00^2 + tan(rotation)^2 a00^2
  #   scale_x^2 = a00^2 (1 + tan(rotation)^2)

  #   a00^2 = scale_x^2 / (1 + tan(rotation)^2)
  #   a10 = tan(rotation) * sqrt(scale_x^2 / (1 + tan(rotation)^2))
  
  # Solving for a11 and a01...

  #   a11 = tan(shear - pi/2 - rotation) * a01
  #   scale_y^2 / cos(shear)^2 = tan(shear - pi/2 - rotation)^2 * a01^2 + a01^2
  #   scale_y^2 / cos(shear)^2 = (1 + tan(shear - pi/2 - rotation)^2) a01^2
  #   a01^2 = scale_y^2 / cos(shear)^2 / (1 + tan(shear - pi/2 - rotation)^2)

  #   Let k^2 = cos(shear)^2 / (1 + tan(shear - pi/2 - rotation)^2)
  #   a01^2 = scale_y^2 / k^2
  #   a11 = tan(shear - pi/2 - rotation) * scale_y / k
  
  # This mostly works, except the sign ends up getting borked because of all
  # the squaring and square-root operations. To fix that, we need all of those
  # operations to cancel each other out.

  #   a00^2 = scale_x^2 / (1 + tan(rotation)^2)
  #   a00^2 = scale_x^2 / (1 + sin(rotation)^2 / cos(rotation)^2)
  #   a00^2 = scale_x^2 * cos(rotation)^2 / (cos(rotation)^2 + sin(rotation)^2)
  #   a00^2 = scale_x^2 * cos(rotation)^2 / 1
  #   a00 = scale_x * cos(rotation)
  #   a00 = scale_x * cos(rotation)
  #   ... Since we're factoring out rotation and scale_x into separate matrices,
  #   ... s00 = 1 * cos(0)
  #   ... s00 = 1

  #   a10 = tan(rotation) * scale_x * cos(rotation)
  #   a10 = sin(rotation) / cos(rotation) * scale_x * cos(rotation)
  #   a10 = sin(rotation) * scale_x
  #   ... Since we're factoring out rotation and scale_x into separate matrices,
  #   ... s10 = sin(0) * 1
  #   ... s10 = 0

  #   a01^2 = scale_y^2 / cos(shear)^2 / (1 + tan(shear - pi/2 - rotation)^2)
  #   a01^2 = scale_y^2 / cos(shear)^2 / (1 + cot(shear - rotation)^2)
  #   a01^2 = scale_y^2 / cos(shear)^2 * sin(shear - rotation)^2 / 1
  #   a01 = scale_y * sin(shear - rotation) / cos(shear)
  #   ... Since we're factoring out rotation and scale_y into separate matrices,
  #   ... s01 = 1 * sin(shear - 0) / cos(shear)
  #   ... s01 = sin(shear) / cos(shear) = tan(shear)

  #   a11 = tan(shear - pi/2 - rotation) * a01
  #   a11 = cot(shear - rotation) * a01
  #   ... Since we're factoring out rotation and scale_y into separate matrices,
  #   ... s11 = cot(shear - 0) * s01
  #   ... s11 = cot(shear) * tan(shear)
  #   ... s11 = 1
  #
  # We can move the cos(shear) term from the Direct2D scale matrix to the shear
  # matrix by multiplying the y co-vector [tan(shear), 1] by cos(shear). The
  # new y co-vector becomes [sin(shear), cos(shear)].
  skew_matrix = numpy.array([
    [1, math.sin(shear)],
    [0, math.cos(shear)]
  ])
  
  scale_matrix = numpy.array([
    [scale_x, 0],
    [0, scale_y]
  ])
  
  return rotation_matrix @ skew_matrix @ scale_matrix