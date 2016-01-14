The C programs in this directory are used to correct for the way in which the sky (which is a sphere) is projected onto flat PNG images by a camera lens.

This projection is called a gnomonic projection, which may also suffer barrel distortion if the lens used is badly figured.

One binary corrects the barrel distortion which may be present in images recorded by cheap lenses.

Another reprojects images around a different central point. This is useful if an attempt is being made to average many astronomical images together (i.e. to stack them), because the sky will have rotated between the various images, and the images need to be "derotated" before they can be stacked.
