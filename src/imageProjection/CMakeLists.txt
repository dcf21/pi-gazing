cmake_minimum_required(VERSION 3.3)
project(imageProjection)

include_directories(src)
include_directories(src/frontends)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(SOURCE_FILES
        src/asciiDouble.c
        src/asciiDouble.h
    src/backgroundSub.c
    src/backgroundSub.h
    src/error.c
    src/error.h
    src/gnomonic.c
    src/gnomonic.h
    src/image.h
    src/image_in.c
    src/image_out.c
    src/imageProcess.c
    src/imageProcess.h
    src/readConfig.c
    src/readConfig.h
    src/settings.c
    src/settings.h
    src/str_constants.h)

add_executable(barrel ${SOURCE_FILES} src/frontends/barrel.c)
add_executable(camfit ${SOURCE_FILES} src/frontends/cameraFit.c)
add_executable(multiply ${SOURCE_FILES} src/frontends/multiply.c)
add_executable(stack ${SOURCE_FILES} src/frontends/stack.c)
add_executable(subtract ${SOURCE_FILES} src/frontends/subtract.c)