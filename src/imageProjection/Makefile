# MAKEFILE
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

CWD=$(shell pwd)

VERSION = 0.0.1
DATE    = 08/10/2014

COMPILE = $(CC) -Wall -g -fopenmp `gsl-config --cflags` -c -I $(CWD)/src
LINK    = $(CC) -Wall -g -fopenmp
LIBS    = `gsl-config --libs` -lpng -lm

OPTIMISATION = -O1

DEBUG   = -D DEBUG=1
NODEBUG = -D DEBUG=0

LOCAL_SRCDIR = src
LOCAL_OBJDIR = obj
LOCAL_DOCDIR = doc
LOCAL_BINDIR = bin

STACK_FILES = asciidouble.c backgroundSub.c error.c gnomonic.c imageProcess.c image_in.c image_out.c readConfig.c settings.c stack.c
CAMFT_FILES = asciidouble.c backgroundSub.c error.c gnomonic.c imageProcess.c image_in.c image_out.c readConfig.c settings.c cameraFit.c
BARRL_FILES = asciidouble.c backgroundSub.c error.c gnomonic.c imageProcess.c image_in.c image_out.c readConfig.c settings.c barrel.c
SUBTR_FILES = asciidouble.c backgroundSub.c error.c gnomonic.c imageProcess.c image_in.c image_out.c readConfig.c settings.c subtract.c

HEADERS = asciidouble.h backgroundSub.h error.h gnomonic.h imageProcess.h image.h readConfig.h settings.h str_constants.h

STACK_SOURCES         = $(STACK_FILES:%.c=$(LOCAL_SRCDIR)/%.c)
STACK_OBJECTS         = $(STACK_FILES:%.c=$(LOCAL_OBJDIR)/%.o)
STACK_OBJECTS_DEBUG   = $(STACK_OBJECTS:%.o=%.debug.o)

CAMFT_SOURCES         = $(CAMFT_FILES:%.c=$(LOCAL_SRCDIR)/%.c)
CAMFT_OBJECTS         = $(CAMFT_FILES:%.c=$(LOCAL_OBJDIR)/%.o)
CAMFT_OBJECTS_DEBUG   = $(CAMFT_OBJECTS:%.o=%.debug.o)

BARRL_SOURCES         = $(BARRL_FILES:%.c=$(LOCAL_SRCDIR)/%.c)
BARRL_OBJECTS         = $(BARRL_FILES:%.c=$(LOCAL_OBJDIR)/%.o)
BARRL_OBJECTS_DEBUG   = $(BARRL_OBJECTS:%.o=%.debug.o)

SUBTR_SOURCES         = $(SUBTR_FILES:%.c=$(LOCAL_SRCDIR)/%.c)
SUBTR_OBJECTS         = $(SUBTR_FILES:%.c=$(LOCAL_OBJDIR)/%.o)
SUBTR_OBJECTS_DEBUG   = $(SUBTR_OBJECTS:%.o=%.debug.o)

ALL_HFILES             = $(HEADERS:%.h=$(LOCAL_SRCDIR)/%.h) Makefile


COMMON_SWITCHES = -D VERSION=\"$(VERSION)\"  -D DATE=\"$(DATE)\"  -D SRCDIR=\"$(CWD)/$(LOCAL_SRCDIR)/\"

all: $(LOCAL_BINDIR)/stack $(LOCAL_BINDIR)/debug/stack $(LOCAL_BINDIR)/camfit $(LOCAL_BINDIR)/debug/camfit $(LOCAL_BINDIR)/barrel $(LOCAL_BINDIR)/debug/barrel $(LOCAL_BINDIR)/subtract $(LOCAL_BINDIR)/debug/subtract

#
# General macros for the compile steps
#

$(LOCAL_OBJDIR)/%.o:         $(LOCAL_SRCDIR)/%.c $(ALL_HFILES)
	mkdir -p $(LOCAL_OBJDIR) 
	$(COMPILE) $(OPTIMISATION) $(NODEBUG) $(COMMON_SWITCHES) $< -o $@

$(LOCAL_OBJDIR)/%.debug.o:   $(LOCAL_SRCDIR)/%.c $(ALL_HFILES)
	mkdir -p $(LOCAL_OBJDIR)
	$(COMPILE) $(OPTIMISATION) $(DEBUG)   $(COMMON_SWITCHES)     $< -o $@

#
# Make the binaries
#

$(LOCAL_BINDIR)/stack:         $(STACK_OBJECTS)
	mkdir -p $(LOCAL_BINDIR)
	$(LINK) $(OPTIMISATION) $(STACK_OBJECTS) $(LIBS)       -o $(LOCAL_BINDIR)/stack

$(LOCAL_BINDIR)/debug/stack:   $(STACK_OBJECTS_DEBUG)
	mkdir -p $(LOCAL_BINDIR)/debug
	$(LINK) $(OPTIMISATION) $(STACK_OBJECTS_DEBUG) $(LIBS) -o $(LOCAL_BINDIR)/debug/stack

$(LOCAL_BINDIR)/camfit:        $(CAMFT_OBJECTS)
	mkdir -p $(LOCAL_BINDIR)
	$(LINK) $(OPTIMISATION) $(CAMFT_OBJECTS) $(LIBS)       -o $(LOCAL_BINDIR)/camfit

$(LOCAL_BINDIR)/debug/camfit:  $(CAMFT_OBJECTS_DEBUG)
	mkdir -p $(LOCAL_BINDIR)/debug
	$(LINK) $(OPTIMISATION) $(CAMFT_OBJECTS_DEBUG) $(LIBS) -o $(LOCAL_BINDIR)/debug/camfit

$(LOCAL_BINDIR)/barrel:        $(BARRL_OBJECTS)
	mkdir -p $(LOCAL_BINDIR)
	$(LINK) $(OPTIMISATION) $(BARRL_OBJECTS) $(LIBS)       -o $(LOCAL_BINDIR)/barrel

$(LOCAL_BINDIR)/debug/barrel:  $(BARRL_OBJECTS_DEBUG)
	mkdir -p $(LOCAL_BINDIR)/debug
	$(LINK) $(OPTIMISATION) $(BARRL_OBJECTS_DEBUG) $(LIBS) -o $(LOCAL_BINDIR)/debug/barrel

$(LOCAL_BINDIR)/subtract:        $(SUBTR_OBJECTS)
	mkdir -p $(LOCAL_BINDIR)
	$(LINK) $(OPTIMISATION) $(SUBTR_OBJECTS) $(LIBS)       -o $(LOCAL_BINDIR)/subtract

$(LOCAL_BINDIR)/debug/subtract:  $(SUBTR_OBJECTS_DEBUG)
	mkdir -p $(LOCAL_BINDIR)/debug
	$(LINK) $(OPTIMISATION) $(SUBTR_OBJECTS_DEBUG) $(LIBS) -o $(LOCAL_BINDIR)/debug/subtract

#
# Clean macros
#

clean:
	rm -vfR $(LOCAL_OBJDIR) $(LOCAL_BINDIR) gnom.log* locate.*.out

afresh: clean all

