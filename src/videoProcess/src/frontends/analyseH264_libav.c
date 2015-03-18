/*
 * copyright (c) 2001 Fabrice Bellard
 *
 * This file is part of FFmpeg.
 *
 * FFmpeg is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * FFmpeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with FFmpeg; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

/**
 * @file
 * H.264 decoder example, takes raw H.264 bitstreams and plays them using SDL
 * Requirements: libavcodec 0.52 or newer with both CONFIG_H264_DECODER *and* CONFIG_H264_PARSER enabled, a recent version of SDL with the video subsystem enabled. 
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>

#include <sys/time.h>
#include <time.h>

#include <libavcodec/avcodec.h>
#include <libavutil/mathematics.h>

#include <SDL/SDL.h>

void sigint_handler(int signal) {
    printf("\n");
    exit(0);
}

const char *window_title;
SDL_Surface *screen;
SDL_Overlay *yuv_overlay;

#define INBUF_SIZE 80000

/*
 * Video decoding example
 */

static long get_time_diff(struct timeval time_now) {
   struct timeval time_now2;
   gettimeofday(&time_now2,0);
   return time_now2.tv_sec*1.e6 - time_now.tv_sec*1.e6 + time_now2.tv_usec - time_now.tv_usec;
}

int video_open(AVCodecContext *avctx, const char *filename){
    int flags = SDL_HWSURFACE|SDL_ASYNCBLIT|SDL_HWACCEL;
    int w,h;
    
    flags |= SDL_RESIZABLE;

    if (avctx->width){
        w = avctx->width;
        h = avctx->height;
    } else {
        w = 640;
        h = 480;
    }

    if(SDL_Init(SDL_INIT_VIDEO) < 0) {
	fprintf(stderr, "SDL_INIT_VIDEO failed!\n");
	exit(1);
    }

    screen = SDL_SetVideoMode(w, h, 0, flags);

    if (!screen) {
        fprintf(stderr, "SDL: could not set video mode - exiting\n");
        return -1;
    }
    if (!window_title)
        window_title = filename;
    SDL_WM_SetCaption(window_title, window_title);

    yuv_overlay = SDL_CreateYUVOverlay(w, h, SDL_YV12_OVERLAY, screen);

    if (yuv_overlay->hw_overlay) {
	fprintf(stderr, "Using hardware overlay!\n");
    } 

    return 0;
}

int main(int argc, char **argv) {
    AVCodec *codec;
    AVCodecContext *c= NULL;
    AVCodecParserContext *parser = NULL;
    int frame, got_picture, len2, len;
    const char *filename;
    FILE *f;
    AVFrame *picture;
    char *arghwtf = malloc(INBUF_SIZE);
    char *luma = NULL; 
    char *chroma = NULL;
    int i=0;
    uint64_t in_len;
    int pts, dts;
    struct timeval t;
    float inv_fps = 1e6/23.98;
    AVPacket avpkt;
    SDL_Rect rect;

    /* must be called before using avcodec lib */
    avcodec_init();

    /* register all the codecs */
    avcodec_register_all();
                
    filename = argv[1];

    av_init_packet(&avpkt);

    printf("Decoding file %s...\n", filename);

    /* find the H.264 video decoder */
    codec = avcodec_find_decoder(CODEC_ID_H264);
    if (!codec) {
        fprintf(stderr, "codec not found\n");
        exit(1);
    }

    c = avcodec_alloc_context();
    picture = avcodec_alloc_frame();

    c->skip_loop_filter = 48; // skiploopfilter=all

    if (avcodec_open(c, codec) < 0) {
        fprintf(stderr, "could not open codec\n");
        exit(1);
    }

    /* the codec gives us the frame size, in samples */
    parser = av_parser_init(c->codec_id);
    parser->flags |= PARSER_FLAG_ONCE;

    f = fopen(filename, "rb");
    if (!f) {
        fprintf(stderr, "could not open %s\n", filename); 
        exit(1);
    }

    frame = 0;
    gettimeofday(&t, 0);
    if(fread(arghwtf, 1, INBUF_SIZE, f) == 0) {
	exit(1);
    }
	in_len = 80000;
        while (in_len > 0 && !feof(f)) {
	    len = av_parser_parse2(parser, c, &avpkt.data, &avpkt.size, arghwtf, in_len,
                                   pts, dts, AV_NOPTS_VALUE);

            len2 = avcodec_decode_video2(c, picture, &got_picture, &avpkt);
            if (len2 < 0) {
                fprintf(stderr, "Error while decoding frame %d\n", frame);
                exit(1);
            }
            if (got_picture) {
		if(!screen) {
		    video_open(c, filename);

		    rect.x = 0;
		    rect.y = 0;
		    rect.w = c->width;
		    rect.h = c->height;
		    inv_fps = av_q2d(c->time_base); 
		    fprintf(stderr, "w:%i h:%i\n", rect.w, rect.h);

		    luma = malloc(c->width*c->height);
		    chroma = malloc(c->width*c->height/4);

		    SDL_DisplayYUVOverlay(yuv_overlay, &rect);

		    signal(SIGINT, sigint_handler);
		}		
                fprintf(stderr, "\rDisplaying %c:frame %3d (%02d:%02d)...", av_get_pict_type_char(picture->pict_type), frame, frame/1440, (frame/24)%60);
                fflush(stderr);

		SDL_LockYUVOverlay(yuv_overlay);

                for(i=0;i<c->height;i++) {
                  memcpy(luma + i * c->width, picture->data[0] + i * picture->linesize[0], c->width);
                }
		memcpy(yuv_overlay->pixels[0], luma, c->width * c->height);
                for(i=0;i<c->height/2;i++) {
                  memcpy(chroma + i * c->width/2, picture->data[2] + i * picture->linesize[2], c->width/2);
                }
		memcpy(yuv_overlay->pixels[1], chroma, c->width * c->height / 4);
                for(i=0;i<c->height/2;i++) {
                  memcpy(chroma + i * c->width/2, picture->data[1] + i * picture->linesize[1], c->width/2);
                }
		memcpy(yuv_overlay->pixels[2], chroma, c->width * c->height / 4);

		SDL_UnlockYUVOverlay(yuv_overlay);
		SDL_DisplayYUVOverlay(yuv_overlay, &rect);

		while(get_time_diff(t) < inv_fps) {
		    usleep(1000);
		}
                frame++;
		gettimeofday(&t, 0);
            }
	    memcpy(arghwtf, arghwtf + len, 80000-len);
	    fread(arghwtf + 80000 - len, 1, len, f);
        }

    /* some codecs, such as MPEG, transmit the I and P frame with a
       latency of one frame. You must do the following to have a
       chance to get the last frame of the video */
    avpkt.data = NULL;
    avpkt.size = 0;
    len = avcodec_decode_video2(c, picture, &got_picture, &avpkt);
    if (got_picture) {
        printf("saving last frame %3d\n", frame);
        fflush(stdout);

	/* Display last frame here, same code as in the decoding loop above. */

        frame++;
    }

    fclose(f);

    avcodec_close(c);
    av_free(c);
    av_free(picture);
    printf("\n");
}
