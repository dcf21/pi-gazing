// rawvid2mp4_libav.c 
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "utils/tools.h"
#include "jpeg/jpeg.h"
#include "utils/error.h"

#include "settings.h"

#include <stdarg.h>
#include <string.h>
#include <errno.h>

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/mem.h>
#include <libavutil/mathematics.h>
#include <x264.h>

int main(int argc, char **argv)
 {
  // Read commandline switches

  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawvid2mp4_libav foo.raw frame.mp4'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char *rawFname = argv[1];
  char *frOut = argv[2];

  FILE *infile;
  if ((infile = fopen(rawFname,"rb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output raw video file %s.\n", rawFname); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  int size, width, height, i, got_packet_ptr;
  i=fread(&size  ,sizeof(int),1,infile);
  i=fread(&width ,sizeof(int),1,infile);
  i=fread(&height,sizeof(int),1,infile);

  size-=3*sizeof(int);
  unsigned char *vidRaw = malloc(size);
  if (vidRaw==NULL) { sprintf(temp_err_string, "ERROR: malloc fail"); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  i=fread(vidRaw,1,size,infile);
  fclose(infile);

  const int frameSize = width * height;
  const int nfr = size / frameSize;

  // Init context
  av_register_all();
  avcodec_register_all();

  AVCodec *codecEncode;
  AVCodecContext *ctxEncode= NULL;

  AVFrame *pictureEncoded;
  AVPacket avpkt;

  uint8_t *picEncodeBuf;

  int frame_in=0, frame_out=0;

  AVFormatContext *outContainer = avformat_alloc_context();
  outContainer->oformat = av_guess_format("mp4", NULL, NULL);
  outContainer->oformat->video_codec = AV_CODEC_ID_H264;
  snprintf(outContainer->filename, sizeof(outContainer->filename),"%s", frOut);

  codecEncode = avcodec_find_encoder(outContainer->oformat->video_codec);
  if (!codecEncode) { gnom_fatal(__FILE__,__LINE__,"codec not found"); }

  AVStream *video_avstream = avformat_new_stream(outContainer, codecEncode);
  if (!video_avstream) { gnom_fatal(__FILE__,__LINE__,"Could not alloc stream"); }
  if (video_avstream->codec == NULL) { gnom_fatal(__FILE__,__LINE__,"AVStream codec is NULL"); }

  ctxEncode = video_avstream->codec;

  /* put sample parameters */
  ctxEncode->bit_rate = 10000000;
  /* resolution must be a multiple of two */
  ctxEncode->width = width;
  ctxEncode->height = height;
  /* frames per second */
  ctxEncode->time_base= (AVRational){1,VIDEO_FPS};
  ctxEncode->gop_size = 30; /* emit one intra frame every ten frames */
  //ctxEncode->max_b_frames=1;
  ctxEncode->pix_fmt = AV_PIX_FMT_YUV420P;
  //av_opt_set(ctxEncode->priv_data, "preset", "slow", 0);

  /* open codec for encoder*/
  if (avcodec_open2(ctxEncode, codecEncode, NULL) < 0) { gnom_fatal(__FILE__,__LINE__,"could not open codec"); }

  pictureEncoded = avcodec_alloc_frame();
  if (!pictureEncoded) { gnom_fatal(__FILE__,__LINE__,"Could not allocate video frame"); }
  pictureEncoded->format = ctxEncode->pix_fmt;
  pictureEncoded->width  = ctxEncode->width;
  pictureEncoded->height = ctxEncode->height;

  // some formats want stream headers to be separate
  if (outContainer->oformat->flags & AVFMT_GLOBALHEADER) ctxEncode->flags |= CODEC_FLAG_GLOBAL_HEADER;

  if (!(ctxEncode->flags & AVFMT_NOFILE))
   {
    if (avio_open(&outContainer->pb, frOut, AVIO_FLAG_WRITE) < 0) { gnom_fatal(__FILE__,__LINE__,"could not open output file"); }
   }

  avformat_write_header(outContainer, NULL);

  /* alloc image and output buffer for encoder*/
  picEncodeBuf = (uint8_t *)malloc(3*frameSize/2); /* size for YUV 420 */
  pictureEncoded->data[0] = picEncodeBuf;
  pictureEncoded->data[1] = pictureEncoded->data[0] + frameSize;
  pictureEncoded->data[2] = pictureEncoded->data[1] + frameSize / 4;
  pictureEncoded->linesize[0] = ctxEncode->width;
  pictureEncoded->linesize[1] = ctxEncode->width / 2;
  pictureEncoded->linesize[2] = ctxEncode->width / 2; 

  /* encode loop */
  while (frame_in<nfr)
   {
    memcpy(pictureEncoded->data[0], vidRaw+frame_in*frameSize, width*height);
    memset(pictureEncoded->data[1], 128, width*height/4);
    memset(pictureEncoded->data[2], 128, width*height/4);
    pictureEncoded->pts = AV_NOPTS_VALUE;

    /* encode frame */
    av_init_packet(&avpkt);
    avpkt.data = NULL;    // packet data will be allocated by the encoder
    avpkt.size = 0;
    pictureEncoded->pts = av_rescale_q(frame_in, video_avstream->codec->time_base, video_avstream->time_base);
    i = avcodec_encode_video2(ctxEncode, &avpkt, pictureEncoded, &got_packet_ptr);
    //printf("encoding frame %3d (size=%5d)\n", frame_in, avpkt->size);
    if (i) printf("error encoding frame\n");
    frame_in++;
    if (got_packet_ptr) { frame_out++; av_write_frame(outContainer, &avpkt); }
    av_free_packet(&avpkt);
   }

  while (1)
   {
    av_init_packet(&avpkt);
    avpkt.data = NULL;    // packet data will be allocated by the encoder
    avpkt.size = 0;
    pictureEncoded->pts = av_rescale_q(frame_in, video_avstream->codec->time_base, video_avstream->time_base);
    i = avcodec_encode_video2(ctxEncode, &avpkt, NULL, &got_packet_ptr);
    //printf("encoding frame %3d (size=%5d)\n", frame_in, avpkt->size);
    if (!got_packet_ptr) break;
    frame_out++;
    av_write_frame(outContainer, &avpkt);
    av_free_packet(&avpkt);
   }

  av_write_trailer(outContainer);
  av_freep(video_avstream);
  if (!(outContainer->oformat->flags & AVFMT_NOFILE)) avio_close(outContainer->pb);
  avformat_free_context(outContainer);
  av_free(pictureEncoded);
  return 0;
 }

