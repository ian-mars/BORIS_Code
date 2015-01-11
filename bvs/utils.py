"""
Methods that process the eye movement data, including epipolar reprojection,
calculating version, vergence, torsion, and the 3D fixation point.
"""

import numpy as np

# from ndssettings import *

# DEG_PER_RAD = 180/np.pi
# RAD_PER_DEG = np.pi/180

def calc_target_locations(df, ipd):

    target_directions = df['target', 'direction']
    target_eccentricities = df['target', 'eccentricity']
    target_dists = df['target', 'distance']

    # target x and y positions in world coords (z position is just target dist)
    target_hypotenuses = target_dists * np.tan(target_eccentricities*RAD_PER_DEG)
    x = target_hypotenuses * np.cos(target_eccentricities*RAD_PER_DEG)
    y = target_hypotenuses * np.sin(target_eccentricities*RAD_PER_DEG)

    df['target', 'x'] = x
    df['target', 'y'] = y

    target_expected_fixation_pts = np.c_[x, y, target_dists]

    vergences = calc_vergence(target_expected_fixation_pts, ipd)
    versions = calc_version(target_expected_fixation_pts)

    df['target', 'vergence'] = vergences
    df['target', 'version'] = versions

def calc_fixation_pts(task_df, rt_df, ipd):

    href_center = find_href_center(rt_df)
    for df in [task_df, rt_df]:
        for eye in ['left', 'right']:
            convert_href_to_ndsref(df, eye=eye, center=href_center)
        ndsref_to_fixation(df, ipd)

def find_href_center(rt_df):

    central_target = (rt_df['target', 'direction'] == 0) & \
                     (rt_df['target', 'eccentricity'] == 0) & \
                     (rt_df['target', 'distance'] == calibration_dist) & \
                     (rt_df['target', 'rep'] == 1)

    good_data = rt_df['both', 'quality'] == 'GOOD'

    central_data = rt_df[[('left', 'href x'), ('left', 'href y'),
                          ('right', 'href x'), ('right', 'href y')]][central_target & good_data]

    return central.mean()


def convert_href_to_ndsref(df, eye, center):

    CM_PER_HREF_UNIT = calibration_dist / HREF_DIST
    # recenter href coordinates and convert to cm to get ndsref for each eye
    # in the world coordinate system
    df[eye, 'ndsref x'] = (df[eye, 'href x'] - center[eye, 'href x']) * CM_PER_HREF_UNIT
    df[eye, 'ndsref y'] = (df[eye, 'href y'] - center[eye, 'href y']) * CM_PER_HREF_UNIT

    # flip y-axis so up is positive
    df[eye, 'ndsref y'] *= -1

    df[eye, 'ndsref z'] = calibration_dist

def ndsref_to_fixation(df, ipd):

    ndsref = df[[('left', 'ndsref x'), ('left', 'ndsref y'), ('left', 'ndsref z'),
                 ('right', 'ndsref x'), ('right', 'ndsref y'), ('right', 'ndsref z')]]

    eyeref_le = ndsref['left'] - np.array([-ipd/2.0, 0, 0])
    eyeref_re = ndsref['right'] - np.array([ipd/2.0, 0, 0])

    # TODO fit eyerefs vectors to plane and project them
    
    assert 0


def calc_vergence(fixation_pt, ipd):

    fixation_pt = np.atleast_2d(fixation_pt)
    assert fixation_pt.shape[1] == 3
    eyeref_le = fixation_pt - [-ipd/2.0, 0, 0]
    eyeref_re = fixation_pt - [ipd/2.0, 0, 0]

    vergence = calc_angle(eyeref_le, eyeref_re)

    nan_inds = np.where(np.isnan(fixation_pt).any(axis=1))
    vergence[nan_inds] = np.nan

    return vergence

def calc_version(fixation_pt):

    fixation_pt = np.atleast_2d(fixation_pt)
    assert fixation_pt.shape[1] == 3
    z_dir = np.array([0, 0, 1.0])

    zy_component = fixation_pt.copy()
    zy_component[:,0] = 0

    vert_version = calc_angle(z_dir, zy_component) * get_angle_direction(z_dir, zy_component, axis='x')
    horz_version = calc_angle(zy_component, fixation_pt) * get_angle_direction(fixation_pt, zy_component, axis='y')

    # flag bad/missing data with nans
    nan_inds = np.where(np.isnan(fixation_pt).any(axis=1))
    vert_version[nan_inds] = np.nan
    horz_version[nan_inds] = np.nan

    return (horz_version, vert_version)

def calc_angle(v1, v2):
    """
    Calculate the angle between two sets of vectors v1 and v2 in degrees. Inputs
    must both be Nx3 unless one argument is 1x3 or (3,).
    """

    v1, v2 = np.atleast_2d(v1, v2)  # vectors will be (1,3) or (N,3)
    assert v1.shape[1] == v2.shape[1] == 3

    v1_norm = np.sqrt(np.sum(v1**2, axis=1))
    v2_norm = np.sqrt(np.sum(v2**2, axis=1))

    v1N = v1/np.expand_dims(v1_norm, axis=1)
    v2N = v2/np.expand_dims(v2_norm, axis=1)

    cosarg = np.sum(v1N*v2N, axis=1)
    cosarg = np.min(np.c_[np.ones((cosarg.shape[0], 1)), cosarg], axis=1)

    return np.arccos(cosarg) * DEG_PER_RAD

def get_angle_direction(v1, v2, axis):
    """
    Return the direction of rotation to get v1 onto v2 about the provided axis.
    """

    axes_dict = {'x':0, 'y':1, 'z':2, 'X':0, 'Y':1, 'Z':2}
    if axis in axes_dict:
        axis = axes_dict[axis]

    v1, v2 = np.atleast_2d(v1, v2)  # vectors will be (1,3) or (N,3)

    vec_normal = np.cross(v1, v2)

    directions = np.where(vec_normal[:,axis] == 0, np.ones(vec_normal.shape[0]), np.sign(vec_normal[:,axis]))

    return directions

def get_R(theta, phi):
    """
    Convert horizontal and vertical versions into a rotation matrix. phi is the vertical rotation
    and is positive DOWNWARD, theta is the horizontal rotation and is positive LEFTWARD.
    """

    phi = phi * RAD_PER_DEG #phi is the angle of rotation about the x axis (ie vertical version)
    theta = theta * RAD_PER_DEG # theta is the angle about the y-axis (ie horizontal version)

    R_phi = np.matrix([[1, 0, 0],
                       [0, np.cos(phi), -np.sin(phi)],
                       [0, np.sin(phi), np.cos(phi)]])
    R_theta = np.matrix([[np.cos(theta), 0, -np.sin(theta)],
                         [0, 1, 0],
                         [np.sin(theta), 0, np.cos(theta)]])

    R = R_phi*R_theta

    return R.A