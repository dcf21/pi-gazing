// recordH264_openmax.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

// Record a video stream from a webcam to an H264 video file for later analysis, using openmax (hardware encoding).

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#include "argparse/argparse.h"
#include "png/image.h"
#include "utils/error.h"
#include "vidtools/v4l2uvc.h"
#include "utils/asciiDouble.h"
#include "utils/tools.h"
#include "vidtools/color.h"

#include "str_constants.h"
#include "settings.h"

static const char *const usage[] = {
    "recordH264_openmax [options] [[--] args]",
    "recordH264_openmax [options]",
    NULL,
};

/*
 * Parts of this code are borrowed from <https://github.com/tjormola/rpi-openmax-demos>
 * Copyright (C) 2013 Tuomas Jormola <tj@solitudo.net> <http://solitudo.net>
 */

#include <stdarg.h>
#include <string.h>
#include <errno.h>

#include <bcm_host.h>

#include <interface/vcos/vcos_semaphore.h>
#include <interface/vmcs_host/vchost.h>

#include <IL/OMX_Core.h>
#include <IL/OMX_Component.h>
#include <IL/OMX_Video.h>
#include <IL/OMX_Broadcom.h>

// Hard coded parameters
#define VIDEO_BITRATE   6000000

static int want_quit = 0;

// Fetch an input frame from v4l2
int fetchFrame(struct video_info *video_in, unsigned char *tmpc, int upside_down) {
    int status = uvcGrab(video_in);
    if (status) return status;
    Pyuv422to420(video_in->frame_buffer, tmpc, video_in->width, video_in->height, upside_down);
    return 0;
}

// Dunno where this is originally stolen from...
#define OMX_INIT_STRUCTURE(a) \
    memset(&(a), 0, sizeof(a)); \
    (a).nSize = sizeof(a); \
    (a).nVersion.nVersion = OMX_VERSION; \
    (a).nVersion.s.nVersionMajor = OMX_VERSION_MAJOR; \
    (a).nVersion.s.nVersionMinor = OMX_VERSION_MINOR; \
    (a).nVersion.s.nRevision = OMX_VERSION_REVISION; \
    (a).nVersion.s.nStep = OMX_VERSION_STEP

// Our application context passed around
// the main routine and callback handlers
typedef struct {
    OMX_HANDLETYPE encoder;
    OMX_BUFFERHEADERTYPE *encoder_ppBuffer_in;
    OMX_BUFFERHEADERTYPE *encoder_ppBuffer_out;
    int encoder_input_buffer_needed;
    int encoder_output_buffer_available;
    int flushed;
    VCOS_SEMAPHORE_T handler_lock;
} appctx;

// I420 frame stuff
typedef struct {
    int width;
    int height;
    size_t size;
    int buf_stride;
    int buf_slice_height;
    int buf_extra_padding;
    int p_offset[3];
    int p_stride[3];
} i420_frame_info;

// Stolen from video-info.c of gstreamer-plugins-base
#define ROUND_UP_2(num) (((num)+1)&~1)
#define ROUND_UP_4(num) (((num)+3)&~3)

static void get_i420_frame_info(int width, int height, int buf_stride, int buf_slice_height, i420_frame_info *info) {
    info->p_stride[0] = ROUND_UP_4(width);
    info->p_stride[1] = ROUND_UP_4(ROUND_UP_2(width) / 2);
    info->p_stride[2] = info->p_stride[1];
    info->p_offset[0] = 0;
    info->p_offset[1] = info->p_stride[0] * ROUND_UP_2(height);
    info->p_offset[2] = info->p_offset[1] + info->p_stride[1] * (ROUND_UP_2(height) / 2);
    info->size = info->p_offset[2] + info->p_stride[2] * (ROUND_UP_2(height) / 2);
    info->width = width;
    info->height = height;
    info->buf_stride = buf_stride;
    info->buf_slice_height = buf_slice_height;
    info->buf_extra_padding =
            buf_slice_height >= 0
            ? ((buf_slice_height && (height % buf_slice_height))
               ? (buf_slice_height - (height % buf_slice_height))
               : 0)
            : -1;
}

// Ugly, stupid utility functions
static void say(const char *message, ...) {
    va_list args;
    char str[1024];
    memset(str, 0, sizeof(str));
    va_start(args, message);
    vsnprintf(str, sizeof(str) - 1, message, args);
    va_end(args);
    if (DEBUG) logging_info(str);
}

static void die(const char *message, ...) {
    va_list args;
    char str[1024];
    memset(str, 0, sizeof(str));
    va_start(args, message);
    vsnprintf(str, sizeof(str), message, args);
    va_end(args);
    logging_fatal(__FILE__, __LINE__, str);
    exit(1);
}

static void omx_die(OMX_ERRORTYPE error, const char *message, ...) {
    va_list args;
    char str[1024];
    char *e;
    memset(str, 0, sizeof(str));
    va_start(args, message);
    vsnprintf(str, sizeof(str), message, args);
    va_end(args);
    switch (error) {
        case OMX_ErrorNone:
            e = "no error";
            break;
        case OMX_ErrorBadParameter:
            e = "bad parameter";
            break;
        case OMX_ErrorIncorrectStateOperation:
            e = "invalid state while trying to perform command";
            break;
        case OMX_ErrorIncorrectStateTransition:
            e = "unallowed state transition";
            break;
        case OMX_ErrorInsufficientResources:
            e = "insufficient resource";
            break;
        case OMX_ErrorBadPortIndex:
            e = "bad port index, i.e. incorrect port";
            break;
        case OMX_ErrorHardware:
            e = "hardware error";
            break;
            /* That's all I've encountered during hacking so let's not bother with the rest... */
        default:
            e = "(no description)";
    }
    die("OMX error: %s: 0x%08x %s", str, error, e);
}

static void dump_frame_info(const char *message, const i420_frame_info *info) {
    say("%s frame info:\n"
                "\tWidth:\t\t\t%d\n"
                "\tHeight:\t\t\t%d\n"
                "\tSize:\t\t\t%d\n"
                "\tBuffer stride:\t\t%d\n"
                "\tBuffer slice height:\t%d\n"
                "\tBuffer extra padding:\t%d\n"
                "\tPlane strides:\t\tY:%d U:%d V:%d\n"
                "\tPlane offsets:\t\tY:%d U:%d V:%d\n",
        message,
        info->width, info->height, info->size, info->buf_stride, info->buf_slice_height, info->buf_extra_padding,
        info->p_stride[0], info->p_stride[1], info->p_stride[2],
        info->p_offset[0], info->p_offset[1], info->p_offset[2]);
}

static void dump_event(OMX_HANDLETYPE hComponent, OMX_EVENTTYPE eEvent, OMX_U32 nData1, OMX_U32 nData2) {
    char *e;
    switch (eEvent) {
        case OMX_EventCmdComplete:
            e = "command complete";
            break;
        case OMX_EventError:
            e = "error";
            break;
        case OMX_EventParamOrConfigChanged:
            e = "parameter or configuration changed";
            break;
        case OMX_EventPortSettingsChanged:
            e = "port settings changed";
            break;
            /* That's all I've encountered during hacking so let's not bother with the rest... */
        default:
            e = "(no description)";
    }
    say("Received event 0x%08x %s, hComponent:0x%08x, nData1:0x%08x, nData2:0x%08x",
        eEvent, e, hComponent, nData1, nData2);
}

static const char *dump_compression_format(OMX_VIDEO_CODINGTYPE c) {
    char *f;
    switch (c) {
        case OMX_VIDEO_CodingUnused:
            return "not used";
        case OMX_VIDEO_CodingAutoDetect:
            return "autodetect";
        case OMX_VIDEO_CodingMPEG2:
            return "MPEG2";
        case OMX_VIDEO_CodingH263:
            return "H.263";
        case OMX_VIDEO_CodingMPEG4:
            return "MPEG4";
        case OMX_VIDEO_CodingWMV:
            return "Windows Media Video";
        case OMX_VIDEO_CodingRV:
            return "RealVideo";
        case OMX_VIDEO_CodingAVC:
            return "H.264/AVC";
        case OMX_VIDEO_CodingMJPEG:
            return "Motion JPEG";
        case OMX_VIDEO_CodingVP6:
            return "VP6";
        case OMX_VIDEO_CodingVP7:
            return "VP7";
        case OMX_VIDEO_CodingVP8:
            return "VP8";
        case OMX_VIDEO_CodingYUV:
            return "Raw YUV video";
        case OMX_VIDEO_CodingSorenson:
            return "Sorenson";
        case OMX_VIDEO_CodingTheora:
            return "OGG Theora";
        case OMX_VIDEO_CodingMVC:
            return "H.264/MVC";

        default:
            f = calloc(23, sizeof(char));
            if (f == NULL) {
                die("Failed to allocate memory");
            }
            snprintf(f, 23 * sizeof(char) - 1, "format type 0x%08x", c);
            return f;
    }
}

static const char *dump_color_format(OMX_COLOR_FORMATTYPE c) {
    char *f;
    switch (c) {
        case OMX_COLOR_FormatUnused:
            return "OMX_COLOR_FormatUnused: not used";
        case OMX_COLOR_FormatMonochrome:
            return "OMX_COLOR_FormatMonochrome";
        case OMX_COLOR_Format8bitRGB332:
            return "OMX_COLOR_Format8bitRGB332";
        case OMX_COLOR_Format12bitRGB444:
            return "OMX_COLOR_Format12bitRGB444";
        case OMX_COLOR_Format16bitARGB4444:
            return "OMX_COLOR_Format16bitARGB4444";
        case OMX_COLOR_Format16bitARGB1555:
            return "OMX_COLOR_Format16bitARGB1555";
        case OMX_COLOR_Format16bitRGB565:
            return "OMX_COLOR_Format16bitRGB565";
        case OMX_COLOR_Format16bitBGR565:
            return "OMX_COLOR_Format16bitBGR565";
        case OMX_COLOR_Format18bitRGB666:
            return "OMX_COLOR_Format18bitRGB666";
        case OMX_COLOR_Format18bitARGB1665:
            return "OMX_COLOR_Format18bitARGB1665";
        case OMX_COLOR_Format19bitARGB1666:
            return "OMX_COLOR_Format19bitARGB1666";
        case OMX_COLOR_Format24bitRGB888:
            return "OMX_COLOR_Format24bitRGB888";
        case OMX_COLOR_Format24bitBGR888:
            return "OMX_COLOR_Format24bitBGR888";
        case OMX_COLOR_Format24bitARGB1887:
            return "OMX_COLOR_Format24bitARGB1887";
        case OMX_COLOR_Format25bitARGB1888:
            return "OMX_COLOR_Format25bitARGB1888";
        case OMX_COLOR_Format32bitBGRA8888:
            return "OMX_COLOR_Format32bitBGRA8888";
        case OMX_COLOR_Format32bitARGB8888:
            return "OMX_COLOR_Format32bitARGB8888";
        case OMX_COLOR_FormatYUV411Planar:
            return "OMX_COLOR_FormatYUV411Planar";
        case OMX_COLOR_FormatYUV411PackedPlanar:
            return "OMX_COLOR_FormatYUV411PackedPlanar: Planes fragmented when a frame is split in multiple buffers";
        case OMX_COLOR_FormatYUV420Planar:
            return "OMX_COLOR_FormatYUV420Planar: Planar YUV, 4:2:0 (I420)";
        case OMX_COLOR_FormatYUV420PackedPlanar:
            return "OMX_COLOR_FormatYUV420PackedPlanar: Planar YUV, 4:2:0 (I420), planes fragmented when a frame is split in multiple buffers";
        case OMX_COLOR_FormatYUV420SemiPlanar:
            return "OMX_COLOR_FormatYUV420SemiPlanar, Planar YUV, 4:2:0 (NV12), U and V planes interleaved with first U value";
        case OMX_COLOR_FormatYUV422Planar:
            return "OMX_COLOR_FormatYUV422Planar";
        case OMX_COLOR_FormatYUV422PackedPlanar:
            return "OMX_COLOR_FormatYUV422PackedPlanar: Planes fragmented when a frame is split in multiple buffers";
        case OMX_COLOR_FormatYUV422SemiPlanar:
            return "OMX_COLOR_FormatYUV422SemiPlanar";
        case OMX_COLOR_FormatYCbYCr:
            return "OMX_COLOR_FormatYCbYCr";
        case OMX_COLOR_FormatYCrYCb:
            return "OMX_COLOR_FormatYCrYCb";
        case OMX_COLOR_FormatCbYCrY:
            return "OMX_COLOR_FormatCbYCrY";
        case OMX_COLOR_FormatCrYCbY:
            return "OMX_COLOR_FormatCrYCbY";
        case OMX_COLOR_FormatYUV444Interleaved:
            return "OMX_COLOR_FormatYUV444Interleaved";
        case OMX_COLOR_FormatRawBayer8bit:
            return "OMX_COLOR_FormatRawBayer8bit";
        case OMX_COLOR_FormatRawBayer10bit:
            return "OMX_COLOR_FormatRawBayer10bit";
        case OMX_COLOR_FormatRawBayer8bitcompressed:
            return "OMX_COLOR_FormatRawBayer8bitcompressed";
        case OMX_COLOR_FormatL2:
            return "OMX_COLOR_FormatL2";
        case OMX_COLOR_FormatL4:
            return "OMX_COLOR_FormatL4";
        case OMX_COLOR_FormatL8:
            return "OMX_COLOR_FormatL8";
        case OMX_COLOR_FormatL16:
            return "OMX_COLOR_FormatL16";
        case OMX_COLOR_FormatL24:
            return "OMX_COLOR_FormatL24";
        case OMX_COLOR_FormatL32:
            return "OMX_COLOR_FormatL32";
        case OMX_COLOR_FormatYUV420PackedSemiPlanar:
            return "OMX_COLOR_FormatYUV420PackedSemiPlanar: Planar YUV, 4:2:0 (NV12), planes fragmented when a frame is split in multiple buffers, U and V planes interleaved with first U value";
        case OMX_COLOR_FormatYUV422PackedSemiPlanar:
            return "OMX_COLOR_FormatYUV422PackedSemiPlanar: Planes fragmented when a frame is split in multiple buffers";
        case OMX_COLOR_Format18BitBGR666:
            return "OMX_COLOR_Format18BitBGR666";
        case OMX_COLOR_Format24BitARGB6666:
            return "OMX_COLOR_Format24BitARGB6666";
        case OMX_COLOR_Format24BitABGR6666:
            return "OMX_COLOR_Format24BitABGR6666";
        case OMX_COLOR_Format32bitABGR8888:
            return "OMX_COLOR_Format32bitABGR8888";
        case OMX_COLOR_Format8bitPalette:
            return "OMX_COLOR_Format8bitPalette";
        case OMX_COLOR_FormatYUVUV128:
            return "OMX_COLOR_FormatYUVUV128";
        case OMX_COLOR_FormatRawBayer12bit:
            return "OMX_COLOR_FormatRawBayer12bit";
        case OMX_COLOR_FormatBRCMEGL:
            return "OMX_COLOR_FormatBRCMEGL";
        case OMX_COLOR_FormatBRCMOpaque:
            return "OMX_COLOR_FormatBRCMOpaque";
        case OMX_COLOR_FormatYVU420PackedPlanar:
            return "OMX_COLOR_FormatYVU420PackedPlanar";
        case OMX_COLOR_FormatYVU420PackedSemiPlanar:
            return "OMX_COLOR_FormatYVU420PackedSemiPlanar";
        default:
            f = calloc(23, sizeof(char));
            if (f == NULL) {
                die("Failed to allocate memory");
            }
            snprintf(f, 23 * sizeof(char) - 1, "format type 0x%08x", c);
            return f;
    }
}

static void dump_portdef(OMX_PARAM_PORTDEFINITIONTYPE *portdef) {
    say("Port %d is %s, %s, buffers wants:%d needs:%d, size:%d, pop:%d, aligned:%d",
        portdef->nPortIndex,
        (portdef->eDir == OMX_DirInput ? "input" : "output"),
        (portdef->bEnabled == OMX_TRUE ? "enabled" : "disabled"),
        portdef->nBufferCountActual,
        portdef->nBufferCountMin,
        portdef->nBufferSize,
        portdef->bPopulated,
        portdef->nBufferAlignment);

    OMX_VIDEO_PORTDEFINITIONTYPE *viddef = &portdef->format.video;
    OMX_IMAGE_PORTDEFINITIONTYPE *imgdef = &portdef->format.image;
    switch (portdef->eDomain) {
        case OMX_PortDomainVideo:
            say("Video type:\n"
                        "\tWidth:\t\t%d\n"
                        "\tHeight:\t\t%d\n"
                        "\tStride:\t\t%d\n"
                        "\tSliceHeight:\t%d\n"
                        "\tBitrate:\t%d\n"
                        "\tFramerate:\t%.02f\n"
                        "\tError hiding:\t%s\n"
                        "\tCodec:\t\t%s\n"
                        "\tColor:\t\t%s\n",
                viddef->nFrameWidth,
                viddef->nFrameHeight,
                viddef->nStride,
                viddef->nSliceHeight,
                viddef->nBitrate,
                ((float) viddef->xFramerate / (float) 65536),
                (viddef->bFlagErrorConcealment == OMX_TRUE ? "yes" : "no"),
                dump_compression_format(viddef->eCompressionFormat),
                dump_color_format(viddef->eColorFormat));
            break;
        case OMX_PortDomainImage:
            say("Image type:\n"
                        "\tWidth:\t\t%d\n"
                        "\tHeight:\t\t%d\n"
                        "\tStride:\t\t%d\n"
                        "\tSliceHeight:\t%d\n"
                        "\tError hiding:\t%s\n"
                        "\tCodec:\t\t%s\n"
                        "\tColor:\t\t%s\n",
                imgdef->nFrameWidth,
                imgdef->nFrameHeight,
                imgdef->nStride,
                imgdef->nSliceHeight,
                (imgdef->bFlagErrorConcealment == OMX_TRUE ? "yes" : "no"),
                dump_compression_format(imgdef->eCompressionFormat),
                dump_color_format(imgdef->eColorFormat));
            break;
        default:
            break;
    }
}

static void dump_port(OMX_HANDLETYPE hComponent, OMX_U32 nPortIndex, OMX_BOOL dumpformats) {
    OMX_ERRORTYPE r;
    OMX_PARAM_PORTDEFINITIONTYPE portdef;
    OMX_INIT_STRUCTURE(portdef);
    portdef.nPortIndex = nPortIndex;
    if ((r = OMX_GetParameter(hComponent, OMX_IndexParamPortDefinition, &portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to get port definition for port %d", nPortIndex);
    }
    dump_portdef(&portdef);
    if (dumpformats) {
        OMX_VIDEO_PARAM_PORTFORMATTYPE portformat;
        OMX_INIT_STRUCTURE(portformat);
        portformat.nPortIndex = nPortIndex;
        portformat.nIndex = 0;
        r = OMX_ErrorNone;
        say("Port %d supports these video formats:", nPortIndex);
        while (r == OMX_ErrorNone) {
            if ((r = OMX_GetParameter(hComponent, OMX_IndexParamVideoPortFormat, &portformat)) == OMX_ErrorNone) {
                say("\t%s, compression: %s", dump_color_format(portformat.eColorFormat),
                    dump_compression_format(portformat.eCompressionFormat));
                portformat.nIndex++;
            }
        }
    }
}

// Some busy loops to verify we're running in order
static void block_until_state_changed(OMX_HANDLETYPE hComponent, OMX_STATETYPE wanted_eState) {
    OMX_STATETYPE eState;
    int i = 0;
    while (i++ == 0 || eState != wanted_eState) {
        OMX_GetState(hComponent, &eState);
        if (eState != wanted_eState) {
            usleep(10000);
        }
    }
}

static void block_until_port_changed(OMX_HANDLETYPE hComponent, OMX_U32 nPortIndex, OMX_BOOL bEnabled) {
    OMX_ERRORTYPE r;
    OMX_PARAM_PORTDEFINITIONTYPE portdef;
    OMX_INIT_STRUCTURE(portdef);
    portdef.nPortIndex = nPortIndex;
    OMX_U32 i = 0;
    while (i++ == 0 || portdef.bEnabled != bEnabled) {
        if ((r = OMX_GetParameter(hComponent, OMX_IndexParamPortDefinition, &portdef)) != OMX_ErrorNone) {
            omx_die(r, "Failed to get port definition");
        }
        if (portdef.bEnabled != bEnabled) {
            usleep(10000);
        }
    }
}

static void block_until_flushed(appctx *ctx) {
    int quit;
    while (!quit) {
        vcos_semaphore_wait(&ctx->handler_lock);
        if (ctx->flushed) {
            ctx->flushed = 0;
            quit = 1;
        }
        vcos_semaphore_post(&ctx->handler_lock);
        if (!quit) {
            usleep(10000);
        }
    }
}

static void init_component_handle(
        const char *name,
        OMX_HANDLETYPE *hComponent,
        OMX_PTR pAppData,
        OMX_CALLBACKTYPE *callbacks) {
    OMX_ERRORTYPE r;
    char fullname[32];

    // Get handle
    memset(fullname, 0, sizeof(fullname));
    strcat(fullname, "OMX.broadcom.");
    strncat(fullname, name, strlen(fullname) - 1);
    say("Initializing component %s", fullname);
    if ((r = OMX_GetHandle(hComponent, fullname, pAppData, callbacks)) != OMX_ErrorNone) {
        omx_die(r, "Failed to get handle for component %s", fullname);
    }

    // Disable ports
    OMX_INDEXTYPE types[] = {
            OMX_IndexParamAudioInit,
            OMX_IndexParamVideoInit,
            OMX_IndexParamImageInit,
            OMX_IndexParamOtherInit
    };
    OMX_PORT_PARAM_TYPE ports;
    OMX_INIT_STRUCTURE(ports);
    OMX_GetParameter(*hComponent, OMX_IndexParamVideoInit, &ports);

    int i;
    for (i = 0; i < 4; i++) {
        if (OMX_GetParameter(*hComponent, types[i], &ports) == OMX_ErrorNone) {
            OMX_U32 nPortIndex;
            for (nPortIndex = ports.nStartPortNumber;
                 nPortIndex < ports.nStartPortNumber + ports.nPorts; nPortIndex++) {
                say("Disabling port %d of component %s", nPortIndex, fullname);
                if ((r = OMX_SendCommand(*hComponent, OMX_CommandPortDisable, nPortIndex, NULL)) != OMX_ErrorNone) {
                    omx_die(r, "Failed to disable port %d of component %s", nPortIndex, fullname);
                }
                block_until_port_changed(*hComponent, nPortIndex, OMX_FALSE);
            }
        }
    }
}

// Global signal handler for trapping SIGINT, SIGTERM, and SIGQUIT
static void signal_handler(int signal) {
    want_quit = 1;
}

// OMX calls this handler for all the events it emits
static OMX_ERRORTYPE event_handler(
        OMX_HANDLETYPE hComponent,
        OMX_PTR pAppData,
        OMX_EVENTTYPE eEvent,
        OMX_U32 nData1,
        OMX_U32 nData2,
        OMX_PTR pEventData) {

    dump_event(hComponent, eEvent, nData1, nData2);

    appctx *ctx = (appctx *) pAppData;

    switch (eEvent) {
        case OMX_EventCmdComplete:
            vcos_semaphore_wait(&ctx->handler_lock);
            if (nData1 == OMX_CommandFlush) {
                ctx->flushed = 1;
            }
            vcos_semaphore_post(&ctx->handler_lock);
            break;
        case OMX_EventError:
            omx_die(nData1, "error event received");
            break;
        default:
            break;
    }

    return OMX_ErrorNone;
}

// Called by OMX when the encoder component requires
// the input buffer to be filled with YUV video data
static OMX_ERRORTYPE empty_input_buffer_done_handler(
        OMX_HANDLETYPE hComponent,
        OMX_PTR pAppData,
        OMX_BUFFERHEADERTYPE *pBuffer) {
    appctx *ctx = ((appctx *) pAppData);
    vcos_semaphore_wait(&ctx->handler_lock);
    // The main loop can now fill the buffer from input file
    ctx->encoder_input_buffer_needed = 1;
    vcos_semaphore_post(&ctx->handler_lock);
    return OMX_ErrorNone;
}

// Called by OMX when the encoder component has filled
// the output buffer with H.264 encoded video data
static OMX_ERRORTYPE fill_output_buffer_done_handler(
        OMX_HANDLETYPE hComponent,
        OMX_PTR pAppData,
        OMX_BUFFERHEADERTYPE *pBuffer) {
    appctx *ctx = ((appctx *) pAppData);
    vcos_semaphore_wait(&ctx->handler_lock);
    // The main loop can now flush the buffer to output file
    ctx->encoder_output_buffer_available = 1;
    vcos_semaphore_post(&ctx->handler_lock);
    return OMX_ErrorNone;
}


//! Record a video stream from a webcam to an H264 video file for later analysis, using openmax (hardware encoding).
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

int main(int argc, const char **argv) {
    video_metadata vmd;
    char line[FNAME_LENGTH];
    const char *mask_file = "\0";
    const char *obstory_id = "\0";
    const char *input_device = "\0";
    const char *output_filename = "\0";

    vmd.utc_start = time(NULL);
    vmd.utc_stop = vmd.utc_start + 5;
    vmd.frame_count = 0;
    vmd.width = 720;
    vmd.height = 576;
    vmd.fps = 24.71;
    vmd.lat = 52.2;
    vmd.lng = 0.12;
    vmd.flag_gps = 0;
    vmd.flag_upside_down = 1;

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('o', "obsid", &obstory_id, "observatory id"),
        OPT_STRING('x', "output", &vmd.filename, "output filename"),
        OPT_STRING('d', "device", &input_device, "input video device, e.g. /dev/video0"),
        OPT_STRING('m', "mask", &mask_file, "mask file"),
        OPT_FLOAT('s', "utc-stop", &vmd.utc_stop, "time stamp at which to end observing"),
        OPT_FLOAT('f', "fps", &vmd.fps, "frame count per second"),
        OPT_FLOAT('l', "latitude", &vmd.lat, "latitude of observatory"),
        OPT_FLOAT('L', "longitude", &vmd.lng, "longitude of observatory"),
        OPT_INTEGER('w', "width", &vmd.width, "frame width"),
        OPT_INTEGER('h', "height", &vmd.height, "frame height"),
        OPT_INTEGER('g', "flag-gps", &vmd.flag_gps, "boolean flag indicating whether position determined by GPS"),
        OPT_INTEGER('u', "flag-upside-down", &vmd.flag_upside_down, "boolean flag indicating whether the camera is upside down"),
        OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
    "\nRecord a video stream to an H264 file for future analysis.",
    "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    vmd.obstory_id = obstory_id;
    vmd.video_device = input_device;
    vmd.mask_file = mask_file;
    vmd.filename = output_filename;

    // Append .h264 suffix to output filename
    char frOut[4096];
    sprintf(frOut, "%s.h264", vmd.filename);

    if (DEBUG) {
        sprintf(line, "Starting video recording run at %s.",
                str_strip(friendly_time_string(vmd.utc_start), temp_err_string));
        logging_info(line);
    }
    if (DEBUG) {
        sprintf(line, "Video will end at %s.", str_strip(friendly_time_string(vmd.utc_stop), temp_err_string));
        logging_info(line);
    }

    initLut();

    struct video_info *video_in;

    const float fps = nearest_multiple(vmd.fps, 1);       // Requested frame rate
    const int v4l_format = V4L2_PIX_FMT_YUYV;
    const int grab_method = 1;

    video_in = (struct video_info *) calloc(1, sizeof(struct video_info));

    // Fetch the dimensions of the video stream as returned by V4L (which may differ from what we requested)
    if (init_videoIn(video_in, vmd.video_device, vmd.width, vmd.height, fps, v4l_format, grab_method) < 0)
        exit(1);
    const int width = video_in->width;
    const int height = video_in->height;
    vmd.width = width;
    vmd.height = height;
    write_raw_video_metadata(vmd);

    // Initialise H264 encoder
    bcm_host_init();

    OMX_ERRORTYPE r;

    if ((r = OMX_Init()) != OMX_ErrorNone) {
        omx_die(r, "OMX initalization failed");
    }

    const int frame_size = width * height;
    unsigned char *tmpc = malloc(
            frame_size * 1.5); // Temporary frame buffer for converting YUV422 data from v4l2 into YUV420
    if (!tmpc) logging_fatal(__FILE__, __LINE__, "Malloc fail");

    // Init context
    appctx ctx;
    memset(&ctx, 0, sizeof(ctx));
    if (vcos_semaphore_create(&ctx.handler_lock, "handler_lock", 1) != VCOS_SUCCESS) {
        die("Failed to create handler lock semaphore");
    }

    // Init component handles
    OMX_CALLBACKTYPE callbacks;
    memset(&ctx, 0, sizeof(callbacks));
    callbacks.EventHandler = event_handler;
    callbacks.EmptyBufferDone = empty_input_buffer_done_handler;
    callbacks.FillBufferDone = fill_output_buffer_done_handler;

    init_component_handle("video_encode", &ctx.encoder, &ctx, &callbacks);

    say("Configuring encoder...");

    say("Default port definition for encoder input port 200");
    dump_port(ctx.encoder, 200, OMX_TRUE);
    say("Default port definition for encoder output port 201");
    dump_port(ctx.encoder, 201, OMX_TRUE);

    OMX_PARAM_PORTDEFINITIONTYPE encoder_portdef;
    OMX_INIT_STRUCTURE(encoder_portdef);
    encoder_portdef.nPortIndex = 200;
    if ((r = OMX_GetParameter(ctx.encoder, OMX_IndexParamPortDefinition, &encoder_portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to get port definition for encoder input port 200");
    }
    encoder_portdef.format.video.nFrameWidth = width;
    encoder_portdef.format.video.nFrameHeight = height;
    encoder_portdef.format.video.xFramerate = ((int) vmd.fps) << 16;
    // Stolen from gstomxvideodec.c of gst-omx
    encoder_portdef.format.video.nStride =
            (encoder_portdef.format.video.nFrameWidth + encoder_portdef.nBufferAlignment - 1) &
            (~(encoder_portdef.nBufferAlignment - 1));
    encoder_portdef.format.video.eColorFormat = OMX_COLOR_FormatYUV420PackedPlanar;
    if ((r = OMX_SetParameter(ctx.encoder, OMX_IndexParamPortDefinition, &encoder_portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to set port definition for encoder input port 200");
    }

    // Copy encoder input port definition as basis encoder output port definition
    OMX_INIT_STRUCTURE(encoder_portdef);
    encoder_portdef.nPortIndex = 200;
    if ((r = OMX_GetParameter(ctx.encoder, OMX_IndexParamPortDefinition, &encoder_portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to get port definition for encoder input port 200");
    }
    encoder_portdef.nPortIndex = 201;
    encoder_portdef.format.video.eColorFormat = OMX_COLOR_FormatUnused;
    encoder_portdef.format.video.eCompressionFormat = OMX_VIDEO_CodingAVC;
    // Which one is effective, this or the configuration just below?
    encoder_portdef.format.video.nBitrate = VIDEO_BITRATE;
    if ((r = OMX_SetParameter(ctx.encoder, OMX_IndexParamPortDefinition, &encoder_portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to set port definition for encoder output port 201");
    }
    // Configure bitrate
    OMX_VIDEO_PARAM_BITRATETYPE bitrate;
    OMX_INIT_STRUCTURE(bitrate);
    bitrate.eControlRate = OMX_Video_ControlRateVariable;
    bitrate.nTargetBitrate = encoder_portdef.format.video.nBitrate;
    bitrate.nPortIndex = 201;
    if ((r = OMX_SetParameter(ctx.encoder, OMX_IndexParamVideoBitrate, &bitrate)) != OMX_ErrorNone) {
        omx_die(r, "Failed to set bitrate for encoder output port 201");
    }
    // Configure format
    OMX_VIDEO_PARAM_PORTFORMATTYPE format;
    OMX_INIT_STRUCTURE(format);
    format.nPortIndex = 201;
    format.eCompressionFormat = OMX_VIDEO_CodingAVC;
    if ((r = OMX_SetParameter(ctx.encoder, OMX_IndexParamVideoPortFormat, &format)) != OMX_ErrorNone) {
        omx_die(r, "Failed to set video format for encoder output port 201");
    }

    // Switch components to idle state
    say("Switching state of the encoder component to idle...");
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandStateSet, OMX_StateIdle, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to switch state of the encoder component to idle");
    }
    block_until_state_changed(ctx.encoder, OMX_StateIdle);

    // Enable ports
    say("Enabling ports...");
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandPortEnable, 200, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to enable encoder input port 200");
    }
    block_until_port_changed(ctx.encoder, 200, OMX_TRUE);
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandPortEnable, 201, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to enable encoder output port 201");
    }
    block_until_port_changed(ctx.encoder, 201, OMX_TRUE);

    // Allocate encoder input and output buffers
    say("Allocating buffers...");
    OMX_INIT_STRUCTURE(encoder_portdef);
    encoder_portdef.nPortIndex = 200;
    if ((r = OMX_GetParameter(ctx.encoder, OMX_IndexParamPortDefinition, &encoder_portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to get port definition for encoder input port 200");
    }
    if ((r = OMX_AllocateBuffer(ctx.encoder, &ctx.encoder_ppBuffer_in, 200, NULL, encoder_portdef.nBufferSize)) !=
        OMX_ErrorNone) {
        omx_die(r, "Failed to allocate buffer for encoder input port 200");
    }
    OMX_INIT_STRUCTURE(encoder_portdef);
    encoder_portdef.nPortIndex = 201;
    if ((r = OMX_GetParameter(ctx.encoder, OMX_IndexParamPortDefinition, &encoder_portdef)) != OMX_ErrorNone) {
        omx_die(r, "Failed to get port definition for encoder output port 201");
    }
    if ((r = OMX_AllocateBuffer(ctx.encoder, &ctx.encoder_ppBuffer_out, 201, NULL, encoder_portdef.nBufferSize)) !=
        OMX_ErrorNone) {
        omx_die(r, "Failed to allocate buffer for encoder output port 201");
    }

    // Just use stdin for input and stdout for output
    say("Opening input and output files...");
    FILE *fd_out = fopen(frOut, "w");
    if (fd_out == NULL) omx_die(r, "Could not open output h264 file <%s>.", frOut);

    // Switch state of the components prior to starting
    // the video capture and encoding loop
    say("Switching state of the encoder component to executing...");
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandStateSet, OMX_StateExecuting, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to switch state of the encoder component to executing");
    }
    block_until_state_changed(ctx.encoder, OMX_StateExecuting);

    say("Configured port definition for encoder input port 200");
    dump_port(ctx.encoder, 200, OMX_FALSE);
    say("Configured port definition for encoder output port 201");
    dump_port(ctx.encoder, 201, OMX_FALSE);

    i420_frame_info frame_info, buf_info;
    get_i420_frame_info(encoder_portdef.format.image.nFrameWidth, encoder_portdef.format.image.nFrameHeight,
                        encoder_portdef.format.image.nStride, encoder_portdef.format.video.nSliceHeight, &frame_info);
    get_i420_frame_info(frame_info.buf_stride, frame_info.buf_slice_height, -1, -1, &buf_info);

    dump_frame_info("Destination frame", &frame_info);
    dump_frame_info("Source buffer", &buf_info);

    if (ctx.encoder_ppBuffer_in->nAllocLen != buf_info.size) {
        die("Allocated encoder input port 200 buffer size %d doesn't equal to the expected buffer size %d",
            ctx.encoder_ppBuffer_in->nAllocLen, buf_info.size);
    }

    say("Enter encode loop, press Ctrl-C to quit...");

    int frame_in = 0, frame_out = 0, firstPass = 1;
    size_t input_total_read, output_written;
    // I420 spec: U and V plane span size half of the size of the Y plane span size
    int plane_span_y = ROUND_UP_2(frame_info.height), plane_span_uv = plane_span_y / 2;

    ctx.encoder_input_buffer_needed = 1;

    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGQUIT, signal_handler);

    while (!want_quit) {

        int t = time(NULL);
        if (t >= vmd.utc_stop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!


        // empty_input_buffer_done_handler() has marked that there's
        // a need for a buffer to be filled by us
        if (ctx.encoder_input_buffer_needed) {
            int line;
            input_total_read = 0;

            if (fetchFrame(video_in, tmpc, vmd.flag_upside_down)) {
                want_quit = 1;
                break;
            }

            // Increment frame counter
            vmd.frame_count++;

            // Copy frame data into openmax buffer
#pragma omp parallel for private(line)
            for (line = 0; line < height; line++)
                memcpy(ctx.encoder_ppBuffer_in->pBuffer + buf_info.p_offset[0] + frame_info.buf_stride * line,
                       tmpc + width * line, width);
#pragma omp parallel for private(line)
            for (line = 0; line < height / 2; line++)
                memcpy(ctx.encoder_ppBuffer_in->pBuffer + buf_info.p_offset[1] + frame_info.buf_stride / 2 * line,
                       tmpc + (width / 2) * line + frame_size, width / 2);
#pragma omp parallel for private(line)
            for (line = 0; line < height / 2; line++)
                memcpy(ctx.encoder_ppBuffer_in->pBuffer + buf_info.p_offset[2] + frame_info.buf_stride / 2 * line,
                       tmpc + (width / 2) * line + frame_size * 5 / 4, width / 2);

            input_total_read += (frame_info.p_stride[0] * plane_span_y) + (frame_info.p_stride[1] * plane_span_uv) +
                                (frame_info.p_stride[2] * plane_span_uv);

            ctx.encoder_ppBuffer_in->nOffset = 0;
            ctx.encoder_ppBuffer_in->nFilledLen = (buf_info.size - frame_info.size) + input_total_read;
            frame_in++;
            //say("Read from input file and wrote to input buffer %d/%d, frame %d", ctx.encoder_ppBuffer_in->nFilledLen, ctx.encoder_ppBuffer_in->nAllocLen, frame_in);
            if (input_total_read > 0) {
                ctx.encoder_input_buffer_needed = 0;
                if ((r = OMX_EmptyThisBuffer(ctx.encoder, ctx.encoder_ppBuffer_in)) != OMX_ErrorNone) {
                    omx_die(r, "Failed to request emptying of the input buffer on encoder input port 200");
                }
            }
        }
        // fill_output_buffer_done_handler() has marked that there's
        // a buffer for us to flush
        if (ctx.encoder_output_buffer_available) {
            if (ctx.encoder_ppBuffer_out->nFlags & OMX_BUFFERFLAG_ENDOFFRAME) {
                frame_out++;
            }
            // Flush buffer to output file
            output_written = fwrite(ctx.encoder_ppBuffer_out->pBuffer + ctx.encoder_ppBuffer_out->nOffset, 1,
                                    ctx.encoder_ppBuffer_out->nFilledLen, fd_out);
            if (output_written != ctx.encoder_ppBuffer_out->nFilledLen) {
                die("Failed to write to output file: %s", strerror(errno));
            }
            //say("Read from output buffer and wrote to output file %d/%d, frame %d", ctx.encoder_ppBuffer_out->nFilledLen, ctx.encoder_ppBuffer_out->nAllocLen, frame_out + 1);
        }
        if (ctx.encoder_output_buffer_available || firstPass) {
            // Buffer flushed, request a new buffer to be filled by the encoder component
            ctx.encoder_output_buffer_available = 0;
            if ((r = OMX_FillThisBuffer(ctx.encoder, ctx.encoder_ppBuffer_out)) != OMX_ErrorNone) {
                omx_die(r, "Failed to request filling of the output buffer on encoder output port 201");
            }
        }
        // Would be better to use signaling here but hey this works too
        usleep(10);
        firstPass = 0;
    }
    say("Cleaning up...");

    // Restore signal handlers
    signal(SIGINT, SIG_DFL);
    signal(SIGTERM, SIG_DFL);
    signal(SIGQUIT, SIG_DFL);

    // Flush the buffers on each component
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandFlush, 200, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to flush buffers of encoder input port 200");
    }
    block_until_flushed(&ctx);
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandFlush, 201, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to flush buffers of encoder output port 201");
    }
    block_until_flushed(&ctx);

    // Disable all the ports
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandPortDisable, 200, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to disable encoder input port 200");
    }
    block_until_port_changed(ctx.encoder, 200, OMX_FALSE);
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandPortDisable, 201, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to disable encoder output port 201");
    }
    block_until_port_changed(ctx.encoder, 201, OMX_FALSE);

    // Free all the buffers
    if ((r = OMX_FreeBuffer(ctx.encoder, 200, ctx.encoder_ppBuffer_in)) != OMX_ErrorNone) {
        omx_die(r, "Failed to free buffer for encoder input port 200");
    }
    if ((r = OMX_FreeBuffer(ctx.encoder, 201, ctx.encoder_ppBuffer_out)) != OMX_ErrorNone) {
        omx_die(r, "Failed to free buffer for encoder output port 201");
    }

    // Transition all the components to idle and then to loaded states
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandStateSet, OMX_StateIdle, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to switch state of the encoder component to idle");
    }
    block_until_state_changed(ctx.encoder, OMX_StateIdle);
    if ((r = OMX_SendCommand(ctx.encoder, OMX_CommandStateSet, OMX_StateLoaded, NULL)) != OMX_ErrorNone) {
        omx_die(r, "Failed to switch state of the encoder component to loaded");
    }
    block_until_state_changed(ctx.encoder, OMX_StateLoaded);

    // Free the component handles
    if ((r = OMX_FreeHandle(ctx.encoder)) != OMX_ErrorNone) {
        omx_die(r, "Failed to free encoder component handle");
    }

    // Exit
    fclose(fd_out);

    vcos_semaphore_delete(&ctx.handler_lock);
    if ((r = OMX_Deinit()) != OMX_ErrorNone) {
        omx_die(r, "OMX de-initalization failed");
    }

    vmd.utc_stop = time(NULL);
    write_raw_video_metadata(vmd);
    say("Exit!");

    return 0;
}
