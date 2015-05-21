// rawvid2mp4_libav.c 
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "utils/tools.h"
#include "png/image.h"
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

  const int imageSize = width * height;
  const int frameSize = width * height * 3/2;
  const int nfr = size / frameSize;

  // Init context
  av_register_all();
  avcodec_register_all();

  AVCodec *codecEncode;
  AVCodecContext *ctxEncode= NULL;

  AVFrame *pictureEncoded;
  AVPacket avpkt;

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
  ctxEncode->bit_rate = 4000*1000;
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
  ctxEncode->flags |= CODEC_FLAG_LOOP_FILTER;
  ctxEncode->me_method = ME_HEX;
  ctxEncode->me_subpel_quality = 5;
  ctxEncode->i_quant_factor = 0.71;
  ctxEncode->qcompress = 0.6;
  ctxEncode->max_qdiff = 4;
  ctxEncode->trellis = 1; // trellis=1

  ctxEncode->width = width;
  ctxEncode->height = height;
  ctxEncode->time_base= (AVRational){1,nearestMultiple(VIDEO_FPS,1)};
  ctxEncode->pix_fmt = AV_PIX_FMT_YUV420P;

  AVDictionary* options = NULL;
  av_dict_set(&options, "preset","veryfast",0);

  /* open codec for encoder*/
  if (avcodec_open2(ctxEncode, codecEncode, &options) < 0) { gnom_fatal(__FILE__,__LINE__,"could not open codec"); }

  pictureEncoded = avcodec_alloc_frame();
  if (!pictureEncoded) { gnom_fatal(__FILE__,__LINE__,"Could not allocate video frame"); }

  // some formats want stream headers to be separate
  if (outContainer->oformat->flags & AVFMT_GLOBALHEADER) ctxEncode->flags |= CODEC_FLAG_GLOBAL_HEADER;

  if (!(ctxEncode->flags & AVFMT_NOFILE))
   {
    if (avio_open(&outContainer->pb, frOut, AVIO_FLAG_WRITE) < 0) { gnom_fatal(__FILE__,__LINE__,"could not open output file"); }
   }

  avformat_write_header(outContainer, NULL);

  /* encode loop */
  while (frame_in<nfr)
   {
    int j;
    avpicture_alloc((AVPicture *)pictureEncoded,ctxEncode->pix_fmt,ctxEncode->width,ctxEncode->height);
    for (j=0;j<height  ;j++) memcpy(pictureEncoded->data[0]+j*pictureEncoded->linesize[0], vidRaw+frame_in*frameSize+              j*width  , width  );
    for (j=0;j<height/2;j++) memcpy(pictureEncoded->data[1]+j*pictureEncoded->linesize[1], vidRaw+frame_in*frameSize+imageSize    +j*width/2, width/2);
    for (j=0;j<height/2;j++) memcpy(pictureEncoded->data[2]+j*pictureEncoded->linesize[2], vidRaw+frame_in*frameSize+imageSize*5/4+j*width/2, width/2);

    /* encode frame */
    av_init_packet(&avpkt);
    avpkt.data = NULL;    // packet data will be allocated by the encoder
    avpkt.size = 0;
    pictureEncoded->pts = av_rescale_q(frame_in, video_avstream->codec->time_base, video_avstream->time_base);
    i = avcodec_encode_video2(ctxEncode, &avpkt, pictureEncoded, &got_packet_ptr);
//printf(". %d %d %d\n",got_packet_ptr,avpkt.flags,avpkt.size); if (got_packet_ptr) fwrite(avpkt.data,1,avpkt.size,tmpout);
    avpicture_free((AVPicture *)pictureEncoded);
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

