"""
Module with auxillary
    jit-compiled functions
    for resize of
    DICOM-scans
"""

from numba import jit
import scipy.ndimage
import numpy as np


@jit(nogil=True)
def resize_patient_numba(patient, out_patient, res, shape=None, order=3):
    """
    resizes 3d-scan for one patient
        args
        - patient: ndarray with patient data
        - out_patient: ndarray, in which patient data
            after resize should be put
        - order: order of interpolation
        - res: out array for the whole batch
            not needed here, will be used later by post default

        * shape of resized array has to be inferred
            from out_patient
    """
    # an actual shape is inferred from out_patient
    _ = shape

    # define resize factor
    res_factor = np.array(out_patient.shape) / np.array(patient.shape)

    # perform resizing and put the result into out_patient
    out_patient[:, :, :] = scipy.ndimage.interpolation.zoom(patient, res_factor, order=order)

    # return out-array for the whole batch
    # and shape of out_patient
    return res, out_patient.shape