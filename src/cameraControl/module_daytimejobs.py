# module_daytimejobs.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Define the tasks we need to do
rawH264ToTriggers = '%(binary_path)s/h264observe%(opm)s %(input)s'
rawImgToJpeg      = '%(binary_path)s/rawimg2jpg         %(input)s %(outdir)s/%(date)s/%(filename)s.jpg'
rawRgbToPng       = '%(binary_path)s/rawrgb2png         %(input)s %(outdir)s/%(date)s/%(filename)s.png'
rawVidToMp4       = '%(binary_path)s/rawvid2mp4%(opm)s  %(input)s /tmp/pivid_%(pid)s.h264 ; avconv -i "/tmp/pivid_%(pid)s.h264" -c:v copy -f mp4 %(outdir)s/%(date)s/%(filename)s.mp4 ; rm /tmp/pivid_%(pid)s.h264'

#                 HWMoutput              Folder of input files      Folder of output files                          Input ext  Shell command
dayTimeTasks = [ ['rawvideo'        , [ ['rawvideo'               ,['triggers_raw_nonlive','timelapse_raw_nonlive'],'h264'   , ''] ]],
                 ['triggers_rawimg' , [ ['triggers_raw_nonlive'   ,['triggers_img_processed']                      ,'rawimg' , rawImgToJpeg],
                                        ['triggers_raw_live'      ,['triggers_img_processed']                      ,'rawimg' , rawImgToJpeg],
                                        ['triggers_raw_nonlive'   ,['triggers_img_processed']                      ,'rawrgb' , rawRgbToPng],
                                        ['triggers_raw_live'      ,['triggers_img_processed']                      ,'rawrgb' , rawRgbToPng] ]],
                 ['triggers_rawvid' , [ ['triggers_raw_nonlive'   ,['triggers_vid_processed']                      ,'rawvid' , rawVidToMp4],
                                        ['triggers_raw_live'      ,['triggers_vid_processed']                      ,'rawvid' , rawVidToMp4] ]],
                 ['timelapse_rawimg', [ ['timelapse_raw_nonlive'  ,['timelapse_img_processed']                     ,'rawimg' , rawImgToJpeg],
                                        ['timelapse_raw_live'     ,['timelapse_img_processed']                     ,'rawimg' , rawImgToJpeg] ]],
               ]

