// rawvid2mp4_libav.c 
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

// Convert a raw video file into a compressed MP4 file, using libav (software encoding).

// Due to the tight constraints on data processing when analysing video in real time, we dump video to disk in
// uncompressed format. This converter is used to turn the raw video into a compressed MP4 file that video players
// will accept.

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
#include "png/image.h"
#include "utils/error.h"
#include "settings.h"

#define H264_FPS 25

int nearest_multiple(double in, int factor) {
    return (int) (round(in / factor) * factor);
}

static const char *const usage[] = {
        "rawvid2mp4_libav [options] [[--] args]",
        "rawvid2mp4_libav [options]",
        NULL,
};

int main(int argc, const char **argv) {
    // Read commandline switches
    const char *input_filename = "\0";
    const char *output_filename = "\0";

    struct argparse_option arg_options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, arg_options, usage, 0);
    argparse_describe(&argparse,
                      "\nConvert raw video files into MP4 format using libav.",
                      "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    FILE *infile;
    if ((infile = fopen(input_filename, "rb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output raw video file %s.\n", input_filename);
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int size, width, height, i, got_packet_ptr;
    i = fread(&size, sizeof(int), 1, infile);
    i = fread(&width, sizeof(int), 1, infile);
    i = fread(&height, sizeof(int), 1, infile);

    size -= 3 * sizeof(int);
    unsigned char *video_raw = malloc(size);
    if (video_raw == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }
    i = fread(video_raw, 1, size, infile);
    fclose(infile);

    const int image_size = width * height;
    const int frame_size = width * height * 3 / 2;
    const int frame_count = size / frame_size;

    // Init context
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
    snprintf(outContainer->filename, sizeof(outContainer->filename), "%s", output_filename);

    codecEncode = avcodec_find_encoder(outContainer->oformat->video_codec);
    if (!codecEncode) { logging_fatal(__FILE__, __LINE__, "codec not found"); }

    AVStream *video_avstream = avformat_new_stream(outContainer, codecEncode);
    if (!video_avstream) { logging_fatal(__FILE__, __LINE__, "Could not alloc stream"); }
    if (video_avstream->codec == NULL) { logging_fatal(__FILE__, __LINE__, "AVStream codec is NULL"); }

    ctxEncode = video_avstream->codec;

    /* put sample parameters */
    ctxEncode->bit_rate = 500 * 1000;
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

    video_avstream->time_base = (AVRational) {1, nearest_multiple(H264_FPS, 1)};

    AVDictionary *options = NULL;
    av_dict_set(&options, "preset", "veryfast", 0);

    /* open codec for encoder*/
    if (avcodec_open2(ctxEncode, codecEncode, &options) < 0) { logging_fatal(__FILE__, __LINE__, "could not open codec"); }

    pictureEncoded = av_frame_alloc();
    if (!pictureEncoded) { logging_fatal(__FILE__, __LINE__, "Could not allocate video frame"); }

    // some formats want stream headers to be separate
    if (outContainer->oformat->flags & AVFMT_GLOBALHEADER) ctxEncode->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;

    if (!(ctxEncode->flags & AVFMT_NOFILE)) {
        if (avio_open(&outContainer->pb, output_filename, AVIO_FLAG_WRITE) < 0) {
            logging_fatal(__FILE__, __LINE__, "could not open output file");
        }
    }

    avformat_write_header(outContainer, NULL);

    /* encode loop */
    while (frame_in < frame_count) {
        int j;
        avpicture_alloc((AVPicture *) pictureEncoded, ctxEncode->pix_fmt, ctxEncode->width, ctxEncode->height);
        for (j = 0; j < height; j++)
            memcpy(pictureEncoded->data[0] + j * pictureEncoded->linesize[0], video_raw + frame_in * frame_size + j * width,
                   width);
        for (j = 0; j < height / 2; j++)
            memcpy(pictureEncoded->data[1] + j * pictureEncoded->linesize[1],
                   video_raw + frame_in * frame_size + image_size + j * width / 2, width / 2);
        for (j = 0; j < height / 2; j++)
            memcpy(pictureEncoded->data[2] + j * pictureEncoded->linesize[2],
                   video_raw + frame_in * frame_size + image_size * 5 / 4 + j * width / 2, width / 2);

        /* encode frame */
        av_init_packet(&avpkt);
        avpkt.data = NULL;    // packet data will be allocated by the encoder
        avpkt.size = 0;
        pictureEncoded->pts = av_rescale_q(frame_in, video_avstream->codec->time_base, video_avstream->time_base);
        pictureEncoded->format = ctxEncode->pix_fmt;
        pictureEncoded->width = ctxEncode->width;
        pictureEncoded->height = ctxEncode->height;
        i = avcodec_encode_video2(ctxEncode, &avpkt, pictureEncoded, &got_packet_ptr);
//printf(". %d %d %d\n",got_packet_ptr,avpkt.flags,avpkt.size); if (got_packet_ptr) fwrite(avpkt.data,1,avpkt.size,tmpout);
        avpicture_free((AVPicture *) pictureEncoded);
        if (i) printf("error encoding frame\n");
        frame_in++;
        if (got_packet_ptr) {
            frame_out++;
            av_write_frame(outContainer, &avpkt);
        }
        av_free_packet(&avpkt);
    }

    while (1) {
        av_init_packet(&avpkt);
        avpkt.data = NULL;    // packet data will be allocated by the encoder
        avpkt.size = 0;
        i = avcodec_encode_video2(ctxEncode, &avpkt, NULL, &got_packet_ptr);
//printf("! %d %d %d\n",got_packet_ptr,avpkt.flags,avpkt.size); if (got_packet_ptr) fwrite(avpkt.data,1,avpkt.size,tmpout);
        //printf("encoding frame %3d (size=%5d)\n", frame_in, avpkt->size);
        if (!got_packet_ptr) break;
        frame_out++;
        av_write_frame(outContainer, &avpkt);
        av_free_packet(&avpkt);
    }

//fclose(tmpout);
    av_write_trailer(outContainer);
    av_freep(video_avstream);
    if (!(outContainer->oformat->flags & AVFMT_NOFILE)) avio_close(outContainer->pb);
    avformat_free_context(outContainer);
    av_free(pictureEncoded);
    return 0;
}
