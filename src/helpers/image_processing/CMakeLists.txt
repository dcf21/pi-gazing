cmake_minimum_required(VERSION 3.3)
project(image_processing)

include_directories(src)
include_directories(src/frontends)
include_directories(src/frontends/converters)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(SOURCE_FILES
        src/argparse/argparse.c
        src/argparse/argparse.h
        src/backgroundSub.c
        src/backgroundSub.h
        src/gnomonic.c
        src/gnomonic.h
        src/imageProcess.c
        src/imageProcess.h
        src/jpeg/jpeg.h
        src/jpeg/jpeg_in.c
        src/png/image.h
        src/png/image_in.c
        src/png/image_out.c
        src/settings.c
        src/settings.h
        src/str_constants.h
        src/utils/asciiDouble.c
        src/utils/asciiDouble.h
        src/utils/error.c
        src/utils/error.h
        src/utils/julianDate.c
        src/utils/julianDate.h
        src/utils/lensCorrect.c
        src/utils/lensCorrect.h
        src/utils/skyClarity.c
        src/utils/skyClarity.h
        src/vidtools/color.c
        src/vidtools/color.h
        src/vidtools/uvc_compat.h
        src/vidtools/uvcvideo.h
        src/vidtools/v4l2uvc.c
        src/vidtools/v4l2uvc.h)

add_executable(rawimg2png ${SOURCE_FILES} src/frontends/converters/rawimg2png.c)
add_executable(rawimg2png3 ${SOURCE_FILES} src/frontends/converters/rawimg2png3.c)
add_executable(rawvid2frames ${SOURCE_FILES} src/frontends/converters/rawvid2frames.c)
add_executable(rawvid2mp4_libav ${SOURCE_FILES} src/frontends/converters/rawvid2mp4_libav.c)
add_executable(rawvid2mp4_openmax ${SOURCE_FILES} src/frontends/converters/rawvid2mp4_openmax.c)
add_executable(lensCorrect ${SOURCE_FILES} src/frontends/lensCorrect.c)
add_executable(multiply ${SOURCE_FILES} src/frontends/multiply.c)
add_executable(resize ${SOURCE_FILES} src/frontends/resize.c)
add_executable(skyClarity ${SOURCE_FILES} src/frontends/skyClarity.c)
add_executable(subtract ${SOURCE_FILES} src/frontends/subtract.c)
