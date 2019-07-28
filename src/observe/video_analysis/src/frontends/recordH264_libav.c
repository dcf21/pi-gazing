// recordH264_libav.c
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

// Record a video stream from a webcam to an H264 video file for later analysis, using libav (software encoding).

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <stdarg.h>
#include <string.h>
#include <errno.h>

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/mem.h>
#include <libavutil/mathematics.h>
#include <x264.h>

#include "argparse/argparse.h"
#include "vidtools/v4l2uvc.h"
#include "utils/asciiDouble.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

#define H264_FPS 25

// Fetch an input frame from v4l2
int fetchFrame(struct video_info *video_in, unsigned char *tmpc, int upside_down) {
    int status = uvcGrab(video_in);
    if (status) return status;
    Pyuv422to420(video_in->frame_buffer, tmpc, video_in->width, video_in->height, upside_down);
    return 0;
}

static const char *const usage[] = {
    "recordH264_libav [options] [[--] args]",
    "recordH264_libav [options]",
    NULL,
};

//! Record a video stream from a webcam to an H264 video file for later analysis, using libav (software encoding).
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

int main(int argc, const char *argv[]) {
    video_metadata vmd;
    char line[FNAME_LENGTH];
    int got_packet_ptr;
    const char *mask_file = "\0";
    const char *obstory_id = "\0";
    const char *input_device = "\0";
    const char *output_filename = "\0";

    vmd.utc_start = time(NULL);
    vmd.utc_stop = vmd.utc_start + 5;
    vmd.frame_count = 0;
    vmd.width = 720;
    vmd.height = 480;
    vmd.fps = 24.71;
    vmd.lat = 52.2;
    vmd.lng = 0.12;
    vmd.flag_gps = 0;
    vmd.flag_upside_down = 0;

    struct argparse_option arg_options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('o', "obsid", &obstory_id, "observatory id"),
        OPT_STRING('x', "output", &output_filename, "output filename"),
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
    argparse_init(&argparse, arg_options, usage, 0);
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
    char product_filename[4096];
    sprintf(product_filename, "%s.h264", vmd.filename);

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

    const int image_size = width * height;
    const int frame_size = width * height * 3 / 2;

    // Temporary frame buffer for converting YUV422 data from v4l2 into YUV420
    unsigned char *tmpc = malloc(frame_size * 1.5);
    if (!tmpc) logging_fatal(__FILE__, __LINE__, "Malloc fail");

    // Init libav encoding context
    av_register_all();
    avcodec_register_all();

    AVCodec *codecEncode;
    AVCodecContext *ctxEncode = NULL;

    AVFrame *pictureEncoded;
    AVPacket avpkt;

    int frame_in = 0, frame_out = 0;

    AVFormatContext *outContainer = avformat_alloc_context();
    outContainer->oformat = av_guess_format("mp4", NULL, NULL);
    outContainer->oformat->video_codec = AV_CODEC_ID_H264;
    snprintf(outContainer->filename, sizeof(outContainer->filename), "%s", product_filename);

    codecEncode = avcodec_find_encoder(outContainer->oformat->video_codec);
    if (!codecEncode) { logging_fatal(__FILE__, __LINE__, "codec not found"); }

    AVStream *video_avstream = avformat_new_stream(outContainer, codecEncode);
    if (!video_avstream) { logging_fatal(__FILE__, __LINE__, "Could not alloc stream"); }
    if (video_avstream->codec == NULL) { logging_fatal(__FILE__, __LINE__, "AVStream codec is NULL"); }

    ctxEncode = video_avstream->codec;

    /* put sample parameters */
    ctxEncode->bit_rate = 6000 * 1000;
    ctxEncode->bit_rate_tolerance = 0;
    ctxEncode->rc_max_rate = 0;
    ctxEncode->rc_buffer_size = 0;
    ctxEncode->gop_size = 30;
    ctxEncode->max_b_frames = 3;
    ctxEncode->b_frame_strategy = 1;
    ctxEncode->coder_type = 1;
    ctxEncode->me_cmp = 1;
    ctxEncode->me_range = 16;
    ctxEncode->qmin = 10;
    ctxEncode->qmax = 51;
    ctxEncode->scenechange_threshold = 40;
    ctxEncode->flags |= AV_CODEC_FLAG_LOOP_FILTER;
    ctxEncode->me_subpel_quality = 5;
    ctxEncode->i_quant_factor = 0.71;
    ctxEncode->qcompress = 0.6;
    ctxEncode->max_qdiff = 4;
    ctxEncode->trellis = 1; // trellis=1

    ctxEncode->width = width;
    ctxEncode->height = height;
    ctxEncode->time_base = (AVRational) {1, nearest_multiple(H264_FPS, 1)};
    ctxEncode->pix_fmt = AV_PIX_FMT_YUV420P;

    AVDictionary *options = NULL;
    av_dict_set(&options, "preset", "veryfast", 0);

    /* open codec for encoder*/
    if (avcodec_open2(ctxEncode, codecEncode, &options) < 0) { logging_fatal(__FILE__, __LINE__, "could not open codec"); }

    pictureEncoded = av_frame_alloc();
    if (!pictureEncoded) { logging_fatal(__FILE__, __LINE__, "Could not allocate video frame"); }

    // some formats want stream headers to be separate
    if (outContainer->oformat->flags & AVFMT_GLOBALHEADER) ctxEncode->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;

    if (!(ctxEncode->flags & AVFMT_NOFILE)) {
        if (avio_open(&outContainer->pb, product_filename, AVIO_FLAG_WRITE) < 0) {
            logging_fatal(__FILE__, __LINE__, "could not open output file");
        }
    }

    avformat_write_header(outContainer, NULL);

    // encode loop
    while (1) {
        int i, j;

        int t = time(NULL);
        if (t >= vmd.utc_stop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

        if (fetchFrame(video_in, tmpc, vmd.flag_upside_down)) {
            break;
        }

        avpicture_alloc((AVPicture *) pictureEncoded, ctxEncode->pix_fmt, ctxEncode->width, ctxEncode->height);

        // Copy Y channel
        for (j = 0; j < height; j++) {
            memcpy(pictureEncoded->data[0] + j * pictureEncoded->linesize[0],
                   tmpc + j * width,
                   width);
        }

        // Copy U channel
        for (j = 0; j < height / 2; j++) {
            memcpy(pictureEncoded->data[1] + j * pictureEncoded->linesize[1],
                   tmpc + image_size + j * width / 2,
                   width / 2);
        }

        // Copy V channel
        for (j = 0; j < height / 2; j++) {
            memcpy(pictureEncoded->data[2] + j * pictureEncoded->linesize[2],
                   tmpc + image_size * 5 / 4 + j * width / 2,
                   width / 2);
        }

        /* encode frame */
        av_init_packet(&avpkt);
        avpkt.data = NULL;    // packet data will be allocated by the encoder
        avpkt.size = 0;
        pictureEncoded->pts = av_rescale_q(frame_in, video_avstream->codec->time_base, video_avstream->time_base);
        i = avcodec_encode_video2(ctxEncode, &avpkt, pictureEncoded, &got_packet_ptr);
        // printf(". %d %d %d\n",got_packet_ptr,avpkt.flags,avpkt.size);
        // if (got_packet_ptr) fwrite(avpkt.data,1,avpkt.size,tmpout);
        avpicture_free((AVPicture *) pictureEncoded);
        if (i) printf("error encoding frame\n");
        frame_in++;
        if (got_packet_ptr) {
            frame_out++;
            av_write_frame(outContainer, &avpkt);
        }
        av_packet_unref(&avpkt);
        
        // Increment frame counter
        vmd.frame_count++;
    }

    while (1) {
        int i;

        av_init_packet(&avpkt);
        avpkt.data = NULL;    // packet data will be allocated by the encoder
        avpkt.size = 0;
        i = avcodec_encode_video2(ctxEncode, &avpkt, NULL, &got_packet_ptr);
        // printf("! %d %d %d\n",got_packet_ptr,avpkt.flags,avpkt.size);
        // if (got_packet_ptr) fwrite(avpkt.data,1,avpkt.size,tmpout);
        // printf("encoding frame %3d (size=%5d)\n", frame_in, avpkt->size);
        if (!got_packet_ptr) break;
        frame_out++;
        av_write_frame(outContainer, &avpkt);
        av_packet_unref(&avpkt);
    }

    //fclose(tmpout);
    write_raw_video_metadata(vmd);
    
    av_write_trailer(outContainer);
    av_freep(video_avstream);
    if (!(outContainer->oformat->flags & AVFMT_NOFILE)) avio_close(outContainer->pb);
    avformat_free_context(outContainer);
    av_free(pictureEncoded);
    return 0;
}
