import subprocess
import numpy as np
from optparse import OptionParser
import sys
import pickle
import os.path
import os
import shlex

def get_mouse_info(key):
    """
    Returns the mouse info
    from the a dict key of the format:
    409_20130327_homecagesocial
    """

    info = key.split('_')
    mouse_number = info[0]
    date = info[1]
    exp_type = info[2]
    if exp_type == 'homecagesocial':
        exp_type = 'social'
    elif exp_type == 'homecagenovel':
        exp_type = 'novel'

    return mouse_number, date, exp_type

## Get list of times and fluor values for each movie
def get_movie_file(key, path_to_data):
    """
    Given a key of the format: 409_20130327_homecagesocial
    and a path to the folder containing the folders for 
    each day of data (i.e. 20130327), returns a full
    path to the .avi file containing the movie for that trial
    (i.e. the homecagesocial trial for mouse 409 on day 20130327)
    """
    mouse_number, date, exp_type = get_mouse_info(key)
    movie_file = path_to_data+date+'/'+mouse_number+'_'+exp_type
    return movie_file

def get_output_file(key, path_to_data, output_folder):
    mouse_number, date, exp_type = get_mouse_info(key)

    output_dir = path_to_data+date+'/'+output_folder
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = output_dir+'/'+mouse_number+'_'+exp_type
    return output_file


def load_start_times(start_times_file):
    all_start_times_dict = dict()
    f = open(start_times_file, 'r')
    for line in f:
        info = line.split(',')
        all_start_times_dict[info[0]] = int(info[1])
    f.close()
    return all_start_times_dict


def load_clip_times(clip_list_file, path_to_data, start_times_file, output_folder):
    """
    Loads the three dictionaries all_peak_times_dict, all_peak_vals_dict, 
    and all_local_times_dict from the provided .pkl clip_list_file, which
    was produced by print_spike_times in group_analysis.py.
    The key of each dict is a name of the format: 409_20130327_homecagesocial
    and the number of entries for each key is variable.

    Then, makes a new dict with the format:
    dict{409_20130327_homecagesocial: 
            dict{movie_file: path to movie file (will check for avi or mp4), 
                 peak_times: array with times of each peak,
                 peak_vals: array with vals of each peak,
                 local_times: array with local times of each peak
                }
        }
    """
    print "clip_list_file", clip_list_file
    pkl_file = open(clip_list_file, 'rb')
    all_peak_times_dict = pickle.load(pkl_file)
    all_peak_vals_dict = pickle.load(pkl_file)
    all_local_times_dict = pickle.load(pkl_file)
    # all_interaction_start_times_dict = pickle.load(pkl_file)
    # all_interaction_end_times_dict = pickle.load(pkl_file)
    all_start_times_dict = load_start_times(start_times_file)

    movie_info_dict = dict()
    for key in all_peak_times_dict.keys():
        movie_info = dict()
        movie_info['movie_file'] = get_movie_file(key, path_to_data)
        movie_info['output_file'] = get_output_file(key, path_to_data, output_folder)
        movie_info['peak_times'] = all_peak_times_dict[key]
        movie_info['peak_vals'] = all_peak_vals_dict[key]
        movie_info['local_times'] = all_local_times_dict[key]
        movie_info['name'] = key
        movie_info['start_time'] = all_start_times_dict[key] #TO DO - update this to higher precision
        # movie_info['interaction_start'] = all_interaction_start_times_dict[key]
        # movie_info['interaction_end'] = all_interaction_end_times_dict[key]

        movie_info_dict[key] = movie_info
    return movie_info_dict

def get_time_string(t, prefix):
    start = t - prefix
    hr = int(np.floor(start/3600.0))
    min = int(np.floor((start - hr*3600)/60.0))
    sec = int(start - hr*3600 - min*60)
    return str(hr)+':'+str(min)+':'+str(sec)

def splice_clips(list_file, output_file):
    """
    Calling ffmpeg in the command line,
    joins the clips (in order) listed in 'list_file', 
    a text file with the format for each line: 
    file file1.mp4
    file file2.mp4
    """
    cmd = ['ffmpeg']
    cmd += ['-f', 'concat']
    cmd += ['-i', list_file]
    cmd += ['-c', 'copy']
    cmd += [output_file + '_clips.mp4']
    #cmd += ['> /dev/null 2>&1 < /dev/null'] 

    cmd_string = ''.join(["%s " % el for el in cmd])
    print '-->Running: ', cmd_string
    p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()

def delete_clips(clip_list_arr):
    """
    Deletes the clips listed in provided array
    (specified by full path/filename.mp4)
    The example use of this deleting all of the
    clips that were generated for the sake
    of splicing together into a larger video.
    """

    for clip in clip_list_arr:
        os.remove(clip)

def write_list_file(output_file, clip_list_arr):
    """
    Write all clip filenames to a text file for use
    by ffmpeg concat (i.e. the function splice_clips).
    """
    list_file = output_file+'_clip_list.txt'
    f = open(list_file, 'w')
    for clip in clip_list_arr:
        line = 'file '+clip
        f.write("%s\n" % line)
        # Add in a divider movie between clips? (it could go here)
    f.close()
    # print 'list_file', list_file
    # print clip_list_arr

    return list_file

def check_video_timestamps(movie_file, desired_format='.mp4', desired_framerate=30):
    """
    Check whether frame rate is 30fps (the original video files should
    be 10fps). If not, convert framerate, and add timecode stamps
    to the videos.
    """

    if not os.path.isfile(movie_file+'_tt'+desired_format):
        #Convert file to 30 fps
        cmd = ['ffmpeg', '-i', movie_file+desired_format]
        cmd += ['-r', str(desired_framerate)]
        cmd += ['-y', movie_file+'_t'+desired_format]
        cmd_string = ''.join(["%s " % el for el in cmd])  
        print '-->Running: ', cmd_string
        p = subprocess.Popen(cmd, shell=False)
        p.wait()

        #Add time code to file
        cmd = 'ffmpeg -i '+movie_file+'_t'+desired_format+' -vf drawtext=\"fontfile=/opt/X11/share/fonts/TTF/VeraMoBd.ttf: timecode=\'00\:00\:00\:00\':rate=30: fontcolor=white@0.8: x=7: y=460\" -an -y '+movie_file+'_tt'+desired_format
        args = shlex.split(cmd)
        print args
        p = subprocess.Popen(args, shell=False)
        p.wait()

        os.remove(movie_file+'_t'+desired_format)





def  check_video_format(movie_file, desired_format='.mp4', original_format='.avi'):
    """
    The original (data) video should be in .avi format. But 
    we may need the video to be in a different format (i.e. mp4)
    for proper processing. This function checks whether the desired_format
    video exists. If not, then it converts (copies) the original_format
    to the desired_format.
    """

    if not os.path.isfile(movie_file+original_format):
        print 'Error. avi file does not exist:'+movie_file+'.avi'
    if not os.path.isfile(movie_file+desired_format):
        cmd = ['ffmpeg']
        cmd += ['-i', movie_file+original_format]
        cmd += [movie_file+desired_format]
        cmd_string = ''.join(["%s " % el for el in cmd])
        print '-->Running: ', cmd_string
        p = subprocess.Popen(cmd, shell=False)
        p.wait()

    check_video_timestamps(movie_file, desired_format='.mp4', desired_framerate=30)




def cut_into_clips(movie_info, peak_thresh, clip_window, output_file):
    """
    Given movie_info (which contains a 'movie_file', a 
    list of times at which to cut clips ('peak_times'),
    and values to judge the quality of the clip against
    a threshold ('peak_vals', vs. 'peak_thresh'), and a 
    'start_time' which indicates the length in seconds
    of buffer at the beginning of the video which
    must be added to the listed times in 'peak_times',
    cuts clips and saves them using the output_file
    template (i.e. path/movie_name).

    Returns an array listing the file paths to each
    saved clip.
    These clips should only be temporary, and can be
    deleted with the function delete_clips().
    """

    movie_file = movie_info['movie_file']
    peak_times = movie_info['peak_times']
    peak_vals = movie_info['peak_vals']
    start_time = movie_info['start_time']
    clip_list_arr = []
    ## Now cut clips (do this the lazy way for now,
    ## saving to individual files, figure out pipes
    ## after you get this working). 
    for i in range(len(peak_times)):
        t = peak_times[i] + start_time
        v = peak_vals[i]
        start = get_time_string(t, clip_window[0])
        duration = get_time_string(clip_window[1], 0)
        print 'start', start, t - clip_window[0]
        new_file = output_file+'_'+str(int(t))+'_clip.mp4'
        if v>peak_thresh:
            if len(clip_list_arr) == 0 or clip_list_arr[-1] != new_file:
                clip_list_arr.append(new_file)

                cmd = ['ffmpeg']
                cmd += ['-i', movie_file+'.mp4']
                cmd += ['-ss', start]
                cmd += ['-t', duration]
                cmd += ['-vf']
                cmd += ['drawbox=0:0:'+str(int(v*1000))+':'+str(int(v*1000))+':red']
                cmd += [new_file]
                #cmd += ['> /dev/null 2>&1 < /dev/null'] #not 100% sure what this does
                                                        # it is supposed to not send
                                                        # output to the PIPE buffer

                cmd_string = ''.join(["%s " % el for el in cmd])
                print '-->Running: ', cmd_string
                p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.wait()

    return clip_list_arr

def cut_and_splice_clips(movie_info, clip_window, peak_thresh=0.05):
    """
    Given a dict containing the 'movie_file', 'peak_times', 
    'peak_vals', 'start_time', and 'name', splice a movie clip 
    of clip_window[0] seconds before the peak_time and
    clip_window[1] seconds after the peak_time for all times
    in peak_times where peak_val > peak_thresh.
    """

    movie_file = movie_info['movie_file']
    output_file = movie_info['output_file']

    check_video_format(movie_file, desired_format='.mp4')
    clip_list_arr = cut_into_clips(movie_info, peak_thresh, clip_window, output_file)
    list_file = write_list_file(output_file, clip_list_arr)
    splice_clips(list_file, output_file)
    delete_clips(clip_list_arr)


if __name__ == '__main__':
    ## The path_to_data is the folder containing folders corresponding to each trial date.
    path_to_data='/Users/isaackauvar/Dropbox/Fiberkontrol/Fiberkontrol_Data/Lisa_Data/'
    start_times_file='/Users/isaackauvar/Dropbox/Fiberkontrol/Fiberkontrol_Data/Lisa_Data/video_start_times_precise.txt'

    ## The path_to_clip_lists is the folder containing multiple .pkl which each contain
    ## three dicts: all_peak_times_dict, all_peak_vals_dict, all_local_times_dict
    ## where the key of each dict is a name of the format: 409_20130327_homecagesocial
    ## and the number of entries for each key is variable.
   # path_to_clip_lists = '/Users/isaackauvar/Documents/2012-2013/ZDlab/FiberKontrol/Results/Cell/Plots/Finalz_including_20130920/print-spike-times'

    parser = OptionParser()
    parser.add_option("-o", "--output-folder", dest="output_folder", 
                      default='test', 
                      help=("Specify the name (not full path) of the output folder "
                            "to contain the output movies."))

    parser.add_option("", "--behavior-time-window", dest="behavior_time_window",default='0:0',
                      help="Specify a time window in which to choose peaks, in format before:after.")

    parser.add_option("", "--clip-window", dest="clip_window",default='0:1',
                      help="Specify a time window in which to display video clip"
                            " around given time points, in format before:after.")


    (options, args) = parser.parse_args()

    behavior_time_window = np.array(options.behavior_time_window.split(':'), dtype='float32') 
    clip_window = np.array(options.clip_window.split(':'), dtype='float32') 
    output_folder = options.output_folder

    # Check for required input path
    if len(args) < 1:
        print 'You must supply at a path to the .pkl file to be used'
        print ' (i.e. generated by group_analysis.py) which should contain three dicts:'
        print ' all_peak_times_dict, all_peak_vals_dict, all_local_times_dict,'
        print ' where the key of each dict is a name of the format: 409_20130327_homecagesocial .' 
        sys.exit(1)

    clip_list_file = args[0]
    movie_info_dict = load_clip_times(clip_list_file, path_to_data, start_times_file, output_folder)

    for key in movie_info_dict:
        print key
       # cut_and_splice_clips(movie_info_dict[key], clip_window=clip_window)
        
        movie_file = movie_info_dict[key]['movie_file']
        #check_video_timestamps(movie_file)
        #check_video_format(movie_file)



"""
#REFERENCE FOR FFMPEG COMMAND LINE COMMANDS
datapath=/Users/isaackauvar/Dropbox/Fiberkontrol/Fiberkontrol_Data/Lisa_Data

ffmpeg -i 407_social.avi 407_social.mp4
ffmpeg -i 407_social.mp4 -ss 00:02:21 -t 00:00:10 407_clip.mp4

ffmpeg -i 401_social.avi 401_social.mp4
ffmpeg -i 401_social.mp4 -ss 00:02:21 -t 00:00:10 401_clip.mp4

ffmpeg -f concat -i mylist.txt -c copy output.mp4

mylist.txt:
file 407_clip.mp4
file 401_clip.mp4

ffmpeg -i 407_clip.mp4 -vf drawbox=10:10:50:50:red,drawbox=100:100:200:200:green 407_box.mp4

ffmpeg -f concat -i <(for f in ./*.wav; do echo "file '$f'"; done) -c copy output.wav

#for adding text - this does not currently work on my installation of ffmpeg
ffmpeg -i 407_clip.mp4 -vf \
   drawtext="fontfile=/usr/share/fonts/truetype/ttf-dejavu/DejaVuSerif.ttf: \
   text='Text to write is this one, overlaid':fontsize=20:fontcolor=red:x=100:y=100" \
   with_text3.mp4

ffmpeg -i 407_clip.mp4 -vf drawtext="fontfile=/usr/share/fonts/truetype/ttf-dejavu/DejaVuSerif.ttf: text='\%T': fontcolor=white@0.8: x=7: y=460" with_text3.mp4

#for adding an overlay video
ffmpeg -i 407_clip.mp4 -i 407_box.mp4  -filter_complex "[0:v] setpts=PTS-STARTPTS, scale=640x480 [background]; [1:v] setpts=PTS-STARTPTS, scale=200x100 [upperleft]; [background][upperleft] overlay=shortest=1" -c:v libx264 overlay_output.mp4


#convert framerate - this is super sketchy to me, but it won't print the timestamp for the 10fps that the video is at.
ffmpeg -i 407_social.mp4 -r 30 -y 407_social_30.mp4

#Adding timecode
ffmpeg -i /Users/isaackauvar/Documents/2012-2013/ZDlab/Test_video_extract/30fps_407_clip.mp4  -vf drawtext="fontfile=/opt/X11/share/fonts/TTF/VeraMoBd.ttf: timecode='00\:00\:00\:00':rate=30: fontcolor=white@0.8: x=7: y=460" -an -y with_text3.mp4

#checking framerate
ffmpeg -i 407_social_30.mp4 2>&1 | sed -n "s/.*, \(.*\) fp.*/\1/p"

"""



