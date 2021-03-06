"""
Custom 2D FFT functions.

numpy, scipy and mkl_fft do not have fft implemented such that output argument 
can be provided. This implementation adds the output argument for fft2 and 
ifft2 functions. 

Also, for mkl_fft and scipy, the computation can be performed in parallel using ThreadPool.

"""
from __future__ import absolute_import, print_function, division

from dtmm.conf import DTMMConfig, CDTYPE, MKL_FFT_INSTALLED, SCIPY_INSTALLED
import numpy as np

import numpy.fft as npfft

from multiprocessing.pool import ThreadPool

from functools import reduce

if MKL_FFT_INSTALLED == True:
    import mkl_fft
    
if SCIPY_INSTALLED == True:
    import scipy.fftpack as spfft

def _set_out_mkl(a,out):
    if out is not a:
        if out is None:
            out = a.copy()
        else:
            out[...] = a 
    return out

def _set_out(a,out):
    if out is not a:
        if out is None:
            out = np.empty_like(a)
    return out

def _copy(x,y):
    y[...] = x

_copy_if_needed = lambda x,y: _copy(x,y) if x is not y else None
    
def _sequential_inplace_fft(fft,array):
    [fft(d,overwrite_x = True) for d in array] 

def _sequential_fft(fft,array, out):
    if out is array:
        [_copy_if_needed(fft(d, overwrite_x = True),out[i]) for i,d in enumerate(array)] 
    else:
        [_copy_if_needed(fft(d),out[i]) for i,d in enumerate(array)] 

def _optimal_workers(size, nthreads):
    if size%nthreads == 0:
        return nthreads
    else:
        return _optimal_workers(size, nthreads-1)
    
def _reshape(a):
    shape = a.shape
    newshape = reduce((lambda x,y: x*y), shape[:-2] or [1])
    if DTMMConfig.nthreads > 1:
        n = _optimal_workers(newshape,DTMMConfig.nthreads)
        newshape = (n,newshape//n,) + shape[-2:]
    else:
        newshape = (newshape,) + shape[-2:]
    a = a.reshape(newshape)
    return shape, a    

def __mkl_fft(fft,a,out):
    out = _set_out_mkl(a,out)
    shape, out = _reshape(out)
    if DTMMConfig.nthreads > 1:
        pool = ThreadPool(DTMMConfig.nthreads)
        workers = [pool.apply_async(_sequential_inplace_fft, args = (fft,d)) for d in out] 
        results = [w.get() for w in workers]
        pool.close()
    else:
        _sequential_inplace_fft(fft,out)
    return out.reshape(shape)    

def _mkl_fft2(a,out = None):
    return __mkl_fft(mkl_fft.fft2,a,out)

def _mkl_ifft2(a,out = None):
    return __mkl_fft(mkl_fft.ifft2,a,out)


def __sp_fft(fft,a,out):
    out = _set_out(a,out)
    shape, a = _reshape(a)
    shape, out = _reshape(out)
    if DTMMConfig.nthreads > 1:
        pool = ThreadPool(DTMMConfig.nthreads)
        workers = [pool.apply_async(_sequential_fft, args = (fft,d,out[i])) for i,d in enumerate(a)] 
        results = [w.get() for w in workers]
        pool.close()
    else:
        _sequential_fft(fft,a,out)
    return out.reshape(shape)   

#def __sp_fft(fft,a,out):
#    if out is None:
#        return fft(a)
#    elif out is a:
#        out = fft(a, overwrite_x = True)
#        if out is a:
#            return out
#        else:
#            a[...] = out
#        return a
#    else:
#        out[...] = fft(a)
#        return out
        
def _sp_fft2(a, out = None):
    return __sp_fft(spfft.fft2, a, out)
    
def _sp_ifft2(a, out = None):
    return __sp_fft(spfft.ifft2, a, out)        

def __np_fft(fft,a,out):
    if out is None:
        return fft(a)
    else:
        out[...] = fft(a)
        return out
        
def _np_fft2(a, out = None):
    return __np_fft(npfft.fft2, a, out)
    
def _np_ifft2(a, out = None):
    return __np_fft(npfft.ifft2, a, out)       

                
def fft2(a, out = None):
    """Computes fft2 of the input complex array.
    
    Parameters
    ----------
    a : array_like
        Input array (must be complex).
    out : array or None, optional
        Output array. Can be same as input for fast inplace transform.
       
    Returns
    -------
    out : complex ndarray
        Result of the transformation along the last two axes.
    """
    a = np.asarray(a, dtype = CDTYPE)
    libname = DTMMConfig["fftlib"]
    if libname == "mkl_fft":
        return _mkl_fft2(a, out)
    elif libname == "scipy":
        return _sp_fft2(a, out)
    elif libname == "numpy":
        return _np_fft2(a, out) 
    else:#default implementation is numpy
        return _np_fft2(a, out) 

    
def ifft2(a, out = None): 
    """Computes ifft2 of the input complex array.
    
    Parameters
    ----------
    a : array_like
        Input array (must be complex).
    out : array or None, optional
        Output array. Can be same as input for fast inplace transform.
       
    Returns
    -------
    out : complex ndarray
        Result of the transformation along the last two axes.
    """
    a = np.asarray(a, dtype = CDTYPE)      
    libname = DTMMConfig["fftlib"]
    if libname == "mkl_fft":
        return _mkl_ifft2(a, out)
    
    elif libname == "scipy":
        return _sp_ifft2(a, out)
    elif libname == "numpy":
        return _np_ifft2(a, out)  
    else: #default implementation is numpy
        return _np_ifft2(a, out)    
 