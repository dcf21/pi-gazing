// analyseH264_libav.c 
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

// This code is based on the FFmpeg source code; (C) 2001 Fabrice Bellard; distributed under GPL version 2.1

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>

#include <sys/time.h>
#include <time.h>

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/mem.h>
#include <libavutil/mathematics.h>

#include "argparse/argparse.h"
#include "analyse/observe.h"
#include "utils/asciiDouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/filledPoly.h"
#include "vidtools/color.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

static const char *const usage[] = {
    "analyseH264_libav [options] [[--] args]",
    "analyseH264_libav [options]",
    NULL,
};

void sigint_handler(int signal) {
    printf("\n");
    exit(0);
}

typedef struct context {
    AVCodec *codec;
    AVCodecContext *c;
    int frame, got_picture, len2, len, stream_num;
    double utc_start, utc_stop, fps;
    const char *filename, *mask_file;
    unsigned char *mask;
    FILE *f;
    AVFrame *picture;
    AVPacket avpkt;
    AVFormatContext *avFormatPtr;
} context;

int fetch_frame(void *ctx_void, unsigned char *tmpc, double *utc) {
    context *ctx = (context *)ctx_void;

    if (utc) *utc = ctx->utc_start + ctx->frame / ctx->fps;

    while (1) {
        av_init_packet(&ctx->avpkt);
        ctx->len = av_read_frame(ctx->avFormatPtr, &ctx->avpkt);
        ctx->len2 = avcodec_decode_video2(ctx->c, ctx->picture, &ctx->got_picture, &ctx->avpkt);

        if (ctx->len < 0) {
            sprintf(temp_err_string, "In input file <%s>, error decoding frame %d", ctx->filename, ctx->frame);
            logging_error(ERR_GENERAL, temp_err_string);
        }

        if (ctx->got_picture) {
            if (tmpc) {
                const int w = ctx->c->width;
                const int h = ctx->c->height;
                const int s = w * h;
                int i;
                for (i = 0; i < h; i++) memcpy(tmpc + +i * w, ctx->picture->data[0] + i * ctx->picture->linesize[0], w);
                for (i = 0; i < h / 2; i++)
                    memcpy(tmpc + s + i * w / 2, ctx->picture->data[1] + i * ctx->picture->linesize[1], w / 2);
                for (i = 0; i < h / 2; i++)
                    memcpy(tmpc + s * 5 / 4 + i * w / 2, ctx->picture->data[2] + i * ctx->picture->linesize[2], w / 2);
            }
            ctx->frame++;
        }
        av_packet_unref(&ctx->avpkt);
        if (ctx->got_picture) return 0;
        if (!ctx->got_picture) return 1;
    }
}

int decoder_init(context *ctx) {
    printf("Decoding file <%s>\n", ctx->filename);
    ctx->avFormatPtr = avformat_alloc_context();
    if (avformat_open_input(&ctx->avFormatPtr, ctx->filename, NULL, NULL) != 0) {
        logging_fatal(__FILE__, __LINE__, "could not open input video");
    }
    ctx->stream_num = av_find_best_stream(ctx->avFormatPtr, AVMEDIA_TYPE_VIDEO, -1, -1, &ctx->codec, 0);
    if (!ctx->codec) { logging_fatal(__FILE__, __LINE__, "codec not found"); }
    ctx->c = avcodec_alloc_context3(ctx->codec);
    if (avcodec_open2(ctx->c, ctx->codec, NULL) < 0) { logging_fatal(__FILE__, __LINE__, "codec could not be opened"); }
    ctx->picture = av_frame_alloc();
    signal(SIGINT, sigint_handler);
    ctx->frame = 0;
    fetch_frame((void *) ctx, NULL, NULL); // Get libav to pick up video size
    ctx->mask = malloc(ctx->c->width * ctx->c->height);
    FILE *mask_file = fopen(ctx->mask_file, "r");
    if (!mask_file) { logging_fatal(__FILE__, __LINE__, "mask file could not be opened"); }
    fill_polygons_from_file(mask_file, ctx->mask, ctx->c->width, ctx->c->height);
    fclose(mask_file);
    return 0;
}

int decoder_shutdown(context *ctx) {
    avcodec_close(ctx->c);
    av_free(ctx->c);
    av_free(ctx->picture);
    return 0;
}

int rewind_video(void *ctx_void, double *utc) {
    context *ctx = (context *) ctx_void;
    decoder_shutdown(ctx);
    decoder_init(ctx);
    if (utc) *utc = ctx->utc_start;
    return 0;
}

int main(int argc, const char **argv) {
    context ctx;
    const char *fname = "\0";
    const char *mask_file = "\0";
    const char *obstory_id = "\0";

    ctx.utc_start = 0;
    ctx.utc_stop = time(NULL) + 3600 * 24;
    ctx.fps = 0;

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('i', "input", &fname, "input filename"),
        OPT_STRING('o', "obsid", &obstory_id, "observatory id"),
        OPT_STRING('m', "mask", &mask_file, "mask file"),
        OPT_FLOAT('t', "time-start", &ctx.utc_start, "time stamp of start of video clip"),
        OPT_FLOAT('f', "fps", &ctx.fps, "frame count per second"),
        OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
    "\nAnalyse an H264 video clip.",
    "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    ctx.filename = fname;
    ctx.mask_file = mask_file;

    initLut();

    const int background_map_use_every_nth_stack = 1;
    const int background_map_use_n_images = 3600;
    const int background_map_reduction_cycles = 32;

    // Register all the codecs
    av_register_all();
    avcodec_register_all();
    decoder_init(&ctx);
    observe((void *) &ctx, obstory_id, ctx.utc_start, ctx.utc_stop, ctx.c->width, ctx.c->height, ctx.fps,
            "nonlive", ctx.mask, CHANNEL_COUNT, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME,
            TRIGGER_FRAMEGROUP, TRIGGER_MAXRECORDLEN, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT,
            TIMELAPSE_EXPOSURE, TIMELAPSE_INTERVAL, STACK_TARGET_BRIGHTNESS, background_map_use_every_nth_stack,
            background_map_use_n_images, background_map_reduction_cycles, &fetch_frame, &rewind_video);
    decoder_shutdown(&ctx);
    printf("\n");
    return 0;
}

