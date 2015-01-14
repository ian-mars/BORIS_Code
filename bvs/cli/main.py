from __future__ import absolute_import, print_function, division

import click

from bvs.eyeparse import *

@click.group()
def main():
    #click.echo("Tesing the main function!")
    pass


@main.command()
@click.argument('fpath')#, help='Path to the EyeLink ascii file.')
def parse(fpath):
    """
    Parse an ascii eyelink file into a file with gaze info
    """

    import os

    eye_data_parser = EyeDataParser(fpath)
    print("Parsing...")
    eye_data_parser.parse_data()
    print("Done!\n")

    print("Creating DataFrames...")
    eye_dfs = EyeDataFrameCreator(eye_data_parser)

    # calc_target_locations(eye_dfs.)

    # TODO Decide where to put the parsed data. Putting it in a test file for now.
    # Probably want to make a list of current subjects and tasks
    out_fpath = './testing/parser_output'
    if not os.path.exists(out_fpath):
	    os.makedirs(out_fpath)
    eye_dfs.task_df.to_hdf(os.path.join(out_fpath, 'task_output.h5'), 'task')
    eye_dfs.radial_target_df.to_hdf(os.path.join(out_fpath, 'rt_output.h5'), 'rt')
    eye_dfs.frame_df.to_hdf(os.path.join(out_fpath, 'frame_output.h5'), 'frames', index=False)