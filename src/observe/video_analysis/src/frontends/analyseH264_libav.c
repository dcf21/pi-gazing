// analyseH264_libav.c 
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

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

// Pass the contents of a pre-recorded H264 video file through the analysis code to search for moving objects and to
// create long-exposure time-lapse images

// This code is based on the FFmpeg source code; (C) 2001 Fabrice Bellard; distributed under GPL version 2.1

// https://libav.org/documentation/doxygen/master/decode__video_8c_source.html

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

#define INBUF_SIZE 65536

typedef struct context {
    uint8_t inbuf[INBUF_SIZE + AV_INPUT_BUFFER_PADDING_SIZE];
    uint8_t *data;
    int data_size;
    const AVCodec *codec;
    AVCodecContext *c;
    AVCodecParserContext *parser;
    FILE *f;
    AVFrame *picture;
    AVPacket *avpkt;

    int frame;
    double utc_start, utc_stop, fps;
    const char *filename, *mask_file;
    unsigned char *mask;
} context;

int fetch_frame(void *ctx_void, unsigned char *tmpc, double *utc) {
    context *ctx = (context *) ctx_void;

    if (utc) *utc = ctx->utc_start + ctx->frame / ctx->fps;

    while (1) {
        if (ctx->data_size == 0) {
            if (feof(ctx->f)) {
                snprintf(temp_err_string, FNAME_LENGTH, "End of video file");
                logging_error(ERR_GENERAL, temp_err_string);
                return 1;
            }

            ctx->data_size = fread(ctx->inbuf, 1, INBUF_SIZE, ctx->f);
            ctx->data = ctx->inbuf;
        } else {
            int ret = av_parser_parse2(ctx->parser, ctx->c,
                                       &ctx->avpkt->data, &ctx->avpkt->size,
                                       ctx->data, ctx->data_size,
                                       AV_NOPTS_VALUE, AV_NOPTS_VALUE, 0);
            if (ret < 0) {
                logging_error(ERR_GENERAL, "Error while parsing (av_parser_parse2)");
                return 1;
            }

            ctx->data += ret;
            ctx->data_size -= ret;

            if (ctx->avpkt->size) {

                int status1 = avcodec_send_packet(ctx->c, ctx->avpkt);

                if (status1) {
                    snprintf(temp_err_string, FNAME_LENGTH,
                             "In input file <%s>, error decoding frame %d; avcodec_send_packet returned %d.",
                             ctx->filename, ctx->frame, status1);
                    logging_error(ERR_GENERAL, temp_err_string);

                    av_strerror(status1, temp_err_string, LSTR_LENGTH);
                    logging_error(ERR_GENERAL, temp_err_string);

                    return 1;
                }

                int status2 = avcodec_receive_frame(ctx->c, ctx->picture);
                if (status2 == AVERROR(EAGAIN)) continue;

                if (status2) {
                    snprintf(temp_err_string, FNAME_LENGTH,
                             "In input file <%s>, error decoding frame %d; avcodec_receive_frame returned %d.",
                             ctx->filename, ctx->frame, status2);
                    logging_error(ERR_GENERAL, temp_err_string);

                    av_strerror(status2, temp_err_string, LSTR_LENGTH);
                    logging_error(ERR_GENERAL, temp_err_string);

                    return 1;
                }

                if (tmpc) {
                    const int w = ctx->c->width;
                    const int h = ctx->c->height;
                    const int s = w * h;
                    int i;
                    for (i = 0; i < h; i++)
                        memcpy(tmpc + +i * w,
                               ctx->picture->data[0] + i * ctx->picture->linesize[0],
                               w);
                    for (i = 0; i < h / 2; i++)
                        memcpy(tmpc + s + i * w / 2,
                               ctx->picture->data[1] + i * ctx->picture->linesize[1],
                               w / 2);
                    for (i = 0; i < h / 2; i++)
                        memcpy(tmpc + s * 5 / 4 + i * w / 2,
                               ctx->picture->data[2] + i * ctx->picture->linesize[2],
                               w / 2);
                }
                ctx->frame++;

                if ((ctx->frame % 1000) == 0) {
                    printf("Time point %02dh%02dm%02d (frame %d)\n",
                           (int) (ctx->frame / ctx->fps / 3600) % 100,
                           (int) (ctx->frame / ctx->fps / 60) % 60,
                           (int) (ctx->frame / ctx->fps) % 60,
                           ctx->frame
                    );
                }

                return 0;
            }
        }
    }
}

int decoder_init(context *ctx) {
    printf("Decoding file <%s>\n", ctx->filename);

    // Register all the codecs
    avcodec_register_all();

    // Set end of buffer to 0. This ensures that no over-reading happens for
    // damaged streams.
    memset(ctx->inbuf + INBUF_SIZE, 0, AV_INPUT_BUFFER_PADDING_SIZE);

    ctx->avpkt = av_packet_alloc();

    // find the H264 video decoder
    ctx->codec = avcodec_find_decoder(AV_CODEC_ID_H264);
    if (!ctx->codec) {
        logging_fatal(__FILE__, __LINE__, "codec not found");
    }

    ctx->parser = av_parser_init(ctx->codec->id);
    if (!ctx->parser) {
        logging_fatal(__FILE__, __LINE__, "parser not found");
    }

    ctx->c = avcodec_alloc_context3(ctx->codec);

    ctx->picture = av_frame_alloc();

    if (avcodec_open2(ctx->c, ctx->codec, NULL) != 0) {
        logging_fatal(__FILE__, __LINE__, "could not open codec");
    }

    // Open input file
    ctx->f = fopen(ctx->filename, "rb");

    if (ctx->f == NULL) {
        logging_fatal(__FILE__, __LINE__, "could not open input video");
    }

    ctx->frame = 0;
    ctx->data = NULL;
    ctx->data_size = 0;

    return 0;
}

int decoder_shutdown(context *ctx) {
    fclose(ctx->f);
    av_parser_close(ctx->parser);
    avcodec_free_context(&ctx->c);
    av_frame_free(&ctx->picture);
    av_packet_free(&ctx->avpkt);
    return 0;
}

int rewind_video(void *ctx_void, double *utc) {
    // For some reason, rewinding videos makes libav segfault

    //context *ctx = (context *) ctx_void;
    //decoder_shutdown(ctx);
    //decoder_init(ctx);
    //if (utc) *utc = ctx->utc_start;
    return 0;
}

int create_observation_mask(context *ctx) {
    // Get libav to pick up video size by fetching a frame
    fetch_frame((void *) ctx, NULL, NULL);

    ctx->mask = malloc(ctx->c->width * ctx->c->height);
    FILE *mask_file = fopen(ctx->mask_file, "r");
    if (!mask_file) { logging_fatal(__FILE__, __LINE__, "mask file could not be opened"); }

    fill_polygons_from_file(mask_file, ctx->mask, ctx->c->width, ctx->c->height);
    fclose(mask_file);

    // Rewind video
    rewind_video(ctx, NULL);

    return 0;
}

//! Pass the contents of a pre-recorded H264 video file through the analysis code to search for moving objects and to
//! create long-exposure time-lapse images
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

int main(int argc, const char **argv) {
    context ctx;
    const char *filename = "\0";
    const char *mask_file = "\0";
    const char *obstory_id = "\0";

    ctx.utc_start = 0;
    ctx.utc_stop = time(NULL) + 3600 * 24;
    ctx.fps = 0;

    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &filename, "input filename"),
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

    ctx.filename = filename;
    ctx.mask_file = mask_file;

    initLut();

    decoder_init(&ctx);
    create_observation_mask(&ctx);
    observe((void *) &ctx, obstory_id, ctx.utc_start, ctx.utc_stop, ctx.c->width, ctx.c->height, ctx.fps,
            "nonlive", ctx.mask, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME,
            TRIGGER_SUFFIX_TIME_INITIAL, TRIGGER_MIN_DETECTIONS, TRIGGER_MIN_PATH_LENGTH,
            TRIGGER_MAX_MOVEMENT_PER_FRAME, TRIGGER_MIN_SIGNIFICANCE, TRIGGER_MIN_SIGNIFICANCE_INITIAL,
            VIDEO_BUFFER_LENGTH, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT,
            TIMELAPSE_EXPOSURE, TIMELAPSE_INTERVAL, STACK_TARGET_BRIGHTNESS,
            BACKGROUND_MAP_FRAMES, BACKGROUND_MAP_SAMPLES, BACKGROUND_MAP_REDUCTION_CYCLES,
            &fetch_frame, &rewind_video);
    decoder_shutdown(&ctx);
    printf("\n");
    return 0;
}
