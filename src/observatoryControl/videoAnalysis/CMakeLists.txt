cmake_minimum_required(VERSION 3.3)
project(videoAnalysis)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

include_directories(src)
include_directories(src/analyse)
include_directories(src/converters)
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
        src/jpeg/jpeg.h
        src/jpeg/jpeg_in.c
        src/png/image.h
        src/png/image_in.c
        src/png/image_out.c
        src/utils/asciidouble.c
        src/utils/asciidouble.h
        src/utils/error.c
        src/utils/error.h
        src/utils/filledPoly.c
        src/utils/filledPoly.h
        src/utils/JulianDate.c
        src/utils/JulianDate.h
        src/utils/lensCorrect.c
        src/utils/lensCorrect.h
        src/utils/tools.c
        src/utils/tools.h
        src/vidtools/color.c
        src/vidtools/color.h
        src/vidtools/uvc_compat.h
        src/vidtools/uvcvideo.h
        src/vidtools/v4l2uvc.c
        src/vidtools/v4l2uvc.h
        src/settings.h
        src/settings_dslr.h
        src/settings_webcam.h
        src/str_constants.h)

add_executable(rawimg2png ${SOURCE_FILES} src/converters/rawimg2png.c)
add_executable(rawimg2png3 ${SOURCE_FILES} src/converters/rawimg2png3.c)
add_executable(rawvid2frames ${SOURCE_FILES} src/converters/rawvid2frames.c)
add_executable(rawvid2mp4_libav ${SOURCE_FILES} src/converters/rawvid2mp4_libav.c)
add_executable(rawvid2mp4_openmax ${SOURCE_FILES} src/converters/rawvid2mp4_openmax.c)
add_executable(analyseH264_libav ${SOURCE_FILES} src/frontends/analyseH264_libav.c)
add_executable(makeMedianMap ${SOURCE_FILES} src/frontends/makeMedianMap.c)
add_executable(realtimeObserve ${SOURCE_FILES} src/frontends/realtimeObserve.c)
add_executable(realtimeObserve_dslr ${SOURCE_FILES} src/frontends/realtimeObserve_dslr.c)
add_executable(recordH264 ${SOURCE_FILES} src/frontends/recordH264.c)
add_executable(skyClarity ${SOURCE_FILES} src/frontends/skyClarity.c)
add_executable(snapshot ${SOURCE_FILES} src/frontends/snapshot.c)
add_executable(vidRec ${SOURCE_FILES} src/frontends/vidRec.c)