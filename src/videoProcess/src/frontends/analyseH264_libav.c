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
#include <libavutil/mem.h>
#include <libavutil/mathematics.h>

#include "analyse/observe.h"
#include "utils/asciidouble.h"
#include "utils/error.h"
#include "settings.h"

void sigint_handler(int signal) { printf("\n"); exit(0); }

#define INBUF_SIZE 80000

typedef struct context
 {
    AVCodec *codec;
    AVCodecContext *c;
    AVCodecParserContext *parser;
    int frame, got_picture, len2, len;
    double tstart, tstop, utcoffset, FPS;
    const char *filename;
    FILE *f;
    AVFrame *picture;
    uint8_t *arghwtf;
    //char *luma;
    // char *chroma;
    uint64_t in_len;
    int pts, dts;
    //struct timeval t;
    float inv_fps;
    AVPacket avpkt;
 } context;


int fetchFrame(void *ctx_void, unsigned char *tmpc, double *utc)
 {
  context *ctx = (context *)ctx_void;

  if (utc) *utc = ctx->tstart + ctx->FPS*ctx->frame;

  while (ctx->in_len > 0 && !feof(ctx->f))
   {
    ctx->len = av_parser_parse2(ctx->parser, ctx->c, &ctx->avpkt.data, &ctx->avpkt.size, ctx->arghwtf, ctx->in_len, ctx->pts, ctx->dts, AV_NOPTS_VALUE);
    ctx->len2 = avcodec_decode_video2(ctx->c, ctx->picture, &ctx->got_picture, &ctx->avpkt);

    if (ctx->len2 < 0) { sprintf(temp_err_string, "In input file <%s>, error decoding frame %d", ctx->filename, ctx->frame); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

    if (ctx->got_picture)
     {
      int i;
      if (ctx->frame==0)
       {
        ctx->inv_fps = av_q2d(ctx->c->time_base);
        //ctx->luma = malloc(ctx->c->width*ctx->c->height);
        //ctx->chroma = malloc(ctx->c->width*ctx->c->height/4);
       }

      //fprintf(stderr, "\rDisplaying %c:frame %3d (%02d:%02d)...", av_get_pict_type_char(picture->pict_type), frame, frame/1440, (frame/24)%60); fflush(stderr);
      if (tmpc) for(i=0;i<ctx->c->height;i++) memcpy(tmpc + i * ctx->c->width, ctx->picture->data[0] + i * ctx->picture->linesize[0], ctx->c->width);
      //memcpy(yuv_overlay->pixels[0], luma, c->width * c->height);
      //for(i=0;i<c->height/2;i++) memcpy(chroma + i * c->width/2, picture->data[2] + i * picture->linesize[2], c->width/2);
      //memcpy(yuv_overlay->pixels[1], chroma, c->width * c->height / 4);
      //for(i=0;i<c->height/2;i++) memcpy(chroma + i * c->width/2, picture->data[1] + i * picture->linesize[1], c->width/2);
      //memcpy(yuv_overlay->pixels[2], chroma, c->width * c->height / 4);

      ctx->frame++;
     }
    memcpy(ctx->arghwtf, ctx->arghwtf + ctx->len, 80000-ctx->len);
    fread(ctx->arghwtf + 80000 - ctx->len, 1, ctx->len, ctx->f);
    if (ctx->got_picture) return 0;
   }

  // some codecs, such as MPEG, transmit the I and P frame with a latency of one frame. You must do the following to have a chance to get the last frame of the video
  ctx->avpkt.data = NULL;
  ctx->avpkt.size = 0;
  ctx->len = avcodec_decode_video2(ctx->c, ctx->picture, &ctx->got_picture, &ctx->avpkt);
  if (ctx->got_picture)
   {
    int i;
    for(i=0;i<ctx->c->height;i++) memcpy(tmpc + i * ctx->c->width, ctx->picture->data[0] + i * ctx->picture->linesize[0], ctx->c->width);
    ctx->frame++;
    return 0;
   }
  return 1;
 }

int main(int argc, char **argv)
 {
  context ctx;
  ctx.c = NULL;
  ctx.parser = NULL;
  ctx.arghwtf = malloc(INBUF_SIZE);

  // Register all the codecs
  avcodec_register_all();
                
  ctx.filename = argv[1];
  ctx.tstart   = GetFloat(argv[2],NULL);
  ctx.tstop    = time(NULL)+3600*24;
  ctx.utcoffset= 0;
  ctx.FPS      = VIDEO_FPS;

  av_init_packet(&ctx.avpkt);

  printf("Decoding file <%s>\n", ctx.filename);

  // Find the H.264 video decoder
  ctx.codec = avcodec_find_decoder(CODEC_ID_H264);
  if (!ctx.codec) { gnom_fatal(__FILE__,__LINE__,"codec not found"); }

  ctx.c = avcodec_alloc_context3(NULL);
  ctx.picture = avcodec_alloc_frame();

  ctx.c->skip_loop_filter = 48; // skiploopfilter=all

  if (avcodec_open2(ctx.c, ctx.codec, NULL) < 0) { gnom_fatal(__FILE__,__LINE__,"codec could not be opened"); }

  // The codec gives us the frame size, in samples
  ctx.parser = av_parser_init(ctx.c->codec_id);
  ctx.parser->flags |= PARSER_FLAG_ONCE;

  ctx.f = fopen(ctx.filename, "rb");
  if (!ctx.f) { sprintf(temp_err_string, "Could not open input file <%s>", ctx.filename); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  signal(SIGINT, sigint_handler);

  ctx.frame = 0;
  if (fread(ctx.arghwtf, 1, INBUF_SIZE, ctx.f) == 0) { exit(1); }
  ctx.in_len = 80000;

  fetchFrame((void *)&ctx, NULL, NULL); // Get libav to pick up video size
  observe((void *)&ctx, ctx.utcoffset, ctx.tstart, ctx.tstop, ctx.c->width, ctx.c->height, "live", &fetchFrame);

  fclose(ctx.f);

  avcodec_close(ctx.c);
  av_free(ctx.c);
  av_free(ctx.picture);
  printf("\n");
  return 0;
 }
