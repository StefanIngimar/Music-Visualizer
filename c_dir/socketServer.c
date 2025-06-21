#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/samplefmt.h>
#include <libswresample/swresample.h>

#define PORT 8080
#define BACKLOG 1

int send_amplitude_stream(int client_fd){
  for(int i = 0; i < 10000; i++){
    int16_t amplitude = (i % 100) - 50;
    if(send(client_fd, &amplitude, sizeof(amplitude), 0) == -1){
      perror("send");
      return -1;
    }
    usleep(1000);
  }
  return 0;
}

int main(int argc, char const* argv[])
{
    if(argc < 2){
    printf("wrong usage\n");
    return 1;
  }
    int server_fd, client_fd;
    //ssize_t valread;
    struct sockaddr_in address;
    socklen_t addrlen = sizeof(address);
    int opt = 1;

    // Creating socket file descriptor
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Forcefully attaching socket to the port 8080
    if (setsockopt(server_fd, SOL_SOCKET,
                   SO_REUSEADDR | SO_REUSEPORT, &opt,
                   sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = inet_addr("127.0.0.1");
    address.sin_port = htons(PORT);

    // Forcefully attaching socket to the port 8080
    if (bind(server_fd, (struct sockaddr*)&address,
             sizeof(address))
        < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }
    if (listen(server_fd, BACKLOG) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }
    printf("Waiting for visualizer connection...\n");
    if ((client_fd
         = accept(server_fd, (struct sockaddr*)&address,
                  &addrlen))
        < 0) {
        perror("accept");
        exit(EXIT_FAILURE);
    }

    AVFormatContext *fmt_ctx = NULL;
    AVCodecContext *codec_ctx = NULL;
    AVCodec *codec;
    AVPacket *pkt;
    AVFrame *frame;
    int audio_stream_index;

    avformat_open_input(&fmt_ctx, argv[1], NULL, NULL);
    avformat_find_stream_info(fmt_ctx, NULL);
    audio_stream_index = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, NULL, 0);
    codec = avcodec_find_decoder(fmt_ctx->streams[audio_stream_index]->codecpar->codec_id);
    codec_ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codec_ctx, fmt_ctx->streams[audio_stream_index]->codecpar);
    avcodec_open2(codec_ctx, codec, NULL);

    pkt = av_packet_alloc();
    frame = av_frame_alloc();


  SwrContext *swr_ctx = swr_alloc_set_opts(
    NULL,
    av_get_default_channel_layout(codec_ctx->channels),
    AV_SAMPLE_FMT_S16,              // Output format
    codec_ctx->sample_rate,
    av_get_default_channel_layout(codec_ctx->channels),
    codec_ctx->sample_fmt,          // Input format
    codec_ctx->sample_rate,
    0, NULL
);

if (!swr_ctx || swr_init(swr_ctx) < 0) {
    fprintf(stderr, "Failed to initialize resampler\n");
    exit(1);
}


    // ----- Decode and stream amplitudes -----
   while (av_read_frame(fmt_ctx, pkt) >= 0) {
    if (pkt->stream_index == audio_stream_index) {
        avcodec_send_packet(codec_ctx, pkt);
        while (avcodec_receive_frame(codec_ctx, frame) == 0) {

            // Resample decoded frame to S16 interleaved
            int out_samples = av_rescale_rnd(
                swr_get_delay(swr_ctx, codec_ctx->sample_rate) + frame->nb_samples,
                codec_ctx->sample_rate, codec_ctx->sample_rate, AV_ROUND_UP
            );

            uint8_t *out_buf = NULL;
            int out_linesize;
            av_samples_alloc(&out_buf, &out_linesize, codec_ctx->channels,
                             out_samples, AV_SAMPLE_FMT_S16, 0);

            int converted_samples = swr_convert(
                swr_ctx,
                &out_buf, out_samples,
                (const uint8_t **)frame->extended_data, frame->nb_samples
            );

            int bytes_per_sample = av_get_bytes_per_sample(AV_SAMPLE_FMT_S16);
            int total_bytes = converted_samples * codec_ctx->channels * bytes_per_sample;

            send(client_fd, out_buf, total_bytes, 0);
            av_freep(&out_buf);
        }
    }
    av_packet_unref(pkt);
}
 
  
    // subtract 1 for the null
    // terminator at the end
    //send(client_fd, &sample, sizeof(sample), 0);
    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&codec_ctx);
    avformat_close_input(&fmt_ctx);
    // closing the connected socket
    close(client_fd);
  
    // closing the listening socket
    close(server_fd);
    return 0;
}
