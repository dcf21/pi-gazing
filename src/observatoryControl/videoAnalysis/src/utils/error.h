// error.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// Functions for returning messages to the user

#ifndef ERROR_H
#define ERROR_H 1

#define ERR_INTERNAL 100
#define ERR_GENERAL  101
#define ERR_SYNTAX   102
#define ERR_NUMERIC  103
#define ERR_FILE     104
#define ERR_MEMORY   105
#define ERR_STACKED  106
#define ERR_PREFORMED 107

extern char temp_err_string[];

void gnom_error_setstreaminfo(int linenumber, char *filename);

void gnom_error(int ErrType, char *msg);

void gnom_fatal(char *file, int line, char *msg);

void gnom_warning(int ErrType, char *msg);

void gnom_report(char *msg);

void gnom_log(char *msg);

void dcffread(void *ptr, size_t size, size_t nmemb, FILE *stream);

#endif

