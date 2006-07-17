#!/usr/bin/env python

'''Pygame module for accessing surface pixel data.

Functions to convert pixel data between pygame Surfaces and Numeric arrays.
This module will only be available when pygame can use the external Numeric
package.

Note, that surfarray is an optional module.  It requires that Numeric is 
installed to be used.  If not installed, an exception will be raised when
it is used.  eg. NotImplementedError: surfarray module not available

Every pixel is stored as a single integer value to represent the red, green,
and blue colors. The 8bit images use a value that looks into a colormap. Pixels
with higher depth use a bit packing process to place three or four values into
a single number.

The Numeric arrays are indexed by the X axis first, followed by the Y axis.
Arrays that treat the pixels as a single integer are referred to as 2D arrays.
This module can also separate the red, green, and blue color values into
separate indices. These types of arrays are referred to as 3D arrays, and the
last index is 0 for red, 1 for green, and 2 for blue.

Numeric does not use unsigned 16bit integers, images with 16bit data will
be treated as signed integers.
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id$'

from ctypes import *
import re

from SDL import *

# Numeric doesn't provide a Python interface to its array strides, which
# we need to modify, so we go under the bonnet and fiddle with it directly.
# This probably won't work in a lot of scenarios (i.e., outside of my 
# house).
class _PyArrayObject(Structure):
    _fields_ = [('ob_refcnt', c_int),
                ('ob_type', c_void_p),
                ('data', c_char_p),
                ('nd', c_int),
                ('dimensions', POINTER(c_int)),
                ('strides', POINTER(c_int)),
                ('base', c_void_p),
                ('descr', c_void_p),
                ('flags', c_uint),
                ('weakreflist', c_void_p)]

# Provide support for numpy and numarray in addition to Numeric.  To
# be compatible with Pygame, by default the module will be unavailable
# if Numeric is not available.  You can activate it to use any available
# array module by calling set_array_module().
try:
    import Numeric
    _array = Numeric
except ImportError:
    _array = None

def set_array_module(module=None):
    '''Set the array module to use; numpy, numarray or Numeric.

    If no arguments are given, every array module is tried and the
    first one that can be imported will be used.  The order of
    preference is numpy, numarray, Numeric.  You can determine which
    module was set with `get_array_module`.

    :Parameters:
        `module` : module or None
            Module to use.

    '''
    global _array
    if not module:
        for name in ('numpy', 'numarray', 'Numeric'):
            try:
                set_array_module(__import__(name, locals(), globals(), []))
            except ImportError:
                pass
    else:
        _array = module

def get_array_module():
    '''Get the currently set array module.

    If None is returned, no array module is set and the surfarray
    functions will not be useable.

    :rtype: module
    '''
    return _array

def _check_array():
    if not _array:
        raise ImportError, \
              'No array module set; use set_array_module if you want to ' + \
              'use numpy or numarray instead of Numeric.'

def array2d(surface):
    '''Copy pixels into a 2d array.

    Copy the pixels from a Surface into a 2D array. The bit depth of the surface
    will control the size of the integer values, and will work for any type of
    pixel format.

    This function will temporarily lock the Surface as pixels are copied
    (see the Surface.lock() method).

    :Parameters:
        `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''
    _check_array()

    surf = surface._surf
    bpp = surf.format.BytesPerPixel

    if bpp <= 0 or bpp > 4:
        raise ValueError, 'unsupport bit depth for surface array'

    surface.lock()
    data = surf.pixels.to_string()
    surface.unlock()

    # Remove extra pitch from each row
    pitchdiff = surf.pitch - surf.w * bpp
    if pitchdiff > 0:
        pattern = re.compile('(%s)%s' % ('.' * surf.w * bpp, '.' * pitchdiff),
                             flags=re.DOTALL)
        data = ''.join(pattern.findall(data))

    if bpp == 1:
        t = _array.UInt8
    elif bpp == 2:
        t = _array.UInt16
    elif bpp == 3:
        # Pad each triplet of bytes with another zero
        pattern = re.compile('...', flags=re.DOTALL)
        data = '\0'.join(pattern.findall(data))
        if SDL_BYTEORDER == SDL_LIL_ENDIAN:
            data += '\0'
        else:
            data = '\0' + data
        t = _array.UInt32
        bpp = 4
    elif bpp == 4:
        t = _array.UInt32

    shape = surf.w, surf.h
    fake_strides = bpp, bpp * surf.w
    assert len(data) == bpp * surf.w * surf.h

    print _array.__name__
    if _array.__name__ == 'numpy':
        ar = _array.fromstring(data, t).reshape(shape)
        ar.strides = fake_strides
    elif _array.__name__ == 'numarray':
        ar = _array.fromstring(data, t, shape)
        ar._strides = fake_strides
    elif _array.__name__ == 'Numeric':
        ar = _array.fromstring(data, t).resize(shape)
        # Dodginess follows...
        ar_obj = _PyArrayObject.from_address(id(ar))
        strides = cast(ar_obj.strides, POINTER(c_int * 2)).contents
        strides[:] = fake_strides

    return ar

def pixels2d(surface):
    '''Reference pixels into a 2d array.

    Create a new 2D array that directly references the pixel values in a
    Surface.  Any changes to the array will affect the pixels in the Surface.
    This is a fast operation since no data is copied.

    Pixels from a 24-bit Surface cannot be referenced, but all other Surface
    bit depths can.

    The Surface this references will remain locked for the lifetime of the
    array (see the Surface.lock() method).

    :Parameters:
         `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''       

def array3d(surface):
    '''Copy pixels into a 3d array.

    Copy the pixels from a Surface into a 3D array. The bit depth of the
    surface will control the size of the integer values, and will work for any
    type of pixel format.

    This function will temporarily lock the Surface as pixels are copied (see
    the Surface.lock() method).

    :Parameters:
         `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''    

def pixels3d(surface):
    '''Reference pixels into a 3d array.

    Create a new 3D array that directly references the pixel values in a
    Surface.  Any changes to the array will affect the pixels in the Surface.
    This is a fast operation since no data is copied.

    This will only work on Surfaces that have 24-bit or 32-bit formats. Lower
    pixel formats cannot be referenced.

    The Surface this references will remain locked for the lifetime of the array
    (see the Surface.lock() method).

    :Parameters:
         `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''  

def array_alpha(surface):
    '''Copy pixel alphas into a 2d array.

    Copy the pixel alpha values (degree of transparency) from a Surface into a
    2D array. This will work for any type of Surface format. Surfaces without
    a pixel alpha will return an array with all opaque values.

    This function will temporarily lock the Surface as pixels are copied
    (see the Surface.lock() method).

    :Parameters:
         `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''  

def pixels_alpha(surface):
    '''Reference pixel alphas into a 2d array.

    Create a new 2D array that directly references the alpha values (degree of
    transparency) in a Surface.  Any changes to the array will affect the
    pixels in the Surface. This is a fast operation since no data is copied.

    This can only work on 32-bit Surfaces with a per-pixel alpha value.

    The Surface this references will remain locked for the lifetime of the
    array.

    :Parameters:
         `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''  

def array_colorkey(surface):
    '''Copy the colorkey values into a 2d array.

    Create a new array with the colorkey transparency value from each pixel. If
    the pixel matches the colorkey it will be fully tranparent; otherwise it
    will be fully opaque.

    This will work on any type of Surface format. If the image has no colorkey
    a solid opaque array will be returned.

    This function will temporarily lock the Surface as pixels are copied.

    :Parameters:
         `surface` : `Surface`
            Surface to copy.

    :rtype: Numeric array
    '''  

def make_surface(array):
    '''Copy an array to a new surface.

    Create a new Surface that best resembles the data and format on the array.
    The array can be 2D or 3D with any sized integer values.

    :Parameters:
        `array` : Numeric array
            Image data.

    :rtype: `Surface`
    '''

def blit_array(surface, array):
    '''Blit directly from the values in an array.

    Directly copy values from an array into a Surface. This is faster than
    converting the array into a Surface and blitting. The array must be the
    same dimensions as the Surface and will completely replace all pixel
    values.

    This function will temporarily lock the Surface as the new values are
    copied.

    :Parameters:
        `surface` : `Surface`
            Surface to blit to.
        `array` : numpy, numarray or Numeric 2D or 3D array
            Image data.

    :rtype: `Surface`
    '''
    _check_array()

    surf = surface._surf
    bpp = surf.format.BytesPerPixel

    # Get shape
    if hasattr(array, 'shape'):
        # numpy, numarray
        shape = array.shape
        is_Numeric = False
    else:
        import Numeric
        shape = Numeric.shape(array)
        is_Numeric = True

    if not (len(shape) == 2 or (len(shape) == 3 and shape[2] == 3)):
        raise ValueError, 'must be a valid 2d or 3d array\n'

    if len(shape) == 3:
        raise NotImplementedError, 'TODO, 3D'

    if bpp <= 0 or bpp > 4:
        raise ValueError, 'unsupport bit depth for surface'

    if surf.w != shape[0] or surf.h != shape[1]:
        raise ValueError, 'array must match surface dimensions'

    # Get strides
    if hasattr(array, 'strides'):
        # numpy
        strides = array.strides
    elif hasattr(array, '_strides'):
        # numarray
        strides = array._strides
    else:
        # Numeric
        array_obj = _PyArrayObject.from_address(id(array))
        strides = tuple(cast(array_obj.strides, 
                             POINTER(c_int * len(shape))).contents)

    print 'strides ', strides

    data = array.tostring()

    # Get element size
    if callable(array.itemsize):
        # numarray, Numeric
        itemsize = array.itemsize()
    else:
        # numpy
        itemsize = array.itemsize

    # XXX Following probably doesn't work for RGB->RGBA or RGBA->RGB
    print itemsize, bpp
    if itemsize > bpp:
        print 'a'
        # Trim bytes from each pixel, keep least significant byte(s)
        if SDL_BYTEORDER == SDL_LIL_ENDIAN:
            pattern = '(%s)%s' % ('.' * bpp, '.' * (itemsize - bpp))
        else:
            pattern = '%s(%s)' % ('.' * (itemsize - bpp), '.' * bpp)
        data = ''.join(re.compile(pattern, flags=re.DOTALL).findall(data))
    elif itemsize < bpp:
        print 'b'
        # Add pad bytes to each pixel, at most significant end
        pad = '\0' * (bpp - itemsize)
        pixels = re.compile('.' * itemsize, flags=re.DOTALL).findall(data)
        data = pad.join(pixels)
        if SDL_BYTEORDER == SDL_LIL_ENDIAN:
            data = data + pad
        else:
            data = pad + data

    # Add zeros pad for pitch correction
    pitchdiff = surf.pitch - surf.w * bpp
    if pitchdiff > 0:
        print 'c'
        pad = '\0' * pitchdiff
        rows = re.compile('.' * surf.w * bpp, flags=re.DOTALL).findall(data)
        data = pad.join(rows) + pad

    # Good to go
    surface.lock()
    memmove(surf.pixels.ptr, data, len(data))
    surface.unlock()

def map_array(surface, array):
    '''Map a 3d array into a 2d array.

    Convert a 3D array into a 2D array. This will use the given Surface format
    to control the conversion.

    :Parameters:
        `surface` : `Surface`
            Surface with format information.
        `array` : Numeric array
            Array to convert.

    :rtype: Numeric array
    '''
