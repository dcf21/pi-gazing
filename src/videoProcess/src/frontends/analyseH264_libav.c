// analyseH264_libav.c 
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

#include "analyse/observe.h"
#include "utils/asciidouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/filledPoly.h"
#include "vidtools/color.h"
#include "settings.h"

extern char *analysisCameraId;

void sigint_handler(int signal) { printf("\n"); exit(0); }

#define INBUF_SIZE 200000

typedef struct context
 {
    AVCodec *codec;
    AVCodecContext *c;
    int frame, got_picture, len2, len, streamNum;
    double tstart, tstop, utcoffset, FPS;
    const char *filename, *maskFile;
    unsigned char *mask;
    FILE *f;
    AVFrame *picture;
    int pts, dts;
    AVPacket avpkt;
    AVFormatContext *avFormatPtr;
 } context;

int fetchFrame(void *ctx_void, unsigned char *tmpc, double *utc)
 {
  context *ctx = (context *)ctx_void;

  if (utc) *utc = ctx->tstart + ctx->frame / ctx->FPS;

  while (1)
   {
    av_init_packet(&ctx->avpkt);
    ctx->len  = av_read_frame(ctx->avFormatPtr, &ctx->avpkt);
    ctx->len2 = avcodec_decode_video2(ctx->c, ctx->picture, &ctx->got_picture, &ctx->avpkt);

    if (ctx->len < 0) { sprintf(temp_err_string, "In input file <%s>, error decoding frame %d", ctx->filename, ctx->frame); gnom_error(ERR_GENERAL,temp_err_string); }

    if (ctx->got_picture)
     {
      if (tmpc)
       {
        const int w = ctx->c->width;
        const int h = ctx->c->height;
        const int s = w*h;
        int i;
        for (i=0;i<h  ;i++) memcpy(tmpc +       + i*w  , ctx->picture->data[0] + i*ctx->picture->linesize[0], w  );
        for (i=0;i<h/2;i++) memcpy(tmpc + s     + i*w/2, ctx->picture->data[1] + i*ctx->picture->linesize[1], w/2);
        for (i=0;i<h/2;i++) memcpy(tmpc + s*5/4 + i*w/2, ctx->picture->data[2] + i*ctx->picture->linesize[2], w/2);
       }
      ctx->frame++;
     }
    av_free_packet(&ctx->avpkt);
    if (ctx->got_picture) return 0;
    if (!ctx->got_picture) return 1;
   }

  return 1;
 }

int decoder_init(context *ctx)
 { 
  printf("Decoding file <%s>\n", ctx->filename);
  ctx->avFormatPtr = avformat_alloc_context();
  if (avformat_open_input(&ctx->avFormatPtr, ctx->filename, NULL, NULL) != 0) { gnom_fatal(__FILE__,__LINE__,"could not open input video"); }
  ctx->streamNum = av_find_best_stream(ctx->avFormatPtr, AVMEDIA_TYPE_VIDEO, -1, -1, &ctx->codec, 0);
  if (!ctx->codec) { gnom_fatal(__FILE__,__LINE__,"codec not found"); }
  ctx->c           = avcodec_alloc_context3(ctx->codec);
  if (avcodec_open2(ctx->c, ctx->codec, NULL) < 0) { gnom_fatal(__FILE__,__LINE__,"codec could not be opened"); }
  ctx->picture = avcodec_alloc_frame();
  signal(SIGINT, sigint_handler);
  ctx->frame = 0;
  fetchFrame((void *)ctx, NULL, NULL); // Get libav to pick up video size
  ctx->mask = malloc( ctx->c->width * ctx->c->height );
  FILE *maskfile = fopen(ctx->maskFile,"r");
  if (!maskfile) { gnom_fatal(__FILE__,__LINE__,"mask file could not be opened"); }
  fillPolygonsFromFile(maskfile, ctx->mask, ctx->c->width, ctx->c->height);
  fclose(maskfile);
  return 0;
 }

int decoder_shutdown(context *ctx)
 {
  avcodec_close(ctx->c);
  av_free(ctx->c);
  av_free(ctx->picture); 
  return 0;
 }

int rewindVideo(void *ctx_void, double *utc)
 {
  context *ctx = (context *)ctx_void;
  decoder_shutdown(ctx);
  decoder_init(ctx);
  if (utc) *utc = ctx->tstart;
  return 0;
 }

int main(int argc, char **argv)
 {
  context ctx;

  if (argc!=5)
   {
    sprintf(temp_err_string, "ERROR: Command line syntax is:\n\n analyseH264_libav <filename> <tstart> <fps> <cameraId>\n\ne.g.\n\n analyseH264_libav foo.rawvid 1234 24.71 xxx\n"); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  ctx.filename = argv[1];
  ctx.tstart   = GetFloat(argv[2],NULL);
  ctx.tstop    = time(NULL)+3600*24;
  ctx.utcoffset= 0;
  ctx.FPS      = GetFloat(argv[3],NULL);
  ctx.maskFile = argv[4];
  analysisCameraId = argv[5];
  initLut();

  // Register all the codecs
  av_register_all();
  avcodec_register_all();
  decoder_init(&ctx);
  observe((void *)&ctx, ctx.utcoffset, ctx.tstart, ctx.tstop, ctx.c->width, ctx.c->height, "nonlive", ctx.mask, &fetchFrame, &rewindVideo);
  decoder_shutdown(&ctx);
  printf("\n");
  return 0;
 }

