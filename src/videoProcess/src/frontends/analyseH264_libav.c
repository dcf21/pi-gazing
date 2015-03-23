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

#define INBUF_SIZE 200000

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
    //char *chroma;
    uint64_t in_len;
    int pts, dts;
    //struct timeval t;
    float inv_fps;
    AVPacket avpkt;
 } context;

int fetchFrame(void *ctx_void, unsigned char *tmpc, double *utc)
 {
  context *ctx = (context *)ctx_void;

  if (utc) *utc = ctx->tstart + ctx->frame / ctx->FPS;

  while (1)
   {
    av_init_packet(&ctx->avpkt);
    ctx->len  = av_parser_parse2(ctx->parser, ctx->c, &ctx->avpkt.data, &ctx->avpkt.size, ctx->arghwtf, ctx->in_len, ctx->pts, ctx->dts, AV_NOPTS_VALUE);
    ctx->len2 = avcodec_decode_video2(ctx->c, ctx->picture, &ctx->got_picture, &ctx->avpkt);

    if (ctx->in_len && (ctx->len < 0)) { sprintf(temp_err_string, "In input file <%s>, error decoding frame %d", ctx->filename, ctx->frame); gnom_error(ERR_GENERAL,temp_err_string); }

    if (ctx->got_picture)
     {
      int i;
      if (tmpc) for(i=0;i<ctx->c->height;i++) memcpy(tmpc + i * ctx->c->width, ctx->picture->data[0] + i * ctx->picture->linesize[0], ctx->c->width);
      ctx->frame++;
     }
    uint64_t remainingBufLen = ctx->in_len-ctx->len;
    memcpy(ctx->arghwtf, ctx->arghwtf + ctx->len, remainingBufLen);
    uint64_t newBufLen = remainingBufLen;
    if (!feof(ctx->f)) newBufLen += fread(ctx->arghwtf + remainingBufLen, 1, INBUF_SIZE-remainingBufLen, ctx->f);
    ctx->in_len = newBufLen;
    if (ctx->got_picture) return 0;
    if ((!ctx->got_picture)&&(feof(ctx->f))) return 1;
   }

  return 1;
 }

int decoder_init(context *ctx)
 { 
  ctx->c = NULL;
  ctx->parser = NULL;

  printf("Decoding file <%s>\n", ctx->filename);

  // Find the H.264 video decoder
  ctx->codec = avcodec_find_decoder(CODEC_ID_H264);
  if (!ctx->codec) { gnom_fatal(__FILE__,__LINE__,"codec not found"); }

  ctx->c = avcodec_alloc_context3(ctx->codec);
  if (ctx->codec->capabilities&CODEC_CAP_TRUNCATED) ctx->c->flags|= CODEC_FLAG_TRUNCATED; /* we do not send complete frames */

  ctx->c->width    = VIDEO_WIDTH;
  ctx->c->height   = VIDEO_HEIGHT;
  ctx->c->pix_fmt  = AV_PIX_FMT_YUV420P;
  ctx->c->time_base= (AVRational){1,VIDEO_FPS};

  ctx->picture = avcodec_alloc_frame();

  //ctx->c->skip_loop_filter = 48; // skiploopfilter=all

  if (avcodec_open2(ctx->c, ctx->codec, NULL) < 0) { gnom_fatal(__FILE__,__LINE__,"codec could not be opened"); }

  // The codec gives us the frame size, in samples
  ctx->parser = av_parser_init(ctx->c->codec_id);

  //ctx->parser->flags |= PARSER_FLAG_ONCE;

  ctx->f = fopen(ctx->filename, "rb");
  if (!ctx->f) { sprintf(temp_err_string, "Could not open input file <%s>", ctx->filename); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  signal(SIGINT, sigint_handler);

  ctx->frame = 0;
  if ((ctx->in_len=fread(ctx->arghwtf, 1, INBUF_SIZE, ctx->f)) == 0) { exit(1); }

  fetchFrame((void *)ctx, NULL, NULL); // Get libav to pick up video size
  return 0;
 }


int decoder_shutdown(context *ctx)
 {
  fclose(ctx->f);
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
  ctx.arghwtf = malloc(INBUF_SIZE);

  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw video filename on commandline, followed by UTC time of start of video, e.g. 'analyseH264_libav foo.rawvid 1234'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  ctx.filename = argv[1];
  ctx.tstart   = GetFloat(argv[2],NULL);
  ctx.tstop    = time(NULL)+3600*24;
  ctx.utcoffset= 0;
  ctx.FPS      = VIDEO_FPS;

  // Register all the codecs
  avcodec_register_all();
  decoder_init(&ctx);
  observe((void *)&ctx, ctx.utcoffset, ctx.tstart, ctx.tstop, ctx.c->width, ctx.c->height, "nonlive", &fetchFrame, &rewindVideo);
  decoder_shutdown(&ctx);
  printf("\n");
  return 0;
 }

