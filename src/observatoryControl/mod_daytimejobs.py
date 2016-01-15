# mod_daytimejobs.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os

import mod_settings

# This file defines the commands which daytimeJobs.py uses to do tasks such as encoding videos

# This is the template command used when we are not doing real-time observing, but instead recording raw H264 video
# all night and analysing it in the morning
rawH264ToTriggers = "%(binary_path)s/debug/analyseH264_libav %(input)s %(tstamp)s %(fps)s %(triggermask)s %(cameraId)s"

# This is the template command used to convert a raw image frame into a PNG image
rawImgToPng = "%(binary_path)s/rawimg2png %(input)s %(filename_out)s %(produceFilesWithoutLC)s %(stackNoiseLevel)s " \
              "%(barrel_a)s %(barrel_b)s %(barrel_c)s"

# This is the template command used to convert a raw image frame into three PNG images, one for each colour channel
rawImgToPng3 = "%(binary_path)s/rawimg2png3 %(input)s %(filename_out)s %(produceFilesWithoutLC)s %(stackNoiseLevel)s " \
               "%(barrel_a)s %(barrel_b)s %(barrel_c)s"

# This is the template command for converting a raw video file into an H264-encoded MP4 file
# We use a different command on a Raspberry Pi, as it has a hardware H264 encoded (OpenMAX), and avconv will
# run very slowly
if mod_settings.settings['i_am_a_rpi']:
    rawVidToMp4 = "timeout 2m %(binary_path)s/rawvid2mp4_openmax       %(input)s /tmp/pivid_%(pid)s.h264 ; " \
                  "avconv -i \"/tmp/pivid_%(pid)s.h264\" -c:v copy -f mp4 %(filename_out)s.mp4 ; " \
                  "rm /tmp/pivid_%(pid)s.h264"
else:
    rawVidToMp4 = "%(binary_path)s/rawvid2mp4_libav %(input)s %(filename_out)s.mp4"

# The list dayTimeTasks is a list of all of the jobs that need to be done in the day time.
# Each task is defined as a list of properties

# 0. Name. This is the name of the task. It will have an associated high water mark in the database.
# 1. Nmax. Maximum number of copies of this job which can run in parallel.
#          NB: OpenMAX can only be used by one process at a time
# 2. Folder of input files which need processing
# 3. Folder to put output files into
# 4. The file extension we should look for to identify the files we need to process
# 5. The file extension which gets given to output files (so we can identify jobs already done)
# 6. The shell command we use to do this job

dayTimeTasks = [
    [
        'rawvideo',
        1,
        [['rawvideo', ['triggers_raw_nonlive', 'timelapse_raw_nonlive'], 'h264', '???', rawH264ToTriggers]]
    ], [
        'triggers_rawimg',
        3,
        [['triggers_raw_nonlive', ['triggers_img_processed'], 'rgb', 'png', rawImgToPng],
         ['triggers_raw_live', ['triggers_img_processed'], 'rgb', 'png', rawImgToPng],
         ['triggers_raw_nonlive', ['triggers_img_processed'], 'sep', 'png', rawImgToPng3],
         ['triggers_raw_live', ['triggers_img_processed'], 'sep', 'png', rawImgToPng3]
         ]
    ], [
        'triggers_rawvid',
        1,
        [['triggers_raw_nonlive', ['triggers_vid_processed'], 'vid', 'mp4', rawVidToMp4],
         ['triggers_raw_live', ['triggers_vid_processed'], 'vid', 'mp4', rawVidToMp4]
         ]
    ], [
        'timelapse_rawimg',
        3,
        [['timelapse_raw_nonlive', ['timelapse_img_processed'], 'rgb', 'png', rawImgToPng],
         ['timelapse_raw_live', ['timelapse_img_processed'], 'rgb', 'png', rawImgToPng]
         ]
    ],
]

# Make a dictionary from a file containing metadata keys and values on lines
def file_to_dict(in_filename, must_be_float=False):
    output = {}
    if not os.path.exists(in_filename):
        return output
    for line in open(in_filename):
        if line.strip() == "":
            continue
        if line[0] == "#":
            continue
        words = line.split()
        keyword = words[0]
        val = words[1]
        try:
            val = float(val)
        except ValueError:
            if must_be_float:
                continue
        output[keyword] = val
    return output

# Convert a dictionary of metadata keys and values into a file with keys and values on lines
def dict_to_file(out_filename, in_dict):
    f = open(out_filename, "w")
    keywords = in_dict.keys()
    keywords.sort()
    for keyword in keywords:
        value = in_dict[keyword]
        f.write("%16s %s\n" % (keyword, value))
    f.close()
