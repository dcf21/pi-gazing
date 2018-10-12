This directory contains two XML files which contain the default properties of each of the lenses and sensors (i.e. models of camera) that we use.

These settings are copied into an observatory's local metadata, and can be overridden on a camera-by-camera basis.

So, for example, if a camera is using a particular lens, it will default to using the barrel correction parameters stored here. However, it may be more accurate to rederive new correction parameters for each particular set up. This is possible be changing the values of `barrel_a`, `barrel_b` and `barrel_c` in that observatory's metadata in the database.
