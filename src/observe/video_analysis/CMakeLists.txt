cmake_minimum_required(VERSION 3.3)
project(video_analysis)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

include_directories(src)
include_directories(src/analyse)
include_directories(src/argparse)
include_directories(src/frontends)
include_directories(src/jpeg)
include_directories(src/png)
include_directories(src/utils)
include_directories(src/vidtools)

set(SOURCE_FILES
        src/analyse/observe.c
        src/analyse/observe.h
        src/analyse/trigger.c
        src/analyse/trigger.h
        src/argparse/argparse.c
        src/argparse/argparse.h
        src/jpeg/jpeg.h
        src/jpeg/jpeg_in.c
        src/png/image.h
        src/png/image_in.c
        src/png/image_out.c
        src/settings_dslr.h
        src/settings.h
        src/settings_webcam.h
        src/str_constants.h
        src/utils/asciiDouble.c
        src/utils/asciiDouble.h
        src/utils/error.c
        src/utils/error.h
        src/utils/filledPoly.c
        src/utils/filledPoly.h
        src/utils/julianDate.c
        src/utils/julianDate.h
        src/utils/tools.c
        src/utils/tools.h
        src/vidtools/color.c
        src/vidtools/color.h
        src/vidtools/uvc_compat.h
        src/vidtools/uvcvideo.h
        src/vidtools/v4l2uvc.c
        src/vidtools/v4l2uvc.h)

add_executable(analyseH264_libav ${SOURCE_FILES} src/frontends/analyseH264_libav.c)
add_executable(makeBackgroundMap ${SOURCE_FILES} src/frontends/makeBackgroundMap.c)
add_executable(realtimeObserve ${SOURCE_FILES} src/frontends/realtimeObserve.c)
add_executable(realtimeObserve_dslr ${SOURCE_FILES} src/frontends/realtimeObserve_dslr.c)
add_executable(recordH264 ${SOURCE_FILES} src/frontends/recordH264.c)
add_executable(snapshot ${SOURCE_FILES} src/frontends/snapshot.c)
add_executable(videoRecord ${SOURCE_FILES} src/frontends/videoRecord.c)
